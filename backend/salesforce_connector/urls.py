from django.urls import path

from . import views

urlpatterns = [
    path("pull/", views.pull_from_salesforce, name="sf-pull"),
    path("notify/", views.sf_webhook_notify, name="sf-webhook-notify"),
    path("status/", views.sf_sync_status, name="sf-sync-status"),
    path("pull-and-sync/", views.sf_pull_and_sync, name="sf-pull-and-sync"),
    path("schema-check/", views.sf_schema_check, name="sf-schema-check"),
    path("schema-webhook/", views.sf_schema_webhook, name="sf-schema-webhook"),
]
