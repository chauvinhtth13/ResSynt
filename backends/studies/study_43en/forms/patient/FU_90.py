from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from backends.studies.study_43en.models import (
    FU_CASE_90,
    Rehospitalization90,
    FollowUpAntibiotic90
)


# ==========================================
# FOLLOW-UP DAY 90 MAIN FORM
# ==========================================

class FollowUpCase90Form(forms.ModelForm):
    """
    Form for FU_CASE_90 model (Day 90)
     UPDATED: Field names and labels match model
    """

    #  UPDATED: Field names match new model fields
    EvaluatedAtDay90 = forms.ChoiceField(
        choices=[('No', 'No'), ('Yes', 'Yes'), ('NA', 'Not Applicable')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='No',
        required=True,
        label=_("1. The patient's condition was assessed on Day 90?")
    )
    
    Rehospitalized = forms.ChoiceField(
        choices=[('No', 'No'), ('Yes', 'Yes'), ('NA', 'Not Applicable')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='No',
        required=False,
        label=_('2. Patients readmitted to hospital?')
    )
    
    Dead = forms.ChoiceField(
        choices=[('No', 'No'), ('Yes', 'Yes'), ('NA', 'Not Applicable')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='No',
        required=True,
        label=_('3. Patient death?')
    )
    
    Antb_Usage = forms.ChoiceField(
        choices=[('No', 'No'), ('Yes', 'Yes'), ('NA', 'Not Applicable')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='No',
        required=False,
        label=_('4. Did the patient use antibiotics since the last visit?')
    )
    
    Func_Status = forms.ChoiceField(
        choices=[('No', 'No'), ('Yes', 'Yes'), ('NA', 'Not Applicable')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='No',
        required=False,
        label=_('5. Assessment of Functional Status at Day 90?')
    )

    class Meta:
        model = FU_CASE_90
        #  UPDATED: Field names match new model
        fields = [
            'EvaluatedAtDay90', 'EvaluateDate', 'Outcome90Days',
            'Rehospitalized', 'ReHosp_Times',
            'Dead', 'DeathDate', 'DeathReason',
            'Antb_Usage', 'Antb_Usage_Times',
            'Func_Status', 'Mobility', 'Personal_Hygiene',
            'Daily_Activities', 'Pain_Discomfort', 'Anxiety',
            'FBSI'
        ]
        widgets = {
            'EvaluateDate': forms.DateInput(
                attrs={
                    'class': 'datepicker form-control',
                    'placeholder': 'DD/MM/YYYY'
                }
            ),
            'DeathDate': forms.DateInput(
                attrs={
                    'class': 'datepicker form-control',
                    'placeholder': 'DD/MM/YYYY'
                }
            ),
            'Outcome90Days': forms.Select(
                attrs={
                    'class': 'form-control select2'
                }
            ),
            'DeathReason': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Cause of death...'
                }
            ),
            'FBSI': forms.Select(
                attrs={
                    'class': 'form-control select2'
                }
            ),
            'Mobility': forms.RadioSelect(
                attrs={
                    'class': 'form-check-input'
                }
            ),
            'Personal_Hygiene': forms.RadioSelect(
                attrs={
                    'class': 'form-check-input'
                }
            ),
            'Daily_Activities': forms.RadioSelect(
                attrs={
                    'class': 'form-check-input'
                }
            ),
            'Pain_Discomfort': forms.RadioSelect(
                attrs={
                    'class': 'form-check-input'
                }
            ),
            'Anxiety': forms.RadioSelect(
                attrs={
                    'class': 'form-check-input'
                }
            ),
        }
        labels = {
            # Match verbose_name from model exactly
            'EvaluateDate': _('a. Date (dd/mm/yyyy)'),
            'Outcome90Days': _('b. Status'),
            'ReHosp_Times': _('a. How many times?'),
            'DeathDate': _('a. Date (dd/mm/yyyy)'),
            'DeathReason': _('b. Reason'),
            'Antb_Usage_Times': _('a. How many times?'),
            'Mobility': _('5a. Mobility (walking)'),
            'Personal_Hygiene': _('5b. Self-care (washing, dressing)'),
            'Daily_Activities': _('5c. Daily activities (work, study, housework, leisure activities)'),
            'Pain_Discomfort': _('5d. Pain/Discomfort'),
            'Anxiety': _('5e. Anxiety/Depression'),
            'FBSI': _('5f. Functional Bloodstream Infection Score (FBSI)'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make all fields optional by default (validation will be in clean())
        radio_fields = ['EvaluatedAtDay90', 'Rehospitalized', 'Dead', 'Antb_Usage', 'Func_Status']
        for field_name, field in self.fields.items():
            if field_name not in radio_fields:
                field.required = False

        # Set initial values for radio fields
        if self.instance and self.instance.pk:
            for field_name in radio_fields:
                current_value = getattr(self.instance, field_name, None)
                self.fields[field_name].initial = current_value if current_value else 'No'
        else:
            for field_name in radio_fields:
                self.fields[field_name].initial = 'No'

    def clean(self):
        """
        Enhanced validation with field dependencies (same as Day 28)
        """
        cleaned_data = super().clean()
        errors = {}

        # Validate EvaluatedAtDay90 dependencies
        evaluated = cleaned_data.get('EvaluatedAtDay90')
        if evaluated == 'Yes':
            if not cleaned_data.get('EvaluateDate'):
                errors['EvaluateDate'] = _('Evaluation date is required when patient is assessed')
        
        # Validate Dead dependencies
        dead = cleaned_data.get('Dead')
        if dead == 'Yes':
            if not cleaned_data.get('DeathDate'):
                errors['DeathDate'] = _('Death date is required when patient died')
            if not cleaned_data.get('DeathReason') or not cleaned_data.get('DeathReason').strip():
                errors['DeathReason'] = _('Death reason is required when patient died')
            
            # FBSI score must be 0 when deceased
            fbsi = cleaned_data.get('FBSI')
            if fbsi is not None and fbsi != 0:
                errors['FBSI'] = _('FBSI score must be 0 when patient died')
        
        if errors:
            raise ValidationError(errors)

        return cleaned_data


# ==========================================
# REHOSPITALIZATION FORM (DAY 90)
# ==========================================

class Rehospitalization90Form(forms.ModelForm):
    """
    Form for Rehospitalization90 records (Day 90)
     UPDATED: Field names and labels match model
    """
    
    class Meta:
        model = Rehospitalization90
        #  UPDATED: New field names
        fields = ['REHOSP_No', 'ReHospDate', 'ReHospReason', 'ReHospLocate', 'REHOSPDAYS']
        widgets = {
            'REHOSP_No': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'readonly': True,
                    'placeholder': 'Auto-generated'
                }
            ),
            'ReHospDate': forms.DateInput(
                attrs={
                    'class': 'datepicker form-control',
                    'placeholder': 'DD/MM/YYYY'
                }
            ),
            'ReHospReason': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 2,
                    'placeholder': 'Reason for readmission...'
                }
            ),
            'ReHospLocate': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Hospital location'
                }
            ),
            'REHOSPDAYS': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Duration (e.g., 5 days)'
                }
            ),
        }
        labels = {
            # Match verbose_name from model exactly
            'REHOSP_No': _('No.'),
            'ReHospDate': _('Readmitted Date'),
            'ReHospReason': _('Reason'),
            'ReHospLocate': _('Hospital'),
            'REHOSPDAYS': _('Duration'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['REHOSP_No'].required = False
        
        for field_name in self.fields:
            self.fields[field_name].required = False


# ==========================================
# ANTIBIOTIC FORM (DAY 90)
# ==========================================

class FollowUpAntibiotic90Form(forms.ModelForm):
    """
    Form for FollowUpAntibiotic90 records (Day 90)
     UPDATED: Field names and labels match model
    """
    
    class Meta:
        model = FollowUpAntibiotic90
        #  UPDATED: New field names
        fields = ['Antb_Usage_No', 'Antb_Name', 'Antb_Usage_Reason', 'Antb_Usage_Date']
        widgets = {
            'Antb_Usage_No': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'readonly': True,
                    'placeholder': 'Auto-generated'
                }
            ),
            'Antb_Name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Antibiotic name (required if adding row)'
                }
            ),
            'Antb_Usage_Reason': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 2,
                    'placeholder': 'Reason for use...'
                }
            ),
            'Antb_Usage_Date': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Duration (e.g., 7 days)'
                }
            ),
        }
        labels = {
            # Match verbose_name from model exactly
            'Antb_Usage_No': _('No.'),
            'Antb_Name': _('Antibiotics Name'),
            'Antb_Usage_Reason': _('Reason'),
            'Antb_Usage_Date': _('Duration'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['Antb_Usage_No'].required = False
        
        for field_name in self.fields:
            self.fields[field_name].required = False
    
    def clean(self):
        """
        Validate that if any data is entered, Antb_Name must be provided
        """
        cleaned_data = super().clean()
        
        # Check if this row has any data
        has_data = any([
            cleaned_data.get('Antb_Name'),
            cleaned_data.get('Antb_Usage_Reason'),
            cleaned_data.get('Antb_Usage_Date')
        ])
        
        # If row has data, Antb_Name is required
        if has_data:
            antb_name = cleaned_data.get('Antb_Name')
            if not antb_name or not antb_name.strip():
                raise ValidationError({
                    'Antb_Name': _('Antibiotic name is required when adding antibiotic information')
                })
        
        return cleaned_data


# ==========================================
# BASE FORMSETS (DAY 90)
# ==========================================

class BaseRehospitalization90FormSet(forms.BaseInlineFormSet):
    """
    Base formset for Rehospitalization90 with auto episode numbering
     UPDATED: Use new field name REHOSP_No
    """
    
    def add_fields(self, form, index):
        """Auto-set episode number ONLY for new forms"""
        super().add_fields(form, index)
        
        #  CRITICAL: Only set REHOSP_No for forms WITHOUT pk (new forms)
        if not form.instance.pk:
            # Calculate max REHOSP_No from DATABASE (not from forms)
            max_episode = 0
            if self.instance and self.instance.pk:
                # Get max from SAVED instances only
                existing_episodes = self.instance.rehospitalizations.values_list('REHOSP_No', flat=True)
                if existing_episodes:
                    max_episode = max(existing_episodes)
            
            # Set initial for new form
            form.fields['REHOSP_No'].initial = max_episode + 1
            form.initial['REHOSP_No'] = max_episode + 1
    
    def clean(self):
        """
        Validate formset-level rules
        - Check for duplicate dates
        """
        if any(self.errors):
            return
        
        dates = []
        
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                rehospdate = form.cleaned_data.get('ReHospDate')
                if rehospdate:
                    if rehospdate in dates:
                        raise ValidationError(
                            _('Multiple readmissions on the same date are not allowed')
                        )
                    dates.append(rehospdate)
        
        return super().clean()


class BaseFollowUpAntibiotic90FormSet(forms.BaseInlineFormSet):
    """
    Base formset for FollowUpAntibiotic90 with auto episode numbering
     UPDATED: Use new field name Antb_Usage_No
    """
    
    def add_fields(self, form, index):
        """Auto-set episode number ONLY for new forms"""
        super().add_fields(form, index)
        
        #  CRITICAL: Only set Antb_Usage_No for forms WITHOUT pk (new forms)
        if not form.instance.pk:
            # Calculate max Antb_Usage_No from DATABASE (not from forms)
            max_episode = 0
            if self.instance and self.instance.pk:
                # Get max from SAVED instances only
                existing_episodes = self.instance.antibiotics.values_list('Antb_Usage_No', flat=True)
                if existing_episodes:
                    max_episode = max(existing_episodes)
            
            # Set initial for new form
            form.fields['Antb_Usage_No'].initial = max_episode + 1
            form.initial['Antb_Usage_No'] = max_episode + 1
    
    def clean(self):
        """
        Validate formset-level rules
        - Check for duplicate antibiotic names
        """
        if any(self.errors):
            return
        
        antibiotic_names = []
        
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                antb_name = form.cleaned_data.get('Antb_Name')
                if antb_name and antb_name.strip():
                    name_lower = antb_name.strip().lower()
                    if name_lower in antibiotic_names:
                        raise ValidationError(
                            _('Warning: Antibiotic "{}" appears multiple times').format(antb_name)
                        )
                    antibiotic_names.append(name_lower)
        
        return super().clean()


# ==========================================
# CREATE FORMSETS (DAY 90)
# ==========================================

Rehospitalization90FormSet = forms.inlineformset_factory(
    FU_CASE_90,
    Rehospitalization90,
    form=Rehospitalization90Form,
    formset=BaseRehospitalization90FormSet,
    extra=1,
    can_delete=False,
    min_num=0,
    validate_min=False,
    max_num=10,
    validate_max=True
)

FollowUpAntibiotic90FormSet = forms.inlineformset_factory(
    FU_CASE_90,
    FollowUpAntibiotic90,
    form=FollowUpAntibiotic90Form,
    formset=BaseFollowUpAntibiotic90FormSet,
    extra=1,
    can_delete=False,
    min_num=0,
    validate_min=False,
    max_num=20,
    validate_max=True
)