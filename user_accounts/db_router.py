class RemoteUserRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'remote_auth':
            return 'rit_approval_system'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'remote_auth':
            return 'rit_approval_system'
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Disable migrations for remote_auth
        if app_label == 'remote_auth':
            return False
        return None
