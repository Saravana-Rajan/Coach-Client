"""Admin CRUD views for Coach management in the Salesforce simulated source."""
import logging
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from salesforce_sim.models import SFCoach, SFAccount, SFContact, SFAssignment
from .serializers import AdminCoachSerializer
from .models import BulkOperationLog

logger = logging.getLogger(__name__)


@api_view(["GET"])
def list_coaches(request):
    """List all coaches in the Salesforce source."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    coaches = SFCoach.objects.using("salesforce").all()
    serializer = AdminCoachSerializer(coaches, many=True)
    return Response(serializer.data)


@api_view(["POST"])
def create_coach(request):
    """Add a new coach to the Salesforce source."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    serializer = AdminCoachSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(using="salesforce")
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def get_coach(request, coach_id):
    """Get a single coach with details."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    try:
        coach = SFCoach.objects.using("salesforce").get(id=coach_id)
    except SFCoach.DoesNotExist:
        return Response({"error": "Coach not found"}, status=status.HTTP_404_NOT_FOUND)
    serializer = AdminCoachSerializer(coach)
    return Response(serializer.data)


@api_view(["PATCH"])
def update_coach(request, coach_id):
    """Update coach details in the Salesforce source."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    try:
        coach = SFCoach.objects.using("salesforce").get(id=coach_id)
    except SFCoach.DoesNotExist:
        return Response({"error": "Coach not found"}, status=status.HTTP_404_NOT_FOUND)
    serializer = AdminCoachSerializer(coach, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save(using="salesforce")
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
def delete_coach(request, coach_id):
    """Delete a coach from the Salesforce source. Handles cascading."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    try:
        coach = SFCoach.objects.using("salesforce").get(id=coach_id)
    except SFCoach.DoesNotExist:
        return Response({"error": "Coach not found"}, status=status.HTTP_404_NOT_FOUND)

    coach_name = coach.name
    affected_accounts = list(SFAccount.objects.using("salesforce").filter(coach=coach).values_list("name", flat=True))
    affected_contacts = list(SFContact.objects.using("salesforce").filter(coach=coach).values_list("name", flat=True))

    SFAccount.objects.using("salesforce").filter(coach=coach).update(coach=None)
    SFContact.objects.using("salesforce").filter(coach=coach).update(coach=None)
    SFAssignment.objects.using("salesforce").filter(coach=coach).delete()
    coach.delete(using="salesforce")

    BulkOperationLog.objects.create(
        operation_type="coach_remove",
        performed_by=request.user.username,
        details={
            "coach_name": coach_name,
            "affected_accounts": affected_accounts,
            "affected_contacts": affected_contacts,
        },
        affected_entities=[{"type": "coach", "name": coach_name}],
    )

    return Response({
        "message": f"Coach '{coach_name}' removed. {len(affected_accounts)} accounts and {len(affected_contacts)} contacts unassigned.",
    })


@api_view(["POST"])
def remove_coach_from_org(request):
    """Remove a coach from the organization and redistribute their clients.

    Deactivates the coach and optionally redistributes their accounts/contacts
    to other coaches via round-robin.
    """
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)

    coach_id = request.data.get("coach_id")
    redistribute_to = request.data.get("redistribute_to", [])

    if not coach_id:
        return Response({"error": "coach_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        coach = SFCoach.objects.using("salesforce").get(id=coach_id)
    except SFCoach.DoesNotExist:
        return Response({"error": "Coach not found"}, status=status.HTTP_404_NOT_FOUND)

    coach_name = coach.name
    accounts = list(SFAccount.objects.using("salesforce").filter(coach=coach))
    contacts = list(SFContact.objects.using("salesforce").filter(coach=coach))

    redistribution_log = []

    if redistribute_to:
        target_coaches = list(SFCoach.objects.using("salesforce").filter(id__in=redistribute_to, is_active=True))
        if not target_coaches:
            return Response({"error": "No valid target coaches found"}, status=status.HTTP_400_BAD_REQUEST)

        for i, account in enumerate(accounts):
            target = target_coaches[i % len(target_coaches)]
            account.coach = target
            account.save(using="salesforce")
            SFContact.objects.using("salesforce").filter(account=account).update(coach=target)
            SFAssignment.objects.using("salesforce").filter(account=account, coach_id=coach.id).update(coach=target)
            redistribution_log.append({
                "account": account.name,
                "from_coach": coach_name,
                "to_coach": target.name,
            })
    else:
        SFAccount.objects.using("salesforce").filter(coach=coach).update(coach=None)
        SFContact.objects.using("salesforce").filter(coach=coach).update(coach=None)
        SFAssignment.objects.using("salesforce").filter(coach=coach).delete()

    coach.is_active = False
    coach.active_clients = 0
    coach.save(using="salesforce")

    BulkOperationLog.objects.create(
        operation_type="coach_remove",
        performed_by=request.user.username,
        details={
            "coach_name": coach_name,
            "redistribution": redistribution_log,
            "accounts_affected": len(accounts),
            "contacts_affected": len(contacts),
        },
        affected_entities=[{"type": "coach", "name": coach_name}],
    )

    return Response({
        "message": f"Coach '{coach_name}' removed from organization",
        "accounts_redistributed": len(accounts),
        "contacts_redistributed": len(contacts),
        "redistribution": redistribution_log,
    })
