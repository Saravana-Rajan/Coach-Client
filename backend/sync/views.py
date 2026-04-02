from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from coaching.permissions import IsAdminUser
from .models import SyncLog, AuditRecord
from .serializers import SyncLogSerializer, SyncLogListSerializer, AuditRecordSerializer
from .engine import run_sync


@api_view(["POST"])
def trigger_sync(request):
    """Admin triggers a full sync."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    sync_log = run_sync()
    serializer = SyncLogSerializer(sync_log)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def sync_history(request):
    """List all sync runs. Admin only."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    syncs = SyncLog.objects.all()
    serializer = SyncLogListSerializer(syncs, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def sync_detail(request, sync_id):
    """Get a single sync with its audit records."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
    try:
        sync_log = SyncLog.objects.get(id=sync_id)
    except SyncLog.DoesNotExist:
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    serializer = SyncLogSerializer(sync_log)
    return Response(serializer.data)


@api_view(["GET"])
def audit_trail(request):
    """Filterable audit trail. Admin only."""
    if not request.user.is_admin():
        return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)

    records = AuditRecord.objects.all()

    # Filters
    change_type = request.query_params.get("change_type")
    if change_type:
        records = records.filter(change_type=change_type)

    coach_name = request.query_params.get("coach")
    if coach_name:
        records = records.filter(coach_name__icontains=coach_name)

    account_name = request.query_params.get("account")
    if account_name:
        records = records.filter(account_name__icontains=account_name)

    date_from = request.query_params.get("date_from")
    if date_from:
        records = records.filter(detected_at__date__gte=date_from)

    date_to = request.query_params.get("date_to")
    if date_to:
        records = records.filter(detected_at__date__lte=date_to)

    serializer = AuditRecordSerializer(records, many=True)
    return Response(serializer.data)
