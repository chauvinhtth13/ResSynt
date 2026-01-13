# backends/studies/study_43en/forms/Discharge.py

from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from backends.studies.study_43en.models.patient import (
    DISCH_CASE,
    DischargeICD
)


# ==========================================
# DISCHARGE CASE FORM (MAIN)
# ==========================================

class DischargeCaseForm(forms.ModelForm):
    """
    Main discharge form
    
    Optimizations:
    - Simplified validation (only essential checks)
    - Auto-populate header fields
    - RadioSelect for Yes/No fields
    - Clean widget configuration
    - Uses model verbose_name for labels
    """
    
    #  RadioSelect for better UX (uses model choices)
    TRANSFERHOSP = forms.ChoiceField(
        choices=DISCH_CASE.YesNoNAChoices.choices,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial=DISCH_CASE.YesNoNAChoices.NO,
        required=True,
        # Label will be taken from model's verbose_name
    )
    
    DEATHATDISCH = forms.ChoiceField(
        choices=DISCH_CASE.YesNoNAChoices.choices,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial=DISCH_CASE.YesNoNAChoices.NO,
        required=True,
        # Label will be taken from model's verbose_name
    )
    
    class Meta:
        model = DISCH_CASE
        exclude = ['USUBJID']  # Set by view
        widgets = {
            #  Readonly header fields (auto-populated from ENR_CASE)
            'EVENT': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'STUDYID': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'SITEID': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'SUBJID': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'INITIAL': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            
            #  Date picker
            'DISCHDATE': forms.DateInput(format='%d/%m/%Y', attrs={
                'class': 'datepicker form-control',
                'placeholder': 'DD/MM/YYYY'
            }),
            
            #  Discharge status
            'DISCHSTATUS': forms.Select(attrs={
                'class': 'form-control select2'
            }),
            'DISCHSTATUSDETAIL': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Discharge status details...')
            }),
            
            #  Transfer info
            'TRANSFERREASON': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('Reason for transfer...')
            }),
            'TRANSFERLOCATION': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Name of receiving hospital')
            }),
            
            #  Death info
            'DEATHCAUSE': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Cause of death...')
            }),
        }
        #  REMOVED labels - will use model's verbose_name
        # This ensures consistency between forms and display
    
    def __init__(self, *args, patient=None, **kwargs):
        """
        Initialize form with patient context for validation
        
        Args:
            patient: ENR_CASE instance (optional)
        """
        #  Auto-detect patient from instance if not provided
        if patient is None and 'instance' in kwargs and kwargs['instance']:
            patient = getattr(kwargs['instance'], 'USUBJID', None)
        
        self.patient = patient
        super().__init__(*args, **kwargs)
        
        # Set input_formats for date field (DD/MM/YYYY)
        if 'DISCHDATE' in self.fields:
            self.fields['DISCHDATE'].input_formats = ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
        
        #  Set labels from model verbose_name for radio fields
        # (since they're custom fields, need manual assignment)
        self.fields['TRANSFERHOSP'].label = DISCH_CASE._meta.get_field('TRANSFERHOSP').verbose_name
        self.fields['DEATHATDISCH'].label = DISCH_CASE._meta.get_field('DEATHATDISCH').verbose_name
        
        #  Make all fields optional initially (validation in clean())
        for field_name, field in self.fields.items():
            if field_name not in ['TRANSFERHOSP', 'DEATHATDISCH']:
                field.required = False
        
        #  Set initial values for radio fields
        if self.instance and self.instance.pk:
            self.fields['TRANSFERHOSP'].initial = self.instance.TRANSFERHOSP or DISCH_CASE.YesNoNAChoices.NO
            self.fields['DEATHATDISCH'].initial = self.instance.DEATHATDISCH or DISCH_CASE.YesNoNAChoices.NO
        else:
            # Default values for new records
            self.fields['TRANSFERHOSP'].initial = DISCH_CASE.YesNoNAChoices.NO
            self.fields['DEATHATDISCH'].initial = DISCH_CASE.YesNoNAChoices.NO
            self.fields['EVENT'].initial = 'DISCHARGE'
    
    def clean(self):
        """
         SIMPLIFIED validation - only essential checks
        Model.clean() handles complex business logic
        """
        cleaned_data = super().clean()
        errors = {}
        
        #  Validate discharge date against enrollment (if patient available)
        dischdate = cleaned_data.get('DISCHDATE')
        if dischdate and self.patient:
            enr_date = getattr(self.patient, 'ENRDATE', None)
            if enr_date and dischdate < enr_date:
                errors['DISCHDATE'] = _(
                    'Discharge date cannot be before enrollment date ({enr_date})'
                ).format(enr_date=enr_date.strftime('%d/%m/%Y'))
        
        #  Validate transfer info (only if Yes)
        transferred = cleaned_data.get('TRANSFERHOSP')
        if transferred == DISCH_CASE.YesNoNAChoices.YES:
            if not cleaned_data.get('TRANSFERREASON') and not cleaned_data.get('TRANSFERLOCATION'):
                errors['TRANSFERREASON'] = _(
                    'Please enter transfer reason or location'
                )
        
        #  Validate death info (only if Yes)
        died = cleaned_data.get('DEATHATDISCH')
        if died == DISCH_CASE.YesNoNAChoices.YES:
            if not cleaned_data.get('DEATHCAUSE') or not cleaned_data.get('DEATHCAUSE').strip():
                errors['DEATHCAUSE'] = _('Please enter cause of death')
        
        if errors:
            raise ValidationError(errors)
        
        #  Let Model.clean() handle the rest (status consistency, etc.)
        return cleaned_data


# ==========================================
# DISCHARGE ICD FORM (1-N with DISCH_CASE)
# ==========================================

class DischargeICDForm(forms.ModelForm):
    """
    Form for individual ICD-10 code
    
    Features:
    - Auto-generated sequence number (readonly)
    - Simple ICD code input
    - Optional diagnosis details
    - Uses model verbose_name for labels
    """
    
    class Meta:
        model = DischargeICD
        fields = ['ICD_SEQUENCE', 'ICDCODE', 'ICDDETAIL']
        widgets = {
            'ICD_SEQUENCE': forms.NumberInput(attrs={
                'class': 'form-control',
                'readonly': True,
                'placeholder': 'Auto-generated'
            }),
            'ICDCODE': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., A41.5, J18.9')
            }),
            'ICDDETAIL': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('Diagnosis details (optional)')
            }),
        }
        #  REMOVED labels - will use model's verbose_name
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        #  ICD_SEQUENCE is auto-generated, not required from user
        self.fields['ICD_SEQUENCE'].required = False
        
        #  ICDDETAIL is optional
        self.fields['ICDDETAIL'].required = False
        
        #  Copy help_text from model to form field (if available)
        for field_name in self.fields:
            model_field = self.Meta.model._meta.get_field(field_name)
            if hasattr(model_field, 'help_text') and model_field.help_text:
                self.fields[field_name].help_text = model_field.help_text
    
    def clean(self):
        """
         SIMPLIFIED validation - only if row has data
        """
        cleaned_data = super().clean()
        
        # Check if this row has any data
        has_data = any([
            cleaned_data.get('ICDCODE'),
            cleaned_data.get('ICDDETAIL')
        ])
        
        # If row has data, ICDCODE is required
        if has_data:
            icdcode = cleaned_data.get('ICDCODE')
            if not icdcode or not icdcode.strip():
                raise ValidationError({
                    'ICDCODE': _('ICD-10 code is required when adding diagnosis')
                })
        
        #  No strict ICD format validation - let users input freely
        # Model.clean() can handle format validation if needed
        
        return cleaned_data
    
    def clean_ICDCODE(self):
        """ Normalize ICD code (uppercase, strip whitespace)"""
        value = self.cleaned_data.get('ICDCODE')
        if value:
            return value.strip().upper()
        return value
    
    def clean_ICDDETAIL(self):
        """ Normalize diagnosis details"""
        value = self.cleaned_data.get('ICDDETAIL')
        if value:
            return value.strip()
        return value


# ==========================================
# DISCHARGE ICD FORMSET
# ==========================================

class BaseDischargeICDFormSet(forms.BaseInlineFormSet):
    """
    Base formset for DischargeICD with auto-sequencing
    
     SIMPLIFIED: No complex validation
     Auto-increment ICD_SEQUENCE for new forms
    """
    
    def add_fields(self, form, index):
        """ Auto-set ICD_SEQUENCE ONLY for new forms"""
        super().add_fields(form, index)
        
        #  Only set sequence for forms WITHOUT pk (new forms)
        if not form.instance.pk:
            # Calculate max ICD_SEQUENCE from DATABASE (not from forms)
            max_sequence = 0
            if self.instance and self.instance.pk:
                # Get max from SAVED instances only
                existing_sequences = self.instance.icd_codes.values_list('ICD_SEQUENCE', flat=True)
                if existing_sequences:
                    max_sequence = max(existing_sequences)
            
            # Set initial for new form
            form.fields['ICD_SEQUENCE'].initial = max_sequence + 1
            form.initial['ICD_SEQUENCE'] = max_sequence + 1
    
    def clean(self):
        """
         OPTIONAL: Formset-level validation
        Only warn about duplicates, don't block
        """
        if any(self.errors):
            return
        
        #  Optional: Check duplicate ICD codes (warning only)
        icd_codes = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE'):
                icd_code = form.cleaned_data.get('ICDCODE')
                if icd_code and icd_code.strip():
                    code_normalized = icd_code.strip().upper()
                    if code_normalized in icd_codes:
                        #  Just warning, don't raise error
                        # Users might want to add same ICD with different details
                        pass
                    else:
                        icd_codes.append(code_normalized)


# ==========================================
# CREATE FORMSET
# ==========================================

DischargeICDFormSet = forms.inlineformset_factory(
    DISCH_CASE,
    DischargeICD,
    form=DischargeICDForm,
    formset=BaseDischargeICDFormSet,
    extra=1,  # Show 1 empty form for adding
    can_delete=False,  #  REMOVED: No DELETE
    min_num=0,  #  ICD codes are optional
    validate_min=False,
    max_num=6,  #  Reasonable limit (1 primary + 5 secondary diagnoses)
    validate_max=True
)