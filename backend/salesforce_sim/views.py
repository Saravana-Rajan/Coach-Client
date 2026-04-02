from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import SFCoach, SFAccount, SFContact, SFAssignment
from .serializers import (
    SFCoachSerializer, SFAccountSerializer,
    SFContactSerializer, SFAssignmentSerializer,
)


class SFCoachViewSet(viewsets.ModelViewSet):
    queryset = SFCoach.objects.using("salesforce").all()
    serializer_class = SFCoachSerializer


class SFAccountViewSet(viewsets.ModelViewSet):
    queryset = SFAccount.objects.using("salesforce").prefetch_related("contacts").all()
    serializer_class = SFAccountSerializer


class SFContactViewSet(viewsets.ModelViewSet):
    queryset = SFContact.objects.using("salesforce").select_related("coach", "account").all()
    serializer_class = SFContactSerializer


class SFAssignmentViewSet(viewsets.ModelViewSet):
    queryset = SFAssignment.objects.using("salesforce").select_related(
        "coach", "contact", "account"
    ).all()
    serializer_class = SFAssignmentSerializer


@api_view(["POST"])
def notify_change(request):
    """Endpoint that only says 'something changed'. No details about what."""
    # In a real system this would trigger an async sync.
    # For now, just return acknowledgement — the admin triggers sync separately.
    return Response({"message": "Change detected. Sync recommended."})
