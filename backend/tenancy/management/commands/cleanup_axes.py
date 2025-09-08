from django.core.management.base import BaseCommand
from axes.models import AccessAttempt, AccessLog
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Clean up old Axes access attempts and logs'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete records older than this many days'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Delete old access attempts
        attempts_deleted = AccessAttempt.objects.filter(
            attempt_time__lt=cutoff_date
        ).delete()[0]
        
        # Delete old access logs
        logs_deleted = AccessLog.objects.filter(
            attempt_time__lt=cutoff_date
        ).delete()[0]
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Deleted {attempts_deleted} access attempts and '
                f'{logs_deleted} access logs older than {days} days'
            )
        )