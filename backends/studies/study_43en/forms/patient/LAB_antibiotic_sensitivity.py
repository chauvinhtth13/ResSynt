# backends/studies/study_43en/forms/LAB_antibiotic_sensitivity.py
"""
Forms for Antibiotic Sensitivity Testing with Semantic IDs

Features:
- Auto-generation of WHONET_CODE
- Auto-generation of AST_ID
- MIC parsing and validation
- Culture eligibility validation
- Inline formset support
"""

from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Q
import re
from backends.studies.study_43en.models.patient import (
    LAB_Microbiology,
    AntibioticSensitivity,
)
WHONET_CODES = {
    # Tier 1 - Access Group (11 antibiotics)
    'Ampicillin': 'AMP',
    'Cefazolin': 'CZO',
    'Cefotaxime': 'CTX',
    'Ceftriaxone': 'CRO',
    'AmoxicillinClavulanate': 'AMC',
    'AmpicillinSulbactam': 'SAM',
    'PiperacillinTazobactam': 'TZP',
    'Gentamicin': 'GEN',
    'Ciprofloxacin': 'CIP',
    'Levofloxacin': 'LVX',
    'TrimethoprimSulfamethoxazole': 'SXT',
    
    # Tier 2 - Watch Group (10 antibiotics)
    'Cefuroxime': 'CXM',
    'Cefepime': 'FEP',
    'Ertapenem': 'ETP',
    'Imipenem': 'IPM',
    'Meropenem': 'MEM',
    'Amikacin': 'AMK',
    'Tobramycin': 'TOB',
    'Cefotetan': 'CTT',
    'Cefoxitin': 'FOX',
    'Tetracycline': 'TCY',
    
    # Tier 3 - Reserve Group (5 antibiotics)
    'Cefiderocol': 'FDC',
    'CeftazidimeAvibactam': 'CZA',
    'ImipenemRelebactam': 'IMR',
    'MeropenemVaborbactam': 'MEV',
    'Plazomicin': 'PLZ',
    
    # Tier 4 - Specialized (4 antibiotics)
    'Aztreonam': 'ATM',
    'Ceftaroline': 'CPT',
    'Ceftazidime': 'CAZ',
    'CeftolozaneTazobactam': 'CZT',
    
    # Urine-Specific (3 antibiotics)
    #  FIX: Use different code for urine-specific Cefazolin to avoid duplicate AST_ID
    'CefazolinUrine': 'CZO-U',  # Different from regular Cefazolin (CZO)
    'Nitrofurantoin': 'NIT',
    'Fosfomycin': 'FOS',
    
    # Colistin (1 antibiotic - last resort)
    'Colistin': 'COL',
}

# ==========================================
# ANTIBIOTIC SENSITIVITY TEST FORM
# ==========================================

class AntibioticSensitivityForm(forms.ModelForm):
    """
    Form for individual antibiotic sensitivity test
    
    Features:
    - Auto-generation of WHONET_CODE
    - Auto-generation of AST_ID
    - MIC parsing and validation
    - Culture eligibility validation
    """
    
    class Meta:
        model = AntibioticSensitivity
        fields = [
            'ANTIBIOTIC_NAME',
            'OTHER_ANTIBIOTIC_NAME',
            'TIER',
            'SENSITIVITY_LEVEL',
            'MIC',
            'IZDIAM',
            'TESTDATE',
            'INTERPRETATION_STANDARD',
            'NOTES',
        ]
        widgets = {
            'ANTIBIOTIC_NAME': forms.Select(attrs={
                'class': 'form-control antibiotic-select',
                'required': True,
                'data-toggle': 'other-antibiotic-field'
            }),
            'OTHER_ANTIBIOTIC_NAME': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Specify antibiotic name'),
                'maxlength': 100
            }),
            'TIER': forms.Select(attrs={
                'class': 'form-control tier-select',
                'required': True
            }),
            'SENSITIVITY_LEVEL': forms.Select(attrs={
                'class': 'form-control sensitivity-select',
                'required': True
            }),
            'MIC': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., "0.5", "<=0.25", ">64"'),
                'maxlength': 20
            }),
            'IZDIAM': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': _('Zone diameter (mm)'),
                'min': '0',
                'max': '100',
                'step': '0.1'
            }),
            'TESTDATE': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control datepicker',
                'placeholder': 'YYYY-MM-DD'
            }),
            'INTERPRETATION_STANDARD': forms.Select(attrs={
                'class': 'form-control'
            }),
            'NOTES': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('QC notes, technical issues, etc.')
            }),
        }
        help_texts = {
            'ANTIBIOTIC_NAME': _('Select antibiotic tested'),
            'TIER': _('WHO AWaRe classification'),
            'SENSITIVITY_LEVEL': _('S=Sensitive, I=Intermediate, R=Resistant, U=Unknown, ND=Not Determined'),
            'MIC': _('Minimum Inhibitory Concentration (auto-parsed to numeric)'),
            'IZDIAM': _('Disk diffusion zone diameter'),
        }
    
    def __init__(self, *args, **kwargs):
        self.culture = kwargs.pop('culture', None)
        super().__init__(*args, **kwargs)
        
        # Get culture from instance if not provided
        if not self.culture and self.instance and self.instance.pk:
            self.culture = self.instance.LAB_CULTURE_ID
        
        # Make optional fields
        optional_fields = [
            'OTHER_ANTIBIOTIC_NAME', 'MIC', 'IZDIAM', 
            'TESTDATE', 'NOTES'
        ]
        for field_name in optional_fields:
            if field_name in self.fields:
                self.fields[field_name].required = False
        
        # Set culture instance
        if not self.instance.pk and self.culture:
            self.instance.LAB_CULTURE_ID = self.culture
        
        # Add WHONET code preview to antibiotic field
        if 'ANTIBIOTIC_NAME' in self.fields:
            help_text_lines = ['Select antibiotic (WHONET codes):']
            for abx_name, abx_label in AntibioticSensitivity.AntibioticChoices.choices[:15]:
                whonet = WHONET_CODES.get(abx_name, abx_name[:3].upper())
                help_text_lines.append(f'  • {abx_label} → {whonet}')
            help_text_lines.append('  ... (and more)')
            
            self.fields['ANTIBIOTIC_NAME'].help_text = '\n'.join(help_text_lines)
    
    def clean(self):
        """Comprehensive validation"""
        cleaned_data = super().clean()
        
        antibiotic_name = cleaned_data.get('ANTIBIOTIC_NAME')
        other_antibiotic = cleaned_data.get('OTHER_ANTIBIOTIC_NAME')
        sensitivity = cleaned_data.get('SENSITIVITY_LEVEL')
        mic = cleaned_data.get('MIC')
        test_date = cleaned_data.get('TESTDATE')
        
        # 1. Validate culture eligibility
        if self.culture:
            if not self.culture.is_testable_for_antibiotics:
                raise ValidationError(
                    _(' Cannot create antibiotic test: Culture %(culture_id)s '
                      'is not positive for Klebsiella pneumoniae. '
                      'Antibiotic testing is only available for KPN+ cultures.'),
                    params={'culture_id': self.culture.LAB_CULTURE_ID},
                    code='culture_not_eligible'
                )
        
        # 2. Validate "Other" antibiotic
        if antibiotic_name == AntibioticSensitivity.AntibioticChoices.OTHER:
            if not other_antibiotic or not other_antibiotic.strip():
                self.add_error('OTHER_ANTIBIOTIC_NAME',
                    _('Please specify the antibiotic name when "Other" is selected'))
        
        # 3. Validate MIC format
        if mic:
            if not re.match(r'^[<>=]*\d+\.?\d*(-\d+\.?\d*)?$', mic.strip()):
                self.add_error('MIC',
                    _('Invalid MIC format. Examples: "0.5", "<=0.25", ">64", "1-2"'))
        
        # 4. Validate test date
        if test_date and self.culture and self.culture.SPECSAMPDATE:
            if test_date < self.culture.SPECSAMPDATE:
                self.add_error('TESTDATE',
                    _('Test date cannot be before specimen sample date (%(sample_date)s)'),
                    params={'sample_date': self.culture.SPECSAMPDATE}
                )
        
        # 5. Result consistency warnings
        if sensitivity == 'R' and mic:
            try:
                mic_clean = re.sub(r'^[<>=]+', '', mic.strip())
                mic_numeric = float(mic_clean.split('-')[0])
                if mic_numeric < 2:
                    # Warning only - don't block save
                    pass
            except (ValueError, IndexError):
                pass
        
        return cleaned_data
    
    def clean_OTHER_ANTIBIOTIC_NAME(self):
        """Normalize other antibiotic name"""
        value = self.cleaned_data.get('OTHER_ANTIBIOTIC_NAME')
        return value.strip().title() if value else value
    
    def clean_MIC(self):
        """Normalize MIC format"""
        value = self.cleaned_data.get('MIC')
        if value:
            return value.strip().replace(' ', '')
        return value
    
    def clean_NOTES(self):
        """Normalize notes"""
        value = self.cleaned_data.get('NOTES')
        return value.strip() if value else value


# ==========================================
# INLINE FORMSET FOR ANTIBIOTIC TESTS
# ==========================================

AntibioticSensitivityInlineFormSet = inlineformset_factory(
    LAB_Microbiology,
    AntibioticSensitivity,
    form=AntibioticSensitivityForm,
    fk_name='LAB_CULTURE_ID',
    extra=1,  # Show 1 empty form
    can_delete=True,
    can_order=False,
    max_num=50,  # Max 50 antibiotics per culture
    validate_max=True,
)


# ==========================================
# FILTER FORM
# ==========================================

class AntibioticSensitivityFilterForm(forms.Form):
    """Filter form for antibiotic sensitivity tests"""
    
    tier = forms.ChoiceField(
        choices=[('', _('All Tiers'))] + list(AntibioticSensitivity.TierChoices.choices),
        required=False,
        label=_('Antibiotic Tier'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    sensitivity = forms.ChoiceField(
        choices=[('', _('All Results'))] + list(AntibioticSensitivity.SensitivityChoices.choices),
        required=False,
        label=_('Sensitivity Level'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    antibiotic = forms.ChoiceField(
        choices=[('', _('All Antibiotics'))],
        required=False,
        label=_('Antibiotic'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    resistant_only = forms.BooleanField(
        required=False,
        label=_('Show Resistant Only'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate antibiotic choices dynamically
        self.fields['antibiotic'].choices = (
            [('', _('All Antibiotics'))] +
            list(AntibioticSensitivity.AntibioticChoices.choices[:25])  # Top 25
        )


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_antibiotic_resistance_profile(culture):
    """
    Get detailed resistance profile for a culture
    
     FIX: Always show ALL standard antibiotics for the specimen type
    - If data exists: show the actual data
    - If no data: show as ND (Not Determined) for user to fill in
    
    Args:
        culture: LAB_Microbiology instance
    
    Returns:
        dict with resistance profile by tier or None if not testable
    """
    if not culture.is_testable_for_antibiotics:
        return None
    
    # Get database from culture instance
    using = culture._state.db or 'db_study_43en'
    
    #  Define ALL standard antibiotics by tier 
    STANDARD_ANTIBIOTICS = {
        'Tier1': [
            'Ampicillin',
            'Cefazolin',
            'Cefotaxime',
            'Ceftriaxone',
            'AmoxicillinClavulanate',
            'AmpicillinSulbactam',
            'PiperacillinTazobactam',
            'Gentamicin',
            'Ciprofloxacin',
            'Levofloxacin',
            'TrimethoprimSulfamethoxazole',
        ],
        'Tier2': [
            'Cefuroxime',
            'Cefepime',
            'Ertapenem',
            'Imipenem',
            'Meropenem',
            'Amikacin',
            'Tobramycin',
            'Cefotetan',
            'Cefoxitin',
            'Tetracycline',
        ],
        'Tier3': [
            'Cefiderocol',
            'CeftazidimeAvibactam',
            'ImipenemRelebactam',
            'MeropenemVaborbactam',
            'Plazomicin',
        ],
        'Tier4': [
            'Aztreonam',
            'Ceftaroline',
            'Ceftazidime',
            'CeftolozaneTazobactam',
        ],
    }
    
    # Add urine-specific if specimen is urine
    if culture.SPECSAMPLOC == 'URINE':
        STANDARD_ANTIBIOTICS['UrineOnly'] = [
            'CefazolinUrine',
            'Nitrofurantoin',
            'Fosfomycin',
        ]
    
    # Colistin - for all specimens (last resort)
    STANDARD_ANTIBIOTICS['Colistin'] = ['Colistin']
    
    #  Get existing tests from database
    existing_tests = AntibioticSensitivity.objects.using(using).filter(
        LAB_CULTURE_ID=culture
    ).select_related('LAB_CULTURE_ID')
    
    # Create a lookup dict: antibiotic_name -> test object
    existing_tests_dict = {test.ANTIBIOTIC_NAME: test for test in existing_tests}
    
    #  Build complete profile with ALL standard antibiotics
    tests_by_tier = {}
    
    for tier_code, tier_label in AntibioticSensitivity.TierChoices.choices:
        if tier_code == 'Other':
            # Skip "Other" tier in standard list
            # But include any existing "Other" antibiotics from database
            other_tests = [t for t in existing_tests if t.TIER == 'Other']
            if other_tests:
                tests_by_tier[tier_code] = {
                    'label': tier_label,
                    'tests': sorted(other_tests, key=lambda t: t.WHONET_CODE)
                }
            continue
        
        # Get standard antibiotics for this tier
        standard_abx_list = STANDARD_ANTIBIOTICS.get(tier_code, [])
        
        if not standard_abx_list:
            continue
        
        # Build test list: use existing or create placeholder
        tier_tests = []
        for abx_name in standard_abx_list:
            if abx_name in existing_tests_dict:
                # Use existing test
                tier_tests.append(existing_tests_dict[abx_name])
            else:
                #  Create virtual placeholder object (not saved to DB)
                # This will be displayed as ND and user can fill it in
                placeholder = AntibioticSensitivity(
                    LAB_CULTURE_ID=culture,
                    ANTIBIOTIC_NAME=abx_name,
                    TIER=tier_code,
                    SENSITIVITY_LEVEL='ND',
                    WHONET_CODE=WHONET_CODES.get(abx_name, abx_name[:3].upper()),
                )
                # Generate AST_ID for display
                placeholder.AST_ID = f"{culture.LAB_CULTURE_ID}-{placeholder.WHONET_CODE}"
                tier_tests.append(placeholder)
        
        # Add to profile
        if tier_tests:
            tests_by_tier[tier_code] = {
                'label': tier_label,
                'tests': tier_tests
            }
    
    # Get summary statistics (only from actual saved tests)
    summary = culture.get_resistance_summary()
    
    return {
        'culture_id': culture.LAB_CULTURE_ID,
        'specimen': culture.get_SPECSAMPLOC_display(),
        'sample_date': culture.SPECSAMPDATE,
        'tests_by_tier': tests_by_tier,  # Complete list with placeholders
        'summary': summary,
        'total_tests': existing_tests.count(),  # Count of actual saved tests
    }


def get_resistance_statistics(usubjid):
    """
    Get comprehensive resistance statistics for a patient
    
    Args:
        usubjid: ENR_CASE instance
    
    Returns:
        dict with resistance statistics
    """
    tests = AntibioticSensitivity.objects.filter(
        LAB_CULTURE_ID__USUBJID=usubjid
    )
    
    total_tests = tests.count()
    
    if total_tests == 0:
        return {
            'total_tests': 0,
            'by_sensitivity': {},
            'by_tier': {},
            'by_antibiotic': {},
            'carbapenem_resistance': False,
        }
    
    # By sensitivity level
    by_sensitivity = {}
    for sens_code, sens_label in AntibioticSensitivity.SensitivityChoices.choices:
        count = tests.filter(SENSITIVITY_LEVEL=sens_code).count()
        if count > 0:
            by_sensitivity[sens_code] = {
                'label': sens_label,
                'count': count,
                'percentage': round(count / total_tests * 100, 1)
            }
    
    # By tier
    by_tier = {}
    for tier_code, tier_label in AntibioticSensitivity.TierChoices.choices:
        tier_tests = tests.filter(TIER=tier_code)
        count = tier_tests.count()
        if count > 0:
            resistant = tier_tests.filter(SENSITIVITY_LEVEL='R').count()
            by_tier[tier_code] = {
                'label': tier_label,
                'count': count,
                'resistant': resistant,
                'resistance_rate': round(resistant / count * 100, 1) if count > 0 else 0
            }
    
    # Top resistant antibiotics
    resistant_tests = tests.filter(SENSITIVITY_LEVEL='R')
    by_antibiotic = (
        resistant_tests
        .values('ANTIBIOTIC_NAME')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )
    
    # Carbapenem resistance check
    carbapenem_names = ['Imipenem', 'Meropenem', 'Ertapenem']
    carbapenem_resistant = tests.filter(
        ANTIBIOTIC_NAME__in=carbapenem_names,
        SENSITIVITY_LEVEL='R'
    ).exists()
    
    return {
        'total_tests': total_tests,
        'by_sensitivity': by_sensitivity,
        'by_tier': by_tier,
        'top_resistant_antibiotics': list(by_antibiotic),
        'carbapenem_resistance': carbapenem_resistant,
    }


def validate_antibiotic_panel(culture, antibiotic_list):
    """
    Validate that a panel of antibiotics can be tested for a culture
    
    Args:
        culture: LAB_Microbiology instance
        antibiotic_list: List of antibiotic names
    
    Returns:
        tuple: (is_valid, error_messages)
    """
    errors = []
    
    # Check culture eligibility
    if not culture.is_testable_for_antibiotics:
        errors.append(
            f'Culture {culture.LAB_CULTURE_ID} is not eligible for antibiotic testing '
            '(must be positive for Klebsiella)'
        )
        return (False, errors)
    
    # Check for duplicates
    if len(antibiotic_list) != len(set(antibiotic_list)):
        duplicates = [abx for abx in antibiotic_list if antibiotic_list.count(abx) > 1]
        errors.append(f'Duplicate antibiotics: {", ".join(set(duplicates))}')
    
    # Check if already tested
    existing_tests = AntibioticSensitivity.objects.filter(
        LAB_CULTURE_ID=culture,
        ANTIBIOTIC_NAME__in=antibiotic_list
    ).values_list('ANTIBIOTIC_NAME', flat=True)
    
    if existing_tests:
        errors.append(
            f'Already tested: {", ".join(existing_tests)}'
        )
    
    return (len(errors) == 0, errors)