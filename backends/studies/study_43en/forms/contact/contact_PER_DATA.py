# backends/studies/study_43en/forms/contact_PER_DATA.py

"""
Personal Data Forms - Separated for Better Security
====================================================

These forms handle PII (Personally Identifiable Information)
Should be used with extra security measures in views
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from backends.studies.study_43en.models.contact.PER_CONTACT_DATA import (
    PERSONAL_CONTACT_DATA
)

# ==========================================
# CONTACT PERSONAL DATA FORM
# ==========================================

class PersonalContactDataForm(forms.ModelForm):
    """
    Contact PII form with enhanced security
    
    Contains:
    - Full name, Phone
    
    Simpler than patient form (no address, no medical record ID)
    """
    
    class Meta:
        model = PERSONAL_CONTACT_DATA
        exclude = [
            'USUBJID',
            'last_modified_by_id',
            'last_modified_by_username',
            'last_modified_at',
            'created_at',
            'version',
        ]
        widgets = {
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
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Apply form-control class
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
    
    def clean(self):
        """
        Basic validation - allow all fields to be optional
        """
        cleaned_data = super().clean()
        # No strict validation - allow all fields to be null/empty
        return cleaned_data