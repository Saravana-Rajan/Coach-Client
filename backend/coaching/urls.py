from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("accounts/", views.accounts_list, name="accounts-list"),
    path("accounts/<int:account_id>/", views.account_detail, name="account-detail"),
    path("contacts/", views.contacts_list, name="contacts-list"),
    path("contacts/<int:contact_id>/", views.contact_detail, name="contact-detail"),
]
