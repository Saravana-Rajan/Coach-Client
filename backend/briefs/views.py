from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from coaching.permissions import get_coach_for_user
from .models import TransitionBrief
from .serializers import TransitionBriefSerializer


@api_view(["GET"])
def briefs_list(request):
    """List briefs. Coach sees own, admin sees all."""
    coach = get_coach_for_user(request.user)
    if coach:
        briefs = TransitionBrief.objects.filter(coach=coach)
    elif request.user.is_admin():
        briefs = TransitionBrief.objects.all()
    else:
        return Response({"error": "No coach profile"}, status=status.HTTP_404_NOT_FOUND)
    return Response(TransitionBriefSerializer(briefs, many=True).data)


@api_view(["GET"])
def brief_detail(request, brief_id):
    """Get single brief. Enforced ownership."""
    try:
        brief = TransitionBrief.objects.select_related("coach").get(id=brief_id)
    except TransitionBrief.DoesNotExist:
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    coach = get_coach_for_user(request.user)
    if coach and (not brief.coach or brief.coach.id != coach.id):
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    return Response(TransitionBriefSerializer(brief).data)
