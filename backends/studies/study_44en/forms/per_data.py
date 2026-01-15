# backends/studies/study_44en/forms/per_data.py

from django import forms
from django.utils.translation import gettext_lazy as _
from backends.studies.study_44en.models.per_data import HH_PERSONAL_DATA


class HH_PersonalDataForm(forms.ModelForm):
    """Household personal data (address) form"""
    
    class Meta:
        model = HH_PERSONAL_DATA
        fields = ['HOUSE_NUMBER', 'STREET', 'WARD', 'CITY']
        widgets = {
            'HOUSE_NUMBER': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('House number, building, apartment')
            }),
            'STREET': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Street/Road Name')
            }),
            'WARD': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Ward/Commune')
            }),
            'CITY': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('City'),
                'value': 'Ho Chi Minh City'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default city
        if not self.instance.pk and not self.initial.get('CITY'):
            self.initial['CITY'] = 'Ho Chi Minh City'