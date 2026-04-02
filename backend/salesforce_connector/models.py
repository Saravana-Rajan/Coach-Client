from django.db import models


class SyncNotification(models.Model):
    """Tracks whether Salesforce has notified us of changes."""
    out_of_sync = models.BooleanField(default=False)
    last_notified = models.DateTimeField(null=True, blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    message = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        # Only one row ever exists
        pass

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
