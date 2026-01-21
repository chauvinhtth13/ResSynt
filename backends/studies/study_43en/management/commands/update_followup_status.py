from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from django.core.management.base import BaseCommand
from django.db.models import Q
from datetime import datetime, timedelta
from backends.studies.study_43en.models.schedule import (
    FollowUpStatus, ExpectedDates, ContactExpectedDates,
)
from backends.studies.study_43en.models.patient import SCR_CASE, ENR_CASE,FU_CASE_28, FU_CASE_90,SAM_CASE
from backends.studies.study_43en.models.contact import ENR_CONTACT, FU_CONTACT_28, FU_CONTACT_90


class Command(BaseCommand):
    help = 'Cập nhật bảng FollowUpStatus từ dữ liệu hiện có'

    def handle(self, *args, **options):
        self.stdout.write('🚀 Bắt đầu cập nhật FollowUpStatus...')
        
        if options.get('reset', False):
            deleted = FollowUpStatus.objects.using('db_study_43en').all().delete()
            self.stdout.write(f'🗑️  Đã xóa {deleted[0]} records cũ')
        
        self.update_patient_statuses()
        self.update_contact_statuses()
        self.update_all_statuses()
        
        self.stdout.write(self.style.SUCCESS(' Hoàn thành cập nhật FollowUpStatus!'))
    
    def update_patient_statuses(self):
        """Cập nhật dữ liệu theo dõi từ bệnh nhân"""
        count = 0
        expected_dates = ExpectedDates.objects.using('db_study_43en').select_related('USUBJID').all()
        
        for expected in expected_dates:
            patient = expected.USUBJID
            
            #  Get INITIAL and PHONE - ONLY if they have values
            try:
                screening = patient.USUBJID
                initial = screening.INITIAL if screening and screening.INITIAL else ''
            except:
                initial = ''
            
            #  CRITICAL: Only get phone if it exists, otherwise use existing value
            try:
                phone = patient.PHONE if patient.PHONE else None
            except:
                phone = None
            
            #  Check V2 (Sample) - Get EARLIEST date
            try:
                sample_v2 = SAM_CASE.objects.using('db_study_43en').get(USUBJID=patient, SAMPLE_TYPE='2')
                
                if sample_v2.SAMPLE:
                    sample_dates = [
                        sample_v2.STOOLDATE,
                        sample_v2.RECTSWABDATE,
                        sample_v2.THROATSWABDATE,
                        sample_v2.BLOODDATE
                    ]
                    valid_dates = [d for d in sample_dates if d is not None]
                    v2_actual_date = min(valid_dates) if valid_dates else None
                    v2_status = 'COMPLETED' if v2_actual_date else None
                else:
                    v2_actual_date = None
                    v2_status = None
                    
            except SAM_CASE.DoesNotExist:
                v2_actual_date = None
                v2_status = None
            
            # Check V3
            try:
                followup_v3 = FU_CASE_28.objects.using('db_study_43en').get(USUBJID=patient)
                v3_actual_date = followup_v3.EvaluateDate if followup_v3.EvaluatedAtDay28 == 'Yes' else None
                v3_status = 'COMPLETED' if followup_v3.EvaluatedAtDay28 == 'Yes' else None
            except FU_CASE_28.DoesNotExist:
                v3_actual_date = None
                v3_status = None
            
            # Check V4
            try:
                followup_v4 = FU_CASE_90.objects.using('db_study_43en').get(USUBJID=patient)
                v4_actual_date = followup_v4.EvaluateDate if followup_v4.EvaluatedAtDay90 == 'Yes' else None
                v4_status = 'COMPLETED' if followup_v4.EvaluatedAtDay90 == 'Yes' else None
            except FU_CASE_90.DoesNotExist:
                v4_actual_date = None
                v4_status = None
            
            #  Update V2 - Only update phone if new value exists
            if expected.V2_EXPECTED_DATE:
                status_data = {
                    'INITIAL': initial,
                    'EXPECTED_FROM': expected.V2_EXPECTED_FROM,
                    'EXPECTED_TO': expected.V2_EXPECTED_TO,
                    'EXPECTED_DATE': expected.V2_EXPECTED_DATE,
                    'ACTUAL_DATE': v2_actual_date,
                }
                #  Only update PHONE if we have a new value
                if phone:
                    status_data['PHONE'] = phone
                
                if v2_status:
                    status_data['STATUS'] = v2_status
                
                FollowUpStatus.objects.using('db_study_43en').update_or_create(
                    USUBJID=patient.USUBJID_id,
                    SUBJECT_TYPE='PATIENT',
                    VISIT='V2',
                    defaults=status_data
                )
                count += 1
            
            #  Update V3 - Only update phone if new value exists
            if expected.V3_EXPECTED_DATE:
                status_data = {
                    'INITIAL': initial,
                    'EXPECTED_FROM': expected.V3_EXPECTED_FROM,
                    'EXPECTED_TO': expected.V3_EXPECTED_TO,
                    'EXPECTED_DATE': expected.V3_EXPECTED_DATE,
                    'ACTUAL_DATE': v3_actual_date,
                }
                if phone:
                    status_data['PHONE'] = phone
                
                if v3_status:
                    status_data['STATUS'] = v3_status
                
                FollowUpStatus.objects.using('db_study_43en').update_or_create(
                    USUBJID=patient.USUBJID_id,
                    SUBJECT_TYPE='PATIENT',
                    VISIT='V3',
                    defaults=status_data
                )
                count += 1
            
            #  Update V4 - Only update phone if new value exists
            if expected.V4_EXPECTED_DATE:
                status_data = {
                    'INITIAL': initial,
                    'EXPECTED_FROM': expected.V4_EXPECTED_FROM,
                    'EXPECTED_TO': expected.V4_EXPECTED_TO,
                    'EXPECTED_DATE': expected.V4_EXPECTED_DATE,
                    'ACTUAL_DATE': v4_actual_date,
                }
                if phone:
                    status_data['PHONE'] = phone
                
                if v4_status:
                    status_data['STATUS'] = v4_status
                
                FollowUpStatus.objects.using('db_study_43en').update_or_create(
                    USUBJID=patient.USUBJID_id,
                    SUBJECT_TYPE='PATIENT',
                    VISIT='V4',
                    defaults=status_data
                )
                count += 1
        
        self.stdout.write(f'📋 Đã cập nhật {count} mục theo dõi cho bệnh nhân')
    
    def update_contact_statuses(self):
        """Cập nhật dữ liệu theo dõi từ người tiếp xúc"""
        count = 0
        expected_dates = ContactExpectedDates.objects.using('db_study_43en').select_related('USUBJID').all()
        
        for expected in expected_dates:
            contact = expected.USUBJID
            
            #  Get INITIAL and PHONE - ONLY if they have values
            try:
                screening = contact.USUBJID
                initial = screening.INITIAL if screening and screening.INITIAL else ''
            except:
                initial = ''
            
            #  CRITICAL: Only get phone if it exists
            try:
                phone = contact.PHONE if contact.PHONE else None
            except:
                phone = None
            
            # Check V2
            try:
                followup_v2 = FU_CONTACT_28.objects.using('db_study_43en').get(USUBJID=contact)
                v2_actual_date = followup_v2.ASSESSDATE if followup_v2.ASSESSED == 'Yes' else None
                v2_status = 'COMPLETED' if followup_v2.ASSESSED == 'Yes' else None
            except FU_CONTACT_28.DoesNotExist:
                v2_actual_date = None
                v2_status = None
            
            # Check V3
            try:
                followup_v3 = FU_CONTACT_90.objects.using('db_study_43en').get(USUBJID=contact)
                v3_actual_date = followup_v3.ASSESSDATE if followup_v3.ASSESSED == 'Yes' else None
                v3_status = 'COMPLETED' if followup_v3.ASSESSED == 'Yes' else None
            except FU_CONTACT_90.DoesNotExist:
                v3_actual_date = None
                v3_status = None
            
            #  Update V2 - Only update phone if new value exists
            if expected.V2_EXPECTED_DATE:
                status_data = {
                    'INITIAL': initial,
                    'EXPECTED_FROM': expected.V2_EXPECTED_FROM,
                    'EXPECTED_TO': expected.V2_EXPECTED_TO,
                    'EXPECTED_DATE': expected.V2_EXPECTED_DATE,
                    'ACTUAL_DATE': v2_actual_date,
                }
                if phone:
                    status_data['PHONE'] = phone
                
                if v2_status:
                    status_data['STATUS'] = v2_status
                
                FollowUpStatus.objects.using('db_study_43en').update_or_create(
                    USUBJID=contact.USUBJID_id,
                    SUBJECT_TYPE='CONTACT',
                    VISIT='V2',
                    defaults=status_data
                )
                count += 1
            
            #  Update V3 - Only update phone if new value exists
            if expected.V3_EXPECTED_DATE:
                status_data = {
                    'INITIAL': initial,
                    'EXPECTED_FROM': expected.V3_EXPECTED_FROM,
                    'EXPECTED_TO': expected.V3_EXPECTED_TO,
                    'EXPECTED_DATE': expected.V3_EXPECTED_DATE,
                    'ACTUAL_DATE': v3_actual_date,
                }
                if phone:
                    status_data['PHONE'] = phone
                
                if v3_status:
                    status_data['STATUS'] = v3_status
                
                FollowUpStatus.objects.using('db_study_43en').update_or_create(
                    USUBJID=contact.USUBJID_id,
                    SUBJECT_TYPE='CONTACT',
                    VISIT='V3',
                    defaults=status_data
                )
                count += 1
        
        self.stdout.write(f'📋 Đã cập nhật {count} mục theo dõi cho người tiếp xúc')
    
    def update_all_statuses(self):
        """
         FIXED: Re-evaluate MISSED → LATE if no MISSED_DATE
        Only truly MISSED records have MISSED_DATE set manually
        """
        today = date.today()
        updated_count = 0
        
        #  Only exclude COMPLETED (truly final state)
        # Re-check all MISSED/LATE/UPCOMING records
        followups = FollowUpStatus.objects.using('db_study_43en').exclude(
            STATUS='COMPLETED'
        )
        
        for followup in followups:
            old_status = followup.STATUS
            
            # Priority 1: Has ACTUAL_DATE → COMPLETED (final)
            if followup.ACTUAL_DATE:
                followup.STATUS = 'COMPLETED'
            
            # Priority 2: Has MISSED_DATE (manual) → MISSED (final)
            elif followup.MISSED_DATE:
                followup.STATUS = 'MISSED'
            
            # Priority 3: Past EXPECTED_TO → LATE
            elif followup.EXPECTED_TO and today > followup.EXPECTED_TO:
                followup.STATUS = 'LATE'
            
            # Priority 4: Past EXPECTED_DATE → LATE
            elif followup.EXPECTED_DATE and today > followup.EXPECTED_DATE:
                followup.STATUS = 'LATE'
            
            # Priority 5: Within/approaching window → UPCOMING
            else:
                followup.STATUS = 'UPCOMING'
            
            # Save if changed
            if followup.STATUS != old_status:
                followup.save(using='db_study_43en', update_fields=['STATUS'])
                updated_count += 1
                self.stdout.write(f'  {followup.USUBJID} {followup.VISIT}: {old_status} → {followup.STATUS}')
        
        self.stdout.write(f' Đã cập nhật {updated_count} trạng thái')

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Xóa tất cả dữ liệu trước khi cập nhật',
        )