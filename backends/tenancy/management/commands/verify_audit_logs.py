"""
Verify audit log integrity using SHA-256 checksums
"""
from django.core.management.base import BaseCommand
from django.db import connection
from backends.tenancy.db_router import set_current_db
from backends.tenancy.db_loader import study_db_manager


class Command(BaseCommand):
    help = 'Verify audit log integrity'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--study',
            type=str,
            help='Study code (e.g., 43EN)'
        )
        
        parser.add_argument(
            '--all',
            action='store_true',
            help='Verify all studies'
        )
        
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to fix invalid checksums (regenerate)'
        )
    
    def handle(self, *args, **options):
        if options['all']:
            self.verify_all_studies(options.get('fix', False))
        elif options['study']:
            self.verify_single_study(options['study'], options.get('fix', False))
        else:
            self.stdout.write(self.style.ERROR(
                "Please specify --study STUDY_CODE or --all"
            ))
    
    def verify_single_study(self, study_code: str, fix: bool = False):
        """Verify audit logs for a single study"""
        study_code = study_code.upper()
        db_name = f"db_study_{study_code.lower()}"
        
        self.stdout.write(f"\n🔍 Verifying audit logs for Study {study_code}")
        self.stdout.write("═" * 70)
        
        try:
            # Switch to study database
            set_current_db(db_name)
            study_db_manager.add_study_db(db_name)
            
            # Import models (must be after switching DB)
            from backends.studies.study_43en.models.audit_log import AuditLog
            from backends.studies.study_43en.utils.audit.integrity import IntegrityChecker
            
            # Get all audit logs
            total = AuditLog.objects.using(db_name).count()
            
            if total == 0:
                self.stdout.write(self.style.WARNING("No audit logs found."))
                return
            
            self.stdout.write(f"Checking {total} audit log(s)...\n")
            
            valid = 0
            invalid = []
            no_checksum = []
            fixed = 0
            
            # Verify each log
            for log in AuditLog.objects.using(db_name).all():
                if not log.checksum:
                    no_checksum.append(log.id)
                    continue
                
                is_valid = IntegrityChecker.verify_integrity(log)
                
                if is_valid:
                    valid += 1
                else:
                    invalid.append(log.id)
                    
                    # Fix if requested
                    if fix:
                        try:
                            # Rebuild old_data and new_data from details
                            details = log.details.all()
                            old_data = {d.field_name: d.old_value for d in details}
                            new_data = {d.field_name: d.new_value for d in details}
                            
                            audit_data = {
                                'user_id': log.user_id,
                                'username': log.username,
                                'action': log.action,
                                'model_name': log.model_name,
                                'patient_id': log.patient_id,
                                'timestamp': str(log.timestamp),
                                'old_data': old_data,
                                'new_data': new_data,
                                'reason': log.reason,
                            }
                            
                            # Regenerate checksum
                            new_checksum = IntegrityChecker.generate_checksum(audit_data)
                            log.checksum = new_checksum
                            log.save(update_fields=['checksum'])
                            
                            fixed += 1
                            self.stdout.write(self.style.WARNING(
                                f"  Fixed AuditLog {log.id}"
                            ))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(
                                f"  Failed to fix AuditLog {log.id}: {e}"
                            ))
            
            # Results
            self.stdout.write("\n" + "─" * 70)
            self.stdout.write("RESULTS:")
            self.stdout.write("─" * 70)
            self.stdout.write(f"Total:          {total}")
            self.stdout.write(self.style.SUCCESS(f"Valid:        {valid}"))
            
            if invalid:
                self.stdout.write(self.style.ERROR(
                    f"✗ Invalid:      {len(invalid)}"
                ))
                self.stdout.write(f"  IDs: {invalid[:20]}")
                if len(invalid) > 20:
                    self.stdout.write(f"  ... and {len(invalid) - 20} more")
            
            if no_checksum:
                self.stdout.write(self.style.WARNING(
                    f"⚠ No checksum:  {len(no_checksum)}"
                ))
                self.stdout.write(f"  IDs: {no_checksum[:20]}")
            
            if fix and fixed > 0:
                self.stdout.write(self.style.SUCCESS(
                    f"\nFixed {fixed} checksum(s)"
                ))
            
            # Overall status
            if len(invalid) == 0 and len(no_checksum) == 0:
                self.stdout.write("\n" + self.style.SUCCESS(
                    "═" * 70 + "\n"
                    "ALL AUDIT LOGS ARE VALID\n"
                    "═" * 70
                ))
            else:
                self.stdout.write("\n" + self.style.ERROR(
                    "═" * 70 + "\n"
                    "⚠ INTEGRITY ISSUES DETECTED\n"
                    "═" * 70
                ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"\nError verifying audit logs: {e}"
            ))
            import traceback
            traceback.print_exc()
        finally:
            # Reset to default database
            set_current_db('default')
    
    def verify_all_studies(self, fix: bool = False):
        """Verify audit logs for all studies"""
        from backends.tenancy.models import Study
        
        studies = Study.objects.filter(
            status__in=[Study.Status.ACTIVE, Study.Status.PLANNING]
        )
        
        self.stdout.write(f"\n🔍 Verifying audit logs for {studies.count()} study/studies")
        self.stdout.write("═" * 70)
        
        for study in studies:
            self.verify_single_study(study.code, fix)
            self.stdout.write("\n")