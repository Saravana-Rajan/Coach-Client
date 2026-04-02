from rest_framework import serializers
from .models import Coach, Account, Contact, Assignment


class ContactSerializer(serializers.ModelSerializer):
    coach_name = serializers.CharField(source="coach.name", read_only=True)

    class Meta:
        model = Contact
        fields = [
            "id", "sf_id", "name", "title", "phone", "email",
            "account_id", "coach_id", "coach_name",
        ]


class AccountSerializer(serializers.ModelSerializer):
    coach_name = serializers.CharField(source="coach.name", read_only=True)
    contacts = ContactSerializer(many=True, read_only=True)

    class Meta:
        model = Account
        fields = [
            "id", "sf_id", "name", "industry", "website",
            "coaching_start_date", "coach_id", "coach_name", "contacts",
        ]


class CoachSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coach
        fields = ["id", "sf_id", "name", "email", "active_clients", "is_active"]


class DashboardSerializer(serializers.Serializer):
    """Coach dashboard data."""
    coach = CoachSerializer()
    accounts = AccountSerializer(many=True)
    total_accounts = serializers.IntegerField()
    total_clients = serializers.IntegerField()
