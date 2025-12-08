# backends/studies/study_43en/models/patient/LAB_models_semantic.py
"""
Laboratory Models with Semantic IDs - CORRECT VERSION
- Correct model names: LAB_Microbiology, AntibioticSensitivity
- FK to ENR_CASE (not SCR_CASE)
- Semantic IDs for better traceability
- WHONET antibiotic codes
- One test per antibiotic per culture (no SEQUENCE)
- Only test when culture is positive for Klebsiella
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.functional import cached_property
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin
from datetime import date
from django.db.models.signals import post_save
from django.dispatch import receiver 
import re

from backends.studies.study_43en.models.patient.LAB_AntibioticSensitivity import AntibioticSensitivity
import logging
logger = logging.getLogger(__name__)
# ==========================================
# WHONET Antibiotic Code Mapping
# ==========================================
WHONET_CODES = {
    # Tier 1 - Access Group (11 antibiotics)
    'Ampicillin': 'AMP',
    'Cefazolin': 'CZO',
    'Cefotaxime': 'CTX',
    'Ceftriaxone': 'CRO',
    'AmoxicillinClavulanate': 'AMC',
    'AmpicillinSulbactam': 'SAM',
    'PiperacillinTazobactam': 'TZP',
    'Gentamicin': 'GEN',
    'Ciprofloxacin': 'CIP',
    'Levofloxacin': 'LVX',
    'TrimethoprimSulfamethoxazole': 'SXT',
    
    # Tier 2 - Watch Group (10 antibiotics)
    'Cefuroxime': 'CXM',
    'Cefepime': 'FEP',
    'Ertapenem': 'ETP',
    'Imipenem': 'IPM',
    'Meropenem': 'MEM',
    'Amikacin': 'AMK',
    'Tobramycin': 'TOB',
    'Cefotetan': 'CTT',
    'Cefoxitin': 'FOX',
    'Tetracycline': 'TCY',
    
    # Tier 3 - Reserve Group (5 antibiotics)
    'Cefiderocol': 'FDC',
    'CeftazidimeAvibactam': 'CZA',
    'ImipenemRelebactam': 'IMR',
    'MeropenemVaborbactam': 'MEV',
    'Plazomicin': 'PLZ',
    
    # Tier 4 - Specialized (4 antibiotics)
    'Aztreonam': 'ATM',
    'Ceftaroline': 'CPT',
    'Ceftazidime': 'CAZ',
    'CeftolozaneTazobactam': 'CZT',
    
    # Urine-Specific (3 antibiotics)
    #  FIX: Use different code for urine-specific Cefazolin to avoid duplicate AST_ID
    'CefazolinUrine': 'CZO-U',  # Different from regular Cefazolin (CZO)
    'Nitrofurantoin': 'NIT',
    'Fosfomycin': 'FOS',
    
    # Colistin (1 antibiotic - last resort)
    'Colistin': 'COL',
}


# ==========================================
# MODEL 1: LAB_Microbiology (CORRECT NAME)
# ==========================================

class LAB_Microbiology(AuditFieldsMixin):
    """
    Laboratory microbiology culture results with SEMANTIC PRIMARY KEY
    
     LAB_CULTURE_ID Format: {USUBJID}-C{SEQ}
    Example: "001-A-001-C1" = Blood culture #1 for patient 001-A-001
    
     Antibiotic testing ONLY if:
       - Culture is POSITIVE
       - Organism is Klebsiella pneumoniae (KPN)
    """
    
    class SpecimenLocationChoices(models.TextChoices):
        BLOOD = 'BLOOD', _('Blood')
        URINE = 'URINE', _('Urine')
        PLEURAL_FLUID = 'PLEURAL_FLUID', _('Pleural Fluid')
        PERITONEAL_FLUID = 'PERITONEAL_FLUID', _('Peritoneal Fluid')
        SPUTUM = 'SPUTUM', _('Sputum')
        BRONCHIAL = 'BRONCHIAL', _('Bronchial Lavage')
        CSF = 'CSF', _('Cerebrospinal Fluid')
        WOUND = 'WOUND', _('Wound Discharge')
        OTHER = 'OTHER', _('Other')
    
    class ResultTypeChoices(models.TextChoices):
        POSITIVE = 'Positive', _('Positive')
        NEGATIVE = 'Negative', _('Negative')    
    # ==========================================
    # MANAGERS
    # ==========================================
        
    
    # ==========================================
    # FOREIGN KEY 
    # ==========================================
    USUBJID = models.ForeignKey(
        'ENR_CASE', 
        to_field='USUBJID', 
        on_delete=models.CASCADE,
        related_name='lab_microbiology_cultures',
        db_column='USUBJID',
        verbose_name=_('Patient ID')
    )
    
    LAB_CASE_SEQ = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_('Lab Case Sequence Number'),
        help_text=_('Sequential culture number per patient (1, 2, 3...)')
    )
    
    # ==========================================
    #  SEMANTIC ID (Human-readable Primary Key)
    # ==========================================
    LAB_CULTURE_ID = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name=_('Lab Culture ID'),
        help_text=_('Auto-generated format: {USUBJID}-{SEQ} e.g., "001-A-001-1"')
    )
    
    # ==========================================
    # STUDY IDENTIFIERS (from original model)
    # ==========================================
    STUDYID = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Study ID')
    )
    
    SITEID = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name=_('Site ID')
    )
    
    SUBJID = models.CharField(
        max_length=50,
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
    # SPECIMEN INFORMATION
    # ==========================================
    SPECIMENID = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Sample ID (SID')
    )
    
    SPECSAMPLOC = models.CharField(
        max_length=20,
        choices=SpecimenLocationChoices.choices,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Sampling site')
    )
    
    OTHERSPECIMEN = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Other Specimen Type')
    )
    
    SPECSAMPDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Specimen Sample Date')
    )
    
    BACSTRAINISOLDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Bacterial Strain Isolation Date')
    )
    
    # ==========================================
    #  CULTURE RESULTS
    # ==========================================
    RESULT = models.CharField(
        max_length=20,
        choices=ResultTypeChoices.choices,
        blank=True,
        null=True,
        db_index=True,
        verbose_name=_('Culture Result')
    )
    
    RESULTDETAILS = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Result Details'),
        help_text=_('Organism identification (e.g., "Klebsiella pneumoniae")')
    )
    
    # ==========================================
    #  NEW: IF POSITIVE - Organism Type
    # ==========================================
    class IfPositiveChoices(models.TextChoices):
        KPNEUMONIAE = 'Kpneumoniae', _('K. pneumoniae')
        OTHER = 'Other', _('Other')
    
    IFPOSITIVE = models.CharField(
        max_length=20,
        choices=IfPositiveChoices.choices,
        blank=True,
        null=True,
        verbose_name=_('If Positive - Organism Type'),
        help_text=_('Select organism type if result is positive')
    )
    
    SPECIFYOTHERSPECIMEN = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_('Specify Other Organism'),
        help_text=_('Specify organism name if "Other" is selected')
    )
    
    # ==========================================
    #  KLEBSIELLA FLAG (for antibiotic testing eligibility)
    # ==========================================
    IS_KLEBSIELLA = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_('Klebsiella Detected'),
        help_text=_('True if culture is positive for Klebsiella pneumoniae')
    )
    
    # ==========================================
    # DEPARTMENT INFORMATION
    # ==========================================
    ORDEREDBYDEPT = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Ordering Department')
    )
    
    DEPTDIAGSENT = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Department Diagnosis')
    )

    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'LAB_CASE'  #  CORRECT table name
        verbose_name = _('LAB Microbiology Culture')
        verbose_name_plural = _('LAB Microbiology Cultures')
        unique_together = [['USUBJID', 'LAB_CASE_SEQ']]
        ordering = ['USUBJID', 'LAB_CASE_SEQ']
        indexes = [
            models.Index(fields=['LAB_CULTURE_ID'], name='idx_lmc_cid'),
            models.Index(fields=['USUBJID', 'LAB_CASE_SEQ'], name='idx_lmc_subj_seq'),
            models.Index(fields=['RESULT', 'IS_KLEBSIELLA'], name='idx_lmc_res_kleb'),
            models.Index(fields=['SPECSAMPDATE'], name='idx_lmc_date'),
            models.Index(fields=['SPECSAMPLOC'], name='idx_lmc_spec'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_lmc_modified'),
        ]
        constraints = [
            # If positive, must have IFPOSITIVE
            models.CheckConstraint(
                check=(
                    ~models.Q(RESULT='Positive') |
                    models.Q(IFPOSITIVE__isnull=False)
                ),
                name='lmc_positive_needs_ifpositive'
            ),
            # If IFPOSITIVE is Other, must specify organism name
            models.CheckConstraint(
                check=(
                    ~models.Q(IFPOSITIVE='Other') |
                    models.Q(SPECIFYOTHERSPECIMEN__isnull=False)
                ),
                name='lmc_other_needs_specify'
            ),
            # Isolation date must be after or equal to collection date
            models.CheckConstraint(
                check=(
                    models.Q(SPECSAMPDATE__isnull=True) |
                    models.Q(BACSTRAINISOLDATE__isnull=True) |
                    models.Q(BACSTRAINISOLDATE__gte=models.F('SPECSAMPDATE'))
                ),
                name='lmc_isolation_after_collection'
            ),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate LAB_CASE_SEQ, LAB_CULTURE_ID, and IS_KLEBSIELLA flag"""
        # Determine which database to use
        using = kwargs.get('using', 'default')
        
        # Auto-increment LAB_CASE_SEQ if not provided
        if not self.LAB_CASE_SEQ:
            last_seq = (
                LAB_Microbiology.objects
                .using(using)
                .filter(USUBJID=self.USUBJID)
                .aggregate(models.Max('LAB_CASE_SEQ'))['LAB_CASE_SEQ__max']
            )
            self.LAB_CASE_SEQ = (last_seq or 0) + 1
        
        #  Generate semantic LAB_CULTURE_ID
        if not self.LAB_CULTURE_ID and self.USUBJID:
            # Get USUBJID string - avoid nested FK access to prevent schema issues
            # self.USUBJID is FK to ENR_CASE
            # ENR_CASE.USUBJID is CharField containing the actual USUBJID string
            try:
                # Try to get from memory first (if ENR_CASE already loaded)
                if hasattr(self.USUBJID, 'USUBJID'):
                    usubjid_str = str(self.USUBJID.USUBJID)
                else:
                    # Fallback: query with explicit database
                    from study_43en.models.patient.ENR_CASE import ENR_CASE
                    enr = ENR_CASE.objects.using(using).filter(pk=self.USUBJID_id).values_list('USUBJID', flat=True).first()
                    usubjid_str = str(enr) if enr else str(self.USUBJID_id)
            except Exception:
                # Last resort: use the FK ID
                usubjid_str = str(self.USUBJID_id)
            
            self.LAB_CULTURE_ID = f"{usubjid_str}-C{self.LAB_CASE_SEQ}"
        
        #  Set IS_KLEBSIELLA based on IFPOSITIVE selection
        if self.RESULT == self.ResultTypeChoices.POSITIVE:
            # If user selected K.pneumoniae
            self.IS_KLEBSIELLA = (self.IFPOSITIVE == self.IfPositiveChoices.KPNEUMONIAE)
        else:
            # If not positive, clear everything
            self.IS_KLEBSIELLA = False
            self.IFPOSITIVE = None
            self.SPECIFYOTHERSPECIMEN = None
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        specimen_display = self.get_SPECSAMPLOC_display() if self.SPECSAMPLOC else 'Unknown'
        kpn_flag = ' [KPN+]' if self.IS_KLEBSIELLA else ''
        return f"{self.LAB_CULTURE_ID} - {specimen_display}{kpn_flag}"
    
    # ==========================================
    # PROPERTIES
    # ==========================================
    @property
    def is_positive(self):
        """Check if culture result is positive"""
        return self.RESULT == self.ResultTypeChoices.POSITIVE
    
    @property
    def is_testable_for_antibiotics(self):
        """Check if culture is eligible for antibiotic sensitivity testing"""
        return self.is_positive and self.IS_KLEBSIELLA
    
    @property
    def display_name(self):
        """Human-readable display name"""
        specimen = self.get_SPECSAMPLOC_display() if self.SPECSAMPLOC else 'Unknown'
        date_str = self.SPECSAMPDATE.strftime('%Y-%m-%d') if self.SPECSAMPDATE else 'N/A'
        kpn = ' (KPN+)' if self.IS_KLEBSIELLA else ''
        return f"{self.LAB_CULTURE_ID} - {specimen} ({date_str}){kpn}"
    
    def get_sensitivity_count(self):
        """Count number of antibiotic sensitivity results"""
        #  Get database from instance
        using = self._state.db or 'db_study_43en'
        return AntibioticSensitivity.objects.using(using).filter(LAB_CULTURE_ID=self).count()
    
    def get_sensitivity_by_tier(self):
        """Get antibiotic sensitivity results grouped by tier"""
        #  Get database from instance
        using = self._state.db or 'db_study_43en'
        
        results = {}
        for tier_value, _ in AntibioticSensitivity.TierChoices.choices:
            sensitivities = AntibioticSensitivity.objects.using(using).filter(
                LAB_CULTURE_ID=self,
                TIER=tier_value
            ).order_by('WHONET_CODE')
            results[tier_value] = list(sensitivities)
        return results
    
    def get_resistance_summary(self):
        """Get resistance summary (S/I/R/U/ND counts)"""
        from django.db.models import Count, Q
        
        #  Get database from instance
        using = self._state.db or 'db_study_43en'
        
        return AntibioticSensitivity.objects.using(using).filter(
            LAB_CULTURE_ID=self
        ).aggregate(
            sensitive=Count('id', filter=Q(SENSITIVITY_LEVEL='S')),
            intermediate=Count('id', filter=Q(SENSITIVITY_LEVEL='I')),
            resistant=Count('id', filter=Q(SENSITIVITY_LEVEL='R')),
            unknown=Count('id', filter=Q(SENSITIVITY_LEVEL='U')),
            not_determined=Count('id', filter=Q(SENSITIVITY_LEVEL='ND'))
        )
    
    # ==========================================
    # VALIDATION
    # ==========================================
    def clean(self):
        """Enhanced validation"""
        errors = {}
        
        # Positive result must have details
        if self.RESULT == self.ResultTypeChoices.POSITIVE:
            if not self.RESULTDETAILS or not self.RESULTDETAILS.strip():
                errors['RESULTDETAILS'] = _(
                    'Result details are required for positive cultures'
                )
        
        # Date validation
        if self.SPECSAMPDATE and self.SPECSAMPDATE > date.today():
            errors['SPECSAMPDATE'] = _('Sample date cannot be in the future')
        
        if self.BACSTRAINISOLDATE and self.BACSTRAINISOLDATE > date.today():
            errors['BACSTRAINISOLDATE'] = _('Isolation date cannot be in the future')
        
        if self.SPECSAMPDATE and self.BACSTRAINISOLDATE:
            if self.BACSTRAINISOLDATE < self.SPECSAMPDATE:
                errors['BACSTRAINISOLDATE'] = _(
                    'Isolation date cannot be before sample date'
                )
        
        if errors:
            raise ValidationError(errors)



# ==========================================
# SIGNAL: AUTO-CREATE ANTIBIOTICS FOR KPN+ CULTURES
# ==========================================

@receiver(post_save, sender=LAB_Microbiology)
def auto_create_antibiotic_tests(sender, instance, created, **kwargs):
    """
    Auto-create antibiotic sensitivity test slots for KPN+ cultures
    
    Triggered when:
    - New culture is created AND IS_KLEBSIELLA = True
    - Existing culture updated to IS_KLEBSIELLA = True
    
    Creates empty test slots for ALL standard antibiotics according to specimen type.
    User just needs to fill in the results.
    """
    # Only create if culture is testable
    if not instance.is_testable_for_antibiotics:
        return
    
    #  Get database from kwargs or instance
    using = kwargs.get('using', None)
    if not using:
        # Try to get from instance's _state
        using = instance._state.db or 'default'
    
    # Check if already has tests (with correct database)
    existing_count = AntibioticSensitivity.objects.using(using).filter(
        LAB_CULTURE_ID=instance
    ).count()
    
    if existing_count > 0:
        # Already has tests, don't create duplicates
        return
    
    logger.info(f"🔬 Auto-creating antibiotic tests for {instance.LAB_CULTURE_ID}")
    
    #  List of antibiotics to auto-create 
    antibiotics_to_create = [
        #  Tier 1 - Access Group (11 antibiotics)
        ('Ampicillin', 'Tier1'),
        ('Cefazolin', 'Tier1'),
        ('Cefotaxime', 'Tier1'),
        ('Ceftriaxone', 'Tier1'),
        ('AmoxicillinClavulanate', 'Tier1'),
        ('AmpicillinSulbactam', 'Tier1'),
        ('PiperacillinTazobactam', 'Tier1'),
        ('Gentamicin', 'Tier1'),
        ('Ciprofloxacin', 'Tier1'),
        ('Levofloxacin', 'Tier1'),
        ('TrimethoprimSulfamethoxazole', 'Tier1'),
        
        #  Tier 2 - Watch Group (10 antibiotics)
        ('Cefuroxime', 'Tier2'),
        ('Cefepime', 'Tier2'),
        ('Ertapenem', 'Tier2'),
        ('Imipenem', 'Tier2'),
        ('Meropenem', 'Tier2'),
        ('Amikacin', 'Tier2'),
        ('Tobramycin', 'Tier2'),
        ('Cefotetan', 'Tier2'),
        ('Cefoxitin', 'Tier2'),
        ('Tetracycline', 'Tier2'),
        
        #  Tier 3 - Reserve Group (5 antibiotics)
        ('Cefiderocol', 'Tier3'),
        ('CeftazidimeAvibactam', 'Tier3'),
        ('ImipenemRelebactam', 'Tier3'),
        ('MeropenemVaborbactam', 'Tier3'),
        ('Plazomicin', 'Tier3'),
        
        #  Tier 4 - Specialized (4 antibiotics)
        ('Aztreonam', 'Tier4'),
        ('Ceftaroline', 'Tier4'),
        ('Ceftazidime', 'Tier4'),
        ('CeftolozaneTazobactam', 'Tier4'),
    ]
    
    #  Add urine-specific antibiotics if specimen is urine
    # Note: Cefazolin appears AGAIN for urine samples
    if instance.SPECSAMPLOC == 'URINE':
        antibiotics_to_create.extend([
            ('CefazolinUrine', 'UrineOnly'),  # Second Cefazolin for urine
            ('Nitrofurantoin', 'UrineOnly'),
            ('Fosfomycin', 'UrineOnly'),
        ])
    
    #  Colistin (Last Resort - for all specimens)
    antibiotics_to_create.append(('Colistin', 'Colistin'))
    
    # Create test slots (with correct database)
    created_tests = []
    for antibiotic_name, tier in antibiotics_to_create:
        try:
            test = AntibioticSensitivity.objects.using(using).create(
                LAB_CULTURE_ID=instance,
                ANTIBIOTIC_NAME=antibiotic_name,
                TIER=tier,
                SENSITIVITY_LEVEL='ND',  # Not Determined - default
                INTERPRETATION_STANDARD='CLSI',
                last_modified_by_id=instance.last_modified_by_id,
                last_modified_by_username=instance.last_modified_by_username,
            )
            created_tests.append(test)
        except Exception as e:
            logger.error(f"Error creating test for {antibiotic_name}: {e}")
    
    logger.info(f" Created {len(created_tests)} antibiotic test slots for {instance.LAB_CULTURE_ID}")
    
    # Log urine-specific note
    if instance.SPECSAMPLOC == 'URINE':
        logger.info(f" Added urine-specific antibiotics (including 2nd Cefazolin)")