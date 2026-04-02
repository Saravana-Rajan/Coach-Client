from django.urls import path
from . import views

urlpatterns = [
    path("trigger/", views.trigger_sync, name="trigger-sync"),
    path("history/", views.sync_history, name="sync-history"),
    path("history/<int:sync_id>/", views.sync_detail, name="sync-detail"),
    path("audit/", views.audit_trail, name="audit-trail"),
]
