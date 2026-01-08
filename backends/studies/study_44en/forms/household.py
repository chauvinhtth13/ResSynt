# backends/studies/study_44en/forms/household.py

from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory, BaseInlineFormSet
from datetime import date

from backends.studies.study_44en.models import (
    HH_CASE,
    HH_Member,
    HH_Exposure,
    HH_WaterSource,
    HH_WaterTreatment,
    HH_Animal,
    HH_FoodFrequency,
    HH_FoodSource,
)


# ==========================================
# 1. HH_CASE FORM - Main Household
# ==========================================

class HH_CASEForm(forms.ModelForm):
    """Main household information form"""
    
    class Meta:
        model = HH_CASE
        fields = '__all__'
        widgets = {
            # Basic Info
            'HHID': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'placeholder': 'Auto-generated'
            }),
            'RESPONDENT_MEMBER_NUM': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10
            }),
            
            
            # Household Composition
            'TOTAL_MEMBERS': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10
            }),
            'MONTHLY_INCOME': forms.Select(attrs={'class': 'form-select'}),
            
            # Housing
            'OWNERSHIP': forms.Select(attrs={'class': 'form-select'}),
            'LAND_AREA': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 0.1
            }),
            'NUM_FLOORS': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10
            }),
            'NUM_ROOMS': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 20
            }),
            'HOUSING_TYPE': forms.Select(attrs={'class': 'form-select'}),
            'FLOOR_MATERIAL': forms.Select(attrs={'class': 'form-select'}),
            'ROOF_MATERIAL': forms.Select(attrs={'class': 'form-select'}),
            
            # Assets (BooleanFields)
            'TV': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'AC': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'COMPUTER': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'REFRIGERATOR': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'INTERNET': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'WASHING_MACHINE': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'MOBILE_PHONE': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'WATER_HEATER': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'BICYCLE': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'GAS_STOVE': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'MOTORCYCLE': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'INDUCTION_COOKER': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'CAR': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'RICE_COOKER': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # HHID is auto-generated, so not required for new instances
        if not self.instance.pk:
            self.fields['HHID'].required = False
    
    def clean(self):
        """Validate household data"""
        cleaned_data = super().clean()
        total_members = cleaned_data.get('TOTAL_MEMBERS')
        respondent_num = cleaned_data.get('RESPONDENT_MEMBER_NUM')
        
        # Validate respondent is within member range
        if total_members and respondent_num:
            if respondent_num > total_members:
                raise ValidationError({
                    'RESPONDENT_MEMBER_NUM': _('Respondent number cannot exceed total members')
                })
        
        return cleaned_data


# ==========================================
# 2. HH_MEMBER FORM - Household Members
# ==========================================

class HH_MemberForm(forms.ModelForm):
    """Household member form"""
    
    class Meta:
        model = HH_Member
        fields = '__all__'  # Include all fields including MEMBERID
        widgets = {
            'MEMBERID': forms.HiddenInput(),  # Hidden field, auto-generated if empty
            'MEMBER_NUM': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10
            }),
            'RELATIONSHIP': forms.Select(attrs={'class': 'form-select'}),
            'CHILD_ORDER': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10
            }),
            'BIRTH_YEAR': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'YYYY',
                'pattern': '[0-9]{4}',
                'maxlength': 4
            }),
            'GENDER': forms.Select(attrs={'class': 'form-select'}),
            'ISRESPONDENT': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # MEMBERID is auto-generated, not required from user (if field exists)
        if 'MEMBERID' in self.fields:
            self.fields['MEMBERID'].required = False
        # Make other fields optional for empty forms
        self.fields['CHILD_ORDER'].required = False
        self.fields['RELATIONSHIP'].required = False
        self.fields['BIRTH_YEAR'].required = False
        self.fields['GENDER'].required = False
        self.fields['ISRESPONDENT'].required = False
    
    def has_changed(self):
        """Check if form has any meaningful data"""
        if not self.is_bound:
            return False
        
        # Check significant fields
        significant_fields = ['RELATIONSHIP', 'BIRTH_YEAR', 'GENDER']
        for field in significant_fields:
            if self.data.get(self.add_prefix(field)):
                return True
        return False
    
    def clean_MEMBERID(self):
        """Allow blank MEMBERID - will be auto-generated"""
        return self.cleaned_data.get('MEMBERID', '')
    
    def clean(self):
        """Only validate if form has data"""
        cleaned_data = super().clean()
        
        # Check if form has any significant data
        has_data = any([
            cleaned_data.get('RELATIONSHIP'),
            cleaned_data.get('BIRTH_YEAR'),
            cleaned_data.get('GENDER')
        ])
        
        # If form has some data, require all fields
        if has_data:
            required_fields = ['RELATIONSHIP', 'GENDER']
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, f'{field.replace("_", " ").title()} is required when adding a member')
        
        return cleaned_data


# ==========================================
# MEMBERID FORMSET
# ==========================================

class BaseHH_MemberFormSet(BaseInlineFormSet):
    """Custom formset for household members with validation"""
    
    def clean(self):
        """Validate member data"""
        if any(self.errors):
            return
        
        # Track member numbers to check for duplicates
        # Key: member_num, Value: list of form instances with that number
        member_num_tracking = {}
        respondent_count = 0
        respondent_forms = []
        
        for form in self.forms:
            # Skip empty forms
            if not self._has_data(form):
                continue
            
            if not form.cleaned_data or form.cleaned_data.get('DELETE', False):
                continue
            
            member_num = form.cleaned_data.get('MEMBER_NUM')
            is_respondent = form.cleaned_data.get('ISRESPONDENT')
            
            # Track member numbers
            if member_num:
                if member_num not in member_num_tracking:
                    member_num_tracking[member_num] = []
                member_num_tracking[member_num].append(form)
            
            # Track respondents
            if is_respondent:
                respondent_count += 1
                respondent_forms.append(form)
        
        # Check for duplicate member numbers (excluding same instance)
        for member_num, forms in member_num_tracking.items():
            if len(forms) > 1:
                # Multiple forms with same member_num - check if they're different instances
                unique_instances = set()
                for f in forms:
                    if f.instance.pk:
                        unique_instances.add(f.instance.pk)
                    else:
                        unique_instances.add(id(f))  # Use form object id for new forms
                
                # If more than 1 unique instance has same member_num, it's duplicate
                if len(unique_instances) > 1:
                    raise ValidationError(
                        _('Member number %(num)s is used multiple times'),
                        params={'num': member_num},
                        code='duplicate_member_num'
                    )
        
        # Check for multiple respondents (excluding same instance)
        if respondent_count > 1:
            # Check if they're different instances
            unique_respondents = set()
            for f in respondent_forms:
                if f.instance.pk:
                    unique_respondents.add(f.instance.pk)
                else:
                    unique_respondents.add(id(f))
            
            if len(unique_respondents) > 1:
                raise ValidationError(
                    _('Only one member can be marked as respondent'),
                    code='multiple_respondents'
                )
    
    def _has_data(self, form):
        """Check if form has any significant data"""
        if not form.is_bound:
            return bool(form.instance.pk)
        
        # For bound forms, check if any significant field has data
        significant_fields = ['RELATIONSHIP', 'BIRTH_YEAR', 'GENDER']
        for field in significant_fields:
            value = form.data.get(form.add_prefix(field))
            if value:
                return True
        return False
    
    def save(self, commit=True):
        """Save only forms with data"""
        # Filter out empty forms before saving
        saved_instances = []
        
        for form in self.forms:
            # Skip empty forms (but keep existing instances)
            if not self._has_data(form):
                continue
            
            # Skip deleted forms
            if form.cleaned_data.get('DELETE', False):
                if form.instance.pk:
                    form.instance.delete()
                continue
            
            # Save form with data (both new and existing)
            if form.is_valid():
                # For existing instances, always save even if not changed
                # For new instances, only save if has data
                if form.instance.pk or form.has_changed():
                    instance = form.save(commit=commit)
                    saved_instances.append(instance)
        
        return saved_instances

HH_MemberFormSet = inlineformset_factory(
    parent_model=HH_CASE,
    model=HH_Member,
    form=HH_MemberForm,
    formset=BaseHH_MemberFormSet,
    fields=['MEMBER_NUM', 'RELATIONSHIP', 'CHILD_ORDER', 'BIRTH_YEAR', 'GENDER', 'ISRESPONDENT'],
    extra=10,  # Show 10 members by default
    can_delete=True,
    can_delete_extra=True,
    min_num=0,
    validate_min=False,
    max_num=10,
    fk_name='HHID',
)


# ==========================================
# 3. HH_EXPOSURE FORM - Exposure Factors
# ==========================================

class HH_ExposureForm(forms.ModelForm):
    """Household exposure factors form"""
    
    class Meta:
        model = HH_Exposure
        fields = '__all__'
        widgets = {
            'HHID': forms.Select(attrs={'class': 'form-select'}),
            
            # Toilet
            'TOILET_TYPE': forms.Select(attrs={'class': 'form-select'}),
            'TOILET_TYPE_OTHER': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Specify other toilet type')
            }),
            'NUM_TOILETS': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 10
            }),
            
            # Cooking
            'COOKING_FUEL': forms.Select(attrs={'class': 'form-select'}),
            'COOKING_FUEL_OTHER': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Specify other fuel type')
            }),
            
            # Water
            'WATER_TREATMENT': forms.Select(attrs={'class': 'form-select'}),
            
            # Animals
            'RAISES_ANIMALS': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean(self):
        """Validate 'Other' specifications"""
        cleaned_data = super().clean()
        
        # Toilet type OTHER validation
        if cleaned_data.get('TOILET_TYPE') == 'other':
            if not cleaned_data.get('TOILET_TYPE_OTHER'):
                raise ValidationError({
                    'TOILET_TYPE_OTHER': _('Please specify other toilet type')
                })
        
        # Cooking fuel OTHER validation
        if cleaned_data.get('COOKING_FUEL') == 'other':
            if not cleaned_data.get('COOKING_FUEL_OTHER'):
                raise ValidationError({
                    'COOKING_FUEL_OTHER': _('Please specify other cooking fuel')
                })
        
        return cleaned_data


# ==========================================
# 4. INLINE FORMSETS - Water, Animals
# ==========================================

# Water Sources
HH_WaterSourceFormSet = inlineformset_factory(
    HH_Exposure,
    HH_WaterSource,
    fields=['SOURCE_TYPE', 'SOURCE_TYPE_OTHER', 'DRINKING', 'LIVING', 'IRRIGATION', 'OTHER', 'OTHER_PURPOSE'],
    extra=1,
    min_num=1,
    can_delete=True,
    widgets={
        'SOURCE_TYPE': forms.Select(attrs={'class': 'form-select'}),
        'SOURCE_TYPE_OTHER': forms.TextInput(attrs={'class': 'form-control'}),
        'DRINKING': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'LIVING': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'IRRIGATION': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'OTHER': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'OTHER_PURPOSE': forms.TextInput(attrs={'class': 'form-control'}),
    }
)

# Water Treatment
HH_WaterTreatmentFormSet = inlineformset_factory(
    HH_Exposure,
    HH_WaterTreatment,
    fields=['TREATMENT_TYPE', 'TREATMENT_TYPE_OTHER'],
    extra=1,
    max_num=6,
    can_delete=True,
    widgets={
        'TREATMENT_TYPE': forms.Select(attrs={'class': 'form-select'}),
        'TREATMENT_TYPE_OTHER': forms.TextInput(attrs={'class': 'form-control'}),
    }
)

# Animals
HH_AnimalFormSet = inlineformset_factory(
    HH_Exposure,
    HH_Animal,
    fields=['ANIMAL_TYPE', 'ANIMAL_TYPE_OTHER'],
    extra=1,
    max_num=6,
    can_delete=True,
    widgets={
        'ANIMAL_TYPE': forms.Select(attrs={'class': 'form-select'}),
        'ANIMAL_TYPE_OTHER': forms.TextInput(attrs={'class': 'form-control'}),
    }
)


# ==========================================
# 5. FOOD FORMS
# ==========================================

class HH_FoodFrequencyForm(forms.ModelForm):
    """Household food consumption frequency"""
    
    class Meta:
        model = HH_FoodFrequency
        fields = '__all__'
        widgets = {
            'HHID': forms.Select(attrs={'class': 'form-select'}),
            'RICE_NOODLES': forms.Select(attrs={'class': 'form-select'}),
            'RED_MEAT': forms.Select(attrs={'class': 'form-select'}),
            'POULTRY': forms.Select(attrs={'class': 'form-select'}),
            'FISH_SEAFOOD': forms.Select(attrs={'class': 'form-select'}),
            'EGGS': forms.Select(attrs={'class': 'form-select'}),
            'RAW_VEGETABLES': forms.Select(attrs={'class': 'form-select'}),
            'COOKED_VEGETABLES': forms.Select(attrs={'class': 'form-select'}),
            'DAIRY': forms.Select(attrs={'class': 'form-select'}),
            'FERMENTED': forms.Select(attrs={'class': 'form-select'}),
            'BEER': forms.Select(attrs={'class': 'form-select'}),
            'ALCOHOL': forms.Select(attrs={'class': 'form-select'}),
        }


class HH_FoodSourceForm(forms.ModelForm):
    """Household food sources"""
    
    class Meta:
        model = HH_FoodSource
        fields = '__all__'
        widgets = {
            'HHID': forms.Select(attrs={'class': 'form-select'}),
            'TRADITIONAL_MARKET': forms.Select(attrs={'class': 'form-select'}),
            'SUPERMARKET': forms.Select(attrs={'class': 'form-select'}),
            'CONVENIENCE_STORE': forms.Select(attrs={'class': 'form-select'}),
            'RESTAURANT': forms.Select(attrs={'class': 'form-select'}),
            'ONLINE': forms.Select(attrs={'class': 'form-select'}),
            'SELF_GROWN': forms.Select(attrs={'class': 'form-select'}),
            'GIFTED': forms.Select(attrs={'class': 'form-select'}),
            'OTHER': forms.Select(attrs={'class': 'form-select'}),
            'OTHER_SPECIFY': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Specify other source')
            }),
        }
    
    def clean(self):
        """Validate OTHER specification"""
        cleaned_data = super().clean()
        
        if cleaned_data.get('OTHER') and not cleaned_data.get('OTHER_SPECIFY'):
            raise ValidationError({
                'OTHER_SPECIFY': _('Please specify other food source')
            })
        
        return cleaned_data
