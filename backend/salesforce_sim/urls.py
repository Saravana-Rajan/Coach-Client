from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"coaches", views.SFCoachViewSet)
router.register(r"accounts", views.SFAccountViewSet)
router.register(r"contacts", views.SFContactViewSet)
router.register(r"assignments", views.SFAssignmentViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("notify/", views.notify_change, name="sf-notify-change"),
]
