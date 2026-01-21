from django.core.management.base import BaseCommand
from django.core.management.base import BaseCommand
from django.db.models import Q
from datetime import datetime, timedelta
from backends.studies.study_43en.models.schedule import (
    FollowUpStatus, ExpectedDates, ContactExpectedDates,
)
from backends.studies.study_43en.models.patient import SCR_CASE, ENR_CASE,FU_CASE_28, FU_CASE_90,SAM_CASE
from backends.studies.study_43en.models.contact import ENR_CONTACT, FU_CONTACT_28, FU_CONTACT_90,SAM_CONTACT

class Command(BaseCommand):
    help = 'Cập nhật trạng thái FollowUpStatus từ trường ASSESSED trong các form follow-up và SAMPLE'

    def handle(self, *args, **options):
        self.stdout.write('Bắt đầu cập nhật trạng thái từ ASSESSED và SAMPLE...')
        
        # Cập nhật từ FU_CASE_28 (V3 của bệnh nhân)
        self.update_from_followup_case()
        
        # Cập nhật từ FU_CASE_90 (V4 của bệnh nhân)
        self.update_from_followup_case90()
        
        # Cập nhật từ FU_CONTACT_28 (V2 của người tiếp xúc)
        self.update_from_contact_followup28()
        
        # Cập nhật từ FU_CONTACT_90 (V3 của người tiếp xúc)
        self.update_from_contact_followup90()
        
        # Cập nhật từ SAM_CASE (V2 của bệnh nhân)
        self.update_from_sample_collection()
        
        self.stdout.write(self.style.SUCCESS('Hoàn thành cập nhật trạng thái!'))
    
    def update_from_followup_case(self):
        """Cập nhật trạng thái từ FU_CASE_28 (V3 của bệnh nhân)"""
        followups = FU_CASE_28.objects.using('db_study_43en').all()
        count = 0
        
        for followup in followups:
            actual_date = followup.ASSESSDATE if followup.ASSESSED == 'Yes' else None
            status = 'COMPLETED' if followup.ASSESSED == 'Yes' else 'MISSED'
            
            try:
                followup_status = FollowUpStatus.objects.using('db_study_43en').get(
                    USUBJID=followup.USUBJID_id,
                    SUBJECT_TYPE='PATIENT',
                    VISIT='V3'
                )
                followup_status.ACTUAL_DATE = actual_date
                followup_status.STATUS = status
                followup_status.save(using='db_study_43en', update_fields=['ACTUAL_DATE', 'STATUS'])
                count += 1
            except FollowUpStatus.DoesNotExist:
                self.stdout.write(f'Không tìm thấy FollowUpStatus cho {followup.USUBJID_id} - V3')
        
        self.stdout.write(f'Đã cập nhật {count} trạng thái từ FU_CASE_28')
    
    def update_from_followup_case90(self):
        """Cập nhật trạng thái từ FU_CASE_90 (V4 của bệnh nhân)"""
        followups = FU_CASE_90.objects.using('db_study_43en').all()
        count = 0
        
        for followup in followups:
            actual_date = followup.ASSESSDATE if followup.ASSESSED == 'Yes' else None
            status = 'COMPLETED' if followup.ASSESSED == 'Yes' else 'MISSED'
            
            try:
                followup_status = FollowUpStatus.objects.using('db_study_43en').get(
                    USUBJID=followup.USUBJID_id,
                    SUBJECT_TYPE='PATIENT',
                    VISIT='V4'
                )
                followup_status.ACTUAL_DATE = actual_date
                followup_status.STATUS = status
                followup_status.save(update_fields=['ACTUAL_DATE', 'STATUS'])
                count += 1
            except FollowUpStatus.DoesNotExist:
                self.stdout.write(f'Không tìm thấy FollowUpStatus cho {followup.USUBJID_id} - V4')
        
        self.stdout.write(f'Đã cập nhật {count} trạng thái từ FU_CASE_90')
    
    def update_from_contact_followup28(self):
        """Cập nhật trạng thái từ FU_CONTACT_28 (V2 của người tiếp xúc)"""
        followups = FU_CONTACT_28.objects.using('db_study_43en').all()
        count = 0
        
        for followup in followups:
            actual_date = followup.ASSESSDATE if followup.ASSESSED == 'Yes' else None
            status = 'COMPLETED' if followup.ASSESSED == 'Yes' else 'MISSED'
            
            try:
                followup_status = FollowUpStatus.objects.get(
                    USUBJID=followup.USUBJID_id,
                    SUBJECT_TYPE='CONTACT',
                    VISIT='V2'
                )
                followup_status.ACTUAL_DATE = actual_date
                followup_status.STATUS = status
                followup_status.save(update_fields=['ACTUAL_DATE', 'STATUS'])
                count += 1
            except FollowUpStatus.DoesNotExist:
                self.stdout.write(f'Không tìm thấy FollowUpStatus cho {followup.USUBJID_id} - V2')
        
        self.stdout.write(f'Đã cập nhật {count} trạng thái từ FU_CONTACT_28')
    
    def update_from_contact_followup90(self):
        """Cập nhật trạng thái từ FU_CONTACT_90 (V3 của người tiếp xúc)"""
        followups = FU_CONTACT_90.objects.using('db_study_43en').all()
        count = 0
        
        for followup in followups:
            actual_date = followup.ASSESSDATE if followup.ASSESSED == 'Yes' else None
            status = 'COMPLETED' if followup.ASSESSED == 'Yes' else 'MISSED'
            
            try:
                followup_status = FollowUpStatus.objects.get(
                    USUBJID=followup.USUBJID_id,
                    SUBJECT_TYPE='CONTACT',
                    VISIT='V3'
                )
                followup_status.ACTUAL_DATE = actual_date
                followup_status.STATUS = status
                followup_status.save(update_fields=['ACTUAL_DATE', 'STATUS'])
                count += 1
            except FollowUpStatus.DoesNotExist:
                self.stdout.write(f'Không tìm thấy FollowUpStatus cho {followup.USUBJID_id} - V3')
        
        self.stdout.write(f'Đã cập nhật {count} trạng thái từ FU_CONTACT_90')
    
    def update_from_sample_collection(self):
        """Cập nhật trạng thái từ SAM_CASE (V2 của bệnh nhân)"""
        samples = SAM_CASE.objects.using('db_study_43en').filter(SAMPLE_TYPE='2')
        count = 0
        
        for sample in samples:
            actual_date = sample.SAMPLEDATE if sample.SAMPLE else None
            status = 'COMPLETED' if sample.SAMPLE else 'MISSED'
            
            try:
                followup_status = FollowUpStatus.objects.using('db_study_43en').get(
                    USUBJID=sample.USUBJID_id,
                    SUBJECT_TYPE='PATIENT',
                    VISIT='V2'
                )
                followup_status.ACTUAL_DATE = actual_date
                followup_status.STATUS = status
                followup_status.save(update_fields=['ACTUAL_DATE', 'STATUS'])
                count += 1
            except FollowUpStatus.DoesNotExist:
                self.stdout.write(f'Không tìm thấy FollowUpStatus cho {sample.USUBJID_id} - V2')
        
        self.stdout.write(f'Đã cập nhật {count} trạng thái từ SAM_CASE')