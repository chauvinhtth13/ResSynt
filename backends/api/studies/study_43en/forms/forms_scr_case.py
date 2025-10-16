from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import date

# Import models
from backends.studies.study_43en.models import ScreeningCase


# ==========================================
# COMMON CHOICES
# ==========================================

SITEID_CHOICES = [
    ('', '--- Select Site ---'),
    ('003', '003 - Hospital A'),
    ('011', '011 - Hospital B'),
    ('020', '020 - Clinic C'),
]

BOOLEAN_CHOICES = [
    (False, 'No'),
    (True, 'Yes'),
]


# ==========================================
# SCREENING CASE FORM
# ==========================================

class ScreeningCaseForm(forms.ModelForm):
    """
    Form for ScreeningCase model - Optimized
    
    Changes from old version:
    - SCRID auto-generated (removed from form)
    - Added UNRECRUITED_REASON with proper choices
    - Added UNRECRUITED_REASON_OTHER conditional field
    - Fixed validation logic
    - Added WARD field
    - Better widget configuration
    - Support for passing user to save()
    """
    
    # Override SITEID with choices
    SITEID = forms.ChoiceField(
        choices=SITEID_CHOICES,
        required=True,
        label=_('Site ID'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Eligibility criteria - using BooleanField with RadioSelect
    UPPER16AGE = forms.BooleanField(
        required=False,  # Don't require True, allow False
        label=_('Age ≥ 16 years'),
        widget=forms.RadioSelect(
            choices=BOOLEAN_CHOICES,
            attrs={'class': 'form-check-input'}
        )
    )
    
    INFPRIOR2OR48HRSADMIT = forms.BooleanField(
        required=False,
        label=_('Infection prior to or within 48h of admission'),
        widget=forms.RadioSelect(
            choices=BOOLEAN_CHOICES,
            attrs={'class': 'form-check-input'}
        )
    )
    
    ISOLATEDKPNFROMINFECTIONORBLOOD = forms.BooleanField(
        required=False,
        label=_('KPN isolated from infection site or blood'),
        widget=forms.RadioSelect(
            choices=BOOLEAN_CHOICES,
            attrs={'class': 'form-check-input'}
        )
    )
    
    KPNISOUNTREATEDSTABLE = forms.BooleanField(
        required=False,
        label=_('KPN untreated and stable'),
        widget=forms.RadioSelect(
            choices=BOOLEAN_CHOICES,
            attrs={'class': 'form-check-input'}
        ),
        help_text=_('Note: For eligibility, this must be "No"')
    )
    
    CONSENTTOSTUDY = forms.BooleanField(
        required=False,
        label=_('Consent to participate in study'),
        widget=forms.RadioSelect(
            choices=BOOLEAN_CHOICES,
            attrs={'class': 'form-check-input'}
        )
    )
    
    # UNRECRUITED_REASON with choices from model
    UNRECRUITED_REASON = forms.ChoiceField(
        choices=[('', '--- Select Reason ---')] + ScreeningCase.UNRECRUITED_CHOICES,
        required=False,
        label=_('Reason Not Recruited'),
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        help_text=_('Required if patient is not eligible')
    )
    
    # OTHER reason field - conditional
    UNRECRUITED_REASON_OTHER = forms.CharField(
        required=False,
        label=_('Other Reason (specify)'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Please specify other reason...',
            'data-depends-on': 'UNRECRUITED_REASON',
            'data-depends-value': 'OTHER'
        })
    )
    
    class Meta:
        model = ScreeningCase
        fields = [
            # Study info (SCRID removed - auto-generated)
            'STUDYID', 'SITEID', 'INITIAL', 'WARD',
            
            # Eligibility criteria
            'UPPER16AGE',
            'INFPRIOR2OR48HRSADMIT',
            'ISOLATEDKPNFROMINFECTIONORBLOOD',
            'KPNISOUNTREATEDSTABLE',
            'CONSENTTOSTUDY',
            
            # Unrecruited reason
            'UNRECRUITED_REASON',
            'UNRECRUITED_REASON_OTHER',
            
            # Dates (manual entry)
            'SCREENINGFORMDATE',
            'COMPLETEDDATE',
            'COMPLETEDBY',
        ]
        
        widgets = {
            'STUDYID': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True,
            }),
            'INITIAL': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., ABC',
                'maxlength': 10,
            }),
            'WARD': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ward/Department',
            }),
            'SCREENINGFORMDATE': forms.DateInput(attrs={
                'class': 'form-control datepicker',
                'type': 'date',
            }),
            'COMPLETEDDATE': forms.DateInput(attrs={
                'class': 'form-control datepicker',
                'type': 'date',
            }),
            'COMPLETEDBY': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Completed by',
            }),
        }
        
        labels = {
            'STUDYID': _('Study ID'),
            'INITIAL': _('Initials'),
            'WARD': _('Ward/Department'),
            'SCREENINGFORMDATE': _('Screening Form Date'),
            'COMPLETEDDATE': _('Completion Date'),
            'COMPLETEDBY': _('Completed By'),
        }
        
        help_texts = {
            'INITIAL': _('Patient initials (2-3 letters)'),
            'SCREENINGFORMDATE': _('Date of screening'),
        }
    
    def __init__(self, *args, **kwargs):
        # Extract user if passed
        self.user = kwargs.pop('user', None)
        
        super().__init__(*args, **kwargs)
        
        # Set default STUDYID
        if not self.instance.pk:
            self.fields['STUDYID'].initial = '43EN'
        
        # Display readonly fields for existing instances
        if self.instance.pk:
            # Show SCRID (read-only)
            if self.instance.SCRID:
                self.fields['SCRID'] = forms.CharField(
                    label=_('Screening ID'),
                    initial=self.instance.SCRID,
                    disabled=True,
                    required=False,
                    widget=forms.TextInput(attrs={
                        'class': 'form-control',
                        'readonly': True,
                    })
                )
                # Move SCRID to top of fields
                scrid_field = self.fields.pop('SCRID')
                self.fields = {'SCRID': scrid_field, **self.fields}
            
            # Show SUBJID if exists (read-only)
            if self.instance.SUBJID:
                self.fields['SUBJID'] = forms.CharField(
                    label=_('Subject ID'),
                    initial=self.instance.SUBJID,
                    disabled=True,
                    required=False,
                    widget=forms.TextInput(attrs={
                        'class': 'form-control',
                        'readonly': True,
                    })
                )
            
            # Show USUBJID if exists (read-only)
            if self.instance.USUBJID:
                self.fields['USUBJID'] = forms.CharField(
                    label=_('Unique Subject ID'),
                    initial=self.instance.USUBJID,
                    disabled=True,
                    required=False,
                    widget=forms.TextInput(attrs={
                        'class': 'form-control bg-success text-white',
                        'readonly': True,
                    })
                )
            
            # Show confirmation status
            if self.instance.is_confirmed:
                self.fields['is_confirmed_display'] = forms.CharField(
                    label=_('Status'),
                    initial='Eligible',
                    disabled=True,
                    required=False,
                    widget=forms.TextInput(attrs={
                        'class': 'form-control bg-success text-white',
                        'readonly': True,
                    })
                )
    
    def clean(self):
        """
        Validate form data
        
        Rules:
        1. If not eligible, UNRECRUITED_REASON is required
        2. If UNRECRUITED_REASON is "OTHER", UNRECRUITED_REASON_OTHER is required
        3. SITEID is required
        """
        cleaned_data = super().clean()
        
        # Get eligibility criteria values
        upper16age = cleaned_data.get('UPPER16AGE', False)
        infprior = cleaned_data.get('INFPRIOR2OR48HRSADMIT', False)
        isolated = cleaned_data.get('ISOLATEDKPNFROMINFECTIONORBLOOD', False)
        stable = cleaned_data.get('KPNISOUNTREATEDSTABLE', False)
        consent = cleaned_data.get('CONSENTTOSTUDY', False)
        
        # Check if eligible
        is_eligible = (
            upper16age and 
            infprior and 
            isolated and 
            not stable and  # Must be False!
            consent
        )
        
        # Validate UNRECRUITED_REASON
        unrecruited_reason = cleaned_data.get('UNRECRUITED_REASON')
        unrecruited_other = cleaned_data.get('UNRECRUITED_REASON_OTHER')
        
        # Rule 1: If not eligible, reason is required
        if not is_eligible:
            if not unrecruited_reason:
                self.add_error(
                    'UNRECRUITED_REASON',
                    _('Please select reason not recruited when patient is not eligible.')
                )
        
        # Rule 2: If reason is "OTHER", other text is required
        if unrecruited_reason == 'OTHER':
            if not unrecruited_other or not unrecruited_other.strip():
                self.add_error(
                    'UNRECRUITED_REASON_OTHER',
                    _('Please specify the other reason when selecting "Other".')
                )
        
        # Rule 3: SITEID is required
        siteid = cleaned_data.get('SITEID')
        if not siteid:
            self.add_error(
                'SITEID',
                _('Please select a site.')
            )
        
        # Auto-suggest reason based on criteria
        if not is_eligible and not unrecruited_reason:
            # Suggest reason based on which criteria failed
            if not upper16age:
                cleaned_data['_suggested_reason'] = '3'  # Age <16
            elif not infprior:
                cleaned_data['_suggested_reason'] = '2'  # Infection after 48h
            elif stable:
                cleaned_data['_suggested_reason'] = '1'  # KPN recovered
            elif not consent:
                cleaned_data['_suggested_reason'] = 'A'  # No consent
        
        return cleaned_data
    
    def save(self, commit=True):
        """
        Save the form
        
        IMPORTANT: Pass user to the model's save method
        """
        instance = super().save(commit=False)
        
        if commit:
            # Pass user to model save method for auto-fill USER_ENTRY
            instance.save(user=self.user)
        
        return instance


# ==========================================
# JavaScript for conditional "Other" field
# ==========================================

# Add this to your template:
"""
<script>
document.addEventListener('DOMContentLoaded', function() {
    const reasonRadios = document.querySelectorAll('input[name="UNRECRUITED_REASON"]');
    const otherField = document.getElementById('id_UNRECRUITED_REASON_OTHER');
    const otherFieldGroup = otherField ? otherField.closest('.form-group') : null;
    
    function toggleOtherField() {
        const selectedReason = document.querySelector('input[name="UNRECRUITED_REASON"]:checked');
        
        if (otherFieldGroup) {
            if (selectedReason && selectedReason.value === 'OTHER') {
                otherFieldGroup.style.display = 'block';
                otherField.required = true;
            } else {
                otherFieldGroup.style.display = 'none';
                otherField.required = false;
                otherField.value = '';  // Clear value
            }
        }
    }
    
    reasonRadios.forEach(radio => {
        radio.addEventListener('change', toggleOtherField);
    });
    
    // Initial check
    toggleOtherField();
});
</script>
"""