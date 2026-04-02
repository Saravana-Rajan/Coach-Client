from rest_framework import serializers
from .models import SFCoach, SFAccount, SFContact, SFAssignment


class SFCoachSerializer(serializers.ModelSerializer):
    class Meta:
        model = SFCoach
        fields = ["id", "sf_id", "name", "email", "active_clients", "is_active"]
        read_only_fields = ["sf_id"]


class SFContactSerializer(serializers.ModelSerializer):
    coach_name = serializers.CharField(source="coach.name", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = SFContact
        fields = [
            "id", "sf_id", "name", "title", "phone", "email",
            "account", "account_name", "coach", "coach_name",
        ]
        read_only_fields = ["sf_id"]


class SFAccountSerializer(serializers.ModelSerializer):
    coach_name = serializers.CharField(source="coach.name", read_only=True)
    contacts = SFContactSerializer(many=True, read_only=True)

    class Meta:
        model = SFAccount
        fields = [
            "id", "sf_id", "name", "industry", "website",
            "coaching_start_date", "coach", "coach_name", "contacts",
        ]
        read_only_fields = ["sf_id"]


class SFAssignmentSerializer(serializers.ModelSerializer):
    coach_name = serializers.CharField(source="coach.name", read_only=True)
    contact_name = serializers.CharField(source="contact.name", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = SFAssignment
        fields = [
            "id", "sf_id", "coach", "coach_name",
            "contact", "contact_name", "account", "account_name", "status",
        ]
        read_only_fields = ["sf_id"]
