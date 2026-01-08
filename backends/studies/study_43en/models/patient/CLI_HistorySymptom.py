from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin


class HistorySymptom(AuditFieldsMixin):
    """
    Patient's symptoms history at admission
    
    Optimizations:
    - Added AuditFieldsMixin
    - Cached property for symptom count
    - Validation for other symptoms
    - Better indexes
    """
    
    # ==========================================
    # MANAGERS
    # ==========================================
        
    
    # ==========================================
    # PRIMARY KEY
    # ==========================================
    USUBJID = models.OneToOneField(
        'CLI_CASE',
        on_delete=models.CASCADE,
        primary_key=True,
        to_field='USUBJID',
        db_column='USUBJID',
        related_name='History_Symptom',
        verbose_name=_('Patient ID')
    )
    
    # ==========================================
    # BASIC SYMPTOMS
    # ==========================================
    FEVER = models.BooleanField(default=False, verbose_name=_('Fever'))
    FATIGUE = models.BooleanField(default=False, verbose_name=_('Fatigue'))
    MUSCLEPAIN = models.BooleanField(default=False, verbose_name=_('Muscle Pain'))
    LOSSAPPETITE = models.BooleanField(default=False, verbose_name=_('Loss of Appetite'))
    COUGH = models.BooleanField(default=False, verbose_name=_('Cough'))
    CHESTPAIN = models.BooleanField(default=False, verbose_name=_('Chest Pain'))
    SHORTBREATH = models.BooleanField(default=False, verbose_name=_('Shortness of Breath'))
    JAUNDICE = models.BooleanField(default=False, verbose_name=_('Jaundice'))
    PAINURINATION = models.BooleanField(default=False, verbose_name=_('Dysuria/Burning Urination '))
    BLOODYURINE = models.BooleanField(default=False, verbose_name=_('Red Urine '))
    CLOUDYURINE = models.BooleanField(default=False, verbose_name=_('Cloudy/Pus/Smelly Urine '))
    EPIGASTRICPAIN = models.BooleanField(default=False, verbose_name=_('Epigastric Pain'))
    LOWERABDPAIN = models.BooleanField(default=False, verbose_name=_('Hypogastric Pain'))
    FLANKPAIN = models.BooleanField(default=False, verbose_name=_('Flank Pain'))
    URINARYHESITANCY = models.BooleanField(default=False, verbose_name=_('Difficulty/Frequent Urination '))
    SUBCOSTALPAIN = models.BooleanField(default=False, verbose_name=_('Hypochondrial Pain'))
    HEADACHE = models.BooleanField(default=False, verbose_name=_('Headache'))
    POORCONTACT = models.BooleanField(default=False, verbose_name=_('Poor Contact/Lethargy'))
    DELIRIUMAGITATION = models.BooleanField(default=False, verbose_name=_('Delirium/Agitation'))
    VOMITING = models.BooleanField(default=False, verbose_name=_('Vomiting'))
    SEIZURES = models.BooleanField(default=False, verbose_name=_('Seizures'))
    EYEPAIN = models.BooleanField(default=False, verbose_name=_('Eye Pain'))
    REDEYES = models.BooleanField(default=False, verbose_name=_('Red Eyes'))
    NAUSEA = models.BooleanField(default=False, verbose_name=_('Nausea'))
    BLURREDVISION = models.BooleanField(default=False, verbose_name=_('Blurred Vision'))
    SKINLESIONS = models.BooleanField(default=False, verbose_name=_('Skin Lesions'))
    
    OTHERSYMPTOM = models.BooleanField(
        default=False,
        verbose_name=_('Other Symptoms')
    )
    
    SPECIFYOTHERSYMPTOM = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Other Symptoms Details')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'CLI_HistorySymptom'
        verbose_name = _('Patient History Symptom')
        verbose_name_plural = _('Patient History Symptoms')
        indexes = [
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_hsym_modified'),
            # Composite indexes for common symptom queries
            models.Index(fields=['FEVER', 'COUGH'], name='idx_hsym_resp'),
            models.Index(fields=['PAINURINATION', 'BLOODYURINE'], name='idx_hsym_uri'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    ~models.Q(OTHERSYMPTOM=True) |
                    models.Q(SPECIFYOTHERSYMPTOM__isnull=False)
                ),
                name='hsym_specify_other'
            )
        ]
    
    def __str__(self):
        count = self.symptom_count
        return f"History: {self.USUBJID_id} ({count} symptoms)"
    
    @cached_property
    def SITEID(self):
        """Get SITEID from related CLI_CASE (cached)"""
        return self.USUBJID.SITEID if self.USUBJID else None
    
    @cached_property
    def symptom_count(self):
        """Count total number of symptoms (cached)"""
        return sum([
            self.FEVER, self.FATIGUE, self.MUSCLEPAIN, self.LOSSAPPETITE,
            self.COUGH, self.CHESTPAIN, self.SHORTBREATH, self.JAUNDICE,
            self.PAINURINATION, self.BLOODYURINE, self.CLOUDYURINE,
            self.EPIGASTRICPAIN, self.LOWERABDPAIN, self.FLANKPAIN,
            self.URINARYHESITANCY, self.SUBCOSTALPAIN, self.HEADACHE,
            self.POORCONTACT, self.DELIRIUMAGITATION, self.VOMITING,
            self.SEIZURES, self.EYEPAIN, self.REDEYES, self.NAUSEA,
            self.BLURREDVISION, self.SKINLESIONS, self.OTHERSYMPTOM
        ])
    
    @cached_property
    def has_respiratory_symptoms(self):
        """Check if patient has any respiratory symptoms"""
        return any([self.COUGH, self.CHESTPAIN, self.SHORTBREATH])
    
    @cached_property
    def has_urinary_symptoms(self):
        """Check if patient has any urinary symptoms"""
        return any([
            self.PAINURINATION, self.BLOODYURINE, self.CLOUDYURINE,
            self.URINARYHESITANCY
        ])
    
    @cached_property
    def has_neurological_symptoms(self):
        """Check if patient has any neurological symptoms"""
        return any([
            self.HEADACHE, self.POORCONTACT, self.DELIRIUMAGITATION,
            self.SEIZURES, self.BLURREDVISION
        ])
    
    @cached_property
    def symptom_list(self):
        """Get list of present symptoms (cached)"""
        if not hasattr(self.__class__, '_SYMPTOM_LABELS'):
            self.__class__._SYMPTOM_LABELS = {
                'FEVER': str(_('Fever')),
                'FATIGUE': str(_('Fatigue')),
                'MUSCLEPAIN': str(_('Muscle Pain')),
                'LOSSAPPETITE': str(_('Loss of Appetite')),
                'COUGH': str(_('Cough')),
                'CHESTPAIN': str(_('Chest Pain')),
                'SHORTBREATH': str(_('Shortness of Breath')),
                'JAUNDICE': str(_('Jaundice')),
                'PAINURINATION': str(_('Dysuria/Burning Urination ')),
                'BLOODYURINE': str(_('Red Urine')),
                'CLOUDYURINE': str(_('Cloudy/Pus/Smelly Urine')),
                'EPIGASTRICPAIN': str(_('Epigastric Pain')),
                'LOWERABDPAIN': str(_('Hypogastric Pain ')),
                'FLANKPAIN': str(_('Flank Pain')),
                'URINARYHESITANCY': str(_('Difficulty/Frequent Urination')),
                'SUBCOSTALPAIN': str(_('Hypochondrial Pain')),
                'HEADACHE': str(_('Headache')),
                'POORCONTACT': str(_('Poor Contact')),
                'DELIRIUMAGITATION': str(_('Delirium/Agitation')),
                'VOMITING': str(_('Vomiting')),
                'SEIZURES': str(_('Seizures')),
                'EYEPAIN': str(_('Eye Pain')),
                'REDEYES': str(_('Red Eyes')),
                'NAUSEA': str(_('Nausea')),
                'BLURREDVISION': str(_('Blurred Vision')),
                'SKINLESIONS': str(_('Skin Lesions')),
            }
        
        symptoms = []
        for field, label in self.__class__._SYMPTOM_LABELS.items():
            if getattr(self, field, False):
                symptoms.append(label)
        
        if self.OTHERSYMPTOM and self.SPECIFYOTHERSYMPTOM:
            symptoms.append(f"Other: {self.SPECIFYOTHERSYMPTOM}")
        
        return symptoms
    
    def clean(self):
        """Validation"""
        errors = {}
        
        if self.OTHERSYMPTOM:
            if not self.SPECIFYOTHERSYMPTOM or not self.SPECIFYOTHERSYMPTOM.strip():
                errors['SPECIFYOTHERSYMPTOM'] = _(
                    'Please specify other symptoms when "Other Symptoms" is checked'
                )
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save with cache management"""
        # Clear cache
        self._clear_cache()
        
        # Strip whitespace
        if self.SPECIFYOTHERSYMPTOM:
            self.SPECIFYOTHERSYMPTOM = self.SPECIFYOTHERSYMPTOM.strip()
        
        super().save(*args, **kwargs)
    
    def _clear_cache(self):
        """Clear all cached properties"""
        cache_attrs = [
            '_symptom_count', '_has_respiratory_symptoms',
            '_has_urinary_symptoms', '_has_neurological_symptoms',
            '_symptom_list', '_SITEID'
        ]
        for attr in cache_attrs:
            if hasattr(self, attr):
                delattr(self, attr)