# backends/studies/study_43en/services/signals.py

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from backends.studies.study_43en.models.patient import (
    ENR_CASE, FU_CASE_28, FU_CASE_90, SAM_CASE
)
from backends.studies.study_43en.models.contact import (
    ENR_CONTACT, FU_CONTACT_28, FU_CONTACT_90, SAM_CONTACT
)
from backends.studies.study_43en.models.schedule import (
    ExpectedCalendar, ExpectedDates, ContactExpectedDates, FollowUpStatus
)
# Import trực tiếp PII models
from backends.studies.study_43en.models.patient.PER_DATA import PERSONAL_DATA
from backends.studies.study_43en.models.contact.PER_CONTACT_DATA import PERSONAL_CONTACT_DATA
import logging

logger = logging.getLogger(__name__)


# ==========================================
# HELPER FUNCTIONS - Get PII from PERSONAL_DATA
# ==========================================

def get_patient_pii(patient):
    """
    Get INITIAL and PHONE for patient
    - INITIAL: from SCR_CASE
    - PHONE: from PERSONAL_DATA
    
    Args:
        patient: ENR_CASE instance
    Returns:
        tuple: (initial, phone)
    """
    initial = ''
    phone = ''
    
    # Get INITIAL from SCR_CASE
    try:
        screening_case = patient.USUBJID  # ENR_CASE → SCR_CASE
        initial = screening_case.INITIAL if screening_case else ''
    except Exception:
        pass
    
    # Get PHONE from PERSONAL_DATA (query trực tiếp)
    try:
        personal_data = PERSONAL_DATA.objects.using('db_study_43en').get(USUBJID=patient)
        phone = personal_data.PHONE or ''
    except PERSONAL_DATA.DoesNotExist:
        phone = ''
    except Exception:
        phone = ''
    
    return initial, phone


def get_contact_pii(contact):
    """
    Get INITIAL and PHONE for contact
    - INITIAL: from SCR_CONTACT
    - PHONE: from PERSONAL_CONTACT_DATA
    
    Args:
        contact: ENR_CONTACT instance
    Returns:
        tuple: (initial, phone)
    """
    initial = ''
    phone = ''
    
    # Get INITIAL from SCR_CONTACT
    try:
        screening_contact = contact.USUBJID  # ENR_CONTACT → SCR_CONTACT
        initial = screening_contact.INITIAL if screening_contact else ''
    except Exception:
        pass
    
    # Get PHONE from PERSONAL_CONTACT_DATA (query trực tiếp)
    try:
        personal_data = PERSONAL_CONTACT_DATA.objects.using('db_study_43en').get(USUBJID=contact)
        phone = personal_data.PHONE or ''
    except PERSONAL_CONTACT_DATA.DoesNotExist:
        phone = ''
    except Exception:
        phone = ''
    
    return initial, phone


# ==========================================
# ENROLLMENT SIGNALS - Sync PHONE & INITIAL
# ==========================================

@receiver(post_save, sender=ENR_CASE)
def sync_enrollment_date_to_expected_dates(sender, instance, **kwargs):
    """
    TWO-WAY SYNC: ENR_CASE → ExpectedDates → FollowUpStatus
    """
    expected, created = ExpectedDates.objects.using('db_study_43en').get_or_create(USUBJID=instance)
    
    if instance.ENRDATE:
        expected.ENROLLMENT_DATE = instance.ENRDATE
        expected.save(using='db_study_43en', update_fields=['ENROLLMENT_DATE'])
        expected.auto_map_from_calendar()
    
    # Sync PHONE & INITIAL to all FollowUpStatus records
    try:
        initial, phone = get_patient_pii(instance)
        
        if initial or phone:
            updated_count = FollowUpStatus.objects.using('db_study_43en').filter(
                USUBJID=instance.USUBJID_id,
                SUBJECT_TYPE='PATIENT'
            ).update(
                INITIAL=initial,
                PHONE=phone
            )
            
            if updated_count > 0:
                logger.info(f"Synced PII for patient {instance.USUBJID_id}: ({updated_count} records)")
    except Exception as e:
        logger.error(f"Error syncing PII: {e}", exc_info=True)


@receiver(post_save, sender=ENR_CONTACT)
def sync_enrollment_date_to_contact_expected_dates(sender, instance, **kwargs):
    """
    TWO-WAY SYNC: ENR_CONTACT → ContactExpectedDates → FollowUpStatus
    """
    expected, created = ContactExpectedDates.objects.using('db_study_43en').get_or_create(USUBJID=instance)
    
    if instance.ENRDATE:
        expected.ENROLLMENT_DATE = instance.ENRDATE
        expected.save(using='db_study_43en', update_fields=['ENROLLMENT_DATE'])
        calendar = ExpectedCalendar.objects.using('db_study_43en').filter(ENROLLMENT_DATE=instance.ENRDATE).first()
        if calendar:
            expected.V2_EXPECTED_FROM = calendar.V3_EXPECTED_FROM
            expected.V2_EXPECTED_TO = calendar.V3_EXPECTED_TO
            expected.V2_EXPECTED_DATE = calendar.V3_EXPECTED_DATE
            expected.V3_EXPECTED_FROM = calendar.V4_EXPECTED_FROM
            expected.V3_EXPECTED_TO = calendar.V4_EXPECTED_TO
            expected.V3_EXPECTED_DATE = calendar.V4_EXPECTED_DATE
            expected.save(using='db_study_43en', update_fields=[
                'V2_EXPECTED_FROM', 'V2_EXPECTED_TO', 'V2_EXPECTED_DATE',
                'V3_EXPECTED_FROM', 'V3_EXPECTED_TO', 'V3_EXPECTED_DATE'
            ])
    
    # Sync PHONE & INITIAL to all FollowUpStatus records
    try:
        initial, phone = get_contact_pii(instance)
        
        if initial or phone:
            updated_count = FollowUpStatus.objects.using('db_study_43en').filter(
                USUBJID=instance.USUBJID_id,
                SUBJECT_TYPE='CONTACT'
            ).update(
                INITIAL=initial,
                PHONE=phone
            )
            
            if updated_count > 0:
                logger.info(f"Synced PII for contact {instance.USUBJID_id}: ({updated_count} records)")
    except Exception as e:
        logger.error(f"Error syncing PII for contact: {e}", exc_info=True)


# ==========================================
# ExpectedDates Signal
# ==========================================

@receiver(post_save, sender=ExpectedDates)
def update_followup_status_from_expected_dates(sender, instance, **kwargs):
    """
    ONE-WAY SYNC: ExpectedDates → FollowUpStatus
    """
    try:
        patient = instance.USUBJID
        initial, phone = get_patient_pii(patient)
        
        # Check V2 completion (Sample)
        try:
            sample_v2 = SAM_CASE.objects.using('db_study_43en').get(USUBJID=patient, SAMPLE_TYPE='2')
            v2_actual_date = sample_v2.SAMPLEDATE if sample_v2.SAMPLE else None
            v2_status = 'COMPLETED' if sample_v2.SAMPLE else 'UPCOMING'
        except SAM_CASE.DoesNotExist:
            v2_actual_date = None
            v2_status = 'UPCOMING'
        
        # Check V3 completion (FU_CASE_28)
        try:
            followup_v3 = FU_CASE_28.objects.using('db_study_43en').get(USUBJID=patient)
            v3_actual_date = followup_v3.EvaluateDate if followup_v3.EvaluatedAtDay28 == 'Yes' else None
            v3_status = 'COMPLETED' if followup_v3.EvaluatedAtDay28 == 'Yes' else 'UPCOMING'
        except FU_CASE_28.DoesNotExist:
            v3_actual_date = None
            v3_status = 'UPCOMING'
        
        # Check V4 completion (FU_CASE_90)
        try:
            followup_v4 = FU_CASE_90.objects.using('db_study_43en').get(USUBJID=patient)
            v4_actual_date = followup_v4.EvaluateDate if followup_v4.EvaluatedAtDay90 == 'Yes' else None
            v4_status = 'COMPLETED' if followup_v4.EvaluatedAtDay90 == 'Yes' else 'UPCOMING'
        except FU_CASE_90.DoesNotExist:
            v4_actual_date = None
            v4_status = 'UPCOMING'
        
        # Update V2
        if instance.V2_EXPECTED_DATE:
            FollowUpStatus.objects.using('db_study_43en').update_or_create(
                USUBJID=patient.USUBJID_id,
                SUBJECT_TYPE='PATIENT',
                VISIT='V2',
                defaults={
                    'INITIAL': initial,
                    'PHONE': phone,
                    'EXPECTED_FROM': instance.V2_EXPECTED_FROM,
                    'EXPECTED_TO': instance.V2_EXPECTED_TO,
                    'EXPECTED_DATE': instance.V2_EXPECTED_DATE,
                    'ACTUAL_DATE': v2_actual_date,
                    'STATUS': v2_status,
                }
            )
        
        # Update V3
        if instance.V3_EXPECTED_DATE:
            FollowUpStatus.objects.using('db_study_43en').update_or_create(
                USUBJID=patient.USUBJID_id,
                SUBJECT_TYPE='PATIENT',
                VISIT='V3',
                defaults={
                    'INITIAL': initial,
                    'PHONE': phone,
                    'EXPECTED_FROM': instance.V3_EXPECTED_FROM,
                    'EXPECTED_TO': instance.V3_EXPECTED_TO,
                    'EXPECTED_DATE': instance.V3_EXPECTED_DATE,
                    'ACTUAL_DATE': v3_actual_date,
                    'STATUS': v3_status,
                }
            )
        
        # Update V4
        if instance.V4_EXPECTED_DATE:
            FollowUpStatus.objects.using('db_study_43en').update_or_create(
                USUBJID=patient.USUBJID_id,
                SUBJECT_TYPE='PATIENT',
                VISIT='V4',
                defaults={
                    'INITIAL': initial,
                    'PHONE': phone,
                    'EXPECTED_FROM': instance.V4_EXPECTED_FROM,
                    'EXPECTED_TO': instance.V4_EXPECTED_TO,
                    'EXPECTED_DATE': instance.V4_EXPECTED_DATE,
                    'ACTUAL_DATE': v4_actual_date,
                    'STATUS': v4_status,
                }
            )
            
    except Exception as e:
        logger.error(f"Error in update_followup_status_from_expected_dates: {e}", exc_info=True)


@receiver(post_save, sender=ContactExpectedDates)
def update_followup_status_from_contact_expected_dates(sender, instance, **kwargs):
    """
    ONE-WAY SYNC: ContactExpectedDates → FollowUpStatus
    """
    try:
        contact = instance.USUBJID
        initial, phone = get_contact_pii(contact)
        
        # Check V2 completion (FU_CONTACT_28)
        try:
            followup_v2 = FU_CONTACT_28.objects.using('db_study_43en').get(USUBJID=contact)
            v2_actual_date = followup_v2.EvaluateDate if followup_v2.EvaluatedAtDay28 == 'Yes' else None
            v2_status = 'COMPLETED' if followup_v2.EvaluatedAtDay28 == 'Yes' else 'UPCOMING'
        except FU_CONTACT_28.DoesNotExist:
            v2_actual_date = None
            v2_status = 'UPCOMING'
        
        # Check V3 completion (FU_CONTACT_90)
        try:
            followup_v3 = FU_CONTACT_90.objects.using('db_study_43en').get(USUBJID=contact)
            v3_actual_date = followup_v3.EvaluateDate if followup_v3.EvaluatedAtDay90 == 'Yes' else None
            v3_status = 'COMPLETED' if followup_v3.EvaluatedAtDay90 == 'Yes' else 'UPCOMING'
        except FU_CONTACT_90.DoesNotExist:
            v3_actual_date = None
            v3_status = 'UPCOMING'
        
        # Update V2
        if instance.V2_EXPECTED_DATE:
            FollowUpStatus.objects.using('db_study_43en').update_or_create(
                USUBJID=contact.USUBJID_id,
                SUBJECT_TYPE='CONTACT',
                VISIT='V2',
                defaults={
                    'INITIAL': initial,
                    'PHONE': phone,
                    'EXPECTED_FROM': instance.V2_EXPECTED_FROM,
                    'EXPECTED_TO': instance.V2_EXPECTED_TO,
                    'EXPECTED_DATE': instance.V2_EXPECTED_DATE,
                    'ACTUAL_DATE': v2_actual_date,
                    'STATUS': v2_status,
                }
            )
        
        # Update V3
        if instance.V3_EXPECTED_DATE:
            FollowUpStatus.objects.using('db_study_43en').update_or_create(
                USUBJID=contact.USUBJID_id,
                SUBJECT_TYPE='CONTACT',
                VISIT='V3',
                defaults={
                    'INITIAL': initial,
                    'PHONE': phone,
                    'EXPECTED_FROM': instance.V3_EXPECTED_FROM,
                    'EXPECTED_TO': instance.V3_EXPECTED_TO,
                    'EXPECTED_DATE': instance.V3_EXPECTED_DATE,
                    'ACTUAL_DATE': v3_actual_date,
                    'STATUS': v3_status,
                }
            )
            
    except Exception as e:
        logger.error(f"Error in update_followup_status_from_contact_expected_dates: {e}", exc_info=True)


# ==========================================
# CRF FORM SIGNALS
# ==========================================

@receiver(post_save, sender=FU_CASE_28)
def sync_fu_case_28_to_followup_status(sender, instance, created, **kwargs):
    """TWO-WAY SYNC: FU_CASE_28 ↔ FollowUpStatus"""
    try:
        actual_date = instance.EvaluateDate if instance.EvaluatedAtDay28 == 'Yes' else None
        status = 'COMPLETED' if instance.EvaluatedAtDay28 == 'Yes' else 'UPCOMING'
        
        patient = instance.USUBJID
        initial, phone = get_patient_pii(patient)
        
        followup_status, status_created = FollowUpStatus.objects.using('db_study_43en').update_or_create(
            USUBJID=instance.USUBJID.USUBJID.USUBJID,
            SUBJECT_TYPE='PATIENT',
            VISIT='V3',
            defaults={
                'ACTUAL_DATE': actual_date,
                'STATUS': status,
                'INITIAL': initial,
                'PHONE': phone,
            }
        )
        
        logger.info(f"{'Created' if status_created else 'Updated'} FollowUpStatus V3 for {instance.USUBJID.USUBJID.USUBJID}: {status}")
        
    except Exception as e:
        logger.error(f"Error syncing FU_CASE_28: {e}", exc_info=True)


@receiver(post_save, sender=FU_CASE_90)
def sync_fu_case_90_to_followup_status(sender, instance, **kwargs):
    """TWO-WAY SYNC: FU_CASE_90 ↔ FollowUpStatus"""
    try:
        actual_date = instance.EvaluateDate if instance.EvaluatedAtDay90 == 'Yes' else None
        status = 'COMPLETED' if instance.EvaluatedAtDay90 == 'Yes' else 'UPCOMING'
        
        patient = instance.USUBJID
        initial, phone = get_patient_pii(patient)
        
        followup_status, status_created = FollowUpStatus.objects.using('db_study_43en').update_or_create(
            USUBJID=instance.USUBJID.USUBJID.USUBJID,
            SUBJECT_TYPE='PATIENT',
            VISIT='V4',
            defaults={
                'ACTUAL_DATE': actual_date,
                'STATUS': status,
                'INITIAL': initial,
                'PHONE': phone,
            }
        )
        
        logger.info(f"{'Created' if status_created else 'Updated'} FollowUpStatus V4 for {instance.USUBJID.USUBJID.USUBJID}: {status}")
        
    except Exception as e:
        logger.error(f"Error syncing FU_CASE_90: {e}", exc_info=True)


@receiver(post_save, sender=FU_CONTACT_28)
def sync_fu_contact_28_to_followup_status(sender, instance, **kwargs):
    """TWO-WAY SYNC: FU_CONTACT_28 ↔ FollowUpStatus"""
    try:
        actual_date = instance.EvaluateDate if instance.EvaluatedAtDay28 == 'Yes' else None
        status = 'COMPLETED' if instance.EvaluatedAtDay28 == 'Yes' else 'UPCOMING'
        
        contact = instance.USUBJID
        initial, phone = get_contact_pii(contact)
        
        followup_status, status_created = FollowUpStatus.objects.using('db_study_43en').update_or_create(
            USUBJID=instance.USUBJID.USUBJID.USUBJID,
            SUBJECT_TYPE='CONTACT',
            VISIT='V2',
            defaults={
                'ACTUAL_DATE': actual_date,
                'STATUS': status,
                'INITIAL': initial,
                'PHONE': phone,
            }
        )
        
        logger.info(f"{'Created' if status_created else 'Updated'} FollowUpStatus V2 for contact {instance.USUBJID.USUBJID.USUBJID}: {status}")
        
    except Exception as e:
        logger.error(f"Error syncing FU_CONTACT_28: {e}", exc_info=True)


@receiver(post_save, sender=FU_CONTACT_90)
def sync_fu_contact_90_to_followup_status(sender, instance, **kwargs):
    """TWO-WAY SYNC: FU_CONTACT_90 ↔ FollowUpStatus"""
    try:
        actual_date = instance.EvaluateDate if instance.EvaluatedAtDay90 == 'Yes' else None
        status = 'COMPLETED' if instance.EvaluatedAtDay90 == 'Yes' else 'UPCOMING'
        
        contact = instance.USUBJID
        initial, phone = get_contact_pii(contact)
        
        followup_status, status_created = FollowUpStatus.objects.using('db_study_43en').update_or_create(
            USUBJID=instance.USUBJID.USUBJID.USUBJID,
            SUBJECT_TYPE='CONTACT',
            VISIT='V3',
            defaults={
                'ACTUAL_DATE': actual_date,
                'STATUS': status,
                'INITIAL': initial,
                'PHONE': phone,
            }
        )
        
        logger.info(f"{'Created' if status_created else 'Updated'} FollowUpStatus V3 for contact {instance.USUBJID.USUBJID.USUBJID}: {status}")
        
    except Exception as e:
        logger.error(f"Error syncing FU_CONTACT_90: {e}", exc_info=True)


@receiver(post_save, sender=SAM_CASE)
def sync_sam_case_to_followup_status(sender, instance, **kwargs):
    """TWO-WAY SYNC: SAM_CASE ↔ FollowUpStatus"""
    if instance.SAMPLE_TYPE == '2':
        try:
            actual_date = None
            if instance.SAMPLE:
                actual_date = (instance.STOOLDATE or instance.RECTSWABDATE or 
                             instance.THROATSWABDATE or instance.BLOODDATE)
                            
            status = 'COMPLETED' if instance.SAMPLE else 'UPCOMING'
            
            patient = instance.USUBJID
            initial, phone = get_patient_pii(patient)
            
            followup_status, status_created = FollowUpStatus.objects.using('db_study_43en').update_or_create(
                USUBJID=instance.USUBJID.USUBJID.USUBJID,
                SUBJECT_TYPE='PATIENT',
                VISIT='V2',
                defaults={
                    'ACTUAL_DATE': actual_date,
                    'STATUS': status,
                    'INITIAL': initial,
                    'PHONE': phone,
                }
            )
            
            logger.info(f"{'Created' if status_created else 'Updated'} FollowUpStatus V2 (sample) for {instance.USUBJID.USUBJID.USUBJID}: {status}")
            
        except Exception as e:
            logger.error(f"Error syncing SAM_CASE: {e}", exc_info=True)


# ==========================================
# DELETE SIGNALS
# ==========================================

@receiver(pre_delete, sender=FU_CASE_28)
def delete_followup_status_on_fu28_delete(sender, instance, **kwargs):
    try:
        deleted_count = FollowUpStatus.objects.using('db_study_43en').filter(
            USUBJID=instance.USUBJID.USUBJID.USUBJID,
            SUBJECT_TYPE='PATIENT',
            VISIT='V3'
        ).delete()[0]
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} FollowUpStatus V3 for {instance.USUBJID.USUBJID.USUBJID}")
    except Exception as e:
        logger.error(f"Error deleting FollowUpStatus: {e}", exc_info=True)


@receiver(pre_delete, sender=FU_CASE_90)
def delete_followup_status_on_fu90_delete(sender, instance, **kwargs):
    try:
        deleted_count = FollowUpStatus.objects.using('db_study_43en').filter(
            USUBJID=instance.USUBJID.USUBJID.USUBJID,
            SUBJECT_TYPE='PATIENT',
            VISIT='V4'
        ).delete()[0]
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} FollowUpStatus V4 for {instance.USUBJID.USUBJID.USUBJID}")
    except Exception as e:
        logger.error(f"Error deleting FollowUpStatus: {e}", exc_info=True)


@receiver(pre_delete, sender=FU_CONTACT_28)
def delete_followup_status_on_contact28_delete(sender, instance, **kwargs):
    try:
        deleted_count = FollowUpStatus.objects.using('db_study_43en').filter(
            USUBJID=instance.USUBJID.USUBJID.USUBJID,
            SUBJECT_TYPE='CONTACT',
            VISIT='V2'
        ).delete()[0]
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} FollowUpStatus V2 for contact {instance.USUBJID.USUBJID.USUBJID}")
    except Exception as e:
        logger.error(f"Error deleting FollowUpStatus: {e}", exc_info=True)


@receiver(pre_delete, sender=FU_CONTACT_90)
def delete_followup_status_on_contact90_delete(sender, instance, **kwargs):
    try:
        deleted_count = FollowUpStatus.objects.using('db_study_43en').filter(
            USUBJID=instance.USUBJID.USUBJID.USUBJID,
            SUBJECT_TYPE='CONTACT',
            VISIT='V3'
        ).delete()[0]
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} FollowUpStatus V3 for contact {instance.USUBJID.USUBJID.USUBJID}")
    except Exception as e:
        logger.error(f"Error deleting FollowUpStatus: {e}", exc_info=True)


@receiver(pre_delete, sender=SAM_CASE)
def delete_followup_status_on_sample_delete(sender, instance, **kwargs):
    if instance.SAMPLE_TYPE == '2':
        try:
            deleted_count = FollowUpStatus.objects.using('db_study_43en').filter(
                USUBJID=instance.USUBJID.USUBJID.USUBJID,
                SUBJECT_TYPE='PATIENT',
                VISIT='V2'
            ).delete()[0]
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} FollowUpStatus V2 (sample) for {instance.USUBJID.USUBJID.USUBJID}")
        except Exception as e:
            logger.error(f"Error deleting FollowUpStatus: {e}", exc_info=True)