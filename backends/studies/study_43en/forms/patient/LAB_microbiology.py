# backends/studies/study_43en/forms/patient/LAB_microbiology.py
"""
Forms for LAB Microbiology Culture with Semantic IDs

Features:
- Auto-generation of LAB_CULTURE_ID
- Klebsiella detection (IS_KLEBSIELLA)
- Conditional field validation
- Date consistency checks
"""

from django import forms
from django.forms import modelformset_factory, BaseModelFormSet
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Q
from backends.studies.study_43en.models.patient import (
    LAB_Microbiology,
    AntibioticSensitivity,
    ENR_CASE,
)


# ==========================================
# LAB MICROBIOLOGY CULTURE FORM
# ==========================================

class LABMicrobiologyCultureForm(forms.ModelForm):
    """
    Form for LAB microbiology culture record with semantic ID support
    
    Features:
    - Auto-sequence generation (LAB_CASE_SEQ)
    - Auto-generation of LAB_CULTURE_ID
    - Klebsiella detection (IS_KLEBSIELLA)
    - Conditional field validation
    - Date consistency checks
    """
    
    class Meta:
        model = LAB_Microbiology
        fields = [
            'STUDYID',
            'SITEID',
            'SUBJID',
            'INITIAL',
            'SPECSAMPLOC', 
            'OTHERSPECIMEN', 
            'SPECIMENID',
            'SPECSAMPDATE', 
            'BACSTRAINISOLDATE',
            'RESULT',
            'IFPOSITIVE',
            'SPECIFYOTHERSPECIMEN',
            'RESULTDETAILS',
            'ORDEREDBYDEPT', 
            'DEPTDIAGSENT',
        ]
        
        #  UPDATED: Labels to match model verbose_name
        labels = {
            'STUDYID': _('Study ID'),
            'SITEID': _('Site ID'),
            'SUBJID': _('Subject ID'),
            'INITIAL': _('Patient Initial'),
            'SPECSAMPLOC': _('Sampling site'),
            'OTHERSPECIMEN': _('Other'),
            'SPECIMENID': _('Sample ID (SID)'),
            'SPECSAMPDATE': _('Date of Specimen Collection'),
            'BACSTRAINISOLDATE': _('Isolated Bacteria Date '),
            'RESULT': _('Culture Result'),
            'IFPOSITIVE': _('Organism Type (If Positive)'),
            'SPECIFYOTHERSPECIMEN': _('Specify Other Organism'),
            'RESULTDETAILS': _('Result Details'),
            'ORDEREDBYDEPT': _('Department'),
            'DEPTDIAGSENT': _('Diagnosis of the department sending the test sample'),
        }
        
        widgets = {
            'STUDYID': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Study ID'),
                'maxlength': 50
            }),
            'SITEID': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Site ID'),
                'maxlength': 20
            }),
            'SUBJID': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Subject ID'),
                'maxlength': 50
            }),
            'INITIAL': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Patient Initial'),
                'maxlength': 10
            }),
            'SPECSAMPLOC': forms.Select(attrs={
                'class': 'form-control specimen-type-select',
                'required': True
            }),
            'OTHERSPECIMEN': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Specify specimen type'),
                'maxlength': 100
            }),
            'SPECIMENID': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Lab specimen ID (SID)'),
                'maxlength': 50
            }),
            'SPECSAMPDATE': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control datepicker',
                'placeholder': 'YYYY-MM-DD',
                'required': True
            }),
            'BACSTRAINISOLDATE': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control datepicker',
                'placeholder': 'YYYY-MM-DD'
            }),
            'RESULT': forms.Select(attrs={
                'class': 'form-control culture-result-select',
                'required': True,
                'data-toggle': 'result-dependent-fields'
            }),
            'IFPOSITIVE': forms.Select(attrs={
                'class': 'form-control ifpositive-select',
                'data-toggle': 'ifpositive-dependent'
            }),
            'SPECIFYOTHERSPECIMEN': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter organism name'),
                'maxlength': 200
            }),
            'RESULTDETAILS': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Additional details (optional)')
            }),
            'ORDEREDBYDEPT': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., ICU, Emergency, Internal Medicine'),
                'maxlength': 100
            }),
            'DEPTDIAGSENT': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('Clinical indication or diagnosis')
            }),
        }
        
        #  UPDATED: Help texts to match model
        help_texts = {
            'SPECSAMPLOC': _('Select the anatomical location where the specimen was collected'),
            'OTHERSPECIMEN': _('Specify if specimen location is "Other"'),
            'SPECIMENID': _('Laboratory specimen identification number'),
            'SPECSAMPDATE': _('Date when the specimen was collected from the patient'),
            'BACSTRAINISOLDATE': _('Date when bacteria was isolated from the culture'),
            'RESULT': _('Select the culture result'),
            'IFPOSITIVE': _('Required if culture result is positive'),
            'SPECIFYOTHERSPECIMEN': _('Required if organism type is "Other"'),
            'RESULTDETAILS': _(' IMPORTANT: Include "Klebsiella" in organism name to enable antibiotic testing'),
            'ORDEREDBYDEPT': _('Department or unit that ordered the culture'),
            'DEPTDIAGSENT': _('Clinical diagnosis or reason for ordering the culture'),
        }
        
        #  Enhanced error messages
        error_messages = {
            'SPECSAMPLOC': {
                'required': _('Specimen location is required'),
                'invalid_choice': _('Invalid specimen location selected'),
            },
            'SPECSAMPDATE': {
                'required': _('Sample collection date is required'),
                'invalid': _('Invalid date format. Use YYYY-MM-DD'),
            },
            'RESULT': {
                'required': _('Culture result is required'),
                'invalid_choice': _('Invalid culture result selected'),
            },
            'IFPOSITIVE': {
                'required': _('Organism type is required for positive results'),
                'invalid_choice': _('Invalid organism type selected'),
            },
        }
    
    def __init__(self, *args, **kwargs):
        self.usubjid = kwargs.pop('usubjid', None)
        super().__init__(*args, **kwargs)
        
        # Get from instance if not provided
        if not self.usubjid and self.instance and self.instance.pk:
            self.usubjid = self.instance.USUBJID
        
        # Make optional fields
        optional_fields = [
            'STUDYID', 'SITEID', 'SUBJID', 'INITIAL',
            'OTHERSPECIMEN', 'SPECIMENID', 'BACSTRAINISOLDATE',
            'RESULTDETAILS', 'ORDEREDBYDEPT', 'DEPTDIAGSENT'
        ]
        for field_name in optional_fields:
            if field_name in self.fields:
                self.fields[field_name].required = False
        
        # Set initial values for new records
        if not self.instance.pk and self.usubjid:
            self.instance.USUBJID = self.usubjid
            
            # Pre-populate from patient data
            if hasattr(self.usubjid, 'USUBJID'):
                screening = self.usubjid.USUBJID  # SCR_CASE
                self.fields['SITEID'].initial = screening.SITEID
                self.fields['SUBJID'].initial = screening.SUBJID
                self.fields['INITIAL'].initial = screening.INITIAL
        
        #  Enhanced help text for Klebsiella detection
        if 'RESULTDETAILS' in self.fields:
            self.fields['RESULTDETAILS'].help_text = _(
                ' IMPORTANT: Include "Klebsiella" in organism name to enable antibiotic testing\n\n'
                ' Auto-detection keywords:\n'
                '   • "Klebsiella"\n'
                '   • "KPN"\n'
                '   • "K. pneumoniae"\n'
                '   • "k.pneumoniae"'
            )
    
    def clean(self):
        """Comprehensive validation"""
        cleaned_data = super().clean()
        
        specimen_loc = cleaned_data.get('SPECSAMPLOC')
        other_specimen = cleaned_data.get('OTHERSPECIMEN')
        sample_date = cleaned_data.get('SPECSAMPDATE')
        isolation_date = cleaned_data.get('BACSTRAINISOLDATE')
        result = cleaned_data.get('RESULT')
        ifpositive = cleaned_data.get('IFPOSITIVE')
        specify_other = cleaned_data.get('SPECIFYOTHERSPECIMEN')
        result_details = cleaned_data.get('RESULTDETAILS')
        
        # 1. Validate "Other" specimen location
        if specimen_loc == LAB_Microbiology.SpecimenLocationChoices.OTHER:
            if not other_specimen or not other_specimen.strip():
                self.add_error('OTHERSPECIMEN', 
                    _('Please specify the specimen type when "Other" is selected'))
        
        # 2. Date validation
        if sample_date and isolation_date:
            if isolation_date < sample_date:
                self.add_error('BACSTRAINISOLDATE',
                    _('Isolation date cannot be before sample collection date'))
        
        # 3. Positive result validation
        if result == LAB_Microbiology.ResultTypeChoices.POSITIVE:
            # Require IFPOSITIVE for positive results
            if not ifpositive:
                self.add_error('IFPOSITIVE',
                    _('Organism type is required when culture result is positive'))
            
            # If organism is "Other", require specification
            if ifpositive == LAB_Microbiology.IfPositiveChoices.OTHER:
                if not specify_other or not specify_other.strip():
                    self.add_error('SPECIFYOTHERSPECIMEN',
                        _('Please specify the organism name when "Other" is selected'))
            
            # Warn if result details don't mention Klebsiella (but don't block)
            if result_details:
                details_lower = result_details.lower()
                has_klebsiella = any(
                    kw in details_lower 
                    for kw in ['klebsiella', 'kpn', 'k. pneumoniae', 'k.pneumoniae']
                )
                
                if not has_klebsiella and ifpositive != LAB_Microbiology.IfPositiveChoices.KPNEUMONIAE:
                    # This is just a warning, not an error
                    pass
        
        return cleaned_data
    
    def clean_OTHERSPECIMEN(self):
        """Normalize other specimen text"""
        value = self.cleaned_data.get('OTHERSPECIMEN')
        return value.strip().title() if value else value
    
    def clean_SPECIFYOTHERSPECIMEN(self):
        """Normalize organism specification"""
        value = self.cleaned_data.get('SPECIFYOTHERSPECIMEN')
        return value.strip() if value else value
    
    def clean_RESULTDETAILS(self):
        """Normalize result details"""
        value = self.cleaned_data.get('RESULTDETAILS')
        return value.strip() if value else value
    
    def clean_ORDEREDBYDEPT(self):
        """Normalize department name"""
        value = self.cleaned_data.get('ORDEREDBYDEPT')
        return value.strip() if value else value


# ==========================================
# BASE FORMSET FOR LAB CULTURES
# ==========================================

class BaseLABMicrobiologyCultureFormSet(BaseModelFormSet):
    """Base formset with custom validation"""
    
    def __init__(self, *args, **kwargs):
        self.usubjid = kwargs.pop('usubjid', None)
        super().__init__(*args, **kwargs)
        
        # Pass usubjid to each form
        if self.usubjid:
            for form in self.forms:
                form.usubjid = self.usubjid
    
    def clean(self):
        """Formset-level validation"""
        if any(self.errors):
            return
        
        # Check for duplicate specimen IDs
        specimen_ids = []
        duplicate_sids = []
        
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get('DELETE'):
                continue
            
            sid = form.cleaned_data.get('SPECIMENID')
            if sid and sid.strip():
                sid_normalized = sid.strip().upper()
                if sid_normalized in specimen_ids:
                    duplicate_sids.append(sid)
                else:
                    specimen_ids.append(sid_normalized)
        
        if duplicate_sids:
            raise ValidationError(
                _('Duplicate specimen IDs found: %(sids)s'),
                params={'sids': ', '.join(set(duplicate_sids))},
                code='duplicate_specimen_ids'
            )


# ==========================================
# FORMSET FACTORY
# ==========================================

LABMicrobiologyCultureFormSet = modelformset_factory(
    LAB_Microbiology,
    form=LABMicrobiologyCultureForm,
    formset=BaseLABMicrobiologyCultureFormSet,
    extra=1,
    can_delete=True,
    can_order=False,
)


# ==========================================
# FILTER FORM
# ==========================================

class LABMicrobiologyFilterForm(forms.Form):
    """Filter form for LAB microbiology culture list"""
    
    specimen_loc = forms.ChoiceField(
        choices=[('', _('All Specimen Types'))] + list(LAB_Microbiology.SpecimenLocationChoices.choices),
        required=False,
        label=_('Specimen Location'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    result = forms.ChoiceField(
        choices=[('', _('All Results'))] + list(LAB_Microbiology.ResultTypeChoices.choices),
        required=False,
        label=_('Culture Result'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    kpn_only = forms.BooleanField(
        required=False,
        label=_('Show Klebsiella Positive Only'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    date_from = forms.DateField(
        required=False,
        label=_('From Date'),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        label=_('To Date'),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_lab_culture_summary(usubjid):
    """
    Get summary statistics for LAB cultures
    
    Args:
        usubjid: ENR_CASE instance
    
    Returns:
        dict with summary data
    """
    cultures = LAB_Microbiology.objects.filter(USUBJID=usubjid)
    
    total = cultures.count()
    positive = cultures.filter(RESULT=LAB_Microbiology.ResultTypeChoices.POSITIVE).count()
    kpn_positive = cultures.filter(IS_KLEBSIELLA=True).count()
    negative = cultures.filter(RESULT=LAB_Microbiology.ResultTypeChoices.NEGATIVE).count()

    
    # No result (NULL or empty)
    no_result = cultures.filter(
        Q(RESULT__isnull=True) | Q(RESULT='')
    ).count()
    
    # By specimen type
    by_specimen = {}
    for spec_loc, spec_label in LAB_Microbiology.SpecimenLocationChoices.choices:
        count = cultures.filter(SPECSAMPLOC=spec_loc).count()
        positive_count = cultures.filter(
            SPECSAMPLOC=spec_loc,
            RESULT=LAB_Microbiology.ResultTypeChoices.POSITIVE
        ).count()
        kpn_count = cultures.filter(
            SPECSAMPLOC=spec_loc,
            IS_KLEBSIELLA=True
        ).count()
        
        if count > 0:
            by_specimen[spec_loc] = {
                'label': spec_label,
                'total': count,
                'positive': positive_count,
                'kpn_positive': kpn_count,
                'positive_rate': round(positive_count / count * 100) if count > 0 else 0,
                'kpn_rate': round(kpn_count / count * 100) if count > 0 else 0,
            }
    
    # Recent cultures
    recent_cultures = cultures.order_by('-SPECSAMPDATE', '-LAB_CASE_SEQ')[:5]
    
    # Antibiotic test summary
    total_tests = AntibioticSensitivity.objects.filter(
        LAB_CULTURE_ID__USUBJID=usubjid
    ).count()
    
    resistant_tests = AntibioticSensitivity.objects.filter(
        LAB_CULTURE_ID__USUBJID=usubjid,
        SENSITIVITY_LEVEL='R'
    ).count()
    
    return {
        'total_cultures': total,
        'positive_count': positive,
        'kpn_positive_count': kpn_positive,
        'negative_count': negative,
        'no_result_count': no_result,
        'positive_rate': round(positive / total * 100) if total > 0 else 0,
        'kpn_rate': round(kpn_positive / total * 100) if total > 0 else 0,
        'completion_rate': round((total - no_result) / total * 100) if total > 0 else 0,
        'by_specimen_type': by_specimen,
        'recent_cultures': recent_cultures,
        'total_antibiotic_tests': total_tests,
        'resistant_count': resistant_tests,
        'resistance_rate': round(resistant_tests / total_tests * 100) if total_tests > 0 else 0,
    }


def get_kpn_positive_cultures(usubjid):
    """Get all Klebsiella-positive cultures eligible for antibiotic testing"""
    return (
        LAB_Microbiology.objects
        .filter(USUBJID=usubjid, IS_KLEBSIELLA=True)
        .select_related('USUBJID')
        .prefetch_related('antibiotic_sensitivities')
        .order_by('-SPECSAMPDATE', '-LAB_CASE_SEQ')
    )