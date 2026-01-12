# backend/tenancy/management/commands/sync_study_permissions.py
"""
Sync permissions for study groups

This command assigns Django permissions to study groups based on role templates.
Run this after migrations to ensure permissions are properly assigned.

Usage:
    python manage.py sync_study_permissions
    python manage.py sync_study_permissions --study 43EN
    python manage.py sync_study_permissions --force
    python manage.py sync_study_permissions --verbose
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from backends.tenancy.models import Study
from backends.tenancy.utils.role_manager import StudyRoleManager, RoleTemplate


class Command(BaseCommand):
    help = 'Sync permissions for study groups based on role templates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--study',
            type=str,
            help='Sync only this study code'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-assignment (remove extra permissions)'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes'
        )
        
        parser.add_argument(
            '--create-groups',
            action='store_true',
            help='Create groups if they do not exist'
        )

    def handle(self, *args, **options):
        study_code = options.get('study')
        force = options.get('force')
        verbose = options.get('verbose')
        dry_run = options.get('dry_run')
        create_groups = options.get('create_groups')

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("SYNCING STUDY PERMISSIONS"))
        self.stdout.write("=" * 80 + "\n")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made\n"))

        # Get studies to process
        if study_code:
            studies = Study.objects.filter(code__iexact=study_code)
            if not studies.exists():
                raise CommandError(f"Study '{study_code}' not found")
        else:
            studies = Study.objects.all()

        total_stats = {
            'studies_processed': 0,
            'groups_created': 0,
            'permissions_assigned': 0,
            'permissions_removed': 0,
            'errors': 0,
        }

        for study in studies:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(self.style.HTTP_INFO(f"Study: {study.code} - {study.name}"))
            self.stdout.write(f"{'='*60}")
            
            try:
                stats = self._sync_study(study, force, verbose, dry_run, create_groups)
                
                total_stats['studies_processed'] += 1
                total_stats['groups_created'] += stats.get('groups_created', 0)
                total_stats['permissions_assigned'] += stats.get('permissions_assigned', 0)
                total_stats['permissions_removed'] += stats.get('permissions_removed', 0)
                
            except Exception as e:
                total_stats['errors'] += 1
                self.stderr.write(
                    self.style.ERROR(f"Error processing study {study.code}: {e}")
                )

        # Print summary
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("SYNC SUMMARY"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Studies Processed: {total_stats['studies_processed']}")
        self.stdout.write(f"Groups Created: {total_stats['groups_created']}")
        self.stdout.write(f"Permissions Assigned: {total_stats['permissions_assigned']}")
        self.stdout.write(f"Permissions Removed: {total_stats['permissions_removed']}")
        self.stdout.write(f"Errors: {total_stats['errors']}")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("\nThis was a DRY RUN - no actual changes were made")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("\nSync completed successfully!")
            )
        
        self.stdout.write("=" * 80 + "\n")

    def _sync_study(self, study, force, verbose, dry_run, create_groups):
        """Sync permissions for a single study"""
        app_label = f'study_{study.code.lower()}'
        stats = {'groups_created': 0, 'permissions_assigned': 0, 'permissions_removed': 0}
        
        # Check ContentTypes exist
        content_types = ContentType.objects.filter(app_label=app_label)
        ct_count = content_types.count()
        
        if ct_count == 0:
            self.stdout.write(self.style.WARNING(
                f"  No ContentTypes found for '{app_label}'. "
                f"Make sure migrations have been run."
            ))
            return stats
        
        if verbose:
            self.stdout.write(f"  ContentTypes: {ct_count}")
        
        # Check permissions exist
        permissions = Permission.objects.filter(content_type__app_label=app_label)
        perm_count = permissions.count()
        
        if perm_count == 0:
            self.stdout.write(self.style.WARNING(
                f"  No Permissions found for '{app_label}'. "
                f"Permissions are created automatically when running migrations."
            ))
            return stats
        
        if verbose:
            self.stdout.write(f"  Permissions available: {perm_count}")
            
            # Show breakdown by action
            for action in ['view', 'add', 'change', 'delete']:
                count = permissions.filter(codename__startswith=action).count()
                self.stdout.write(f"    - {action}: {count}")
        
        # Check/create groups
        self.stdout.write(f"\n  Groups for study {study.code}:")
        
        for role_key in RoleTemplate.get_all_role_keys():
            group_name = StudyRoleManager.get_group_name(study.code, role_key)
            
            try:
                group = Group.objects.get(name=group_name)
                existing = True
            except Group.DoesNotExist:
                if create_groups and not dry_run:
                    group = Group.objects.create(name=group_name)
                    stats['groups_created'] += 1
                    existing = False
                    self.stdout.write(self.style.SUCCESS(f"    + Created: {group_name}"))
                else:
                    self.stdout.write(self.style.WARNING(f"    ✗ Missing: {group_name}"))
                    continue
            
            # Get expected permissions for this role
            allowed_actions = set(RoleTemplate.get_permissions(role_key))
            expected_perms = set()
            
            for perm in permissions:
                action = perm.codename.split('_')[0]
                if action in allowed_actions:
                    expected_perms.add(perm)
            
            # Get current permissions
            current_perms = set(group.permissions.filter(content_type__app_label=app_label))
            
            # Calculate diff
            to_add = expected_perms - current_perms
            to_remove = current_perms - expected_perms if force else set()
            
            # Display status
            status_parts = []
            if existing:
                status_parts.append(f"current: {len(current_perms)}")
            status_parts.append(f"expected: {len(expected_perms)}")
            
            if to_add:
                status_parts.append(self.style.SUCCESS(f"+{len(to_add)}"))
            if to_remove:
                status_parts.append(self.style.ERROR(f"-{len(to_remove)}"))
            
            status = ", ".join(status_parts)
            
            if existing:
                if to_add or to_remove:
                    self.stdout.write(f"    ⚠ {group_name} ({status})")
                else:
                    self.stdout.write(f"    ✓ {group_name} ({status})")
            
            # Apply changes
            if not dry_run:
                if to_add:
                    group.permissions.add(*to_add)
                    stats['permissions_assigned'] += len(to_add)
                    
                if to_remove:
                    group.permissions.remove(*to_remove)
                    stats['permissions_removed'] += len(to_remove)
            
            # Verbose: show permission details
            if verbose and (to_add or to_remove):
                if to_add:
                    self.stdout.write(f"        Adding: {[p.codename for p in to_add][:5]}...")
                if to_remove:
                    self.stdout.write(f"        Removing: {[p.codename for p in to_remove][:5]}...")
        
        return stats
