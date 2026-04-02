from rest_framework import serializers
from .models import SyncLog, AuditRecord


class AuditRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditRecord
        fields = [
            "id", "sync_id", "change_type", "entity_type", "entity_sf_id",
            "entity_name", "before_state", "after_state",
            "coach_name", "account_name", "detected_at",
        ]


class SyncLogSerializer(serializers.ModelSerializer):
    audit_records = AuditRecordSerializer(many=True, read_only=True)

    class Meta:
        model = SyncLog
        fields = [
            "id", "started_at", "completed_at", "status",
            "changes_detected", "error_message", "audit_records",
        ]


class SyncLogListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views (no nested audit records)."""

    class Meta:
        model = SyncLog
        fields = [
            "id", "started_at", "completed_at", "status",
            "changes_detected", "error_message",
        ]
