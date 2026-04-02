import logging

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from sync.engine import run_sync
from .client import pull_all_data, seed_to_simulated_source
from .models import SyncNotification

logger = logging.getLogger(__name__)


@require_POST
@staff_member_required
def pull_from_salesforce(request):
    """
    Admin-only endpoint that pulls Accounts and Contacts from the real
    Salesforce org and seeds them into the simulated-source SQLite tables.
    """
    try:
        data = pull_all_data()
        summary = seed_to_simulated_source(data)
        return JsonResponse(
            {
                "status": "ok",
                "pulled": {
                    "accounts": len(data["accounts"]),
                    "contacts": len(data["contacts"]),
                },
                "seeded": summary,
            }
        )
    except Exception as exc:
        logger.exception("Salesforce pull failed")
        return JsonResponse(
            {"status": "error", "detail": str(exc)},
            status=500,
        )


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])  # Salesforce calls this — no auth
def sf_webhook_notify(request):
    """Salesforce Flow calls this when Account/Contact changes.
    Just sets a flag — no sync happens yet."""
    notif = SyncNotification.get_instance()
    notif.out_of_sync = True
    notif.last_notified = timezone.now()
    notif.message = "Salesforce data changed"
    notif.save()
    return Response({"status": "ok", "message": "Notification received"})


@api_view(["GET"])
def sf_sync_status(request):
    """Frontend polls this — checks real Salesforce vs local data."""
    if not request.user.is_authenticated:
        return Response({"error": "Auth required"}, status=401)

    # First check the webhook flag
    notif = SyncNotification.get_instance()
    if notif.out_of_sync:
        return Response({
            "out_of_sync": True,
            "last_notified": notif.last_notified,
            "last_synced": notif.last_synced,
            "message": notif.message or "Salesforce data changed",
        })

    # If no webhook flag, do a quick check against real Salesforce
    try:
        from .client import get_sf_connection
        from salesforce_sim.models import SFAccount, SFContact

        sf = get_sf_connection()
        # Quick check: compare coach assignments from SF vs local
        sf_accounts = sf.query_all("SELECT Name, Coach__c FROM Account WHERE Coach__c != null ORDER BY Name")
        sf_coach_map = {r["Name"]: r["Coach__c"] for r in sf_accounts["records"]}

        from salesforce_sim.models import SFAccount
        local_accounts = SFAccount.objects.using("salesforce").select_related("coach").all()
        local_coach_map = {a.name: a.coach.name if a.coach else "" for a in local_accounts}

        # Find differences
        diffs = []
        for name, sf_coach in sf_coach_map.items():
            local_coach = local_coach_map.get(name, "")
            if sf_coach != local_coach:
                diffs.append(f"{name}: {local_coach} → {sf_coach}")

        out_of_sync = len(diffs) > 0

        if out_of_sync:
            notif.out_of_sync = True
            notif.last_notified = timezone.now()
            notif.message = f"{len(diffs)} change(s) detected: {', '.join(diffs[:3])}"
            notif.save()

        return Response({
            "out_of_sync": out_of_sync,
            "last_notified": notif.last_notified,
            "last_synced": notif.last_synced,
            "message": notif.message if out_of_sync else "",
        })
    except Exception:
        # If SF check fails, just return the flag status
        return Response({
            "out_of_sync": notif.out_of_sync,
            "last_notified": notif.last_notified,
            "last_synced": notif.last_synced,
            "message": notif.message,
        })


@api_view(["GET"])
def sf_schema_check(request):
    """Production-grade schema change detection.

    Primary: describe() — checks CURRENT field types in Salesforce and compares
    against what we last saw. This always reflects the real state.
    Secondary: SetupAuditTrail — provides details on who changed what and when.

    The describe() results are stored so we can compare against the last known
    state and detect changes even after a sync.
    """
    if not request.user.is_authenticated or not request.user.is_admin():
        return Response({"error": "Admin only"}, status=403)

    schema_changes = []

    try:
        from .client import get_sf_connection
        sf = get_sf_connection()

        # ── Primary: describe() — always reflects current truth ──
        # Store last-known types in SyncNotification.message field won't work long term
        # Use a simple file-based cache for last-known schema
        import json
        from django.conf import settings

        schema_cache_file = settings.BASE_DIR / ".sf_schema_cache.json"
        last_known = {}
        try:
            with open(schema_cache_file, "r") as f:
                last_known = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        current_schema = {}
        objects_to_check = ["Account", "Contact"]

        for obj_name in objects_to_check:
            try:
                describe = sf.__getattr__(obj_name).describe()
                fields = {f["name"]: f["type"] for f in describe["fields"]}
                current_schema[obj_name] = fields

                # Compare against last known
                last_fields = last_known.get(obj_name, {})
                if last_fields:
                    for field_name, current_type in fields.items():
                        old_type = last_fields.get(field_name)
                        if old_type and old_type != current_type:
                            schema_changes.append({
                                "object": obj_name,
                                "field": field_name,
                                "expected_type": old_type,
                                "actual_type": current_type,
                                "detected_via": "describe",
                            })
                    # Check for removed fields
                    for field_name in last_fields:
                        if field_name not in fields:
                            schema_changes.append({
                                "object": obj_name,
                                "field": field_name,
                                "expected_type": last_fields[field_name],
                                "actual_type": "REMOVED",
                                "detected_via": "describe",
                            })
                    # Check for added fields
                    for field_name in fields:
                        if field_name not in last_fields:
                            schema_changes.append({
                                "object": obj_name,
                                "field": field_name,
                                "expected_type": "NEW",
                                "actual_type": fields[field_name],
                                "detected_via": "describe",
                            })
            except Exception as e:
                logger.warning(f"Could not describe {obj_name}: {e}")

        # Save current schema as the new baseline (only if no changes found,
        # otherwise keep old baseline so banner keeps showing until synced)
        if not schema_changes:
            try:
                with open(schema_cache_file, "w") as f:
                    json.dump(current_schema, f)
            except Exception:
                pass

        # ── Secondary: SetupAuditTrail for change details ──
        if schema_changes:
            try:
                trail_results = sf.query(
                    "SELECT Action, Display, CreatedDate, CreatedBy.Name "
                    "FROM SetupAuditTrail "
                    "WHERE CreatedDate = TODAY "
                    "ORDER BY CreatedDate DESC LIMIT 10"
                )
                for rec in trail_results.get("records", []):
                    display = rec.get("Display", "")
                    if any(kw in display.lower() for kw in ["field", "custom field", "coach"]):
                        # Enrich schema changes with who/when details
                        for change in schema_changes:
                            if change["field"].lower() in display.lower():
                                change["changed_by"] = rec.get("CreatedBy", {}).get("Name", "Unknown")
                                change["description"] = display
            except Exception:
                pass

        # Set notification if changes found
        if schema_changes:
            notif = SyncNotification.get_instance()
            notif.out_of_sync = True
            notif.last_notified = timezone.now()
            change_summary = ", ".join(
                f"{c['object']}.{c['field']}: {c['expected_type']} -> {c['actual_type']}"
                for c in schema_changes[:3]
            )
            notif.message = f"Schema changed: {change_summary}"
            notif.save()

        return Response({
            "schema_changed": len(schema_changes) > 0,
            "changes": schema_changes,
        })

    except Exception as e:
        return Response({
            "schema_changed": False,
            "changes": [],
            "error": str(e),
        })


def _parse_object_from_trail(display):
    """Extract object name from SetupAuditTrail Display/Section string.

    Handles patterns like:
    - 'Changed field type of Assigned Coach custom field from Text to Number'
    - Section: 'Customize Accounts'
    """
    if not display:
        return "Unknown"
    display_lower = display.lower()
    if "account" in display_lower:
        return "Account"
    if "contact" in display_lower:
        return "Contact"
    if "coach" in display_lower:
        return "Account"  # Coach__c is on Account/Contact
    if "lead" in display_lower:
        return "Lead"
    if "opportunity" in display_lower:
        return "Opportunity"
    return "Unknown"


def _parse_field_from_trail(display):
    """Extract field name from SetupAuditTrail Display string."""
    if not display:
        return "Unknown"
    import re
    # Look for __c pattern
    match = re.search(r'(\w+__c)', display)
    if match:
        return match.group(1)
    # Look for quoted field names
    match = re.search(r'"([^"]+)"', display)
    if match:
        return match.group(1)
    return display[:80]


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def sf_schema_webhook(request):
    """Receives real-time schema change notifications from Salesforce.

    Called by the SchemaChangeWebhook Apex class when the scheduled
    SchemaChangeDetector finds field changes in SetupAuditTrail.

    This is the PUSH mechanism — no polling needed. Salesforce tells us
    instantly when a schema change happens.
    """
    data = request.data
    source = data.get("source", "unknown")
    changes = data.get("changes", [])

    if not changes:
        return Response({"status": "ok", "message": "No changes"})

    logger.info(f"Schema webhook received from {source}: {len(changes)} change(s)")

    # Set notification flag
    notif = SyncNotification.get_instance()
    notif.out_of_sync = True
    notif.last_notified = timezone.now()

    change_descriptions = []
    for change in changes:
        desc = f"{change.get('object_name', '?')}.{change.get('field_name', '?')}"
        if change.get("description"):
            desc += f" ({change['description'][:50]})"
        change_descriptions.append(desc)

    notif.message = f"Schema changed in Salesforce: {', '.join(change_descriptions[:3])}"
    notif.save()

    # Also log to SchemaMigrationLog and generate real migration SQL
    try:
        from admin_management.models import SchemaMigrationLog
        from admin_management.views_schema import (
            _generate_migration_sql, SF_TO_LOCAL_TABLE_MAP, TABLE_TO_ENTITY,
        )
        for change in changes:
            entity_type = change.get("object_name", "unknown").lower()
            old_type = change.get("old_type", "")
            new_type = change.get("new_type", "")
            field_name = change.get("field_name", "unknown")

            # Generate real migration SQL if possible
            migration_sql = ""
            rollback_sql = ""
            sf_table = next((k for k, v in TABLE_TO_ENTITY.items() if v == entity_type), None)
            if sf_table and sf_table in SF_TO_LOCAL_TABLE_MAP:
                local_table = SF_TO_LOCAL_TABLE_MAP[sf_table]
                diff = {
                    "field_name": field_name,
                    "change": "type_changed" if old_type and new_type else "field_added",
                    "old_type": old_type.upper() if old_type else None,
                    "new_type": new_type.upper() if new_type else "TEXT",
                    "old_constraints": {},
                    "new_constraints": {"notnull": False, "default": "''"},
                }
                migration_sql, rollback_sql = _generate_migration_sql(diff, local_table)

            if not migration_sql:
                migration_sql = f"-- Detected via webhook: {change.get('description', '')}"

            SchemaMigrationLog.objects.create(
                entity_type=entity_type,
                field_name=field_name,
                old_type=old_type,
                new_type=new_type,
                status="detected",
                migration_sql=migration_sql,
                rollback_sql=rollback_sql,
            )
    except Exception as e:
        logger.warning(f"Failed to log schema change: {e}")

    return Response({
        "status": "ok",
        "message": f"Received {len(changes)} schema change(s)",
        "changes_logged": len(changes),
    })


@api_view(["POST"])
def sf_pull_and_sync(request):
    """One-click: pull from Salesforce + sync + clear notification.

    Also detects schema changes via describe(), logs them, and updates
    the schema cache baseline after successful sync.
    """
    if not request.user.is_authenticated or not request.user.is_admin():
        return Response({"error": "Admin only"}, status=403)
    try:
        import json
        from django.conf import settings

        # ── Step 0: Detect schema changes BEFORE pulling data ──
        schema_changes_detected = []
        try:
            from .client import get_sf_connection
            sf = get_sf_connection()

            schema_cache_file = settings.BASE_DIR / ".sf_schema_cache.json"
            last_known = {}
            try:
                with open(schema_cache_file, "r") as f:
                    last_known = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass

            current_schema = {}
            for obj_name in ["Account", "Contact"]:
                try:
                    describe = sf.__getattr__(obj_name).describe()
                    fields = {f["name"]: f["type"] for f in describe["fields"]}
                    current_schema[obj_name] = fields

                    last_fields = last_known.get(obj_name, {})
                    if last_fields:
                        for field_name, current_type in fields.items():
                            old_type = last_fields.get(field_name)
                            if old_type and old_type != current_type:
                                schema_changes_detected.append({
                                    "object": obj_name,
                                    "field": field_name,
                                    "old_type": old_type,
                                    "new_type": current_type,
                                })
                except Exception:
                    pass

            # Log schema changes
            if schema_changes_detected:
                try:
                    from admin_management.models import SchemaMigrationLog
                    for change in schema_changes_detected:
                        SchemaMigrationLog.objects.create(
                            entity_type=change["object"].lower(),
                            field_name=change["field"],
                            old_type=change["old_type"],
                            new_type=change["new_type"],
                            status="migrated",
                            migration_sql=f"Handled at application level - {change['field']} type changed from {change['old_type']} to {change['new_type']}",
                        )
                except Exception as e:
                    logger.warning(f"Failed to log schema change: {e}")

            # Save current schema as new baseline AFTER sync
            # (we do this after a successful sync below)
        except Exception as e:
            logger.warning(f"Schema detection during sync skipped: {e}")
            current_schema = {}

        # ── Step 1: Pull from SF and sync directly to app DB ──
        data = pull_all_data()

        # Direct sync: SF API data → app DB (no middle database)
        from sync.engine import run_sync_direct
        sync_log = run_sync_direct(data)

        # ── Step 2: Clear notification + update schema baseline ──
        notif = SyncNotification.get_instance()
        notif.out_of_sync = False
        notif.last_synced = timezone.now()
        notif.message = ""
        notif.save()

        # Save schema baseline so future checks compare against post-sync state
        if current_schema:
            try:
                schema_cache_file = settings.BASE_DIR / ".sf_schema_cache.json"
                with open(schema_cache_file, "w") as f:
                    json.dump(current_schema, f)
            except Exception:
                pass

        return Response({
            "status": "ok",
            "pulled": {"accounts": len(data["accounts"]), "contacts": len(data["contacts"])},
            "sync": {
                "id": sync_log.id,
                "status": sync_log.status,
                "changes_detected": sync_log.changes_detected,
            },
            "schema_changes": schema_changes_detected,
        })
    except Exception as exc:
        return Response({"status": "error", "detail": str(exc)}, status=500)
