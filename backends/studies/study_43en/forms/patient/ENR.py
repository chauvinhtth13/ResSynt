# backends/studies/study_43en/forms/patient/ENR_updated.py

"""
UPDATED Enrollment Forms - Integrated with Personal Data
=========================================================

Key Changes:
- Personal data fields removed from EnrollmentCaseForm
- Personal data handled separately via PersonalDataForm
- Views will manage both forms together
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from datetime import date
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.core.exceptions import ValidationError

from backends.studies.study_43en.models.patient import (
    ENR_CASE, ENR_CASE_MedHisDrug, UnderlyingCondition
)
from backends.studies.study_43en.models.base_models import get_department_choices


# ==========================================
# UPDATED ENROLLMENT FORM (WITHOUT PII FIELDS)
# ==========================================

class EnrollmentCaseForm(forms.ModelForm):
    """
    Enrollment form WITHOUT personal data fields
    
    Personal data (FULLNAME, PHONE, MEDRECORDID, addresses) 
    are now handled by PersonalDataForm
    """

    version = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
        initial=0
    )

    class Meta:
        model = ENR_CASE
        exclude = [
            'USUBJID',
            #  These fields are now in PERSONAL_DATA model:
            # 'FULLNAME', 'PHONE', 'MEDRECORDID',
            # 'STREET_NEW', 'WARD_NEW', 'CITY_NEW',
            # 'STREET', 'WARD', 'DISTRICT', 'PROVINCECITY',
            # 'PRIMARY_ADDRESS'
        ]
        widgets = {
            # Dates
            'ENRDATE': forms.DateInput(format='%d/%m/%Y', attrs={
                'class': 'datepicker form-control',
                'placeholder': 'DD/MM/YYYY'
            }),
            'PRIORHOSPIADMISDATE': forms.DateInput(format='%d/%m/%Y', attrs={
                'class': 'datepicker form-control',
                'placeholder': 'DD/MM/YYYY'
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
            
            # Demographics
            'SEX': forms.Select(attrs={'class': 'form-control'}),
            'RESIDENCETYPE': forms.Select(attrs={'class': 'form-control'}),
            'WORKPLACETYPE': forms.Select(attrs={'class': 'form-control'}),
            
            # Risk factors
            'HOSP2D6M': forms.Select(attrs={'class': 'form-control'}),
            'DIAL3M': forms.Select(attrs={'class': 'form-control'}),
            'CATHETER3M': forms.Select(attrs={'class': 'form-control'}),
            'SONDE3M': forms.Select(attrs={'class': 'form-control'}),
            'HOME_WOUND_CARE': forms.Select(attrs={'class': 'form-control'}),
            'LONG_TERM_CARE': forms.Select(attrs={'class': 'form-control'}),
            'CORTICOIDPPI': forms.Select(attrs={'class': 'form-control'}),
            
            'TOILETNUM': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 0.5
            }),
            'REASONFORADM': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'RECRUITDEPT': forms.Select(attrs={
                'class': 'form-control',
                'data-placeholder': 'Chọn khoa tuyển dụng'
            }),
            'ETHNICITY': forms.TextInput(attrs={'class': 'form-control'}),
            'OCCUPATION': forms.TextInput(attrs={'class': 'form-control'}),
            'HEALFACILITYNAME': forms.TextInput(attrs={'class': 'form-control'}),
            
            'FROMOTHERHOSPITAL': forms.RadioSelect(
                choices=[
                    (None, 'Chưa xác định'),
                    (True, 'Có'),
                    (False, 'Không')
                ]
            ),
            'SHAREDTOILET': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'UNDERLYINGCONDS': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, siteid=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set input_formats for all date fields (DD/MM/YYYY)
        date_fields = ['ENRDATE', 'PRIORHOSPIADMISDATE']
        for field_name in date_fields:
            if field_name in self.fields:
                self.fields[field_name].input_formats = ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
        
        # Get version for optimistic locking
        if self.instance and self.instance.pk:
            self.fields['version'].initial = self.instance.version
            if not siteid:
                siteid = self.instance.SITEID
        
        # Set department choices based on SITEID
        dept_choices = [('', '---------')]
        dept_choices.extend(get_department_choices(siteid))
        self.fields['RECRUITDEPT'].widget.choices = dept_choices
        
        # Apply form-control class
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        
        # Optimistic locking check
        if self.instance and self.instance.pk:
            submitted_version = cleaned_data.get('version')
            if submitted_version is not None and submitted_version != self.instance.version:
                raise ValidationError(
                    _('This record has been modified by another user. Please reload and try again.'),
                    code='version_conflict'
                )
        
        return cleaned_data


# ==========================================
# UNCHANGED FORMS (keep as-is)
# ==========================================

class UnderlyingConditionForm(forms.ModelForm):
    """Unchanged - no PII fields"""
    
    class Meta:
        model = UnderlyingCondition
        exclude = [
            'USUBJID',
            'last_modified_by_id',
            'last_modified_by_username',
            'last_modified_at',
            'created_at',
        ]
        widgets = {
            'OTHERDISEASESPECIFY': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': _('Specify other disease(s)')
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})

    def clean(self):
        cleaned_data = super().clean()
        
        if cleaned_data.get('OTHERDISEASE'):
            if not cleaned_data.get('OTHERDISEASESPECIFY', '').strip():
                raise ValidationError({
                    'OTHERDISEASESPECIFY': _('Specify other disease when checked')
                })
        
        return cleaned_data


class MedHisDrugForm(forms.ModelForm):
    """Unchanged - no PII fields"""

    class Meta:
        model = ENR_CASE_MedHisDrug
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
                'placeholder': _('Dosage')
            }),
            'USAGETIME': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Duration')
            }),
            'USAGEREASON': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': _('Reason'),
                'rows': 2
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['SEQUENCE'].required = False
        self.fields['DRUGNAME'].required = True

    def clean_DRUGNAME(self):
        drugname = self.cleaned_data.get('DRUGNAME', '').strip()
        if not drugname:
            raise ValidationError(_('Drug name is required'))
        return drugname.title()


class BaseMedHisDrugFormSet(BaseInlineFormSet):
    """Unchanged - no PII fields"""
    
    def clean(self):
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
                            _('Duplicate drug: "%(drug)s"'),
                            params={'drug': drug_name},
                            code='duplicate_drug'
                        )
                    drug_names.append(drug_name_lower)


MedHisDrugFormSet = inlineformset_factory(
    ENR_CASE,
    ENR_CASE_MedHisDrug,
    form=MedHisDrugForm,
    formset=BaseMedHisDrugFormSet,
    extra=1,
    can_delete=False,
    can_delete_extra=False,
    min_num=0,
    validate_min=False,
    max_num=20,
    fk_name='USUBJID',
)