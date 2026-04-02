class SalesforceRouter:
    """Routes salesforce_sim models to the 'salesforce' database."""

    SF_APP = "salesforce_sim"

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.SF_APP:
            return "salesforce"
        return "default"

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.SF_APP:
            return "salesforce"
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        a1 = obj1._meta.app_label
        a2 = obj2._meta.app_label
        if a1 == self.SF_APP or a2 == self.SF_APP:
            return a1 == a2
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == self.SF_APP:
            return db == "salesforce"
        return db == "default"
