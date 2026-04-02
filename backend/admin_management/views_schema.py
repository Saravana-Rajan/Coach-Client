"""Schema change detection and auto-migration views.

Compares the Salesforce source DB schema against the local app DB schema.
When Salesforce schema changes (e.g., text -> number), detects it and
auto-migrates the local DB to match, with rollback capability.
"""
import logging
from django.db import connections
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import SchemaMigrationLog
from .serializers import SchemaMigrationLogSerializer

logger = logging.getLogger(__name__)

# Mapping of Salesforce source tables to local app tables
SF_TO_LOCAL_TABLE_MAP = {
    "sf_coach": "coaching_coach",
    "sf_account": "coaching_account",
    "sf_contact": "coaching_contact",
    "sf_assignment": "coaching_assignment",
}

# Entity type names for display
TABLE_TO_ENTITY = {
    "sf_coach": "coach",
    "sf_account": "account",
    "sf_contact": "contact",
    "sf_assignment": "assignment",
}

# Fields to skip during comparison (auto-managed by Django)
SKIP_FIELDS = {"id", "sf_id", "coach_id", "account_id", "contact_id"}


def _sf_type_to_sqlite(sf_type):
    """Map Salesforce field types to SQLite column types."""
    sf_type = sf_type.upper()
    mapping = {
        "STRING": "VARCHAR(200)",
        "TEXTAREA": "VARCHAR(200)",
        "DOUBLE": "REAL",
        "INT": "INTEGER",
        "INTEGER": "INTEGER",
        "CURRENCY": "REAL",
        "PERCENT": "REAL",
        "BOOLEAN": "BOOL",
        "DATE": "DATE",
        "DATETIME": "DATETIME",
        "EMAIL": "VARCHAR(254)",
        "PHONE": "VARCHAR(30)",
        "URL": "VARCHAR(200)",
        "PICKLIST": "VARCHAR(200)",
        "MULTIPICKLIST": "TEXT",
        "ID": "VARCHAR(18)",
        "REFERENCE": "VARCHAR(18)",
    }
    return mapping.get(sf_type, sf_type)


def _get_table_schema(db_alias, table_name):
    """Get column info from SQLite PRAGMA for a given table."""
    with connections[db_alias].cursor() as cursor:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
    return {
        col[1]: {
            "type": col[2].upper(),
            "notnull": bool(col[3]),
            "default": col[4],
            "pk": bool(col[5]),
        }
        for col in columns
    }


def _detect_schema_differences():
    """Compare Salesforce and local DB schemas, return list of differences."""
    differences = []

    for sf_table, local_table in SF_TO_LOCAL_TABLE_MAP.items():
        entity_type = TABLE_TO_ENTITY[sf_table]

        try:
            sf_schema = _get_table_schema("salesforce", sf_table)
            local_schema = _get_table_schema("default", local_table)
        except Exception as e:
            logger.warning(f"Could not read schema for {sf_table}/{local_table}: {e}")
            continue

        for field_name, sf_info in sf_schema.items():
            if field_name in SKIP_FIELDS:
                continue

            if field_name not in local_schema:
                differences.append({
                    "entity_type": entity_type,
                    "field_name": field_name,
                    "change": "field_added",
                    "old_type": None,
                    "new_type": sf_info["type"],
                    "old_constraints": {},
                    "new_constraints": {
                        "notnull": sf_info["notnull"],
                        "default": sf_info["default"],
                    },
                })
            else:
                local_info = local_schema[field_name]

                if sf_info["type"] != local_info["type"]:
                    differences.append({
                        "entity_type": entity_type,
                        "field_name": field_name,
                        "change": "type_changed",
                        "old_type": local_info["type"],
                        "new_type": sf_info["type"],
                        "old_constraints": {
                            "notnull": local_info["notnull"],
                            "default": local_info["default"],
                        },
                        "new_constraints": {
                            "notnull": sf_info["notnull"],
                            "default": sf_info["default"],
                        },
                    })

                elif sf_info["notnull"] != local_info["notnull"]:
                    differences.append({
                        "entity_type": entity_type,
                        "field_name": field_name,
                        "change": "constraint_changed",
                        "old_type": local_info["type"],
                        "new_type": sf_info["type"],
                        "old_constraints": {
                            "notnull": local_info["notnull"],
                            "default": local_info["default"],
                        },
                        "new_constraints": {
                            "notnull": sf_info["notnull"],
                            "default": sf_info["default"],
                        },
                    })

        for field_name in local_schema:
            if field_name in SKIP_FIELDS:
                continue
            if field_name not in sf_schema:
                differences.append({
                    "entity_type": entity_type,
                    "field_name": field_name,
                    "change": "field_removed",
                    "old_type": local_schema[field_name]["type"],
                    "new_type": None,
                    "old_constraints": {
                        "notnull": local_schema[field_name]["notnull"],
                        "default": local_schema[field_name]["default"],
                    },
                    "new_constraints": {},
                })

    return differences


def _generate_migration_sql(diff, local_table):
    """Generate ALTER TABLE SQL for a schema difference."""
    field = diff["field_name"]

    if diff["change"] == "type_changed":
        new_type = diff["new_type"]
        old_type = diff["old_type"]
        # Pick a sensible default for the new type
        if new_type in ("REAL", "INTEGER", "INT"):
            new_default = "0"
        else:
            new_default = "''"
        if old_type in ("REAL", "INTEGER", "INT"):
            old_default = "0"
        else:
            old_default = "''"

        migration_sql = (
            f"ALTER TABLE {local_table} ADD COLUMN {field}_new {new_type} DEFAULT {new_default};\n"
            f"UPDATE {local_table} SET {field}_new = CAST({field} AS {new_type});\n"
            f"ALTER TABLE {local_table} DROP COLUMN {field};\n"
            f"ALTER TABLE {local_table} RENAME COLUMN {field}_new TO {field}"
        )
        rollback_sql = (
            f"ALTER TABLE {local_table} ADD COLUMN {field}_new {old_type} DEFAULT {old_default};\n"
            f"UPDATE {local_table} SET {field}_new = CAST({field} AS {old_type});\n"
            f"ALTER TABLE {local_table} DROP COLUMN {field};\n"
            f"ALTER TABLE {local_table} RENAME COLUMN {field}_new TO {field}"
        )
        return migration_sql.strip(), rollback_sql.strip()

    elif diff["change"] == "field_added":
        new_type = diff["new_type"]
        notnull = diff["new_constraints"].get("notnull", False)
        default = diff["new_constraints"].get("default", "''")
        if default is None:
            default = "''"

        constraint = f"NOT NULL DEFAULT {default}" if notnull else f"DEFAULT {default}"
        migration_sql = f"ALTER TABLE {local_table} ADD COLUMN {field} {new_type} {constraint}"
        rollback_sql = f"-- SQLite does not support DROP COLUMN easily. Manual intervention needed for: {local_table}.{field}"
        return migration_sql, rollback_sql

    elif diff["change"] == "field_removed":
        migration_sql = f"-- Field {field} removed in source. Consider dropping: ALTER TABLE {local_table} DROP COLUMN {field}"
        rollback_sql = f"ALTER TABLE {local_table} ADD COLUMN {field} {diff['old_type']}"
        return migration_sql, rollback_sql

    return "", ""


@api_view(["GET"])
def schema_status(request):
    """Get current schema comparison between Salesforce and local DB."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)

    differences = _detect_schema_differences()
    pending = SchemaMigrationLog.objects.filter(status="detected").count()

    return Response({
        "in_sync": len(differences) == 0,
        "differences": differences,
        "pending_migrations": pending,
    })


@api_view(["POST"])
def detect_changes(request):
    """Detect schema changes and create migration log entries. Auto-apply if requested.

    Checks TWO sources:
    1. Local DB comparison (sf_* tables vs coaching_* tables)
    2. Salesforce describe() API — compares SF field types against local DB columns
    """
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)

    auto_apply = request.data.get("auto_apply", True)
    differences = _detect_schema_differences()

    # Also check Salesforce describe() for type mismatches
    try:
        from salesforce_connector.client import get_sf_connection
        sf = get_sf_connection()

        # Map SF field names to local column names and tables
        # Each entry: SF_field -> list of (local_column, local_table, entity_type)
        sf_field_to_local = {
            "Coach__c": [
                ("assigned_coach", "coaching_account", "account"),
                ("assigned_coach", "coaching_contact", "contact"),
            ],
        }

        for obj_name in ["Account", "Contact"]:
            try:
                describe = sf.__getattr__(obj_name).describe()
                sf_fields = {f["name"]: f for f in describe["fields"]}

                for sf_field_name, mappings in sf_field_to_local.items():
                    if sf_field_name in sf_fields:
                        sf_type = sf_fields[sf_field_name]["type"].upper()
                        sf_sqlite_type = _sf_type_to_sqlite(sf_type)

                        for local_col, local_table, entity_type in mappings:
                            local_schema = _get_table_schema("default", local_table)
                            if local_col in local_schema:
                                local_type = local_schema[local_col]["type"]
                                if sf_sqlite_type != local_type:
                                    differences.append({
                                        "entity_type": entity_type,
                                        "field_name": local_col,
                                        "change": "type_changed",
                                        "old_type": local_type,
                                        "new_type": sf_sqlite_type,
                                        "old_constraints": {
                                            "notnull": local_schema[local_col]["notnull"],
                                            "default": local_schema[local_col]["default"],
                                        },
                                        "new_constraints": {"notnull": False, "default": "''"},
                                    })
            except Exception as e:
                logger.warning(f"SF describe check failed for {obj_name}: {e}")
    except Exception as e:
        logger.warning(f"SF connection failed during detect: {e}")

    if not differences:
        return Response({"message": "No schema changes detected", "changes": []})

    # Deduplicate — skip if same field+change already exists as detected/migrated
    unique_diffs = []
    for diff in differences:
        existing = SchemaMigrationLog.objects.filter(
            entity_type=diff["entity_type"],
            field_name=diff["field_name"],
            old_type=diff.get("old_type") or "",
            new_type=diff.get("new_type") or "",
        ).exists()
        if not existing:
            unique_diffs.append(diff)
    differences = unique_diffs

    if not differences:
        return Response({"message": "No new schema changes detected", "changes": []})

    created_logs = []
    for diff in differences:
        entity_type = diff["entity_type"]
        sf_table = [k for k, v in TABLE_TO_ENTITY.items() if v == entity_type][0]
        local_table = SF_TO_LOCAL_TABLE_MAP[sf_table]

        migration_sql, rollback_sql = _generate_migration_sql(diff, local_table)

        log = SchemaMigrationLog.objects.create(
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
        created_logs.append(log)

    applied = []
    if auto_apply:
        for log in created_logs:
            if log.migration_sql and not log.migration_sql.startswith("--"):
                try:
                    with connections["default"].cursor() as cursor:
                        for stmt in log.migration_sql.split(";"):
                            stmt = stmt.strip()
                            if stmt and not stmt.startswith("--"):
                                cursor.execute(stmt)
                    log.status = "migrated"
                    log.applied_at = timezone.now()
                    log.save()
                    applied.append(log.id)
                except Exception as e:
                    log.status = "failed"
                    log.error_message = str(e)
                    log.save()
                    logger.error(f"Auto-migration failed for {log}: {e}")

    serializer = SchemaMigrationLogSerializer(created_logs, many=True)
    return Response({
        "message": f"Detected {len(differences)} schema change(s)",
        "auto_applied": len(applied),
        "changes": serializer.data,
    })


@api_view(["GET"])
def migration_history(request):
    """View schema migration history."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)

    logs = SchemaMigrationLog.objects.all()[:100]
    serializer = SchemaMigrationLogSerializer(logs, many=True)
    return Response(serializer.data)


@api_view(["POST"])
def apply_migration(request, migration_id):
    """Manually apply a detected schema migration."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)

    try:
        log = SchemaMigrationLog.objects.get(id=migration_id)
    except SchemaMigrationLog.DoesNotExist:
        return Response({"error": "Migration not found"}, status=status.HTTP_404_NOT_FOUND)

    if log.status != "detected":
        return Response({"error": f"Migration already {log.status}"}, status=status.HTTP_400_BAD_REQUEST)

    # If SQL is just a comment or empty, mark as migrated (informational entry)
    if not log.migration_sql or log.migration_sql.startswith("--"):
        log.status = "migrated"
        log.applied_at = timezone.now()
        if not log.migration_sql:
            log.migration_sql = "No DB migration needed — handled at application level."
        log.save()
        return Response({"message": "Marked as migrated (no DB change needed)", "migration": SchemaMigrationLogSerializer(log).data})

    try:
        with connections["default"].cursor() as cursor:
            for stmt in log.migration_sql.split(";"):
                stmt = stmt.strip()
                if stmt and not stmt.startswith("--"):
                    cursor.execute(stmt)
        log.status = "migrated"
        log.applied_at = timezone.now()
        log.save()
        return Response({"message": "Migration applied successfully", "migration": SchemaMigrationLogSerializer(log).data})
    except Exception as e:
        log.status = "failed"
        log.error_message = str(e)
        log.save()
        return Response({"error": f"Migration failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def rollback_migration(request, migration_id):
    """Rollback a previously applied migration."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)

    try:
        log = SchemaMigrationLog.objects.get(id=migration_id)
    except SchemaMigrationLog.DoesNotExist:
        return Response({"error": "Migration not found"}, status=status.HTTP_404_NOT_FOUND)

    if log.status != "migrated":
        return Response(
            {"error": f"Can only rollback migrated entries, current status: {log.status}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not log.rollback_sql or log.rollback_sql.startswith("--"):
        return Response({"error": "No executable rollback SQL available"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with connections["default"].cursor() as cursor:
            for stmt in log.rollback_sql.split(";"):
                stmt = stmt.strip()
                if stmt and not stmt.startswith("--"):
                    cursor.execute(stmt)
        log.status = "rolled_back"
        log.save()
        return Response({"message": "Rollback successful", "migration": SchemaMigrationLogSerializer(log).data})
    except Exception as e:
        log.status = "failed"
        log.error_message = f"Rollback failed: {e}"
        log.save()
        return Response({"error": f"Rollback failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
