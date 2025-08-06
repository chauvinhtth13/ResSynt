"""
Database router để điều khiển multiple databases
"""

class DatabaseRouter:
    """
    Router để điều khiển database operations cho multiple databases
    """
    
    # Apps sử dụng database riêng
    fourtythree_apps = {'study_43en'}
    
    def db_for_read(self, model, **hints):
        """Quyết định database cho read operations"""
        if model._meta.app_label in self.fourtythree_apps:
            return 'fourtythree_db'
        return 'default'
    
    def db_for_write(self, model, **hints):
        """Quyết định database cho write operations"""
        if model._meta.app_label in self.fourtythree_apps:
            return 'fourtythree_db'
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        """Cho phép relations giữa objects"""
        db_set = {'default', 'fourtythree_db'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Quyết định app nào migrate vào database nào"""
        if app_label in self.fourtythree_apps:
            return db == 'fourtythree_db'
        elif db == 'fourtythree_db':
            # Không cho apps khác migrate vào fourtythree_db database
            return False
        return db == 'default'
