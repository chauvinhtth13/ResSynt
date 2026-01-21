# backends/studies/study_43en/management/commands/sync_expected_dates.py
"""
Sync Expected Dates from ENR_CASE and ExpectedCalendar

Flow:
1. Get all enrolled patients (ENR_CASE) and contacts (ENR_CONTACT)
2. For each, find matching ENROLLMENT_DATE in ExpectedCalendar
3. Create/update ExpectedDates and ContactExpectedDates records
"""

from django.core.management.base import BaseCommand
from datetime import date

from backends.studies.study_43en.models.patient import ENR_CASE
from backends.studies.study_43en.models.contact import ENR_CONTACT
from backends.studies.study_43en.models.schedule import (
    ExpectedDates, ContactExpectedDates, ExpectedCalendar
)

STUDY_DATABASE = 'db_study_43en'


class Command(BaseCommand):
    help = 'Sync expected dates from ENR_CASE/ENR_CONTACT enrollment dates using ExpectedCalendar'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete all existing ExpectedDates and ContactExpectedDates before syncing',
        )

    def handle(self, *args, **options):
        self.stdout.write('🚀 Bắt đầu đồng bộ Expected Dates...')
        
        if options.get('reset', False):
            deleted_patient = ExpectedDates.objects.using(STUDY_DATABASE).all().delete()
            deleted_contact = ContactExpectedDates.objects.using(STUDY_DATABASE).all().delete()
            self.stdout.write(f'🗑️  Đã xóa {deleted_patient[0]} ExpectedDates và {deleted_contact[0]} ContactExpectedDates')
        
        # Sync patients
        patient_count = self._sync_patient_expected_dates()
        
        # Sync contacts
        contact_count = self._sync_contact_expected_dates()
        
        self.stdout.write(self.style.SUCCESS(
            f'✅ Hoàn thành! Đã đồng bộ {patient_count} bệnh nhân và {contact_count} người tiếp xúc'
        ))

    def _sync_patient_expected_dates(self):
        """Sync ExpectedDates from ENR_CASE"""
        self.stdout.write('📋 Đang đồng bộ Expected Dates cho bệnh nhân...')
        
        # Get all enrolled patients with enrollment date
        enrollments = ENR_CASE.objects.using(STUDY_DATABASE).select_related(
            'USUBJID'  # SCR_CASE
        ).filter(ENRDATE__isnull=False)
        
        # Statistics by site
        site_stats = {}
        count = 0
        created_count = 0
        updated_count = 0
        no_calendar_count = 0
        missing_dates = []
        
        for enr in enrollments:
            enrollment_date = enr.ENRDATE
            
            # Get site ID from USUBJID
            try:
                site_id = enr.USUBJID.SITEID if enr.USUBJID else 'Unknown'
            except:
                site_id = 'Unknown'
            
            # Initialize site stats
            if site_id not in site_stats:
                site_stats[site_id] = {'total': 0, 'success': 0, 'no_calendar': 0}
            site_stats[site_id]['total'] += 1
            
            # Find matching calendar entry
            calendar = ExpectedCalendar.objects.using(STUDY_DATABASE).filter(
                ENROLLMENT_DATE=enrollment_date
            ).first()
            
            if not calendar:
                self.stdout.write(self.style.WARNING(
                    f'   {enr.USUBJID_id} (Site {site_id}): Không tìm thấy lịch cho ngày {enrollment_date}'
                ))
                no_calendar_count += 1
                site_stats[site_id]['no_calendar'] += 1
                if enrollment_date not in missing_dates:
                    missing_dates.append(enrollment_date)
                continue
            
            # Create or update ExpectedDates
            expected, created = ExpectedDates.objects.using(STUDY_DATABASE).update_or_create(
                USUBJID=enr,
                defaults={
                    'ENROLLMENT_DATE': enrollment_date,
                    'V2_EXPECTED_FROM': calendar.V2_EXPECTED_FROM,
                    'V2_EXPECTED_TO': calendar.V2_EXPECTED_TO,
                    'V2_EXPECTED_DATE': calendar.V2_EXPECTED_DATE,
                    'V3_EXPECTED_FROM': calendar.V3_EXPECTED_FROM,
                    'V3_EXPECTED_TO': calendar.V3_EXPECTED_TO,
                    'V3_EXPECTED_DATE': calendar.V3_EXPECTED_DATE,
                    'V4_EXPECTED_FROM': calendar.V4_EXPECTED_FROM,
                    'V4_EXPECTED_TO': calendar.V4_EXPECTED_TO,
                    'V4_EXPECTED_DATE': calendar.V4_EXPECTED_DATE,
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
            
            site_stats[site_id]['success'] += 1
            count += 1
        
        # Print summary
        self.stdout.write(
            f'  ✅ Bệnh nhân: {count} (mới: {created_count}, cập nhật: {updated_count})'
        )
        
        # Print site-based statistics
        self.stdout.write('\n  📊 Thống kê theo Site:')
        for site_id, stats in sorted(site_stats.items()):
            self.stdout.write(
                f'     Site {site_id}: {stats["success"]}/{stats["total"]} thành công, '
                f'{stats["no_calendar"]} thiếu lịch'
            )
        
        if no_calendar_count > 0:
            self.stdout.write(self.style.WARNING(
                f'\n   {no_calendar_count} bệnh nhân không có lịch trong ExpectedCalendar'
            ))
            if missing_dates:
                self.stdout.write(self.style.WARNING(
                    f'  📅 Các ngày enrollment chưa có trong ExpectedCalendar:'
                ))
                for d in sorted(missing_dates)[:10]:  # Show first 10
                    self.stdout.write(self.style.WARNING(f'      - {d}'))
                if len(missing_dates) > 10:
                    self.stdout.write(self.style.WARNING(f'      ... và {len(missing_dates) - 10} ngày khác'))
        
        return count

    def _sync_contact_expected_dates(self):
        """Sync ContactExpectedDates from ENR_CONTACT"""
        self.stdout.write('📋 Đang đồng bộ Expected Dates cho người tiếp xúc...')
        
        # Get all enrolled contacts with enrollment date
        enrollments = ENR_CONTACT.objects.using(STUDY_DATABASE).select_related(
            'USUBJID'  # SCR_CONTACT
        ).filter(ENRDATE__isnull=False)
        
        count = 0
        created_count = 0
        updated_count = 0
        no_calendar_count = 0
        
        for enr in enrollments:
            enrollment_date = enr.ENRDATE
            
            # Find matching calendar entry
            calendar = ExpectedCalendar.objects.using(STUDY_DATABASE).filter(
                ENROLLMENT_DATE=enrollment_date
            ).first()
            
            if not calendar:
                self.stdout.write(self.style.WARNING(
                    f'   {enr.USUBJID_id}: Không tìm thấy lịch cho ngày {enrollment_date}'
                ))
                no_calendar_count += 1
                continue
            
            # Create or update ContactExpectedDates
            # Note: Contacts only have V2 and V3, no V4
            expected, created = ContactExpectedDates.objects.using(STUDY_DATABASE).update_or_create(
                USUBJID=enr,
                defaults={
                    'ENROLLMENT_DATE': enrollment_date,
                    'V2_EXPECTED_FROM': calendar.V3_EXPECTED_FROM,  # Contact V2 = Patient V3 (28-day)
                    'V2_EXPECTED_TO': calendar.V3_EXPECTED_TO,
                    'V2_EXPECTED_DATE': calendar.V3_EXPECTED_DATE,
                    'V3_EXPECTED_FROM': calendar.V4_EXPECTED_FROM,  # Contact V3 = Patient V4 (90-day)
                    'V3_EXPECTED_TO': calendar.V4_EXPECTED_TO,
                    'V3_EXPECTED_DATE': calendar.V4_EXPECTED_DATE,
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
            
            count += 1
        
        self.stdout.write(
            f'  ✅ Người tiếp xúc: {count} (mới: {created_count}, cập nhật: {updated_count})'
        )
        if no_calendar_count > 0:
            self.stdout.write(self.style.WARNING(
                f'   {no_calendar_count} người tiếp xúc không có lịch trong ExpectedCalendar'
            ))
        
        return count
