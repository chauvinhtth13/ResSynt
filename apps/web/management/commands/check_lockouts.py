from django.core.management.base import BaseCommand
from axes.models import AccessAttempt
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Check and manage login lockouts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-ip',
            type=str,
            help='Clear lockout for specific IP',
        )
        parser.add_argument(
            '--clear-user',
            type=str,
            help='Clear lockout for specific username',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all current lockouts',
        )

    def handle(self, *args, **options):
        if options['clear_ip']:
            AccessAttempt.objects.filter(ip_address=options['clear_ip']).delete()
            self.stdout.write(f"Cleared lockout for IP: {options['clear_ip']}")
        
        elif options['clear_user']:
            AccessAttempt.objects.filter(username=options['clear_user']).delete()
            self.stdout.write(f"Cleared lockout for user: {options['clear_user']}")
        
        elif options['list']:
            recent = timezone.now() - timedelta(hours=24)
            attempts = AccessAttempt.objects.filter(
                attempt_time__gte=recent
            ).order_by('-failures_since_start')
            
            for attempt in attempts:
                self.stdout.write(
                    f"IP: {attempt.ip_address} | "
                    f"User: {attempt.username} | "
                    f"Failures: {attempt.failures_since_start} | "
                    f"Last: {attempt.attempt_time}"
                )