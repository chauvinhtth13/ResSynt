from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class ClinicalCase(models.Model):
    """
    Clinical information for enrolled patients
    Comprehensive clinical data including symptoms, vital signs, and treatment
    """
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Choices definitions using TextChoices
    class ThreeStateChoices(models.TextChoices):
        YES = 'yes', _('Yes')
        NO = 'no', _('No')
        UNKNOWN = 'unknown', _('Unknown')
    
    class InfectFocus48HChoices(models.TextChoices):
        ABD_ABSCESS = 'AbdAbscess', _('Abdominal Abscess')
        EMPYEMA = 'Empyema', _('Empyema')
        MENINGITIS = 'Meningitis', _('Meningitis')
        NTTKTW = 'NTTKTW', _('NTTKTW')
        PERITONITIS = 'Peritonitis', _('Peritonitis')
        OSTEOMYELITIS = 'Osteomyelitis', _('Osteomyelitis')
        OTHER = 'Other', _('Other')
        PNEUMONIA = 'Pneumonia', _('Pneumonia/Lung Abscess')
        SOFT_TISSUE = 'SoftTissue', _('Skin/Soft Tissue')
        UNKNOWN = 'Unk', _('Unknown')
        UTI = 'UTI', _('Urinary Tract Infection')
    
    class InfectSrcChoices(models.TextChoices):
        COMMUNITY = 'Community', _('Community-Acquired')
        HEALTHCARE_ASSOCIATED = 'HealthcareAssociated', _('Healthcare-Associated')
    
    class SupportTypeChoices(models.TextChoices):
        OXY_MASK = 'Oxy mũi/mask', _('Nasal Cannula/Mask')
        HFNC_NIV = 'HFNC/NIV', _('HFNC/NIV')
        VENTILATOR = 'Thở máy', _('Mechanical Ventilation')
    
    class FluidChoices(models.TextChoices):
        CRYSTAL = 'Crystal', _('Crystalloid')
        COLLOID = 'Colloid', _('Colloid')
    
    class DrainageTypeChoices(models.TextChoices):
        ABSCESS = 'Abscess', _('Abscess')
        EMPYEMA = 'Empyema', _('Empyema')
        OTHER = 'Other', _('Other')
    
    # Primary key - OneToOne with EnrollmentCase
    USUBJID = models.OneToOneField('EnrollmentCase',
        on_delete=models.CASCADE,
        primary_key=True,
        to_field='USUBJID',
        db_column='USUBJID',
        verbose_name=_('Patient ID')
    )
    
    # Basic information
    EVENT = models.CharField(
        max_length=50,
        default='CASE',
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
        verbose_name=_('Initials')
    )
    
    # Admission information
    ADMISDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Admission Date')
    )
    
    ADMISREASON = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Reason for Admission')
    )
    
    SYMPTOMONSETDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Symptom Onset Date')
    )
    
    ADMISDEPT = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Admission Department')
    )
    
    OUTPATIENT_ERDEPT = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Outpatient/ER Department')
    )
    
    SYMPTOMADMISDEPT = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Symptoms at Admission')
    )
    
    # Consciousness assessment
    AWARENESS = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Level of Consciousness')
    )
    
    GCS = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Glasgow Coma Scale (GCS)')
    )
    
    EYES = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Eye Opening Response')
    )
    
    MOTOR = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Motor Response')
    )
    
    VERBAL = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Verbal Response')
    )
    
    # Vital signs
    PULSE = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Heart Rate (bpm)')
    )
    
    AMPLITUDE = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Pulse Amplitude')
    )
    
    CAPILLARYMOIS = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Capillary Moisture')
    )
    
    CRT = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Capillary Refill Time (seconds)')
    )
    
    TEMPERATURE = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Temperature (°C)')
    )
    
    BLOODPRESSURE_SYS = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Systolic Blood Pressure (mmHg)')
    )
    
    BLOODPRESSURE_DIAS = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Diastolic Blood Pressure (mmHg)')
    )
    
    RESPRATE = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Respiratory Rate (breaths/min)')
    )
    
    SPO2 = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('SpO2 (%)')
    )
    
    FIO2 = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('FiO2 (%)')
    )
    
    # Respiratory pattern
    RESPPATTERN = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Respiratory Pattern')
    )
    
    RESPPATTERNOTHERSPEC = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Other Respiratory Pattern Details')
    )
    
    RESPSUPPORT = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Respiratory Support')
    )
    
    # Clinical scores
    VASOMEDS = models.BooleanField(
        default=False,
        verbose_name=_('Vasoactive Medications')
    )
    
    HYPOTENSION = models.BooleanField(
        default=False,
        verbose_name=_('Hypotension')
    )
    
    QSOFA = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('qSOFA Score')
    )
    
    NEWS2 = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('NEWS2 Score')
    )
    
    # Symptoms group 1 (Basic symptoms)
    LISTBASICSYMTOMS = models.JSONField(
        default=list,
        null=True,
        blank=True,
        verbose_name=_('Basic Symptoms List')
    )
    
    OTHERSYMPTOM = models.BooleanField(
        default=False,
        verbose_name=_('Other Symptoms')
    )
    
    SPECIFYOTHERSYMPTOM = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Other Symptoms Details')
    )
    
    # Physical measurements
    WEIGHT = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Weight (kg)')
    )
    
    HEIGHT = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Height (cm)')
    )
    
    BMI = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Body Mass Index')
    )
    
    # Symptoms group 2 (Clinical examination)
    LISTCLINISYMTOMS = models.JSONField(
        default=list,
        null=True,
        blank=True,
        verbose_name=_('Clinical Symptoms List')
    )
    
    OTHERSYMPTOM_2 = models.BooleanField(
        default=False,
        verbose_name=_('Other Clinical Symptoms')
    )
    
    SPECIFYOTHERSYMPTOM_2 = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Other Clinical Symptoms Details')
    )
    
    TOTALCULTURERES = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Total Culture Results')
    )
    
    # Infection information
    INFECTFOCUS48H = models.CharField(
        max_length=50,
        choices=InfectFocus48HChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Infection Focus within 48h')
    )
    
    SPECIFYOTHERINFECT48H = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Other Infection Details')
    )
    
    BLOODINFECT = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Bloodstream Infection')
    )
    
    SOFABASELINE = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Baseline SOFA Score')
    )
    
    DIAGSOFA = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('SOFA Score at Diagnosis')
    )
    
    SEPTICSHOCK = models.CharField(
        max_length=10,
        choices=ThreeStateChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Septic Shock')
    )
    
    INFECTSRC = models.CharField(
        max_length=50,
        choices=InfectSrcChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Infection Source')
    )
    
    # Respiratory support
    RESPISUPPORT = models.BooleanField(
        default=False,
        verbose_name=_('Respiratory Support Provided')
    )
    
    SUPPORTTYPE = ArrayField(
        models.CharField(max_length=50, choices=SupportTypeChoices.choices),
        default=list,
        blank=True,
        null=True,
        verbose_name=_('Support Type')
    )
    
    OXYMASKDURATION = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Oxygen Mask Duration (days)')
    )
    
    HFNCNIVDURATION = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('HFNC/NIV Duration (days)')
    )
    
    VENTILATORDURATION = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Ventilator Duration (days)')
    )
    
    # Fluid resuscitation
    RESUSFLUID = models.BooleanField(
        default=False,
        verbose_name=_('Resuscitation Fluid Given')
    )
    
    FLUID6HOURS = models.CharField(
        max_length=50,
        choices=FluidChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Fluid Type (First 6 hours)')
    )
    
    CRYSTAL6HRS = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Crystalloid Volume 6h (ml)')
    )
    
    COL6HRS = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Colloid Volume 6h (ml)')
    )
    
    FLUID24HOURS = models.CharField(
        max_length=50,
        choices=FluidChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Fluid Type (First 24 hours)')
    )
    
    CRYSTAL24HRS = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Crystalloid Volume 24h (ml)')
    )
    
    COL24HRS = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Colloid Volume 24h (ml)')
    )
    
    # Other treatments
    VASOINOTROPES = models.BooleanField(
        default=False,
        verbose_name=_('Vasopressors/Inotropes Used')
    )
    
    DIALYSIS = models.BooleanField(
        default=False,
        verbose_name=_('Dialysis Performed')
    )
    
    DRAINAGE = models.BooleanField(
        default=False,
        verbose_name=_('Drainage Performed')
    )
    
    DRAINAGETYPE = models.CharField(
        max_length=50,
        choices=DrainageTypeChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Drainage Type')
    )
    
    SPECIFYOTHERDRAINAGE = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Other Drainage Details')
    )
    
    # Antibiotic information
    PRIORANTIBIOTIC = models.BooleanField(
        default=False,
        verbose_name=_('Prior Antibiotic Use')
    )
    
    INITIALANTIBIOTIC = models.BooleanField(
        default=False,
        verbose_name=_('Initial Antibiotic Given')
    )
    
    INITIALABXAPPROP = models.BooleanField(
        default=False,
        verbose_name=_('Initial Antibiotic Appropriate')
    )
    
    # Completion info
    COMPLETEDBY = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Completed By')
    )
    
    COMPLETEDDATE = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Completion Date')
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
        db_table = 'CLI_Case'
        verbose_name = _('Clinical Case')
        verbose_name_plural = _('Clinical Cases')
        indexes = [
            models.Index(fields=['ADMISDATE'], name='idx_clin_admis'),
            models.Index(fields=['INFECTFOCUS48H'], name='idx_clin_infect'),
        ]
    
    def __str__(self):
        return f"Clinical Case: {self.USUBJID}"
    
    @property
    def SITEID(self):
        """Get SITEID from related EnrollmentCase"""
        return self.USUBJID.SITEID if self.USUBJID else None
    
    # Property getters for basic symptoms (Group 1)
    @property
    def FEVER(self):
        return 'FEVER' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def FATIGUE(self):
        return 'FATIGUE' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def MUSCLEPAIN(self):
        return 'MUSCLEPAIN' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def LOSSAPPETITE(self):
        return 'LOSSAPPETITE' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def COUGH(self):
        return 'COUGH' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def CHESTPAIN(self):
        return 'CHESTPAIN' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def SHORTBREATH(self):
        return 'SHORTBREATH' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def JAUNDICE(self):
        return 'JAUNDICE' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def PAINURINATION(self):
        return 'PAINURINATION' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def BLOODYURINE(self):
        return 'BLOODYURINE' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def CLOUDYURINE(self):
        return 'CLOUDYURINE' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def EPIGASTRICPAIN(self):
        return 'EPIGASTRICPAIN' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def LOWERABDPAIN(self):
        return 'LOWERABDPAIN' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def FLANKPAIN(self):
        return 'FLANKPAIN' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def URINARYHESITANCY(self):
        return 'URINARYHESITANCY' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def SUBCOSTALPAIN(self):
        return 'SUBCOSTALPAIN' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def HEADACHE(self):
        return 'HEADACHE' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def POORCONTACT(self):
        return 'POORCONTACT' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def DELIRIUMAGITATION(self):
        return 'DELIRIUMAGITATION' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def VOMITING(self):
        return 'VOMITING' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def SEIZURES(self):
        return 'SEIZURES' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def EYEPAIN(self):
        return 'EYEPAIN' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def REDEYES(self):
        return 'REDEYES' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def NAUSEA(self):
        return 'NAUSEA' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def BLURREDVISION(self):
        return 'BLURREDVISION' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    @property
    def SKINLESIONS(self):
        return 'SKINLESIONS' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
    # Property getters for clinical symptoms (Group 2)
    @property
    def FEVER_2(self):
        return 'FEVER_2' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def RASH(self):
        return 'RASH' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def SKINBLEEDING(self):
        return 'SKINBLEEDING' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def MUCOSALBLEEDING(self):
        return 'MUCOSALBLEEDING' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def SKINLESIONS_2(self):
        return 'SKINLESIONS_2' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def LUNGCRACKLES(self):
        return 'LUNGCRACKLES' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def CONSOLIDATIONSYNDROME(self):
        return 'CONSOLIDATIONSYNDROME' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def PLEURALEFFUSION(self):
        return 'PLEURALEFFUSION' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def PNEUMOTHORAX(self):
        return 'PNEUMOTHORAX' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def HEARTMURMUR(self):
        return 'HEARTMURMUR' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def ABNORHEARTSOUNDS(self):
        return 'ABNORHEARTSOUNDS' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def JUGULARVEINDISTENTION(self):
        return 'JUGULARVEINDISTENTION' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def LIVERFAILURESIGNS(self):
        return 'LIVERFAILURESIGNS' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def PORTALHYPERTENSIONSIGNS(self):
        return 'PORTALHYPERTENSIONSIGNS' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def HEPATOSPLENOMEGALY(self):
        return 'HEPATOSPLENOMEGALY' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def CONSCIOUSNESSDISTURBANCE(self):
        return 'CONSCIOUSNESSDISTURBANCE' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def LIMBWEAKNESSPARALYSIS(self):
        return 'LIMBWEAKNESSPARALYSIS' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def CRANIALNERVEPARALYSIS(self):
        return 'CRANIALNERVEPARALYSIS' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def MENINGEALSIGNS(self):
        return 'MENINGEALSIGNS' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def REDEYES_2(self):
        return 'REDEYES_2' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def HYPOPYON(self):
        return 'HYPOPYON' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def EDEMA(self):
        return 'EDEMA' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def CUSHINGOIDAPPEARANCE(self):
        return 'CUSHINGOIDAPPEARANCE' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def EPIGASTRICPAIN_2(self):
        return 'EPIGASTRICPAIN_2' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def LOWERABDPAIN_2(self):
        return 'LOWERABDPAIN_2' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def FLANKPAIN_2(self):
        return 'FLANKPAIN_2' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    @property
    def SUBCOSTALPAIN_2(self):
        return 'SUBCOSTALPAIN_2' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
    # Infection focus property getters
    @property
    def is_AbdAbscess(self):
        return self.INFECTFOCUS48H == self.InfectFocus48HChoices.ABD_ABSCESS
    
    @property
    def is_Empyema(self):
        return self.INFECTFOCUS48H == self.InfectFocus48HChoices.EMPYEMA
    
    @property
    def is_Meningitis(self):
        return self.INFECTFOCUS48H == self.InfectFocus48HChoices.MENINGITIS
    
    @property
    def is_NTTKTW(self):
        return self.INFECTFOCUS48H == self.InfectFocus48HChoices.NTTKTW
    
    @property
    def is_Peritonitis(self):
        return self.INFECTFOCUS48H == self.InfectFocus48HChoices.PERITONITIS
    
    @property
    def is_Osteomyelitis(self):
        return self.INFECTFOCUS48H == self.InfectFocus48HChoices.OSTEOMYELITIS
    
    @property
    def is_Other_Infection(self):
        return self.INFECTFOCUS48H == self.InfectFocus48HChoices.OTHER
    
    @property
    def is_Pneumonia(self):
        return self.INFECTFOCUS48H == self.InfectFocus48HChoices.PNEUMONIA
    
    @property
    def is_SoftTissue(self):
        return self.INFECTFOCUS48H == self.InfectFocus48HChoices.SOFT_TISSUE
    
    @property
    def is_Unk(self):
        return self.INFECTFOCUS48H == self.InfectFocus48HChoices.UNKNOWN
    
    @property
    def is_UTI(self):
        return self.INFECTFOCUS48H == self.InfectFocus48HChoices.UTI
    
    # Clinical status property getters
    @property
    def has_bloodstream_infection(self):
        return self.BLOODINFECT == self.ThreeStateChoices.YES
    
    @property
    def has_septic_shock(self):
        return self.SEPTICSHOCK == self.ThreeStateChoices.YES
    
    @property
    def is_community_acquired(self):
        return self.INFECTSRC == self.InfectSrcChoices.COMMUNITY
    
    @property
    def is_healthcare_associated(self):
        return self.INFECTSRC == self.InfectSrcChoices.HEALTHCARE_ASSOCIATED
    
    # Respiratory support property getters
    @property
    def has_oxygen_mask(self):
        return self.SUPPORTTYPE and self.SupportTypeChoices.OXY_MASK in self.SUPPORTTYPE
    
    @property
    def has_hfnc_niv(self):
        return self.SUPPORTTYPE and self.SupportTypeChoices.HFNC_NIV in self.SUPPORTTYPE
    
    @property
    def has_ventilator(self):
        return self.SUPPORTTYPE and self.SupportTypeChoices.VENTILATOR in self.SUPPORTTYPE
    
    # Drainage property getters
    @property
    def has_abscess_drainage(self):
        return self.DRAINAGE and self.DRAINAGETYPE == self.DrainageTypeChoices.ABSCESS
    
    @property
    def has_empyema_drainage(self):
        return self.DRAINAGE and self.DRAINAGETYPE == self.DrainageTypeChoices.EMPYEMA
    
    @property
    def has_other_drainage(self):
        return self.DRAINAGE and self.DRAINAGETYPE == self.DrainageTypeChoices.OTHER