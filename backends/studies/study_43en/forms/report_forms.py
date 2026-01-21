# backends/studies/study_43en/forms/report_forms.py
"""
Report Export Forms

Forms for selecting report parameters and manual input.
Server-side validation only, no JavaScript.
"""

from django import forms
from datetime import datetime, timedelta


class ReportExportForm(forms.Form):
    """
    Form chọn tham số xuất báo cáo TMG
    
    Validation hoàn toàn ở server-side
    Không cần JavaScript
    """
    
    REPORT_TYPE_CHOICES = [
        ('monthly', 'Monthly Report'),
        ('quarterly', 'Quarterly Report'),
        ('custom', 'Custom Date Range'),
    ]
    
    EXPORT_FORMAT_CHOICES = [
        ('docx', 'Word Document (.docx)'),
        ('pdf', 'PDF Document (.pdf)'),
    ]
    
    # ==========================================
    # REPORT SETTINGS
    # ==========================================
    export_format = forms.ChoiceField(
        choices=EXPORT_FORMAT_CHOICES,
        initial='docx',
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        }),
        label='Export Format'
    )
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPE_CHOICES,
        initial='monthly',
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        }),
        label='Report Type'
    )
    
    reporting_date = forms.DateField(
        initial=datetime.now,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label='Reporting Date (displayed on report)'
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label='Start Date',
        help_text='For custom range only'
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label='End Date',
        help_text='For custom range only'
    )
    
    # ==========================================
    # SECTION TOGGLES
    # ==========================================
    include_recruitment = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Include Recruitment Statistics (auto-generated from database)'
    )
    
    include_samples = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Include Sample Processing Statistics (auto-generated from database)'
    )
    
    include_safety = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Include Safety Reporting Statistics (auto-generated from database)'
    )
    
    # ==========================================
    # MANUAL INPUT SECTIONS
    # ==========================================
    action_points_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter action points, one per line:\nAction | Actioned By | Status\nExample: Review protocol | Dr. Nguyen | Ongoing'
        }),
        label='1. Outstanding Action Points',
        help_text='Format: Action | Actioned By | Status (one per line)'
    )
    
    general_procedures = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter general trial procedures notes...'
        }),
        label='2. General Trial Procedures'
    )
    
    ethics_regulatory = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'List details of ethics/regulatory submissions or amendments...'
        }),
        label='3. Ethics & Regulatory'
    )
    
    study_amendments = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter study amendments...'
        }),
        label='4. Study Amendments'
    )
    
    deviations_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter protocol deviations, one per line:\nSubject ID | Deviation | Violation? | Action\nExample: 003-A-001 | Missed blood draw | No | Rescheduled'
        }),
        label='6. Protocol Deviations/Violations',
        help_text='Format: Subject ID | Deviation | Violation? | Action (one per line)'
    )
    
    data_management = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter data management notes...'
        }),
        label='8. Data Management'
    )
    
    aob = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Any other business...'
        }),
        label='10. AOB (Any Other Business)'
    )
    
    def clean(self):
        """Server-side validation"""
        cleaned_data = super().clean()
        report_type = cleaned_data.get('report_type')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if report_type == 'custom':
            if not start_date:
                self.add_error('start_date', 'Start date is required for custom range.')
            if not end_date:
                self.add_error('end_date', 'End date is required for custom range.')
            if start_date and end_date and start_date > end_date:
                self.add_error('end_date', 'End date must be after start date.')
        
        return cleaned_data
    
    def get_date_range(self) -> tuple:
        """
        Tính toán date range dựa trên report type
        
        Returns:
            Tuple of (start_date, end_date)
        """
        report_type = self.cleaned_data['report_type']
        reporting_date = self.cleaned_data['reporting_date']
        
        if report_type == 'monthly':
            # Get previous month
            first_of_month = reporting_date.replace(day=1)
            end_date = first_of_month - timedelta(days=1)
            start_date = end_date.replace(day=1)
        
        elif report_type == 'quarterly':
            # Get previous quarter
            current_quarter = (reporting_date.month - 1) // 3
            if current_quarter == 0:
                # Q4 of previous year
                start_date = datetime(reporting_date.year - 1, 10, 1).date()
                end_date = datetime(reporting_date.year - 1, 12, 31).date()
            else:
                quarter_start_month = (current_quarter - 1) * 3 + 1
                quarter_end_month = quarter_start_month + 2
                start_date = datetime(reporting_date.year, quarter_start_month, 1).date()
                
                # Calculate end of quarter
                if quarter_end_month == 12:
                    end_date = datetime(reporting_date.year, 12, 31).date()
                else:
                    next_month = datetime(reporting_date.year, quarter_end_month + 1, 1).date()
                    end_date = next_month - timedelta(days=1)
        
        else:  # custom
            start_date = self.cleaned_data['start_date']
            end_date = self.cleaned_data['end_date']
        
        return start_date, end_date
    
    def parse_action_points(self) -> list:
        """
        Parse action points from text input
        
        Returns:
            List of dicts with action, actioned_by, complete
        """
        text = self.cleaned_data.get('action_points_text', '')
        if not text.strip():
            return []
        
        action_points = []
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 3:
                action_points.append({
                    'action': parts[0],
                    'actioned_by': parts[1],
                    'complete': parts[2]
                })
            elif len(parts) == 2:
                action_points.append({
                    'action': parts[0],
                    'actioned_by': parts[1],
                    'complete': 'Pending'
                })
            else:
                action_points.append({
                    'action': parts[0],
                    'actioned_by': '',
                    'complete': 'Pending'
                })
        
        return action_points
    
    def parse_deviations(self) -> list:
        """
        Parse protocol deviations from text input
        
        Returns:
            List of dicts with subject_id, deviation, violation, action
        """
        text = self.cleaned_data.get('deviations_text', '')
        if not text.strip():
            return []
        
        deviations = []
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                deviations.append({
                    'subject_id': parts[0],
                    'deviation': parts[1],
                    'violation': parts[2],
                    'action': parts[3]
                })
            elif len(parts) == 3:
                deviations.append({
                    'subject_id': parts[0],
                    'deviation': parts[1],
                    'violation': parts[2],
                    'action': ''
                })
            elif len(parts) == 2:
                deviations.append({
                    'subject_id': parts[0],
                    'deviation': parts[1],
                    'violation': 'No',
                    'action': ''
                })
        
        return deviations
