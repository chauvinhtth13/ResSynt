# backends/studies/study_43en/forms/personal_data_forms.py

"""
Personal Data Forms - Separated for Better Security
====================================================

These forms handle PII (Personally Identifiable Information)
Should be used with extra security measures in views
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from backends.studies.study_43en.models.patient.PER_DATA import (
    PERSONAL_DATA
)


# ==========================================
# PATIENT PERSONAL DATA FORM
# ==========================================

class PersonalDataForm(forms.ModelForm):
    """
    Patient PII form with enhanced security
    
    Contains:
    - Full name, Phone, Medical Record ID
    - Address fields (new and old systems)
    - Primary address selection
    """
    
    class Meta:
        model = PERSONAL_DATA
        exclude = [
            'USUBJID',
            'last_modified_by_id',
            'last_modified_by_username',
            'last_modified_at',
            'created_at',
            'version',
        ]
        widgets = {
            # Personal identifiers
            'FULLNAME': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter full name'),
                'autocomplete': 'off',  # Security: disable autocomplete
            }),
            'PHONE': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter phone number'),
                'autocomplete': 'off',
            }),
            'MEDRECORDID': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter medical record number'),
                'autocomplete': 'off',
            }),
            
            # Address system selection
            'PRIMARY_ADDRESS': forms.RadioSelect(
                choices=[
                    ('new', 'Chỉ địa chỉ mới'),
                    ('old', 'Chỉ địa chỉ cũ'),
                    ('both', 'Cả hai địa chỉ')
                ],
                attrs={'class': 'primary-address-radio'}
            ),
            
            # NEW ADDRESS FIELDS
            'STREET_NEW': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ví dụ: 123 Đường Nguyễn Văn Linh',
                'autocomplete': 'off',
            }),
            'WARD_NEW': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ví dụ: Phường Tân Thuận Đông',
                'autocomplete': 'off',
            }),
            'CITY_NEW': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ví dụ: TP. Hồ Chí Minh',
                'autocomplete': 'off',
            }),
            
            # OLD ADDRESS FIELDS
            'STREET': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ví dụ: 123 Đường Trần Hưng Đạo',
                'autocomplete': 'off',
            }),
            'WARD': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ví dụ: Phường Bến Nghé (cũ)',
                'autocomplete': 'off',
            }),
            'DISTRICT': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ví dụ: Quận 1 (cũ)',
                'autocomplete': 'off',
            }),
            'PROVINCECITY': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ví dụ: TP. Hồ Chí Minh',
                'autocomplete': 'off',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Apply form-control class to all fields
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'
    
    def clean(self):
        """
        Basic validation - allow all address fields to be optional
        """
        cleaned_data = super().clean()
        # No strict validation - allow all fields to be null/empty
        return cleaned_data


