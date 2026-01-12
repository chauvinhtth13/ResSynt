# backends/audit_logs/management/commands/verify_audit_integrity.py
"""
Management command to verify integrity of audit log records.

This command checks HMAC checksums to detect any tampering with audit logs.

Usage:
    python manage.py verify_audit_integrity --database db_study_43en
    python manage.py verify_audit_integrity --database db_study_43en --fix
    python manage.py verify_audit_integrity --all-studies
"""
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Verify integrity of audit log records using HMAC checksums'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--database',
            type=str,
            help='Specific study database alias (e.g., db_study_43en)',
        )
        parser.add_argument(
            '--all-studies',
            action='store_true',
            help='Verify all study databases',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to check (default: 30)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=1000,
            help='Maximum number of records to check per database (default: 1000)',
        )
        parser.add_argument(
            '--mark-invalid',
            action='store_true',
            help='Mark invalid records with is_verified=False',
        )
    
    def handle(self, *args, **options):
        if options['all_studies']:
            databases = self._get_all_study_databases()
        elif options['database']:
            databases = [options['database']]
        else:
            raise CommandError(
                'You must specify either --database or --all-studies'
            )
        
        if not databases:
            self.stdout.write(
                self.style.WARNING('No study databases found.')
            )
            return
        
        total_valid = 0
        total_invalid = 0
        
        for db_alias in databases:
            valid, invalid = self._verify_database(
                db_alias,
                days=options['days'],
                limit=options['limit'],
                mark_invalid=options['mark_invalid'],
            )
            total_valid += valid
            total_invalid += invalid
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write('VERIFICATION SUMMARY')
        self.stdout.write('='*60)
        self.stdout.write(f'Total valid records:   {total_valid}')
        self.stdout.write(f'Total invalid records: {total_invalid}')
        
        if total_invalid > 0:
            self.stdout.write(
                self.style.ERROR(
                    f'\n⚠️  ALERT: {total_invalid} audit log(s) may have been tampered!'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\n✓ All checked records have valid checksums.')
            )
    
    def _get_all_study_databases(self):
        """Get all study database aliases from settings."""
        study_prefix = getattr(settings, 'STUDY_DB_PREFIX', 'db_study_')
        databases = []
        
        for db_alias in connections.databases.keys():
            if db_alias.startswith(study_prefix):
                databases.append(db_alias)
        
        return databases
    
    def _verify_database(self, db_alias, days, limit, mark_invalid):
        """Verify audit logs in a specific database."""
        self.stdout.write(f'\n{"="*50}')
        self.stdout.write(f'Verifying: {db_alias}')
        self.stdout.write(f'{"="*50}')
        
        # Extract study code from db_alias (e.g., 'db_study_43en' -> 'study_43en')
        study_prefix = getattr(settings, 'STUDY_DB_PREFIX', 'db_study_')
        study_code = db_alias.replace(study_prefix.rstrip('_'), '').lstrip('_')
        
        try:
            # Import audit models for this study
            from backends.audit_logs.models import get_audit_models
            models = get_audit_models(study_code)
            
            if not models:
                self.stdout.write(
                    self.style.WARNING(
                        f'Audit models not found for {study_code}. '
                        'Make sure study app is loaded.'
                    )
                )
                return 0, 0
            
            AuditLog, AuditLogDetail = models
            
            # Query recent audit logs
            cutoff_date = timezone.now() - timedelta(days=days)
            audit_logs = AuditLog.objects.using(db_alias).filter(
                timestamp__gte=cutoff_date
            ).prefetch_related('details').order_by('-timestamp')[:limit]
            
            valid_count = 0
            invalid_count = 0
            
            for audit_log in audit_logs:
                is_valid = audit_log.verify_integrity()
                
                if is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'  INVALID: ID={audit_log.id} '
                            f'User={audit_log.username} '
                            f'Action={audit_log.action} '
                            f'Time={audit_log.timestamp}'
                        )
                    )
                    
                    if mark_invalid:
                        # Update is_verified flag (requires admin override)
                        AuditLog.objects.using(db_alias).filter(
                            pk=audit_log.pk
                        ).update(is_verified=False)
                        self.stdout.write('    → Marked as invalid')
            
            self.stdout.write(
                f'\nResults: {valid_count} valid, {invalid_count} invalid '
                f'(out of {valid_count + invalid_count} checked)'
            )
            
            return valid_count, invalid_count
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error verifying {db_alias}: {e}')
            )
            logger.exception(f'Verification error for {db_alias}')
            return 0, 0
