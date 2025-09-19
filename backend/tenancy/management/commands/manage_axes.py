# backend/tenancy/management/commands/manage_axes.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from axes.models import AccessAttempt, AccessFailureLog
from axes.utils import reset
from django.utils import timezone
from tabulate import tabulate

User = get_user_model()


class Command(BaseCommand):
    help = 'Manage Axes security blocks and user status'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--list-blocked',
            action='store_true',
            help='List all blocked users'
        )
        parser.add_argument(
            '--unblock',
            type=str,
            help='Unblock specific username'
        )
        parser.add_argument(
            '--unblock-all',
            action='store_true',
            help='Unblock all users'
        )
        parser.add_argument(
            '--show-status',
            type=str,
            help='Show axes status for specific username'
        )
        parser.add_argument(
            '--sync-all',
            action='store_true',
            help='Sync all user statuses with axes'
        )
        parser.add_argument(
            '--activate',
            type=str,
            help='Activate user and unblock axes'
        )
        parser.add_argument(
            '--report',
            action='store_true',
            help='Generate security report'
        )
    
    def handle(self, *args, **options):
        if options['list_blocked']:
            self.list_blocked_users()
        elif options['unblock']:
            self.unblock_user(options['unblock'])
        elif options['unblock_all']:
            self.unblock_all_users()
        elif options['show_status']:
            self.show_user_status(options['show_status'])
        elif options['sync_all']:
            self.sync_all_users()
        elif options['activate']:
            self.activate_user(options['activate'])
        elif options['report']:
            self.generate_report()
        else:
            self.stdout.write(self.style.WARNING('No action specified. Use --help for options.'))
    
    def list_blocked_users(self):
        """List all blocked users with details"""
        blocked_users = []
        
        for user in User.objects.all():
            is_blocked, reason, attempts = user.get_axes_status() # type: ignore
            
            if is_blocked or user.status == User.Status.BLOCKED: # type: ignore
                blocked_users.append([
                    user.username,
                    user.email or 'N/A',
                    user.status, # type: ignore
                    'Yes' if is_blocked else 'No',
                    attempts,
                    reason or 'Manual block'
                ])
        
        if blocked_users:
            self.stdout.write(self.style.ERROR(f"\n{len(blocked_users)} blocked user(s) found:\n"))
            headers = ['Username', 'Email', 'Status', 'Axes Blocked', 'Attempts', 'Reason']
            print(tabulate(blocked_users, headers=headers, tablefmt='grid'))
        else:
            self.stdout.write(self.style.SUCCESS("\n✓ No blocked users found."))
    
    def unblock_user(self, username):
        """Unblock specific user"""
        try:
            user = User.objects.get(username=username)
            
            # Show current status
            self.stdout.write(f"\nUnblocking user: {username}")
            self.stdout.write(f"Current status: {user.status}") # type: ignore
            
            # Unblock
            if user.unblock_user(): # type: ignore
                self.stdout.write(self.style.SUCCESS(f"✓ Successfully unblocked {username}"))
                self.stdout.write(f"New status: {user.status}") # type: ignore
            else:
                self.stdout.write(self.style.ERROR(f"✗ Failed to unblock {username}"))
                
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"✗ User not found: {username}"))
    
    def unblock_all_users(self):
        """Unblock all users"""
        confirm = input("\nAre you sure you want to unblock ALL users? (yes/no): ")
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING("Operation cancelled."))
            return
        
        count = User.objects.unblock_users() # type: ignore
        self.stdout.write(self.style.SUCCESS(f"\n✓ Unblocked {count} user(s)."))
    
    def show_user_status(self, username):
        """Show detailed status for a user"""
        try:
            user = User.objects.get(username=username)
            is_blocked, reason, attempts = user.get_axes_status() # type: ignore
            
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(self.style.SUCCESS(f"USER DETAILS: {username}"))
            self.stdout.write(f"{'='*60}")
            
            # User info
            info = [
                ['Full Name', user.get_full_name() or 'N/A'],
                ['Email', user.email or 'N/A'],
                ['Status', user.status], # type: ignore
                ['Is Active', '✓' if user.is_active else '✗'],
                ['Is Superuser', '✓' if user.is_superuser else '✗'],
                ['Date Joined', user.date_joined.strftime('%Y-%m-%d %H:%M')],
                ['Last Login', user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never'],
            ]
            print(tabulate(info, tablefmt='plain'))
            
            # Axes status
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(self.style.SUCCESS("AXES SECURITY STATUS"))
            self.stdout.write(f"{'='*60}")
            
            if is_blocked:
                self.stdout.write(self.style.ERROR(f"Status: BLOCKED"))
                self.stdout.write(f"Reason: {reason}")
            else:
                self.stdout.write(self.style.SUCCESS(f"Status: NOT BLOCKED"))
            
            from axes.conf import settings as axes_settings
            limit = axes_settings.AXES_FAILURE_LIMIT
            self.stdout.write(f"Failed Attempts: {attempts} / {limit}")
            
            # Progress bar
            if attempts > 0:
                percentage = min((attempts / limit) * 100, 100)
                filled = int(percentage / 2)
                bar = '█' * filled + '░' * (50 - filled)
                color = self.style.ERROR if percentage >= 80 else self.style.WARNING if percentage >= 50 else self.style.SUCCESS
                self.stdout.write(color(f"[{bar}] {percentage:.0f}%"))
            
            # Recent failures
            recent_failures = AccessFailureLog.objects.filter(
                username=username
            ).order_by('-attempt_time')[:10]
            
            if recent_failures:
                self.stdout.write(f"\n{'='*60}")
                self.stdout.write(self.style.SUCCESS("RECENT FAILED ATTEMPTS"))
                self.stdout.write(f"{'='*60}")
                
                failures_data = []
                for failure in recent_failures:
                    failures_data.append([
                        failure.attempt_time.strftime('%Y-%m-%d %H:%M:%S'),
                        failure.ip_address,
                        failure.user_agent[:50] if failure.user_agent else 'N/A'
                    ])
                
                headers = ['Time', 'IP Address', 'User Agent']
                print(tabulate(failures_data, headers=headers, tablefmt='grid'))
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"✗ User not found: {username}"))
    
    def sync_all_users(self):
        """Sync all user statuses with axes"""
        self.stdout.write("\nSyncing all users with axes status...")
        count = User.objects.sync_all_with_axes() # type: ignore
        self.stdout.write(self.style.SUCCESS(f"✓ Synced {count} user(s)."))
    
    def activate_user(self, username):
        """Activate user and unblock axes"""
        try:
            user = User.objects.get(username=username)
            user.status = User.Status.ACTIVE # type: ignore
            user.save()
            self.stdout.write(self.style.SUCCESS(f"✓ User {username} activated and unblocked."))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"✗ User not found: {username}"))
    
    def generate_report(self):
        """Generate security report"""
        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(self.style.SUCCESS("SECURITY REPORT"))
        self.stdout.write(f"{'='*80}")
        self.stdout.write(f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write(f"{'='*80}\n")
        
        # Statistics
        total_users = User.objects.count()
        active_users = User.objects.filter(status=User.Status.ACTIVE).count() # type: ignore
        blocked_users = User.objects.filter(status=User.Status.BLOCKED).count() # type: ignore
        
        axes_blocked = 0
        users_with_attempts = 0
        total_attempts = 0
        
        for user in User.objects.all():
            is_blocked, _, attempts = user.get_axes_status() # type: ignore
            if is_blocked:
                axes_blocked += 1
            if attempts > 0:
                users_with_attempts += 1
                total_attempts += attempts
        
        stats = [
            ['Total Users', total_users],
            ['Active Users', f"{active_users} ({active_users/total_users*100:.1f}%)"],
            ['Blocked Users (Status)', f"{blocked_users} ({blocked_users/total_users*100:.1f}%)"],
            ['Blocked by Axes', f"{axes_blocked} ({axes_blocked/total_users*100:.1f}%)"],
            ['Users with Failed Attempts', f"{users_with_attempts} ({users_with_attempts/total_users*100:.1f}%)"],
            ['Total Failed Attempts', total_attempts],
        ]
        
        print(tabulate(stats, tablefmt='grid'))
        
        # Top failed login attempts
        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(self.style.WARNING("TOP USERS WITH FAILED ATTEMPTS"))
        self.stdout.write(f"{'='*80}\n")
        
        top_failures = []
        for user in User.objects.all():
            is_blocked, _, attempts = user.get_axes_status() # type: ignore
            if attempts > 0:
                top_failures.append([user.username, attempts, 'BLOCKED' if is_blocked else 'ACTIVE'])
        
        top_failures.sort(key=lambda x: x[1], reverse=True)
        
        if top_failures[:10]:
            headers = ['Username', 'Failed Attempts', 'Status']
            print(tabulate(top_failures[:10], headers=headers, tablefmt='grid'))
        else:
            self.stdout.write("No failed attempts found.")