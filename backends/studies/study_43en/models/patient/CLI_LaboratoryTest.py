from django.db import models
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.study_site_manage import SiteFilteredManage


class LaboratoryTest(models.Model):
    """
    Laboratory test and imaging results
    Tracks various lab tests and diagnostic imaging across 3 time points
    """
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Choices definitions using TextChoices
    class LabTypeChoices(models.TextChoices):
        TEST1 = '1', _('Test 1 (First 24h)')
        TEST2 = '2', _('Test 2 (48-72h after initial antibiotics)')
        TEST3 = '3', _('Test 3 (Within 72h before discharge)')
    
    class CategoryChoices(models.TextChoices):
        BLOOD_COAGULATION = 'BLOOD_COAGULATION', _('11. Blood Coagulation')
        COMPLETE_BLOOD_COUNT = 'COMPLETE_BLOOD_COUNT', _('12. Complete Blood Count')
        BIOCHEMISTRY = 'BIOCHEMISTRY', _('13. Biochemistry & Immunology')
        BLOOD_GAS_ANALYSIS = 'BLOOD_GAS_ANALYSIS', _('14. Arterial Blood Gas')
        LACTATE = 'LACTATE', _('15. Arterial Lactate')
        URINE_ANALYSIS = 'URINE_ANALYSIS', _('16. Urinalysis')
        PLEURAL_FLUID = 'PLEURAL_FLUID', _('17. Peritoneal Fluid')
        PLEURAL_FLUID_ANALYSIS = 'PLEURAL_FLUID_ANALYSIS', _('18. Pleural Fluid')
        CSF_ANALYSIS = 'CSF_ANALYSIS', _('19. Cerebrospinal Fluid')
        CHEST_XRAY = 'CHEST_XRAY', _('20. Chest X-Ray')
        ABDOMINAL_ULTRASOUND = 'ABDOMINAL_ULTRASOUND', _('21. Abdominal Ultrasound')
        BRAIN_CT_MRI = 'BRAIN_CT_MRI', _('22. Brain CT/MRI')
        CHEST_ABDOMEN_CT = 'CHEST_ABDOMEN_CT', _('23. Chest/Abdomen CT')
        ECHOCARDIOGRAPHY = 'ECHOCARDIOGRAPHY', _('24. Echocardiography')
        SOFT_TISSUE_ULTRASOUND = 'SOFT_TISSUE_ULTRASOUND', _('25. Soft Tissue Ultrasound')
    
    class TestTypeChoices(models.TextChoices):
        # 11. Blood Coagulation
        INR = 'INR', _('INR')
        DIC = 'DIC', _('DIC')
        
        # 12. Complete Blood Count
        WBC = 'WBC', _('White Blood Cells')
        NEU = 'NEU', _('Neutrophils')
        LYM = 'LYM', _('Lymphocytes')
        EOS = 'EOS', _('Eosinophils')
        RBC = 'RBC', _('Red Blood Cells')
        HEMOGLOBIN = 'HEMOGLOBIN', _('Hemoglobin')
        PLATELETS = 'PLATELETS', _('Platelets')
        
        # 13. Biochemistry & Immunology
        NATRI = 'NATRI', _('Sodium')
        KALI = 'KALI', _('Potassium')
        CLO = 'CLO', _('Chloride')
        MAGNE = 'MAGNE', _('Magnesium')
        URE = 'URE', _('Urea')
        CREATININE = 'CREATININE', _('Creatinine')
        AST = 'AST', _('AST')
        ALT = 'ALT', _('ALT')
        GLUCOSEBLOOD = 'GLUCOSEBLOOD', _('Blood Glucose')
        BEDSIDE_GLUCOSE = 'BEDSIDE_GLUCOSE', _('Bedside Glucose')
        BILIRUBIN_TP = 'BILIRUBIN_TP', _('Total Bilirubin')
        BILIRUBIN_TT = 'BILIRUBIN_TT', _('Direct Bilirubin')
        PROTEIN = 'PROTEIN', _('Protein')
        ALBUMIN = 'ALBUMIN', _('Albumin')
        CRP_QUALITATIVE = 'CRP_QUALITATIVE', _('CRP Qualitative')
        CRP_QUANTITATIVE = 'CRP_QUANTITATIVE', _('CRP Quantitative')
        CRP = 'CRP', _('C-Reactive Protein')
        PROCALCITONIN = 'PROCALCITONIN', _('Procalcitonin')
        HBA1C = 'HBA1C', _('HbA1c')
        CORTISOL = 'CORTISOL', _('Cortisol')
        HIV = 'HIV', _('HIV')
        CD4 = 'CD4', _('CD4 Count')
        
        # 14. Arterial Blood Gas
        PH = 'PH', _('pH')
        PCO2 = 'PCO2', _('pCO2')
        PO2 = 'PO2', _('pO2')
        HCO3 = 'HCO3', _('HCO3')
        BE = 'BE', _('Base Excess')
        AADO2 = 'AADO2', _('A-a Gradient')
        
        # 15. Arterial Lactate
        LACTATE_ARTERIAL = 'LACTATE_ARTERIAL', _('Arterial Lactate')
        
        # 16. Urinalysis
        URINE_PH = 'URINE_PH', _('Urine pH')
        NITRIT = 'NITRIT', _('Nitrite')
        URINE_PROTEIN = 'URINE_PROTEIN', _('Urine Protein')
        LEU = 'LEU', _('Leukocytes')
        URINE_RBC = 'URINE_RBC', _('Urine RBC')
        SEDIMENT = 'SEDIMENT', _('Sediment')
        
        # 17. Peritoneal Fluid
        PERITONEAL_WBC = 'PERITONEAL_WBC', _('White Blood Cells')
        PERITONEAL_NEU = 'PERITONEAL_NEU', _('Polymorphonuclear')
        PERITONEAL_MONO = 'PERITONEAL_MONO', _('Mononuclear')
        PERITONEAL_RBC = 'PERITONEAL_RBC', _('Red Blood Cells')
        PERITONEAL_PROTEIN = 'PERITONEAL_PROTEIN', _('Protein')
        PERITONEAL_PROTEIN_BLOOD = 'PERITONEAL_PROTEIN_BLOOD', _('Blood Protein')
        PERITONEAL_ALBUMIN = 'PERITONEAL_ALBUMIN', _('Albumin')
        PERITONEAL_ALBUMIN_BLOOD = 'PERITONEAL_ALBUMIN_BLOOD', _('Blood Albumin')
        PERITONEAL_ADA = 'PERITONEAL_ADA', _('ADA')
        PERITONEAL_CELLBLOCK = 'PERITONEAL_CELLBLOCK', _('Cell Block')
        
        # 18. Pleural Fluid
        PLEURAL_WBC = 'PLEURAL_WBC', _('White Blood Cells')
        PLEURAL_NEU = 'PLEURAL_NEU', _('Polymorphonuclear')
        PLEURAL_MONO = 'PLEURAL_MONO', _('Mononuclear')
        PLEURAL_EOS = 'PLEURAL_EOS', _('Eosinophils')
        PLEURAL_RBC = 'PLEURAL_RBC', _('Red Blood Cells')
        PLEURAL_PROTEIN = 'PLEURAL_PROTEIN', _('Protein')
        PLEURAL_LDH = 'PLEURAL_LDH', _('LDH')
        PLEURAL_LDH_BLOOD = 'PLEURAL_LDH_BLOOD', _('Blood LDH')
        PLEURAL_ADA = 'PLEURAL_ADA', _('ADA')
        PLEURAL_CELLBLOCK = 'PLEURAL_CELLBLOCK', _('Cell Block')
        
        # 19. Cerebrospinal Fluid
        CSF_WBC = 'CSF_WBC', _('White Blood Cells')
        CSF_NEU = 'CSF_NEU', _('Polymorphonuclear')
        CSF_MONO = 'CSF_MONO', _('Mononuclear')
        CSF_EOS = 'CSF_EOS', _('Eosinophils')
        CSF_RBC = 'CSF_RBC', _('Red Blood Cells')
        CSF_PROTEIN = 'CSF_PROTEIN', _('Protein')
        CSF_GLUCOSE = 'CSF_GLUCOSE', _('Glucose')
        CSF_LACTATE = 'CSF_LACTATE', _('Lactate')
        CSF_GRAM_STAIN = 'CSF_GRAM_STAIN', _('Gram Stain')
        
        # 20-25. Imaging Studies
        CHEST_XRAY = 'CHEST_XRAY', _('Chest X-Ray')
        ABDOMINAL_ULTRASOUND = 'ABDOMINAL_ULTRASOUND', _('Abdominal Ultrasound')
        BRAIN_CT_MRI = 'BRAIN_CT_MRI', _('Brain CT/MRI')
        CHEST_ABDOMEN_CT = 'CHEST_ABDOMEN_CT', _('Chest/Abdomen CT')
        ECHOCARDIOGRAPHY = 'ECHOCARDIOGRAPHY', _('Echocardiography')
        SOFT_TISSUE_ULTRASOUND = 'SOFT_TISSUE_ULTRASOUND', _('Soft Tissue Ultrasound')
    
    # Foreign key
    USUBJID = models.ForeignKey('EnrollmentCase',
        to_field='USUBJID',
        db_column='USUBJID',
        on_delete=models.CASCADE,
        verbose_name=_('Patient ID')
    )
    
    LAB_TYPE = models.CharField(
        max_length=1,
        choices=LabTypeChoices.choices,
        db_index=True,
        verbose_name=_('Test Time Point')
    )
    
    CATEGORY = models.CharField(
        max_length=50,
        choices=CategoryChoices.choices,
        db_index=True,
        verbose_name=_('Test Category')
    )
    
    TESTTYPE = models.CharField(
        max_length=50,
        choices=TestTypeChoices.choices,
        db_index=True,
        verbose_name=_('Test Type')
    )
    
    PERFORMED = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_('Test Performed')
    )
    
    PERFORMEDDATE = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Performance Date')
    )
    
    RESULT = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Test Result')
    )
    
    # Metadata
    CREATEDAT = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    
    UPDATEDAT = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )

    class Meta:
        db_table = 'CLI_Laboratory_Test'
        verbose_name = _('Laboratory Test')
        verbose_name_plural = _('Laboratory Tests')
        unique_together = ['USUBJID', 'TESTTYPE', 'LAB_TYPE']
        ordering = ['CATEGORY', 'TESTTYPE', 'LAB_TYPE']
        indexes = [
            models.Index(fields=['USUBJID', 'LAB_TYPE'], name='idx_lab_subj_type'),
            models.Index(fields=['CATEGORY', 'PERFORMED'], name='idx_lab_cat_perf'),
            models.Index(fields=['PERFORMEDDATE'], name='idx_lab_date'),
        ]
    
    def __str__(self):
        return f"{self.USUBJID_id} - {self.get_TESTTYPE_display()} - {self.get_LAB_TYPE_display()}"
    
    def save(self, *args, **kwargs):
        """Auto-assign category based on test type if not set"""
        if not self.CATEGORY:
            self.CATEGORY = self._get_category_from_test_type()
        super().save(*args, **kwargs)
    
    def _get_category_from_test_type(self):
        """Auto-determine category from test type"""
        category_mapping = {
            # Coagulation
            'INR': self.CategoryChoices.BLOOD_COAGULATION,
            'DIC': self.CategoryChoices.BLOOD_COAGULATION,
            
            # Complete Blood Count
            'WBC': self.CategoryChoices.COMPLETE_BLOOD_COUNT,
            'NEU': self.CategoryChoices.COMPLETE_BLOOD_COUNT,
            'LYM': self.CategoryChoices.COMPLETE_BLOOD_COUNT,
            'EOS': self.CategoryChoices.COMPLETE_BLOOD_COUNT,
            'RBC': self.CategoryChoices.COMPLETE_BLOOD_COUNT,
            'HEMOGLOBIN': self.CategoryChoices.COMPLETE_BLOOD_COUNT,
            'PLATELETS': self.CategoryChoices.COMPLETE_BLOOD_COUNT,
            
            # Biochemistry
            'NATRI': self.CategoryChoices.BIOCHEMISTRY,
            'KALI': self.CategoryChoices.BIOCHEMISTRY,
            'CLO': self.CategoryChoices.BIOCHEMISTRY,
            'MAGNE': self.CategoryChoices.BIOCHEMISTRY,
            'URE': self.CategoryChoices.BIOCHEMISTRY,
            'CREATININE': self.CategoryChoices.BIOCHEMISTRY,
            'AST': self.CategoryChoices.BIOCHEMISTRY,
            'ALT': self.CategoryChoices.BIOCHEMISTRY,
            'GLUCOSEBLOOD': self.CategoryChoices.BIOCHEMISTRY,
            'BEDSIDE_GLUCOSE': self.CategoryChoices.BIOCHEMISTRY,
            'BILIRUBIN_TP': self.CategoryChoices.BIOCHEMISTRY,
            'BILIRUBIN_TT': self.CategoryChoices.BIOCHEMISTRY,
            'PROTEIN': self.CategoryChoices.BIOCHEMISTRY,
            'ALBUMIN': self.CategoryChoices.BIOCHEMISTRY,
            'CRP_QUALITATIVE': self.CategoryChoices.BIOCHEMISTRY,
            'CRP_QUANTITATIVE': self.CategoryChoices.BIOCHEMISTRY,
            'CRP': self.CategoryChoices.BIOCHEMISTRY,
            'PROCALCITONIN': self.CategoryChoices.BIOCHEMISTRY,
            'HBA1C': self.CategoryChoices.BIOCHEMISTRY,
            'CORTISOL': self.CategoryChoices.BIOCHEMISTRY,
            'HIV': self.CategoryChoices.BIOCHEMISTRY,
            'CD4': self.CategoryChoices.BIOCHEMISTRY,
            
            # Blood Gas
            'PH': self.CategoryChoices.BLOOD_GAS_ANALYSIS,
            'PCO2': self.CategoryChoices.BLOOD_GAS_ANALYSIS,
            'PO2': self.CategoryChoices.BLOOD_GAS_ANALYSIS,
            'HCO3': self.CategoryChoices.BLOOD_GAS_ANALYSIS,
            'BE': self.CategoryChoices.BLOOD_GAS_ANALYSIS,
            'AADO2': self.CategoryChoices.BLOOD_GAS_ANALYSIS,
            
            # Lactate
            'LACTATE_ARTERIAL': self.CategoryChoices.LACTATE,
            
            # Urine
            'URINE_PH': self.CategoryChoices.URINE_ANALYSIS,
            'NITRIT': self.CategoryChoices.URINE_ANALYSIS,
            'URINE_PROTEIN': self.CategoryChoices.URINE_ANALYSIS,
            'LEU': self.CategoryChoices.URINE_ANALYSIS,
            'URINE_RBC': self.CategoryChoices.URINE_ANALYSIS,
            'SEDIMENT': self.CategoryChoices.URINE_ANALYSIS,
            
            # Imaging
            'CHEST_XRAY': self.CategoryChoices.CHEST_XRAY,
            'ABDOMINAL_ULTRASOUND': self.CategoryChoices.ABDOMINAL_ULTRASOUND,
            'BRAIN_CT_MRI': self.CategoryChoices.BRAIN_CT_MRI,
            'CHEST_ABDOMEN_CT': self.CategoryChoices.CHEST_ABDOMEN_CT,
            'ECHOCARDIOGRAPHY': self.CategoryChoices.ECHOCARDIOGRAPHY,
            'SOFT_TISSUE_ULTRASOUND': self.CategoryChoices.SOFT_TISSUE_ULTRASOUND,
        }
        
        # Handle prefixed tests
        if self.TESTTYPE.startswith('PERITONEAL_'):
            return self.CategoryChoices.PLEURAL_FLUID
        elif self.TESTTYPE.startswith('PLEURAL_'):
            return self.CategoryChoices.PLEURAL_FLUID_ANALYSIS
        elif self.TESTTYPE.startswith('CSF_'):
            return self.CategoryChoices.CSF_ANALYSIS
        else:
            return category_mapping.get(self.TESTTYPE, self.CategoryChoices.BIOCHEMISTRY)
    
    def is_imaging_test(self):
        """Check if test is diagnostic imaging"""
        imaging_categories = [
            self.CategoryChoices.CHEST_XRAY,
            self.CategoryChoices.ABDOMINAL_ULTRASOUND,
            self.CategoryChoices.BRAIN_CT_MRI,
            self.CategoryChoices.CHEST_ABDOMEN_CT,
            self.CategoryChoices.ECHOCARDIOGRAPHY,
            self.CategoryChoices.SOFT_TISSUE_ULTRASOUND,
        ]
        return self.CATEGORY in imaging_categories


class OtherTest(models.Model):
    """
    Other laboratory tests not covered in main test categories
    Allows custom test tracking with flexible naming
    """
    
    # Choices definitions using TextChoices
    class LabTypeChoices(models.TextChoices):
        TEST1 = '1', _('Test 1 (First 24h)')
        TEST2 = '2', _('Test 2 (48-72h after initial antibiotics)')
        TEST3 = '3', _('Test 3 (Within 72h before discharge)')
    
    class CategoryChoices(models.TextChoices):
        OTHER = 'OTHER', _('Other Tests')
    
    # Managers
    objects = models.Manager()
    site_objects = SiteFilteredManage()
    
    # Foreign key
    USUBJID = models.ForeignKey('LaboratoryTest',
        db_column='USUBJID',
        on_delete=models.CASCADE,
        verbose_name=_('Patient ID')
    )
    
    SEQUENCE = models.IntegerField(
        default=1,
        db_index=True,
        verbose_name=_('Sequence Number')
    )
    
    LAB_TYPE = models.CharField(
        max_length=1,
        choices=LabTypeChoices.choices,
        default=LabTypeChoices.TEST1,
        db_index=True,
        verbose_name=_('Test Time Point')
    )
    
    CATEGORY = models.CharField(
        max_length=50,
        choices=CategoryChoices.choices,
        default=CategoryChoices.OTHER,
        verbose_name=_('Test Category')
    )
    
    OTHERTESTNAME = models.CharField(
        max_length=255,
        verbose_name=_('Other Test Name')
    )
    
    OTHERTESTPERFORMED = models.BooleanField(
        default=False,
        verbose_name=_('Test Performed')
    )
    
    OTHERTESTDTC = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Test Date')
    )
    
    OTHERTESTRESULT = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Test Result')
    )
    
    # Metadata
    entry = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Entry Number')
    )
    
    enteredtime = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Entry Time')
    )

    class Meta:
        db_table = 'CLI_Other_Test'
        verbose_name = _('Other Test')
        verbose_name_plural = _('Other Tests')
        unique_together = ['USUBJID', 'SEQUENCE']
        ordering = ['USUBJID', 'SEQUENCE']
        indexes = [
            models.Index(fields=['USUBJID', 'LAB_TYPE'], name='idx_ot_subj_type'),
            models.Index(fields=['OTHERTESTDTC'], name='idx_ot_date'),
        ]

    def save(self, *args, **kwargs):
        """Auto-generate SEQUENCE if not provided"""
        if not self.SEQUENCE:
            last_seq = (
                OtherTest.objects
                .filter(USUBJID=self.USUBJID)
                .aggregate(models.Max('SEQUENCE'))['SEQUENCE__max']
            )
            self.SEQUENCE = (last_seq or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.USUBJID_id} - {self.OTHERTESTNAME} - #{self.SEQUENCE}"