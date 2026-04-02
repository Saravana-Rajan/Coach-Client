"""Admin CRUD views for Contact management in the Salesforce simulated source."""
import logging
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from salesforce_sim.models import SFCoach, SFAccount, SFContact, SFAssignment
from .serializers import AdminContactSerializer
from .models import BulkOperationLog

logger = logging.getLogger(__name__)


@api_view(["GET"])
def list_contacts(request):
    """List all contacts in the Salesforce source."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    contacts = SFContact.objects.using("salesforce").select_related("coach", "account").all()
    serializer = AdminContactSerializer(contacts, many=True)
    return Response(serializer.data)


@api_view(["POST"])
def create_contact(request):
    """Add a new contact to the Salesforce source."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    serializer = AdminContactSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(using="salesforce")
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def get_contact(request, contact_id):
    """Get a single contact with details."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    try:
        contact = SFContact.objects.using("salesforce").select_related("coach", "account").get(id=contact_id)
    except SFContact.DoesNotExist:
        return Response({"error": "Contact not found"}, status=status.HTTP_404_NOT_FOUND)
    serializer = AdminContactSerializer(contact)
    return Response(serializer.data)


@api_view(["PATCH"])
def update_contact(request, contact_id):
    """Update contact details in the Salesforce source."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    try:
        contact = SFContact.objects.using("salesforce").select_related("coach", "account").get(id=contact_id)
    except SFContact.DoesNotExist:
        return Response({"error": "Contact not found"}, status=status.HTTP_404_NOT_FOUND)
    serializer = AdminContactSerializer(contact, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save(using="salesforce")
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
def delete_contact(request, contact_id):
    """Delete a contact from the Salesforce source."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    try:
        contact = SFContact.objects.using("salesforce").select_related("coach", "account").get(id=contact_id)
    except SFContact.DoesNotExist:
        return Response({"error": "Contact not found"}, status=status.HTTP_404_NOT_FOUND)

    contact_name = contact.name
    account_name = contact.account.name if contact.account else "Unknown"
    coach_name = contact.coach.name if contact.coach else "Unassigned"

    SFAssignment.objects.using("salesforce").filter(contact=contact).delete()
    contact.delete(using="salesforce")

    BulkOperationLog.objects.create(
        operation_type="contact_remove",
        performed_by=request.user.username,
        details={
            "contact_name": contact_name,
            "account_name": account_name,
            "coach_name": coach_name,
        },
        affected_entities=[{"type": "contact", "name": contact_name}],
    )

    return Response({"message": f"Contact '{contact_name}' removed from account '{account_name}'"})


@api_view(["POST"])
def move_contact(request, contact_id):
    """Move a contact to a different account, optionally reassigning coach."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)

    target_account_id = request.data.get("target_account_id")
    target_coach_id = request.data.get("target_coach_id")

    if not target_account_id:
        return Response({"error": "target_account_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        contact = SFContact.objects.using("salesforce").select_related("coach", "account").get(id=contact_id)
    except SFContact.DoesNotExist:
        return Response({"error": "Contact not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        target_account = SFAccount.objects.using("salesforce").select_related("coach").get(id=target_account_id)
    except SFAccount.DoesNotExist:
        return Response({"error": "Target account not found"}, status=status.HTTP_404_NOT_FOUND)

    old_account_name = contact.account.name if contact.account else "Unknown"
    old_coach_name = contact.coach.name if contact.coach else "Unassigned"

    contact.account = target_account

    if target_coach_id:
        try:
            new_coach = SFCoach.objects.using("salesforce").get(id=target_coach_id)
            contact.coach = new_coach
        except SFCoach.DoesNotExist:
            return Response({"error": "Target coach not found"}, status=status.HTTP_404_NOT_FOUND)
    elif target_account.coach:
        contact.coach = target_account.coach

    contact.save(using="salesforce")

    SFAssignment.objects.using("salesforce").filter(contact=contact).update(
        account=target_account,
        coach=contact.coach,
    )

    new_coach_name = contact.coach.name if contact.coach else "Unassigned"

    BulkOperationLog.objects.create(
        operation_type="contact_move",
        performed_by=request.user.username,
        details={
            "contact_name": contact.name,
            "from_account": old_account_name,
            "to_account": target_account.name,
            "from_coach": old_coach_name,
            "to_coach": new_coach_name,
        },
        affected_entities=[{"type": "contact", "name": contact.name}],
    )

    return Response({
        "message": f"Contact '{contact.name}' moved from '{old_account_name}' to '{target_account.name}'",
        "contact": AdminContactSerializer(contact).data,
    })


@api_view(["POST"])
def reassign_contact(request, contact_id):
    """Reassign a contact to a different coach."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)

    target_coach_id = request.data.get("coach_id")

    try:
        contact = SFContact.objects.using("salesforce").select_related("coach", "account").get(id=contact_id)
    except SFContact.DoesNotExist:
        return Response({"error": "Contact not found"}, status=status.HTTP_404_NOT_FOUND)

    old_coach_name = contact.coach.name if contact.coach else "Unassigned"

    if target_coach_id:
        try:
            new_coach = SFCoach.objects.using("salesforce").get(id=target_coach_id)
        except SFCoach.DoesNotExist:
            return Response({"error": "Target coach not found"}, status=status.HTTP_404_NOT_FOUND)
        contact.coach = new_coach
        SFAssignment.objects.using("salesforce").filter(contact=contact).update(coach=new_coach)
        new_coach_name = new_coach.name
    else:
        contact.coach = None
        SFAssignment.objects.using("salesforce").filter(contact=contact).delete()
        new_coach_name = "Unassigned"

    contact.save(using="salesforce")

    return Response({
        "message": f"Contact '{contact.name}' reassigned from {old_coach_name} to {new_coach_name}",
        "contact": AdminContactSerializer(contact).data,
    })
