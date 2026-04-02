from django.urls import path
from . import views_coaches, views_accounts, views_contacts, views_bulk
from . import views_schema

urlpatterns = [
    # Coach management
    path("coaches/", views_coaches.list_coaches, name="admin-coaches-list"),
    path("coaches/create/", views_coaches.create_coach, name="admin-coach-create"),
    path("coaches/<int:coach_id>/", views_coaches.get_coach, name="admin-coach-detail"),
    path("coaches/<int:coach_id>/update/", views_coaches.update_coach, name="admin-coach-update"),
    path("coaches/<int:coach_id>/delete/", views_coaches.delete_coach, name="admin-coach-delete"),
    path("coaches/remove-from-org/", views_coaches.remove_coach_from_org, name="admin-coach-remove-org"),

    # Account management
    path("accounts/", views_accounts.list_accounts, name="admin-accounts-list"),
    path("accounts/create/", views_accounts.create_account, name="admin-account-create"),
    path("accounts/<int:account_id>/", views_accounts.get_account, name="admin-account-detail"),
    path("accounts/<int:account_id>/update/", views_accounts.update_account, name="admin-account-update"),
    path("accounts/<int:account_id>/delete/", views_accounts.delete_account, name="admin-account-delete"),
    path("accounts/<int:account_id>/reassign/", views_accounts.reassign_account, name="admin-account-reassign"),

    # Contact management
    path("contacts/", views_contacts.list_contacts, name="admin-contacts-list"),
    path("contacts/create/", views_contacts.create_contact, name="admin-contact-create"),
    path("contacts/<int:contact_id>/", views_contacts.get_contact, name="admin-contact-detail"),
    path("contacts/<int:contact_id>/update/", views_contacts.update_contact, name="admin-contact-update"),
    path("contacts/<int:contact_id>/delete/", views_contacts.delete_contact, name="admin-contact-delete"),
    path("contacts/<int:contact_id>/move/", views_contacts.move_contact, name="admin-contact-move"),
    path("contacts/<int:contact_id>/reassign/", views_contacts.reassign_contact, name="admin-contact-reassign"),

    # Bulk operations
    path("bulk/swap-coaches/", views_bulk.swap_coaches, name="admin-swap-coaches"),
    path("bulk/reassign/", views_bulk.bulk_reassign, name="admin-bulk-reassign"),
    path("bulk/history/", views_bulk.operation_history, name="admin-operation-history"),

    # Schema detection
    path("schema/status/", views_schema.schema_status, name="admin-schema-status"),
    path("schema/history/", views_schema.migration_history, name="admin-schema-history"),
    path("schema/detect/", views_schema.detect_changes, name="admin-schema-detect"),
    path("schema/apply/<int:migration_id>/", views_schema.apply_migration, name="admin-schema-apply"),
    path("schema/rollback/<int:migration_id>/", views_schema.rollback_migration, name="admin-schema-rollback"),
]
