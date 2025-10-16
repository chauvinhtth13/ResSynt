# backend/tenancy/management/commands/check_user_roles.py
"""
Management command to check user roles and permissions

Usage:
    python manage.py check_user_roles <username> [study_code]
    python manage.py check_user_roles john_doe
    python manage.py check_user_roles john_doe 43EN
    python manage.py check_user_roles --all-users
"""
from django.core.management.base import BaseCommand, CommandError
from backends.tenancy.models import User, Study
from backends.tenancy.utils import RoleChecker


class Command(BaseCommand):
    help = 'Check user roles and permissions across studies'

    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            nargs='?',
            type=str,
            help='Username to check'
        )
        
        parser.add_argument(
            'study_code',
            nargs='?',
            type=str,
            help='Specific study code (optional)'
        )
        
        parser.add_argument(
            '--all-users',
            action='store_true',
            help='Show roles for all active users'
        )
        
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed permissions'
        )

    def handle(self, *args, **options):
        username = options.get('username')
        study_code = options.get('study_code')
        all_users = options.get('all_users')
        detailed = options.get('detailed')

        if all_users:
            self.show_all_users(detailed)
        elif username:
            if study_code:
                self.show_user_in_study(username, study_code, detailed)
            else:
                self.show_user_all_studies(username, detailed)
        else:
            raise CommandError('Please specify username or use --all-users')

    def show_all_users(self, detailed=False):
        """Show roles for all active users"""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("ALL USERS AND THEIR ROLES"))
        self.stdout.write("=" * 80 + "\n")

        users = User.objects.filter(is_active=True).order_by('username')
        
        for user in users:
            all_roles = RoleChecker.get_all_user_roles(user)
            
            if not all_roles:
                continue
            
            self.stdout.write(
                self.style.WARNING(
                    f"\n{user.username} ({user.get_full_name() or 'No name'})"
                )
            )
            self.stdout.write("-" * 80)
            
            for study_id, info in all_roles.items():
                role_display = f"{info['role_name']:25s}"
                study_display = f"{info['study_code']:10s}"
                
                self.stdout.write(
                    f"  Study: {study_display} Role: {role_display}"
                )
                
                if detailed:
                    study = Study.objects.get(pk=study_id)
                    summary = RoleChecker.get_permission_summary(user, study)
                    
                    for model, actions in sorted(summary.items()):
                        self.stdout.write(
                            f"    {model:20s}: {', '.join(sorted(actions))}"
                        )

        self.stdout.write("\n" + "=" * 80 + "\n")

    def show_user_all_studies(self, username, detailed=False):
        """Show all roles for a user across all studies"""
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' not found")

        all_roles = RoleChecker.get_all_user_roles(user)

        if not all_roles:
            self.stdout.write(
                self.style.WARNING(
                    f"\nUser '{username}' has no active study memberships\n"
                )
            )
            return

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(
            self.style.SUCCESS(
                f"ROLES FOR USER: {username} ({user.get_full_name() or 'No name'})"
            )
        )
        self.stdout.write("=" * 80 + "\n")

        for study_id, info in all_roles.items():
            study = Study.objects.get(pk=study_id)
            
            self.stdout.write(
                self.style.WARNING(
                    f"\nStudy: {info['study_code']} - {info['study_name']}"
                )
            )
            self.stdout.write("-" * 80)
            
            self.stdout.write(f"Role: {info['role_name']} ({info['role_key']})")
            
            # Get membership
            membership = user.get_study_membership(study)
            if membership:
                role_info = membership.get_role_info()
                
                self.stdout.write(
                    f"Description: {role_info.get('description', 'N/A')}"
                )
                self.stdout.write(
                    f"Privileged: {role_info.get('is_privileged', False)}"
                )
                self.stdout.write(
                    f"Priority: {role_info.get('priority', 0)}"
                )
                
                # Sites
                sites = membership.get_accessible_sites()
                if membership.can_access_all_sites:
                    self.stdout.write(f"Sites: All Sites ({len(sites)} total)")
                else:
                    self.stdout.write(f"Sites: {', '.join(sites)}")
            
            if detailed:
                self.stdout.write("\nPermissions by Model:")
                summary = RoleChecker.get_permission_summary(user, study)
                
                if summary:
                    for model, actions in sorted(summary.items()):
                        self.stdout.write(
                            f"  {model:25s}: {', '.join(sorted(actions))}"
                        )
                else:
                    self.stdout.write("  No permissions found")
                
                total_perms = len(RoleChecker.get_all_permissions(user, study))
                self.stdout.write(f"\nTotal Permissions: {total_perms}")

        self.stdout.write("\n" + "=" * 80 + "\n")

    def show_user_in_study(self, username, study_code, detailed=False):
        """Show user's role and permissions in a specific study"""
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' not found")

        try:
            study = Study.objects.get(code=study_code.upper())
        except Study.DoesNotExist:
            raise CommandError(f"Study '{study_code}' not found")

        # Check if user has access
        if not user.has_study_access(study):
            self.stdout.write(
                self.style.WARNING(
                    f"\nUser '{username}' does not have access to study '{study_code}'\n"
                )
            )
            return

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(
            self.style.SUCCESS(
                f"USER ROLE IN STUDY: {username} @ {study_code}"
            )
        )
        self.stdout.write("=" * 80 + "\n")

        # Get role
        role_key = RoleChecker.get_role(user, study)
        role_display = RoleChecker.get_role_display(user, study)
        
        self.stdout.write(f"User: {user.username} ({user.get_full_name()})")
        self.stdout.write(f"Study: {study.code} - {study.safe_translation_getter('name', any_language=True)}")
        self.stdout.write(f"Role Key: {role_key}")
        self.stdout.write(f"Role Name: {role_display}")
        
        # Get membership details
        membership = user.get_study_membership(study)
        if membership:
            role_info = membership.get_role_info()
            
            self.stdout.write(f"\nRole Details:")
            self.stdout.write(f"  Description: {role_info.get('description', 'N/A')}")
            self.stdout.write(f"  Is Privileged: {role_info.get('is_privileged', False)}")
            self.stdout.write(f"  Priority: {role_info.get('priority', 0)}")
            self.stdout.write(f"  Allowed Actions: {', '.join(role_info.get('permissions', []))}")
            
            # Sites
            sites = membership.get_accessible_sites()
            self.stdout.write(f"\nSite Access:")
            if membership.can_access_all_sites:
                self.stdout.write(f"  All Sites ({len(sites)} total)")
            else:
                self.stdout.write(f"  Specific Sites: {', '.join(sites)}")
            
            # Status
            self.stdout.write(f"\nStatus:")
            self.stdout.write(f"  Is Active: {membership.is_active}")
            self.stdout.write(f"  Assigned At: {membership.assigned_at}")
            if membership.assigned_by:
                self.stdout.write(f"  Assigned By: {membership.assigned_by.username}")

        # Check admin status
        is_admin = RoleChecker.is_admin(user, study)
        self.stdout.write(f"\nIs Admin: {is_admin}")

        # Show permissions
        self.stdout.write(f"\nPermissions by Model:")
        summary = RoleChecker.get_permission_summary(user, study)
        
        if summary:
            for model, actions in sorted(summary.items()):
                self.stdout.write(
                    f"  {model:25s}: {', '.join(sorted(actions))}"
                )
        else:
            self.stdout.write("  No permissions found")

        total_perms = len(RoleChecker.get_all_permissions(user, study))
        self.stdout.write(f"\nTotal Permissions: {total_perms}")

        # If detailed, show all permission codenames
        if detailed:
            self.stdout.write("\nAll Permission Codenames:")
            all_perms = RoleChecker.get_all_permissions(user, study)
            for perm in sorted(all_perms):
                self.stdout.write(f"  - {perm}")

        self.stdout.write("\n" + "=" * 80 + "\n")