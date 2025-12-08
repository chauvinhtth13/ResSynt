# backends/studies/study_43en/forms/EndCase.py

from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from backends.studies.study_43en.models.patient import EndCaseCRF


# ==========================================
# END CASE CRF FORM
# ==========================================

class EndCaseCRFForm(forms.ModelForm):
    """
    Form for End Case CRF (Study Completion)
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
        model = EndCaseCRF
        fields = [
            'ENDDATE', 'ENDFORMDATE',
            'VICOMPLETED', 'V2COMPLETED', 'V3COMPLETED', 'V4COMPLETED',
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
            'V4COMPLETED': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
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
            'V2COMPLETED': _('V2 (Day 10±3) - Completed'),
            'V3COMPLETED': _('V3 (Day 28±3) - Completed'),
            'V4COMPLETED': _('V4 (Day 90±3) - Completed'),
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
            'ENDDATE': _('Date when patient ended study participation'),
            'ENDFORMDATE': _('Date when end case form was completed'),
            'WITHDRAWREASON': _('Select reason if patient withdrew'),
            'INCOMPLETE': _('Mark if patient unable to complete fully'),
            'LOSTTOFOLLOWUP': _('Mark if unable to contact patient'),
        }
    
    def __init__(self, *args, patient=None, **kwargs):
        """
        Initialize form with patient context
        
        Args:
            patient: ENR_CASE instance (optional)
        """
        #  Auto-detect patient from instance if not provided
        if patient is None and 'instance' in kwargs and kwargs['instance']:
            patient = getattr(kwargs['instance'], 'USUBJID', None)
        
        self.patient = patient
        super().__init__(*args, **kwargs)
        
        #  Make all fields optional initially (validation in clean())
        for field_name, field in self.fields.items():
            if field_name not in ['WITHDRAWREASON', 'INCOMPLETE', 'LOSTTOFOLLOWUP']:
                field.required = False
        
        #  Set initial values for radio fields
        if self.instance and self.instance.pk:
            # Set from existing instance
            self.fields['WITHDRAWREASON'].initial = self.instance.WITHDRAWREASON or 'na'
            self.fields['INCOMPLETE'].initial = self.instance.INCOMPLETE or 'na'
            self.fields['LOSTTOFOLLOWUP'].initial = self.instance.LOSTTOFOLLOWUP or 'na'
        else:
            # Default values for new records
            self.fields['WITHDRAWREASON'].initial = 'na'
            self.fields['INCOMPLETE'].initial = 'na'
            self.fields['LOSTTOFOLLOWUP'].initial = 'na'
    
    def clean(self):
        """
         SIMPLIFIED validation - only essential checks
        Model.clean() handles complex business logic
        """
        cleaned_data = super().clean()
        errors = {}
        
        # ==========================================
        # 1. VALIDATE END DATES
        # ==========================================
        enddate = cleaned_data.get('ENDDATE')
        
        #  Only check basic logic (not future date validation for flexibility)
        if enddate and self.patient:
            enr_date = getattr(self.patient, 'ENRDATE', None)
            if enr_date and enddate < enr_date:
                errors['ENDDATE'] = _(
                    'Ngày kết thúc không được trước ngày enrollment ({enr_date})'
                ).format(enr_date=enr_date.strftime('%d/%m/%Y'))
        
        # ==========================================
        # 2. VALIDATE WITHDRAWAL INFO
        # ==========================================
        withdraw_reason = cleaned_data.get('WITHDRAWREASON')
        withdraw_date = cleaned_data.get('WITHDRAWDATE')
        
        if withdraw_reason in ['withdraw', 'forced']:
            if not withdraw_date:
                errors['WITHDRAWDATE'] = _(
                    'Vui lòng nhập ngày rút lui khi bệnh nhân rút khỏi nghiên cứu'
                )
        
        # ==========================================
        # 3. VALIDATE INCOMPLETE INFO
        # ==========================================
        incomplete = cleaned_data.get('INCOMPLETE')
        
        if incomplete == 'yes':
            # Check at least one reason is provided
            has_reason = any([
                cleaned_data.get('INCOMPLETEDEATH'),
                cleaned_data.get('INCOMPLETEMOVED'),
                cleaned_data.get('INCOMPLETEOTHER')
            ])
            
            if not has_reason:
                errors['INCOMPLETE'] = _(
                    'Vui lòng chọn ít nhất một lý do khi đánh dấu không hoàn thành nghiên cứu'
                )
            
            # If "other" reason not selected, must specify
            if not cleaned_data.get('INCOMPLETEDEATH') and not cleaned_data.get('INCOMPLETEMOVED'):
                other_reason = cleaned_data.get('INCOMPLETEOTHER')
                if not other_reason or not other_reason.strip():
                    errors['INCOMPLETEOTHER'] = _(
                        'Vui lòng ghi rõ lý do khác khi không chọn tử vong hoặc di chuyển'
                    )
        
        # ==========================================
        # 4. VALIDATE LOST TO FOLLOW-UP
        # ==========================================
        lost_to_followup = cleaned_data.get('LOSTTOFOLLOWUP')
        ltfu_date = cleaned_data.get('LOSTTOFOLLOWUPDATE')
        
        if lost_to_followup == 'yes':
            if not ltfu_date:
                errors['LOSTTOFOLLOWUPDATE'] = _(
                    'Vui lòng nhập ngày mất liên lạc'
                )
        
        # ==========================================
        # RAISE ALL ERRORS AT ONCE
        # ==========================================
        if errors:
            raise ValidationError(errors)
        
        #  Let Model.clean() handle the rest (status consistency, etc.)
        return cleaned_data
    
    def clean_WITHDRAWDATE(self):
        """Validate withdrawal date"""
        date_value = self.cleaned_data.get('WITHDRAWDATE')
        
        if date_value:
            #  Basic validation only
            if self.patient:
                enr_date = getattr(self.patient, 'ENRDATE', None)
                if enr_date and date_value < enr_date:
                    raise ValidationError(
                        _('Ngày rút lui không được trước ngày enrollment')
                    )
        
        return date_value
    
    def clean_LOSTTOFOLLOWUPDATE(self):
        """Validate lost to follow-up date"""
        date_value = self.cleaned_data.get('LOSTTOFOLLOWUPDATE')
        
        if date_value:
            #  Basic validation only
            if self.patient:
                enr_date = getattr(self.patient, 'ENRDATE', None)
                if enr_date and date_value < enr_date:
                    raise ValidationError(
                        _('Ngày mất liên lạc không được trước ngày enrollment')
                    )
        
        return date_value
    
    def clean_INCOMPLETEOTHER(self):
        """ Normalize other reason"""
        value = self.cleaned_data.get('INCOMPLETEOTHER')
        if value:
            return value.strip()
        return value
    
    def clean_WITHDRAWDETAILS(self):
        """ Normalize withdrawal details"""
        value = self.cleaned_data.get('WITHDRAWDETAILS')
        if value:
            return value.strip()
        return value


# ==========================================
# FORM HELPER FUNCTIONS
# ==========================================

def get_completion_summary(end_case):
    """
    Get summary of study completion for display
    
    Args:
        end_case: EndCaseCRF instance
    
    Returns:
        dict: Summary information
    """
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


def validate_end_case_completeness(end_case):
    """
    Validate if end case can be marked as completed
    
    Args:
        end_case: EndCaseCRF instance
    
    Returns:
        tuple: (is_valid, error_messages)
    """
    errors = []
    
    if not end_case.all_visits_completed:
        errors.append(_('Not all required visits are completed'))
    
    if end_case.has_early_termination:
        errors.append(_('Study has early termination (withdrawal/incomplete/lost to follow-up)'))
    
    if not end_case.ENDDATE:
        errors.append(_('End date is required'))
    
    return (len(errors) == 0, errors)


def get_visit_completion_status(end_case):
    """
    Get detailed visit completion status
    
    Args:
        end_case: EndCaseCRF instance
    
    Returns:
        list: Visit status information
    """
    if not end_case:
        return []
    
    visits = [
        {
            'name': 'V1 (Enrollment)',
            'completed': end_case.VICOMPLETED,
            'icon': '✓' if end_case.VICOMPLETED else '✗'
        },
        {
            'name': 'V2 (Day 10±3)',
            'completed': end_case.V2COMPLETED,
            'icon': '✓' if end_case.V2COMPLETED else '✗'
        },
        {
            'name': 'V3 (Day 28±3)',
            'completed': end_case.V3COMPLETED,
            'icon': '✓' if end_case.V3COMPLETED else '✗'
        },
        {
            'name': 'V4 (Day 90±3)',
            'completed': end_case.V4COMPLETED,
            'icon': '✓' if end_case.V4COMPLETED else '✗'
        }
    ]
    
    return visits