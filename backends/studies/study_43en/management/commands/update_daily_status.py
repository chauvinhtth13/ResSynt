from django.core.management.base import BaseCommand
from datetime import date


from django.core.management.base import BaseCommand
from django.db.models import Q
from datetime import datetime, timedelta
from backends.studies.study_43en.models.schedule import (
    FollowUpStatus, ExpectedDates, ContactExpectedDates,
)
from backends.studies.study_43en.models.patient import SCR_CASE, ENR_CASE,FU_CASE_28, FU_CASE_90
from backends.studies.study_43en.models.contact import ENR_CONTACT, FU_CONTACT_28, FU_CONTACT_90


class Command(BaseCommand):
    help = 'Cập nhật trạng thái theo dõi hàng ngày dựa trên ngày hiện tại'

    def handle(self, *args, **options):
        today = date.today()
        updated_count = 0
        
        # Lấy các mục chưa hoàn thành
        followups = FollowUpStatus.objects.using('db_study_43en').exclude(STATUS='COMPLETED')
        
        for followup in followups:
            old_status = followup.STATUS
            
            # Cập nhật trạng thái dựa trên ngày hiện tại
            if followup.ACTUAL_DATE:
                followup.STATUS = 'COMPLETED'
            elif followup.EXPECTED_TO and today > followup.EXPECTED_TO:
                followup.STATUS = 'MISSED'
            elif followup.EXPECTED_FROM and today >= followup.EXPECTED_FROM:
                followup.STATUS = 'LATE'
            else:
                followup.STATUS = 'UPCOMING'
            
            # Chỉ lưu nếu có sự thay đổi
            if followup.STATUS != old_status:
                followup.save(using='db_study_43en', update_fields=['STATUS'])
                updated_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Đã cập nhật {updated_count} trạng thái theo dõi'))