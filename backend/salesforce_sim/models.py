import uuid
from django.db import models


class SFCoach(models.Model):
    sf_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    active_clients = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "salesforce_sim"
        db_table = "sf_coach"

    def __str__(self):
        return self.name


class SFAccount(models.Model):
    sf_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=200)
    industry = models.CharField(max_length=100)
    website = models.URLField(blank=True)
    coaching_start_date = models.DateField()
    assigned_coach = models.CharField(max_length=200, blank=True, default="")
    coach = models.ForeignKey(
        SFCoach, on_delete=models.SET_NULL, null=True, related_name="accounts"
    )

    class Meta:
        app_label = "salesforce_sim"
        db_table = "sf_account"

    def __str__(self):
        return self.name


class SFContact(models.Model):
    sf_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField()
    assigned_coach = models.CharField(max_length=200, blank=True, default="")
    account = models.ForeignKey(
        SFAccount, on_delete=models.CASCADE, related_name="contacts"
    )
    coach = models.ForeignKey(
        SFCoach, on_delete=models.SET_NULL, null=True, related_name="contacts"
    )

    class Meta:
        app_label = "salesforce_sim"
        db_table = "sf_contact"

    def __str__(self):
        return self.name


class SFAssignment(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    sf_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    coach = models.ForeignKey(
        SFCoach, on_delete=models.CASCADE, related_name="assignments"
    )
    contact = models.ForeignKey(
        SFContact, on_delete=models.CASCADE, related_name="assignments"
    )
    account = models.ForeignKey(
        SFAccount, on_delete=models.CASCADE, related_name="assignments"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    class Meta:
        app_label = "salesforce_sim"
        db_table = "sf_assignment"
        unique_together = ["coach", "contact"]

    def __str__(self):
        return f"{self.coach.name} -> {self.contact.name} ({self.status})"
