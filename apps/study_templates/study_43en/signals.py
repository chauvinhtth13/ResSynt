from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import EnrollmentCase, ExpectedDates

@receiver(post_save, sender=EnrollmentCase)
def create_expected_dates(sender, instance, created, **kwargs):
    print(f"[Signal] EnrollmentCase saved: USUBJID={instance.USUBJID}, ENRDATE={instance.ENRDATE}, created={created}")
    if instance.ENRDATE:
        try:
            obj, created_ed = ExpectedDates.objects.get_or_create(enrollment_case=instance)
            print(f"[Signal] ExpectedDates {'created' if created_ed else 'already exists'} for USUBJID={instance.USUBJID}")
        except Exception as e:
            print(f"[Signal] Error creating ExpectedDates for USUBJID={instance.USUBJID}: {e}")