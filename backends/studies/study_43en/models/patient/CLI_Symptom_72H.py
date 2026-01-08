from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin


class Symptom_72H(AuditFieldsMixin):
    """
    Patient's clinical examination findings within 72 hours
    
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
        related_name='Symptom_72H',
        verbose_name=_('Patient ID')
    )
    
    # ==========================================
    # CLINICAL SYMPTOMS
    # ==========================================
    FEVER_2 = models.BooleanField(default=False, verbose_name=_('Fever (Clinical)'))
    RASH = models.BooleanField(default=False, verbose_name=_('Rash'))
    SKINBLEEDING = models.BooleanField(default=False, verbose_name=_('Skin Hemorrhage'))
    MUCOSALBLEEDING = models.BooleanField(default=False, verbose_name=_('Mucosal Hemorrhage'))
    SKINLESIONS_2 = models.BooleanField(default=False, verbose_name=_('Skin Lesions'))
    
    # Respiratory
    LUNGCRACKLES = models.BooleanField(default=False, verbose_name=_('Pulmonary Rales'))
    CONSOLIDATIONSYNDROME = models.BooleanField(default=False, verbose_name=_('Consolidation Syndrome'))
    PLEURALEFFUSION = models.BooleanField(default=False, verbose_name=_('Pleural Effusion'))
    PNEUMOTHORAX = models.BooleanField(default=False, verbose_name=_('Pneumothorax'))
    
    # Cardiovascular
    HEARTMURMUR = models.BooleanField(default=False, verbose_name=_('Heart Murmur'))
    ABNORHEARTSOUNDS = models.BooleanField(default=False, verbose_name=_('Abnormal Heart Sounds'))
    JUGULARVEINDISTENTION = models.BooleanField(default=False, verbose_name=_('Jugular Vein Distention'))
    
    # Hepatic
    LIVERFAILURESIGNS = models.BooleanField(default=False, verbose_name=_('Signs of Liver Failure'))
    PORTALHYPERTENSIONSIGNS = models.BooleanField(default=False, verbose_name=_('Signs of portal hypertension'))
    HEPATOSPLENOMEGALY = models.BooleanField(default=False, verbose_name=_('Hepatomegaly/Splenomegaly '))
    
    # Neurological
    CONSCIOUSNESSDISTURBANCE = models.BooleanField(default=False, verbose_name=_('Signs of portal hypertension  '))
    LIMBWEAKNESSPARALYSIS = models.BooleanField(default=False, verbose_name=_('Limb Weakness/Paralysis'))
    CRANIALNERVEPARALYSIS = models.BooleanField(default=False, verbose_name=_('Cranial Nerve Paralysis'))
    MENINGEALSIGNS = models.BooleanField(default=False, verbose_name=_('Meningeal Signs'))
    
    # Ophthalmic
    REDEYES_2 = models.BooleanField(default=False, verbose_name=_('Red Eyes'))
    HYPOPYON = models.BooleanField(default=False, verbose_name=_('Hypopyon'))
    
    # Other
    EDEMA = models.BooleanField(default=False, verbose_name=_('Edema'))
    CUSHINGOIDAPPEARANCE = models.BooleanField(default=False, verbose_name=_('Cushingoid Appearance'))
    
    # Abdominal
    EPIGASTRICPAIN_2 = models.BooleanField(default=False, verbose_name=_('Epigastric Pain'))
    LOWERABDPAIN_2 = models.BooleanField(default=False, verbose_name=_('Lower Abdominal Pain'))
    FLANKPAIN_2 = models.BooleanField(default=False, verbose_name=_('Flank Pain'))
    SUBCOSTALPAIN_2 = models.BooleanField(default=False, verbose_name=_('Hypochondrial Pain '))
    
    OTHERSYMPTOM_2 = models.BooleanField(
        default=False,
        verbose_name=_('Other Clinical Symptoms')
    )
    
    SPECIFYOTHERSYMPTOM_2 = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Other Symptoms Details')
    )
    
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'CLI_Symptom_72H'
        verbose_name = _('Patient Symptom 72H')
        verbose_name_plural = _('Symptoms 72H')
        indexes = [
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_s72_modified'),
            # Composite indexes for organ system queries
            models.Index(fields=['LUNGCRACKLES', 'PLEURALEFFUSION'], name='idx_s72_resp'),
            models.Index(fields=['LIVERFAILURESIGNS', 'HEPATOSPLENOMEGALY'], name='idx_s72_hepatic'),
            models.Index(fields=['CONSCIOUSNESSDISTURBANCE', 'MENINGEALSIGNS'], name='idx_s72_neuro'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    ~models.Q(OTHERSYMPTOM_2=True) |
                    models.Q(SPECIFYOTHERSYMPTOM_2__isnull=False)
                ),
                name='s72_specify_other'
            )
        ]
    
    def __str__(self):
        count = self.symptom_count
        return f"72H Symptoms: {self.USUBJID_id} ({count} findings)"
    
    @cached_property
    def SITEID(self):
        """Get SITEID from related CLI_CASE (cached)"""
        return self.USUBJID.SITEID if self.USUBJID else None
    
    @cached_property
    def symptom_count(self):
        """Count total number of clinical findings (cached)"""
        return sum([
            self.FEVER_2, self.RASH, self.SKINBLEEDING, self.MUCOSALBLEEDING,
            self.SKINLESIONS_2, self.LUNGCRACKLES, self.CONSOLIDATIONSYNDROME,
            self.PLEURALEFFUSION, self.PNEUMOTHORAX, self.HEARTMURMUR,
            self.ABNORHEARTSOUNDS, self.JUGULARVEINDISTENTION, self.LIVERFAILURESIGNS,
            self.PORTALHYPERTENSIONSIGNS, self.HEPATOSPLENOMEGALY,
            self.CONSCIOUSNESSDISTURBANCE, self.LIMBWEAKNESSPARALYSIS,
            self.CRANIALNERVEPARALYSIS, self.MENINGEALSIGNS, self.REDEYES_2,
            self.HYPOPYON, self.EDEMA, self.CUSHINGOIDAPPEARANCE,
            self.EPIGASTRICPAIN_2, self.LOWERABDPAIN_2, self.FLANKPAIN_2,
            self.SUBCOSTALPAIN_2, self.OTHERSYMPTOM_2
        ])
    
    @cached_property
    def has_respiratory_findings(self):
        """Check if patient has respiratory findings"""
        return any([
            self.LUNGCRACKLES, self.CONSOLIDATIONSYNDROME,
            self.PLEURALEFFUSION, self.PNEUMOTHORAX
        ])
    
    @cached_property
    def has_cardiovascular_findings(self):
        """Check if patient has cardiovascular findings"""
        return any([
            self.HEARTMURMUR, self.ABNORHEARTSOUNDS,
            self.JUGULARVEINDISTENTION
        ])
    
    @cached_property
    def has_hepatic_findings(self):
        """Check if patient has hepatic findings"""
        return any([
            self.LIVERFAILURESIGNS, self.PORTALHYPERTENSIONSIGNS,
            self.HEPATOSPLENOMEGALY
        ])
    
    @cached_property
    def has_neurological_findings(self):
        """Check if patient has neurological findings"""
        return any([
            self.CONSCIOUSNESSDISTURBANCE, self.LIMBWEAKNESSPARALYSIS,
            self.CRANIALNERVEPARALYSIS, self.MENINGEALSIGNS
        ])
    
    @cached_property
    def has_severe_findings(self):
        """Check if patient has severe clinical findings"""
        return any([
            self.SKINBLEEDING, self.MUCOSALBLEEDING,
            self.PNEUMOTHORAX, self.LIVERFAILURESIGNS,
            self.CONSCIOUSNESSDISTURBANCE, self.MENINGEALSIGNS
        ])
    
    @cached_property
    def symptom_list(self):
        """Get list of present symptoms (cached)"""
        if not hasattr(self.__class__, '_SYMPTOM_LABELS'):
            self.__class__._SYMPTOM_LABELS = {
                'FEVER_2': str(_('Fever')),
                'RASH': str(_('Rash')),
                'SKINBLEEDING': str(_('Skin Hemorrhage')),
                'MUCOSALBLEEDING': str(_('Mucosal Hemorrhage')),
                'SKINLESIONS_2': str(_('Skin Lesions')),
                'LUNGCRACKLES': str(_('Pulmonary Rales')),
                'CONSOLIDATIONSYNDROME': str(_('Consolidation Syndrome')),
                'PLEURALEFFUSION': str(_('Pleural Effusion')),
                'PNEUMOTHORAX': str(_('Pneumothorax')),
                'HEARTMURMUR': str(_('Heart Murmur')),
                'ABNORHEARTSOUNDS': str(_('Abnormal Heart Sounds')),
                'JUGULARVEINDISTENTION': str(_('Jugular Vein Distention')),
                'LIVERFAILURESIGNS': str(_('Signs of Liver Failure')),
                'PORTALHYPERTENSIONSIGNS': str(_('Signs of portal hypertension')),
                'HEPATOSPLENOMEGALY': str(_('Hepatosplenomegaly')),
                'CONSCIOUSNESSDISTURBANCE': str(_('Signs of portal hypertension')),
                'LIMBWEAKNESSPARALYSIS': str(_('Limb Weakness/Paralysis')),
                'CRANIALNERVEPARALYSIS': str(_('Cranial Nerve Paralysis')),
                'MENINGEALSIGNS': str(_('Meningeal Signs')),
                'REDEYES_2': str(_('Red Eyes')),
                'HYPOPYON': str(_('Hypopyon')),
                'EDEMA': str(_('Edema')),
                'CUSHINGOIDAPPEARANCE': str(_('Cushingoid Appearance')),
                'EPIGASTRICPAIN_2': str(_('Epigastric Pain')),
                'LOWERABDPAIN_2': str(_('Lower Abdominal Pain')),
                'FLANKPAIN_2': str(_('Flank Pain')),
                'SUBCOSTALPAIN_2': str(_('Hypochondrial Pain ')),
            }
        
        symptoms = []
        for field, label in self.__class__._SYMPTOM_LABELS.items():
            if getattr(self, field, False):
                symptoms.append(label)
        
        if self.OTHERSYMPTOM_2 and self.SPECIFYOTHERSYMPTOM_2:
            symptoms.append(f"Other: {self.SPECIFYOTHERSYMPTOM_2}")
        
        return symptoms
    
    def clean(self):
        """Validation"""
        errors = {}
        
        if self.OTHERSYMPTOM_2:
            if not self.SPECIFYOTHERSYMPTOM_2 or not self.SPECIFYOTHERSYMPTOM_2.strip():
                errors['SPECIFYOTHERSYMPTOM_2'] = _(
                    'Please specify other symptoms when "Other Symptoms" is checked'
                )
        

        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save with cache management"""
        # Clear cache
        self._clear_cache()
        
        # Strip whitespace
        if self.SPECIFYOTHERSYMPTOM_2:
            self.SPECIFYOTHERSYMPTOM_2 = self.SPECIFYOTHERSYMPTOM_2.strip()
        

        
        super().save(*args, **kwargs)
    
    def _clear_cache(self):
        """Clear all cached properties"""
        cache_attrs = [
            '_symptom_count', '_has_respiratory_findings',
            '_has_cardiovascular_findings', '_has_hepatic_findings',
            '_has_neurological_findings', '_has_severe_findings',
            '_symptom_list', '_SITEID'
        ]
        for attr in cache_attrs:
            if hasattr(self, attr):
                delattr(self, attr)