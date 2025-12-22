# backends/studies/study_44en/models/household.py

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.functional import cached_property
from backends.studies.study_44en.models.base_models import AuditFieldsMixin
from django.db.models import Q
from datetime import date
import re


# ==========================================
# 1. MAIN HOUSEHOLD MODEL
# ==========================================
class HH_CASE(AuditFieldsMixin):
    """Main household information"""
    
    class OwnershipChoices(models.TextChoices):
        RENTED = 'rented', _('Rented')
        OWNED = 'owned', _('Owned')
    
    class IncomeRangeChoices(models.TextChoices):
        LESS_15 = '<15', _('< 15 million VND')
        RANGE_15_30 = '15-30', _('15-30 million VND')
        RANGE_31_50 = '31-50', _('31-50 million VND')
        MORE_50 = '>50', _('> 50 million VND')
    
    class HousingTypeChoices(models.TextChoices):
        PERMANENT = 'permanent', _('Permanent house')
        TEMPORARY = 'temporary', _('Temporary/rudimentary house')
        OTHER = 'other', _('Other')
    
    class FloorMaterialChoices(models.TextChoices):
        CERAMIC_TILE = 'ceramic', _('Ceramic/Granite tiles')
        WOOD = 'wood', _('Wooden floor')
        VINYL = 'vinyl', _('Vinyl/Plastic floor')
        NATURAL_STONE = 'stone', _('Natural stone')
        CONCRETE = 'concrete', _('Concrete/Cement')
        OTHER = 'other', _('Other')
    
    class RoofMaterialChoices(models.TextChoices):
        CONCRETE = 'concrete', _('Reinforced concrete')
        METAL = 'metal', _('Metal sheets/Corrugated iron')
        TILE = 'tile', _('Tiles')
        FIBER = 'fiber', _('Fiber cement sheets')
        OTHER = 'other', _('Other')
    
    # PRIMARY KEY
    HHID = models.CharField(max_length=50, primary_key=True, verbose_name=_('Household ID'))
    STUDYID = models.CharField(max_length=50, default='44EN', verbose_name=_('Study ID'))
    
    # RESPONDENT
    RESPONDENT_MEMBER_NUM = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name=_('Respondent Member Number')
    )
    
    # ADDRESS
    STREET = models.CharField(max_length=200, null=True, blank=True, verbose_name=_('Street/Road/Block'))
    WARD = models.CharField(max_length=100, null=True, blank=True, db_index=True, verbose_name=_('Ward/Commune'))
    CITY = models.CharField(max_length=100, default='Ho Chi Minh City', verbose_name=_('City'))
    
    # HOUSEHOLD COMPOSITION
    TOTAL_MEMBERS = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        db_index=True, verbose_name=_('Total Household Members')
    )
    MONTHLY_INCOME = models.CharField(
        max_length=10, choices=IncomeRangeChoices.choices,
        null=True, blank=True, db_index=True,
        verbose_name=_('Average Monthly Household Income')
    )
    
    # HOUSING
    OWNERSHIP = models.CharField(max_length=20, choices=OwnershipChoices.choices, null=True, blank=True, verbose_name=_('House Ownership'))
    LAND_AREA = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)], verbose_name=_('Land Area (m²)'))
    NUM_FLOORS = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1)], verbose_name=_('Number of Floors'))
    NUM_ROOMS = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)], verbose_name=_('Number of Rooms'))
    
    HOUSING_TYPE = models.CharField(max_length=20, choices=HousingTypeChoices.choices, null=True, blank=True, verbose_name=_('Housing Type'))
    HOUSING_TYPE_OTHER = models.CharField(max_length=200, null=True, blank=True, verbose_name=_('Other Housing Type'))
    
    FLOOR_MATERIAL = models.CharField(max_length=20, choices=FloorMaterialChoices.choices, null=True, blank=True, verbose_name=_('Floor Material'))
    FLOOR_MATERIAL_OTHER = models.CharField(max_length=200, null=True, blank=True, verbose_name=_('Other Floor Material'))
    
    ROOF_MATERIAL = models.CharField(max_length=20, choices=RoofMaterialChoices.choices, null=True, blank=True, verbose_name=_('Roof Material'))
    ROOF_MATERIAL_OTHER = models.CharField(max_length=200, null=True, blank=True, verbose_name=_('Other Roof Material'))
    
    # ASSETS
    TV = models.BooleanField(default=False, verbose_name=_('Television'))
    AC = models.BooleanField(default=False, verbose_name=_('Air Conditioner'))
    COMPUTER = models.BooleanField(default=False, verbose_name=_('Desktop/Laptop'))
    REFRIGERATOR = models.BooleanField(default=False, verbose_name=_('Refrigerator'))
    INTERNET = models.BooleanField(default=False, verbose_name=_('Internet Access'))
    WASHING_MACHINE = models.BooleanField(default=False, verbose_name=_('Washing Machine'))
    MOBILE_PHONE = models.BooleanField(default=False, verbose_name=_('Mobile Phone'))
    WATER_HEATER = models.BooleanField(default=False, verbose_name=_('Water Heater'))
    BICYCLE = models.BooleanField(default=False, verbose_name=_('Bicycle'))
    GAS_STOVE = models.BooleanField(default=False, verbose_name=_('Gas Stove'))
    MOTORCYCLE = models.BooleanField(default=False, verbose_name=_('Motorcycle'))
    INDUCTION_COOKER = models.BooleanField(default=False, verbose_name=_('Induction Cooker'))
    CAR = models.BooleanField(default=False, verbose_name=_('Car'))
    RICE_COOKER = models.BooleanField(default=False, verbose_name=_('Rice Cooker'))
    
    class Meta:
        db_table = 'HH_CASE'
        verbose_name = _('Household Case')
        verbose_name_plural = _('Household Cases')
        ordering = ['HHID']
        indexes = [
            models.Index(fields=['WARD', 'CITY'], name='idx_hh_location'),
            models.Index(fields=['TOTAL_MEMBERS'], name='idx_hh_members'),
            models.Index(fields=['MONTHLY_INCOME'], name='idx_hh_income'),
        ]
    
    def __str__(self):
        return self.HHID
    
    def save(self, *args, **kwargs):
        # Auto-generate HHID
        if not self.HHID:
            last_hh = HH_CASE.objects.filter(HHID__startswith='44EN-').order_by('-HHID').first()
            if last_hh:
                match = re.match(r'44EN-(\d+)', last_hh.HHID)
                last_num = int(match.group(1)) if match else 0
                self.HHID = f"44EN-{last_num + 1:03d}"
            else:
                self.HHID = "44EN-001"
        super().save(*args, **kwargs)


# ==========================================
# 2. HOUSEHOLD MEMBER MODEL
# ==========================================
class HH_Member(AuditFieldsMixin):
    """Household member with dynamic child ordering"""
    
    class RelationshipChoices(models.TextChoices):
        HEAD = 'A', _('Household head')
        WIFE = 'B', _('Wife')
        HUSBAND = 'C', _('Husband')
        CHILD = 'D', _('Child')
        PARENT = 'E', _('Parent')
        GRANDPARENT = 'F', _('Grandparent')
        OTHER = 'G', _('Other')
    
    class GenderChoices(models.TextChoices):
        MALE = 'Male', _('Male')
        FEMALE = 'Female', _('Female')
    
    # PRIMARY KEY: HHID-MEMBER_NUM (e.g., "44EN-001-1")
    MEMBERID = models.CharField(max_length=50, primary_key=True, editable=False, verbose_name=_('Member ID'))
    HHID = models.ForeignKey('HH_CASE', on_delete=models.CASCADE, to_field='HHID', db_column='HHID', related_name='members')
    MEMBER_NUM = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)], verbose_name=_('Member Number'))
    RELATIONSHIP = models.CharField(max_length=5, choices=RelationshipChoices.choices, null=True, blank=True, verbose_name=_('Relationship'))
    CHILD_ORDER = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1)], verbose_name=_('Child Order'))
    BIRTH_YEAR = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1900)], verbose_name=_('Birth Year'))
    GENDER = models.CharField(max_length=10, choices=GenderChoices.choices, null=True, blank=True, verbose_name=_('Gender'))
    ISRESPONDENT = models.BooleanField(default=False, verbose_name=_('Is Respondent'))
    
    class Meta:
        db_table = 'HH_Member'
        verbose_name = _('Household Member')
        verbose_name_plural = _('Household Members')
        ordering = ['HHID', 'MEMBER_NUM']
        indexes = [
            models.Index(fields=['HHID', 'MEMBER_NUM'], name='idx_hhmem_hh_num'),
            models.Index(fields=['RELATIONSHIP', 'CHILD_ORDER'], name='idx_hhmem_child'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['HHID'], condition=Q(ISRESPONDENT=True), name='unique_respondent'),
            models.UniqueConstraint(fields=['HHID', 'CHILD_ORDER'], condition=Q(RELATIONSHIP='D'), name='unique_child_order'),
            # MEMBER_NUM range
            models.CheckConstraint(
                condition=models.Q(MEMBER_NUM__gte=1, MEMBER_NUM__lte=10),
                name='hh_member_num_range',
                violation_error_message='Member number must be between 1 and 10'
            ),
            # Birth year reasonable
            models.CheckConstraint(
                condition=models.Q(BIRTH_YEAR__isnull=True) | models.Q(BIRTH_YEAR__gte=1900, BIRTH_YEAR__lte=2025),
                name='hh_member_birth_year_range',
                violation_error_message='Birth year must be between 1900 and current year'
            ),
        ]
    
    def clean(self):
        """Validate HH_Member data."""
        errors = {}
        
        # Validate MEMBER_NUM range
        if self.MEMBER_NUM:
            if self.MEMBER_NUM < 1 or self.MEMBER_NUM > 10:
                errors['MEMBER_NUM'] = _('Member number must be between 1 and 10')
            
            # Check for duplicate MEMBER_NUM in household
            if self.HHID:
                existing = HH_Member.objects.filter(
                    HHID=self.HHID,
                    MEMBER_NUM=self.MEMBER_NUM
                ).exclude(MEMBERID=self.MEMBERID).exists()
                
                if existing:
                    errors['MEMBER_NUM'] = _(f'Member number {self.MEMBER_NUM} already exists in household')
        
        # Validate birth year
        if self.BIRTH_YEAR:
            current_year = date.today().year
            if self.BIRTH_YEAR > current_year:
                errors['BIRTH_YEAR'] = _('Birth year cannot be in the future')
            if self.BIRTH_YEAR < 1900:
                errors['BIRTH_YEAR'] = _('Birth year seems unrealistic (<1900)')
            if current_year - self.BIRTH_YEAR > 150:
                errors['BIRTH_YEAR'] = _('Unrealistic age (>150 years)')
        
        # Validate CHILD_ORDER only for children
        if self.CHILD_ORDER and self.RELATIONSHIP != 'D':
            errors['CHILD_ORDER'] = _('Child order only applicable for children (relationship D)')
        
        # Validate CHILD_ORDER required for children
        if self.RELATIONSHIP == 'D' and not self.CHILD_ORDER:
            errors['CHILD_ORDER'] = _('Child order is required for children')
        
        # Validate ISRESPONDENT logic (constraint handles uniqueness)
        if self.ISRESPONDENT:
            if self.HHID:
                existing = HH_Member.objects.filter(
                    HHID=self.HHID,
                    ISRESPONDENT=True
                ).exclude(MEMBERID=self.MEMBERID).exists()
                
                if existing:
                    errors['ISRESPONDENT'] = _('Household already has a respondent')
        
        # Validate gender provided
        if not self.GENDER:
            errors['GENDER'] = _('Gender is required')
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        # Auto-generate MEMBERID from HHID + MEMBER_NUM
        if not self.MEMBERID:
            self.MEMBERID = f"{self.HHID_id}-{self.MEMBER_NUM}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.MEMBERID}"
    
    @property
    def crf_code(self):
        """CRF code: A, B, C, D1, D2, E, F, G"""
        if self.RELATIONSHIP == 'D' and self.CHILD_ORDER:
            return f"D{self.CHILD_ORDER}"
        return self.RELATIONSHIP


# ==========================================
# 3. HOUSEHOLD EXPOSURE - FULLY NORMALIZED
# ==========================================
class HH_Exposure(AuditFieldsMixin):
    """Household exposure factors"""
    
    class ToiletTypeChoices(models.TextChoices):
        SEPTIC_FLUSH = 'septic_flush', _('Toilet with septic tank')
        NO_SEPTIC = 'no_septic', _('Toilet without septic tank')
        OUTDOOR = 'outdoor', _('Outdoor toilet')
        NO_TOILET = 'no_toilet', _('No toilet')
        OTHER = 'other', _('Other')
    
    class CookingFuelChoices(models.TextChoices):
        GAS = 'gas', _('Gas')
        COAL = 'coal', _('Coal')
        WOOD = 'wood', _('Wood/Firewood')
        OIL = 'oil', _('Oil')
        ELECTRICITY = 'electricity', _('Electricity')
        OTHER = 'other', _('Other')
    
    class YesNoChoices(models.TextChoices):
        YES = 'yes', _('Yes')
        NO = 'no', _('No')
    
    HHID = models.OneToOneField('HH_CASE', on_delete=models.CASCADE, primary_key=True, to_field='HHID', db_column='HHID', related_name='exposure')
    
    # SANITATION
    TOILET_TYPE = models.CharField(max_length=20, choices=ToiletTypeChoices.choices, null=True, blank=True, db_index=True)
    TOILET_TYPE_OTHER = models.CharField(max_length=200, null=True, blank=True)
    NUM_TOILETS = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    
    # COOKING
    COOKING_FUEL = models.CharField(max_length=20, choices=CookingFuelChoices.choices, null=True, blank=True, db_index=True)
    COOKING_FUEL_OTHER = models.CharField(max_length=200, null=True, blank=True)
    
    #  WATER TREATMENT - Just Yes/No, details in separate model
    WATER_TREATMENT = models.CharField(max_length=10, choices=YesNoChoices.choices, null=True, blank=True)
    
    #  ANIMALS - Just Yes/No, details in separate model
    RAISES_ANIMALS = models.CharField(max_length=10, choices=YesNoChoices.choices, null=True, blank=True)
    
    class Meta:
        db_table = 'HH_Exposure'
        verbose_name = _('Household Exposure')
        verbose_name_plural = _('Household Exposures')
        indexes = [
            models.Index(fields=['TOILET_TYPE'], name='idx_exp_toilet'),
            models.Index(fields=['COOKING_FUEL'], name='idx_exp_fuel'),
            models.Index(fields=['WATER_TREATMENT'], name='idx_exp_water'),
            models.Index(fields=['RAISES_ANIMALS'], name='idx_exp_animals'),
        ]
        constraints = [
            # Toilet type OTHER must have detail
            models.CheckConstraint(
                condition=~models.Q(TOILET_TYPE='other') | models.Q(TOILET_TYPE_OTHER__isnull=False),
                name='hh_toilet_type_other_detail',
                violation_error_message='Please specify other toilet type'
            ),
            # Cooking fuel OTHER must have detail
            models.CheckConstraint(
                condition=~models.Q(COOKING_FUEL='other') | models.Q(COOKING_FUEL_OTHER__isnull=False),
                name='hh_cooking_fuel_other_detail',
                violation_error_message='Please specify other cooking fuel'
            ),
            # Number of toilets must be reasonable
            models.CheckConstraint(
                condition=models.Q(NUM_TOILETS__isnull=True) | models.Q(NUM_TOILETS__gte=0, NUM_TOILETS__lte=10),
                name='hh_num_toilets_range',
                violation_error_message='Number of toilets must be between 0 and 10'
            ),
        ]
    
    def __str__(self):
        return f"Exposure: {self.HHID_id}"


# ==========================================
# 4. WATER SOURCE - NORMALIZED
# ==========================================
class HH_WaterSource(AuditFieldsMixin):
    """Water sources - one record per source"""
    
    class SourceTypeChoices(models.TextChoices):
        TAP = 'tap', _('Tap water')
        BOTTLED = 'bottled', _('Bottled water')
        WELL = 'well', _('Well water')
        RAIN = 'rain', _('Rain water')
        RIVER = 'river', _('River water')
        POND = 'pond', _('Pond/Lake water')
        OTHER = 'other', _('Other')
    
    HHID = models.ForeignKey('HH_Exposure', on_delete=models.CASCADE, to_field='HHID', db_column='HHID', related_name='water_sources')
    SOURCE_TYPE = models.CharField(max_length=20, choices=SourceTypeChoices.choices, db_index=True)
    SOURCE_TYPE_OTHER = models.CharField(max_length=200, null=True, blank=True)
    
    # PURPOSES
    DRINKING = models.BooleanField(default=False)
    LIVING = models.BooleanField(default=False)
    IRRIGATION = models.BooleanField(default=False)
    OTHER = models.BooleanField(default=False)
    OTHER_PURPOSE = models.CharField(max_length=200, null=True, blank=True)
    
    class Meta:
        db_table = 'HH_WaterSource'
        verbose_name = _('Water Source')
        verbose_name_plural = _('Water Sources')
        ordering = ['HHID', 'SOURCE_TYPE']
        unique_together = [['HHID', 'SOURCE_TYPE']]
        indexes = [
            models.Index(fields=['HHID', 'SOURCE_TYPE'], name='idx_water_hh_type'),
            models.Index(fields=['DRINKING'], name='idx_water_drinking'),
        ]
    
    def __str__(self):
        return f"{self.HHID_id} - {self.get_SOURCE_TYPE_display()}"


# ==========================================
# 5. WATER TREATMENT - NORMALIZED (NEW!)
# ==========================================
class HH_WaterTreatment(AuditFieldsMixin):
    """Water treatment methods - one record per method"""
    
    class TreatmentTypeChoices(models.TextChoices):
        BOILING = 'boiling', _('Boiling')
        FILTER_MACHINE = 'filter_machine', _('Filter machine')
        FILTER_PORTABLE = 'filter_portable', _('Portable filter')
        CHEMICAL = 'chemical', _('Chemical disinfection')
        SODIS = 'sodis', _('Solar disinfection (SODIS)')
        OTHER = 'other', _('Other')
    
    HHID = models.ForeignKey('HH_Exposure', on_delete=models.CASCADE, to_field='HHID', db_column='HHID', related_name='treatment_methods')
    TREATMENT_TYPE = models.CharField(max_length=20, choices=TreatmentTypeChoices.choices, db_index=True)
    TREATMENT_TYPE_OTHER = models.CharField(max_length=200, null=True, blank=True)
    
    class Meta:
        db_table = 'HH_WaterTreatment'
        verbose_name = _('Water Treatment Method')
        verbose_name_plural = _('Water Treatment Methods')
        ordering = ['HHID', 'TREATMENT_TYPE']
        unique_together = [['HHID', 'TREATMENT_TYPE']]
        indexes = [
            models.Index(fields=['HHID', 'TREATMENT_TYPE'], name='idx_treatment_hh_type'),
        ]
    
    def __str__(self):
        return f"{self.HHID_id} - {self.get_TREATMENT_TYPE_display()}"


# ==========================================
# 6. ANIMAL - NORMALIZED
# ==========================================
class HH_Animal(AuditFieldsMixin):
    """Animals raised - one record per animal type"""
    
    class AnimalTypeChoices(models.TextChoices):
        DOG = 'dog', _('Dog')
        CAT = 'cat', _('Cat')
        COW = 'cow', _('Cow')
        BIRD = 'bird', _('Bird')
        POULTRY = 'poultry', _('Chicken/Duck')
        OTHER = 'other', _('Other')
    
    HHID = models.ForeignKey('HH_Exposure', on_delete=models.CASCADE, to_field='HHID', db_column='HHID', related_name='animals')
    ANIMAL_TYPE = models.CharField(max_length=20, choices=AnimalTypeChoices.choices, db_index=True)
    ANIMAL_TYPE_OTHER = models.CharField(max_length=200, null=True, blank=True)
    
    class Meta:
        db_table = 'HH_Animal'
        verbose_name = _('Animal')
        verbose_name_plural = _('Animals')
        ordering = ['HHID', 'ANIMAL_TYPE']
        unique_together = [['HHID', 'ANIMAL_TYPE']]
        indexes = [
            models.Index(fields=['HHID', 'ANIMAL_TYPE'], name='idx_animal_hh_type'),
        ]
    
    def __str__(self):
        return f"{self.HHID_id} - {self.get_ANIMAL_TYPE_display()}"


# ==========================================
# QUERY HELPERS
# ==========================================
class HH_WaterTreatmentQuerySet(models.QuerySet):
    def adequate(self):
        """Get adequate treatment methods (boiling or filtration)"""
        return self.filter(TREATMENT_TYPE__in=['boiling', 'filter_machine'])


# Attach querysets
HH_WaterTreatment.add_to_class('objects', HH_WaterTreatmentQuerySet.as_manager())


# ==========================================
# 7. FOOD FREQUENCY - SIMPLIFIED
# ==========================================
class HH_FoodFrequency(AuditFieldsMixin):
    """Food consumption frequency"""
    
    class FrequencyChoices(models.TextChoices):
        NEVER = 'never', _('Never')
        MONTHLY_1_3 = '1-3/month', _('1-3 times/month')
        WEEKLY_1_2 = '1-2/week', _('1-2 times/week')
        WEEKLY_3_5 = '3-5/week', _('3-5 times/week')
        DAILY_1 = '1/day', _('1 time/day')
        DAILY_2_PLUS = '2+/day', _('2+ times/day')
    
    HHID = models.OneToOneField('HH_CASE', on_delete=models.CASCADE, primary_key=True, to_field='HHID', db_column='HHID', related_name='food_frequency')
    
    # FOOD CATEGORIES
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
        db_table = 'HH_FoodFrequency'
        verbose_name = _('Food Frequency')
        verbose_name_plural = _('Food Frequencies')
    
    def __str__(self):
        return f"Food Freq: {self.HHID_id}"


# ==========================================
# 8. FOOD SOURCE - SIMPLIFIED
# ==========================================
class HH_FoodSource(AuditFieldsMixin):
    """Food source frequency"""
    
    class FrequencyChoices(models.TextChoices):
        NEVER = 'never', _('Never')
        MONTHLY_1_3 = '1-3/month', _('1-3 times/month')
        WEEKLY_1_2 = '1-2/week', _('1-2 times/week')
        WEEKLY_3_5 = '3-5/week', _('3-5 times/week')
        DAILY_1 = '1/day', _('1 time/day')
        DAILY_2_PLUS = '2+/day', _('2+ times/day')
    
    HHID = models.OneToOneField('HH_CASE', on_delete=models.CASCADE, primary_key=True, to_field='HHID', db_column='HHID', related_name='food_source')
    
    # FOOD SOURCES
    TRADITIONAL_MARKET = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    SUPERMARKET = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    CONVENIENCE_STORE = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    RESTAURANT = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    ONLINE = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    SELF_GROWN = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    GIFTED = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    OTHER = models.CharField(max_length=15, choices=FrequencyChoices.choices, null=True, blank=True)
    OTHER_SPECIFY = models.CharField(max_length=200, null=True, blank=True)
    
    class Meta:
        db_table = 'HH_FoodSource'
        verbose_name = _('Food Source')
        verbose_name_plural = _('Food Sources')
    
    def __str__(self):
        return f"Food Source: {self.HHID_id}"


# ==========================================
# QUERY HELPERS - MINIMAL
# ==========================================
class HH_CASEQuerySet(models.QuerySet):
    def with_relations(self):
        return self.select_related('exposure', 'food_frequency', 'food_source').prefetch_related('members', 'exposure__water_sources', 'exposure__animals')
    
    def by_ward(self, ward):
        return self.filter(WARD__iexact=ward)
    
    def recent(self, days=30):
        from datetime import date, timedelta
        return self.filter(last_modified_at__gte=date.today() - timedelta(days=days))


class HH_MemberQuerySet(models.QuerySet):
    def respondents(self):
        return self.filter(ISRESPONDENT=True)
    
    def by_household(self, hhid):
        return self.filter(HHID=hhid).order_by('MEMBER_NUM')
    
    def children_only(self):
        return self.filter(RELATIONSHIP='D').order_by('HHID', 'CHILD_ORDER')


class HH_WaterSourceQuerySet(models.QuerySet):
    def drinking(self):
        return self.filter(DRINKING=True)
    
    def safe_sources(self):
        return self.filter(SOURCE_TYPE__in=['tap', 'bottled'])


class HH_AnimalQuerySet(models.QuerySet):
    def livestock(self):
        return self.filter(ANIMAL_TYPE__in=['cow', 'poultry'])


# Attach querysets
HH_CASE.add_to_class('objects', HH_CASEQuerySet.as_manager())
HH_Member.add_to_class('objects', HH_MemberQuerySet.as_manager())
HH_WaterSource.add_to_class('objects', HH_WaterSourceQuerySet.as_manager())
HH_Animal.add_to_class('objects', HH_AnimalQuerySet.as_manager())