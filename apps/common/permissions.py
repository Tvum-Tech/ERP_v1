from urllib import request

from rest_framework import permissions

class BaseRolePermission(permissions.BasePermission):
    """
    Base class for role-based permissions checking Django Groups.
    Blocks DELETE for everyone.
    """
    role_name = None

    def has_permission(self, request, view):
        # 🚫 GLOBAL ERP RULE: No one can delete
        if request.method == 'DELETE':
            return False

        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers bypass role checks but NOT the delete rule
        if request.user.is_superuser:
            return True

        if not self.role_name:
            return False

        return request.user.groups.filter(name=self.role_name).exists()

class IsAdmin(BaseRolePermission):
    role_name = 'Admin'

class IsSales(BaseRolePermission):
    role_name = 'Sales'

class IsFinance(BaseRolePermission):
    role_name = 'Finance'

class IsViewer(BaseRolePermission):
    role_name = 'Viewer'

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allows Admin to edit (C/U), but blocks DELETE for everyone.
    """
    def has_permission(self, request, view):
        # 🚫 GLOBAL ERP RULE: No one can delete
        if request.method == 'DELETE':
            return False

        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        return request.user and (request.user.is_superuser or request.user.groups.filter(name='Admin').exists())

class IsEditor(permissions.BasePermission):
    """
    Allows Admin or Sales to edit (C/U), blocks DELETE.
    """
    def has_permission(self, request, view):
        print(f"Checking permissions for {request.user} on {request.method} {request.path}")

        # GLOBAL ERP RULE: No one can delete
        if request.method == 'DELETE':
    # allow superuser
            if request.user and request.user.is_superuser:
                return True

    # allow Admin / Sales group
        return request.user.groups.filter(name__in=['Admin', 'Sales']).exists()

        if not request.user or not request.user.is_authenticated:
            return False
            
        if request.user.is_superuser:
            return True
            
        return request.user.groups.filter(name__in=['Admin', 'Sales']).exists()

class IsEditorOrReadOnly(permissions.BasePermission):
    """
    Allows Admin or Sales to edit (C/U), Read-Only for others. Blocks DELETE.
    """
    def has_permission(self, request, view):
        # GLOBAL ERP RULE: No one can delete
        print(f"Checking permissions for {request.user} on {request.method} {request.path}")
        if request.method == 'DELETE':
             return request.user.is_superuser or \
                    request.user.groups.filter(name__in=['Admin', 'Sales']).exists()

        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
            
        if not request.user or not request.user.is_authenticated:
            return False
            
        return request.user.is_superuser or request.user.groups.filter(name__in=['Admin', 'Sales']).exists()
