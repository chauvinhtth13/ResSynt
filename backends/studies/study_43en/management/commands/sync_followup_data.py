# management/commands/sync_followup_status.py

from django.core.management.base import BaseCommand
from django.db.models import Q
from datetime import datetime, timedelta
from study_43en.models import (
    FollowUpStatus, ExpectedDates, ContactExpectedDates,
    FU_CASE_28, FU_CASE_90, FU_CONTACT_28, FU_CONTACT_90,
    SAM_CASE, ENR_CASE, ENR_CONTACT, SCR_CASE
)


class Command(BaseCommand):
    help = 'Đồng bộ dữ liệu từ các model liên quan về FollowUpStatus'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Xóa tất cả bản ghi FollowUpStatus trước khi đồng bộ')
        parser.add_argument('--force-initial', action='store_true', help='Cập nhật lại trường INITIAL cho tất cả bản ghi')

    def handle(self, *args, **kwargs):
        reset = kwargs.get('reset', False)
        force_initial = kwargs.get('force_initial', False)
        
        if reset:
            self.stdout.write(self.style.WARNING('Đang xóa tất cả bản ghi FollowUpStatus...'))
            FollowUpStatus.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Đã xóa tất cả bản ghi FollowUpStatus'))
        
        if force_initial and not reset:
            self._update_initials()
            self.stdout.write(self.style.SUCCESS('Đã cập nhật lại trường INITIAL cho tất cả bản ghi'))
            return
        
        self._sync_from_patients()
        self._sync_from_contacts()
        self._update_status_based_on_date()
        
        self.stdout.write(self.style.SUCCESS('Đã hoàn thành đồng bộ dữ liệu'))

    def _sync_from_patients(self):
        """ UPDATED: Sync PHONE from ENR_CASE"""
        self.stdout.write('Đang đồng bộ dữ liệu từ bệnh nhân...')
        
        expected_dates = ExpectedDates.objects.using('db_study_43en').all()
        count = 0
        
        for ed in expected_dates:
            initial = ''
            phone = ''
            
            try:
                enrollment = ed.USUBJID  # ENR_CASE
                screening_case = enrollment.USUBJID  # SCR_CASE through ENR_CASE
                
                #  Get INITIAL from SCR_CASE
                initial = screening_case.INITIAL if screening_case else ''
                
                #  Get PHONE from ENR_CASE (not SCR_CASE!)
                phone = enrollment.PHONE if hasattr(enrollment, 'PHONE') and enrollment.PHONE else ''
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Lỗi khi lấy thông tin bệnh nhân {ed.USUBJID_id}: {str(e)}'))
            
            # V2 (Sample)
            if ed.V2_EXPECTED_DATE:
                followup, created = FollowUpStatus.objects.using('db_study_43en').update_or_create(
                    USUBJID=ed.USUBJID_id,
                    SUBJECT_TYPE='PATIENT',
                    VISIT='V2',
                    defaults={
                        'INITIAL': initial,
                        'PHONE': phone,  #  From ENR_CASE
                        'EXPECTED_DATE': ed.V2_EXPECTED_DATE,
                        'EXPECTED_FROM': ed.V2_EXPECTED_FROM,
                        'EXPECTED_TO': ed.V2_EXPECTED_TO,
                        'STATUS': 'UPCOMING'
                    }
                )
                if created:
                    count += 1
            
            # V3
            if ed.V3_EXPECTED_DATE:
                try:
                    fu_case = FU_CASE_28.objects.using('db_study_43en').get(USUBJID=ed.USUBJID)
                    actual_date = fu_case.EvaluateDate
                    status = 'COMPLETED' if fu_case.EvaluatedAtDay28 == 'Yes' else 'MISSED'
                except FU_CASE_28.DoesNotExist:
                    actual_date = None
                    status = 'UPCOMING'
                
                followup, created = FollowUpStatus.objects.using('db_study_43en').update_or_create(
                    USUBJID=ed.USUBJID_id,
                    SUBJECT_TYPE='PATIENT',
                    VISIT='V3',
                    defaults={
                        'INITIAL': initial,
                        'PHONE': phone,  #  From ENR_CASE
                        'EXPECTED_DATE': ed.V3_EXPECTED_DATE,
                        'EXPECTED_FROM': ed.V3_EXPECTED_FROM,
                        'EXPECTED_TO': ed.V3_EXPECTED_TO,
                        'ACTUAL_DATE': actual_date,
                        'STATUS': status
                    }
                )
                if created:
                    count += 1
            
            # V4
            if ed.V4_EXPECTED_DATE:
                try:
                    fu_case = FU_CASE_90.objects.using('db_study_43en').get(USUBJID=ed.USUBJID)
                    actual_date = fu_case.EvaluateDate
                    status = 'COMPLETED' if fu_case.EvaluatedAtDay90 == 'Yes' else 'MISSED'
                except FU_CASE_90.DoesNotExist:
                    actual_date = None
                    status = 'UPCOMING'
                
                followup, created = FollowUpStatus.objects.using('db_study_43en').update_or_create(
                    USUBJID=ed.USUBJID_id,
                    SUBJECT_TYPE='PATIENT',
                    VISIT='V4',
                    defaults={
                        'INITIAL': initial,
                        'PHONE': phone,  #  From ENR_CASE
                        'EXPECTED_DATE': ed.V4_EXPECTED_DATE,
                        'EXPECTED_FROM': ed.V4_EXPECTED_FROM,
                        'EXPECTED_TO': ed.V4_EXPECTED_TO,
                        'ACTUAL_DATE': actual_date,
                        'STATUS': status
                    }
                )
                if created:
                    count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Đã đồng bộ {count} lịch hẹn từ bệnh nhân'))


    def _sync_from_contacts(self):
        """ UPDATED: Sync PHONE from ENR_CONTACT"""
        self.stdout.write('Đang đồng bộ dữ liệu từ người tiếp xúc...')
        
        contact_expected_dates = ContactExpectedDates.objects.using('db_study_43en').all()
        count = 0
        
        for ed in contact_expected_dates:
            try:
                enrollment = ed.USUBJID  # ENR_CONTACT
                screening_contact = enrollment.USUBJID  # SCR_CONTACT
                
                #  Get INITIAL from SCR_CONTACT
                initial = screening_contact.INITIAL if screening_contact else ''
                
                #  Get PHONE from ENR_CONTACT (not SCR_CONTACT!)
                phone = enrollment.PHONE if hasattr(enrollment, 'PHONE') and enrollment.PHONE else ''
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Lỗi: {str(e)}'))
                initial = ''
                phone = ''
            
            # V2 (Day 28)
            if ed.V2_EXPECTED_DATE:
                try:
                    fu_case = FU_CONTACT_28.objects.using('db_study_43en').get(USUBJID=ed.USUBJID)
                    actual_date = fu_case.EvaluateDate
                    status = 'COMPLETED' if fu_case.EvaluatedAtDay28 == 'Yes' else 'MISSED'
                except FU_CONTACT_28.DoesNotExist:
                    actual_date = None
                    status = 'UPCOMING'
                
                followup, created = FollowUpStatus.objects.using('db_study_43en').update_or_create(
                    USUBJID=ed.USUBJID_id,
                    SUBJECT_TYPE='CONTACT',
                    VISIT='V2',
                    defaults={
                        'INITIAL': initial,
                        'PHONE': phone,  #  From ENR_CONTACT
                        'EXPECTED_DATE': ed.V2_EXPECTED_DATE,
                        'EXPECTED_FROM': ed.V2_EXPECTED_FROM,
                        'EXPECTED_TO': ed.V2_EXPECTED_TO,
                        'ACTUAL_DATE': actual_date,
                        'STATUS': status
                    }
                )
                if created:
                    count += 1
            
            # V3 (Day 90)
            if ed.V3_EXPECTED_DATE:
                try:
                    fu_case = FU_CONTACT_90.objects.using('db_study_43en').get(USUBJID=ed.USUBJID)
                    actual_date = fu_case.EvaluateDate
                    status = 'COMPLETED' if fu_case.EvaluatedAtDay90 == 'Yes' else 'MISSED'
                except FU_CONTACT_90.DoesNotExist:
                    actual_date = None
                    status = 'UPCOMING'
                
                followup, created = FollowUpStatus.objects.using('db_study_43en').update_or_create(
                    USUBJID=ed.USUBJID_id,
                    SUBJECT_TYPE='CONTACT',
                    VISIT='V3',
                    defaults={
                        'INITIAL': initial,
                        'PHONE': phone,  #  From ENR_CONTACT
                        'EXPECTED_DATE': ed.V3_EXPECTED_DATE,
                        'EXPECTED_FROM': ed.V3_EXPECTED_FROM,
                        'EXPECTED_TO': ed.V3_EXPECTED_TO,
                        'ACTUAL_DATE': actual_date,
                        'STATUS': status
                    }
                )
                if created:
                    count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Đã đồng bộ {count} lịch hẹn từ người tiếp xúc'))
    
    def _update_status_based_on_date(self):
        """Cập nhật trạng thái dựa trên ngày hiện tại"""
        self.stdout.write('Đang cập nhật trạng thái dựa trên ngày hiện tại...')
        
        today = datetime.now().date()
        
        upcoming_to_late = FollowUpStatus.objects.filter(
            STATUS='UPCOMING',
            EXPECTED_DATE__lte=today
        )
        
        late_count = upcoming_to_late.count()
        upcoming_to_late.update(STATUS='LATE')
        
        late_to_missed = FollowUpStatus.objects.filter(
            STATUS='LATE',
            EXPECTED_TO__lt=today
        )
        
        missed_count = late_to_missed.count()
        late_to_missed.update(STATUS='MISSED')
        
        self.stdout.write(self.style.SUCCESS(
            f'Đã cập nhật {late_count} lịch "sắp tới" thành "trễ" và {missed_count} lịch "trễ" thành "lỡ hẹn"'
        ))
    
    def _update_initials(self):
        """Cập nhật lại INITIAL cho tất cả bản ghi FollowUpStatus"""
        self.stdout.write('Đang cập nhật lại trường INITIAL...')
        
        patient_followups = FollowUpStatus.objects.filter(SUBJECT_TYPE='PATIENT')
        count_patient = 0
        
        for followup in patient_followups:
            try:
                usubjid = followup.USUBJID
                screening_case = SCR_CASE.objects.get(USUBJID=usubjid)
                followup.INITIAL = screening_case.INITIAL
                followup.save()
                count_patient += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Lỗi khi cập nhật INITIAL cho bệnh nhân {followup.USUBJID}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'Đã cập nhật INITIAL cho {count_patient} bệnh nhân'))