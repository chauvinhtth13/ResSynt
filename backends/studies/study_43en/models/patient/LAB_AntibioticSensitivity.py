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
import re

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

class AntibioticSensitivity(AuditFieldsMixin):
    """
    Antibiotic sensitivity testing (AST) results with SEMANTIC PRIMARY KEY
    
     AST_ID Format: {CULTURE_ID}-{WHONET_CODE}
    Example: "001-A-001-C1-AMP" = Ampicillin test for culture C1
    
     Key Features:
    - NO SEQUENCE field (one test per antibiotic per culture)
    - Only created when culture is positive for Klebsiella
    - Uses WHONET standard antibiotic codes
    """
    
    # ==========================================
    # CHOICES DEFINITIONS
    # ==========================================
    class TierChoices(models.TextChoices):
        TIER1 = 'Tier1', _(' Tier 1')
        TIER2 = 'Tier2', _(' Tier 2')
        TIER3 = 'Tier3', _(' Tier 3')
        TIER4 = 'Tier4', _(' Tier 4')
        URINE_ONLY = 'UrineOnly', _(' Urine Only')
        COLISTIN = 'Colistin', _(' Colistin')
        OTHER = 'Other', _('Other')
    
    class AntibioticChoices(models.TextChoices):
        # TIER 1 - ACCESS GROUP (11 antibiotics)
        AMPICILLIN = 'Ampicillin', _('Ampicillin')
        CEFAZOLIN = 'Cefazolin', _('Cefazolin')
        CEFOTAXIME = 'Cefotaxime', _('Cefotaxime')
        CEFTRIAXONE = 'Ceftriaxone', _('Ceftriaxone')
        AMOXICILLIN_CLAVULANATE = 'AmoxicillinClavulanate', _('Amoxicillin-clavulanate')
        AMPICILLIN_SULBACTAM = 'AmpicillinSulbactam', _('Ampicillin/sulbactam')
        PIPERACILLIN_TAZOBACTAM = 'PiperacillinTazobactam', _('Piperacillin/tazobactam')
        GENTAMICIN = 'Gentamicin', _('Gentamicin')
        CIPROFLOXACIN = 'Ciprofloxacin', _('Ciprofloxacin')
        LEVOFLOXACIN = 'Levofloxacin', _('Levofloxacin')
        TRIMETHOPRIM_SULFAMETHOXAZOLE = 'TrimethoprimSulfamethoxazole', _('Trimethoprim/sulfamethoxazole')
        
        # TIER 2 - WATCH GROUP (10 antibiotics)
        CEFUROXIME = 'Cefuroxime', _('Cefuroxime')
        CEFEPIME = 'Cefepime', _('Cefepime')
        ERTAPENEM = 'Ertapenem', _('Ertapenem')
        IMIPENEM = 'Imipenem', _('Imipenem')
        MEROPENEM = 'Meropenem', _('Meropenem')
        AMIKACIN = 'Amikacin', _('Amikacin')
        TOBRAMYCIN = 'Tobramycin', _('Tobramycin')
        CEFOTETAN = 'Cefotetan', _('Cefotetan')
        CEFOXITIN = 'Cefoxitin', _('Cefoxitin')
        TETRACYCLINE = 'Tetracycline', _('Tetracycline')
        
        # TIER 3 - RESERVE GROUP (5 antibiotics)
        CEFIDEROCOL = 'Cefiderocol', _('Cefiderocol')
        CEFTAZIDIME_AVIBACTAM = 'CeftazidimeAvibactam', _('Ceftazidime/avibactam')
        IMIPENEM_RELEBACTAM = 'ImipenemRelebactam', _('Imipenem/relebactam')
        MEROPENEM_VABORBACTAM = 'MeropenemVaborbactam', _('Meropenem/vaborbactam')
        PLAZOMICIN = 'Plazomicin', _('Plazomicin')
        
        # TIER 4 - SPECIALIZED (4 antibiotics)
        AZTREONAM = 'Aztreonam', _('Aztreonam')
        CEFTAROLINE = 'Ceftaroline', _('Ceftaroline')
        CEFTAZIDIME = 'Ceftazidime', _('Ceftazidime')
        CEFTOLOZANE_TAZOBACTAM = 'CeftolozaneTazobactam', _('Ceftolozane/tazobactam')
        
        # URINE-SPECIFIC (3 antibiotics)
        CEFAZOLIN_URINE = 'CefazolinUrine', _('Cefazolin (Urine)')
        NITROFURANTOIN = 'Nitrofurantoin', _('Nitrofurantoin')
        FOSFOMYCIN = 'Fosfomycin', _('Fosfomycin')
        
        # COLISTIN (1 antibiotic - last resort)
        COLISTIN = 'Colistin', _('Colistin')
        
        # OTHER
        OTHER = 'Other', _('Other Antibiotic')
    
    class SensitivityChoices(models.TextChoices):
        """
        CLSI/EUCAST standard interpretive categories
        
        S  = Sensitive (susceptible)
        I  = Intermediate
        R  = Resistant
        U  = Unknown (result unclear or equivocal)
        ND = Not Determined (test not performed)
        """
        SENSITIVE = 'S', _('Sensitive (S)')
        INTERMEDIATE = 'I', _('Intermediate (I)')
        RESISTANT = 'R', _('Resistant (R)')
        UNKNOWN = 'U', _('Unknown (U)')
        NOT_DETERMINED = 'ND', _('Not Determined (ND)')
    
    # ==========================================
    # MANAGERS
    # ==========================================
    objects = models.Manager()
    site_objects = SiteFilteredManager()
    
    # ==========================================
    # FOREIGN KEY -  Links to LAB_CULTURE_ID
    # ==========================================
    LAB_CULTURE_ID = models.ForeignKey(
        'LAB_Microbiology',  #  CORRECT model name
        on_delete=models.CASCADE,
        related_name='antibiotic_sensitivities',
        db_column='LAB_CULTURE_ID',
        to_field='LAB_CULTURE_ID',
        verbose_name=_('Lab Culture ID'),
        help_text=_('Reference to lab culture (e.g., 001-A-001-C1)')
    )
    
    ANTIBIOTIC_NAME = models.CharField(
        max_length=50,
        choices=AntibioticChoices.choices,
        db_index=True,
        verbose_name=_('Antibiotic Name')
    )
    
    OTHER_ANTIBIOTIC_NAME = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Other Antibiotic Name'),
        help_text=_('Specify if antibiotic is not in standard list')
    )
    
    # ==========================================
    #  WHONET CODE (Auto-generated)
    # ==========================================
    WHONET_CODE = models.CharField(
        max_length=10,
        editable=False,
        db_index=True,
        verbose_name=_('WHONET Antibiotic Code'),
        help_text=_('Standard WHONET code (e.g., AMP, GEN, CIP)')
    )
    
    # ==========================================
    #  SEMANTIC ID (NO SEQUENCE - One test per antibiotic)
    # ==========================================
    AST_ID = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name=_('Antibiotic Sensitivity Test ID'),
        help_text=_('Auto-generated format: {CULTURE_ID}-{WHONET_CODE} e.g., "001-A-001-C1-AMP"')
    )
    
    # ==========================================
    # ANTIBIOTIC CLASSIFICATION
    # ==========================================
    TIER = models.CharField(
        max_length=20,
        choices=TierChoices.choices,
        db_index=True,
        verbose_name=_('Antibiotic Tier'),
        help_text=_('WHO AWaRe classification tier')
    )
    
    # ==========================================
    # SENSITIVITY RESULTS
    # ==========================================
    SENSITIVITY_LEVEL = models.CharField(
        max_length=2,
        choices=SensitivityChoices.choices,
        default=SensitivityChoices.NOT_DETERMINED,
        db_index=True,
        verbose_name=_('Sensitivity Level'),
        help_text=_('CLSI/EUCAST interpretive category: S/I/R/U/ND')
    )
    
    # ==========================================
    # QUANTITATIVE RESULTS
    # ==========================================
    IZDIAM = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('Inhibition Zone Diameter (mm)'),
        help_text=_('Disk diffusion zone size')
    )
    
    MIC = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name=_('MIC Value (µg/mL)'),
        help_text=_('Minimum Inhibitory Concentration (e.g., "<=0.25", "2", ">256")')
    )
    
    MIC_NUMERIC = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('MIC Numeric Value'),
        help_text=_('Numeric MIC for calculations (auto-parsed from MIC field)')
    )
    
    # ==========================================
    # TESTING DETAILS
    # ==========================================

    
    TESTDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Testing Date')
    )
    
    INTERPRETATION_STANDARD = models.CharField(
        max_length=20,
        choices=[
            ('CLSI', _('CLSI')),
            ('EUCAST', _('EUCAST')),
            ('Other', _('Other'))
        ],
        default='CLSI',
        verbose_name=_('Breakpoint Standard'),
        help_text=_('Which guidelines used for interpretation')
    )
    
    NOTES = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Testing Notes'),
        help_text=_('Quality control notes, technical issues, etc.')
    )
    
    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'LAB_Antibiotic_Sensitivity'  #  CORRECT table name
        verbose_name = _('Antibiotic Sensitivity Test')
        verbose_name_plural = _('Antibiotic Sensitivity Tests')
        #  UNIQUE: One test per antibiotic per culture (NO SEQUENCE)
        unique_together = [['LAB_CULTURE_ID', 'ANTIBIOTIC_NAME']]
        ordering = ['LAB_CULTURE_ID', 'TIER', 'WHONET_CODE']
        indexes = [
            models.Index(fields=['AST_ID'], name='idx_ast_ast_id'),
            models.Index(fields=['LAB_CULTURE_ID', 'ANTIBIOTIC_NAME'], name='idx_ast_cult_abx'),
            models.Index(fields=['WHONET_CODE'], name='idx_ast_whonet'),
            models.Index(fields=['TIER', 'SENSITIVITY_LEVEL'], name='idx_ast_tier_sens'),
            models.Index(fields=['ANTIBIOTIC_NAME', 'SENSITIVITY_LEVEL'], name='idx_ast_abx_sens'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_ast_modified'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['LAB_CULTURE_ID', 'ANTIBIOTIC_NAME'],
                name='unique_ast_per_culture'
            ),
            # If OTHER antibiotic, must specify name
            models.CheckConstraint(
                condition=(
                    ~models.Q(ANTIBIOTIC_NAME='Other') |
                    models.Q(OTHER_ANTIBIOTIC_NAME__isnull=False)
                ),
                name='ast_specify_other_antibiotic'
            ),
            # MIC numeric must be positive if provided
            models.CheckConstraint(
                condition=(
                    models.Q(MIC_NUMERIC__isnull=True) |
                    models.Q(MIC_NUMERIC__gt=0)
                ),
                name='ast_mic_positive'
            ),
            # Test date cannot be in future
            models.CheckConstraint(
                condition=(
                    models.Q(TESTDATE__isnull=True) |
                    models.Q(TESTDATE__lte=models.functions.Now())
                ),
                name='ast_testdate_not_future'
            ),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate WHONET_CODE and AST_ID"""
        
        #  Validation: Only allow if culture is Klebsiella positive
        if self.LAB_CULTURE_ID and not self.LAB_CULTURE_ID.is_testable_for_antibiotics:
            raise ValidationError(
                f'Cannot create antibiotic test: Culture {self.LAB_CULTURE_ID.LAB_CULTURE_ID} '
                f'is not positive for Klebsiella pneumoniae'
            )
        
        # Strip whitespace from text fields
        if self.OTHER_ANTIBIOTIC_NAME:
            self.OTHER_ANTIBIOTIC_NAME = self.OTHER_ANTIBIOTIC_NAME.strip()
        if self.MIC:
            self.MIC = self.MIC.strip()
        if self.NOTES:
            self.NOTES = self.NOTES.strip()
        
        #  Generate WHONET code
        if not self.WHONET_CODE:
            self.WHONET_CODE = WHONET_CODES.get(
                self.ANTIBIOTIC_NAME, 
                self.ANTIBIOTIC_NAME[:3].upper()
            )
        
        #  Generate semantic AST_ID (NO SEQUENCE)
        if not self.AST_ID and self.LAB_CULTURE_ID:
            culture_id = self.LAB_CULTURE_ID.LAB_CULTURE_ID
            self.AST_ID = f"{culture_id}-{self.WHONET_CODE}"
        
        # Auto-parse MIC numeric value
        if self.MIC and not self.MIC_NUMERIC:
            self.MIC_NUMERIC = self.parse_mic_value()
        
        super().save(*args, **kwargs)
    
    def parse_mic_value(self):
        """Parse MIC string to extract numeric value"""
        if not self.MIC:
            return None
        
        mic_str = self.MIC.strip()
        mic_clean = re.sub(r'^[<>=]+', '', mic_str)
        
        # Handle ranges (take upper bound)
        if '-' in mic_clean:
            parts = mic_clean.split('-')
            try:
                return float(parts[1])
            except (ValueError, IndexError):
                pass
        
        # Try direct conversion
        try:
            return float(mic_clean)
        except ValueError:
            return None
    
    def __str__(self):
        antibiotic = self.get_antibiotic_display_name()
        sensitivity = self.get_sensitivity_display()
        mic_info = f" (MIC: {self.MIC})" if self.MIC else ""
        return f"{antibiotic} - {sensitivity}{mic_info}"
    
    # ==========================================
    # PROPERTIES
    # ==========================================
    @property
    def SITEID(self):
        """Get SITEID from related LAB_Microbiology"""
        if self.LAB_CULTURE_ID and hasattr(self.LAB_CULTURE_ID, 'SITEID'):
            return self.LAB_CULTURE_ID.SITEID
        return None
    
    @cached_property
    def USUBJID(self):
        """Get patient USUBJID (cached)"""
        if self.LAB_CULTURE_ID and self.LAB_CULTURE_ID.USUBJID:
            # ENR_CASE.USUBJID → SCR_CASE.USUBJID (CharField)
            return self.LAB_CULTURE_ID.USUBJID.USUBJID.USUBJID
        return None
    
    @cached_property
    def is_resistant(self):
        """Check if result indicates resistance"""
        return self.SENSITIVITY_LEVEL == self.SensitivityChoices.RESISTANT
    
    @cached_property
    def is_sensitive(self):
        """Check if fully sensitive (only S counts as sensitive)"""
        return self.SENSITIVITY_LEVEL == self.SensitivityChoices.SENSITIVE
    
    @cached_property
    def is_intermediate(self):
        """Check if intermediate"""
        return self.SENSITIVITY_LEVEL == self.SensitivityChoices.INTERMEDIATE
    
    @cached_property
    def is_unknown(self):
        """Check if result is unknown/unclear"""
        return self.SENSITIVITY_LEVEL == self.SensitivityChoices.UNKNOWN
    
    @cached_property
    def is_not_tested(self):
        """Check if test was not performed"""
        return self.SENSITIVITY_LEVEL == self.SensitivityChoices.NOT_DETERMINED
    
    # ==========================================
    # PROPERTIES
    # ==========================================
    @property
    def display_name(self):
        """Human-readable display"""
        abx_name = self.get_antibiotic_display_name()
        sens = self.get_SENSITIVITY_LEVEL_display()
        mic_info = f" (MIC: {self.MIC})" if self.MIC else ""
        return f"{self.AST_ID}: {abx_name} - {sens}{mic_info}"
    
    def get_antibiotic_display_name(self):
        """Get formatted display name for antibiotic (works for both saved and unsaved instances)"""
        if self.ANTIBIOTIC_NAME == self.AntibioticChoices.OTHER:
            return self.OTHER_ANTIBIOTIC_NAME or _("Other Antibiotic")
        
        # Try to use Django's built-in display method
        try:
            return self.get_ANTIBIOTIC_NAME_display()
        except:
            # For unsaved instances (placeholders), manually lookup the label
            for choice_value, choice_label in self.AntibioticChoices.choices:
                if choice_value == self.ANTIBIOTIC_NAME:
                    return choice_label
            return self.ANTIBIOTIC_NAME
    
    def get_sensitivity_display(self):
        """Get formatted display name for sensitivity level (works for both saved and unsaved instances)"""
        try:
            return self.get_SENSITIVITY_LEVEL_display()
        except:
            # For unsaved instances (placeholders), manually lookup the label
            for choice_value, choice_label in self.SensitivityChoices.choices:
                if choice_value == self.SENSITIVITY_LEVEL:
                    return choice_label
            return self.SENSITIVITY_LEVEL
    
    # ==========================================
    # VALIDATION
    # ==========================================
    def clean(self):
        """Enhanced validation"""
        errors = {}
        
        # Check if culture is eligible for testing
        if self.LAB_CULTURE_ID:
            if not self.LAB_CULTURE_ID.is_testable_for_antibiotics:
                errors['LAB_CULTURE_ID'] = _(
                    f'Culture {self.LAB_CULTURE_ID.LAB_CULTURE_ID} is not positive for Klebsiella. '
                    'Antibiotic sensitivity tests can only be performed on KPN+ cultures.'
                )
        
        # Antibiotic name validation
        if not self.ANTIBIOTIC_NAME:
            errors['ANTIBIOTIC_NAME'] = _('Antibiotic name is required')
        elif self.ANTIBIOTIC_NAME == self.AntibioticChoices.OTHER:
            if not self.OTHER_ANTIBIOTIC_NAME or not self.OTHER_ANTIBIOTIC_NAME.strip():
                errors['OTHER_ANTIBIOTIC_NAME'] = _(
                    'Please specify other antibiotic name'
                )
        
        # Tier validation
        if not self.TIER:
            errors['TIER'] = _('Antibiotic tier is required')
        
        # Date validation
        if self.TESTDATE and self.TESTDATE > date.today():
            errors['TESTDATE'] = _('Test date cannot be in the future')
        
        # Cross-validation with culture
        if self.LAB_CULTURE_ID:
            try:
                culture = self.LAB_CULTURE_ID
                # Test date should be after specimen collection
                if (self.TESTDATE and culture.SPECSAMPDATE and 
                    self.TESTDATE < culture.SPECSAMPDATE):
                    errors['TESTDATE'] = _(
                        'Test date cannot be before specimen collection date'
                    )
            except:
                pass
        
        if errors:
            raise ValidationError(errors)
    
    def _clear_cache(self):
        """Clear all cached properties"""
        cache_attrs = [
            '_SITEID', '_USUBJID', '_is_resistant', '_is_sensitive', 
            '_is_intermediate', '_is_reserve_antibiotic'
        ]
        for attr in cache_attrs:
            if hasattr(self, attr):
                delattr(self, attr)