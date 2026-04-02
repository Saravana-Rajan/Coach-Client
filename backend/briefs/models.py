from django.db import models
from sync.models import SyncLog, AuditRecord
from coaching.models import Coach


class TransitionBrief(models.Model):
    sync = models.ForeignKey(SyncLog, on_delete=models.PROTECT, related_name="briefs")
    audit_record = models.ForeignKey(
        AuditRecord, on_delete=models.PROTECT, null=True, related_name="briefs"
    )
    coach = models.ForeignKey(
        Coach, on_delete=models.SET_NULL, null=True, related_name="briefs"
    )
    contact_name = models.CharField(max_length=200)
    account_name = models.CharField(max_length=200)
    previous_coach_name = models.CharField(max_length=200)
    content = models.TextField()
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"Brief: {self.contact_name} → {self.coach.name if self.coach else 'Unknown'}"
