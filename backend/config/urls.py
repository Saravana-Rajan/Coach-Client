from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("users.urls")),
    path("api/salesforce/", include("salesforce_sim.urls")),
    path("api/coaching/", include("coaching.urls")),
    path("api/sync/", include("sync.urls")),
    path("api/briefs/", include("briefs.urls")),
    path("api/sf-connector/", include("salesforce_connector.urls")),
    path("api/admin-mgmt/", include("admin_management.urls")),
]
