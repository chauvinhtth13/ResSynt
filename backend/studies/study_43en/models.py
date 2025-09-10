from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import JSONField
from datetime import datetime, date, timedelta
import json
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import transaction
import json

class ScreeningCase(models.Model):
    SCRID = models.CharField(_("Screening ID"), max_length=50, primary_key=True, db_index=True)
    USUBJID = models.CharField(_("USUBJID"), max_length=50, unique=True, db_index=True) 
    STUDYID = models.CharField(_("Study ID"), max_length=50, db_index=True)
    SITEID = models.CharField(_("Site ID"), max_length=20, db_index=True)
    SUBJID = models.CharField(_("Patient ID"), max_length=50, db_index=True)
    INITIAL = models.CharField(_("Initials"), max_length=10)
    UPPER16AGE = models.BooleanField(_("Over 16 years old"), default=False)
    INFPRIOR2OR48HRSADMIT = models.BooleanField(_("Infection 2 or 48 hours prior to admission"), default=False)
    ISOLATEDKPNFROMINFECTIONORBLOOD = models.BooleanField(_("KPN isolated from infection or blood"), default=False)
    KPNISOUNTREATEDSTABLE = models.BooleanField(_("Untreated, stable KPN"), default=False)
    CONSENTTOSTUDY = models.BooleanField(_("Consent to study"), default=False)
    SCREENINGFORMDATE = models.DateField(_("Screening form date"), null=True, blank=True, db_index=True)
    COMPLETEDBY = models.CharField(_("Completed by"), max_length=50, null=True, blank=True)
    COMPLETEDDATE = models.DateField(_("Completion date"), null=True, blank=True, db_index=True)
    ENTRY = models.IntegerField(_("Entry"), null=True, blank=True)
    ENTEREDTIME = models.DateTimeField(_("Entry time"), null=True, blank=True, db_index=True)
    CONFIRMED = models.BooleanField(_("Confirmed"), null=True, blank=True, default=False)
    UNRECRUITED_REASON = models.CharField(_("Reason for non-recruitment"), max_length=255, null=True, blank=True)
    WARD = models.CharField(_("Ward/Department"), max_length=255, null=True, blank=True)
    is_confirmed = models.BooleanField(_("Confirmed"), default=False, db_index=True)

    # Metadata fields
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'study_43en_screeningcase'
        verbose_name = _("Patient screening")
        verbose_name_plural = _("Patient screening")
        ordering = ['-SCREENINGFORMDATE', '-created_at']
        indexes = [
            models.Index(fields=['SITEID', 'is_confirmed']),
            models.Index(fields=['STUDYID', 'SITEID']),
            models.Index(fields=['SCREENINGFORMDATE', 'is_confirmed']),
        ]

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if not self.SCRID:
                # Optimize SCRID creation
                last_case = ScreeningCase.objects.select_for_update().filter(
                    SCRID__startswith='PS'
                ).order_by('-SCRID').first()
                
                if last_case:
                    try:
                        last_num = int(last_case.SCRID[2:])
                        self.SCRID = f"PS{last_num + 1:04d}"
                    except (ValueError, IndexError):
                        self.SCRID = "PS0001"
                else:
                    self.SCRID = "PS0001"

            # Logic to create SUBJID and USUBJID
            if self._should_generate_ids():
                self._generate_subject_ids()
                self.is_confirmed = True
            else:
                self.SUBJID = None
                self.USUBJID = None
                self.is_confirmed = False

            super().save(*args, **kwargs)

    def _should_generate_ids(self):
        """Check conditions to create SUBJID and USUBJID"""
        return (
            self.UPPER16AGE and 
            self.INFPRIOR2OR48HRSADMIT and
            self.ISOLATEDKPNFROMINFECTIONORBLOOD and 
            not self.KPNISOUNTREATEDSTABLE and
            self.CONSENTTOSTUDY
        )

    def _generate_subject_ids(self):
        """Create SUBJID and USUBJID"""
        if not self.SUBJID:
            last_case = ScreeningCase.objects.filter(
                SITEID=self.SITEID,
                SUBJID__isnull=False,
                SUBJID__startswith='A-'
            ).order_by('-SUBJID').first()
            
            if last_case and last_case.SUBJID:
                try:
                    last_number = int(last_case.SUBJID.split('-')[-1])
                    next_number = last_number + 1
                except (ValueError, IndexError):
                    next_number = 1
            else:
                next_number = 1
            
            self.SUBJID = f"A-{next_number:03d}"

        if not self.USUBJID:
            if not self.SITEID or not self.SUBJID:
                raise ValueError("SITEID and SUBJID must be provided to create USUBJID")
            
            self.USUBJID = f"{self.SITEID}-{self.SUBJID}"
            
            # Ensure no duplicate USUBJID
            counter = 1
            original_usubjid = self.USUBJID
            while ScreeningCase.objects.filter(USUBJID=self.USUBJID).exclude(pk=self.pk).exists():
                counter += 1
                try:
                    subjid_parts = self.SUBJID.split('-')
                    subjid_number = int(subjid_parts[-1]) + counter - 1
                    self.SUBJID = f"A-{subjid_number:03d}"
                    self.USUBJID = f"{self.SITEID}-{self.SUBJID}"
                except (ValueError, IndexError):
                    self.USUBJID = f"{original_usubjid}-{counter}"

    def __str__(self):
        return self.USUBJID if self.USUBJID else f"PS{self.SCRID}"