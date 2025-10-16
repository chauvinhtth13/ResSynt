from django.core.management.base import BaseCommand
from study_43en.models import FollowUpStatus
from datetime import date

class Command(BaseCommand):
    help = 'Cập nhật trạng thái theo dõi hàng ngày dựa trên ngày hiện tại'

    def handle(self, *args, **options):
        today = date.today()
        updated_count = 0
        
        # Lấy các mục chưa hoàn thành
        followups = FollowUpStatus.objects.exclude(STATUS='COMPLETED')
        
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
                followup.save(update_fields=['STATUS'])
                updated_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Đã cập nhật {updated_count} trạng thái theo dõi'))