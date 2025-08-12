from rest_framework.permissions import BasePermission

class IsDataManager(BasePermission):
    def has_permission(self, request, view):
        return getattr(request, "study_role", None) and request.study_role.key == "data_manager"

class HasRole(BasePermission):
    required_roles = []

    def has_permission(self, request, view):
        role = getattr(request, "study_role", None)
        return role and role.key in self.required_roles