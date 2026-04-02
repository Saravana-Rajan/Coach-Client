from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ("coach", "Coach"),
        ("admin", "Admin"),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="coach")
    # Links to the coaching.Coach model after sync creates it.
    # Null for admins or before first sync.
    coach_sf_id = models.UUIDField(null=True, blank=True)

    def is_admin(self):
        return self.role == "admin"

    def is_coach(self):
        return self.role == "coach"
