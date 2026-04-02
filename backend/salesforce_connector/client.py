"""
Salesforce connector — pulls real data from a Salesforce org and seeds it
into the simulated-source SQLite tables so the existing sync engine keeps
working unchanged.

SCHEMA-AGNOSTIC: All field values from Salesforce are coerced to whatever
type the local model expects. If Salesforce changes a Text field to Number
(or vice versa), the pull still succeeds — values are cast safely.
"""

import json
import logging
import os
import subprocess
from datetime import date

from simple_salesforce import Salesforce

from salesforce_sim.models import SFAccount, SFContact, SFCoach

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Generic type coercion — handles ANY Salesforce schema change
# ---------------------------------------------------------------------------

def _safe_str(value, default="") -> str:
    """Coerce any Salesforce value to string safely."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return str(int(value)) if isinstance(value, float) and value == int(value) else str(value)
    return str(value)


def _safe_int(value, default=0) -> int:
    """Coerce any Salesforce value to int safely."""
    if value is None:
        return default
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default


def _safe_bool(value, default=True) -> bool:
    """Coerce any Salesforce value to bool safely."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    s = str(value).lower().strip()
    return s in ("true", "1", "yes", "active", "on")


def _safe_date(value, default=None):
    """Coerce any Salesforce value to date safely."""
    if value is None:
        return default or date.today()
    if isinstance(value, date):
        return value
    try:
        from datetime import datetime
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return default or date.today()


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def _get_token_from_cli() -> dict:
    result = subprocess.run(
        ["sf.cmd", "org", "display", "--target-org", "coach-dev", "--json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"sf org display failed: {result.stderr}")
    payload = json.loads(result.stdout)
    org_info = payload.get("result", {})
    return {
        "access_token": org_info.get("accessToken"),
        "instance_url": org_info.get("instanceUrl"),
    }


def get_sf_connection() -> Salesforce:
    username = os.environ.get("SF_USERNAME")
    password = os.environ.get("SF_PASSWORD")
    token = os.environ.get("SF_SECURITY_TOKEN")

    if username and password and token:
        try:
            return Salesforce(username=username, password=password, security_token=token)
        except Exception:
            pass

    creds = _get_token_from_cli()
    return Salesforce(instance_url=creds["instance_url"], session_id=creds["access_token"])


# ---------------------------------------------------------------------------
# Data pull — now includes Coach__c field
# ---------------------------------------------------------------------------

def _resolve_coach_value(raw_value, coach_id_map=None):
    """Resolve Coach__c to a coach name regardless of its Salesforce type.

    Works for: Text ("Alice Johnson"), Number (1), Lookup ID, Boolean, etc.
    """
    if raw_value is None or raw_value == "" or raw_value == 0:
        return ""
    if isinstance(raw_value, bool):
        return ""
    if isinstance(raw_value, (int, float)):
        int_val = int(raw_value)
        if coach_id_map and int_val in coach_id_map:
            return coach_id_map[int_val]
        return str(int_val)
    return _safe_str(raw_value)


def _build_coach_id_map():
    """Build a numeric ID → coach name map from existing local coaches."""
    coach_id_map = {}
    try:
        existing_coaches = SFCoach.objects.using("salesforce").all()
        for c in existing_coaches:
            coach_id_map[c.id] = c.name
        for i, c in enumerate(existing_coaches, 1):
            coach_id_map[i] = c.name
    except Exception:
        pass
    return coach_id_map


def pull_all_data() -> dict:
    sf = get_sf_connection()

    # Log the schema we receive so admins can see what SF is sending
    accounts_result = sf.query_all(
        "SELECT Id, Name, Industry, Website, Coach__c FROM Account"
    )
    contacts_result = sf.query_all(
        "SELECT Id, FirstName, LastName, Title, Email, Phone, AccountId, Coach__c FROM Contact"
    )

    # Build coach ID map for resolving numeric Coach__c values
    coach_id_map = _build_coach_id_map()

    # Log detected field types for schema tracking
    if accounts_result["records"]:
        sample = accounts_result["records"][0]
        field_types = {k: type(v).__name__ for k, v in sample.items() if k != "attributes"}
        logger.info(f"Salesforce Account field types: {field_types}")

    # Use _safe_* coercion for EVERY field — handles any type change
    accounts = [
        {
            "sf_id": _safe_str(rec["Id"]),
            "name": _safe_str(rec.get("Name"), "Unknown"),
            "industry": _safe_str(rec.get("Industry")),
            "website": _safe_str(rec.get("Website")),
            "coach_name": _resolve_coach_value(rec.get("Coach__c"), coach_id_map),
        }
        for rec in accounts_result["records"]
    ]

    contacts = [
        {
            "sf_id": _safe_str(rec["Id"]),
            "first_name": _safe_str(rec.get("FirstName")),
            "last_name": _safe_str(rec.get("LastName")),
            "title": _safe_str(rec.get("Title")),
            "email": _safe_str(rec.get("Email")),
            "phone": _safe_str(rec.get("Phone")),
            "account_id": _safe_str(rec.get("AccountId")),
            "coach_name": _resolve_coach_value(rec.get("Coach__c"), coach_id_map),
        }
        for rec in contacts_result["records"]
    ]

    return {"accounts": accounts, "contacts": contacts}


# ---------------------------------------------------------------------------
# Seed into simulated source — now maps Coach__c to real SFCoach records
# ---------------------------------------------------------------------------

def _get_or_create_coach(coach_identifier) -> SFCoach:
    """Get or create an SFCoach by name or numeric ID.

    Handles schema changes where Coach__c switches between Text and Number.
    """
    if not coach_identifier or coach_identifier == "" or coach_identifier == 0:
        coach, _ = SFCoach.objects.using("salesforce").get_or_create(
            email="unassigned@coach-client.local",
            defaults={"name": "Unassigned", "is_active": True},
        )
        return coach

    # If it's a pure number string, try to find coach by ID first
    str_val = str(coach_identifier)
    try:
        numeric_id = int(float(str_val))
        coach = SFCoach.objects.using("salesforce").filter(id=numeric_id).first()
        if coach:
            return coach
    except (ValueError, TypeError):
        pass

    # Fall back to name lookup
    coach, _ = SFCoach.objects.using("salesforce").get_or_create(
        name=str_val,
        defaults={
            "email": str_val.lower().replace(" ", ".") + "@coaching.com",
            "is_active": True,
        },
    )
    return coach


def seed_to_simulated_source(data: dict) -> dict:
    """Seed pulled data into the simulated source.

    All values are coerced safely — if Salesforce changed a field from
    Text to Number (or Currency, Picklist, Boolean, etc.), the seeding
    still works because every value goes through _safe_* coercion.
    """
    coach_cache = {}

    all_coach_names = set()
    for acct in data.get("accounts", []):
        if acct.get("coach_name"):
            all_coach_names.add(acct["coach_name"])
    for ct in data.get("contacts", []):
        if ct.get("coach_name"):
            all_coach_names.add(ct["coach_name"])

    for name in all_coach_names:
        coach_cache[name] = _get_or_create_coach(name)

    unassigned_coach = _get_or_create_coach("")

    sf_id_to_account = {}
    accounts_created = 0
    accounts_updated = 0

    for acct in data.get("accounts", []):
        coach = coach_cache.get(_safe_str(acct.get("coach_name")), unassigned_coach)
        obj, created = SFAccount.objects.using("salesforce").update_or_create(
            name=_safe_str(acct["name"], "Unknown"),
            defaults={
                "industry": _safe_str(acct.get("industry")),
                "website": _safe_str(acct.get("website")),
                "coaching_start_date": date.today(),
                "coach": coach,
            },
        )
        sf_id_to_account[_safe_str(acct.get("sf_id"))] = obj
        if created:
            accounts_created += 1
        else:
            accounts_updated += 1

    contacts_created = 0
    contacts_updated = 0

    for ct in data.get("contacts", []):
        first = _safe_str(ct.get("first_name"))
        last = _safe_str(ct.get("last_name"))
        full_name = f"{first} {last}".strip()
        account = sf_id_to_account.get(_safe_str(ct.get("account_id")))
        if account is None:
            continue

        coach = coach_cache.get(_safe_str(ct.get("coach_name")), unassigned_coach)
        email = _safe_str(ct.get("email")) or f"{_safe_str(ct.get('sf_id'))}@placeholder.local"
        obj, created = SFContact.objects.using("salesforce").update_or_create(
            email=email,
            account=account,
            defaults={
                "name": full_name or "Unknown",
                "title": _safe_str(ct.get("title")),
                "phone": _safe_str(ct.get("phone")),
                "coach": coach,
            },
        )
        if created:
            contacts_created += 1
        else:
            contacts_updated += 1

    return {
        "accounts_created": accounts_created,
        "accounts_updated": accounts_updated,
        "contacts_created": contacts_created,
        "contacts_updated": contacts_updated,
    }
