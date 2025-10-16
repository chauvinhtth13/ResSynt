# backends/studies/study_43en/models/SYM_ClinicalSymptom.py

from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class Symptom_72H(models.Model):
    """
    Patient's clinical examination findings
    Each finding is a separate Boolean field
    """
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key (1-to-1 với ClinicalCase)
    USUBJID = models.OneToOneField('ClinicalCase',
        on_delete=models.CASCADE,
        primary_key=True,
        to_field='USUBJID',
        db_column='USUBJID',
        related_name='Symptom_72H',
        verbose_name=_('Patient ID')
    )
    
    # Clinical symptoms - mỗi triệu chứng là 1 trường Boolean
    FEVER_2 = models.BooleanField(
        default=False,
        verbose_name=_('Fever (Clinical)')
    )
    
    RASH = models.BooleanField(
        default=False,
        verbose_name=_('Rash')
    )
    
    SKINBLEEDING = models.BooleanField(
        default=False,
        verbose_name=_('Skin Bleeding')
    )
    
    MUCOSALBLEEDING = models.BooleanField(
        default=False,
        verbose_name=_('Mucosal Bleeding')
    )
    
    SKINLESIONS_2 = models.BooleanField(
        default=False,
        verbose_name=_('Skin Lesions')
    )
    
    LUNGCRACKLES = models.BooleanField(
        default=False,
        verbose_name=_('Lung Crackles')
    )
    
    CONSOLIDATIONSYNDROME = models.BooleanField(
        default=False,
        verbose_name=_('Consolidation Syndrome')
    )
    
    PLEURALEFFUSION = models.BooleanField(
        default=False,
        verbose_name=_('Pleural Effusion')
    )
    
    PNEUMOTHORAX = models.BooleanField(
        default=False,
        verbose_name=_('Pneumothorax')
    )
    
    HEARTMURMUR = models.BooleanField(
        default=False,
        verbose_name=_('Heart Murmur')
    )
    
    ABNORHEARTSOUNDS = models.BooleanField(
        default=False,
        verbose_name=_('Abnormal Heart Sounds')
    )
    
    JUGULARVEINDISTENTION = models.BooleanField(
        default=False,
        verbose_name=_('Jugular Vein Distention')
    )
    
    LIVERFAILURESIGNS = models.BooleanField(
        default=False,
        verbose_name=_('Liver Failure Signs')
    )
    
    PORTALHYPERTENSIONSIGNS = models.BooleanField(
        default=False,
        verbose_name=_('Portal Hypertension Signs')
    )
    
    HEPATOSPLENOMEGALY = models.BooleanField(
        default=False,
        verbose_name=_('Hepatosplenomegaly')
    )
    
    CONSCIOUSNESSDISTURBANCE = models.BooleanField(
        default=False,
        verbose_name=_('Consciousness Disturbance')
    )
    
    LIMBWEAKNESSPARALYSIS = models.BooleanField(
        default=False,
        verbose_name=_('Limb Weakness/Paralysis')
    )
    
    CRANIALNERVEPARALYSIS = models.BooleanField(
        default=False,
        verbose_name=_('Cranial Nerve Paralysis')
    )
    
    MENINGEALSIGNS = models.BooleanField(
        default=False,
        verbose_name=_('Meningeal Signs')
    )
    
    REDEYES_2 = models.BooleanField(
        default=False,
        verbose_name=_('Red Eyes')
    )
    
    HYPOPYON = models.BooleanField(
        default=False,
        verbose_name=_('Hypopyon')
    )
    
    EDEMA = models.BooleanField(
        default=False,
        verbose_name=_('Edema')
    )
    
    CUSHINGOIDAPPEARANCE = models.BooleanField(
        default=False,
        verbose_name=_('Cushingoid Appearance')
    )
    
    EPIGASTRICPAIN_2 = models.BooleanField(
        default=False,
        verbose_name=_('Epigastric Pain')
    )
    
    LOWERABDPAIN_2 = models.BooleanField(
        default=False,
        verbose_name=_('Lower Abdominal Pain')
    )
    
    FLANKPAIN_2 = models.BooleanField(
        default=False,
        verbose_name=_('Flank Pain')
    )
    
    SUBCOSTALPAIN_2 = models.BooleanField(
        default=False,
        verbose_name=_('Subcostal Pain')
    )
    
    OTHERSYMPTOM_2 = models.BooleanField(
        default=False,
        verbose_name=_('Other Clinical Symptoms')
    )
    
    SPECIFYOTHERSYMPTOM_2 = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Other Symptoms_72H Details')
    )
    
    # Metadata
    ENTRY = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Data Entry Person')
    )
    
    ENTEREDTIME = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Entry Time')
    )
    
    class Meta:
        db_table = 'CLI_Symptom_72H'
        verbose_name = _('Patient Symptom 72H')
        verbose_name_plural = _('Symptoms_72H')
    
    def __str__(self):
        return f"Symptoms_72H: {self.USUBJID}"
    
    @property
    def symptom_count(self):
        """Count total number of clinical findings"""
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