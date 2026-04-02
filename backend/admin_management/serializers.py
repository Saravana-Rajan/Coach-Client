from rest_framework import serializers
from salesforce_sim.models import SFCoach, SFAccount, SFContact, SFAssignment
from .models import SchemaMigrationLog, BulkOperationLog


class AdminCoachSerializer(serializers.ModelSerializer):
    account_count = serializers.SerializerMethodField()
    contact_count = serializers.SerializerMethodField()

    class Meta:
        model = SFCoach
        fields = [
            "id", "sf_id", "name", "email", "active_clients",
            "is_active", "account_count", "contact_count",
        ]
        read_only_fields = ["sf_id"]

    def get_account_count(self, obj):
        return SFAccount.objects.using("salesforce").filter(coach=obj).count()

    def get_contact_count(self, obj):
        return SFContact.objects.using("salesforce").filter(coach=obj).count()


class AdminAccountSerializer(serializers.ModelSerializer):
    coach_name = serializers.CharField(source="coach.name", read_only=True, default="Unassigned")
    contact_count = serializers.SerializerMethodField()

    class Meta:
        model = SFAccount
        fields = [
            "id", "sf_id", "name", "industry", "website",
            "coaching_start_date", "coach", "coach_name", "contact_count",
        ]
        read_only_fields = ["sf_id"]

    def get_contact_count(self, obj):
        return SFContact.objects.using("salesforce").filter(account=obj).count()


class AdminContactSerializer(serializers.ModelSerializer):
    coach_name = serializers.CharField(source="coach.name", read_only=True, default="Unassigned")
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = SFContact
        fields = [
            "id", "sf_id", "name", "title", "phone", "email",
            "account", "account_name", "coach", "coach_name",
        ]
        read_only_fields = ["sf_id"]


class CoachSwapSerializer(serializers.Serializer):
    swaps = serializers.ListField(
        child=serializers.DictField(child=serializers.IntegerField()),
        min_length=1,
    )


class CoachRemoveSerializer(serializers.Serializer):
    coach_id = serializers.IntegerField()
    redistribute_to = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
    )


class ContactMoveSerializer(serializers.Serializer):
    contact_id = serializers.IntegerField()
    target_account_id = serializers.IntegerField()
    target_coach_id = serializers.IntegerField(required=False)


class BulkReassignSerializer(serializers.Serializer):
    entity_type = serializers.ChoiceField(choices=["account", "contact"])
    entity_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)
    target_coach_id = serializers.IntegerField()


class SchemaMigrationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchemaMigrationLog
        fields = "__all__"


class BulkOperationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkOperationLog
        fields = "__all__"
