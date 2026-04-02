from django.apps import AppConfig


class AdminManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_management'

    def ready(self):
        """Enable WAL mode on SQLite databases to prevent 'database is locked' errors."""
        from django.db import connections
        for alias in connections:
            conn = connections[alias]
            if conn.vendor == 'sqlite':
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA busy_timeout=30000;")
                cursor.close()
