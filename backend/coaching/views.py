from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Coach, Account, Contact
from .serializers import (
    AccountSerializer, ContactSerializer, CoachSerializer, DashboardSerializer,
)
from .permissions import get_coach_for_user


@api_view(["GET"])
def dashboard(request):
    """Coach sees their data. Admin sees all or a specific coach's data."""
    user = request.user

    if user.is_admin():
        coach_id = request.query_params.get("coach_id")
        if coach_id:
            coach = Coach.objects.filter(id=coach_id).first()
            if not coach:
                return Response({"error": "Coach not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Admin overview: all coaches with their accounts
            coaches = Coach.objects.filter(is_active=True)
            data = []
            for c in coaches:
                accounts = Account.objects.filter(coach=c).prefetch_related("contacts")
                data.append({
                    "coach": CoachSerializer(c).data,
                    "accounts": AccountSerializer(accounts, many=True).data,
                    "total_accounts": accounts.count(),
                    "total_clients": Contact.objects.filter(coach=c).count(),
                })
            return Response(data)
    else:
        coach = get_coach_for_user(user)
        if not coach:
            return Response({"error": "No coach profile linked"}, status=status.HTTP_404_NOT_FOUND)

    accounts = Account.objects.filter(coach=coach).prefetch_related("contacts")
    total_clients = Contact.objects.filter(coach=coach).count()

    result = {
        "coach": CoachSerializer(coach).data,
        "accounts": AccountSerializer(accounts, many=True).data,
        "total_accounts": accounts.count(),
        "total_clients": total_clients,
    }
    return Response(result)


@api_view(["GET"])
def accounts_list(request):
    """List accounts. Scoped to coach's own accounts."""
    coach = get_coach_for_user(request.user)
    if coach:
        accounts = Account.objects.filter(coach=coach).prefetch_related("contacts")
    elif request.user.is_admin():
        accounts = Account.objects.all().prefetch_related("contacts")
    else:
        return Response({"error": "No coach profile linked"}, status=status.HTTP_404_NOT_FOUND)
    return Response(AccountSerializer(accounts, many=True).data)


@api_view(["GET"])
def account_detail(request, account_id):
    """Get single account. Enforced ownership."""
    try:
        account = Account.objects.prefetch_related("contacts").get(id=account_id)
    except Account.DoesNotExist:
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    coach = get_coach_for_user(request.user)
    if coach and account.coach_id != coach.id:
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    return Response(AccountSerializer(account).data)


@api_view(["GET"])
def contacts_list(request):
    """List contacts. Scoped to coach."""
    coach = get_coach_for_user(request.user)
    if coach:
        contacts = Contact.objects.filter(coach=coach).select_related("coach")
    elif request.user.is_admin():
        contacts = Contact.objects.all().select_related("coach")
    else:
        return Response({"error": "No coach profile linked"}, status=status.HTTP_404_NOT_FOUND)
    return Response(ContactSerializer(contacts, many=True).data)


@api_view(["GET"])
def contact_detail(request, contact_id):
    """Get single contact. Enforced ownership."""
    try:
        contact = Contact.objects.select_related("coach", "account").get(id=contact_id)
    except Contact.DoesNotExist:
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    coach = get_coach_for_user(request.user)
    if coach and contact.coach_id != coach.id:
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    return Response(ContactSerializer(contact).data)
