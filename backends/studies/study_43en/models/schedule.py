# backends/studies/study_43en/models/schedule.py
"""
Schedule and Follow-up Models
Manages expected dates, calendars, and follow-up status tracking
"""
from datetime import date
from django.db import models
from django.utils.translation import gettext_lazy as _
from encrypted_model_fields.fields import EncryptedCharField

from backends.studies.study_43en.study_site_manage import SiteFilteredManager


class ExpectedDates(models.Model):
    """
    Expected visit dates for enrolled patients
    Auto-calculated based on enrollment date
    """
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManager()
    
    # Primary relationship
    USUBJID = models.OneToOneField('ENR_CASE',
        on_delete=models.CASCADE,
        related_name='expected_dates',
        to_field='USUBJID',
        db_column='USUBJID',
        verbose_name=_('Patient')
    )
    
    # Enrollment
    ENROLLMENT_DATE = models.DateField(
        null=True,
        blank=True,
        #db_index=True,
        verbose_name=_('Enrollment Date')
    )
    
    # Visit 2 (Day 7 ± 1)
    V2_EXPECTED_FROM = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V2 Expected From')
    )
    V2_EXPECTED_TO = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V2 Expected To')
    )
    V2_EXPECTED_DATE = models.DateField(
        null=True,
        blank=True,
        #db_index=True,
        verbose_name=_('V2 Expected Date')
    )
    
    # Visit 3 (Day 28 ± 3)
    V3_EXPECTED_FROM = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V3 Expected From')
    )
    V3_EXPECTED_TO = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V3 Expected To')
    )
    V3_EXPECTED_DATE = models.DateField(
        null=True,
        blank=True,
        #db_index=True,
        verbose_name=_('V3 Expected Date')
    )
    
    # Visit 4 (Day 90 ± 3)
    V4_EXPECTED_FROM = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V4 Expected From')
    )
    V4_EXPECTED_TO = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V4 Expected To')
    )
    V4_EXPECTED_DATE = models.DateField(
        null=True,
        blank=True,
        #db_index=True,
        verbose_name=_('V4 Expected Date')
    )
    
    # Metadata
    CREATED_AT = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    UPDATED_AT = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )

    class Meta:
        db_table = 'expected_dates'
        verbose_name = _('Expected Date')
        verbose_name_plural = _('Expected Dates')
        indexes = [
            models.Index(fields=['ENROLLMENT_DATE'], name='idx_ed_enroll'),
            models.Index(fields=['V2_EXPECTED_DATE'], name='idx_ed_v2'),
            models.Index(fields=['V3_EXPECTED_DATE'], name='idx_ed_v3'),
            models.Index(fields=['V4_EXPECTED_DATE'], name='idx_ed_v4'),
        ]

    def __str__(self):
        return f"Expected dates for {self.USUBJID.USUBJID}"

    def auto_map_from_calendar(self):
        """
        Auto-populate visit dates from ExpectedCalendar
        based on ENROLLMENT_DATE
        
        Returns:
            bool: True if mapping successful, False otherwise
        """
        if not self.ENROLLMENT_DATE:
            return False

        calendar = ExpectedCalendar.objects.using('db_study_43en').filter(
            ENROLLMENT_DATE=self.ENROLLMENT_DATE
        ).first()
        
        if not calendar:
            return False

        # Map all visit dates
        self.V2_EXPECTED_FROM = calendar.V2_EXPECTED_FROM
        self.V2_EXPECTED_TO = calendar.V2_EXPECTED_TO
        self.V2_EXPECTED_DATE = calendar.V2_EXPECTED_DATE
        self.V3_EXPECTED_FROM = calendar.V3_EXPECTED_FROM
        self.V3_EXPECTED_TO = calendar.V3_EXPECTED_TO
        self.V3_EXPECTED_DATE = calendar.V3_EXPECTED_DATE
        self.V4_EXPECTED_FROM = calendar.V4_EXPECTED_FROM
        self.V4_EXPECTED_TO = calendar.V4_EXPECTED_TO
        self.V4_EXPECTED_DATE = calendar.V4_EXPECTED_DATE
        
        self.save(using='db_study_43en', update_fields=[
            'V2_EXPECTED_FROM', 'V2_EXPECTED_TO', 'V2_EXPECTED_DATE',
            'V3_EXPECTED_FROM', 'V3_EXPECTED_TO', 'V3_EXPECTED_DATE',
            'V4_EXPECTED_FROM', 'V4_EXPECTED_TO', 'V4_EXPECTED_DATE'
        ])
        
        return True

    @classmethod
    def auto_map_all(cls):
        """
        Batch mapping for all ExpectedDates records
        Useful for initial data setup or bulk updates
        """
        success_count = 0
        for obj in cls.objects.using('db_study_43en').all():
            if obj.auto_map_from_calendar():
                success_count += 1
        return success_count


class ContactExpectedDates(models.Model):
    """
    Expected visit dates for enrolled contacts
    Auto-calculated based on enrollment date
    """
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManager()
    
    # Primary relationship
    USUBJID = models.OneToOneField('ENR_CONTACT',
        on_delete=models.CASCADE,
        related_name='expected_dates',
        to_field='USUBJID',
        db_column='USUBJID',
        verbose_name=_('Contact')
    )
    
    # Enrollment
    ENROLLMENT_DATE = models.DateField(
        null=True,
        blank=True,
        #db_index=True,
        verbose_name=_('Enrollment Date')
    )
    
    # Visit 2 (Day 28 ± 3) - Note: Contacts don't have V1
    V2_EXPECTED_FROM = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V2 Expected From')
    )
    V2_EXPECTED_TO = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V2 Expected To')
    )
    V2_EXPECTED_DATE = models.DateField(
        null=True,
        blank=True,
        #db_index=True,
        verbose_name=_('V2 Expected Date')
    )
    
    # Visit 3 (Day 90 ± 3)
    V3_EXPECTED_FROM = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V3 Expected From')
    )
    V3_EXPECTED_TO = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V3 Expected To')
    )
    V3_EXPECTED_DATE = models.DateField(
        null=True,
        blank=True,
        #db_index=True,
        verbose_name=_('V3 Expected Date')
    )
    
    # Metadata
    CREATED_AT = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    UPDATED_AT = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )

    class Meta:
        db_table = 'contact_expected_dates'
        verbose_name = _('Contact Expected Date')
        verbose_name_plural = _('Contact Expected Dates')
        indexes = [
            models.Index(fields=['ENROLLMENT_DATE'], name='idx_ced_enroll'),
            models.Index(fields=['V2_EXPECTED_DATE'], name='idx_ced_v2'),
            models.Index(fields=['V3_EXPECTED_DATE'], name='idx_ced_v3'),
        ]

    def __str__(self):
        return f"Expected dates for {self.USUBJID.USUBJID}"

    def auto_map_from_calendar(self):
        """
        Auto-populate visit dates from ExpectedCalendar
        based on ENROLLMENT_DATE
        
        Returns:
            bool: True if mapping successful, False otherwise
        """
        if not self.ENROLLMENT_DATE:
            return False

        calendar = ExpectedCalendar.objects.using('db_study_43en').filter(
            ENROLLMENT_DATE=self.ENROLLMENT_DATE
        ).first()
        
        if not calendar:
            return False

        # Map visit dates (V2 and V3 only for contacts)
        self.V2_EXPECTED_FROM = calendar.V2_EXPECTED_FROM
        self.V2_EXPECTED_TO = calendar.V2_EXPECTED_TO
        self.V2_EXPECTED_DATE = calendar.V2_EXPECTED_DATE
        self.V3_EXPECTED_FROM = calendar.V3_EXPECTED_FROM
        self.V3_EXPECTED_TO = calendar.V3_EXPECTED_TO
        self.V3_EXPECTED_DATE = calendar.V3_EXPECTED_DATE
        
        self.save(using='db_study_43en', update_fields=[
            'V2_EXPECTED_FROM', 'V2_EXPECTED_TO', 'V2_EXPECTED_DATE',
            'V3_EXPECTED_FROM', 'V3_EXPECTED_TO', 'V3_EXPECTED_DATE'
        ])
        
        return True

    @classmethod
    def auto_map_all(cls):
        """
        Batch mapping for all ContactExpectedDates records
        Useful for initial data setup or bulk updates
        """
        success_count = 0
        for obj in cls.objects.using('db_study_43en').all():
            if obj.auto_map_from_calendar():
                success_count += 1
        return success_count


class ExpectedCalendar(models.Model):
    """
    Master calendar for visit date calculations
    Pre-calculated expected visit windows based on enrollment date
    """
    
    # Managers
    objects = models.Manager()
    # Note: No site filtering needed as this is a lookup table
    
    # Enrollment date (used as lookup key)
    ENROLLMENT_DATE = models.DateField(
        unique=True,
        #db_index=True,
        verbose_name=_('Enrollment Date')
    )
    
    # Visit 2 (Day 7 ± 1)
    V2_EXPECTED_FROM = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V2 Expected From')
    )
    V2_EXPECTED_TO = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V2 Expected To')
    )
    V2_EXPECTED_DATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V2 Expected Date')
    )
    
    # Visit 3 (Day 28 ± 3)
    V3_EXPECTED_FROM = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V3 Expected From')
    )
    V3_EXPECTED_TO = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V3 Expected To')
    )
    V3_EXPECTED_DATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V3 Expected Date')
    )
    
    # Visit 4 (Day 90 ± 3)
    V4_EXPECTED_FROM = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V4 Expected From')
    )
    V4_EXPECTED_TO = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V4 Expected To')
    )
    V4_EXPECTED_DATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('V4 Expected Date')
    )

    class Meta:
        db_table = 'expected_calender'  
        verbose_name = _('Expected Calendar')
        verbose_name_plural = _('Expected Calendars')
        ordering = ['ENROLLMENT_DATE']
        indexes = [
            models.Index(fields=['ENROLLMENT_DATE'], name='idx_cal_enroll'),
        ]

    def __str__(self):
        return f"Calendar for {self.ENROLLMENT_DATE}"


class FollowUpStatus(models.Model):
    """
    Follow-up status tracking for patients and contacts
    Automatically updated based on expected dates and actual visit dates
    """
    
    
    SUBJECT_TYPE_CHOICES = [
        ('PATIENT', _('Patient')),
        ('CONTACT', _('Contact')),
    ]
    
    VISIT_CHOICES = [
        ('V2', _('Visit 2')),
        ('V3', _('Visit 3')),
        ('V4', _('Visit 4')),
    ]
    
    STATUS_CHOICES = [
        ('COMPLETED', _('Completed')),
        ('LATE', _('Late')),
        ('MISSED', _('Missed')),
        ('UPCOMING', _('Upcoming')),
    ]
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManager()
    
    # Subject identification
    USUBJID = models.CharField(
        max_length=50,
        #db_index=True,
        verbose_name=_('Subject ID')
    )
    SUBJECT_TYPE = models.CharField(
        max_length=10,
        choices=SUBJECT_TYPE_CHOICES,
        #db_index=True,
        verbose_name=_('Subject Type')
    )
    INITIAL = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('Initial')
    )
    
    # Visit information
    VISIT = models.CharField(
        max_length=10,
        choices=VISIT_CHOICES,
        #db_index=True,
        verbose_name=_('Visit')
    )
    
    # Expected window (from ExpectedDates/ContactExpectedDates)
    EXPECTED_FROM = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Expected From')
    )
    EXPECTED_TO = models.DateField(
        null=True,
        blank=True,
        #db_index=True,
        verbose_name=_('Expected To')
    )
    EXPECTED_DATE = models.DateField(
        null=True,
        blank=True,
        #db_index=True,
        verbose_name=_('Expected Date')
    )
    
    # Actual visit
    ACTUAL_DATE = models.DateField(
        null=True,
        blank=True,
        #db_index=True,
        verbose_name=_('Actual Visit Date')
    )

    MISSED_DATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Missed Date')
    )

    MISSED_REASON = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Missed Reason')
    )

    STATUS = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='UPCOMING',
        #db_index=True,
        verbose_name=_('Status')
    )
    
    # Contact information
    PHONE = EncryptedCharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('Phone Number')
    )
    
    # Metadata
    CREATED_AT = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    UPDATED_AT = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )
    
    class Meta:
        db_table = 'follow_up_status'
        verbose_name = _('Follow-up Status')
        verbose_name_plural = _('Follow-up Statuses')
        unique_together = ('USUBJID', 'SUBJECT_TYPE', 'VISIT')
        ordering = ['SUBJECT_TYPE', 'EXPECTED_DATE']
        indexes = [
            models.Index(fields=['SUBJECT_TYPE', 'STATUS'], name='idx_fus_type_status'),
            models.Index(fields=['EXPECTED_DATE', 'STATUS'], name='idx_fus_date_status'),
            models.Index(fields=['USUBJID', 'VISIT'], name='idx_fus_subj_visit'),
        ]
    
    def __str__(self):
        subject_type_display = dict(self.SUBJECT_TYPE_CHOICES).get(self.SUBJECT_TYPE, self.SUBJECT_TYPE)
        visit_display = dict(self.VISIT_CHOICES).get(self.VISIT, self.VISIT)
        return f"{self.USUBJID} ({subject_type_display}) - {visit_display}"
    
    def save(self, *args, **kwargs):
        """
        Auto-update status based on dates
        UPDATED: COMPLETED > MISSED (manual) > LATE > UPCOMING
        """
        update_fields = kwargs.get('update_fields', None)
        if update_fields and 'STATUS' in update_fields:
            super().save(*args, **kwargs)
            return
        
        if self.STATUS in ['COMPLETED', 'MISSED']:
            super().save(*args, **kwargs)
            return
        
        today = date.today()
        
        if self.ACTUAL_DATE:
            self.STATUS = 'COMPLETED'
        elif self.MISSED_DATE:
            #  NEW: Manual missed
            self.STATUS = 'MISSED'
        elif self.EXPECTED_TO and today > self.EXPECTED_TO:
            #  CHANGED: Past expected_to → LATE (not MISSED)
            self.STATUS = 'LATE'
        elif self.EXPECTED_DATE and today > self.EXPECTED_DATE and today <= self.EXPECTED_TO:
            self.STATUS = 'LATE'
        elif self.EXPECTED_FROM and today >= self.EXPECTED_FROM and today <= self.EXPECTED_TO:
            self.STATUS = 'UPCOMING'
        elif self.EXPECTED_DATE and today < self.EXPECTED_FROM:
            self.STATUS = 'UPCOMING'
        else:
            self.STATUS = 'UPCOMING'
        
        super().save(*args, **kwargs)
    
    def update_from_expected_dates(self):
        """
        Update expected date fields from ExpectedDates or ContactExpectedDates
        based on SUBJECT_TYPE
        """
        if self.SUBJECT_TYPE == 'PATIENT':
            try:
                expected = ExpectedDates.objects.using('db_study_43en').get(USUBJID__USUBJID=self.USUBJID)
            except ExpectedDates.DoesNotExist:
                return False
        else:  # CONTACT
            try:
                expected = ContactExpectedDates.objects.using('db_study_43en').get(USUBJID__USUBJID=self.USUBJID)
            except ContactExpectedDates.DoesNotExist:
                return False
        
        # Map visit fields
        visit_map = {
            'V2': ('V2_EXPECTED_FROM', 'V2_EXPECTED_TO', 'V2_EXPECTED_DATE'),
            'V3': ('V3_EXPECTED_FROM', 'V3_EXPECTED_TO', 'V3_EXPECTED_DATE'),
            'V4': ('V4_EXPECTED_FROM', 'V4_EXPECTED_TO', 'V4_EXPECTED_DATE'),
        }
        
        if self.VISIT in visit_map:
            from_field, to_field, date_field = visit_map[self.VISIT]
            self.EXPECTED_FROM = getattr(expected, from_field)
            self.EXPECTED_TO = getattr(expected, to_field)
            self.EXPECTED_DATE = getattr(expected, date_field)
            self.save(using='db_study_43en', update_fields=['EXPECTED_FROM', 'EXPECTED_TO', 'EXPECTED_DATE'])
            return True
        
        return False