# backend/tenancy/management/commands/init_tenancy.py
from django.core.management.base import BaseCommand
from django.db import transaction
from backend.tenancy.models import Role, Permission
# List permissions by category
from backend.tenancy.models.permission import PermissionCategory, RolePermission

class Command(BaseCommand):
    help = 'Initialize tenancy system with default roles and permissions'
    
    def handle(self, *args, **options):
        with transaction.atomic():
            # Initialize permissions
            self.stdout.write('Creating permissions...')
            perm_count = Permission.initialize_permissions()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created {perm_count} permissions'
                )
            )
            
            # Initialize roles
            self.stdout.write('\nCreating roles...')
            role_count = Role.initialize_roles()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created {role_count} roles'
                )
            )
            
            # Display summary
            self.stdout.write('\n' + '='*50)
            self.stdout.write('Summary:')
            self.stdout.write('='*50)
            

            
            for category, category_name in PermissionCategory.CHOICES:
                perms = Permission.objects.filter(category=category)
                if perms.exists():
                    self.stdout.write(f'\n{category_name}:')
                    for perm in perms:
                        danger_mark = ' ' if perm.is_dangerous else ''
                        self.stdout.write(f'  - {danger_mark}{perm.name} ({perm.code})')
            
            # List roles
            self.stdout.write('\n\nRoles:')
            for role in Role.objects.all().order_by('title'):
                # Use direct query instead of role_permissions
                perm_count = RolePermission.objects.filter(role=role).count()
                self.stdout.write(
                    f'  - {role.title} ({role.code}): '
                    f'{perm_count} permissions'
                )
                
                # Show permissions for this role
                role_perms = RolePermission.objects.filter(
                    role=role
                ).select_related('permission')
                
                if role_perms:
                    self.stdout.write('    Permissions:')
                    for rp in role_perms[:5]:  # Show first 5
                        self.stdout.write(f'      {rp.permission.name}')
                    if role_perms.count() > 5:
                        self.stdout.write(f'      ... and {role_perms.count() - 5} more')
            
            # Summary statistics
            self.stdout.write('\n' + '='*50)
            self.stdout.write('Statistics:')
            self.stdout.write(f'  - Total Permissions: {Permission.objects.count()}')
            self.stdout.write(f'  - Total Roles: {Role.objects.count()}')
            self.stdout.write(f'  - Total Role-Permission Links: {RolePermission.objects.count()}')
            
            self.stdout.write(
                self.style.SUCCESS(
                    '\nTenancy system initialized successfully!'
                )
            )