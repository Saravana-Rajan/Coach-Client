from rest_framework import serializers
from .models import TransitionBrief


class TransitionBriefSerializer(serializers.ModelSerializer):
    coach_name = serializers.CharField(source="coach.name", read_only=True, default="Unknown")

    class Meta:
        model = TransitionBrief
        fields = [
            "id", "sync_id", "coach_id", "coach_name",
            "contact_name", "account_name", "previous_coach_name",
            "content", "generated_at",
        ]
