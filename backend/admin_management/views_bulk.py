"""Bulk admin operation views — coach swap, bulk reassign, etc."""
import logging
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from salesforce_sim.models import SFCoach, SFAccount, SFContact, SFAssignment
from .models import BulkOperationLog

logger = logging.getLogger(__name__)


@api_view(["POST"])
def swap_coaches(request):
    """Simultaneously swap accounts/contacts between multiple coaches.

    Request body:
    {
        "swaps": [
            {"coach_id": 1, "target_coach_id": 2},
            {"coach_id": 3, "target_coach_id": 4}
        ]
    }

    Each pair swaps ALL accounts and contacts between the two coaches simultaneously.
    """
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)

    swaps = request.data.get("swaps", [])
    if not swaps or len(swaps) < 1:
        return Response({"error": "At least one swap pair is required"}, status=status.HTTP_400_BAD_REQUEST)

    swap_log = []

    try:
        for swap in swaps:
            coach_a_id = swap.get("coach_id")
            coach_b_id = swap.get("target_coach_id")

            if not coach_a_id or not coach_b_id:
                return Response(
                    {"error": "Each swap must have coach_id and target_coach_id"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                coach_a = SFCoach.objects.using("salesforce").get(id=coach_a_id)
                coach_b = SFCoach.objects.using("salesforce").get(id=coach_b_id)
            except SFCoach.DoesNotExist:
                return Response(
                    {"error": f"Coach {coach_a_id} or {coach_b_id} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get current assignments for both coaches
            a_accounts = list(SFAccount.objects.using("salesforce").filter(coach=coach_a))
            b_accounts = list(SFAccount.objects.using("salesforce").filter(coach=coach_b))
            a_contacts = list(SFContact.objects.using("salesforce").filter(coach=coach_a))
            b_contacts = list(SFContact.objects.using("salesforce").filter(coach=coach_b))

            # Swap using temporary null to avoid constraint issues
            # Step 1: Set A's items to null coach
            for acc in a_accounts:
                acc.coach = None
                acc.save(using="salesforce")
            for con in a_contacts:
                con.coach = None
                con.save(using="salesforce")

            # Step 2: Set B's items to coach A
            for acc in b_accounts:
                acc.coach = coach_a
                acc.save(using="salesforce")
            for con in b_contacts:
                con.coach = coach_a
                con.save(using="salesforce")

            # Step 3: Set A's items (currently null) to coach B
            for acc in a_accounts:
                acc.coach = coach_b
                acc.save(using="salesforce")
            for con in a_contacts:
                con.coach = coach_b
                con.save(using="salesforce")

            # Step 4: Update assignments
            for acc in b_accounts:
                SFAssignment.objects.using("salesforce").filter(account=acc).update(coach=coach_a)
            for acc in a_accounts:
                SFAssignment.objects.using("salesforce").filter(account=acc).update(coach=coach_b)

            swap_log.append({
                "coach_a": coach_a.name,
                "coach_b": coach_b.name,
                "a_accounts_moved": [a.name for a in a_accounts],
                "b_accounts_moved": [a.name for a in b_accounts],
                "a_contacts_moved": len(a_contacts),
                "b_contacts_moved": len(b_contacts),
            })

        BulkOperationLog.objects.create(
            operation_type="coach_swap",
            performed_by=request.user.username,
            details={"swaps": swap_log},
            affected_entities=[{"type": "swap", "details": s} for s in swap_log],
        )

        return Response({
            "message": f"Successfully swapped {len(swaps)} coach pair(s)",
            "swaps": swap_log,
        })

    except Exception as e:
        logger.exception("Coach swap failed")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def bulk_reassign(request):
    """Bulk reassign multiple accounts or contacts to a target coach.

    Request body:
    {
        "entity_type": "account" | "contact",
        "entity_ids": [1, 2, 3],
        "target_coach_id": 5
    }
    """
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)

    entity_type = request.data.get("entity_type")
    entity_ids = request.data.get("entity_ids", [])
    target_coach_id = request.data.get("target_coach_id")

    if not entity_type or not entity_ids:
        return Response(
            {"error": "entity_type and entity_ids are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if entity_type not in ["account", "contact"]:
        return Response({"error": "entity_type must be 'account' or 'contact'"}, status=status.HTTP_400_BAD_REQUEST)

    target_coach = None
    if target_coach_id:
        try:
            target_coach = SFCoach.objects.using("salesforce").get(id=target_coach_id)
        except SFCoach.DoesNotExist:
            return Response({"error": "Target coach not found"}, status=status.HTTP_404_NOT_FOUND)

    reassigned = []

    if entity_type == "account":
        accounts = SFAccount.objects.using("salesforce").filter(id__in=entity_ids)
        for account in accounts:
            old_coach = account.coach.name if account.coach else "Unassigned"
            account.coach = target_coach
            account.save(using="salesforce")
            SFContact.objects.using("salesforce").filter(account=account).update(coach=target_coach)
            SFAssignment.objects.using("salesforce").filter(account=account).update(coach=target_coach)
            reassigned.append({"name": account.name, "from": old_coach})

    elif entity_type == "contact":
        contacts = SFContact.objects.using("salesforce").filter(id__in=entity_ids)
        for contact in contacts:
            old_coach = contact.coach.name if contact.coach else "Unassigned"
            contact.coach = target_coach
            contact.save(using="salesforce")
            SFAssignment.objects.using("salesforce").filter(contact=contact).update(coach=target_coach)
            reassigned.append({"name": contact.name, "from": old_coach})

    target_name = target_coach.name if target_coach else "Unassigned"

    BulkOperationLog.objects.create(
        operation_type="bulk_reassign",
        performed_by=request.user.username,
        details={
            "entity_type": entity_type,
            "target_coach": target_name,
            "reassigned": reassigned,
        },
        affected_entities=reassigned,
    )

    return Response({
        "message": f"Reassigned {len(reassigned)} {entity_type}(s) to {target_name}",
        "reassigned": reassigned,
    })


@api_view(["GET"])
def operation_history(request):
    """View history of bulk admin operations."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)

    from .serializers import BulkOperationLogSerializer

    logs = BulkOperationLog.objects.all()[:50]
    serializer = BulkOperationLogSerializer(logs, many=True)
    return Response(serializer.data)
