# backend/tenancy/management/commands/sync_user_groups.py
"""
Sync User.groups with StudyMembership assignments

This command ensures that Django's User.groups reflects all active StudyMemberships.
Run this after updating the StudyMembership model to enable auto-sync.

Usage:
    python manage.py sync_user_groups
    python manage.py sync_user_groups --user john_doe
    python manage.py sync_user_groups --study 43EN
    python manage.py sync_user_groups --dry-run
"""
from django.core.management.base import BaseCommand, CommandError
from backends.tenancy.models import User, StudyMembership
from backends.tenancy.utils.role_manager import StudyRoleManager


class Command(BaseCommand):
    help = 'Sync User.groups with StudyMembership assignments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Sync only this username'
        )
        
        parser.add_argument(
            '--study',
            type=str,
            help='Sync only users in this study'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually changing it'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )

    def handle(self, *args, **options):
        username = options.get('user')
        study_code = options.get('study')
        dry_run = options.get('dry_run')
        verbose = options.get('verbose')

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("SYNCING USER GROUPS WITH STUDY MEMBERSHIPS"))
        self.stdout.write("=" * 80 + "\n")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made\n"))

        # Build queryset
        users = User.objects.filter(is_active=True)
        
        if username:
            users = users.filter(username=username)
            if not users.exists():
                raise CommandError(f"User '{username}' not found")
            self.stdout.write(f"Syncing user: {username}\n")
        
        if study_code:
            users = users.filter(
                study_memberships__study__code=study_code.upper(),
                study_memberships__is_active=True
            ).distinct()
            if not users.exists():
                raise CommandError(f"No active users found in study '{study_code}'")
            self.stdout.write(f"Syncing users in study: {study_code}\n")

        # Get users with memberships
        users = users.filter(
            study_memberships__isnull=False
        ).distinct().prefetch_related(
            'groups',
            'study_memberships__group',
            'study_memberships__study'
        )

        if not users.exists():
            self.stdout.write(self.style.WARNING("No users with study memberships found\n"))
            return

        self.stdout.write(f"Found {users.count()} user(s) to sync\n")
        
        # Statistics
        total_stats = {
            'users_processed': 0,
            'users_changed': 0,
            'groups_added': 0,
            'groups_removed': 0,
            'errors': 0,
        }

        # Process each user
        for user in users:
            try:
                stats = self._sync_user(user, dry_run, verbose)
                
                total_stats['users_processed'] += 1
                
                if stats['added'] > 0 or stats['removed'] > 0:
                    total_stats['users_changed'] += 1
                    total_stats['groups_added'] += stats['added']
                    total_stats['groups_removed'] += stats['removed']
                    
            except Exception as e:
                total_stats['errors'] += 1
                self.stderr.write(
                    self.style.ERROR(f"Error syncing {user.username}: {e}")
                )

        # Print summary
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("SYNC SUMMARY"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Users Processed: {total_stats['users_processed']}")
        self.stdout.write(f"Users Changed: {total_stats['users_changed']}")
        self.stdout.write(f"Groups Added: {total_stats['groups_added']}")
        self.stdout.write(f"Groups Removed: {total_stats['groups_removed']}")
        self.stdout.write(f"Errors: {total_stats['errors']}")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("\nThis was a DRY RUN - no actual changes were made")
            )
            self.stdout.write("Run without --dry-run to apply changes\n")
        else:
            self.stdout.write(
                self.style.SUCCESS("\nSync completed successfully!")
            )
        
        self.stdout.write("=" * 80 + "\n")

    def _sync_user(self, user, dry_run, verbose):
        """Sync a single user's groups"""
        
        # Get active study memberships
        active_memberships = StudyMembership.objects.filter(
            user=user,
            is_active=True
        ).select_related('group', 'study')

        # Groups user should have
        should_have_groups = set()
        for membership in active_memberships:
            if membership.group:
                should_have_groups.add(membership.group)

        # Current study groups
        current_study_groups = set()
        for group in user.groups.all():
            if StudyRoleManager.is_study_group(group.name):
                current_study_groups.add(group)

        # Calculate changes
        to_add = should_have_groups - current_study_groups
        to_remove = current_study_groups - should_have_groups

        # Show changes if verbose or if changes exist
        if (to_add or to_remove) and (verbose or not dry_run):
            self.stdout.write(
                self.style.WARNING(f"\n{user.username} ({user.get_full_name() or 'No name'})")
            )
            
            if to_add:
                self.stdout.write("  Groups to ADD:")
                for group in to_add:
                    self.stdout.write(f"    + {group.name}")
            
            if to_remove:
                self.stdout.write("  Groups to REMOVE:")
                for group in to_remove:
                    self.stdout.write(f"    - {group.name}")

        # Apply changes
        added = 0
        removed = 0

        if not dry_run:
            for group in to_add:
                user.groups.add(group)
                added += 1
            
            for group in to_remove:
                user.groups.remove(group)
                removed += 1

        return {
            'added': len(to_add),
            'removed': len(to_remove),
            'total_groups': len(should_have_groups),
        }