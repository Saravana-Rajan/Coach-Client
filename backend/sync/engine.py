"""
Sync engine: pulls all data from simulated Salesforce,
runs change detection, updates local DB, creates audit records.
"""
import logging

from django.utils import timezone
from salesforce_sim.models import SFCoach, SFAccount, SFContact, SFAssignment
from coaching.models import Coach, Account, Contact, Assignment
from .models import SyncLog, AuditRecord
from . import detector

logger = logging.getLogger(__name__)


def run_sync():
    """Execute a full sync. Returns the SyncLog instance."""
    sync_log = SyncLog.objects.create(status="in_progress")

    try:
        # 0. Check for schema changes and auto-migrate if needed
        try:
            from admin_management.views_schema import (
                _detect_schema_differences, _generate_migration_sql,
                SF_TO_LOCAL_TABLE_MAP, TABLE_TO_ENTITY,
            )
            from admin_management.models import SchemaMigrationLog
            from django.db import connections

            diffs = _detect_schema_differences()
            for diff in diffs:
                entity_type = diff["entity_type"]
                sf_table = [k for k, v in TABLE_TO_ENTITY.items() if v == entity_type][0]
                local_table = SF_TO_LOCAL_TABLE_MAP[sf_table]
                migration_sql, rollback_sql = _generate_migration_sql(diff, local_table)

                log_entry = SchemaMigrationLog.objects.create(
                    entity_type=entity_type,
                    field_name=diff["field_name"],
                    old_type=diff.get("old_type") or "",
                    new_type=diff.get("new_type") or "",
                    old_constraints=diff.get("old_constraints", {}),
                    new_constraints=diff.get("new_constraints", {}),
                    migration_sql=migration_sql,
                    rollback_sql=rollback_sql,
                    status="detected",
                )
                if migration_sql and not migration_sql.startswith("--"):
                    try:
                        with connections["default"].cursor() as cursor:
                            for stmt in migration_sql.split(";"):
                                stmt = stmt.strip()
                                if stmt and not stmt.startswith("--"):
                                    cursor.execute(stmt)
                        log_entry.status = "migrated"
                        log_entry.applied_at = timezone.now()
                        log_entry.save()
                        logger.info(f"Auto-migrated schema: {log_entry}")
                    except Exception as e:
                        log_entry.status = "failed"
                        log_entry.error_message = str(e)
                        log_entry.save()
                        logger.warning(f"Schema auto-migration failed: {e}")
        except Exception as e:
            logger.warning(f"Schema detection skipped: {e}")

        # 1. Pull all source data
        sf_coaches = list(SFCoach.objects.using("salesforce").all())
        sf_accounts = list(SFAccount.objects.using("salesforce").select_related("coach").all())
        sf_contacts = list(SFContact.objects.using("salesforce").select_related("coach", "account").all())
        sf_assignments = list(SFAssignment.objects.using("salesforce").select_related("coach", "contact", "account").all())

        # 2. Pull all local data
        local_coaches = list(Coach.objects.all())
        local_accounts = list(Account.objects.select_related("coach").all())
        local_contacts = list(Contact.objects.select_related("coach", "account").all())
        local_assignments = list(Assignment.objects.select_related("coach", "contact", "account").all())

        # 3. Build lookup maps: SF PK id -> coach name (for source)
        sf_coach_pk_to_name = {str(c.id): c.name for c in sf_coaches}
        sf_coach_pk_to_sfid = {str(c.id): str(c.sf_id) for c in sf_coaches}

        # Local: coach PK id -> coach name
        local_coach_pk_to_name = {str(c.id): c.name for c in local_coaches}
        local_coach_pk_to_sfid = {str(c.id): str(c.sf_id) for c in local_coaches}

        # 4. Detect changes
        all_changes = []
        all_changes.extend(detector.detect_coach_changes(sf_coaches, local_coaches))
        all_changes.extend(detector.detect_account_changes(
            sf_accounts, local_accounts, sf_coach_pk_to_name, local_coach_pk_to_name
        ))
        all_changes.extend(detector.detect_contact_changes(
            sf_contacts, local_contacts, sf_coach_pk_to_name, local_coach_pk_to_name
        ))
        all_changes.extend(detector.detect_assignment_changes(
            sf_assignments, local_assignments, sf_coach_pk_to_name, local_coach_pk_to_name
        ))

        # 5. Create audit records
        for change in all_changes:
            AuditRecord.objects.create(sync=sync_log, **change)

        # 6. Collect reassignment info BEFORE updating local data
        reassignments = _collect_reassignments(all_changes, sf_contacts, sf_accounts, sf_coaches)

        # 7. Update local database to match source
        _sync_coaches(sf_coaches)
        _sync_accounts(sf_accounts, sf_coaches)
        _sync_contacts(sf_contacts, sf_coaches, sf_accounts)
        _sync_assignments(sf_assignments, sf_coaches, sf_contacts, sf_accounts)

        # 8. Finalize
        sync_log.status = "completed"
        sync_log.changes_detected = len(all_changes)
        sync_log.completed_at = timezone.now()
        sync_log.save()

        # 9. Clear sync/schema notification — sync is done
        try:
            from salesforce_connector.models import SyncNotification
            notif = SyncNotification.get_instance()
            notif.out_of_sync = False
            notif.message = ""
            notif.last_synced = timezone.now()
            notif.save()
        except Exception:
            pass

        # 10. Generate transition briefs (non-blocking)
        if reassignments:
            _generate_briefs(reassignments, sync_log)

        return sync_log

    except Exception as e:
        logger.exception("Sync failed")
        sync_log.status = "failed"
        sync_log.error_message = str(e)
        sync_log.completed_at = timezone.now()
        sync_log.save()
        return sync_log


def run_sync_direct(sf_data):
    """Direct sync: Salesforce API data → app DB. No intermediate database.

    Takes the raw pulled data dict from client.pull_all_data() and syncs
    directly to the application database by comparing against local state.
    """
    sync_log = SyncLog.objects.create(status="in_progress")

    try:
        # 1. Build source data from API response
        source_coaches = {}  # name → coach dict
        for acct in sf_data.get("accounts", []):
            coach_name = acct.get("coach_name", "")
            if coach_name and coach_name not in source_coaches:
                source_coaches[coach_name] = {
                    "name": coach_name,
                    "email": coach_name.lower().replace(" ", ".") + "@coaching.com",
                    "is_active": True,
                }
        for ct in sf_data.get("contacts", []):
            coach_name = ct.get("coach_name", "")
            if coach_name and coach_name not in source_coaches:
                source_coaches[coach_name] = {
                    "name": coach_name,
                    "email": coach_name.lower().replace(" ", ".") + "@coaching.com",
                    "is_active": True,
                }

        # 2. Get current local state
        local_coaches = list(Coach.objects.all())
        local_accounts = list(Account.objects.select_related("coach").all())
        local_contacts = list(Contact.objects.select_related("coach", "account").all())

        # 3. Upsert coaches from SF data
        import uuid
        for coach_name, coach_data in source_coaches.items():
            Coach.objects.update_or_create(
                name=coach_data["name"],
                defaults={
                    "sf_id": Coach.objects.filter(name=coach_data["name"]).values_list("sf_id", flat=True).first() or uuid.uuid4(),
                    "email": coach_data["email"],
                    "is_active": coach_data["is_active"],
                },
            )

        # 4. Upsert accounts from SF data
        all_changes = []
        local_account_map = {a.name: a for a in local_accounts}

        for acct in sf_data.get("accounts", []):
            acct_name = acct["name"]
            coach_name = acct.get("coach_name", "")
            coach = Coach.objects.filter(name=coach_name).first() if coach_name else None

            local_acct = local_account_map.get(acct_name)
            if local_acct:
                # Check for reassignment
                old_coach = local_acct.coach.name if local_acct.coach else "Unassigned"
                new_coach = coach_name or "Unassigned"
                if old_coach != new_coach:
                    all_changes.append({
                        "change_type": "account_reassigned",
                        "entity_type": "account",
                        "entity_sf_id": local_acct.sf_id,
                        "entity_name": acct_name,
                        "before_state": {"coach": old_coach},
                        "after_state": {"coach": new_coach},
                        "coach_name": new_coach,
                        "account_name": acct_name,
                    })
                # Check for field updates
                before = {}
                after = {}
                if acct.get("industry", "") and acct["industry"] != local_acct.industry:
                    before["industry"] = local_acct.industry
                    after["industry"] = acct["industry"]
                if before:
                    all_changes.append({
                        "change_type": "account_updated",
                        "entity_type": "account",
                        "entity_sf_id": local_acct.sf_id,
                        "entity_name": acct_name,
                        "before_state": before,
                        "after_state": after,
                        "account_name": acct_name,
                    })
                # Update
                local_acct.industry = acct.get("industry", local_acct.industry)
                local_acct.website = acct.get("website", local_acct.website)
                local_acct.assigned_coach = coach_name
                local_acct.coach = coach
                local_acct.save()
            else:
                # New account
                Account.objects.create(
                    sf_id=uuid.uuid4(),
                    name=acct_name,
                    industry=acct.get("industry", ""),
                    website=acct.get("website", ""),
                    coaching_start_date=timezone.now().date(),
                    assigned_coach=coach_name,
                    coach=coach,
                )
                all_changes.append({
                    "change_type": "account_added",
                    "entity_type": "account",
                    "entity_sf_id": uuid.uuid4(),
                    "entity_name": acct_name,
                    "before_state": None,
                    "after_state": {"name": acct_name, "coach": coach_name},
                    "coach_name": coach_name or "Unassigned",
                    "account_name": acct_name,
                })

        # 5. Upsert contacts from SF data
        local_contact_map = {c.email: c for c in local_contacts}

        for ct in sf_data.get("contacts", []):
            full_name = f"{ct.get('first_name', '')} {ct.get('last_name', '')}".strip()
            email = ct.get("email", "")
            coach_name = ct.get("coach_name", "")
            coach = Coach.objects.filter(name=coach_name).first() if coach_name else None
            account = Account.objects.filter(name__icontains=ct.get("account_id", "")).first()

            local_ct = local_contact_map.get(email)
            if local_ct:
                old_coach = local_ct.coach.name if local_ct.coach else "Unassigned"
                new_coach = coach_name or "Unassigned"
                if old_coach != new_coach:
                    all_changes.append({
                        "change_type": "contact_reassigned",
                        "entity_type": "contact",
                        "entity_sf_id": local_ct.sf_id,
                        "entity_name": full_name or local_ct.name,
                        "before_state": {"coach": old_coach},
                        "after_state": {"coach": new_coach},
                        "coach_name": new_coach,
                    })
                local_ct.name = full_name or local_ct.name
                local_ct.title = ct.get("title", local_ct.title)
                local_ct.phone = ct.get("phone", local_ct.phone)
                local_ct.assigned_coach = coach_name
                local_ct.coach = coach
                local_ct.save()

        # 6. Create audit records
        for change in all_changes:
            AuditRecord.objects.create(sync=sync_log, **change)

        # 7. Generate transition briefs
        reassignments = []
        for change in all_changes:
            if change["change_type"] == "contact_reassigned":
                reassignments.append({
                    "contact_name": change["entity_name"],
                    "contact_title": "",
                    "contact_email": "",
                    "contact_sf_id": str(change["entity_sf_id"]),
                    "account_name": change.get("account_name", "Unknown"),
                    "account_industry": "",
                    "account_start_date": "",
                    "previous_coach": change["before_state"].get("coach", "Unknown"),
                    "new_coach": change["after_state"].get("coach", "Unknown"),
                    "new_coach_sf_id": None,
                })

        # 8. Finalize
        sync_log.status = "completed"
        sync_log.changes_detected = len(all_changes)
        sync_log.completed_at = timezone.now()
        sync_log.save()

        # 9. Clear notification
        try:
            from salesforce_connector.models import SyncNotification
            notif = SyncNotification.get_instance()
            notif.out_of_sync = False
            notif.message = ""
            notif.last_synced = timezone.now()
            notif.save()
        except Exception:
            pass

        # 10. Generate briefs (non-blocking)
        if reassignments:
            _generate_briefs(reassignments, sync_log)

        return sync_log

    except Exception as e:
        logger.exception("Direct sync failed")
        sync_log.status = "failed"
        sync_log.error_message = str(e)
        sync_log.completed_at = timezone.now()
        sync_log.save()
        return sync_log


def _sync_coaches(sf_coaches):
    sf_ids = set()
    for sf_c in sf_coaches:
        sf_ids.add(str(sf_c.sf_id))
        Coach.objects.update_or_create(
            sf_id=sf_c.sf_id,
            defaults={
                "name": sf_c.name,
                "email": sf_c.email,
                "active_clients": sf_c.active_clients,
                "is_active": sf_c.is_active,
            },
        )
    # Handle coaches marked as inactive (leaving org)
    for sf_c in sf_coaches:
        if not sf_c.is_active:
            local_coach = Coach.objects.filter(sf_id=sf_c.sf_id).first()
            if local_coach and local_coach.is_active:
                local_coach.is_active = False
                local_coach.save()
                logger.info(f"Coach '{local_coach.name}' marked as inactive (left org)")

    # Remove coaches no longer in source
    Coach.objects.exclude(sf_id__in=[c.sf_id for c in sf_coaches]).delete()


def _sync_accounts(sf_accounts, sf_coaches):
    sf_coach_map = {c.id: c.sf_id for c in sf_coaches}  # SF PK -> sf_id
    for sf_a in sf_accounts:
        coach = None
        if sf_a.coach_id:
            coach_sf_id = sf_coach_map.get(sf_a.coach_id)
            if coach_sf_id:
                coach = Coach.objects.filter(sf_id=coach_sf_id).first()
        Account.objects.update_or_create(
            sf_id=sf_a.sf_id,
            defaults={
                "name": sf_a.name,
                "industry": sf_a.industry,
                "website": sf_a.website,
                "coaching_start_date": sf_a.coaching_start_date,
                "assigned_coach": sf_a.assigned_coach,
                "coach": coach,
            },
        )
    Account.objects.exclude(sf_id__in=[a.sf_id for a in sf_accounts]).delete()


def _sync_contacts(sf_contacts, sf_coaches, sf_accounts):
    sf_coach_map = {c.id: c.sf_id for c in sf_coaches}
    sf_account_map = {a.id: a.sf_id for a in sf_accounts}

    for sf_con in sf_contacts:
        coach = None
        if sf_con.coach_id:
            coach_sf_id = sf_coach_map.get(sf_con.coach_id)
            if coach_sf_id:
                coach = Coach.objects.filter(sf_id=coach_sf_id).first()
        account = None
        if sf_con.account_id:
            account_sf_id = sf_account_map.get(sf_con.account_id)
            if account_sf_id:
                account = Account.objects.filter(sf_id=account_sf_id).first()
        Contact.objects.update_or_create(
            sf_id=sf_con.sf_id,
            defaults={
                "name": sf_con.name,
                "title": sf_con.title,
                "phone": sf_con.phone,
                "email": sf_con.email,
                "assigned_coach": sf_con.assigned_coach,
                "account": account,
                "coach": coach,
            },
        )
    Contact.objects.exclude(sf_id__in=[c.sf_id for c in sf_contacts]).delete()


def _sync_assignments(sf_assignments, sf_coaches, sf_contacts, sf_accounts):
    sf_coach_map = {c.id: c.sf_id for c in sf_coaches}
    sf_contact_map = {c.id: c.sf_id for c in sf_contacts}
    sf_account_map = {a.id: a.sf_id for a in sf_accounts}

    for sf_a in sf_assignments:
        coach = Coach.objects.filter(sf_id=sf_coach_map.get(sf_a.coach_id)).first()
        contact = Contact.objects.filter(sf_id=sf_contact_map.get(sf_a.contact_id)).first()
        account = Account.objects.filter(sf_id=sf_account_map.get(sf_a.account_id)).first()

        if coach and contact and account:
            Assignment.objects.update_or_create(
                sf_id=sf_a.sf_id,
                defaults={
                    "coach": coach,
                    "contact": contact,
                    "account": account,
                    "status": sf_a.status,
                },
            )
    Assignment.objects.exclude(sf_id__in=[a.sf_id for a in sf_assignments]).delete()


def _collect_reassignments(changes, sf_contacts, sf_accounts, sf_coaches):
    """Identify contact reassignments for brief generation.

    Handles simultaneous multi-coach swaps correctly because each
    contact/account reassignment is detected independently by comparing
    sf_id-matched entities' coach fields. If Coach A's clients go to B
    and B's go to A in the same sync, both changes are detected as
    separate contact_reassigned audit records.
    """
    reassignments = []
    sf_coach_map = {c.id: c for c in sf_coaches}
    sf_account_map = {a.id: a for a in sf_accounts}

    for change in changes:
        if change["change_type"] == "contact_reassigned":
            sf_id = change["entity_sf_id"]
            sf_contact = next((c for c in sf_contacts if str(c.sf_id) == str(sf_id)), None)
            if sf_contact:
                new_coach = sf_coach_map.get(sf_contact.coach_id)
                account = sf_account_map.get(sf_contact.account_id)
                reassignments.append({
                    "contact_name": sf_contact.name,
                    "contact_title": sf_contact.title,
                    "contact_email": sf_contact.email,
                    "contact_sf_id": str(sf_contact.sf_id),
                    "account_name": account.name if account else "Unknown",
                    "account_industry": account.industry if account else "Unknown",
                    "account_start_date": str(account.coaching_start_date) if account else "Unknown",
                    "previous_coach": change["before_state"].get("coach", "Unknown"),
                    "new_coach": new_coach.name if new_coach else "Unknown",
                    "new_coach_sf_id": str(new_coach.sf_id) if new_coach else None,
                })
    return reassignments


def _generate_briefs(reassignments, sync_log):
    """Generate transition briefs. Failures are logged, not raised."""
    from briefs.generator import generate_transition_brief
    from briefs.models import TransitionBrief
    from coaching.models import Coach

    for r in reassignments:
        try:
            content = generate_transition_brief(r)
            coach = Coach.objects.filter(sf_id=r["new_coach_sf_id"]).first() if r["new_coach_sf_id"] else None
            audit_record = AuditRecord.objects.filter(
                sync=sync_log,
                entity_sf_id=r["contact_sf_id"],
                change_type="contact_reassigned",
            ).first()
            TransitionBrief.objects.create(
                sync=sync_log,
                audit_record=audit_record,
                coach=coach,
                contact_name=r["contact_name"],
                account_name=r["account_name"],
                previous_coach_name=r["previous_coach"],
                content=content,
            )
        except Exception as e:
            logger.error(f"Failed to generate brief for {r['contact_name']}: {e}")
