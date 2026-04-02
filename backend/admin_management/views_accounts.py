"""Admin CRUD views for Account management in the Salesforce simulated source."""
import logging
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from salesforce_sim.models import SFCoach, SFAccount, SFContact, SFAssignment
from .serializers import AdminAccountSerializer
from .models import BulkOperationLog

logger = logging.getLogger(__name__)


@api_view(["GET"])
def list_accounts(request):
    """List all accounts in the Salesforce source."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    accounts = SFAccount.objects.using("salesforce").select_related("coach").all()
    serializer = AdminAccountSerializer(accounts, many=True)
    return Response(serializer.data)


@api_view(["POST"])
def create_account(request):
    """Add a new account to the Salesforce source."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    serializer = AdminAccountSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(using="salesforce")
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def get_account(request, account_id):
    """Get a single account with details."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    try:
        account = SFAccount.objects.using("salesforce").select_related("coach").get(id=account_id)
    except SFAccount.DoesNotExist:
        return Response({"error": "Account not found"}, status=status.HTTP_404_NOT_FOUND)
    serializer = AdminAccountSerializer(account)
    return Response(serializer.data)


@api_view(["PATCH"])
def update_account(request, account_id):
    """Update account details in the Salesforce source."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    try:
        account = SFAccount.objects.using("salesforce").select_related("coach").get(id=account_id)
    except SFAccount.DoesNotExist:
        return Response({"error": "Account not found"}, status=status.HTTP_404_NOT_FOUND)
    serializer = AdminAccountSerializer(account, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save(using="salesforce")
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
def delete_account(request, account_id):
    """Delete an account from the Salesforce source. Cascades to contacts and assignments."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    try:
        account = SFAccount.objects.using("salesforce").select_related("coach").get(id=account_id)
    except SFAccount.DoesNotExist:
        return Response({"error": "Account not found"}, status=status.HTTP_404_NOT_FOUND)

    account_name = account.name
    coach_name = account.coach.name if account.coach else "Unassigned"
    affected_contacts = list(SFContact.objects.using("salesforce").filter(account=account).values_list("name", flat=True))

    SFAssignment.objects.using("salesforce").filter(account=account).delete()
    SFContact.objects.using("salesforce").filter(account=account).delete()
    account.delete(using="salesforce")

    BulkOperationLog.objects.create(
        operation_type="account_remove",
        performed_by=request.user.username,
        details={
            "account_name": account_name,
            "coach_name": coach_name,
            "contacts_removed": affected_contacts,
        },
        affected_entities=[{"type": "account", "name": account_name}],
    )

    return Response({
        "message": f"Account '{account_name}' removed with {len(affected_contacts)} contacts",
        "contacts_removed": affected_contacts,
    })


@api_view(["POST"])
def reassign_account(request, account_id):
    """Reassign an account to a different coach."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)

    target_coach_id = request.data.get("coach_id")
    if target_coach_id is None:
        return Response({"error": "coach_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        account = SFAccount.objects.using("salesforce").select_related("coach").get(id=account_id)
    except SFAccount.DoesNotExist:
        return Response({"error": "Account not found"}, status=status.HTTP_404_NOT_FOUND)

    old_coach_name = account.coach.name if account.coach else "Unassigned"

    if target_coach_id:
        try:
            new_coach = SFCoach.objects.using("salesforce").get(id=target_coach_id)
        except SFCoach.DoesNotExist:
            return Response({"error": "Target coach not found"}, status=status.HTTP_404_NOT_FOUND)
        account.coach = new_coach
        SFContact.objects.using("salesforce").filter(account=account).update(coach=new_coach)
        SFAssignment.objects.using("salesforce").filter(account=account).update(coach=new_coach)
        new_coach_name = new_coach.name
    else:
        account.coach = None
        SFContact.objects.using("salesforce").filter(account=account).update(coach=None)
        SFAssignment.objects.using("salesforce").filter(account=account).delete()
        new_coach_name = "Unassigned"

    account.save(using="salesforce")

    return Response({
        "message": f"Account '{account.name}' reassigned from {old_coach_name} to {new_coach_name}",
        "account": AdminAccountSerializer(account).data,
    })
