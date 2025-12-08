from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.functional import cached_property
from backends.studies.study_43en.study_site_manage import SiteFilteredManager
from backends.studies.study_43en.models.base_models import AuditFieldsMixin
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)


class LaboratoryTest(AuditFieldsMixin):
    """
    Laboratory test and imaging results
    Tracks various lab tests and diagnostic imaging across 3 time points
    
     ENHANCED: Now tracks data entry state to distinguish first entry vs updates
    """
    
    # ==========================================
    # CHOICES DEFINITIONS
    # ==========================================
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
        NATRI = 'NATRI', _('Blood Sodium')
        KALI = 'KALI', _('Blood Potassium')
        CLO = 'CLO', _('Blood Chloride')
        MAGNE = 'MAGNE', _('Blood Magnesium')
        URE = 'URE', _('Blood Urea')
        CREATININE = 'CREATININE', _('Blood Creatinine')
        AST = 'AST', _('AST')
        ALT = 'ALT', _('ALT')
        GLUCOSEBLOOD = 'GLUCOSEBLOOD', _('Blood Glucose')
        BILIRUBIN_TP = 'BILIRUBIN_TP', _('Bilirubin')
        BILIRUBIN_TT = 'BILIRUBIN_TT', _('Bilirubin D')
        PROTEIN = 'PROTEIN', _('Blood Protein')
        ALBUMIN = 'ALBUMIN', _('Blood Albumin')
        CRP_QUALITATIVE = 'CRP_QUALITATIVE', _('Blood ketone qualitative')
        CRP_QUANTITATIVE = 'CRP_QUANTITATIVE', _('Blood ketone quantitative')
        CRP = 'CRP', _('C-Reactive Protein')
        PROCALCITONIN = 'PROCALCITONIN', _('Procalcitonin')
        HBA1C = 'HBA1C', _('HbA1c')
        CORTISOL = 'CORTISOL', _('Cortisol')
        HIV = 'HIV', _('HIV')
        CD4 = 'CD4', _('CD4 Count')
        
        # 14. Arterial Blood Gas
        PH_BLOOD = 'PH_BLOOD', _('pH (Arterial Blood Gas)')
        PCO2 = 'PCO2', _('pCO2')
        PO2 = 'PO2', _('pO2')
        HCO3 = 'HCO3', _('HCO3')
        BE = 'BE', _('Base Excess')
        AADO2 = 'AADO2', _('A-a Gradient')
        
        # 15. Arterial Lactate
        LACTATE_ARTERIAL = 'LACTATE_ARTERIAL', _('Arterial Lactate')
        
        # 16. Urinalysis (Complete Urine Analysis)
        PH = 'PH', _('pH')
        NITRIT = 'NITRIT', _('Nitrite')
        URINE_PROTEIN = 'URINE_PROTEIN', _('Protein')
        LEU = 'LEU', _('Leukocytes')
        URINE_RBC = 'URINE_RBC', _('Red Blood Cells')
        SEDIMENT = 'SEDIMENT', _('Sediment')
        
        # 17. Peritoneal Fluid
        PERITONEAL_WBC = 'PERITONEAL_WBC', _('White blood cell')
        PERITONEAL_NEU = 'PERITONEAL_NEU', _('Polymorphonuclear leukocyte')
        PERITONEAL_MONO = 'PERITONEAL_MONO', _('Monocytes')
        PERITONEAL_RBC = 'PERITONEAL_RBC', _('Red blood cell')
        PERITONEAL_PROTEIN = 'PERITONEAL_PROTEIN', _('Protein')
        PERITONEAL_PROTEIN_BLOOD = 'PERITONEAL_PROTEIN_BLOOD', _('Blood Protein')
        PERITONEAL_ALBUMIN = 'PERITONEAL_ALBUMIN', _('Albumin')
        PERITONEAL_ALBUMIN_BLOOD = 'PERITONEAL_ALBUMIN_BLOOD', _('Blood Albumin')
        PERITONEAL_ADA = 'PERITONEAL_ADA', _('ADA')
        PERITONEAL_CELLBLOCK = 'PERITONEAL_CELLBLOCK', _('Cell block')
        
        # 18. Pleural Fluid
        PLEURAL_WBC = 'PLEURAL_WBC', _('White blood cell')
        PLEURAL_NEU = 'PLEURAL_NEU', _('Polymorphonuclear leukocyte')
        PLEURAL_MONO = 'PLEURAL_MONO', _('Monocytes')
        PLEURAL_EOS = 'PLEURAL_EOS', _('Eosinophils')
        PLEURAL_RBC = 'PLEURAL_RBC', _('Red blood cell')
        PLEURAL_PROTEIN = 'PLEURAL_PROTEIN', _('Protein')
        PLEURAL_PROTEIN_BLOOD = 'PLEURAL_PROTEIN_BLOOD', _('Blood Protein')
        PLEURAL_ALBUMIN = 'PLEURAL_ALBUMIN', _('Albumin')
        PLEURAL_ALBUMIN_BLOOD = 'PLEURAL_ALBUMIN_BLOOD', _('Blood Albumin')
        PLEURAL_LDH = 'PLEURAL_LDH', _('LDH')
        PLEURAL_LDH_BLOOD = 'PLEURAL_LDH_BLOOD', _('Blood LDH')
        PLEURAL_ADA = 'PLEURAL_ADA', _('ADA')
        PLEURAL_CELLBLOCK = 'PLEURAL_CELLBLOCK', _('Cell block')
        
        # 19. Cerebrospinal Fluid
        CSF_WBC = 'CSF_WBC', _('White blood cell')
        CSF_NEU = 'CSF_NEU', _('Polymorphonuclear leukocyte')
        CSF_MONO = 'CSF_MONO', _('Monocytes')
        CSF_EOS = 'CSF_EOS', _('Eos')
        CSF_RBC = 'CSF_RBC', _('Red blood cell')
        CSF_PROTEIN = 'CSF_PROTEIN', _('Protein')
        CSF_GLUCOSE = 'CSF_GLUCOSE', _('Glucose')
        CSF_LACTATE = 'CSF_LACTATE', _('Lactate')
        CSF_GRAM_STAIN = 'CSF_GRAM_STAIN', _('Gram stain')
        
        # 20-25. Imaging Studies
        CHEST_XRAY = 'CHEST_XRAY', _('Chest X-ray')
        ABDOMINAL_ULTRASOUND = 'ABDOMINAL_ULTRASOUND', _('Abdominal Ultrasound')
        BRAIN_CT_MRI = 'BRAIN_CT_MRI', _('Head CT scan/Brain MRI')
        CHEST_ABDOMEN_CT = 'CHEST_ABDOMEN_CT', _('Chest/Abdomen CT')
        ECHOCARDIOGRAPHY = 'ECHOCARDIOGRAPHY', _('Echocardiogram')
        SOFT_TISSUE_ULTRASOUND = 'SOFT_TISSUE_ULTRASOUND', _('Soft tissue ultrasound')
    
    # ==========================================
    # CATEGORY MAPPING - COMPLETE
    # ==========================================
    CATEGORY_MAPPING = {
        # Coagulation
        'INR': CategoryChoices.BLOOD_COAGULATION,
        'DIC': CategoryChoices.BLOOD_COAGULATION,
        
        # Complete Blood Count
        'WBC': CategoryChoices.COMPLETE_BLOOD_COUNT,
        'NEU': CategoryChoices.COMPLETE_BLOOD_COUNT,
        'LYM': CategoryChoices.COMPLETE_BLOOD_COUNT,
        'EOS': CategoryChoices.COMPLETE_BLOOD_COUNT,
        'RBC': CategoryChoices.COMPLETE_BLOOD_COUNT,
        'HEMOGLOBIN': CategoryChoices.COMPLETE_BLOOD_COUNT,
        'PLATELETS': CategoryChoices.COMPLETE_BLOOD_COUNT,
        
        # Biochemistry
        'NATRI': CategoryChoices.BIOCHEMISTRY,
        'KALI': CategoryChoices.BIOCHEMISTRY,
        'CLO': CategoryChoices.BIOCHEMISTRY,
        'MAGNE': CategoryChoices.BIOCHEMISTRY,
        'URE': CategoryChoices.BIOCHEMISTRY,
        'CREATININE': CategoryChoices.BIOCHEMISTRY,
        'AST': CategoryChoices.BIOCHEMISTRY,
        'ALT': CategoryChoices.BIOCHEMISTRY,
        'GLUCOSEBLOOD': CategoryChoices.BIOCHEMISTRY,
        'BILIRUBIN_TP': CategoryChoices.BIOCHEMISTRY,
        'BILIRUBIN_TT': CategoryChoices.BIOCHEMISTRY,
        'PROTEIN': CategoryChoices.BIOCHEMISTRY,
        'ALBUMIN': CategoryChoices.BIOCHEMISTRY,
        'CRP_QUALITATIVE': CategoryChoices.BIOCHEMISTRY,
        'CRP_QUANTITATIVE': CategoryChoices.BIOCHEMISTRY,
        'CRP': CategoryChoices.BIOCHEMISTRY,
        'PROCALCITONIN': CategoryChoices.BIOCHEMISTRY,
        'HBA1C': CategoryChoices.BIOCHEMISTRY,
        'CORTISOL': CategoryChoices.BIOCHEMISTRY,
        'HIV': CategoryChoices.BIOCHEMISTRY,
        'CD4': CategoryChoices.BIOCHEMISTRY,
        
        # Blood Gas
        'PH_BLOOD': CategoryChoices.BLOOD_GAS_ANALYSIS,
        'PCO2': CategoryChoices.BLOOD_GAS_ANALYSIS,
        'PO2': CategoryChoices.BLOOD_GAS_ANALYSIS,
        'HCO3': CategoryChoices.BLOOD_GAS_ANALYSIS,
        'BE': CategoryChoices.BLOOD_GAS_ANALYSIS,
        'AADO2': CategoryChoices.BLOOD_GAS_ANALYSIS,
        
        # Lactate
        'LACTATE_ARTERIAL': CategoryChoices.LACTATE,
        
        # Urine
        'PH': CategoryChoices.URINE_ANALYSIS,
        'NITRIT': CategoryChoices.URINE_ANALYSIS,
        'URINE_PROTEIN': CategoryChoices.URINE_ANALYSIS,
        'LEU': CategoryChoices.URINE_ANALYSIS,
        'URINE_RBC': CategoryChoices.URINE_ANALYSIS,
        'SEDIMENT': CategoryChoices.URINE_ANALYSIS,
        
        # Peritoneal Fluid (10 tests)
        'PERITONEAL_WBC': CategoryChoices.PLEURAL_FLUID,
        'PERITONEAL_NEU': CategoryChoices.PLEURAL_FLUID,
        'PERITONEAL_MONO': CategoryChoices.PLEURAL_FLUID,
        'PERITONEAL_RBC': CategoryChoices.PLEURAL_FLUID,
        'PERITONEAL_PROTEIN': CategoryChoices.PLEURAL_FLUID,
        'PERITONEAL_PROTEIN_BLOOD': CategoryChoices.PLEURAL_FLUID,
        'PERITONEAL_ALBUMIN': CategoryChoices.PLEURAL_FLUID,
        'PERITONEAL_ALBUMIN_BLOOD': CategoryChoices.PLEURAL_FLUID,
        'PERITONEAL_ADA': CategoryChoices.PLEURAL_FLUID,
        'PERITONEAL_CELLBLOCK': CategoryChoices.PLEURAL_FLUID,
        
        # Pleural Fluid (13 tests)
        'PLEURAL_WBC': CategoryChoices.PLEURAL_FLUID_ANALYSIS,
        'PLEURAL_NEU': CategoryChoices.PLEURAL_FLUID_ANALYSIS,
        'PLEURAL_MONO': CategoryChoices.PLEURAL_FLUID_ANALYSIS,
        'PLEURAL_EOS': CategoryChoices.PLEURAL_FLUID_ANALYSIS,
        'PLEURAL_RBC': CategoryChoices.PLEURAL_FLUID_ANALYSIS,
        'PLEURAL_PROTEIN': CategoryChoices.PLEURAL_FLUID_ANALYSIS,
        'PLEURAL_PROTEIN_BLOOD': CategoryChoices.PLEURAL_FLUID_ANALYSIS,
        'PLEURAL_ALBUMIN': CategoryChoices.PLEURAL_FLUID_ANALYSIS,
        'PLEURAL_ALBUMIN_BLOOD': CategoryChoices.PLEURAL_FLUID_ANALYSIS,
        'PLEURAL_LDH': CategoryChoices.PLEURAL_FLUID_ANALYSIS,
        'PLEURAL_LDH_BLOOD': CategoryChoices.PLEURAL_FLUID_ANALYSIS,
        'PLEURAL_ADA': CategoryChoices.PLEURAL_FLUID_ANALYSIS,
        'PLEURAL_CELLBLOCK': CategoryChoices.PLEURAL_FLUID_ANALYSIS,
        
        # CSF (9 tests)
        'CSF_WBC': CategoryChoices.CSF_ANALYSIS,
        'CSF_NEU': CategoryChoices.CSF_ANALYSIS,
        'CSF_MONO': CategoryChoices.CSF_ANALYSIS,
        'CSF_EOS': CategoryChoices.CSF_ANALYSIS,
        'CSF_RBC': CategoryChoices.CSF_ANALYSIS,
        'CSF_PROTEIN': CategoryChoices.CSF_ANALYSIS,
        'CSF_GLUCOSE': CategoryChoices.CSF_ANALYSIS,
        'CSF_LACTATE': CategoryChoices.CSF_ANALYSIS,
        'CSF_GRAM_STAIN': CategoryChoices.CSF_ANALYSIS,
        
        # Imaging
        'CHEST_XRAY': CategoryChoices.CHEST_XRAY,
        'ABDOMINAL_ULTRASOUND': CategoryChoices.ABDOMINAL_ULTRASOUND,
        'BRAIN_CT_MRI': CategoryChoices.BRAIN_CT_MRI,
        'CHEST_ABDOMEN_CT': CategoryChoices.CHEST_ABDOMEN_CT,
        'ECHOCARDIOGRAPHY': CategoryChoices.ECHOCARDIOGRAPHY,
        'SOFT_TISSUE_ULTRASOUND': CategoryChoices.SOFT_TISSUE_ULTRASOUND,
    }
    
    # ==========================================
    # MANAGERS
    # ==========================================
        
    
    # ==========================================
    # FIELDS
    # ==========================================
    USUBJID = models.ForeignKey(
        'ENR_CASE',
        db_column='USUBJID',
        on_delete=models.CASCADE,
        related_name='laboratory_tests',
        verbose_name=_('Patient ID')
    )
    
    LAB_TYPE = models.CharField(
        max_length=1,
        choices=LabTypeChoices.choices,
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
        verbose_name=_('Performance Date')
    )
    
    RESULT = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Test Result')
    )
    
    #  NEW FIELD - Track data entry state
    data_entered = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_('Data Entered'),
        help_text=_('True if test data has been entered at least once')
    )

    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'PARACLI_CASE'
        verbose_name = _('Laboratory Test')
        verbose_name_plural = _('Laboratory Tests')
        unique_together = ['USUBJID', 'TESTTYPE', 'LAB_TYPE']
        ordering = ['CATEGORY', 'TESTTYPE', 'LAB_TYPE']
        indexes = [
            models.Index(fields=['USUBJID', 'LAB_TYPE'], name='idx_lab_subj_type'),
            models.Index(fields=['CATEGORY', 'PERFORMED'], name='idx_lab_cat_perf'),
            models.Index(fields=['PERFORMEDDATE'], name='idx_lab_date'),
            models.Index(fields=['PERFORMED', 'LAB_TYPE', 'USUBJID'], name='idx_lab_perf_query'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_lab_modified'),
            models.Index(fields=['USUBJID', 'CATEGORY', 'LAB_TYPE'], name='idx_lab_subj_cat'),
            models.Index(fields=['CATEGORY', 'PERFORMEDDATE'], name='idx_lab_cat_date'),
            #  NEW INDEXES for data_entered queries
            models.Index(fields=['USUBJID', 'data_entered', 'LAB_TYPE'], name='idx_lab_data_entered'),
            models.Index(fields=['data_entered', 'PERFORMED'], name='idx_lab_entry_status'),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    ~models.Q(PERFORMED=True) |
                    models.Q(PERFORMEDDATE__isnull=False)
                ),
                name='lab_performed_date_required'
            ),
            models.CheckConstraint(
                check=(
                    ~models.Q(PERFORMED=True) |
                    models.Q(RESULT__isnull=False)
                ),
                name='lab_performed_result_required'
            ),
        ]
    
    # ==========================================
    # STRING REPRESENTATION
    # ==========================================
    def __str__(self):
        return f"{self.USUBJID_id} - {self.get_TESTTYPE_display()} - {self.get_LAB_TYPE_display()}"
    
    # ==========================================
    # CACHED PROPERTIES
    # ==========================================
    @cached_property
    def SITEID(self):
        """Get SITEID from related ENR_CASE (cached)"""
        return self.USUBJID.SITEID if self.USUBJID else None
    
    @cached_property
    def is_imaging_test(self):
        """Check if test is diagnostic imaging"""
        imaging_categories = {
            self.CategoryChoices.CHEST_XRAY,
            self.CategoryChoices.ABDOMINAL_ULTRASOUND,
            self.CategoryChoices.BRAIN_CT_MRI,
            self.CategoryChoices.CHEST_ABDOMEN_CT,
            self.CategoryChoices.ECHOCARDIOGRAPHY,
            self.CategoryChoices.SOFT_TISSUE_ULTRASOUND,
        }
        return self.CATEGORY in imaging_categories
    
    @cached_property
    def is_lab_test(self):
        """Check if test is laboratory (non-imaging)"""
        return not self.is_imaging_test
    
    @cached_property
    def is_completed(self):
        """Check if test is fully completed"""
        return self.PERFORMED and self.RESULT
    
    @cached_property
    def days_since_performed(self):
        """Calculate days since test was performed"""
        if self.PERFORMEDDATE:
            return (date.today() - self.PERFORMEDDATE).days
        return None
    
    #  NEW CACHED PROPERTIES
    @cached_property
    def is_first_entry(self):
        """
        Check if this is the first time data is being entered
        
        Returns True if:
        - data_entered is False (never entered before)
        - OR performed but no result yet (partial entry)
        """
        return not self.data_entered or (self.PERFORMED and not self.RESULT)
    
    @cached_property
    def entry_status(self):
        """
        Get human-readable entry status
        
        Returns:
            - 'empty': Not performed, no data
            - 'first_entry': Performed but data_entered=False
            - 'partial': Performed but missing result
            - 'complete': Has data and result
        """
        if not self.PERFORMED:
            return 'empty'
        
        if not self.data_entered:
            return 'first_entry'
        
        if not self.RESULT or not self.RESULT.strip():
            return 'partial'
        
        return 'complete'
    
    # ==========================================
    # PROPERTY HELPERS
    # ==========================================
    @property
    def is_test1(self):
        """First 24h test"""
        return self.LAB_TYPE == self.LabTypeChoices.TEST1
    
    @property
    def is_test2(self):
        """48-72h after antibiotics"""
        return self.LAB_TYPE == self.LabTypeChoices.TEST2
    
    @property
    def is_test3(self):
        """Within 72h before discharge"""
        return self.LAB_TYPE == self.LabTypeChoices.TEST3
    
    @property
    def category_display_short(self):
        """Get category display without number prefix"""
        return self.get_CATEGORY_display().split('. ', 1)[-1]
    
    @property
    def completed_by(self):
        """Alias for last_modified_by for backward compatibility"""
        return self.last_modified_by_username
    
    @property
    def completed_date(self):
        """Alias for last_modified_at for backward compatibility"""
        return self.last_modified_at.date() if self.last_modified_at else None
    
    # ==========================================
    # VALIDATION
    # ==========================================
    def clean(self):
        """Enhanced validation"""
        errors = {}
        
        # Validate performed test requirements
        if self.PERFORMED:
            if not self.PERFORMEDDATE:
                errors['PERFORMEDDATE'] = _('Performance date is required when test is performed')
            
            if not self.RESULT or not self.RESULT.strip():
                errors['RESULT'] = _('Result is required when test is performed')
        
        # Validate dates
        if self.PERFORMEDDATE:
            # Check against admission date if available
            if hasattr(self.USUBJID, 'clinical_case') and self.USUBJID.clinical_case.ADMISDATE:
                admission = self.USUBJID.clinical_case.ADMISDATE
                if self.PERFORMEDDATE < admission:
                    errors['PERFORMEDDATE'] = _(
                        f'Performance date cannot be before admission date ({admission})'
                    )
        
        # Auto-fix category if mismatch
        expected_category = self._get_category_from_test_type()
        if self.CATEGORY != expected_category:
            self.CATEGORY = expected_category
        
        if errors:
            raise ValidationError(errors)
    
    # ==========================================
    # SAVE OVERRIDE
    # ==========================================
    def save(self, *args, **kwargs):
        """
         ENHANCED: Auto-set data_entered flag when test gets real data
        """
        # Clear cached properties
        self._clear_cache()
        
        # Auto-assign category
        if not self.CATEGORY:
            self.CATEGORY = self._get_category_from_test_type()
        
        # Strip whitespace from text fields
        if self.RESULT:
            self.RESULT = self.RESULT.strip()
        
        #  AUTO-SET data_entered FLAG
        if self.PERFORMED and self.RESULT and self.RESULT.strip():
            # Has real data → mark as entered
            if not self.data_entered:
                self.data_entered = True
                logger.info(f" Setting data_entered=True for {self.TESTTYPE} (first time)")
        
        super().save(*args, **kwargs)
    
    def _clear_cache(self):
        """Clear all cached properties"""
        cache_attrs = [
            '_SITEID', '_is_imaging_test', '_is_lab_test',
            '_is_completed', '_days_since_performed',
            '_is_first_entry', '_entry_status'  #  Add new cached properties
        ]
        for attr in cache_attrs:
            if hasattr(self, attr):
                delattr(self, attr)
    
    # ==========================================
    # CATEGORY AUTO-DETECTION - Optimized
    # ==========================================
    def _get_category_from_test_type(self):
        """Auto-determine category from test type"""
        # Handle prefixed tests first (faster)
        if self.TESTTYPE.startswith('PERITONEAL_'):
            return self.CategoryChoices.PLEURAL_FLUID
        elif self.TESTTYPE.startswith('PLEURAL_'):
            return self.CategoryChoices.PLEURAL_FLUID_ANALYSIS
        elif self.TESTTYPE.startswith('CSF_'):
            return self.CategoryChoices.CSF_ANALYSIS
        
        # Use mapping dictionary (O(1) lookup)
        return self.CATEGORY_MAPPING.get(
            self.TESTTYPE, 
            self.CategoryChoices.BIOCHEMISTRY  # Default
        )
    
    # ==========================================
    # QUERY HELPERS
    # ==========================================
    @classmethod
    def get_by_patient_and_timepoint(cls, usubjid, lab_type):
        """Get all tests for a patient at specific timepoint"""
        return cls.objects.filter(
            USUBJID=usubjid,
            LAB_TYPE=lab_type
        ).select_related('USUBJID').order_by('CATEGORY', 'TESTTYPE')
    
    @classmethod
    def get_performed_tests(cls, usubjid=None, lab_type=None, category=None):
        """Get performed tests with optional filters"""
        qs = cls.objects.filter(PERFORMED=True)
        
        if usubjid:
            qs = qs.filter(USUBJID=usubjid)
        if lab_type:
            qs = qs.filter(LAB_TYPE=lab_type)
        if category:
            qs = qs.filter(CATEGORY=category)
        
        return qs.select_related('USUBJID').order_by('-PERFORMEDDATE')
    
    @classmethod
    def get_imaging_tests(cls, usubjid=None):
        """Get all imaging tests"""
        imaging_categories = [
            cls.CategoryChoices.CHEST_XRAY,
            cls.CategoryChoices.ABDOMINAL_ULTRASOUND,
            cls.CategoryChoices.BRAIN_CT_MRI,
            cls.CategoryChoices.CHEST_ABDOMEN_CT,
            cls.CategoryChoices.ECHOCARDIOGRAPHY,
            cls.CategoryChoices.SOFT_TISSUE_ULTRASOUND,
        ]
        
        qs = cls.objects.filter(CATEGORY__in=imaging_categories)
        
        if usubjid:
            qs = qs.filter(USUBJID=usubjid)
        
        return qs.select_related('USUBJID').order_by('CATEGORY', 'LAB_TYPE')
    
    @classmethod
    def get_incomplete_tests(cls, usubjid=None):
        """Get tests marked as performed but missing data"""
        qs = cls.objects.filter(
            PERFORMED=True
        ).filter(
            models.Q(RESULT__isnull=True) |
            models.Q(RESULT__exact='')
        )
        
        if usubjid:
            qs = qs.filter(USUBJID=usubjid)
        
        return qs.select_related('USUBJID').order_by('-PERFORMEDDATE')
    
    @classmethod
    def get_tests_by_category(cls, category, usubjid=None, performed_only=True):
        """Get tests by category"""
        qs = cls.objects.filter(CATEGORY=category)
        
        if usubjid:
            qs = qs.filter(USUBJID=usubjid)
        if performed_only:
            qs = qs.filter(PERFORMED=True)
        
        return qs.select_related('USUBJID').order_by('LAB_TYPE', 'TESTTYPE')
    
    #  NEW QUERY HELPERS for data_entered
    @classmethod
    def get_empty_tests(cls, usubjid=None, lab_type=None):
        """
        Get tests that have never had data entered
        
        Returns tests where data_entered=False
        """
        qs = cls.objects.filter(data_entered=False)
        
        if usubjid:
            qs = qs.filter(USUBJID=usubjid)
        if lab_type:
            qs = qs.filter(LAB_TYPE=lab_type)
        
        return qs.select_related('USUBJID').order_by('CATEGORY', 'TESTTYPE')
    
    @classmethod
    def get_first_entry_candidates(cls, usubjid, lab_type):
        """
        Get tests that are candidates for first data entry
        
        These tests either:
        - Never had data (data_entered=False), OR
        - Marked as performed but missing result (incomplete)
        """
        return cls.objects.filter(
            USUBJID=usubjid,
            LAB_TYPE=lab_type
        ).filter(
            models.Q(data_entered=False) |
            models.Q(PERFORMED=True, RESULT__isnull=True) |
            models.Q(PERFORMED=True, RESULT='')
        ).select_related('USUBJID').order_by('CATEGORY', 'TESTTYPE')
    
    @classmethod
    def get_data_entry_stats(cls, usubjid=None, lab_type=None):
        """
         Get statistics about data entry progress
        
        Returns dict with:
        - total: Total tests
        - empty: Never entered data
        - first_entry: Currently being entered for first time
        - complete: Has data entered
        """
        qs = cls.objects.all()
        
        if usubjid:
            qs = qs.filter(USUBJID=usubjid)
        if lab_type:
            qs = qs.filter(LAB_TYPE=lab_type)
        
        total = qs.count()
        empty = qs.filter(data_entered=False, PERFORMED=False).count()
        first_entry = qs.filter(data_entered=False, PERFORMED=True).count()
        complete = qs.filter(data_entered=True).count()
        
        return {
            'total': total,
            'empty': empty,
            'first_entry': first_entry,
            'complete': complete,
            'completion_rate': round(complete / total * 100, 1) if total > 0 else 0
        }


class OtherTest(AuditFieldsMixin):
    """
    Other laboratory tests not covered in main test categories
    Allows custom test tracking with flexible naming
    
    Optimizations:
    - Added AuditFieldsMixin for version control and audit trail
    - Fixed foreign key to point to ENR_CASE
    - Enhanced validation with clean() method
    - Added cached properties
    - Optimized indexes
    - Added query helper methods
    """
    
    # ==========================================
    # CHOICES DEFINITIONS
    # ==========================================
    class LabTypeChoices(models.TextChoices):
        TEST1 = '1', _('Test 1 (First 24h)')
        TEST2 = '2', _('Test 2 (48-72h after initial antibiotics)')
        TEST3 = '3', _('Test 3 (Within 72h before discharge)')
    
    class CategoryChoices(models.TextChoices):
        OTHER = 'OTHER', _('Other Tests')
    
    # ==========================================
    # MANAGERS
    # ==========================================
        
    
    # ==========================================
    # FIELDS
    # ==========================================
    USUBJID = models.ForeignKey(
        'ENR_CASE',
        db_column='USUBJID',
        on_delete=models.CASCADE,
        related_name='other_tests',
        verbose_name=_('Patient ID')
    )
    
    SEQUENCE = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name=_('Sequence Number')
    )
    
    LAB_TYPE = models.CharField(
        max_length=1,
        choices=LabTypeChoices.choices,
        default=LabTypeChoices.TEST1,
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
        db_index=True,
        verbose_name=_('Test Performed')
    )
    
    OTHERTESTDTC = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Test Date')
    )
    
    OTHERTESTRESULT = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Test Result')
    )

    # ==========================================
    # META OPTIONS
    # ==========================================
    class Meta:
        db_table = 'CLI_Other_Test'
        verbose_name = _('Other Test')
        verbose_name_plural = _('Other Tests')
        unique_together = ['USUBJID', 'SEQUENCE']
        ordering = ['USUBJID', 'SEQUENCE']
        indexes = [
            models.Index(fields=['USUBJID', 'LAB_TYPE'], name='idx_ot_subj_type'),
            models.Index(fields=['OTHERTESTDTC'], name='idx_ot_date'),
            models.Index(fields=['OTHERTESTPERFORMED', 'LAB_TYPE'], name='idx_ot_perf_type'),
            models.Index(fields=['last_modified_by_id', '-last_modified_at'], name='idx_ot_modified'),
            # Composite indexes
            models.Index(fields=['USUBJID', 'OTHERTESTPERFORMED'], name='idx_ot_subj_perf'),
            models.Index(fields=['LAB_TYPE', 'OTHERTESTDTC'], name='idx_ot_type_date'),
        ]
        constraints = [
            # If performed, date must be provided
            models.CheckConstraint(
                check=(
                    ~models.Q(OTHERTESTPERFORMED=True) |
                    models.Q(OTHERTESTDTC__isnull=False)
                ),
                name='ot_performed_date_required'
            ),
            # If performed, result should be provided
            models.CheckConstraint(
                check=(
                    ~models.Q(OTHERTESTPERFORMED=True) |
                    models.Q(OTHERTESTRESULT__isnull=False)
                ),
                name='ot_performed_result_required'
            ),
            # Sequence must be positive
            models.CheckConstraint(
                check=models.Q(SEQUENCE__gte=1),
                name='ot_sequence_positive'
            ),
        ]
    
    # ==========================================
    # STRING REPRESENTATION
    # ==========================================
    def __str__(self):
        return f"{self.USUBJID_id} - {self.OTHERTESTNAME} - #{self.SEQUENCE}"
    
    # ==========================================
    # CACHED PROPERTIES
    # ==========================================
    @cached_property
    def SITEID(self):
        """Get SITEID from related ENR_CASE (cached)"""
        return self.USUBJID.SITEID if self.USUBJID else None
    
    @cached_property
    def is_completed(self):
        """Check if test is fully completed"""
        return self.OTHERTESTPERFORMED and self.OTHERTESTRESULT
    
    @cached_property
    def days_since_performed(self):
        """Calculate days since test was performed"""
        if self.OTHERTESTDTC:
            return (date.today() - self.OTHERTESTDTC).days
        return None
    
    # ==========================================
    # PROPERTY HELPERS
    # ==========================================
    @property
    def is_test1(self):
        """First 24h test"""
        return self.LAB_TYPE == self.LabTypeChoices.TEST1
    
    @property
    def is_test2(self):
        """48-72h after antibiotics"""
        return self.LAB_TYPE == self.LabTypeChoices.TEST2
    
    @property
    def is_test3(self):
        """Within 72h before discharge"""
        return self.LAB_TYPE == self.LabTypeChoices.TEST3
    
    @property
    def completed_by(self):
        """Alias for last_modified_by for backward compatibility"""
        return self.last_modified_by_username
    
    @property
    def completed_date(self):
        """Alias for last_modified_at for backward compatibility"""
        return self.last_modified_at.date() if self.last_modified_at else None
    
    # ==========================================
    # VALIDATION
    # ==========================================
    def clean(self):
        """Enhanced validation"""
        errors = {}
        
        # Validate test name
        if not self.OTHERTESTNAME or not self.OTHERTESTNAME.strip():
            errors['OTHERTESTNAME'] = _('Test name is required')
        
        # Validate performed test requirements
        if self.OTHERTESTPERFORMED:
            if not self.OTHERTESTDTC:
                errors['OTHERTESTDTC'] = _('Test date is required when test is performed')
            
            if not self.OTHERTESTRESULT or not self.OTHERTESTRESULT.strip():
                errors['OTHERTESTRESULT'] = _('Result is required when test is performed')
        
        # Validate dates
        if self.OTHERTESTDTC:
            # Check against admission date if available
            if hasattr(self.USUBJID, 'clinical_case') and self.USUBJID.clinical_case.ADMISDATE:
                admission = self.USUBJID.clinical_case.ADMISDATE
                if self.OTHERTESTDTC < admission:
                    errors['OTHERTESTDTC'] = _(
                        f'Test date cannot be before admission date ({admission})'
                    )
        
        # Validate sequence
        if self.SEQUENCE < 1:
            errors['SEQUENCE'] = _('Sequence number must be positive')
        
        if errors:
            raise ValidationError(errors)
    
    # ==========================================
    # SAVE OVERRIDE
    # ==========================================
    def save(self, *args, **kwargs):
        """
        Auto-generate SEQUENCE if not provided
        Clear cached properties
        """
        # Clear cached properties
        self._clear_cache()
        
        # Auto-generate sequence number
        if not self.SEQUENCE or self.SEQUENCE == 1:
            last_seq = (
                OtherTest.objects
                .filter(USUBJID=self.USUBJID)
                .aggregate(models.Max('SEQUENCE'))['SEQUENCE__max']
            )
            self.SEQUENCE = (last_seq or 0) + 1
        
        # Strip whitespace from text fields
        if self.OTHERTESTNAME:
            self.OTHERTESTNAME = self.OTHERTESTNAME.strip()
        if self.OTHERTESTRESULT:
            self.OTHERTESTRESULT = self.OTHERTESTRESULT.strip()
        
        # Ensure category is always OTHER
        self.CATEGORY = self.CategoryChoices.OTHER
        
        super().save(*args, **kwargs)
    
    def _clear_cache(self):
        """Clear all cached properties"""
        cache_attrs = [
            '_SITEID', '_is_completed', '_days_since_performed'
        ]
        for attr in cache_attrs:
            if hasattr(self, attr):
                delattr(self, attr)
    
    # ==========================================
    # QUERY HELPERS
    # ==========================================
    @classmethod
    def get_by_patient(cls, usubjid, lab_type=None):
        """Get all other tests for a patient"""
        qs = cls.objects.filter(USUBJID=usubjid)
        
        if lab_type:
            qs = qs.filter(LAB_TYPE=lab_type)
        
        return qs.select_related('USUBJID').order_by('SEQUENCE')
    
    @classmethod
    def get_performed_tests(cls, usubjid=None, lab_type=None):
        """Get performed other tests"""
        qs = cls.objects.filter(OTHERTESTPERFORMED=True)
        
        if usubjid:
            qs = qs.filter(USUBJID=usubjid)
        if lab_type:
            qs = qs.filter(LAB_TYPE=lab_type)
        
        return qs.select_related('USUBJID').order_by('-OTHERTESTDTC')
    
    @classmethod
    def get_incomplete_tests(cls, usubjid=None):
        """Get tests marked as performed but missing data"""
        qs = cls.objects.filter(
            OTHERTESTPERFORMED=True
        ).filter(
            models.Q(OTHERTESTRESULT__isnull=True) |
            models.Q(OTHERTESTRESULT__exact='')
        )
        
        if usubjid:
            qs = qs.filter(USUBJID=usubjid)
        
        return qs.select_related('USUBJID').order_by('-OTHERTESTDTC')
    
    @classmethod
    def get_next_sequence(cls, usubjid):
        """Get next available sequence number for a patient"""
        last_seq = (
            cls.objects
            .filter(USUBJID=usubjid)
            .aggregate(models.Max('SEQUENCE'))['SEQUENCE__max']
        )
        return (last_seq or 0) + 1