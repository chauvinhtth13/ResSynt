from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class FollowUpCase(models.Model):
    """
    Patient follow-up at Day 28
    Comprehensive follow-up data including status, rehospitalization, and functional assessment
    """
    
    # Choices definitions using TextChoices
    class AssessedChoices(models.TextChoices):
        YES = 'Yes', _('Yes')
        NO = 'No', _('No')
        NA = 'NA', _('Not Applicable')
    
    class PatientStatusChoices(models.TextChoices):
        ALIVE = 'Alive', _('Alive')
        REHOSPITALIZED = 'Rehospitalized', _('Rehospitalized')
        DECEASED = 'Deceased', _('Deceased')
        LOST_TO_FOLLOWUP = 'LostToFollowUp', _('Lost to Follow-up')
    
    class FunctionalStatusChoices(models.TextChoices):
        NORMAL = 'Normal', _('Normal')
        PROBLEM = 'Problem', _('Problem')
        BEDRIDDEN = 'Bedridden', _('Bedridden')
    
    class AnxietyDepressionChoices(models.TextChoices):
        NONE = 'None', _('None')
        MODERATE = 'Moderate', _('Moderate')
        SEVERE = 'Severe', _('Severe')
    
    class FBSIScoreChoices(models.IntegerChoices):
        SCORE_7 = 7, _('7. Discharged; basically healthy; able to perform high-level daily activities')
        SCORE_6 = 6, _('6. Discharged; moderate symptoms/signs; unable to perform daily activities')
        SCORE_5 = 5, _('5. Discharged; severe disability; requires high-level daily care and support')
        SCORE_4 = 4, _('4. Hospitalized but not in ICU')
        SCORE_3 = 3, _('3. Hospitalized in ICU')
        SCORE_2 = 2, _('2. Long-term ventilation unit')
        SCORE_1 = 1, _('1. End-of-life palliative care (hospital or home)')
        SCORE_0 = 0, _('0. Death')
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Primary key - OneToOne with EnrollmentCase
    USUBJID = models.OneToOneField('EnrollmentCase',
        on_delete=models.CASCADE,
        primary_key=True,
        to_field='USUBJID',
        db_column='USUBJID',
        verbose_name=_('Patient ID')
    )
    
    # 1. Patient assessed at day 28?
    ASSESSED = models.CharField(
        max_length=3,
        choices=AssessedChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Patient Assessed at Day 28?')
    )
    
    ASSESSDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Assessment Date')
    )
    
    # Overall patient status
    PATSTATUS = models.CharField(
        max_length=20,
        choices=PatientStatusChoices.choices,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Patient Status')
    )
    
    # 2. Patient rehospitalized?
    REHOSP = models.CharField(
        max_length=3,
        choices=AssessedChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Patient Rehospitalized?')
    )
    
    REHOSPCOUNT = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Number of Rehospitalizations')
    )
    
    # 3. Patient deceased?
    DECEASED = models.CharField(
        max_length=3,
        choices=AssessedChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Patient Deceased?')
    )
    
    DEATHDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Death Date')
    )
    
    DEATHCAUSE = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Cause of Death')
    )
    
    # 4. Antibiotic use since last visit?
    USEDANTIBIO = models.CharField(
        max_length=3,
        choices=AssessedChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Used Antibiotics Since Last Visit?')
    )
    
    ANTIBIOCOUNT = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Number of Antibiotic Courses')
    )
    
    # 5. Functional status assessment at day 28
    FUNCASSESS = models.CharField(
        max_length=3,
        choices=AssessedChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Functional Status Assessed at Day 28?')
    )
    
    # 5a-5e: Functional aspects
    MOBILITY = models.CharField(
        max_length=20,
        choices=FunctionalStatusChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5a. Mobility (Walking)')
    )
    
    PERHYGIENE = models.CharField(
        max_length=20,
        choices=FunctionalStatusChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5b. Personal Hygiene (Self-bathing, Dressing)')
    )
    
    DAILYACTIV = models.CharField(
        max_length=20,
        choices=FunctionalStatusChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5c. Daily Activities (Work, Study, Housework, Recreation)')
    )
    
    PAINDISCOMF = models.CharField(
        max_length=20,
        choices=FunctionalStatusChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5d. Pain/Discomfort')
    )
    
    ANXIETY_DEPRESSION = models.CharField(
        max_length=20,
        choices=AnxietyDepressionChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5e. Anxiety/Depression')
    )
    
    # 5f. FBSI Score (0-7)
    FBSISCORE = models.IntegerField(
        choices=FBSIScoreChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5f. FBSI Score')
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
    
    class Meta:
        db_table = 'FU_Case_28'
        verbose_name = _('Follow-up Day 28')
        verbose_name_plural = _('Follow-ups Day 28')
        indexes = [
            models.Index(fields=['ASSESSDATE'], name='idx_fuc_assess'),
            models.Index(fields=['PATSTATUS'], name='idx_fuc_status'),
        ]
    
    def __str__(self):
        return f"Follow-up Day 28: {self.USUBJID}"


class FollowUpCase90(models.Model):
    """
    Patient follow-up at Day 90
    Extended follow-up data including status, rehospitalization, and functional assessment
    """
    
    # Choices definitions using TextChoices
    class AssessedChoices(models.TextChoices):
        YES = 'Yes', _('Yes')
        NO = 'No', _('No')
        NA = 'NA', _('Not Applicable')
    
    class PatientStatusChoices(models.TextChoices):
        ALIVE = 'Alive', _('Alive')
        REHOSPITALIZED = 'Rehospitalized', _('Rehospitalized')
        DECEASED = 'Deceased', _('Deceased')
        LOST_TO_FOLLOWUP = 'LostToFollowUp', _('Lost to Follow-up')
    
    class FunctionalStatusChoices(models.TextChoices):
        NORMAL = 'Normal', _('Normal')
        PROBLEM = 'Problem', _('Problem')
        BEDRIDDEN = 'Bedridden', _('Bedridden')
    
    class AnxietyDepressionChoices(models.TextChoices):
        NONE = 'None', _('None')
        MODERATE = 'Moderate', _('Moderate')
        SEVERE = 'Severe', _('Severe')
    
    class FBSIScoreChoices(models.IntegerChoices):
        SCORE_7 = 7, _('7. Discharged; basically healthy; able to perform high-level daily activities')
        SCORE_6 = 6, _('6. Discharged; moderate symptoms/signs; unable to perform daily activities')
        SCORE_5 = 5, _('5. Discharged; severe disability; requires high-level daily care and support')
        SCORE_4 = 4, _('4. Hospitalized but not in ICU')
        SCORE_3 = 3, _('3. Hospitalized in ICU')
        SCORE_2 = 2, _('2. Long-term ventilation unit')
        SCORE_1 = 1, _('1. End-of-life palliative care (hospital or home)')
        SCORE_0 = 0, _('0. Death')
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Primary key - OneToOne with EnrollmentCase
    USUBJID = models.OneToOneField('EnrollmentCase',
        on_delete=models.CASCADE,
        primary_key=True,
        to_field='USUBJID',
        db_column='USUBJID',
        verbose_name=_('Patient ID')
    )
    
    # 1. Patient assessed at day 90?
    ASSESSED = models.CharField(
        max_length=3,
        choices=AssessedChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Patient Assessed at Day 90?')
    )
    
    ASSESSDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Assessment Date')
    )
    
    # Overall patient status
    PATSTATUS = models.CharField(
        max_length=20,
        choices=PatientStatusChoices.choices,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Patient Status')
    )
    
    # 2. Patient rehospitalized?
    REHOSP = models.CharField(
        max_length=3,
        choices=AssessedChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Patient Rehospitalized?')
    )
    
    REHOSPCOUNT = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Number of Rehospitalizations')
    )
    
    # 3. Patient deceased?
    DECEASED = models.CharField(
        max_length=3,
        choices=AssessedChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Patient Deceased?')
    )
    
    DEATHDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Death Date')
    )
    
    DEATHCAUSE = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Cause of Death')
    )
    
    # 4. Antibiotic use since last visit?
    USEDANTIBIO = models.CharField(
        max_length=3,
        choices=AssessedChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Used Antibiotics Since Last Visit?')
    )
    
    ANTIBIOCOUNT = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Number of Antibiotic Courses')
    )
    
    # 5. Functional status assessment at day 90
    FUNCASSESS = models.CharField(
        max_length=3,
        choices=AssessedChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('Functional Status Assessed at Day 90?')
    )
    
    # 5a-5e: Functional aspects
    MOBILITY = models.CharField(
        max_length=20,
        choices=FunctionalStatusChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5a. Mobility (Walking)')
    )
    
    PERHYGIENE = models.CharField(
        max_length=20,
        choices=FunctionalStatusChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5b. Personal Hygiene (Self-bathing, Dressing)')
    )
    
    DAILYACTIV = models.CharField(
        max_length=20,
        choices=FunctionalStatusChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5c. Daily Activities (Work, Study, Housework, Recreation)')
    )
    
    PAINDISCOMF = models.CharField(
        max_length=20,
        choices=FunctionalStatusChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5d. Pain/Discomfort')
    )
    
    ANXIETY_DEPRESSION = models.CharField(
        max_length=20,
        choices=AnxietyDepressionChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5e. Anxiety/Depression')
    )
    
    # 5f. FBSI Score (0-7)
    FBSISCORE = models.IntegerField(
        choices=FBSIScoreChoices.choices,
        null=True,
        blank=True,
        verbose_name=_('5f. FBSI Score')
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
    
    class Meta:
        db_table = 'FU_Case_90'
        verbose_name = _('Follow-up Day 90')
        verbose_name_plural = _('Follow-ups Day 90')
        indexes = [
            models.Index(fields=['ASSESSDATE'], name='idx_fuc90_assess'),
            models.Index(fields=['PATSTATUS'], name='idx_fuc90_status'),
        ]
    
    def __str__(self):
        return f"Follow-up Day 90: {self.USUBJID}"