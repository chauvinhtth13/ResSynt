# backends/studies/study_44en/models/individual.py

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from backends.studies.study_44en.models.base_models import AuditFieldsMixin
from datetime import date


# ==========================================
# 1. INDIVIDUAL - DEMOGRAPHIC INFO
# ==========================================
class Individual(AuditFieldsMixin):
    """Individual member demographic and personal information"""
    
    class EthnicityChoices(models.TextChoices):
        KINH = 'kinh', _('Kinh')
        OTHER = 'other', _('Other')
    
    class EducationChoices(models.TextChoices):
        ILLITERATE = 'illiterate', _('Không biết chữ')
        LITERATE = 'literate', _('Biết đọc, biết viết')
        NOT_SCHOOL_AGE = 'not_school_age', _('Trẻ chưa đi học')
        PRIMARY = 'primary', _('Tiểu học')
        SECONDARY = 'secondary', _('Trung học cơ sở')
        HIGH_SCHOOL = 'high_school', _('Trung học phổ thông')
        VOCATIONAL = 'vocational', _('Trường nghề/Trung cấp/Cao đẳng')
        UNIVERSITY = 'university', _('Đại học trở lên')
    
    class OccupationChoices(models.TextChoices):
        LEADER = 'leader', _('Lãnh đạo, quản lý')
        HIGH_PROFESSIONAL = 'high_professional', _('Nhà chuyên môn bậc cao')
        MID_PROFESSIONAL = 'mid_professional', _('Nhà chuyên môn bậc trung')
        OFFICE_STAFF = 'office_staff', _('Nhân viên trợ lý văn phòng')
        SERVICE_SALES = 'service_sales', _('Nhân viên dịch vụ và bán hàng')
        AGRICULTURE = 'agriculture', _('Lao động nông nghiệp, lâm nghiệp, thủy sản')
        CRAFT = 'craft', _('Lao động thủ công')
        MACHINE_OPERATOR = 'machine_operator', _('Thợ lắp ráp và vận hành máy móc')
        ELEMENTARY = 'elementary', _('Lao động giản đơn')
        ARMED_FORCES = 'armed_forces', _('Lực lượng vũ trang')
        RETIRED = 'retired', _('Hưu trí/Mất sức lao động')
        STUDENT = 'student', _('Còn nhỏ/Đi học')
        UNEMPLOYED = 'unemployed', _('Không có việc làm')
    
    class IndividualIncomeChoices(models.TextChoices):
        NONE = 'none', _('Không có thu nhập')
        LESS_5 = '<5', _('< 5 triệu')
        RANGE_5_12 = '5-12', _('5-12 triệu')
        RANGE_13_25 = '13-25', _('13-25 triệu')
        MORE_25 = '>25', _('> 25 triệu')
    
    class YesNoChoices(models.TextChoices):
        YES = 'yes', _('Yes')
        NO = 'no', _('No')
    
    # PRIMARY KEY - Link to HH_Member
    MEMBER = models.OneToOneField(
        'HH_Member',
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='individual_info',
        verbose_name=_('Household Member')
    )
    
    # PERSONAL INFO
    INITIALS = models.CharField(max_length=20, null=True, blank=True, verbose_name=_('Name Initials'))
    
    # Date of birth (full date) - more detailed than HH_Member.BIRTH_YEAR
    DATE_OF_BIRTH = models.DateField(null=True, blank=True, verbose_name=_('Date of Birth'))
    AGE = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(150)],
        verbose_name=_('Age (if DOB unknown)')
    )
    
    # DEMOGRAPHIC
    ETHNICITY = models.CharField(max_length=20, choices=EthnicityChoices.choices, null=True, blank=True, verbose_name=_('Ethnicity'))
    ETHNICITY_OTHER = models.CharField(max_length=100, null=True, blank=True, verbose_name=_('Other Ethnicity'))
    
    EDUCATION = models.CharField(max_length=30, choices=EducationChoices.choices, null=True, blank=True, verbose_name=_('Education Level'))
    
    OCCUPATION = models.CharField(max_length=30, choices=OccupationChoices.choices, null=True, blank=True, verbose_name=_('Occupation'))
    OCCUPATION_DETAIL = models.CharField(max_length=200, null=True, blank=True, verbose_name=_('Occupation Detail'))
    
    INDIVIDUAL_INCOME = models.CharField(max_length=10, choices=IndividualIncomeChoices.choices, null=True, blank=True, verbose_name=_('Monthly Income'))
    
    HAS_HEALTH_INSURANCE = models.CharField(max_length=10, choices=YesNoChoices.choices, null=True, blank=True, verbose_name=_('Has Health Insurance'))
    
    class Meta:
        db_table = 'Individual'
        verbose_name = _('Individual')
        verbose_name_plural = _('Individuals')
    
    def __str__(self):
        return f"{self.MEMBER.HHID_id} - Member {self.MEMBER.MEMBER_NUM}"
    
    @property
    def full_id(self):
        """44EN-001-1"""
        return f"{self.MEMBER.HHID_id}-{self.MEMBER.MEMBER_NUM}"


# ==========================================
# 2. INDIVIDUAL EXPOSURE
# ==========================================
class Individual_Exposure(AuditFieldsMixin):
    """Individual exposure factors"""
    
    class YesNoChoices(models.TextChoices):
        YES = 'yes', _('Yes')
        NO = 'no', _('No')
    
    MEMBER = models.OneToOneField(
        'Individual',
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='exposure',
        verbose_name=_('Individual')
    )
    
    # SANITATION
    SHARED_TOILET = models.CharField(max_length=10, choices=YesNoChoices.choices, null=True, blank=True, verbose_name=_('Uses Shared Toilet'))
    
    # WATER - Just yes/no, details in separate models (same as household)
    WATER_TREATMENT = models.CharField(max_length=10, choices=YesNoChoices.choices, null=True, blank=True, verbose_name=_('Treats Water'))
    
    # MEDICAL CONDITIONS
    HAS_COMORBIDITY = models.CharField(max_length=10, choices=YesNoChoices.choices, null=True, blank=True, verbose_name=_('Has Comorbidity'))
    
    # VACCINATION
    VACCINATION_STATUS = models.CharField(
        max_length=30,
        choices=[
            ('never', _('Never vaccinated')),
            ('not_remember', _('Not remember')),
            ('vaccinated_not_remember', _('Vaccinated but not remember type')),
            ('vaccinated_specific', _('Vaccinated specific diseases'))
        ],
        null=True, blank=True,
        verbose_name=_('Vaccination Status')
    )
    
    # HOSPITALIZATION (3 months)
    HOSPITALIZED_3M = models.CharField(max_length=10, choices=YesNoChoices.choices, null=True, blank=True, verbose_name=_('Hospitalized (3 months)'))
    
    # MEDICATION (3 months)
    MEDICATION_3M = models.CharField(
        max_length=20,
        choices=[
            ('yes', _('Yes')),
            ('no', _('No')),
        ],
        null=True, blank=True,
        verbose_name=_('Used Medication (3 months)')
    )
    
    class Meta:
        db_table = 'Individual_Exposure'
        verbose_name = _('Individual Exposure')
        verbose_name_plural = _('Individual Exposures')
    
    def __str__(self):
        return f"Exposure: {self.MEMBER_id}"


# ==========================================
# 3. INDIVIDUAL WATER SOURCE - NORMALIZED
# ==========================================
class Individual_WaterSource(AuditFieldsMixin):
    """Individual water sources - same structure as household"""
    
    class SourceTypeChoices(models.TextChoices):
        TAP = 'tap', _('Tap water')
        BOTTLED = 'bottled', _('Bottled water')
        WELL = 'well', _('Well water')
        RAIN = 'rain', _('Rain water')
        RIVER = 'river', _('River water')
        POND = 'pond', _('Pond/Lake water')
        OTHER = 'other', _('Other')
    
    MEMBER = models.ForeignKey('Individual_Exposure', on_delete=models.CASCADE, related_name='water_sources')
    SOURCE_TYPE = models.CharField(max_length=20, choices=SourceTypeChoices.choices, db_index=True)
    SOURCE_TYPE_OTHER = models.CharField(max_length=200, null=True, blank=True)
    
    # PURPOSES
    DRINKING = models.BooleanField(default=False)
    LIVING = models.BooleanField(default=False)
    IRRIGATION = models.BooleanField(default=False)
    FOR_OTHER = models.BooleanField(default=False)
    OTHER_PURPOSE = models.CharField(max_length=200, null=True, blank=True)
    
    class Meta:
        db_table = 'Individual_WaterSource'
        verbose_name = _('Individual Water Source')
        verbose_name_plural = _('Individual Water Sources')
        ordering = ['MEMBER', 'SOURCE_TYPE']
        unique_together = [['MEMBER', 'SOURCE_TYPE']]
    
    def __str__(self):
        return f"{self.MEMBER_id} - {self.get_SOURCE_TYPE_display()}"


# ==========================================
# 4. INDIVIDUAL WATER TREATMENT 
# ==========================================
class Individual_WaterTreatment(AuditFieldsMixin):
    """Individual water treatment methods"""
    
    class TreatmentTypeChoices(models.TextChoices):
        BOILING = 'boiling', _('Boiling')
        FILTER_MACHINE = 'filter_machine', _('Filter machine')
        FILTER_PORTABLE = 'filter_portable', _('Portable filter')
        CHEMICAL = 'chemical', _('Chemical disinfection')
        SODIS = 'sodis', _('Solar disinfection (SODIS)')
        OTHER = 'other', _('Other')
    
    MEMBER = models.ForeignKey('Individual_Exposure', on_delete=models.CASCADE, related_name='treatment_methods')
    TREATMENT_TYPE = models.CharField(max_length=20, choices=TreatmentTypeChoices.choices, db_index=True)
    TREATMENT_TYPE_OTHER = models.CharField(max_length=200, null=True, blank=True)
    
    class Meta:
        db_table = 'Individual_WaterTreatment'
        verbose_name = _('Individual Water Treatment')
        verbose_name_plural = _('Individual Water Treatments')
        ordering = ['MEMBER', 'TREATMENT_TYPE']
        unique_together = [['MEMBER', 'TREATMENT_TYPE']]
    
    def __str__(self):
        return f"{self.MEMBER_id} - {self.get_TREATMENT_TYPE_display()}"


# ==========================================
# 5. COMORBIDITY - NORMALIZED
# ==========================================
class Individual_Comorbidity(AuditFieldsMixin):
    """Medical comorbidities"""
    
    class ComorbidityTypeChoices(models.TextChoices):
        HYPERTENSION = 'hypertension', _('Cao huyết áp')
        DIABETES = 'diabetes', _('Đái tháo đường')
        DYSLIPIDEMIA = 'dyslipidemia', _('Rối loạn mỡ máu')
        CARDIOVASCULAR = 'cardiovascular', _('Bệnh tim mạch')
        ASTHMA = 'asthma', _('Hen suyễn')
        COPD = 'copd', _('Bệnh COPD')
        OSTEOARTHRITIS = 'osteoarthritis', _('Thoái hoá khớp')
        OSTEOPOROSIS = 'osteoporosis', _('Loãng xương')
        DEMENTIA = 'dementia', _('Sa sút trí tuệ')
        STROKE = 'stroke', _('Tai biến')
        DEPRESSION = 'depression', _('Trầm cảm')
        CHRONIC_KIDNEY = 'chronic_kidney', _('Suy thận mạn')
        CHRONIC_HEPATITIS = 'chronic_hepatitis', _('Viêm gan mạn')
        GERD = 'gerd', _('Viêm dạ dày trào ngược')
        CHRONIC_INFECTION = 'chronic_infection', _('Nhiễm trùng mạn tính')
        OBESITY = 'obesity', _('Béo phì')
        ALCOHOL_ADDICTION = 'alcohol_addiction', _('Nghiện bia rượu')
        TOBACCO_ADDICTION = 'tobacco_addiction', _('Nghiện thuốc lá')
        OTHER = 'other', _('Other')
    
    class TreatmentStatusChoices(models.TextChoices):
        TREATING = 'treating', _('Đang điều trị')
        NOT_TREATING = 'not_treating', _('Không điều trị')
    
    MEMBER = models.ForeignKey('Individual_Exposure', on_delete=models.CASCADE, related_name='comorbidities')
    COMORBIDITY_TYPE = models.CharField(max_length=30, choices=ComorbidityTypeChoices.choices, db_index=True)
    COMORBIDITY_OTHER = models.CharField(max_length=200, null=True, blank=True)
    TREATMENT_STATUS = models.CharField(max_length=20, choices=TreatmentStatusChoices.choices, null=True, blank=True)
    
    class Meta:
        db_table = 'Individual_Comorbidity'
        verbose_name = _('Comorbidity')
        verbose_name_plural = _('Comorbidities')
        ordering = ['MEMBER', 'COMORBIDITY_TYPE']
        unique_together = [['MEMBER', 'COMORBIDITY_TYPE']]
    
    def __str__(self):
        return f"{self.MEMBER_id} - {self.get_COMORBIDITY_TYPE_display()}"


# ==========================================
# 6. VACCINE - NORMALIZED
# ==========================================
class Individual_Vaccine(AuditFieldsMixin):
    """Vaccination records"""
    
    class VaccineTypeChoices(models.TextChoices):
        BCG = 'bcg', _('BCG (bệnh lao)')
        FLU = 'flu', _('Cúm')
        RUBELLA = 'rubella', _('Rubella')
        HEPATITIS_A = 'hepatitis_a', _('Viêm gan A')
        HIB = 'hib', _('Haemophilus influenzae type B')
        CHICKENPOX = 'chickenpox', _('Bệnh thuỷ đậu')
        HEPATITIS_B = 'hepatitis_b', _('Viêm gan B')
        POLIO = 'polio', _('Sốt bại liệt')
        JAPANESE_ENCEPHALITIS = 'japanese_encephalitis', _('Viêm não Nhật Bản')
        DIPHTHERIA = 'diphtheria', _('Bạch hầu')
        MEASLES = 'measles', _('Sởi')
        MENINGITIS = 'meningitis', _('Viêm màng não')
        TETANUS = 'tetanus', _('Uốn ván')
        MUMPS = 'mumps', _('Quai bị')
        ROTAVIRUS = 'rotavirus', _('Rotavirus')
        PERTUSSIS = 'pertussis', _('Ho gà')
        RABIES = 'rabies', _('Bệnh dại')
        PNEUMOCOCCAL = 'pneumococcal', _('Phế cầu khuẩn')
        OTHER = 'other', _('Other')
    
    MEMBER = models.ForeignKey('Individual_Exposure', on_delete=models.CASCADE, related_name='vaccines')
    VACCINE_TYPE = models.CharField(max_length=30, choices=VaccineTypeChoices.choices, db_index=True)
    VACCINE_OTHER = models.CharField(max_length=200, null=True, blank=True)
    
    class Meta:
        db_table = 'Individual_Vaccine'
        verbose_name = _('Vaccine')
        verbose_name_plural = _('Vaccines')
        ordering = ['MEMBER', 'VACCINE_TYPE']
        unique_together = [['MEMBER', 'VACCINE_TYPE']]
    
    def __str__(self):
        return f"{self.MEMBER_id} - {self.get_VACCINE_TYPE_display()}"


# ==========================================
# 7. HOSPITALIZATION - NORMALIZED
# ==========================================
class Individual_Hospitalization(AuditFieldsMixin):
    """Hospitalization records in last 3 months"""
    
    class HospitalTypeChoices(models.TextChoices):
        CENTRAL = 'central', _('Bệnh viện trung ương')
        CITY = 'city', _('Bệnh viện thành phố')
        DISTRICT = 'district', _('Bệnh viện quận, huyện')
        PRIVATE = 'private', _('Bệnh viện tư')
        OTHER = 'other', _('Other')
    
    class DurationChoices(models.TextChoices):
        DAYS_1_3 = '1-3', _('1-3 ngày')
        DAYS_3_5 = '3-5', _('3-5 ngày')
        DAYS_5_7 = '5-7', _('5-7 ngày')
        DAYS_7_PLUS = '>7', _('Trên 7 ngày')
    
    MEMBER = models.ForeignKey('Individual_Exposure', on_delete=models.CASCADE, related_name='hospitalizations')
    HOSPITAL_TYPE = models.CharField(max_length=20, choices=HospitalTypeChoices.choices, db_index=True)
    HOSPITAL_OTHER = models.CharField(max_length=200, null=True, blank=True)
    DURATION = models.CharField(max_length=10, choices=DurationChoices.choices, null=True, blank=True)
    
    class Meta:
        db_table = 'Individual_Hospitalization'
        verbose_name = _('Hospitalization')
        verbose_name_plural = _('Hospitalizations')
        ordering = ['MEMBER', 'HOSPITAL_TYPE']
    
    def __str__(self):
        return f"{self.MEMBER_id} - {self.get_HOSPITAL_TYPE_display()}"


# ==========================================
# 8. MEDICATION - NORMALIZED
# ==========================================
class Individual_Medication(AuditFieldsMixin):
    """Medication use in last 3 months"""
    
    class MedicationTypeChoices(models.TextChoices):
        ANTIBIOTIC = 'antibiotic', _('Kháng sinh')
        ACID_SUPPRESSOR = 'acid_suppressor', _('Thuốc ức chế acid dịch vị')
        CHRONIC_DISEASE = 'chronic_disease', _('Thuốc trị bệnh mạn tính')
        PROBIOTICS = 'probiotics', _('Probiotics và prebiotics')
        HERBAL = 'herbal', _('Thuốc thảo dược, đông y')
    
    class DurationChoices(models.TextChoices):
        DAYS_1_3 = '1-3', _('1-3 ngày')
        DAYS_3_5 = '3-5', _('3-5 ngày')
        DAYS_5_7 = '5-7', _('5-7 ngày')
        DAYS_7_14 = '7-14', _('7-14 ngày')
        DAYS_14_PLUS = '>14', _('> 14 ngày')
    
    MEMBER = models.ForeignKey('Individual_Exposure', on_delete=models.CASCADE, related_name='medications')
    MEDICATION_TYPE = models.CharField(max_length=30, choices=MedicationTypeChoices.choices, db_index=True)
    MEDICATION_DETAIL = models.CharField(max_length=500, null=True, blank=True, verbose_name=_('Medication Detail'))
    DURATION = models.CharField(max_length=10, choices=DurationChoices.choices, null=True, blank=True)
    
    class Meta:
        db_table = 'Individual_Medication'
        verbose_name = _('Medication')
        verbose_name_plural = _('Medications')
        ordering = ['MEMBER', 'MEDICATION_TYPE']
    
    def __str__(self):
        return f"{self.MEMBER_id} - {self.get_MEDICATION_TYPE_display()}"


# ==========================================
# 9. FOOD FREQUENCY - SAME AS HOUSEHOLD
# ==========================================
class Individual_FoodFrequency(AuditFieldsMixin):
    """Individual food consumption frequency"""
    
    class FrequencyChoices(models.TextChoices):
        NEVER = 'never', _('Never')
        MONTHLY_1_3 = '1-3/month', _('1-3 times/month')
        WEEKLY_1_2 = '1-2/week', _('1-2 times/week')
        WEEKLY_3_5 = '3-5/week', _('3-5 times/week')
        DAILY_1 = '1/day', _('1 time/day')
        DAILY_2_PLUS = '2+/day', _('2+ times/day')
    
    MEMBER = models.OneToOneField('Individual', on_delete=models.CASCADE, primary_key=True, related_name='food_frequency')
    
    # FOOD CATEGORIES (same as household)
    RICE_NOODLES = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    RED_MEAT = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    POULTRY = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    FISH_SEAFOOD = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    EGGS = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    RAW_VEGETABLES = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    COOKED_VEGETABLES = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    DAIRY = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    FERMENTED = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    BEER = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    ALCOHOL = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    
    class Meta:
        db_table = 'Individual_FoodFrequency'
        verbose_name = _('Individual Food Frequency')
        verbose_name_plural = _('Individual Food Frequencies')
    
    def __str__(self):
        return f"Food Freq: {self.MEMBER_id}"


# ==========================================
# 10. TRAVEL HISTORY
# ==========================================
class Individual_Travel(AuditFieldsMixin):
    """Travel history in last 3 months"""
    
    class FrequencyChoices(models.TextChoices):
        DAILY = 'daily', _('Mỗi ngày')
        WEEKLY_1_2 = '1-2/week', _('1-2 lần/tuần')
        MONTHLY_1_2 = '1-2/month', _('1-2 lần/tháng')
        LESS_MONTHLY = '<1/month', _('< 1 lần/tháng')
        NEVER = 'never', _('Không đi')
    
    class TravelTypeChoices(models.TextChoices):
        INTERNATIONAL = 'international', _('Nước ngoài')
        DOMESTIC = 'domestic', _('Tỉnh thành trong nước')
    
    MEMBER = models.ForeignKey('Individual', on_delete=models.CASCADE, related_name='travel_history')
    TRAVEL_TYPE = models.CharField(max_length=20, choices=TravelTypeChoices.choices, db_index=True)
    FREQUENCY = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    
    class Meta:
        db_table = 'Individual_Travel'
        verbose_name = _('Travel History')
        verbose_name_plural = _('Travel Histories')
        ordering = ['MEMBER', 'TRAVEL_TYPE']
        unique_together = [['MEMBER', 'TRAVEL_TYPE']]
    
    def __str__(self):
        return f"{self.MEMBER_id} - {self.get_TRAVEL_TYPE_display()}"


# ==========================================
# 11. FOLLOW-UP VISITS
# ==========================================
class Individual_FollowUp(AuditFieldsMixin):
    """Follow-up visit records (Day 14, 28, 90)"""
    
    class VisitTimeChoices(models.TextChoices):
        DAY_14 = 'day_14', _('Day 14 ± 3')
        DAY_28 = 'day_28', _('Day 28 ± 3')
        DAY_90 = 'day_90', _('Day 90 ± 3')
    
    class YesNoNAChoices(models.TextChoices):
        YES = 'yes', _('Yes')
        NO = 'no', _('No')
        NA = 'na', _('Not applicable')
    
    # Composite PK: MEMBER + VISIT_TIME
    FOLLOW_UP_id = models.CharField(max_length=50, primary_key=True, editable=False, verbose_name=_('Follow-up ID'))
    MEMBER = models.ForeignKey('Individual', on_delete=models.CASCADE, related_name='follow_ups')
    VISIT_TIME = models.CharField(max_length=10, choices=VisitTimeChoices.choices, db_index=True)
    
    # VISIT INFO
    ASSESSED = models.CharField(max_length=10, choices=YesNoNAChoices.choices, null=True, blank=True, verbose_name=_('Was Assessed'))
    ASSESSMENT_DATE = models.DateField(null=True, blank=True, verbose_name=_('Assessment Date'))
    
    # SYMPTOMS
    HAS_SYMPTOMS = models.CharField(max_length=10, choices=YesNoNAChoices.choices, null=True, blank=True, verbose_name=_('Has Symptoms'))
    
    # HOSPITALIZATION
    HOSPITALIZED = models.CharField(max_length=10, choices=YesNoNAChoices.choices, null=True, blank=True, verbose_name=_('Hospitalized'))
    
    # MEDICATION
    USED_MEDICATION = models.CharField(max_length=10, choices=YesNoNAChoices.choices, null=True, blank=True, verbose_name=_('Used Medication'))
    ANTIBIOTIC_TYPE = models.CharField(max_length=500, null=True, blank=True, verbose_name=_('Antibiotic Type'))
    STEROID_TYPE = models.CharField(max_length=500, null=True, blank=True, verbose_name=_('Steroid Type'))
    OTHER_MEDICATION = models.CharField(max_length=500, null=True, blank=True, verbose_name=_('Other Medication'))
    
    class Meta:
        db_table = 'Individual_FollowUp'
        verbose_name = _('Follow-up Visit')
        verbose_name_plural = _('Follow-up Visits')
        ordering = ['MEMBER', 'VISIT_TIME']
    
    def save(self, *args, **kwargs):
        # Auto-generate PK from MEMBER_id + VISIT_TIME
        if not self.FOLLOW_UP_id:
            self.FOLLOW_UP_id = f"{self.MEMBER_id}-{self.VISIT_TIME}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.MEMBER_id} - {self.get_VISIT_TIME_display()}"


# ==========================================
# 12. SYMPTOMS - NORMALIZED
# ==========================================
class Individual_Symptom(AuditFieldsMixin):
    """Symptoms at each follow-up visit"""
    
    class SymptomTypeChoices(models.TextChoices):
        FATIGUE = 'fatigue', _('Mệt mỏi')
        FEVER = 'fever', _('Sốt')
        COUGH = 'cough', _('Ho')
        EYE_PAIN = 'eye_pain', _('Đau mắt')
        RED_EYES = 'red_eyes', _('Đỏ mắt')
        MUSCLE_PAIN = 'muscle_pain', _('Đau nhức cơ')
        ANOREXIA = 'anorexia', _('Chán ăn')
        DYSPNEA = 'dyspnea', _('Thở mệt')
        JAUNDICE = 'jaundice', _('Vàng da')
        HEADACHE = 'headache', _('Nhức đầu')
        DYSURIA = 'dysuria', _('Tiểu gắt/buốt')
        HEMATURIA = 'hematuria', _('Tiểu đỏ')
        DIFFICULT_URINATION = 'difficult_urination', _('Tiểu khó/lắt nhắt')
        PYURIA = 'pyuria', _('Tiểu mủ/đục/hôi')
        VOMITING = 'vomiting', _('Nôn ói')
        NAUSEA = 'nausea', _('Buồn nôn')
        DIARRHEA = 'diarrhea', _('Tiêu chảy')
        ABDOMINAL_PAIN = 'abdominal_pain', _('Đau bụng')
        OTHER = 'other', _('Other')
    
    FOLLOW_UP = models.ForeignKey('Individual_FollowUp', on_delete=models.CASCADE, related_name='symptoms')
    SYMPTOM_TYPE = models.CharField(max_length=30, choices=SymptomTypeChoices.choices, db_index=True)
    SYMPTOM_OTHER = models.CharField(max_length=200, null=True, blank=True)
    
    class Meta:
        db_table = 'Individual_Symptom'
        verbose_name = _('Symptom')
        verbose_name_plural = _('Symptoms')
        ordering = ['FOLLOW_UP', 'SYMPTOM_TYPE']
        unique_together = [['FOLLOW_UP', 'SYMPTOM_TYPE']]
    
    def __str__(self):
        return f"{self.FOLLOW_UP.MEMBER_id} - {self.FOLLOW_UP.get_VISIT_TIME_display()} - {self.get_SYMPTOM_TYPE_display()}"


# ==========================================
# 13. FOLLOW-UP HOSPITALIZATION - NORMALIZED
# ==========================================
class Individual_FollowUp_Hospitalization(AuditFieldsMixin):
    """Hospitalization records at each follow-up visit"""
    
    class HospitalTypeChoices(models.TextChoices):
        CENTRAL = 'central', _('Bệnh viện trung ương')
        CITY = 'city', _('Bệnh viện thành phố')
        DISTRICT = 'district', _('Bệnh viện quận, huyện')
        PRIVATE = 'private', _('Bệnh viện tư')
        OTHER = 'other', _('Other')
    
    class DurationChoices(models.TextChoices):
        DAYS_1_3 = '1-3', _('1-3 ngày')
        DAYS_3_5 = '3-5', _('3-5 ngày')
        DAYS_5_7 = '5-7', _('5-7 ngày')
        DAYS_7_PLUS = '>7', _('Trên 7 ngày')
    
    FOLLOW_UP = models.ForeignKey('Individual_FollowUp', on_delete=models.CASCADE, related_name='hospitalizations')
    HOSPITAL_TYPE = models.CharField(max_length=20, choices=HospitalTypeChoices.choices, db_index=True)
    HOSPITAL_OTHER = models.CharField(max_length=200, null=True, blank=True)
    DURATION = models.CharField(max_length=10, choices=DurationChoices.choices, null=True, blank=True)
    
    class Meta:
        db_table = 'Individual_FollowUp_Hospitalization'
        verbose_name = _('Follow-up Hospitalization')
        verbose_name_plural = _('Follow-up Hospitalizations')
        ordering = ['FOLLOW_UP', 'HOSPITAL_TYPE']
        unique_together = [['FOLLOW_UP', 'HOSPITAL_TYPE']]
    
    def __str__(self):
        return f"{self.FOLLOW_UP.MEMBER_id} - {self.FOLLOW_UP.get_VISIT_TIME_display()} - {self.get_HOSPITAL_TYPE_display()}"

# ==========================================
# 14. SAMPLE COLLECTION
# ==========================================

class Individual_Sample(AuditFieldsMixin):
    """Sample collection records"""
    
    class SampleTimeChoices(models.TextChoices):
        BASELINE = 'baseline', _('Ngày tham gia + 3')
        DAY_14 = 'day_14', _('Ngày 14 ± 3')
        DAY_28 = 'day_28', _('Ngày 28 ± 3')
        DAY_90 = 'day_90', _('Ngày 90 ± 3')
    
    class YesNoNAChoices(models.TextChoices):
        YES = 'yes', _('Yes')
        NO = 'no', _('No')
        NA = 'na', _('Not applicable')
    
    MEMBER = models.ForeignKey('Individual', on_delete=models.CASCADE, related_name='samples')
    SAMPLE_TIME = models.CharField(max_length=10, choices=SampleTimeChoices.choices, db_index=True)
    
    # SAMPLE COLLECTION
    SAMPLE_COLLECTED = models.CharField(max_length=10, choices=YesNoNAChoices.choices, null=True, blank=True, verbose_name=_('Sample Collected'))
    
    # STOOL SAMPLE
    STOOL_DATE = models.DateField(null=True, blank=True, verbose_name=_('Stool Sample Date'))
    
    # THROAT SWAB
    THROAT_SWAB_DATE = models.DateField(null=True, blank=True, verbose_name=_('Throat Swab Date'))
    
    # REASON IF NOT COLLECTED
    NOT_COLLECTED_REASON = models.CharField(max_length=500, null=True, blank=True, verbose_name=_('Reason Not Collected'))
    
    class Meta:
        db_table = 'Individual_Sample'
        verbose_name = _('Sample Collection')
        verbose_name_plural = _('Sample Collections')
        ordering = ['MEMBER', 'SAMPLE_TIME']
        unique_together = [['MEMBER', 'SAMPLE_TIME']]
    
    def __str__(self):
        return f"{self.MEMBER_id} - {self.get_SAMPLE_TIME_display()}"