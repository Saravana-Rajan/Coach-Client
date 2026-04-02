from django.db import models


class SchemaMigrationLog(models.Model):
    """Tracks schema changes detected from Salesforce and auto-migrations applied."""
    STATUS_CHOICES = [
        ("detected", "Detected"),
        ("migrated", "Migrated"),
        ("rolled_back", "Rolled Back"),
        ("failed", "Failed"),
    ]

    detected_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    entity_type = models.CharField(max_length=50)
    field_name = models.CharField(max_length=100)
    old_type = models.CharField(max_length=100)
    new_type = models.CharField(max_length=100)
    old_constraints = models.JSONField(default=dict, blank=True)
    new_constraints = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="detected")
    migration_sql = models.TextField(blank=True)
    rollback_sql = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-detected_at"]

    def __str__(self):
        return f"{self.entity_type}.{self.field_name}: {self.old_type} -> {self.new_type} ({self.status})"


class BulkOperationLog(models.Model):
    """Logs bulk admin operations for audit purposes."""
    OPERATION_TYPES = [
        ("coach_swap", "Coach Swap"),
        ("coach_remove", "Coach Removal"),
        ("account_remove", "Account Removal"),
        ("contact_remove", "Contact Removal"),
        ("contact_move", "Contact Move"),
        ("bulk_reassign", "Bulk Reassignment"),
    ]

    operation_type = models.CharField(max_length=30, choices=OPERATION_TYPES)
    performed_by = models.CharField(max_length=200)
    performed_at = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict)
    affected_entities = models.JSONField(default=list)
    status = models.CharField(max_length=20, default="completed")
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-performed_at"]

    def __str__(self):
        return f"{self.operation_type} by {self.performed_by} at {self.performed_at}"
