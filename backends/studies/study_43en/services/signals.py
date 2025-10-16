from django.db.models.signals import post_save
from django.dispatch import receiver
from study_43en.models import (
    EnrollmentCase, ExpectedCalendar, ExpectedDates, 
    EnrollmentContact, ContactExpectedDates,
    FollowUpCase, FollowUpCase90, 
    ContactFollowUp28, ContactFollowUp90,
    SampleCollection, ContactSampleCollection,
    FollowUpStatus
)

@receiver(post_save, sender=EnrollmentCase)
def sync_enrollment_date_to_expected_dates(sender, instance, **kwargs):
    expected, created = ExpectedDates.objects.get_or_create(USUBJID=instance)
    if instance.ENRDATE:
        expected.ENROLLMENT_DATE = instance.ENRDATE
        expected.save(update_fields=['ENROLLMENT_DATE'])
        expected.auto_map_from_calendar()

@receiver(post_save, sender=EnrollmentContact)
def sync_enrollment_date_to_contact_expected_dates(sender, instance, **kwargs):
    expected, created = ContactExpectedDates.objects.get_or_create(USUBJID=instance)
    if instance.ENRDATE:
        expected.ENROLLMENT_DATE = instance.ENRDATE
        expected.save(update_fields=['ENROLLMENT_DATE'])
        # Mapping V2/V3 từ V3/V4 của ExpectedCalendar
        calendar = ExpectedCalendar.objects.filter(ENROLLMENT_DATE=instance.ENRDATE).first()
        if calendar:
            expected.V2_EXPECTED_FROM = calendar.V3_EXPECTED_FROM
            expected.V2_EXPECTED_TO = calendar.V3_EXPECTED_TO
            expected.V2_EXPECTED_DATE = calendar.V3_EXPECTED_DATE
            expected.V3_EXPECTED_FROM = calendar.V4_EXPECTED_FROM
            expected.V3_EXPECTED_TO = calendar.V4_EXPECTED_TO
            expected.V3_EXPECTED_DATE = calendar.V4_EXPECTED_DATE
            expected.save(update_fields=[
                'V2_EXPECTED_FROM', 'V2_EXPECTED_TO', 'V2_EXPECTED_DATE',
                'V3_EXPECTED_FROM', 'V3_EXPECTED_TO', 'V3_EXPECTED_DATE'
            ])

# Thêm signals cho ExpectedDates
@receiver(post_save, sender=ExpectedDates)
def update_followup_status_from_expected_dates(sender, instance, **kwargs):
    """Cập nhật FollowUpStatus khi ExpectedDates được lưu"""
    # Lấy thông tin bệnh nhân
    patient = instance.USUBJID
    
    # Kiểm tra nếu có form follow-up cho V3 (ngày 28)
    try:
        followup_v3 = FollowUpCase.objects.get(USUBJID=patient)
        v3_actual_date = followup_v3.ASSESSDATE if followup_v3.ASSESSED == 'Yes' else None
        v3_status = 'COMPLETED' if followup_v3.ASSESSED == 'Yes' else 'MISSED'
    except FollowUpCase.DoesNotExist:
        followup_v3 = None
        v3_actual_date = None
        v3_status = 'UPCOMING'
        
    # Kiểm tra nếu có form follow-up cho V4 (ngày 90)
    try:
        followup_v4 = FollowUpCase90.objects.get(USUBJID=patient)
        v4_actual_date = followup_v4.ASSESSDATE if followup_v4.ASSESSED == 'Yes' else None
        v4_status = 'COMPLETED' if followup_v4.ASSESSED == 'Yes' else 'MISSED'
    except FollowUpCase90.DoesNotExist:
        followup_v4 = None
        v4_actual_date = None
        v4_status = 'UPCOMING'
    
    # Kiểm tra nếu có mẫu lần 2 (V2)
    try:
        sample_v2 = SampleCollection.objects.get(USUBJID=patient, SAMPLE_TYPE='2')
        v2_actual_date = sample_v2.COMPLETEDDATE if sample_v2.SAMPLE else None
        v2_status = 'COMPLETED' if sample_v2.SAMPLE else 'MISSED'
    except SampleCollection.DoesNotExist:
        sample_v2 = None
        v2_actual_date = None
        v2_status = 'UPCOMING'
    
    # Cập nhật cho V2
    if instance.V2_EXPECTED_DATE:
        FollowUpStatus.objects.update_or_create(
            USUBJID=patient.USUBJID_id,
            SUBJECT_TYPE='PATIENT',
            VISIT='V2',
            defaults={
                'INITIAL': patient.USUBJID.INITIAL,
                'EXPECTED_FROM': instance.V2_EXPECTED_FROM,
                'EXPECTED_TO': instance.V2_EXPECTED_TO,
                'EXPECTED_DATE': instance.V2_EXPECTED_DATE,
                'ACTUAL_DATE': v2_actual_date,
                'STATUS': v2_status,
            }
        )
    
    # Cập nhật cho V3
    if instance.V3_EXPECTED_DATE:
        FollowUpStatus.objects.update_or_create(
            USUBJID=patient.USUBJID_id,
            SUBJECT_TYPE='PATIENT',
            VISIT='V3',
            defaults={
                'INITIAL': patient.USUBJID.INITIAL,
                'EXPECTED_FROM': instance.V3_EXPECTED_FROM,
                'EXPECTED_TO': instance.V3_EXPECTED_TO,
                'EXPECTED_DATE': instance.V3_EXPECTED_DATE,
                'ACTUAL_DATE': v3_actual_date,
                'STATUS': v3_status,
            }
        )
    
    # Cập nhật cho V4
    if instance.V4_EXPECTED_DATE:
        FollowUpStatus.objects.update_or_create(
            USUBJID=patient.USUBJID_id,
            SUBJECT_TYPE='PATIENT',
            VISIT='V4',
            defaults={
                'INITIAL': patient.USUBJID.INITIAL,
                'EXPECTED_FROM': instance.V4_EXPECTED_FROM,
                'EXPECTED_TO': instance.V4_EXPECTED_TO,
                'EXPECTED_DATE': instance.V4_EXPECTED_DATE,
                'ACTUAL_DATE': v4_actual_date,
                'STATUS': v4_status,
            }
        )

# Thêm signals cho ContactExpectedDates
@receiver(post_save, sender=ContactExpectedDates)
def update_followup_status_from_contact_expected_dates(sender, instance, **kwargs):
    """Cập nhật FollowUpStatus khi ContactExpectedDates được lưu"""
    # Lấy thông tin người tiếp xúc
    contact = instance.USUBJID
    
    # Kiểm tra nếu có form follow-up cho V2 (ngày 28)
    try:
        followup_v2 = ContactFollowUp28.objects.get(USUBJID=contact)
        v2_actual_date = followup_v2.ASSESSDATE if followup_v2.ASSESSED == 'Yes' else None
        v2_status = 'COMPLETED' if followup_v2.ASSESSED == 'Yes' else 'MISSED'
    except ContactFollowUp28.DoesNotExist:
        followup_v2 = None
        v2_actual_date = None
        v2_status = 'UPCOMING'
        
    # Kiểm tra nếu có form follow-up cho V3 (ngày 90)
    try:
        followup_v3 = ContactFollowUp90.objects.get(USUBJID=contact)
        v3_actual_date = followup_v3.ASSESSDATE if followup_v3.ASSESSED == 'Yes' else None
        v3_status = 'COMPLETED' if followup_v3.ASSESSED == 'Yes' else 'MISSED'
    except ContactFollowUp90.DoesNotExist:
        followup_v3 = None
        v3_actual_date = None
        v3_status = 'UPCOMING'
    
    # Cập nhật cho V2
    if instance.V2_EXPECTED_DATE:
        FollowUpStatus.objects.update_or_create(
            USUBJID=contact.USUBJID_id,
            SUBJECT_TYPE='CONTACT',
            VISIT='V2',
            defaults={
                'INITIAL': contact.USUBJID.INITIAL,  # Access INITIAL from ScreeningContact
                'EXPECTED_FROM': instance.V2_EXPECTED_FROM,
                'EXPECTED_TO': instance.V2_EXPECTED_TO,
                'EXPECTED_DATE': instance.V2_EXPECTED_DATE,
                'ACTUAL_DATE': v2_actual_date,
                'STATUS': v2_status,
            }
        )
    
    # Cập nhật cho V3
    if instance.V3_EXPECTED_DATE:
        FollowUpStatus.objects.update_or_create(
            USUBJID=contact.USUBJID_id,
            SUBJECT_TYPE='CONTACT',
            VISIT='V3',
            defaults={
                'INITIAL': contact.USUBJID.INITIAL,  # Access INITIAL from ScreeningContact
                'EXPECTED_FROM': instance.V3_EXPECTED_FROM,
                'EXPECTED_TO': instance.V3_EXPECTED_TO,
                'EXPECTED_DATE': instance.V3_EXPECTED_DATE,
                'ACTUAL_DATE': v3_actual_date,
                'STATUS': v3_status,
            }
        )

# Signals cho các form follow-up
@receiver(post_save, sender=FollowUpCase)
def update_followup_status_from_followup_case(sender, instance, **kwargs):
    """Cập nhật trạng thái FollowUpStatus từ form FollowUpCase (V3)"""
    actual_date = instance.ASSESSDATE if instance.ASSESSED == 'Yes' else None
    status = 'COMPLETED' if instance.ASSESSED == 'Yes' else 'MISSED'
    
    try:
        followup_status = FollowUpStatus.objects.get(
            USUBJID=instance.USUBJID_id,
            SUBJECT_TYPE='PATIENT',
            VISIT='V3'
        )
        followup_status.ACTUAL_DATE = actual_date
        followup_status.STATUS = status
        followup_status.save(update_fields=['ACTUAL_DATE', 'STATUS'])
    except FollowUpStatus.DoesNotExist:
        # Tạo mới nếu chưa có
        expected_dates = ExpectedDates.objects.filter(USUBJID=instance.USUBJID).first()
        if expected_dates:
            FollowUpStatus.objects.create(
                USUBJID=instance.USUBJID_id,
                SUBJECT_TYPE='PATIENT',
                VISIT='V3',
                INITIAL=instance.USUBJID.USUBJID.INITIAL,
                EXPECTED_FROM=expected_dates.V3_EXPECTED_FROM,
                EXPECTED_TO=expected_dates.V3_EXPECTED_TO,
                EXPECTED_DATE=expected_dates.V3_EXPECTED_DATE,
                ACTUAL_DATE=actual_date,
                STATUS=status
            )

@receiver(post_save, sender=FollowUpCase90)
def update_followup_status_from_followup_case90(sender, instance, **kwargs):
    """Cập nhật trạng thái FollowUpStatus từ form FollowUpCase90 (V4)"""
    actual_date = instance.ASSESSDATE if instance.ASSESSED == 'Yes' else None
    status = 'COMPLETED' if instance.ASSESSED == 'Yes' else 'MISSED'
    
    try:
        followup_status = FollowUpStatus.objects.get(
            USUBJID=instance.USUBJID_id,
            SUBJECT_TYPE='PATIENT',
            VISIT='V4'
        )
        followup_status.ACTUAL_DATE = actual_date
        followup_status.STATUS = status
        followup_status.save(update_fields=['ACTUAL_DATE', 'STATUS'])
    except FollowUpStatus.DoesNotExist:
        # Tạo mới nếu chưa có
        expected_dates = ExpectedDates.objects.filter(USUBJID=instance.USUBJID).first()
        if expected_dates:
            FollowUpStatus.objects.create(
                USUBJID=instance.USUBJID_id,
                SUBJECT_TYPE='PATIENT',
                VISIT='V4',
                INITIAL=instance.USUBJID.USUBJID.INITIAL,
                EXPECTED_FROM=expected_dates.V4_EXPECTED_FROM,
                EXPECTED_TO=expected_dates.V4_EXPECTED_TO,
                EXPECTED_DATE=expected_dates.V4_EXPECTED_DATE,
                ACTUAL_DATE=actual_date,
                STATUS=status
            )

@receiver(post_save, sender=ContactFollowUp28)
def update_followup_status_from_contact_followup28(sender, instance, **kwargs):
    """Cập nhật trạng thái FollowUpStatus từ form ContactFollowUp28 (V2)"""
    actual_date = instance.ASSESSDATE if instance.ASSESSED == 'Yes' else None
    status = 'COMPLETED' if instance.ASSESSED == 'Yes' else 'MISSED'
    
    try:
        followup_status = FollowUpStatus.objects.get(
            USUBJID=instance.USUBJID_id,
            SUBJECT_TYPE='CONTACT',
            VISIT='V2'
        )
        followup_status.ACTUAL_DATE = actual_date
        followup_status.STATUS = status
        followup_status.save(update_fields=['ACTUAL_DATE', 'STATUS'])
    except FollowUpStatus.DoesNotExist:
        # Tạo mới nếu chưa có
        expected_dates = ContactExpectedDates.objects.filter(USUBJID=instance.USUBJID).first()
        if expected_dates:
            FollowUpStatus.objects.create(
                USUBJID=instance.USUBJID_id,
                SUBJECT_TYPE='CONTACT',
                VISIT='V2',
                INITIAL=instance.USUBJID.INITIAL,
                EXPECTED_FROM=expected_dates.V2_EXPECTED_FROM,
                EXPECTED_TO=expected_dates.V2_EXPECTED_TO,
                EXPECTED_DATE=expected_dates.V2_EXPECTED_DATE,
                ACTUAL_DATE=actual_date,
                STATUS=status,
                CONTACT_PERSON=instance.USUBJID.INITIAL
            )

@receiver(post_save, sender=ContactFollowUp90)
def update_followup_status_from_contact_followup90(sender, instance, **kwargs):
    """Cập nhật trạng thái FollowUpStatus từ form ContactFollowUp90 (V3)"""
    actual_date = instance.ASSESSDATE if instance.ASSESSED == 'Yes' else None
    status = 'COMPLETED' if instance.ASSESSED == 'Yes' else 'MISSED'
    
    try:
        followup_status = FollowUpStatus.objects.get(
            USUBJID=instance.USUBJID_id,
            SUBJECT_TYPE='CONTACT',
            VISIT='V3'
        )
        followup_status.ACTUAL_DATE = actual_date
        followup_status.STATUS = status
        followup_status.save(update_fields=['ACTUAL_DATE', 'STATUS'])
    except FollowUpStatus.DoesNotExist:
        # Tạo mới nếu chưa có
        expected_dates = ContactExpectedDates.objects.filter(USUBJID=instance.USUBJID).first()
        if expected_dates:
            FollowUpStatus.objects.create(
                USUBJID=instance.USUBJID_id,
                SUBJECT_TYPE='CONTACT',
                VISIT='V3',
                INITIAL=instance.USUBJID.INITIAL,
                EXPECTED_FROM=expected_dates.V3_EXPECTED_FROM,
                EXPECTED_TO=expected_dates.V3_EXPECTED_TO,
                EXPECTED_DATE=expected_dates.V3_EXPECTED_DATE,
                ACTUAL_DATE=actual_date,
                STATUS=status,
                CONTACT_PERSON=instance.USUBJID.INITIAL
            )

# Signal cho mẫu lần 2 (V2) của bệnh nhân
@receiver(post_save, sender=SampleCollection)
def update_followup_status_from_sample(sender, instance, **kwargs):
    """Cập nhật trạng thái FollowUpStatus từ mẫu thu thập"""
    # Chỉ cập nhật cho mẫu lần 2 (V2)
    if instance.SAMPLE_TYPE == '2':
        actual_date = instance.COMPLETEDDATE if instance.SAMPLE else None
        status = 'COMPLETED' if instance.SAMPLE else 'MISSED'
        
        try:
            followup_status = FollowUpStatus.objects.get(
                USUBJID=instance.USUBJID_id,
                SUBJECT_TYPE='PATIENT',
                VISIT='V2'
            )
            followup_status.ACTUAL_DATE = actual_date
            followup_status.STATUS = status
            followup_status.save(update_fields=['ACTUAL_DATE', 'STATUS'])
        except FollowUpStatus.DoesNotExist:
            # Tạo mới nếu chưa có
            expected_dates = ExpectedDates.objects.filter(USUBJID=instance.USUBJID).first()
            if expected_dates:
                FollowUpStatus.objects.create(
                    USUBJID=instance.USUBJID_id,
                    SUBJECT_TYPE='PATIENT',
                    VISIT='V2',
                    INITIAL=instance.USUBJID.USUBJID.INITIAL,
                    EXPECTED_FROM=expected_dates.V2_EXPECTED_FROM,
                    EXPECTED_TO=expected_dates.V2_EXPECTED_TO,
                    EXPECTED_DATE=expected_dates.V2_EXPECTED_DATE,
                    ACTUAL_DATE=actual_date,
                    STATUS=status
                )