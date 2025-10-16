from django.core.management.base import BaseCommand
from study_43en.models import (
    FollowUpCase, FollowUpCase90, 
    ContactFollowUp28, ContactFollowUp90,
    SampleCollection, ContactSampleCollection,
    FollowUpStatus
)

class Command(BaseCommand):
    help = 'Cập nhật trạng thái FollowUpStatus từ trường ASSESSED trong các form follow-up và SAMPLE'

    def handle(self, *args, **options):
        self.stdout.write('Bắt đầu cập nhật trạng thái từ ASSESSED và SAMPLE...')
        
        # Cập nhật từ FollowUpCase (V3 của bệnh nhân)
        self.update_from_followup_case()
        
        # Cập nhật từ FollowUpCase90 (V4 của bệnh nhân)
        self.update_from_followup_case90()
        
        # Cập nhật từ ContactFollowUp28 (V2 của người tiếp xúc)
        self.update_from_contact_followup28()
        
        # Cập nhật từ ContactFollowUp90 (V3 của người tiếp xúc)
        self.update_from_contact_followup90()
        
        # Cập nhật từ SampleCollection (V2 của bệnh nhân)
        self.update_from_sample_collection()
        
        self.stdout.write(self.style.SUCCESS('Hoàn thành cập nhật trạng thái!'))
    
    def update_from_followup_case(self):
        """Cập nhật trạng thái từ FollowUpCase (V3 của bệnh nhân)"""
        followups = FollowUpCase.objects.all()
        count = 0
        
        for followup in followups:
            actual_date = followup.ASSESSDATE if followup.ASSESSED == 'Yes' else None
            status = 'COMPLETED' if followup.ASSESSED == 'Yes' else 'MISSED'
            
            try:
                followup_status = FollowUpStatus.objects.get(
                    USUBJID=followup.USUBJID_id,
                    SUBJECT_TYPE='PATIENT',
                    VISIT='V3'
                )
                followup_status.ACTUAL_DATE = actual_date
                followup_status.STATUS = status
                followup_status.save(update_fields=['ACTUAL_DATE', 'STATUS'])
                count += 1
            except FollowUpStatus.DoesNotExist:
                self.stdout.write(f'Không tìm thấy FollowUpStatus cho {followup.USUBJID_id} - V3')
        
        self.stdout.write(f'Đã cập nhật {count} trạng thái từ FollowUpCase')
    
    def update_from_followup_case90(self):
        """Cập nhật trạng thái từ FollowUpCase90 (V4 của bệnh nhân)"""
        followups = FollowUpCase90.objects.all()
        count = 0
        
        for followup in followups:
            actual_date = followup.ASSESSDATE if followup.ASSESSED == 'Yes' else None
            status = 'COMPLETED' if followup.ASSESSED == 'Yes' else 'MISSED'
            
            try:
                followup_status = FollowUpStatus.objects.get(
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
        
        self.stdout.write(f'Đã cập nhật {count} trạng thái từ FollowUpCase90')
    
    def update_from_contact_followup28(self):
        """Cập nhật trạng thái từ ContactFollowUp28 (V2 của người tiếp xúc)"""
        followups = ContactFollowUp28.objects.all()
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
        
        self.stdout.write(f'Đã cập nhật {count} trạng thái từ ContactFollowUp28')
    
    def update_from_contact_followup90(self):
        """Cập nhật trạng thái từ ContactFollowUp90 (V3 của người tiếp xúc)"""
        followups = ContactFollowUp90.objects.all()
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
        
        self.stdout.write(f'Đã cập nhật {count} trạng thái từ ContactFollowUp90')
    
    def update_from_sample_collection(self):
        """Cập nhật trạng thái từ SampleCollection (V2 của bệnh nhân)"""
        samples = SampleCollection.objects.filter(SAMPLE_TYPE='2')
        count = 0
        
        for sample in samples:
            actual_date = sample.COMPLETEDDATE if sample.SAMPLE else None
            status = 'COMPLETED' if sample.SAMPLE else 'MISSED'
            
            try:
                followup_status = FollowUpStatus.objects.get(
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
        
        self.stdout.write(f'Đã cập nhật {count} trạng thái từ SampleCollection')