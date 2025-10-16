from django.db import models
from django.utils.translation import gettext_lazy as _


class AntibioticSensitivity(models.Model):
    """
    Antibiotic sensitivity results for positive culture specimens
    Tracks sensitivity levels and MIC values
    """
    
    # Choices definitions using TextChoices
    class TierChoices(models.TextChoices):
        TIER1 = 'TIER1', _('Tier 1')
        TIER2 = 'TIER2', _('Tier 2')
        TIER3 = 'TIER3', _('Tier 3')
        TIER4 = 'TIER4', _('Tier 4')
        COLISTIN = 'COLISTIN', _('Colistin')
        URINE_ONLY = 'URINE_ONLY', _('Urine Only')
        OTHER = 'OTHER', _('Other Antibiotics')
    
    class AntibioticChoices(models.TextChoices):
        # Tier 1
        AMPICILLIN = 'Ampicillin', _('Ampicillin')
        CEFAZOLIN = 'Cefazolin', _('Cefazolin')
        CEFOTAXIME = 'Cefotaxime', _('Cefotaxime')
        CEFTRIAXONE = 'Ceftriaxone', _('Ceftriaxone')
        AMOXICILLIN_CLAVULANATE = 'AmoxicillinClavulanate', _('Amoxicillin-Clavulanate')
        AMPICILLIN_SULBACTAM = 'AmpicillinSulbactam', _('Ampicillin-Sulbactam')
        PIPERACILLIN_TAZOBACTAM = 'PiperacillinTazobactam', _('Piperacillin-Tazobactam')
        GENTAMICIN = 'Gentamicin', _('Gentamicin')
        CIPROFLOXACIN = 'Ciprofloxacin', _('Ciprofloxacin')
        LEVOFLOXACIN = 'Levofloxacin', _('Levofloxacin')
        TRIMETHOPRIM_SULFAMETHOXAZOLE = 'TrimethoprimSulfamethoxazole', _('Trimethoprim-Sulfamethoxazole')
        
        # Tier 2
        CEFEPIME = 'Cefepime', _('Cefepime')
        IMIPENEM = 'Imipenem', _('Imipenem')
        MEROPENEM = 'Meropenem', _('Meropenem')
        CEFUROXIME = 'Cefuroxime', _('Cefuroxime')
        ERTAPENEM = 'Ertapenem', _('Ertapenem')
        CEFOXITIN = 'Cefoxitin', _('Cefoxitin')
        TOBRAMYCIN = 'Tobramycin', _('Tobramycin')
        AMIKACIN = 'Amikacin', _('Amikacin')
        CEFOTETAN = 'Cefotetan', _('Cefotetan')
        TETRACYCLINE = 'Tetracycline', _('Tetracycline')
        
        # Tier 3
        CEFIDEROCOL = 'Cefiderocol', _('Cefiderocol')
        CEFTAZIDIME_AVIBACTAM = 'CeftazidimeAvibactam', _('Ceftazidime-Avibactam')
        IMIPENEM_RELEBACTAM = 'ImipenemRelebactam', _('Imipenem-Relebactam')
        MEROPENEM_VABORBACTAM = 'MeropenemVaborbactam', _('Meropenem-Vaborbactam')
        PLAZOMICIN = 'Plazomicin', _('Plazomicin')
        
        # Tier 4
        AZTREONAM = 'Aztreonam', _('Aztreonam')
        CEFTAROLINE = 'Ceftaroline', _('Ceftaroline')
        CEFTAZIDIME = 'Ceftazidime', _('Ceftazidime')
        CEFTOLOZANE_TAZOBACTAM = 'CeftolozaneTazobactam', _('Ceftolozane-Tazobactam')
        
        # Colistin
        COLISTIN = 'Colistin', _('Colistin')
        
        # Urine Only
        CEFAZOLIN_URINE = 'Cefazolin_Urine', _('Cefazolin (Urine)')
        NITROFURANTOIN = 'Nitrofurantoin', _('Nitrofurantoin')
        FOSFOMYCIN = 'Fosfomycin', _('Fosfomycin')
        
        # Other common antibiotics
        CEFTRIAZONE = 'Ceftriazone', _('Ceftriazone')
        TIGECYCLINE = 'Tigecycline', _('Tigecycline')
        TICARCILLIN_CLAVULANIC = 'TicarcillinClavulanic', _('Ticarcillin-Clavulanic')
        CEFOPERAZONE_SULBACTAM = 'CefoperazoneSulbactam', _('Cefoperazone-Sulbactam')
        OTHER = 'OTHER', _('Other Antibiotic')
    
    class SensitivityChoices(models.TextChoices):
        SENSITIVE = 'S', _('Sensitive (S)')
        INTERMEDIATE = 'I', _('Intermediate (I)')
        RESISTANT = 'R', _('Resistant (R)')
        NOT_DETERMINED = 'ND', _('Not Determined (ND)')
        UNKNOWN = 'U', _('Unknown (U)')
    
    # Foreign key
    USUBJID = models.ForeignKey('LAB_Microbiology',
        on_delete=models.CASCADE,
        related_name='antibiotic_sensitivities',
        db_column='USUBJID',
        verbose_name=_('LAB Culture')
    )
    
    TIER = models.CharField(
        max_length=20,
        choices=TierChoices.choices,
        db_index=True,
        verbose_name=_('Antibiotic Tier')
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
        verbose_name=_('Other Antibiotic Name')
    )
    
    SENSITIVITY_LEVEL = models.CharField(
        max_length=2,
        choices=SensitivityChoices.choices,
        default=SensitivityChoices.NOT_DETERMINED,
        db_index=True,
        verbose_name=_('Sensitivity Level')
    )
    
    IZDIAM = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name=_('Inhibition Zone Diameter (mm)')
    )
    
    MIC = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name=_('MIC Value')
    )
    
    SEQUENCE = models.IntegerField(
        default=1,
        verbose_name=_('Sequence Number')
    )
    
    # Metadata
    CREATED_AT = models.DateTimeField(auto_now_add=True)
    UPDATED_AT = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'LAB_Antibiotic_Sensitivity'
        verbose_name = _('Antibiotic Sensitivity')
        verbose_name_plural = _('Antibiotic Sensitivities')
        unique_together = ['USUBJID', 'ANTIBIOTIC_NAME', 'OTHER_ANTIBIOTIC_NAME']
        ordering = ['TIER', 'SEQUENCE', 'ANTIBIOTIC_NAME']
        indexes = [
            models.Index(fields=['TIER', 'SENSITIVITY_LEVEL'], name='idx_as_tier_sens'),
            models.Index(fields=['ANTIBIOTIC_NAME'], name='idx_as_antibiotic'),
        ]

    def __str__(self):
        antibiotic_display = self.get_antibiotic_display_name()
        sensitivity_display = self.get_SENSITIVITY_LEVEL_display()
        return f"{antibiotic_display} - {sensitivity_display}"

    def get_antibiotic_display_name(self):
        """Get display name for antibiotic"""
        if self.ANTIBIOTIC_NAME == self.AntibioticChoices.OTHER:
            return self.OTHER_ANTIBIOTIC_NAME or _("Other Antibiotic")
        return self.get_ANTIBIOTIC_NAME_display()