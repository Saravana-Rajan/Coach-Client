from rest_framework.permissions import BasePermission
from coaching.models import Coach


class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin()


class IsCoachOrAdmin(BasePermission):
    """Coaches see only their own data. Admins see everything."""

    def has_permission(self, request, view):
        return request.user.is_authenticated


def get_coach_for_user(user):
    """Return the Coach object linked to this user, or None for admins."""
    if user.is_admin() or not user.coach_sf_id:
        return None
    try:
        return Coach.objects.get(sf_id=user.coach_sf_id)
    except Coach.DoesNotExist:
        return None
