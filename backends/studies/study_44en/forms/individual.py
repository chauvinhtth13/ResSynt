# backends/studies/study_44en/forms/individual.py

from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from datetime import date

from backends.studies.study_44en.models import (
    Individual,
    Individual_Exposure,
    Individual_WaterSource,
    Individual_WaterTreatment,
    Individual_Comorbidity,
    Individual_Vaccine,
    Individual_Hospitalization,
    Individual_Medication,
    Individual_FoodFrequency,
    Individual_Travel,
    Individual_FollowUp,
    Individual_Symptom,
    Individual_Sample,
    FollowUp_Hospitalization,
)


# ==========================================
# 1. INDIVIDUAL FORM - Demographics
# ==========================================

class IndividualForm(forms.ModelForm):
    """Individual demographic information form"""
    
    class Meta:
        model = Individual
        fields = '__all__'
        widgets = {
            'MEMBER': forms.Select(attrs={'class': 'form-select'}),
            
            # Personal Info
            'INITIALS': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Name initials')
            }),
            'DATE_OF_BIRTH': forms.DateInput(attrs={
                'class': 'form-control datepicker',
                'placeholder': 'YYYY-MM-DD',
                'type': 'date'
            }),
            'AGE': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 150,
                'placeholder': _('Age (if DOB unknown)')
            }),
            
            # Demographics
            'ETHNICITY': forms.Select(attrs={'class': 'form-select'}),
            'ETHNICITY_OTHER': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Specify other ethnicity')
            }),
            'EDUCATION': forms.Select(attrs={'class': 'form-select'}),
            'OCCUPATION': forms.Select(attrs={'class': 'form-select'}),
            'OCCUPATION_OTHER': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Specify other occupation')
            }),
            
            # Economic
            'INDIVIDUAL_INCOME': forms.Select(attrs={'class': 'form-select'}),
            'HAS_HEALTH_INSURANCE': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make DATE_OF_BIRTH and AGE optional (but one must be provided)
        self.fields['DATE_OF_BIRTH'].required = False
        self.fields['AGE'].required = False
    
    def clean(self):
        """Validate demographics"""
        cleaned_data = super().clean()
        dob = cleaned_data.get('DATE_OF_BIRTH')
        age = cleaned_data.get('AGE')
        ethnicity = cleaned_data.get('ETHNICITY')
        ethnicity_other = cleaned_data.get('ETHNICITY_OTHER')
        occupation = cleaned_data.get('OCCUPATION')
        occupation_other = cleaned_data.get('OCCUPATION_OTHER')
        
        # Either DOB or AGE required
        if not dob and age is None:
            raise ValidationError(_('Either Date of Birth or Age must be provided'))
        
        # Ethnicity OTHER validation
        if ethnicity == 'other' and not ethnicity_other:
            raise ValidationError({
                'ETHNICITY_OTHER': _('Please specify other ethnicity')
            })
        
        # Occupation OTHER validation
        if occupation == 'other' and not occupation_other:
            raise ValidationError({
                'OCCUPATION_OTHER': _('Please specify other occupation')
            })
        
        return cleaned_data


# ==========================================
# 2. INDIVIDUAL_EXPOSURE FORMS - SPLIT BY SECTION
# ==========================================

class Individual_ExposureForm(forms.ModelForm):
    """Individual exposure factors form - EXP 1/3 (Water & Comorbidities)"""
    
    class Meta:
        model = Individual_Exposure
        fields = ['SHARED_TOILET', 'WATER_TREATMENT', 'HAS_COMORBIDITY']
        widgets = {
            'SHARED_TOILET': forms.Select(attrs={'class': 'form-select'}),
            'WATER_TREATMENT': forms.Select(attrs={'class': 'form-select'}),
            'HAS_COMORBIDITY': forms.Select(attrs={'class': 'form-select'}),
        }


class Individual_Exposure2Form(forms.ModelForm):
    """Individual exposure factors form - EXP 2/3 (Vaccination & Hospitalization)"""
    
    class Meta:
        model = Individual_Exposure
        fields = ['VACCINATION_STATUS', 'HOSPITALIZED_3M', 'MEDICATION_3M']
        widgets = {
            'VACCINATION_STATUS': forms.Select(attrs={'class': 'form-select'}),
            'HOSPITALIZED_3M': forms.Select(attrs={'class': 'form-select'}),
            'MEDICATION_3M': forms.Select(attrs={'class': 'form-select'}),
        }


# ==========================================
# 3. INLINE FORMSETS - Exposure Details
# ==========================================

# Water Sources
Individual_WaterSourceFormSet = inlineformset_factory(
    Individual_Exposure,
    Individual_WaterSource,
    fields=['SOURCE_TYPE', 'SOURCE_TYPE_OTHER', 'DRINKING', 'LIVING', 'IRRIGATION', 'FOR_OTHER', 'OTHER_PURPOSE'],
    extra=1,
    min_num=0,
    can_delete=True,
    widgets={
        'SOURCE_TYPE': forms.Select(attrs={'class': 'form-select'}),
        'SOURCE_TYPE_OTHER': forms.TextInput(attrs={'class': 'form-control'}),
        'DRINKING': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'LIVING': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'IRRIGATION': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'FOR_OTHER': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'OTHER_PURPOSE': forms.TextInput(attrs={'class': 'form-control'}),
    }
)

# Water Treatment
Individual_WaterTreatmentFormSet = inlineformset_factory(
    Individual_Exposure,
    Individual_WaterTreatment,
    fields=['TREATMENT_TYPE', 'TREATMENT_TYPE_OTHER'],
    extra=1,
    max_num=6,
    can_delete=True,
    widgets={
        'TREATMENT_TYPE': forms.Select(attrs={'class': 'form-select'}),
        'TREATMENT_TYPE_OTHER': forms.TextInput(attrs={'class': 'form-control'}),
    }
)

# Comorbidities
Individual_ComorbidityFormSet = inlineformset_factory(
    Individual_Exposure,
    Individual_Comorbidity,
    fields=['COMORBIDITY_TYPE', 'COMORBIDITY_OTHER', 'TREATMENT_STATUS'],
    extra=1,
    max_num=19,
    can_delete=True,
    widgets={
        'COMORBIDITY_TYPE': forms.Select(attrs={'class': 'form-select'}),
        'COMORBIDITY_OTHER': forms.TextInput(attrs={'class': 'form-control'}),
        'TREATMENT_STATUS': forms.Select(attrs={'class': 'form-select'}),
    }
)

# Vaccines
Individual_VaccineFormSet = inlineformset_factory(
    Individual_Exposure,
    Individual_Vaccine,
    fields=['VACCINE_TYPE', 'VACCINE_OTHER'],
    extra=1,
    max_num=19,
    can_delete=True,
    widgets={
        'VACCINE_TYPE': forms.Select(attrs={'class': 'form-select'}),
        'VACCINE_OTHER': forms.TextInput(attrs={'class': 'form-control'}),
    }
)

# Hospitalizations
Individual_HospitalizationFormSet = inlineformset_factory(
    Individual_Exposure,
    Individual_Hospitalization,
    fields=['HOSPITAL_TYPE', 'HOSPITAL_OTHER', 'DURATION'],
    extra=1,
    max_num=5,
    can_delete=True,
    widgets={
        'HOSPITAL_TYPE': forms.Select(attrs={'class': 'form-select'}),
        'HOSPITAL_OTHER': forms.TextInput(attrs={'class': 'form-control'}),
        'DURATION': forms.Select(attrs={'class': 'form-select'}),
    }
)

# Medications
Individual_MedicationFormSet = inlineformset_factory(
    Individual_Exposure,
    Individual_Medication,
    fields=['MEDICATION_TYPE', 'MEDICATION_DETAIL', 'DURATION'],
    extra=1,
    max_num=5,
    can_delete=True,
    widgets={
        'MEDICATION_TYPE': forms.Select(attrs={'class': 'form-select'}),
        'MEDICATION_DETAIL': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        'DURATION': forms.Select(attrs={'class': 'form-select'}),
    }
)


# ==========================================
# 4. FOOD FREQUENCY FORM
# ==========================================

class Individual_FoodFrequencyForm(forms.ModelForm):
    """Individual food consumption frequency"""
    
    class Meta:
        model = Individual_FoodFrequency
        exclude = ['MEMBER']  # MEMBER will be set in view
        widgets = {
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


# ==========================================
# 5. TRAVEL HISTORY FORMSET
# ==========================================

Individual_TravelFormSet = inlineformset_factory(
    Individual,
    Individual_Travel,
    fields=['TRAVEL_TYPE', 'FREQUENCY'],
    extra=1,
    max_num=10,
    can_delete=True,
    widgets={
        'TRAVEL_TYPE': forms.Select(attrs={'class': 'form-select'}),
        'FREQUENCY': forms.Select(attrs={'class': 'form-select'}),
    }
)


# ==========================================
# 6. FOLLOW-UP FORM
# ==========================================

class Individual_FollowUpForm(forms.ModelForm):
    """Individual follow-up visit form"""
    
    class Meta:
        model = Individual_FollowUp
        exclude = ['MEMBER']  # MEMBER will be set in view
        widgets = {
            'FOLLOW_UP_id': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'placeholder': 'Auto-generated'
            }),
            'VISIT_TIME': forms.Select(attrs={'class': 'form-select'}),
            
            # Assessment
            'ASSESSED': forms.Select(attrs={'class': 'form-select'}),
            'ASSESSMENT_DATE': forms.DateInput(attrs={
                'class': 'form-control datepicker',
                'type': 'date'
            }),
            
            # Symptoms
            'HAS_SYMPTOMS': forms.Select(attrs={'class': 'form-select'}),
            
            # Hospitalization
            'HOSPITALIZED': forms.Select(attrs={'class': 'form-select'}),
            
            # Medication
            'USED_MEDICATION': forms.Select(attrs={'class': 'form-select'}),
            'ANTIBIOTIC_TYPE': forms.Select(attrs={'class': 'form-select'}),
            'STEROID_TYPE': forms.Select(attrs={'class': 'form-select'}),
            'OTHER_MEDICATION': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Specify other medication')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ASSESSMENT_DATE'].required = False
    
    def clean(self):
        """Validate follow-up data"""
        cleaned_data = super().clean()
        assessed = cleaned_data.get('ASSESSED')
        assessment_date = cleaned_data.get('ASSESSMENT_DATE')
        has_symptoms = cleaned_data.get('HAS_SYMPTOMS')
        hospitalized = cleaned_data.get('HOSPITALIZED')
        used_medication = cleaned_data.get('USED_MEDICATION')
        antibiotic = cleaned_data.get('ANTIBIOTIC_TYPE')
        steroid = cleaned_data.get('STEROID_TYPE')
        other_med = cleaned_data.get('OTHER_MEDICATION')
        
        # Assessment date required if assessed
        if assessed == 'yes' and not assessment_date:
            raise ValidationError({
                'ASSESSMENT_DATE': _('Assessment date required when assessed=yes')
            })
        
        # No assessment date if not assessed
        if assessed == 'no' and assessment_date:
            raise ValidationError({
                'ASSESSMENT_DATE': _('Assessment date should be empty when assessed=no')
            })
        
        # Medication details required if used
        if used_medication == 'yes':
            if not antibiotic and not steroid and not other_med:
                raise ValidationError({
                    'OTHER_MEDICATION': _('Please specify medication type when used_medication=yes')
                })
        
        return cleaned_data


# Follow-up Symptoms
Individual_SymptomFormSet = inlineformset_factory(
    Individual_FollowUp,
    Individual_Symptom,
    fields=['SYMPTOM_TYPE', 'SYMPTOM_OTHER'],
    extra=1,
    max_num=19,
    can_delete=True,
    widgets={
        'SYMPTOM_TYPE': forms.Select(attrs={'class': 'form-select'}),
        'SYMPTOM_OTHER': forms.TextInput(attrs={'class': 'form-control'}),
    }
)

# Follow-up Hospitalizations
Individual_FollowUp_HospitalizationFormSet = inlineformset_factory(
    Individual_FollowUp,
    FollowUp_Hospitalization,
    fields=['HOSPITAL_TYPE', 'HOSPITAL_OTHER', 'DURATION'],
    extra=1,
    max_num=5,
    can_delete=True,
    widgets={
        'HOSPITAL_TYPE': forms.Select(attrs={'class': 'form-select'}),
        'HOSPITAL_OTHER': forms.TextInput(attrs={'class': 'form-control'}),
        'DURATION': forms.Select(attrs={'class': 'form-select'}),
    }
)


# ==========================================
# 7. SAMPLE COLLECTION FORM
# ==========================================

class Individual_SampleForm(forms.ModelForm):
    """Sample collection form"""
    
    class Meta:
        model = Individual_Sample
        exclude = ['MEMBER']  # MEMBER will be set in view
        widgets = {
            'SAMPLE_TIME': forms.Select(attrs={'class': 'form-select'}),
            'SAMPLE_COLLECTED': forms.Select(attrs={'class': 'form-select'}),
            'STOOL_DATE': forms.DateInput(attrs={
                'class': 'form-control datepicker',
                'type': 'date'
            }),
            'THROAT_SWAB_DATE': forms.DateInput(attrs={
                'class': 'form-control datepicker',
                'type': 'date'
            }),
            'NOT_COLLECTED_REASON': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Reason for not collecting')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['STOOL_DATE'].required = False
        self.fields['THROAT_SWAB_DATE'].required = False
        self.fields['NOT_COLLECTED_REASON'].required = False
    
    def clean(self):
        """Validate sample collection"""
        cleaned_data = super().clean()
        collected = cleaned_data.get('SAMPLE_COLLECTED')
        stool_date = cleaned_data.get('STOOL_DATE')
        throat_date = cleaned_data.get('THROAT_SWAB_DATE')
        reason = cleaned_data.get('NOT_COLLECTED_REASON')
        
        # If collected, need at least one date
        if collected == 'yes':
            if not stool_date and not throat_date:
                raise ValidationError(_('At least one sample date required when collected=yes'))
        
        # If not collected, need reason
        if collected == 'no' and not reason:
            raise ValidationError({
                'NOT_COLLECTED_REASON': _('Please provide reason for not collecting')
            })
        
        return cleaned_data
