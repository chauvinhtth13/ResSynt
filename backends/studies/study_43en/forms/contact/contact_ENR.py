# backends/studies/study_43en/forms/contact/ContactENR.py

from django import forms
from django.utils.translation import gettext_lazy as _
from datetime import date
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.core.exceptions import ValidationError

# Import models
from backends.studies.study_43en.models.contact import (
    ENR_CONTACT, ENR_CONTACT_MedHisDrug, ContactUnderlyingCondition
)

# ==========================================
# COMMON CHOICES
# ==========================================

SITEID_CHOICES = [
    ('003', '003'),
    ('011', '011'),
    ('020', '020'),
]

# ==========================================
# CONTACT ENROLLMENT FORM
# ==========================================

class EnrollmentContactForm(forms.ModelForm):
    """
    Contact enrollment form with optimistic locking
    
    Differences from Patient:
    - Has RELATIONSHIP field
    - Has SPECIFYIFOTHERETHNI field
    - Uses ThreeStateChoices for risk factors (yes/no/unknown)
    - Less strict validation
    """

    version = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
        initial=0
    )

    class Meta:
        model = ENR_CONTACT
        exclude = ['USUBJID']
        widgets = {

            'FULLNAME': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter full name')
            }),
            'PHONE': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter phone number')
            }),

            # Dates
            'ENRDATE': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'placeholder': 'YYYY-MM-DD'
            }),
            
            # Birth information
            'DAYOFBIRTH': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'DD',
                'min': 1,
                'max': 31
            }),
            'MONTHOFBIRTH': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'MM',
                'min': 1,
                'max': 12
            }),
            'YEAROFBIRTH': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'YYYY',
                'min': 1900,
                'max': date.today().year
            }),
            'AGEIFDOBUNKNOWN': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Age',
                'min': 0,
                'max': 150,
                'step': 0.1
            }),
            
            # Contact-specific fields
            'RELATIONSHIP': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., spouse, child, parent, sibling')
            }),
            'SPECIFYIFOTHERETHNI': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Specify if ethnicity is "Other"')
            }),
            
            # Demographics
            'SEX': forms.Select(attrs={'class': 'form-control'}),
            'ETHNICITY': forms.TextInput(attrs={'class': 'form-control'}),
            'OCCUPATION': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Risk factors - ThreeStateChoices (yes/no/unknown)
            'HOSP2D6M': forms.Select(attrs={'class': 'form-control'}),
            'DIAL3M': forms.Select(attrs={'class': 'form-control'}),
            'CATHETER3M': forms.Select(attrs={'class': 'form-control'}),
            'SONDE3M': forms.Select(attrs={'class': 'form-control'}),
            'HOME_WOUND_CARE': forms.Select(attrs={'class': 'form-control'}),
            'LONG_TERM_CARE': forms.Select(attrs={'class': 'form-control'}),
            'CORTICOIDPPI': forms.Select(attrs={'class': 'form-control'}),
            
            # Underlying conditions flag
            'UNDERLYINGCONDS': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set version for optimistic locking
        if self.instance and self.instance.pk:
            self.fields['version'].initial = self.instance.version
        
        # Apply form-control class to all fields except checkboxes and radios
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'

    def clean(self):
        """
        Validation with optimistic locking
        Less strict than patient validation
        """
        cleaned_data = super().clean()
        
        # ==========================================
        # 1. OPTIMISTIC LOCKING CHECK
        # ==========================================
        if self.instance and self.instance.pk:
            submitted_version = cleaned_data.get('version')
            if submitted_version is not None and submitted_version != self.instance.version:
                raise ValidationError(
                    _('This record has been modified by another user. Please reload and try again.'),
                    code='version_conflict'
                )
        
        # ==========================================
        # 2. VALIDATE OTHER ETHNICITY SPECIFICATION
        # ==========================================
        ethnicity = (cleaned_data.get('ETHNICITY') or '').strip()
        specify_other = (cleaned_data.get('SPECIFYIFOTHERETHNI') or '').strip()
        
        if ethnicity and ethnicity.lower() == 'other':
            if not specify_other:
                raise ValidationError({
                    'SPECIFYIFOTHERETHNI': _('Please specify ethnicity when "Other" is selected')
                })
        
        return cleaned_data


# ==========================================
# CONTACT UNDERLYING CONDITION FORM
# ==========================================

class ContactUnderlyingConditionForm(forms.ModelForm):
    """Contact underlying conditions form"""
    
    class Meta:
        model = ContactUnderlyingCondition
        exclude = [
            'USUBJID',
            'last_modified_by_id',
            'last_modified_by_username',
            'last_modified_at',
            'created_at',
        ]
        widgets = {
            'OTHERDISEASESPECIFY': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Specify other disease(s)')
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Apply checkbox class to all boolean fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})

    def clean(self):
        """Validate other disease specification"""
        cleaned_data = super().clean()
        
        if cleaned_data.get('OTHERDISEASE'):
            if not (cleaned_data.get('OTHERDISEASESPECIFY') or '').strip():
                raise ValidationError({
                    'OTHERDISEASESPECIFY': _('Please specify other disease when checked')
                })
        
        return cleaned_data


# ==========================================
# CONTACT MEDICATION HISTORY FORM
# ==========================================

class ContactMedHisDrugForm(forms.ModelForm):
    """Individual contact medication form"""

    class Meta:
        model = ENR_CONTACT_MedHisDrug
        fields = ['SEQUENCE', 'DRUGNAME', 'DOSAGE', 'USAGETIME', 'USAGEREASON']
        widgets = {
            'SEQUENCE': forms.NumberInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'DRUGNAME': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Drug name')
            }),
            'DOSAGE': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., 500mg, 2 tablets')
            }),
            'USAGETIME': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., 2 weeks, 6 months')
            }),
            'USAGEREASON': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': _('Medical condition or reason'),
                'rows': 2
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['SEQUENCE'].required = False
        self.fields['DRUGNAME'].required = True

    def clean_DRUGNAME(self):
        """Clean and capitalize drug name"""
        drugname = (self.cleaned_data.get('DRUGNAME') or '').strip()
        if not drugname:
            raise ValidationError(_('Drug name is required'))
        return drugname.title()


# ==========================================
# CONTACT MEDICATION FORMSET (NO DELETE)
# ==========================================

class BaseContactMedHisDrugFormSet(BaseInlineFormSet):
    """Formset with duplicate detection - NO DELETE"""
    
    def clean(self):
        """Check for duplicate drug names"""
        if any(self.errors):
            return
        
        drug_names = []
        for form in self.forms:
            if form.cleaned_data:
                drug_name = form.cleaned_data.get('DRUGNAME')
                if drug_name:
                    drug_name_lower = drug_name.strip().lower()
                    if drug_name_lower in drug_names:
                        raise ValidationError(
                            _('Duplicate drug: "%(drug)s". Please remove duplicates.'),
                            params={'drug': drug_name},
                            code='duplicate_drug'
                        )
                    drug_names.append(drug_name_lower)


#  FORMSET WITHOUT DELETE CAPABILITY
ContactMedHisDrugFormSet = inlineformset_factory(
    ENR_CONTACT,
    ENR_CONTACT_MedHisDrug,
    form=ContactMedHisDrugForm,
    formset=BaseContactMedHisDrugFormSet,
    extra=1,
    can_delete=False,  #  NO DELETE
    can_delete_extra=False,
    min_num=0,
    validate_min=False,
    max_num=20,
    fk_name='USUBJID',
)