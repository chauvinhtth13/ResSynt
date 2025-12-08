from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.functional import cached_property
from django.db import transaction
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin
from datetime import date, timedelta


class SAM_CASE(AuditFieldsMixin):
    """
    Sample collection tracking for enrolled patients
    
    Optimizations:
    - Added AuditFieldsMixin for compliance and version control
    - Comprehensive validation with constraints
    - Cached properties for computed values
    - Better indexes for common queries
    - Query helpers for complex lookups
    - Auto-validation of sample dates and culture results
    """
    
    # ==========================================
    # CHOICES DEFINITIONS
    # ==========================================
    class SampleTypeChoices(models.TextChoices):
        SAMPLE1 = '1', _('Sample 1 (At enrollment)')
        SAMPLE2 = '2', _('Sample 2 (10 ± 3 days after enrollment)')
        SAMPLE3 = '3', _('Sample 3 (28 ± 3 days after enrollment)')
        SAMPLE4 = '4', _('Sample 4 (90 ± 3 days after enrollment)')
    
    class CultureResultChoices(models.TextChoices):
        POSITIVE = 'Pos', _('Positive')
        NEGATIVE = 'Neg', _('Negative')
        NO_APPLY = 'NoApply', _('Not Applicable')
        NOT_PERFORMED = 'NotPerformed', _('Not Performed')
    
    class SampleStatusChoices(models.TextChoices):
        COLLECTED = 'collected', _('Collected')
        NOT_COLLECTED = 'not_collected', _('Not Collected')
        LOST = 'lost', _('Lost/Damaged')
    
    # ==========================================
    # MANAGERS
    # ==========================================
        
    
    # ==========================================
    # PRIMARY KEY & FOREIGN KEY
    # ==========================================
    id = models.AutoField(
        primary_key=True,
        verbose_name=_('Sample Collection ID')
    )
    
    USUBJID = models.ForeignKey(
        'ENR_CASE',
        to_field='USUBJID',
        on_delete=models.CASCADE,
        related_name='sample_collections',
        db_column='USUBJID',
        db_index=True,
        verbose_name=_('Patient ID')
    )
    
    # ==========================================
    # SAMPLE IDENTIFICATION
    # ==========================================
    SAMPLE_TYPE = models.CharField(
        max_length=1,
        choices=SampleTypeChoices.choices,
        db_index=True,
        verbose_name=_('Sample Type')
    )
    
    SAMPLE_STATUS = models.CharField(
        max_length=20,
        choices=SampleStatusChoices.choices,
        db_index=True,
        verbose_name=_('Sample Status')
    )
    
    # ==========================================
    # SAMPLE COLLECTION STATUS
    # ==========================================
    SAMPLE = models.BooleanField(
        default=True,
        verbose_name=_('Sample Collected'),
        help_text=_('Indicates if any sample was collected')
    )
    
    REASONIFNO = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Reason if Not Collected'),
        help_text=_('Required if no sample was collected')
    )
    
    # ==========================================
    # STOOL SAMPLE
    # ==========================================
    STOOL = models.BooleanField(
        default=False,
        verbose_name=_('Stool Sample Collected')
    )
    
    STOOLDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Stool Collection Date')
    )
    
    CULTRES_1 = models.CharField(
        max_length=20,
        choices=CultureResultChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Stool Culture Result')
    )
    
    KLEBPNEU_1 = models.BooleanField(
        default=False,
        verbose_name=_('Klebsiella pneumoniae (Stool)')
    )
    
    OTHERRES_1 = models.BooleanField(
        default=False,
        verbose_name=_('Other Organism (Stool)')
    )
    
    OTHERRESSPECIFY_1 = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Other Organism Specify (Stool)')
    )
    
    # ==========================================
    # RECTAL SWAB
    # ==========================================
    RECTSWAB = models.BooleanField(
        default=False,
        verbose_name=_('Rectal Swab Collected')
    )
    
    RECTSWABDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Rectal Swab Collection Date')
    )
    
    CULTRES_2 = models.CharField(
        max_length=20,
        choices=CultureResultChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Rectal Swab Culture Result')
    )
    
    KLEBPNEU_2 = models.BooleanField(
        default=False,
        verbose_name=_('Klebsiella pneumoniae (Rectal)')
    )
    
    OTHERRES_2 = models.BooleanField(
        default=False,
        verbose_name=_('Other Organism (Rectal)')
    )
    
    OTHERRESSPECIFY_2 = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Other Organism Specify (Rectal)')
    )
    
    # ==========================================
    # THROAT SWAB
    # ==========================================
    THROATSWAB = models.BooleanField(
        default=False,
        verbose_name=_('Throat Swab Collected')
    )
    
    THROATSWABDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Throat Swab Collection Date')
    )
    
    CULTRES_3 = models.CharField(
        max_length=20,
        choices=CultureResultChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Throat Swab Culture Result')
    )
    
    KLEBPNEU_3 = models.BooleanField(
        default=False,
        verbose_name=_('Klebsiella pneumoniae (Throat)')
    )
    
    OTHERRES_3 = models.BooleanField(
        default=False,
        verbose_name=_('Other Organism (Throat)')
    )
    
    OTHERRESSPECIFY_3 = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Other Organism Specify (Throat)')
    )
    
    # ==========================================
    # BLOOD SAMPLE
    # ==========================================
    BLOOD = models.BooleanField(
        default=False,
        verbose_name=_('Blood Sample Collected')
    )
    
    BLOODDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Blood Collection Date')
    )
    
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'SAM_CASE'
        verbose_name = _('Sample Collection')
        verbose_name_plural = _('Sample Collections')
        unique_together = [('USUBJID', 'SAMPLE_TYPE')]
        ordering = ['USUBJID', 'SAMPLE_TYPE']
        indexes = [
            models.Index(fields=['SAMPLE_TYPE'], name='idx_sam_type'),
            models.Index(fields=['USUBJID', 'SAMPLE_TYPE'], name='idx_sam_subj_type'),
            models.Index(fields=['SAMPLE_STATUS', 'SAMPLE_TYPE'], name='idx_sam_status'),
            models.Index(fields=['STOOLDATE'], name='idx_sam_stool_date'),
            models.Index(fields=['RECTSWABDATE'], name='idx_sam_rect_date'),
            models.Index(fields=['THROATSWABDATE'], name='idx_sam_throat_date'),
            models.Index(fields=['BLOODDATE'], name='idx_sam_blood_date'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_sam_modified'),
            # Composite indexes for common queries
            models.Index(fields=['USUBJID', 'KLEBPNEU_1'], name='idx_sam_kleb_stool'),
            models.Index(fields=['USUBJID', 'KLEBPNEU_2'], name='idx_sam_kleb_rect'),
            models.Index(fields=['USUBJID', 'KLEBPNEU_3'], name='idx_sam_kleb_throat'),
        ]
        constraints = [
            # If no sample collected, reason must be provided
            models.CheckConstraint(
                check=(
                    models.Q(SAMPLE=True) |
                    models.Q(REASONIFNO__isnull=False)
                ),
                name='sam_reason_if_not_collected'
            ),
            # If stool collected, date must be provided
            models.CheckConstraint(
                check=(
                    ~models.Q(STOOL=True) |
                    models.Q(STOOLDATE__isnull=False)
                ),
                name='sam_stool_date_required'
            ),
            # If rectal swab collected, date must be provided
            models.CheckConstraint(
                check=(
                    ~models.Q(RECTSWAB=True) |
                    models.Q(RECTSWABDATE__isnull=False)
                ),
                name='sam_rect_date_required'
            ),
            # If throat swab collected, date must be provided
            models.CheckConstraint(
                check=(
                    ~models.Q(THROATSWAB=True) |
                    models.Q(THROATSWABDATE__isnull=False)
                ),
                name='sam_throat_date_required'
            ),
            # If blood collected, date must be provided
            models.CheckConstraint(
                check=(
                    ~models.Q(BLOOD=True) |
                    models.Q(BLOODDATE__isnull=False)
                ),
                name='sam_blood_date_required'
            ),
            # If other organism found, must specify
            models.CheckConstraint(
                check=(
                    ~models.Q(OTHERRES_1=True) |
                    models.Q(OTHERRESSPECIFY_1__isnull=False)
                ),
                name='sam_specify_other_stool'
            ),
            models.CheckConstraint(
                check=(
                    ~models.Q(OTHERRES_2=True) |
                    models.Q(OTHERRESSPECIFY_2__isnull=False)
                ),
                name='sam_specify_other_rect'
            ),
            models.CheckConstraint(
                check=(
                    ~models.Q(OTHERRES_3=True) |
                    models.Q(OTHERRESSPECIFY_3__isnull=False)
                ),
                name='sam_specify_other_throat'
            ),
            # If Klebsiella found, culture result must be positive
            models.CheckConstraint(
                check=(
                    ~models.Q(KLEBPNEU_1=True) |
                    models.Q(CULTRES_1='Pos')
                ),
                name='sam_kleb_requires_pos_stool'
            ),
            models.CheckConstraint(
                check=(
                    ~models.Q(KLEBPNEU_2=True) |
                    models.Q(CULTRES_2='Pos')
                ),
                name='sam_kleb_requires_pos_rect'
            ),
            models.CheckConstraint(
                check=(
                    ~models.Q(KLEBPNEU_3=True) |
                    models.Q(CULTRES_3='Pos')
                ),
                name='sam_kleb_requires_pos_throat'
            ),
        ]
    
    def __str__(self):
        sample_type_display = self.get_SAMPLE_TYPE_display()
        return f"{self.USUBJID_id} - {sample_type_display}"
    
    # ==========================================
    # CACHED PROPERTIES
    # ==========================================
    @cached_property
    def SITEID(self):
        """Get SITEID from related ENR_CASE (cached)"""
        return self.USUBJID.SITEID if self.USUBJID else None
    
    @cached_property
    def expected_collection_date(self):
        """
        Calculate expected collection date based on sample type and enrollment date
        Returns: date or None
        """
        if not self.USUBJID or not self.USUBJID.ENRDATE:
            return None
        
        enrollment_date = self.USUBJID.ENRDATE
        
        # Sample type specific offsets
        offsets = {
            self.SampleTypeChoices.SAMPLE1: 0,      # At enrollment
            self.SampleTypeChoices.SAMPLE2: 10,     # 10 days
            self.SampleTypeChoices.SAMPLE3: 28,     # 28 days
            self.SampleTypeChoices.SAMPLE4: 90,     # 90 days
        }
        
        offset = offsets.get(self.SAMPLE_TYPE, 0)
        return enrollment_date + timedelta(days=offset)
    
    @cached_property
    def collection_window(self):
        """
        Get acceptable collection window (start_date, end_date) based on ±3 days
        Returns: tuple(date, date) or (None, None)
        """
        expected = self.expected_collection_date
        if not expected:
            return (None, None)
        
        # Sample 1 has no window, others have ±3 days
        if self.SAMPLE_TYPE == self.SampleTypeChoices.SAMPLE1:
            return (expected, expected)
        
        return (expected - timedelta(days=3), expected + timedelta(days=3))
    
    @cached_property
    def any_sample_collected(self):
        """Check if any type of sample was collected"""
        return any([self.STOOL, self.RECTSWAB, self.THROATSWAB, self.BLOOD])
    
    @cached_property
    def total_samples_collected(self):
        """Count number of different sample types collected"""
        return sum([self.STOOL, self.RECTSWAB, self.THROATSWAB, self.BLOOD])
    
    @cached_property
    def has_positive_culture(self):
        """Check if any culture result is positive"""
        return any([
            self.CULTRES_1 == self.CultureResultChoices.POSITIVE,
            self.CULTRES_2 == self.CultureResultChoices.POSITIVE,
            self.CULTRES_3 == self.CultureResultChoices.POSITIVE,
        ])
    
    @cached_property
    def has_klebsiella(self):
        """Check if Klebsiella pneumoniae found in any sample"""
        return any([self.KLEBPNEU_1, self.KLEBPNEU_2, self.KLEBPNEU_3])
    
    @cached_property
    def klebsiella_sites(self):
        """List of sites where Klebsiella was found"""
        sites = []
        if self.KLEBPNEU_1:
            sites.append('Stool')
        if self.KLEBPNEU_2:
            sites.append('Rectal')
        if self.KLEBPNEU_3:
            sites.append('Throat')
        return sites
    
    @cached_property
    def collection_completeness(self):
        """
        Calculate collection completeness percentage
        Returns: float (0-100)
        """
        total_possible = 4  # stool, rectal, throat, blood
        collected = self.total_samples_collected
        return (collected / total_possible) * 100 if total_possible > 0 else 0
    
    @cached_property
    def is_within_collection_window(self):
        """
        Check if samples were collected within acceptable time window
        Returns: dict with status for each sample type
        """
        start_date, end_date = self.collection_window
        if not start_date or not end_date:
            return None
        
        status = {}
        if self.STOOLDATE:
            status['stool'] = start_date <= self.STOOLDATE <= end_date
        if self.RECTSWABDATE:
            status['rectal'] = start_date <= self.RECTSWABDATE <= end_date
        if self.THROATSWABDATE:
            status['throat'] = start_date <= self.THROATSWABDATE <= end_date
        if self.BLOODDATE:
            status['blood'] = start_date <= self.BLOODDATE <= end_date
        
        return status
    
    @cached_property
    def days_from_expected(self):
        """
        Calculate days difference from expected collection date
        Returns: dict with days difference for each collected sample
        """
        expected = self.expected_collection_date
        if not expected:
            return None
        
        differences = {}
        if self.STOOLDATE:
            differences['stool'] = (self.STOOLDATE - expected).days
        if self.RECTSWABDATE:
            differences['rectal'] = (self.RECTSWABDATE - expected).days
        if self.THROATSWABDATE:
            differences['throat'] = (self.THROATSWABDATE - expected).days
        if self.BLOODDATE:
            differences['blood'] = (self.BLOODDATE - expected).days
        
        return differences
    
    # ==========================================
    # CULTURE RESULT PROPERTIES
    # ==========================================
    @property
    def stool_culture_positive(self):
        return self.CULTRES_1 == self.CultureResultChoices.POSITIVE
    
    @property
    def rectal_culture_positive(self):
        return self.CULTRES_2 == self.CultureResultChoices.POSITIVE
    
    @property
    def throat_culture_positive(self):
        return self.CULTRES_3 == self.CultureResultChoices.POSITIVE
    
    @property
    def all_cultures_negative(self):
        """Check if all performed cultures are negative"""
        performed_cultures = [
            self.CULTRES_1,
            self.CULTRES_2,
            self.CULTRES_3,
        ]
        performed = [c for c in performed_cultures if c and c != self.CultureResultChoices.NOT_PERFORMED]
        if not performed:
            return None
        return all(c == self.CultureResultChoices.NEGATIVE for c in performed)
    
    # ==========================================
    # VALIDATION
    # ==========================================
    def clean(self):
        """Enhanced validation with comprehensive checks"""
        errors = {}
        
        # Validate sample collection status
        if not self.SAMPLE and not self.REASONIFNO:
            errors['REASONIFNO'] = _(
                'Reason must be provided if no sample was collected'
            )
        
        # Validate that at least one sample type matches SAMPLE flag
        if self.SAMPLE and not self.any_sample_collected:
            errors['SAMPLE'] = _(
                'At least one sample type must be selected if sample was collected'
            )
        
        # Validate dates are provided for collected samples
        date_validations = [
            (self.STOOL, self.STOOLDATE, 'STOOLDATE', 'stool'),
            (self.RECTSWAB, self.RECTSWABDATE, 'RECTSWABDATE', 'rectal swab'),
            (self.THROATSWAB, self.THROATSWABDATE, 'THROATSWABDATE', 'throat swab'),
            (self.BLOOD, self.BLOODDATE, 'BLOODDATE', 'blood'),
        ]
        
        for collected, date_value, field_name, sample_name in date_validations:
            if collected and not date_value:
                errors[field_name] = _(
                    f'Collection date is required when {sample_name} is collected'
                )
        
        # Prepare dates list for enrollment date validation
        all_dates = [
            ('STOOLDATE', self.STOOLDATE),
            ('RECTSWABDATE', self.RECTSWABDATE),
            ('THROATSWABDATE', self.THROATSWABDATE),
            ('BLOODDATE', self.BLOODDATE),
        ]
        
        # Validate collection dates are after enrollment
        #  FIX: Only check if USUBJID_id exists (safer than accessing relation)
        if self.USUBJID_id:
            try:
                enrollment_date = self.USUBJID.ENRDATE
                if enrollment_date:
                    for field_name, date_value in all_dates:
                        if date_value and date_value < enrollment_date:
                            errors[field_name] = _(
                                f'Collection date cannot be before enrollment date ({enrollment_date})'
                            )
            except Exception:
                # If USUBJID not yet saved or accessible, skip validation
                pass
        
        # Validate collection window compliance (warning, not error)
        #  FIX: Wrap in try-except to handle missing USUBJID during creation
        try:
            window_status = self.is_within_collection_window
            if window_status:
                for sample_type, in_window in window_status.items():
                    if not in_window and self.SAMPLE_TYPE != self.SampleTypeChoices.SAMPLE1:
                        # This is a warning, not blocking
                        pass  # Could add to a warnings list if needed
        except Exception:
            # If USUBJID not accessible, skip window validation
            pass
        
        # Validate culture results and organism findings
        culture_validations = [
            (self.KLEBPNEU_1, self.CULTRES_1, 'CULTRES_1', 'stool'),
            (self.KLEBPNEU_2, self.CULTRES_2, 'CULTRES_2', 'rectal'),
            (self.KLEBPNEU_3, self.CULTRES_3, 'CULTRES_3', 'throat'),
        ]
        
        for kleb_found, culture_result, field_name, sample_name in culture_validations:
            if kleb_found and culture_result != self.CultureResultChoices.POSITIVE:
                errors[field_name] = _(
                    f'Culture result must be Positive if Klebsiella found in {sample_name}'
                )
        
        # Validate other organism specification
        other_validations = [
            (self.OTHERRES_1, self.OTHERRESSPECIFY_1, 'OTHERRESSPECIFY_1', 'stool'),
            (self.OTHERRES_2, self.OTHERRESSPECIFY_2, 'OTHERRESSPECIFY_2', 'rectal'),
            (self.OTHERRES_3, self.OTHERRESSPECIFY_3, 'OTHERRESSPECIFY_3', 'throat'),
        ]
        
        for other_found, specification, field_name, sample_name in other_validations:
            if other_found and (not specification or not specification.strip()):
                errors[field_name] = _(
                    f'Please specify other organism found in {sample_name}'
                )
        
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save with auto-calculations and cache management"""
        # Clear cached properties
        self._clear_cache()
        
        # Auto-update SAMPLE flag based on collected samples
        self.SAMPLE = self.any_sample_collected
        
        # Auto-update status based on collection
        if self.any_sample_collected:
            self.SAMPLE_STATUS = self.SampleStatusChoices.COLLECTED
        elif self.REASONIFNO:
            self.SAMPLE_STATUS = self.SampleStatusChoices.NOT_COLLECTED
        
        # Strip whitespace from text fields
        text_fields = ['REASONIFNO', 'OTHERRESSPECIFY_1', 'OTHERRESSPECIFY_2', 'OTHERRESSPECIFY_3']
        for field in text_fields:
            value = getattr(self, field)
            if value:
                setattr(self, field, value.strip())
        
        super().save(*args, **kwargs)
    
    def _clear_cache(self):
        """Clear all cached properties"""
        cache_attrs = [
            '_SITEID', '_expected_collection_date', '_collection_window',
            '_any_sample_collected', '_total_samples_collected',
            '_has_positive_culture', '_has_klebsiella', '_klebsiella_sites',
            '_collection_completeness', '_is_within_collection_window',
            '_days_from_expected'
        ]
        for attr in cache_attrs:
            if hasattr(self, attr):
                delattr(self, attr)
    
    # ==========================================
    # QUERY HELPERS
    # ==========================================
    @classmethod
    def get_by_sample_type(cls, sample_type):
        """Get all collections for a specific sample type"""
        return cls.objects.filter(
            SAMPLE_TYPE=sample_type
        ).select_related('USUBJID', 'USUBJID__USUBJID')
    
    @classmethod
    def get_with_klebsiella(cls):
        """Get collections where Klebsiella was found"""
        return cls.objects.filter(
            models.Q(KLEBPNEU_1=True) |
            models.Q(KLEBPNEU_2=True) |
            models.Q(KLEBPNEU_3=True)
        ).select_related('USUBJID', 'USUBJID__USUBJID')
    
    @classmethod
    def get_positive_cultures(cls):
        """Get collections with at least one positive culture"""
        return cls.objects.filter(
            models.Q(CULTRES_1=cls.CultureResultChoices.POSITIVE) |
            models.Q(CULTRES_2=cls.CultureResultChoices.POSITIVE) |
            models.Q(CULTRES_3=cls.CultureResultChoices.POSITIVE)
        ).select_related('USUBJID', 'USUBJID__USUBJID')
    
    @classmethod
    def get_incomplete_collections(cls):
        """Get collections that are missing some sample types"""
        return cls.objects.filter(
            SAMPLE=True
        ).exclude(
            STOOL=True,
            RECTSWAB=True,
            THROATSWAB=True,
            BLOOD=True
        ).select_related('USUBJID', 'USUBJID__USUBJID')
    
    @classmethod
    def get_by_patient(cls, usubjid):
        """Get all sample collections for a specific patient"""
        return cls.objects.filter(
            USUBJID=usubjid
        ).order_by('SAMPLE_TYPE')
    
    @classmethod
    def get_overdue_collections(cls):
        """
        Get collections that are past their expected window
        (Only for samples 2, 3, 4)
        """
        from django.db.models import F
        from datetime import date
        
        overdue = []
        for sample in cls.objects.filter(
            SAMPLE=False,
            SAMPLE_TYPE__in=['2', '3', '4']
        ).select_related('USUBJID'):
            window_start, window_end = sample.collection_window
            if window_end and date.today() > window_end:
                overdue.append(sample)
        
        return overdue
    
    @classmethod
    def get_collection_summary_by_patient(cls, usubjid):
        """
        Get summary of all collections for a patient
        Returns: dict with collection status and results
        """
        collections = cls.objects.filter(USUBJID=usubjid).order_by('SAMPLE_TYPE')
        
        summary = {
            'total_samples': collections.count(),
            'collected': collections.filter(SAMPLE=True).count(),
            'not_collected': collections.filter(SAMPLE=False).count(),
            'has_klebsiella': False,
            'klebsiella_sites': [],
            'positive_cultures': 0,
            'collections': []
        }
        
        for collection in collections:
            summary['collections'].append({
                'type': collection.get_SAMPLE_TYPE_display(),
                'collected': collection.any_sample_collected,
                'has_klebsiella': collection.has_klebsiella,
                'klebsiella_sites': collection.klebsiella_sites,
                'positive_culture': collection.has_positive_culture,
            })
            
            if collection.has_klebsiella:
                summary['has_klebsiella'] = True
                summary['klebsiella_sites'].extend(collection.klebsiella_sites)
            
            if collection.has_positive_culture:
                summary['positive_cultures'] += 1
        
        summary['klebsiella_sites'] = list(set(summary['klebsiella_sites']))
        
        return summary