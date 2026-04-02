from django.urls import path
from . import views

urlpatterns = [
    path("", views.briefs_list, name="briefs-list"),
    path("<int:brief_id>/", views.brief_detail, name="brief-detail"),
]
