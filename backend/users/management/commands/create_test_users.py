from django.core.management.base import BaseCommand
from users.models import CustomUser
from salesforce_sim.models import SFCoach


class Command(BaseCommand):
    help = "Create test user accounts for each coach + one admin"

    def handle(self, *args, **options):
        # Admin
        if not CustomUser.objects.filter(username="admin").exists():
            CustomUser.objects.create_superuser(
                username="admin", password="admin123",
                email="admin@coaching.com", role="admin"
            )
            self.stdout.write(self.style.SUCCESS("Created admin user"))

        # One user per coach
        for coach in SFCoach.objects.using("salesforce").all():
            username = coach.name.split()[0].lower()
            if not CustomUser.objects.filter(username=username).exists():
                CustomUser.objects.create_user(
                    username=username,
                    password=f"{username}123",
                    email=coach.email,
                    role="coach",
                    coach_sf_id=coach.sf_id,
                )
                self.stdout.write(self.style.SUCCESS(f"Created user: {username}"))
