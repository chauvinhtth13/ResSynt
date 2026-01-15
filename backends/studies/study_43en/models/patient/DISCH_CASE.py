from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import ObjectDoesNotExist as RelatedObjectDoesNotExist
from django.utils.functional import cached_property
from django.core.validators import MinValueValidator
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin
from datetime import date


class DISCH_CASE(AuditFieldsMixin):
    """
    Hospital discharge information
    Records discharge status, transfers, and outcomes
    
    Optimizations:
    - Added AuditFieldsMixin for compliance (handles audit trail automatically)
    - Enhanced validation for dates and dependencies
    - Cached properties for computed values
    - Better indexes for queries
    - Query helper methods
    - Database constraints for data integrity
    """
    
    # ==========================================
    # CHOICES DEFINITIONS
    # ==========================================
    class DischargeStatusChoices(models.TextChoices):
        RECOVERED = 'Recovered', _('Discharged - Fully Recovered')
        IMPROVED = 'Improved', _('Discharged - Not Fully Recovered')
        DIED = 'Died', _('Death or Moribund')
        TRANSFERRED_LEFT = 'TransferredLeft', _('Transferred/Left Against Medical Advice')
    
    class YesNoNAChoices(models.TextChoices):
        YES = 'Yes', _('Yes')
        NO = 'No', _('No')
        NA = 'NA', _('Not Applicable')
    
    # ==========================================
    # MANAGERS
    # ==========================================
        
    
    # ==========================================
    # PRIMARY KEY
    # ==========================================
    USUBJID = models.OneToOneField(
        'ENR_CASE',
        on_delete=models.CASCADE,
        primary_key=True,
        to_field='USUBJID',
        db_column='USUBJID',
        related_name='discharge',
        verbose_name=_('Patient ID')
    )
    
    # ==========================================
    # HEADER INFORMATION
    # ==========================================
    EVENT = models.CharField(
        max_length=50,
        default='DISCHARGE',
        verbose_name=_('Event')
    )
    
    STUDYID = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name=_('Study ID')
    )
    
    SITEID = models.CharField(
        max_length=5,
        null=True,
        blank=True,
        db_index=True,  # For site-based queries
        verbose_name=_('Site ID')
    )
    
    SUBJID = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name=_('Subject ID')
    )
    
    INITIAL = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name=_('Initial')
    )
    
    # ==========================================
    # DISCHARGE INFORMATION
    # ==========================================
    DISCHDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('1.Date of discharge '),
        help_text=_('Date patient was discharged from hospital')
    )
    
    DISCHSTATUS = models.CharField(
        max_length=20,
        choices=DischargeStatusChoices.choices,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('3. Discharge Status')
    )
    
    DISCHSTATUSDETAIL = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Discharge Status Details')
    )
    
    # ==========================================
    # TRANSFER INFORMATION
    # ==========================================
    TRANSFERHOSP = models.CharField(
        max_length=3,
        choices=YesNoNAChoices.choices,
        default=YesNoNAChoices.NO,
        verbose_name=_('4. Transferred to Another Hospital?')
    )
    
    TRANSFERREASON = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('4a. Transfer Reason'),
        help_text=_('Required if transferred')
    )
    
    TRANSFERLOCATION = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name=_('4b. Place of transfer:'),
        help_text=_('Required if transferred')
    )
    
    # ==========================================
    # DEATH INFORMATION
    # ==========================================
    DEATHATDISCH = models.CharField(
        max_length=3,
        choices=YesNoNAChoices.choices,
        default=YesNoNAChoices.NO,
        db_index=True,  # For mortality analysis
        verbose_name=_('5. Patient died at discharge?')
    )
    
    DEATHCAUSE = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('5. Reason'),
        help_text=_('Required if death occurred')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'DISCH_CASE'
        verbose_name = _('Discharge Case')
        verbose_name_plural = _('Discharge Cases')
        ordering = ['-DISCHDATE']
        indexes = [
            models.Index(fields=['DISCHDATE'], name='idx_disch_date'),
            models.Index(fields=['DISCHSTATUS'], name='idx_disch_status'),
            models.Index(fields=['DEATHATDISCH', 'DISCHDATE'], name='idx_disch_death_date'),
            models.Index(fields=['SITEID', 'DISCHDATE'], name='idx_disch_site_date'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_disch_modified'),
        ]
        constraints = [
            # If transferred, must have transfer info
            models.CheckConstraint(
                condition=(
                    ~models.Q(TRANSFERHOSP='Yes') |
                    (models.Q(TRANSFERREASON__isnull=False) | models.Q(TRANSFERLOCATION__isnull=False))
                ),
                name='disch_transfer_info_required'
            ),
            # If death, must have death cause
            models.CheckConstraint(
                condition=(
                    ~models.Q(DEATHATDISCH='Yes') |
                    models.Q(DEATHCAUSE__isnull=False)
                ),
                name='disch_death_cause_required'
            ),
            # Death status consistency
            models.CheckConstraint(
                condition=(
                    ~models.Q(DEATHATDISCH='Yes') |
                    models.Q(DISCHSTATUS='Died')
                ),
                name='disch_death_status_consistency'
            ),
        ]
    
    def __str__(self):
        status = self.get_DISCHSTATUS_display() if self.DISCHSTATUS else 'Unknown'
        return f"Discharge: {self.USUBJID_id} - {status}"
    
    # ==========================================
    # CACHED PROPERTIES
    # ==========================================
    @cached_property
    def site_id(self):
        """Get SITEID from related ENR_CASE (cached)"""
        return self.USUBJID.SITEID if self.USUBJID else None
    
    @cached_property
    def is_deceased(self):
        """Check if patient died at discharge"""
        return self.DEATHATDISCH == self.YesNoNAChoices.YES
    
    @cached_property
    def is_transferred(self):
        """Check if patient was transferred"""
        return self.TRANSFERHOSP == self.YesNoNAChoices.YES
    
    @cached_property
    def is_recovered(self):
        """Check if patient fully recovered"""
        return self.DISCHSTATUS == self.DischargeStatusChoices.RECOVERED
    
    @cached_property
    def has_death_info(self):
        """Check if death information is complete"""
        return self.is_deceased and bool(self.DEATHCAUSE and self.DEATHCAUSE.strip())
    
    @cached_property
    def has_transfer_info(self):
        """Check if transfer information is complete"""
        return self.is_transferred and (
            (self.TRANSFERREASON and self.TRANSFERREASON.strip()) or
            (self.TRANSFERLOCATION and self.TRANSFERLOCATION.strip())
        )
    
    @property
    def hospital_stay_days(self):
        """Calculate length of hospital stay"""
        if self.DISCHDATE and self.USUBJID and self.USUBJID.ENRDATE:
            delta = self.DISCHDATE - self.USUBJID.ENRDATE
            return delta.days
        return None
    
    @property
    def icd_code_count(self):
        """Count number of ICD codes"""
        return self.icd_codes.count()
    
    
    @property
    def hospital_stay_days(self):
        """Calculate length of hospital stay (admission to discharge)"""
        if self.DISCHDATE and self.USUBJID:
            try:
                # Get admission date from CLI_CASE through ENR_CASE
                clinical_case = self.USUBJID.clinical_case
                if clinical_case and clinical_case.ADMISDATE:
                    delta = self.DISCHDATE - clinical_case.ADMISDATE
                    # +1 để tính cả ngày nhập viện (nhập và xuất cùng ngày = 1 ngày)
                    return delta.days + 1
            except:
                pass
        return None
    
    # ==========================================
    # VALIDATION
    # ==========================================
    def clean(self):
        """Enhanced validation with better error messages"""
        errors = {}
        
        #  FIX: Safe check for USUBJID (may not exist during form validation)
        # Validate discharge date
        if self.DISCHDATE:
            # Check discharge is after enrollment (only if USUBJID is set)
            try:
                if self.USUBJID and hasattr(self.USUBJID, 'ENRDATE') and self.USUBJID.ENRDATE:
                    if self.DISCHDATE < self.USUBJID.ENRDATE:
                        errors['DISCHDATE'] = _('Discharge date cannot be before enrollment date')
            except RelatedObjectDoesNotExist:
                # USUBJID not set yet (during form validation before save)
                pass
        
        # Validate transfer information
        if self.TRANSFERHOSP == self.YesNoNAChoices.YES:
            if not self.TRANSFERREASON and not self.TRANSFERLOCATION:
                errors['TRANSFERREASON'] = _(
                    'Either transfer reason or location must be provided when patient is transferred'
                )
        
        # Validate death information
        if self.DEATHATDISCH == self.YesNoNAChoices.YES:
            if not self.DEATHCAUSE or not self.DEATHCAUSE.strip():
                errors['DEATHCAUSE'] = _('Cause of death is required when patient died at discharge')
            
            # Check consistency with discharge status
            if self.DISCHSTATUS and self.DISCHSTATUS != self.DischargeStatusChoices.DIED:
                errors['DISCHSTATUS'] = _('Discharge status must be "Died" when death occurred')
        
        # Validate death status consistency (only if death is YES)
        # Allow changing DEATHATDISCH from Yes to No - DISCHSTATUS will be auto-cleared in save()
        if self.DISCHSTATUS == self.DischargeStatusChoices.DIED:
            if self.DEATHATDISCH != self.YesNoNAChoices.YES:
                # Only raise error if DEATHCAUSE is still filled (indicates user wants to keep death status)
                if self.DEATHCAUSE and self.DEATHCAUSE.strip():
                    errors['DEATHATDISCH'] = _('Death at discharge must be "Yes" when discharge status is "Died"')
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save with cache management and auto-set fields"""
        # Clear cached properties
        self._clear_cache()
        
        # Strip whitespace from text fields
        if self.DISCHSTATUSDETAIL:
            self.DISCHSTATUSDETAIL = self.DISCHSTATUSDETAIL.strip()
        if self.TRANSFERREASON:
            self.TRANSFERREASON = self.TRANSFERREASON.strip()
        if self.TRANSFERLOCATION:
            self.TRANSFERLOCATION = self.TRANSFERLOCATION.strip()
        if self.DEATHCAUSE:
            self.DEATHCAUSE = self.DEATHCAUSE.strip()
        
        # Auto-populate fields from ENR_CASE if needed
        if self.USUBJID:
            screening = self.USUBJID.USUBJID  # Get SCR_CASE through ENR_CASE
            if not self.STUDYID:
                self.STUDYID = screening.STUDYID
            if not self.SITEID:
                self.SITEID = screening.SITEID
            if not self.SUBJID:
                self.SUBJID = screening.SUBJID
            if not self.INITIAL:
                self.INITIAL = screening.INITIAL
        
        # Auto-set discharge status if death occurred
        if self.DEATHATDISCH == self.YesNoNAChoices.YES:
            self.DISCHSTATUS = self.DischargeStatusChoices.DIED
        # Auto-clear discharge status if death changed from Yes to No
        elif self.DEATHATDISCH == self.YesNoNAChoices.NO:
            if self.DISCHSTATUS == self.DischargeStatusChoices.DIED:
                self.DISCHSTATUS = None  # Clear status - user must select new status
        
        super().save(*args, **kwargs)
    
    def _clear_cache(self):
        """Clear all cached properties"""
        cache_attrs = [
            '_site_id', '_is_deceased', '_is_transferred', '_is_recovered',
            '_has_death_info', '_has_transfer_info'
        ]
        for attr in cache_attrs:
            if hasattr(self, attr):
                delattr(self, attr)
    
    # ==========================================
    # QUERY HELPERS
    # ==========================================
    @classmethod
    def get_deceased_cases(cls):
        """Get all cases where patient died"""
        return cls.objects.filter(
            DEATHATDISCH=cls.YesNoNAChoices.YES
        ).select_related('USUBJID').order_by('-DISCHDATE')
    
    @classmethod
    def get_transferred_cases(cls):
        """Get all cases where patient was transferred"""
        return cls.objects.filter(
            TRANSFERHOSP=cls.YesNoNAChoices.YES
        ).select_related('USUBJID').order_by('-DISCHDATE')
    
    @classmethod
    def get_recovered_cases(cls):
        """Get all cases where patient fully recovered"""
        return cls.objects.filter(
            DISCHSTATUS=cls.DischargeStatusChoices.RECOVERED
        ).select_related('USUBJID').order_by('-DISCHDATE')
    
    @classmethod
    def get_recent_discharges(cls, days=7):
        """Get recent discharges"""
        from datetime import timedelta
        cutoff_date = date.today() - timedelta(days=days)
        return cls.objects.filter(
            DISCHDATE__gte=cutoff_date
        ).select_related('USUBJID').order_by('-DISCHDATE')
    
    @classmethod
    def get_discharges_by_status(cls, status):
        """Get discharges by status"""
        return cls.objects.filter(
            DISCHSTATUS=status
        ).select_related('USUBJID').order_by('-DISCHDATE')
    
    @classmethod
    def get_site_statistics(cls, siteid):
        """Get discharge statistics for a site"""
        from django.db.models import Count, Q
        
        qs = cls.objects.filter(SITEID=siteid)
        
        return {
            'total': qs.count(),
            'recovered': qs.filter(DISCHSTATUS=cls.DischargeStatusChoices.RECOVERED).count(),
            'improved': qs.filter(DISCHSTATUS=cls.DischargeStatusChoices.IMPROVED).count(),
            'died': qs.filter(DEATHATDISCH=cls.YesNoNAChoices.YES).count(),
            'transferred': qs.filter(TRANSFERHOSP=cls.YesNoNAChoices.YES).count(),
        }


class DischargeICD(AuditFieldsMixin):
    """
    ICD-10 codes at discharge
    Multiple diagnosis codes can be assigned per discharge
    
    Optimizations:
    - Added AuditFieldsMixin (handles audit trail automatically)
    - Auto-incrementing ICD_SEQUENCE
    - Enhanced validation
    - Bulk operations support
    - Query helper methods
    """
    
    # ==========================================
    # MANAGERS
    # ==========================================
        
    
    # ==========================================
    # FOREIGN KEY
    # ==========================================
    USUBJID = models.ForeignKey(
        'DISCH_CASE',
        db_column='USUBJID',
        on_delete=models.CASCADE,
        related_name='icd_codes',
        verbose_name=_('Discharge Case')
    )
    
    ICD_SEQUENCE = models.IntegerField(
        validators=[MinValueValidator(1)],
        default=1,
        verbose_name=_('ICD Sequence'),
        help_text=_('Auto-generated if not provided')
    )
    
    # ==========================================
    # ICD CODE INFORMATION
    # ==========================================
    ICDCODE = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_index=True,  # For ICD code searches
        verbose_name=_('2. ICD-10 Code'),
        help_text=_('e.g., A41.5, J18.9')
    )
    
    ICDDETAIL = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Diagnosis Details')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'discharge_icd'
        verbose_name = _('Discharge ICD Code')
        verbose_name_plural = _('Discharge ICD Codes')
        ordering = ['USUBJID', 'ICD_SEQUENCE']
        indexes = [
            models.Index(fields=['USUBJID', 'ICD_SEQUENCE'], name='idx_dicd_subj_seq'),
            models.Index(fields=['ICDCODE'], name='idx_dicd_code'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_dicd_modified'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['USUBJID', 'ICD_SEQUENCE'],
                name='unique_discharge_icd_sequence'
            )
        ]
    
    def __str__(self):
        code_display = self.ICDCODE or 'No code'
        return f"ICD-10.{self.ICD_SEQUENCE}: {code_display} - {self.USUBJID.USUBJID_id}"
    
    @property
    def SITEID(self):
        """Get SITEID from related DISCH_CASE"""
        if not hasattr(self, '_siteid_cache'):
            self._siteid_cache = self.USUBJID.SITEID if self.USUBJID else None
        return self._siteid_cache
    
    def clean(self):
        """Enhanced validation"""
        errors = {}
        
        # ICD code format validation (basic)
        if self.ICDCODE:
            icd_code = self.ICDCODE.strip().upper()
            # Basic ICD-10 format check: Letter + digits (+ optional decimal)
            import re
            if not re.match(r'^[A-Z]\d{2}(\.\d{1,2})?$', icd_code):
                errors['ICDCODE'] = _(
                    'ICD-10 code format should be like: A41, A41.5, J18.9'
                )
        
        # Validate sequence
        if self.ICD_SEQUENCE is not None and self.ICD_SEQUENCE < 1:
            errors['ICD_SEQUENCE'] = _('Sequence number must be positive (≥1)')
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Save with auto-sequence - DISABLED for formset compatibility"""
        # Strip whitespace and normalize
        if self.ICDCODE:
            self.ICDCODE = self.ICDCODE.strip().upper()
        
        if self.ICDDETAIL:
            self.ICDDETAIL = self.ICDDETAIL.strip()
        
        # Clear cache
        if hasattr(self, '_siteid_cache'):
            del self._siteid_cache
        
        super().save(*args, **kwargs)
    
    # ==========================================
    # BULK OPERATIONS
    # ==========================================
    @classmethod
    def bulk_create_for_discharge(cls, discharge_case, icd_list, user=None):
        """
        Efficiently create multiple ICD code records
        
        Args:
            discharge_case: DISCH_CASE instance
            icd_list: List of dicts [{'ICDCODE': ..., 'ICDDETAIL': ...}, ...]
            user: User object for audit trail
        
        Returns:
            List of created DischargeICD instances
        
        Example:
            icds = [
                {'ICDCODE': 'A41.5', 'ICDDETAIL': 'Sepsis due to other Gram-negative organisms'},
                {'ICDCODE': 'J18.9', 'ICDDETAIL': 'Pneumonia, unspecified'},
            ]
            DischargeICD.bulk_create_for_discharge(discharge, icds, request.user)
        """
        from django.db.models import Max
        
        # Get current max sequence
        max_sequence = (
            cls.objects
            .filter(USUBJID=discharge_case)
            .aggregate(Max('ICD_SEQUENCE'))['ICD_SEQUENCE__max']
        ) or 0
        
        # Prepare instances
        instances = []
        for i, icd_data in enumerate(icd_list, start=1):
            instance = cls(
                USUBJID=discharge_case,
                ICD_SEQUENCE=max_sequence + i,
                **icd_data
            )
            
            # Set audit fields if user provided
            if user:
                instance.last_modified_by_id = user.id
                instance.last_modified_by_username = user.username
            
            instances.append(instance)
        
        # Bulk create
        return cls.objects.bulk_create(instances)
    
    @classmethod
    def get_discharge_icd_codes(cls, discharge_case):
        """Get all ICD codes for a discharge"""
        return cls.objects.filter(
            USUBJID=discharge_case
        ).select_related('USUBJID').order_by('ICD_SEQUENCE')
    
    @classmethod
    def search_by_icd_code(cls, icd_code):
        """Search discharges by ICD code"""
        return cls.objects.filter(
            ICDCODE__icontains=icd_code
        ).select_related('USUBJID').order_by('-USUBJID__DISCHDATE')
    
    @classmethod
    def get_icd_statistics(cls):
        """Get ICD code usage statistics"""
        from django.db.models import Count
        
        return cls.objects.values('ICDCODE').annotate(
            count=Count('ICDCODE')
        ).order_by('-count')