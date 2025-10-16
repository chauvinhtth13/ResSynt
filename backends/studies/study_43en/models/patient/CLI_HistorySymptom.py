# backends/studies/study_43en/models/SYM_BasicSymptom.py

from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class HistorySymptom(models.Model):
    """
    Patient's basic symptoms at admission
    Each symptom is a separate Boolean field
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
        related_name='History_Symptom',
        verbose_name=_('Patient ID')
    )
    
    # Basic symptoms - mỗi triệu chứng là 1 trường Boolean
    FEVER = models.BooleanField(
        default=False,
        verbose_name=_('Fever')
    )
    
    FATIGUE = models.BooleanField(
        default=False,
        verbose_name=_('Fatigue')
    )
    
    MUSCLEPAIN = models.BooleanField(
        default=False,
        verbose_name=_('Muscle Pain')
    )
    
    LOSSAPPETITE = models.BooleanField(
        default=False,
        verbose_name=_('Loss of Appetite')
    )
    
    COUGH = models.BooleanField(
        default=False,
        verbose_name=_('Cough')
    )
    
    CHESTPAIN = models.BooleanField(
        default=False,
        verbose_name=_('Chest Pain')
    )
    
    SHORTBREATH = models.BooleanField(
        default=False,
        verbose_name=_('Shortness of Breath')
    )
    
    JAUNDICE = models.BooleanField(
        default=False,
        verbose_name=_('Jaundice')
    )
    
    PAINURINATION = models.BooleanField(
        default=False,
        verbose_name=_('Painful Urination')
    )
    
    BLOODYURINE = models.BooleanField(
        default=False,
        verbose_name=_('Bloody Urine')
    )
    
    CLOUDYURINE = models.BooleanField(
        default=False,
        verbose_name=_('Cloudy Urine')
    )
    
    EPIGASTRICPAIN = models.BooleanField(
        default=False,
        verbose_name=_('Epigastric Pain')
    )
    
    LOWERABDPAIN = models.BooleanField(
        default=False,
        verbose_name=_('Lower Abdominal Pain')
    )
    
    FLANKPAIN = models.BooleanField(
        default=False,
        verbose_name=_('Flank Pain')
    )
    
    URINARYHESITANCY = models.BooleanField(
        default=False,
        verbose_name=_('Urinary Hesitancy')
    )
    
    SUBCOSTALPAIN = models.BooleanField(
        default=False,
        verbose_name=_('Subcostal Pain')
    )
    
    HEADACHE = models.BooleanField(
        default=False,
        verbose_name=_('Headache')
    )
    
    POORCONTACT = models.BooleanField(
        default=False,
        verbose_name=_('Poor Contact')
    )
    
    DELIRIUMAGITATION = models.BooleanField(
        default=False,
        verbose_name=_('Delirium/Agitation')
    )
    
    VOMITING = models.BooleanField(
        default=False,
        verbose_name=_('Vomiting')
    )
    
    SEIZURES = models.BooleanField(
        default=False,
        verbose_name=_('Seizures')
    )
    
    EYEPAIN = models.BooleanField(
        default=False,
        verbose_name=_('Eye Pain')
    )
    
    REDEYES = models.BooleanField(
        default=False,
        verbose_name=_('Red Eyes')
    )
    
    NAUSEA = models.BooleanField(
        default=False,
        verbose_name=_('Nausea')
    )
    
    BLURREDVISION = models.BooleanField(
        default=False,
        verbose_name=_('Blurred Vision')
    )
    
    SKINLESIONS = models.BooleanField(
        default=False,
        verbose_name=_('Skin Lesions')
    )
    
    OTHERSYMPTOM = models.BooleanField(
        default=False,
        verbose_name=_('Other Symptoms')
    )
    
    SPECIFYOTHERSYMPTOM = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Other History Symptoms Details')
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
        db_table = 'CLI_HistorySymptom'
        verbose_name = _('Patient History Symptom')
        verbose_name_plural = _('Patient History Symptoms')
    
    def __str__(self):
        return f"History Symptoms: {self.USUBJID}"
    
    @property
    def symptom_count(self):
        """Count total number of symptoms"""
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