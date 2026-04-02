from django.db import models


class SyncLog(models.Model):
    STATUS_CHOICES = [
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_progress")
    changes_detected = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Sync #{self.id} - {self.status} ({self.changes_detected} changes)"


class AuditRecord(models.Model):
    """Immutable audit record. Never update or delete."""

    CHANGE_TYPES = [
        ("coach_added", "Coach Added"),
        ("coach_removed", "Coach Removed"),
        ("coach_updated", "Coach Updated"),
        ("account_added", "Account Added"),
        ("account_removed", "Account Removed"),
        ("account_reassigned", "Account Reassigned"),
        ("account_updated", "Account Updated"),
        ("contact_added", "Contact Added"),
        ("contact_removed", "Contact Removed"),
        ("contact_reassigned", "Contact Reassigned"),
        ("contact_updated", "Contact Updated"),
        ("assignment_added", "Assignment Added"),
        ("assignment_removed", "Assignment Removed"),
        ("assignment_updated", "Assignment Updated"),
    ]

    sync = models.ForeignKey(SyncLog, on_delete=models.PROTECT, related_name="audit_records")
    change_type = models.CharField(max_length=30, choices=CHANGE_TYPES)
    entity_type = models.CharField(max_length=30)  # coach, account, contact, assignment
    entity_sf_id = models.UUIDField()
    entity_name = models.CharField(max_length=200)
    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)
    coach_name = models.CharField(max_length=200, blank=True)
    account_name = models.CharField(max_length=200, blank=True)
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-detected_at"]
        # Prevent deletion at the DB constraint level
        managed = True

    def __str__(self):
        return f"{self.change_type}: {self.entity_name}"
