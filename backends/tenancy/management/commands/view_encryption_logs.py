"""
View Encryption Audit Logs

Display and analyze encryption/decryption operations
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from backends.tenancy.models import EncryptionAuditLog, User


class Command(BaseCommand):
    help = 'View and analyze encryption audit logs'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['ENCRYPT', 'DECRYPT', 'VERIFY', 'KEY_GEN', 'KEY_ROTATE', 'ALL'],
            default='ALL',
            help='Filter by action type'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Filter by username'
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Show logs from last N hours (default: 24)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Max number of logs to show (default: 50)'
        )
        parser.add_argument(
            '--failed-only',
            action='store_true',
            help='Show only failed operations'
        )
        parser.add_argument(
            '--invalid-signature',
            action='store_true',
            help='Show only invalid signatures'
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show statistics only'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        username = options.get('user')
        hours = options['hours']
        limit = options['limit']
        failed_only = options['failed_only']
        invalid_signature = options['invalid_signature']
        show_stats = options['stats']
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('ENCRYPTION AUDIT LOGS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # Build query
        cutoff = timezone.now() - timedelta(hours=hours)
        logs = EncryptionAuditLog.objects.filter(timestamp__gte=cutoff)
        
        if action != 'ALL':
            logs = logs.filter(action=action)
        
        if username:
            try:
                user = User.objects.get(username=username)
                logs = logs.filter(user=user)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User "{username}" not found'))
                return
        
        if failed_only:
            logs = logs.filter(success=False)
        
        if invalid_signature:
            logs = logs.filter(signature_valid=False)
        
        total_count = logs.count()
        
        # Show statistics
        self.stdout.write(f'\n📊 Statistics (last {hours} hours):')
        self.stdout.write('─' * 70)
        
        stats = {
            'total': total_count,
            'encrypt': logs.filter(action='ENCRYPT').count(),
            'decrypt': logs.filter(action='DECRYPT').count(),
            'verify': logs.filter(action='VERIFY').count(),
            'key_gen': logs.filter(action='KEY_GEN').count(),
            'key_rotate': logs.filter(action='KEY_ROTATE').count(),
            'success': logs.filter(success=True).count(),
            'failed': logs.filter(success=False).count(),
            'valid_sig': logs.filter(signature_valid=True).count(),
            'invalid_sig': logs.filter(signature_valid=False).count(),
        }
        
        self.stdout.write(f'Total operations:     {stats["total"]}')
        self.stdout.write('')
        self.stdout.write('By action:')
        self.stdout.write(f'  ENCRYPT:            {stats["encrypt"]}')
        self.stdout.write(f'  DECRYPT:            {stats["decrypt"]}')
        self.stdout.write(f'  VERIFY:             {stats["verify"]}')
        self.stdout.write(f'  KEY_GEN:            {stats["key_gen"]}')
        self.stdout.write(f'  KEY_ROTATE:         {stats["key_rotate"]}')
        self.stdout.write('')
        self.stdout.write('By status:')
        self.stdout.write(self.style.SUCCESS(f'  ✓ Success:          {stats["success"]}'))
        if stats['failed'] > 0:
            self.stdout.write(self.style.ERROR(f'  ✗ Failed:           {stats["failed"]}'))
        self.stdout.write('')
        self.stdout.write('Signatures:')
        self.stdout.write(self.style.SUCCESS(f'  ✓ Valid:            {stats["valid_sig"]}'))
        if stats['invalid_sig'] > 0:
            self.stdout.write(self.style.ERROR(f'  ✗ Invalid:          {stats["invalid_sig"]}'))
        
        # Show top users
        top_users = logs.values('user__username').annotate(
            count=models.Count('id')
        ).order_by('-count')[:5]
        
        if top_users:
            self.stdout.write('')
            self.stdout.write('Top users:')
            for item in top_users:
                username = item['user__username'] or 'System'
                self.stdout.write(f'  {username}: {item["count"]} operations')
        
        if show_stats:
            return
        
        # Show detailed logs
        self.stdout.write('')
        self.stdout.write('─' * 70)
        self.stdout.write(f'Recent logs (showing {min(limit, total_count)} of {total_count}):')
        self.stdout.write('─' * 70)
        
        if total_count == 0:
            self.stdout.write(self.style.WARNING('\nNo logs found.'))
            return
        
        for log in logs[:limit]:
            self._display_log(log)
        
        if total_count > limit:
            self.stdout.write(f'\n... and {total_count - limit} more')
            self.stdout.write(f'Use --limit {total_count} to see all')
    
    def _display_log(self, log):
        """Display a single log entry"""
        # Timestamp
        time_str = log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        # Action icon
        action_icons = {
            'ENCRYPT': '🔐',
            'DECRYPT': '🔓',
            'VERIFY': '✅',
            'KEY_GEN': '🔑',
            'KEY_ROTATE': '🔄',
        }
        icon = action_icons.get(log.action, '📝')
        
        # Status
        if not log.success:
            status = self.style.ERROR('✗ FAILED')
        elif log.signature_valid is False:
            status = self.style.ERROR('✗ INVALID SIG')
        elif log.signature_valid is True:
            status = self.style.SUCCESS('✓ VALID')
        else:
            status = self.style.SUCCESS('✓ OK')
        
        # User
        user_str = log.user.username if log.user else 'System'
        
        # Output
        self.stdout.write(f'\n{icon} {time_str} | {log.action:<10} | {user_str:<15} | {status}')
        
        # File
        if log.backup_file:
            self.stdout.write(f'   File: {log.backup_file}')
        
        # Creator
        if log.backup_creator and log.backup_creator != log.user:
            self.stdout.write(f'   Creator: {log.backup_creator.username}')
        
        # IP address
        if log.ip_address:
            self.stdout.write(f'   IP: {log.ip_address}')
        
        # Error details
        if not log.success and log.details:
            error = log.details.get('error', 'Unknown error')
            self.stdout.write(self.style.ERROR(f'   Error: {error}'))


# Import for aggregation
from django.db import models
