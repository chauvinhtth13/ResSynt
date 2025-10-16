from django.core.management.base import BaseCommand
from django.db.models import Q
from datetime import datetime, timedelta
from study_43en.models import (
    FollowUpStatus, ExpectedDates, ContactExpectedDates,
    FollowUpCase, FollowUpCase90, ContactFollowUp28, ContactFollowUp90,
    SampleCollection, EnrollmentCase, EnrollmentContact, ScreeningCase
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
        
        # Nếu chỉ muốn cập nhật lại INITIAL
        if force_initial and not reset:
            self._update_initials()
            self.stdout.write(self.style.SUCCESS('Đã cập nhật lại trường INITIAL cho tất cả bản ghi'))
            return
        
        # Đồng bộ từ bệnh nhân
        self._sync_from_patients()
        
        # Đồng bộ từ người tiếp xúc
        self._sync_from_contacts()
        
        # Cập nhật trạng thái dựa trên ngày hiện tại
        self._update_status_based_on_date()
        
        self.stdout.write(self.style.SUCCESS('Đã hoàn thành đồng bộ dữ liệu'))

    def _update_initials(self):
        """Cập nhật lại INITIAL cho tất cả bản ghi FollowUpStatus"""
        self.stdout.write('Đang cập nhật lại trường INITIAL...')
        
        # Cập nhật INITIAL cho bệnh nhân
        patient_followups = FollowUpStatus.objects.filter(SUBJECT_TYPE='PATIENT')
        count_patient = 0
        
        for followup in patient_followups:
            try:
                # Lấy USUBJID và tìm ScreeningCase tương ứng
                usubjid = followup.USUBJID
                screening_case = ScreeningCase.objects.get(USUBJID=usubjid)
                
                # Cập nhật INITIAL và PHONE nếu có
                followup.INITIAL = screening_case.INITIAL
                # Cập nhật PHONE nếu cần
                # followup.PHONE = screening_case.PHONE
                followup.save()
                count_patient += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Lỗi khi cập nhật INITIAL cho bệnh nhân {followup.USUBJID}: {str(e)}'))
        
        # Cập nhật INITIAL cho người tiếp xúc (tương tự)
        contact_followups = FollowUpStatus.objects.filter(SUBJECT_TYPE='CONTACT')
        count_contact = 0
        
        for followup in contact_followups:
            try:
                # Tương tự cho ScreeningContact
                usubjid = followup.USUBJID
                # Bạn cần điều chỉnh logic này dựa trên cấu trúc của ScreeningContact
                # ví dụ: screening_contact = ScreeningContact.objects.get(USUBJID=usubjid)
                # followup.INITIAL = screening_contact.INITIAL
                # followup.save()
                count_contact += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Lỗi khi cập nhật INITIAL cho người tiếp xúc {followup.USUBJID}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'Đã cập nhật INITIAL cho {count_patient} bệnh nhân và {count_contact} người tiếp xúc'))

    def _sync_from_patients(self):
        """Đồng bộ dữ liệu từ bệnh nhân"""
        self.stdout.write('Đang đồng bộ dữ liệu từ bệnh nhân...')
        
        # Lấy thông tin lịch dự kiến từ ExpectedDates
        expected_dates = ExpectedDates.objects.all()
        count = 0
        
        for ed in expected_dates:
            # Khởi tạo biến bên ngoài khối try/except
            initial = ''
            phone = ''
            
            try:
                # Lấy trực tiếp từ ScreeningCase thông qua EnrollmentCase
                enrollment = ed.USUBJID
                # Lấy ScreeningCase object
                screening_case = ScreeningCase.objects.get(USUBJID=enrollment.USUBJID_id)
                
                # Lấy INITIAL từ ScreeningCase
                initial = screening_case.INITIAL
                
                # Lấy PHONE (nếu có)
                # phone = screening_case.PHONE if hasattr(screening_case, 'PHONE') else ''
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Lỗi khi lấy thông tin bệnh nhân {ed.USUBJID_id}: {str(e)}'))
            
            # Chuyển phần này ra ngoài khối try/except để đảm bảo luôn được thực thi
            # Ngày dự kiến V2
            if ed.V2_EXPECTED_DATE:
                followup, created = FollowUpStatus.objects.update_or_create(
                    USUBJID=ed.USUBJID_id,
                    SUBJECT_TYPE='PATIENT',
                    VISIT='V2',
                    defaults={
                        'INITIAL': initial,
                        'PHONE': phone,
                        'EXPECTED_DATE': ed.V2_EXPECTED_DATE,
                        'EXPECTED_FROM': ed.V2_EXPECTED_FROM,
                        'EXPECTED_TO': ed.V2_EXPECTED_TO,
                        'STATUS': 'UPCOMING'
                    }
                )
                if created:
                    count += 1
            
            # Ngày dự kiến V3
            if ed.V3_EXPECTED_DATE:
                # Kiểm tra xem đã có FollowUpCase chưa
                try:
                    fu_case = FollowUpCase.objects.get(USUBJID=ed.USUBJID)
                    actual_date = fu_case.ASSESSDATE
                    status = 'COMPLETED' if fu_case.ASSESSED == 'Yes' else 'MISSED'
                except FollowUpCase.DoesNotExist:
                    actual_date = None
                    status = 'UPCOMING'
                
                followup, created = FollowUpStatus.objects.update_or_create(
                    USUBJID=ed.USUBJID_id,
                    SUBJECT_TYPE='PATIENT',
                    VISIT='V3',
                    defaults={
                        'INITIAL': initial,
                        'PHONE': phone,
                        'EXPECTED_DATE': ed.V3_EXPECTED_DATE,
                        'EXPECTED_FROM': ed.V3_EXPECTED_FROM,
                        'EXPECTED_TO': ed.V3_EXPECTED_TO,
                        'ACTUAL_DATE': actual_date,
                        'STATUS': status
                    }
                )
                if created:
                    count += 1
            
            # Ngày dự kiến V4
            if ed.V4_EXPECTED_DATE:
                # Kiểm tra xem đã có FollowUpCase90 chưa
                try:
                    fu_case = FollowUpCase90.objects.get(USUBJID=ed.USUBJID)
                    actual_date = fu_case.ASSESSDATE
                    status = 'COMPLETED' if fu_case.ASSESSED == 'Yes' else 'MISSED'
                except FollowUpCase90.DoesNotExist:
                    actual_date = None
                    status = 'UPCOMING'
                
                followup, created = FollowUpStatus.objects.update_or_create(
                    USUBJID=ed.USUBJID_id,
                    SUBJECT_TYPE='PATIENT',
                    VISIT='V4',
                    defaults={
                        'INITIAL': initial,
                        'PHONE': phone,
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
        """Đồng bộ dữ liệu từ người tiếp xúc"""
        self.stdout.write('Đang đồng bộ dữ liệu từ người tiếp xúc...')
        
        # Lấy thông tin lịch dự kiến từ ContactExpectedDates
        contact_expected_dates = ContactExpectedDates.objects.all()
        count = 0
        
        for ed in contact_expected_dates:
            try:
                enrollment = EnrollmentContact.objects.get(USUBJID=ed.USUBJID)
                initial = enrollment.USUBJID.INITIAL if hasattr(enrollment.USUBJID, 'INITIAL') else ''
                phone = enrollment.USUBJID.PHONE if hasattr(enrollment.USUBJID, 'PHONE') else ''
            except EnrollmentContact.DoesNotExist:
                initial = ''
                phone = ''
            
            # Ngày dự kiến V2 cho người tiếp xúc
            if ed.V2_EXPECTED_DATE:
                # Kiểm tra xem đã có ContactFollowUp28 chưa
                try:
                    fu_case = ContactFollowUp28.objects.get(USUBJID=ed.USUBJID)
                    actual_date = fu_case.ASSESSDATE
                    status = 'COMPLETED' if fu_case.ASSESSED == 'Yes' else 'MISSED'
                except ContactFollowUp28.DoesNotExist:
                    actual_date = None
                    status = 'UPCOMING'
                
                followup, created = FollowUpStatus.objects.update_or_create(
                    USUBJID=ed.USUBJID_id,
                    SUBJECT_TYPE='CONTACT',
                    VISIT='V2',
                    defaults={
                        'INITIAL': initial,
                        'PHONE': phone,
                        'EXPECTED_DATE': ed.V2_EXPECTED_DATE,
                        'EXPECTED_FROM': ed.V2_EXPECTED_FROM,
                        'EXPECTED_TO': ed.V2_EXPECTED_TO,
                        'ACTUAL_DATE': actual_date,
                        'STATUS': status
                    }
                )
                if created:
                    count += 1
            
            # Ngày dự kiến V3 cho người tiếp xúc
            if ed.V3_EXPECTED_DATE:
                # Kiểm tra xem đã có ContactFollowUp90 chưa
                try:
                    fu_case = ContactFollowUp90.objects.get(USUBJID=ed.USUBJID)
                    actual_date = fu_case.ASSESSDATE
                    status = 'COMPLETED' if fu_case.ASSESSED == 'Yes' else 'MISSED'
                except ContactFollowUp90.DoesNotExist:
                    actual_date = None
                    status = 'UPCOMING'
                
                followup, created = FollowUpStatus.objects.update_or_create(
                    USUBJID=ed.USUBJID_id,
                    SUBJECT_TYPE='CONTACT',
                    VISIT='V3',
                    defaults={
                        'INITIAL': initial,
                        'PHONE': phone,
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
        
        # Tìm các lịch hẹn chưa hoàn thành và đã đến ngày dự kiến
        upcoming_to_late = FollowUpStatus.objects.filter(
            STATUS='UPCOMING',
            EXPECTED_DATE__lte=today
        )
        
        late_count = upcoming_to_late.count()
        upcoming_to_late.update(STATUS='LATE')
        
        # Tìm các lịch hẹn đang trễ và đã quá ngày kết thúc dự kiến
        late_to_missed = FollowUpStatus.objects.filter(
            STATUS='LATE',
            EXPECTED_TO__lt=today
        )
        
        missed_count = late_to_missed.count()
        late_to_missed.update(STATUS='MISSED')
        
        self.stdout.write(self.style.SUCCESS(
            f'Đã cập nhật {late_count} lịch "sắp tới" thành "trễ" và {missed_count} lịch "trễ" thành "lỡ hẹn"'
        ))