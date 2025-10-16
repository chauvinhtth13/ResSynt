from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from study_43en.models import (
    ExpectedDates, ContactExpectedDates, 
    EnrollmentCase, EnrollmentContact,
    FollowUpCase, FollowUpCase90, 
    ContactFollowUp28, ContactFollowUp90,
    SampleCollection, ContactSampleCollection,
    FollowUpStatus
)

class Command(BaseCommand):
    help = 'Cập nhật bảng FollowUpStatus từ dữ liệu hiện có'

    def handle(self, *args, **options):
        self.stdout.write('Bắt đầu cập nhật FollowUpStatus...')
        
        # Xóa dữ liệu cũ (tùy chọn)
        if options.get('reset', False):
            FollowUpStatus.objects.all().delete()
            self.stdout.write('Đã xóa dữ liệu cũ')
        
        # Cập nhật cho bệnh nhân
        self.update_patient_statuses()
        
        # Cập nhật cho người tiếp xúc
        self.update_contact_statuses()
        
        # Cập nhật trạng thái dựa trên ngày
        self.update_all_statuses()
        
        self.stdout.write(self.style.SUCCESS('Hoàn thành cập nhật FollowUpStatus!'))
    
    def update_patient_statuses(self):
        """Cập nhật dữ liệu theo dõi từ bệnh nhân"""
        count = 0
        # Lấy tất cả lịch dự kiến
        expected_dates = ExpectedDates.objects.select_related('USUBJID').all()
        
        for expected in expected_dates:
            # Lấy thông tin bệnh nhân
            patient = expected.USUBJID
            
            # Lấy các form theo dõi đã hoàn thành (nếu có)
            try:
                followup_v3 = FollowUpCase.objects.get(USUBJID=patient)
                v3_actual_date = followup_v3.ASSESSDATE if followup_v3.ASSESSED == 'Yes' else None
                v3_status = 'COMPLETED' if followup_v3.ASSESSED == 'Yes' else 'MISSED'
            except FollowUpCase.DoesNotExist:
                v3_actual_date = None
                v3_status = None
                
            try:
                followup_v4 = FollowUpCase90.objects.get(USUBJID=patient)
                v4_actual_date = followup_v4.ASSESSDATE if followup_v4.ASSESSED == 'Yes' else None
                v4_status = 'COMPLETED' if followup_v4.ASSESSED == 'Yes' else 'MISSED'
            except FollowUpCase90.DoesNotExist:
                v4_actual_date = None
                v4_status = None
            
            # Kiểm tra nếu có mẫu lần 2 (V2)
            try:
                sample_v2 = SampleCollection.objects.get(USUBJID=patient, SAMPLE_TYPE='2')
                v2_actual_date = sample_v2.COMPLETEDDATE if sample_v2.SAMPLE else None
                v2_status = 'COMPLETED' if sample_v2.SAMPLE else 'MISSED'
            except SampleCollection.DoesNotExist:
                v2_actual_date = None
                v2_status = None
            
            # Cập nhật cho V2
            if expected.V2_EXPECTED_DATE:
                status_data = {
                    'INITIAL': getattr(patient, 'INITIAL', ''),
                    'VISIT_DESCRIPTION': 'D10±3',
                    'EXPECTED_FROM': expected.V2_EXPECTED_FROM,
                    'EXPECTED_TO': expected.V2_EXPECTED_TO,
                    'EXPECTED_DATE': expected.V2_EXPECTED_DATE,
                    'ACTUAL_DATE': v2_actual_date,
                }
                
                if v2_status:
                    status_data['STATUS'] = v2_status
                
                FollowUpStatus.objects.update_or_create(
                    USUBJID=patient.USUBJID_id,
                    SUBJECT_TYPE='PATIENT',
                    VISIT='V2',
                    defaults=status_data
                )
                count += 1
            
            # Cập nhật cho V3
            if expected.V3_EXPECTED_DATE:
                status_data = {
                    'INITIAL': getattr(patient, 'INITIAL', ''),
                    'VISIT_DESCRIPTION': 'D28±3',
                    'EXPECTED_FROM': expected.V3_EXPECTED_FROM,
                    'EXPECTED_TO': expected.V3_EXPECTED_TO,
                    'EXPECTED_DATE': expected.V3_EXPECTED_DATE,
                    'ACTUAL_DATE': v3_actual_date,
                }
                
                if v3_status:
                    status_data['STATUS'] = v3_status
                
                FollowUpStatus.objects.update_or_create(
                    USUBJID=patient.USUBJID_id,
                    SUBJECT_TYPE='PATIENT',
                    VISIT='V3',
                    defaults=status_data
                )
                count += 1
            
            # Cập nhật cho V4
            if expected.V4_EXPECTED_DATE:
                status_data = {
                    'INITIAL': getattr(patient, 'INITIAL', ''),
                    'VISIT_DESCRIPTION': 'D90±3',
                    'EXPECTED_FROM': expected.V4_EXPECTED_FROM,
                    'EXPECTED_TO': expected.V4_EXPECTED_TO,
                    'EXPECTED_DATE': expected.V4_EXPECTED_DATE,
                    'ACTUAL_DATE': v4_actual_date,
                }
                
                if v4_status:
                    status_data['STATUS'] = v4_status
                
                FollowUpStatus.objects.update_or_create(
                    USUBJID=patient.USUBJID_id,
                    SUBJECT_TYPE='PATIENT',
                    VISIT='V4',
                    defaults=status_data
                )
                count += 1
        
        self.stdout.write(f'Đã cập nhật {count} mục theo dõi cho bệnh nhân')
    
    def update_contact_statuses(self):
        """Cập nhật dữ liệu theo dõi từ người tiếp xúc"""
        count = 0
        # Lấy tất cả lịch dự kiến
        expected_dates = ContactExpectedDates.objects.select_related('USUBJID').all()
        
        for expected in expected_dates:
            # Lấy thông tin người tiếp xúc
            contact = expected.USUBJID
            
            # Lấy các form theo dõi đã hoàn thành (nếu có)
            try:
                followup_v2 = ContactFollowUp28.objects.get(USUBJID=contact)
                v2_actual_date = followup_v2.ASSESSDATE if followup_v2.ASSESSED == 'Yes' else None
                v2_status = 'COMPLETED' if followup_v2.ASSESSED == 'Yes' else 'MISSED'
            except ContactFollowUp28.DoesNotExist:
                v2_actual_date = None
                v2_status = None
                
            try:
                followup_v3 = ContactFollowUp90.objects.get(USUBJID=contact)
                v3_actual_date = followup_v3.ASSESSDATE if followup_v3.ASSESSED == 'Yes' else None
                v3_status = 'COMPLETED' if followup_v3.ASSESSED == 'Yes' else 'MISSED'
            except ContactFollowUp90.DoesNotExist:
                v3_actual_date = None
                v3_status = None
            
            # Cập nhật cho V2
            if expected.V2_EXPECTED_DATE:
                status_data = {
                    'INITIAL': getattr(contact, 'INITIAL', ''),
                    'VISIT_DESCRIPTION': 'D28±3',
                    'EXPECTED_FROM': expected.V2_EXPECTED_FROM,
                    'EXPECTED_TO': expected.V2_EXPECTED_TO,
                    'EXPECTED_DATE': expected.V2_EXPECTED_DATE,
                    'ACTUAL_DATE': v2_actual_date,
                    'PHONE': getattr(contact, 'PHONE', None),
                }
                
                if v2_status:
                    status_data['STATUS'] = v2_status
                
                FollowUpStatus.objects.update_or_create(
                    USUBJID=contact.USUBJID_id,
                    SUBJECT_TYPE='CONTACT',
                    VISIT='V2',
                    defaults=status_data
                )
                count += 1
            
            # Cập nhật cho V3
            if expected.V3_EXPECTED_DATE:
                status_data = {
                    'INITIAL': getattr(contact, 'INITIAL', ''),
                    'VISIT_DESCRIPTION': 'D90±3',
                    'EXPECTED_FROM': expected.V3_EXPECTED_FROM,
                    'EXPECTED_TO': expected.V3_EXPECTED_TO,
                    'EXPECTED_DATE': expected.V3_EXPECTED_DATE,
                    'ACTUAL_DATE': v3_actual_date,
                    'PHONE': getattr(contact, 'PHONE', None),
                }
                
                if v3_status:
                    status_data['STATUS'] = v3_status
                
                FollowUpStatus.objects.update_or_create(
                    USUBJID=contact.USUBJID_id,
                    SUBJECT_TYPE='CONTACT',
                    VISIT='V3',
                    defaults=status_data
                )
                count += 1
        
        self.stdout.write(f'Đã cập nhật {count} mục theo dõi cho người tiếp xúc')
    
    def update_all_statuses(self):
        """Cập nhật trạng thái dựa trên ngày hiện tại cho các mục chưa hoàn thành"""
        today = date.today()
        updated_count = 0
        
        # Lấy các mục chưa hoàn thành và không có trạng thái rõ ràng
        followups = FollowUpStatus.objects.filter(STATUS__isnull=True) | FollowUpStatus.objects.filter(STATUS='')
        
        for followup in followups:
            # Nếu đã có ngày thực tế, đánh dấu là hoàn thành
            if followup.ACTUAL_DATE:
                followup.STATUS = 'COMPLETED'
                followup.save(update_fields=['STATUS'])
                updated_count += 1
                continue
                
            # Nếu không có ngày thực tế, xác định trạng thái dựa trên khoảng thời gian
            if followup.EXPECTED_TO and today > followup.EXPECTED_TO:
                followup.STATUS = 'MISSED'
            elif followup.EXPECTED_FROM and today >= followup.EXPECTED_FROM:
                followup.STATUS = 'LATE'
            else:
                followup.STATUS = 'UPCOMING'
                
            followup.save(update_fields=['STATUS'])
            updated_count += 1
        
        self.stdout.write(f'Đã cập nhật {updated_count} trạng thái dựa trên ngày hiện tại')

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Xóa tất cả dữ liệu trước khi cập nhật',
        )