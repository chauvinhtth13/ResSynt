from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from backends.studies.study_43en.models import (
    FU_CONTACT_28,
    FU_CONTACT_90,
    ContactMedicationHistory28,
    ContactMedicationHistory90
)


# ==========================================
# FOLLOW-UP DAY 28 MAIN FORM (CONTACT)
# ==========================================

class ContactFollowUp28Form(forms.ModelForm):
    """
    Form for FU_CONTACT_28 model
    
    Features:
    - RadioSelect for ASSESSED field
    - Date picker for assessment date
    - Checkboxes for healthcare exposures
    - English labels matching CRF form
    - Minimal validation (only essential checks)
    """

    ASSESSED = forms.ChoiceField(
        choices=[('No', 'No'), ('Yes', 'Yes'), ('NA', 'Not Applicable')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='No',
        required=True,
        label=_('Close contacts were assessed as of Day 28?')
    )

    class Meta:
        model = FU_CONTACT_28
        fields = [
            'ASSESSED', 'ASSESSDATE',
            'HOSP2D', 'DIAL', 'CATHETER', 'SONDE',
            'HOME_WOUND_CARE', 'LONG_TERM_CARE',
            'MEDICATION_USE'
        ]
        widgets = {
            'ASSESSDATE': forms.DateInput(
                attrs={
                    'class': 'datepicker form-control',
                    'placeholder': 'DD/MM/YYYY',
                    'autocomplete': 'off'
                }
            ),
            'HOSP2D': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'DIAL': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'CATHETER': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'SONDE': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'HOME_WOUND_CARE': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'LONG_TERM_CARE': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'MEDICATION_USE': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
        }
        labels = {
            'ASSESSDATE': _('a. Date (dd/mm/yyyy)'),
            'HOSP2D': _('a. Hospitalized ≥2 days in the 6 months before admission?'),
            'DIAL': _('b. Received regular dialysis in the 3 months before admission?'),
            'CATHETER': _('c. Had a central venous catheter placed in the 3 months before admission?'),
            'SONDE': _('d. Had an indwelling urinary catheter placed in the 3 months before admission?'),
            'HOME_WOUND_CARE': _('e. Received home wound care?'),
            'LONG_TERM_CARE': _('f. Residing in a long-term care facility?'),
            'MEDICATION_USE': _('History of medication use (corticoid, PPI, antibiotics)?'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make all fields optional by default (validation will be in clean())
        for field_name, field in self.fields.items():
            if field_name not in ['ASSESSED']:
                field.required = False

        # Set initial values for radio field
        if self.instance and self.instance.pk:
            current_value = getattr(self.instance, 'ASSESSED', None)
            self.fields['ASSESSED'].initial = current_value if current_value else 'No'
        else:
            self.fields['ASSESSED'].initial = 'No'

    def clean(self):
        """
        Enhanced validation with minimal checks
        Only validates essential field dependencies
        """
        cleaned_data = super().clean()
        errors = {}

        # Validate ASSESSED dependencies
        assessed = cleaned_data.get('ASSESSED')
        if assessed == 'Yes':
            if not cleaned_data.get('ASSESSDATE'):
                errors['ASSESSDATE'] = _('Assessment date is required when contact is assessed')
        
        if errors:
            raise ValidationError(errors)

        return cleaned_data



# ==========================================
# MEDICATION HISTORY FORM (DAY 28)
# ==========================================

class ContactMedicationHistory28Form(forms.ModelForm):
    """
    Form for ContactMedicationHistory28 model
    
    Features:
    - Auto-generated episode number (readonly)
    - Required medication name with validation
    - Optional dosage, usage period, and reason fields
    - Compact form controls for inline use
    """
    
    class Meta:
        model = ContactMedicationHistory28
        fields = ['EPISODE', 'MEDICATION_NAME', 'DOSAGE', 'USAGE_PERIOD', 'REASON']
        widgets = {
            'EPISODE': forms.NumberInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'readonly': True,
                    'placeholder': 'Auto'
                }
            ),
            'MEDICATION_NAME': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': 'Drug name (required if adding row)'
                }
            ),
            'DOSAGE': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': 'Dose'
                }
            ),
            'USAGE_PERIOD': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': 'Duration (e.g., 7 days)'
                }
            ),
            'REASON': forms.Textarea(
                attrs={
                    'class': 'form-control form-control-sm',
                    'rows': 2,
                    'placeholder': 'Reason for use...'
                }
            ),
        }
        labels = {
            'EPISODE': _('Episode'),
            'MEDICATION_NAME': _('Drug Name'),
            'DOSAGE': _('Dose'),
            'USAGE_PERIOD': _('Duration of Use'),
            'REASON': _('Reason for Use'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Episode is auto-generated, not required from user
        self.fields['EPISODE'].required = False
        
        # Make all fields optional initially (validated in clean)
        for field_name in self.fields:
            self.fields[field_name].required = False
    
    def clean(self):
        """
        Validate that if any data is entered, MEDICATION_NAME must be provided
        """
        cleaned_data = super().clean()
        
        # Check if this row has any data
        has_data = any([
            cleaned_data.get('MEDICATION_NAME'),
            cleaned_data.get('DOSAGE'),
            cleaned_data.get('USAGE_PERIOD'),
            cleaned_data.get('REASON')
        ])
        
        # If row has data, MEDICATION_NAME is required
        if has_data:
            MEDICATION_NAME = cleaned_data.get('MEDICATION_NAME')
            if not MEDICATION_NAME or not MEDICATION_NAME.strip():
                raise ValidationError({
                    'MEDICATION_NAME': _('Drug name is required when adding medication information')
                })
        
        return cleaned_data




# ==========================================
# BASE FORMSETS
# ==========================================

class BaseContactMedicationHistory28FormSet(forms.BaseInlineFormSet):
    """
    Base formset for ContactMedicationHistory28 with auto episode numbering
    
     FIXED: Only auto-increment for NEW forms (no pk)
     FIXED: Don't touch existing forms during UPDATE
    """
    
    def add_fields(self, form, index):
        """Auto-set episode number ONLY for new forms"""
        super().add_fields(form, index)
        
        #  CRITICAL: Only set EPISODE for forms WITHOUT pk (new forms)
        if not form.instance.pk:
            # Calculate max EPISODE from DATABASE (not from forms)
            max_episode = 0
            if self.instance and self.instance.pk:
                # Get max from SAVED instances only
                existing_episodes = self.instance.medications.values_list('EPISODE', flat=True)
                if existing_episodes:
                    max_episode = max(existing_episodes)
            
            # Set initial for new form
            form.fields['EPISODE'].initial = max_episode + 1
            form.initial['EPISODE'] = max_episode + 1




# ==========================================
# CREATE FORMSETS
# ==========================================

ContactMedicationHistory28FormSet = forms.inlineformset_factory(
    FU_CONTACT_28,
    ContactMedicationHistory28,
    form=ContactMedicationHistory28Form,
    formset=BaseContactMedicationHistory28FormSet,
    extra=1,
    can_delete=False,
    min_num=0,
    validate_min=False,
    max_num=20,
    validate_max=True,
    fields=['EPISODE', 'MEDICATION_NAME', 'DOSAGE', 'USAGE_PERIOD', 'REASON']
)