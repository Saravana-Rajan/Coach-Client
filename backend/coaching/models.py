import uuid
from django.db import models


class Coach(models.Model):
    sf_id = models.UUIDField(unique=True)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    active_clients = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Account(models.Model):
    sf_id = models.UUIDField(unique=True)
    name = models.CharField(max_length=200)
    industry = models.CharField(max_length=100)
    website = models.URLField(blank=True)
    coaching_start_date = models.DateField()
    assigned_coach = models.CharField(max_length=200, blank=True, default="")
    coach = models.ForeignKey(
        Coach, on_delete=models.SET_NULL, null=True, related_name="accounts"
    )

    def __str__(self):
        return self.name


class Contact(models.Model):
    sf_id = models.UUIDField(unique=True)
    name = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField()
    assigned_coach = models.CharField(max_length=200, blank=True, default="")
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="contacts"
    )
    coach = models.ForeignKey(
        Coach, on_delete=models.SET_NULL, null=True, related_name="contacts"
    )

    def __str__(self):
        return self.name


class Assignment(models.Model):
    sf_id = models.UUIDField(unique=True)
    coach = models.ForeignKey(
        Coach, on_delete=models.CASCADE, related_name="assignments"
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="assignments"
    )
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="assignments"
    )
    status = models.CharField(max_length=20, default="active")

    class Meta:
        unique_together = ["coach", "contact"]

    def __str__(self):
        return f"{self.coach.name} -> {self.contact.name}"
