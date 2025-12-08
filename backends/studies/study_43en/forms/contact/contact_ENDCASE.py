# backends/studies/study_43en/forms/ContactEndCase.py

from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from backends.studies.study_43en.models.contact import ContactEndCaseCRF


class ContactEndCaseCRFForm(forms.ModelForm):
    """
    Form for Contact End Case CRF (Study Completion)
    
    Differences from Patient Form:
    - 3 visits instead of 4 (V1, V2, V3)
    - V2 at Day 28±3 (not Day 10±3)
    - No V4
    """
    
    #  RadioSelect for better UX
    WITHDRAWREASON = forms.ChoiceField(
        choices=[
            ('na', _('Not Applicable')),
            ('withdraw', _('Voluntary Withdrawal')),
            ('forced', _('Forced Withdrawal'))
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='na',
        required=True,
        label=_('Withdrawal Reason')
    )
    
    INCOMPLETE = forms.ChoiceField(
        choices=[
            ('na', _('Not Applicable')),
            ('no', _('No')),
            ('yes', _('Yes'))
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='na',
        required=True,
        label=_('Unable to Complete Study')
    )
    
    LOSTTOFOLLOWUP = forms.ChoiceField(
        choices=[
            ('na', _('Not Applicable')),
            ('no', _('No')),
            ('yes', _('Yes'))
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='na',
        required=True,
        label=_('Lost to Follow-up')
    )
    
    class Meta:
        model = ContactEndCaseCRF
        fields = [
            'ENDDATE', 'ENDFORMDATE',
            'VICOMPLETED', 'V2COMPLETED', 'V3COMPLETED',
            'WITHDRAWREASON', 'WITHDRAWDATE', 'WITHDRAWDETAILS',
            'INCOMPLETE', 'INCOMPLETEDEATH', 'INCOMPLETEMOVED', 'INCOMPLETEOTHER',
            'LOSTTOFOLLOWUP', 'LOSTTOFOLLOWUPDATE',
        ]
        
        widgets = {
            'ENDDATE': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'placeholder': 'DD/MM/YYYY',
                'type': 'date'
            }),
            'ENDFORMDATE': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'placeholder': 'DD/MM/YYYY',
                'type': 'date'
            }),
            'WITHDRAWDATE': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'placeholder': 'DD/MM/YYYY',
                'type': 'date'
            }),
            'LOSTTOFOLLOWUPDATE': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'placeholder': 'DD/MM/YYYY',
                'type': 'date'
            }),
            'VICOMPLETED': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'V2COMPLETED': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'V3COMPLETED': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'WITHDRAWDETAILS': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Details about withdrawal from study...')
            }),
            'INCOMPLETEDEATH': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'INCOMPLETEMOVED': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'INCOMPLETEOTHER': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Other reason (specify)...')
            }),
        }
        
        labels = {
            'ENDDATE': _('End Date Recorded'),
            'ENDFORMDATE': _('Study End Date'),
            'VICOMPLETED': _('V1 (Enrollment) - Completed'),
            'V2COMPLETED': _('V2 (Day 28±3) - Completed'),
            'V3COMPLETED': _('V3 (Day 90±3) - Completed'),
            'WITHDRAWREASON': _('Withdrawal Reason'),
            'WITHDRAWDATE': _('Withdrawal Date'),
            'WITHDRAWDETAILS': _('Withdrawal Details'),
            'INCOMPLETE': _('Unable to Complete Study'),
            'INCOMPLETEDEATH': _('Participant Death'),
            'INCOMPLETEMOVED': _('Participant Moved/Relocated'),
            'INCOMPLETEOTHER': _('Other Reason, Specify'),
            'LOSTTOFOLLOWUP': _('Lost to Follow-up'),
            'LOSTTOFOLLOWUPDATE': _('Lost to Follow-up Date'),
        }
        
        help_texts = {
            'ENDDATE': _('Date when contact ended study participation'),
            'ENDFORMDATE': _('Date when end case form was completed'),
            'V2COMPLETED': _('Contact V2 is Day 28±3'),
            'WITHDRAWREASON': _('Select reason if contact withdrew'),
            'INCOMPLETE': _('Mark if contact unable to complete fully'),
            'LOSTTOFOLLOWUP': _('Mark if unable to contact participant'),
        }
    
    def __init__(self, *args, contact=None, **kwargs):
        """Initialize form with contact context"""
        if contact is None and 'instance' in kwargs and kwargs['instance']:
            contact = getattr(kwargs['instance'], 'USUBJID', None)
        
        self.contact = contact
        super().__init__(*args, **kwargs)
        
        # Make all fields optional initially
        for field_name, field in self.fields.items():
            if field_name not in ['WITHDRAWREASON', 'INCOMPLETE', 'LOSTTOFOLLOWUP']:
                field.required = False
        
        # Set initial values for radio fields
        if self.instance and self.instance.pk:
            self.fields['WITHDRAWREASON'].initial = self.instance.WITHDRAWREASON or 'na'
            self.fields['INCOMPLETE'].initial = self.instance.INCOMPLETE or 'na'
            self.fields['LOSTTOFOLLOWUP'].initial = self.instance.LOSTTOFOLLOWUP or 'na'
        else:
            self.fields['WITHDRAWREASON'].initial = 'na'
            self.fields['INCOMPLETE'].initial = 'na'
            self.fields['LOSTTOFOLLOWUP'].initial = 'na'
    
    def clean(self):
        """ SIMPLIFIED validation - only essential checks"""
        cleaned_data = super().clean()
        errors = {}
        
        # 1. Validate end dates
        enddate = cleaned_data.get('ENDDATE')
        if enddate and self.contact:
            enr_date = getattr(self.contact, 'ENRDATE', None)
            if enr_date and enddate < enr_date:
                errors['ENDDATE'] = _(
                    'End date cannot be before enrollment date ({enr_date})'
                ).format(enr_date=enr_date.strftime('%d/%m/%Y'))
        
        # 2. Validate withdrawal info
        withdraw_reason = cleaned_data.get('WITHDRAWREASON')
        if withdraw_reason in ['withdraw', 'forced']:
            if not cleaned_data.get('WITHDRAWDATE'):
                errors['WITHDRAWDATE'] = _('Please enter withdrawal date when contact withdrew from study')
        
        # 3. Validate incomplete info
        if cleaned_data.get('INCOMPLETE') == 'yes':
            has_reason = any([
                cleaned_data.get('INCOMPLETEDEATH'),
                cleaned_data.get('INCOMPLETEMOVED'),
                cleaned_data.get('INCOMPLETEOTHER')
            ])
            if not has_reason:
                errors['INCOMPLETE'] = _('Please select at least one reason when marking study incomplete')
        
        # 4. Validate lost to follow-up
        if cleaned_data.get('LOSTTOFOLLOWUP') == 'yes':
            if not cleaned_data.get('LOSTTOFOLLOWUPDATE'):
                errors['LOSTTOFOLLOWUPDATE'] = _('Please enter lost to follow-up date')
        
        if errors:
            raise ValidationError(errors)
        
        return cleaned_data


# ==========================================
# FORM HELPER FUNCTIONS
# ==========================================

def get_contact_completion_summary(end_case):
    """Get summary of study completion for display"""
    if not end_case:
        return None
    
    return {
        'total_visits': end_case.total_visits_completed,
        'completion_rate': f"{end_case.completion_rate:.0f}%",
        'all_completed': end_case.all_visits_completed,
        'has_early_termination': end_case.has_early_termination,
        'termination_reason': end_case.termination_reason,
        'study_duration': end_case.study_duration_days,
        'status': 'Completed' if end_case.STUDYCOMPLETED else 'In Progress'
    }


def get_contact_visit_completion_status(end_case):
    """Get detailed visit completion status (3 visits)"""
    if not end_case:
        return []
    
    visits = [
        {
            'name': 'V1 (Enrollment)',
            'completed': end_case.VICOMPLETED,
            'icon': '✓' if end_case.VICOMPLETED else '✗'
        },
        {
            'name': 'V2 (Day 28±3)',
            'completed': end_case.V2COMPLETED,
            'icon': '✓' if end_case.V2COMPLETED else '✗'
        },
        {
            'name': 'V3 (Day 90±3)',
            'completed': end_case.V3COMPLETED,
            'icon': '✓' if end_case.V3COMPLETED else '✗'
        }
    ]
    
    return visits