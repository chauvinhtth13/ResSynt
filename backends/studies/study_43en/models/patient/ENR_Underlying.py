from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from django.db import transaction
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin


class UnderlyingCondition(AuditFieldsMixin):
    """
    Patient's underlying conditions/comorbidities
    
    Optimizations:
    - Cached computed properties
    - Transaction safety for parent updates
    - Efficient condition counting
    """
    
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
        related_name='Underlying_Condition',
        verbose_name=_('Patient ID')
    )
    
    # ==========================================
    # CARDIOVASCULAR CONDITIONS
    # ==========================================
    HEARTFAILURE = models.BooleanField(
        default=False,
        verbose_name=_('Heart Failure')
    )
    
    CAD = models.BooleanField(
        default=False,
        verbose_name=_('Coronary Artery Disease')
    )
    
    HYPERTENSION = models.BooleanField(
        default=False,
        verbose_name=_('Hypertension')
    )
    
    # ==========================================
    # RESPIRATORY CONDITIONS
    # ==========================================
    COPD = models.BooleanField(
        default=False,
        verbose_name=_('COPD/Chronic bronchitis ')
    )
    
    ASTHMA = models.BooleanField(
        default=False,
        verbose_name=_('Asthma')
    )
    
    # ==========================================
    # METABOLIC/ENDOCRINE CONDITIONS
    # ==========================================
    DIABETES = models.BooleanField(
        default=False,
        verbose_name=_('Diabetes Mellitus')
    )
    
    ADRENALINSUFFICIENCY = models.BooleanField(
        default=False,
        verbose_name=_('Adrenal Insufficiency')
    )
    
    # ==========================================
    # GASTROINTESTINAL/HEPATIC CONDITIONS
    # ==========================================
    HEPATITIS = models.BooleanField(
        default=False,
        verbose_name=_('Chronic hepatitis')
    )
    
    CIRRHOSIS = models.BooleanField(
        default=False,
        verbose_name=_('Cirrhosis')
    )
    
    GASTRICULCER = models.BooleanField(
        default=False,
        verbose_name=_('Gastric ulcer')
    )
    
    COLITIS_IBS = models.BooleanField(
        default=False,
        verbose_name=_('Ulcerative colitis/IBS ')
    )
    
    # ==========================================
    # RENAL CONDITIONS
    # ==========================================
    KIDNEYDISEASE = models.BooleanField(
        default=False,
        verbose_name=_('Chronic kidney disease ')
    )
    
    # ==========================================
    # IMMUNOLOGICAL CONDITIONS
    # ==========================================
    AUTOIMMUNE = models.BooleanField(
        default=False,
        verbose_name=_('Autoimmune Disease')
    )
    
    HIV = models.BooleanField(
        default=False,
        verbose_name=_('HIV/AIDS')
    )
    
    # ==========================================
    # ONCOLOGICAL CONDITIONS
    # ==========================================
    CANCER = models.BooleanField(
        default=False,
        verbose_name=_('Cancer')
    )
    
    # ==========================================
    # LIFESTYLE/BEHAVIORAL
    # ==========================================
    ALCOHOLISM = models.BooleanField(
        default=False,
        verbose_name=_('Alcoholism')
    )
    
    # ==========================================
    # FUNCTIONAL STATUS
    # ==========================================
    BEDRIDDEN = models.BooleanField(
        default=False,
        verbose_name=_('Bedridden')
    )
    
    FRAILTY = models.BooleanField(
        default=False,
        verbose_name=_('FRAILTY')
    )
    
    MALNUTRITION_CACHEXIA = models.BooleanField(
        default=False,
        verbose_name=_('Malnutrition/Cachexia')
    )
    
    # ==========================================
    # OTHER CONDITIONS
    # ==========================================
    OTHERDISEASE = models.BooleanField(
        default=False,
        verbose_name=_('Other Disease')
    )
    
    OTHERDISEASESPECIFY = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Other Disease Details'),
        help_text=_('Required if "Other Disease" is checked')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'ENR_UnderlyingCondition'
        verbose_name = _('Patient Underlying Condition')
        verbose_name_plural = _('Patient Underlying Conditions')
        indexes = [
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_und_modified'),
            # Composite indexes for common queries
            models.Index(fields=['DIABETES', 'HEARTFAILURE'], name='idx_und_cardio_met'),
            models.Index(fields=['HIV', 'CANCER'], name='idx_und_immuno'),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    ~models.Q(OTHERDISEASE=True) |
                    models.Q(OTHERDISEASESPECIFY__isnull=False)
                ),
                name='und_specify_other_disease'
            )
        ]
    
    def __str__(self):
        count = self.condition_count
        return f"{self.USUBJID} - {count} condition{'s' if count != 1 else ''}"
    
    @cached_property
    def SITEID(self):
        """Get SITEID from related ENR_CASE (cached)"""
        return self.USUBJID.SITEID if self.USUBJID else None
    
    @cached_property
    def has_any_condition(self):
        """Check if patient has any underlying condition (cached)"""
        return any([
            self.DIABETES, self.HEARTFAILURE, self.COPD, self.HEPATITIS,
            self.CAD, self.KIDNEYDISEASE, self.ASTHMA, self.CIRRHOSIS,
            self.HYPERTENSION, self.AUTOIMMUNE, self.CANCER, self.ALCOHOLISM,
            self.HIV, self.ADRENALINSUFFICIENCY, self.BEDRIDDEN, self.GASTRICULCER,
            self.COLITIS_IBS, self.FRAILTY, self.MALNUTRITION_CACHEXIA, self.OTHERDISEASE
        ])
    
    @cached_property
    def condition_count(self):
        """Count total number of underlying conditions (cached)"""
        return sum([
            self.DIABETES, self.HEARTFAILURE, self.COPD, self.HEPATITIS,
            self.CAD, self.KIDNEYDISEASE, self.ASTHMA, self.CIRRHOSIS,
            self.HYPERTENSION, self.AUTOIMMUNE, self.CANCER, self.ALCOHOLISM,
            self.HIV, self.ADRENALINSUFFICIENCY, self.BEDRIDDEN, self.GASTRICULCER,
            self.COLITIS_IBS, self.FRAILTY, self.MALNUTRITION_CACHEXIA, self.OTHERDISEASE
        ])
    
    @cached_property
    def condition_list(self):
        """Get list of condition names that are present (cached)"""
        # Define labels as class variable for efficiency
        if not hasattr(self.__class__, '_FIELD_LABELS'):
            self.__class__._FIELD_LABELS = {
                'DIABETES': str(_('Diabetes Mellitus')),
                'HEARTFAILURE': str(_('Heart Failure')),
                'COPD': str(_('COPD/Chronic bronchitis ')),
                'HEPATITIS': str(_('Chronic hepatitis')),
                'CAD': str(_('Coronary Artery Disease')),
                'KIDNEYDISEASE': str(_('Chronic kidney disease ')),
                'ASTHMA': str(_('Asthma')),
                'CIRRHOSIS': str(_('Cirrhosis')),
                'HYPERTENSION': str(_('Hypertension')),
                'AUTOIMMUNE': str(_('Autoimmune Disease')),
                'CANCER': str(_('Cancer')),
                'ALCOHOLISM': str(_('Alcoholism')),
                'HIV': str(_('HIV/AIDS')),
                'ADRENALINSUFFICIENCY': str(_('Adrenal Insufficiency')),
                'BEDRIDDEN': str(_('Bedridden')),
                'GASTRICULCER': str(_('Gastric ulcer')),
                'COLITIS_IBS': str(_('Ulcerative colitis/IBS ')),
                'FRAILTY': str(_('Frailty')),
                'MALNUTRITION_CACHEXIA': str(_('Malnutrition/Wasting')),
            }
        
        conditions = []
        for field, label in self.__class__._FIELD_LABELS.items():
            if getattr(self, field, False):
                conditions.append(label)
        
        if self.OTHERDISEASE and self.OTHERDISEASESPECIFY:
            conditions.append(f"Other: {self.OTHERDISEASESPECIFY}")
        
        return conditions
    
    def clean(self):
        """Enhanced validation"""
        errors = {}
        
        # Validate other disease specification
        if self.OTHERDISEASE:
            if not self.OTHERDISEASESPECIFY or not self.OTHERDISEASESPECIFY.strip():
                errors['OTHERDISEASESPECIFY'] = _(
                    'Please specify the other disease when "Other Disease" is checked'
                )
        
        if errors:
            raise ValidationError(errors)
    
    def _clear_cache(self):
        """Clear all cached properties"""
        cache_attrs = ['_has_any_condition', '_condition_count', '_SITEID', '_condition_list']
        for attr in cache_attrs:
            if hasattr(self, attr):
                delattr(self, attr)
    
    def save(self, *args, **kwargs):
        """Override save with transaction safety and cache management"""
        # Clear cached properties before save
        self._clear_cache()
        
        # Strip whitespace from text field
        if self.OTHERDISEASESPECIFY:
            self.OTHERDISEASESPECIFY = self.OTHERDISEASESPECIFY.strip()
        
        with transaction.atomic():
            super().save(*args, **kwargs)
            
            # Update parent ENR_CASE UNDERLYINGCONDS flag
            if self.USUBJID_id:  # Use _id to avoid extra query
                from django.db.models import Value
                ENR_CASE = self.USUBJID.__class__
                ENR_CASE.objects.filter(
                    USUBJID=self.USUBJID_id
                ).update(
                    UNDERLYINGCONDS=Value(self.has_any_condition)
                )