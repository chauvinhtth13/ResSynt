from django import forms
from django.utils.translation import gettext_lazy as _
from datetime import date
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.core.exceptions import ValidationError

# Import models
from backends.studies.study_43en.models.patient import (
    CLI_CASE,
    HistorySymptom,
    Symptom_72H,
    PriorAntibiotic,
    InitialAntibiotic,
    MainAntibiotic,
    VasoIDrug,
    ImproveSympt,
    HospiProcess,
    AEHospEvent,
)
from backends.studies.study_43en.models.base_models import get_department_choices

# ==========================================
# CLINICAL CASE FORM (MAIN)
# ==========================================

class ClinicalCaseForm(forms.ModelForm):
    """
    Main clinical case form
    
    Optimizations:
    - Optimistic locking with version field
    - ArrayField handling for SUPPORTTYPE
    - Proper widget configuration
    - UI-only validation (business logic in model)
    """
    
    # Version field for optimistic locking
    version = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
        initial=0
    )
    # NOTE: NEWS2_RANGE is handled purely in template/JS, not a model field
    # Only NEWS2 (the actual score) is saved to database
    
    # MultipleChoiceField for ArrayField
    SUPPORTTYPE = forms.MultipleChoiceField(
        choices=[
            ('Oxy mÅ©i/mask', _('Nasal Cannula/Mask')),
            ('HFNC/NIV', _('HFNC/NIV')),
            ('Thá»Ÿ mÃ¡y', _('Mechanical Ventilation')),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label=_("Respiratory Support Type")
    )

    class Meta:
        model = CLI_CASE
        exclude = ['USUBJID']  # USUBJID set by view

    class Meta:
        model = CLI_CASE
        exclude = ['USUBJID']
        
        #  ADD: Labels synced with model verbose_name
        labels = {
            'ADMISDATE': _('Admission Date'),
            'ADMISREASON': _('Reason for Admission'),
            'SYMPTOMONSETDATE': _('Symptom Onset Date'),
            'ADMISDEPT': _('Admission Department'),
            'OUTPATIENT_ERDEPT': _('Outpatient/Emergency Department'),
            'SYMPTOMADMISDEPT': _('Admitting Department'),
            
            # Consciousness
            'AWARENESS': _('Consciousness'),
            'GCS': _('Glasgow Coma Scale (3-15)'),
            'EYES': _('Eye Opening Response (1-4)'),
            'MOTOR': _('Motor Response (1-6)'),
            'VERBAL': _('Verbal Response (1-5)'),
            
            # Vital Signs
            'PULSE': _('Heart Rate (beats/min)'),
            'AMPLITUDE': _('Pulse Amplitude'),
            'CAPILLARYMOIS': _('Capillary Moisture'),
            'CRT': _('Capillary Refill Time (seconds)'),
            'TEMPERATURE': _('Temperature (°C)'),
            'BLOODPRESSURE_SYS': _('Systolic BP (mmHg)'),
            'BLOODPRESSURE_DIAS': _('Diastolic BP (mmHg)'),
            'RESPRATE': _('Respiratory Rate (breaths/min)'),
            'SPO2': _('SpO2 (%)'),
            'FIO2': _('FiO2 (%)'),
            
            # Respiratory
            'RESPPATTERN': _('Respiratory Pattern'),
            'RESPPATTERNOTHERSPEC': _('Other Respiratory Pattern Details'),
            'RESPSUPPORT': _('Respiratory Support'),
            
            # Clinical Scores
            'VASOMEDS': _('Vasopressors'),
            'HYPOTENSION': _('Is there hypotension?'),
            'QSOFA': _('qSOFA Score (0-3)'),
            'NEWS2': _('NEWS2 Score (0-20)'),  #  This is the key label
            
            # Physical Measurements
            'WEIGHT': _('Weight (kg)'),
            'HEIGHT': _('Height (cm)'),
            'BMI': _('Body Mass Index'),
            
            # Infection
            'INFECTFOCUS48H': _('Infection Site (within 48h)'),
            'SPECIFYOTHERINFECT48H': _('Other, specify'),
            'BLOODINFECT': _('Bloodstream infection?'),
            'SOFABASELINE': _('Background SOFA score'),
            'DIAGSOFA': _('SOFA score at diagnosis'),
            'SEPTICSHOCK': _('Septic Shock?'),
            'INFECTSRC': _('Infection source?'),
            
            # Respiratory Support
            'RESPISUPPORT': _('Respiratory support?'),
            'OXYMASKDURATION': _('Nasal O2/mask, duration (days)'),
            'HFNCNIVDURATION': _('HFNC/NIV, duration (days)'),
            'VENTILATORDURATION': _('Mechanical ventilation, duration (days)'),
            
            # Fluid Resuscitation
            'RESUSFLUID': _('Resuscitation fluids?'),
            'FLUID6HOURS': _('Total fluid infusion (first 6 hours)'),
            'CRYSTAL6HRS': _('Crystalloid (ml)'),
            'COL6HRS': _('Colloid (ml)'),
            'FLUID24HOURS': _('Total fluid infusion (first 24 hours)'),
            'CRYSTAL24HRS': _('Crystalloid (ml)'),
            'COL24HRS': _('Colloid (ml)'),
            
            # Other Treatments
            'VASOINOTROPES': _('Vasomotor/increased myocardial contractility?'),
            'DIALYSIS': _('Blood filtration?'),
            'DRAINAGE': _('Drainage?'),
            'DRAINAGETYPE': _('Drainage Type'),
            'SPECIFYOTHERDRAINAGE': _('Other, specify'),
            
            # Antibiotics
            'PRIORANTIBIOTIC': _('Prior Antibiotic Use'),
            'INITIALANTIBIOTIC': _('Initial Antibiotic Given'),
            'INITIALABXAPPROP': _('Initial Antibiotic Appropriate'),
        }

        widgets = {
            # Date widgets
            'ADMISDATE': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'placeholder': 'YYYY-MM-DD'
            }),
            'SYMPTOMONSETDATE': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'placeholder': 'YYYY-MM-DD'
            }),
            
            # Department Select
            'ADMISDEPT': forms.Select(attrs={
                'class': 'form-control',
                'data-placeholder': 'Chọn khoa nhập viện'
            }),
            
            # Select widgets with Select2
            'INFECTFOCUS48H': forms.Select(attrs={'class': 'form-control select2'}),
            'INFECTSRC': forms.Select(attrs={'class': 'form-control select2'}),
            'BLOODINFECT': forms.Select(attrs={'class': 'form-control'}),
            'SEPTICSHOCK': forms.Select(attrs={'class': 'form-control'}),
            'FLUID6HOURS': forms.Select(attrs={'class': 'form-control select2'}),
            'FLUID24HOURS': forms.Select(attrs={'class': 'form-control select2'}),
            'DRAINAGETYPE': forms.Select(attrs={'class': 'form-control select2'}),
            
            # Textarea widgets
            'ADMISREASON': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'SYMPTOMADMISDEPT': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'OUTPATIENT_ERDEPT': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'AWARENESS': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'RESPPATTERNOTHERSPEC': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'SPECIFYOTHERINFECT48H': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'SPECIFYOTHERDRAINAGE': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            
            # Number inputs with validation
            'GCS': forms.NumberInput(attrs={'class': 'form-control', 'min': 3, 'max': 15}),
            'EYES': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 4}),
            'MOTOR': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
            'VERBAL': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'QSOFA': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 3}),
            'NEWS2': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 20}),
            'SOFABASELINE': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 24}),
            'DIAGSOFA': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 24}),
            
            # Vital signs
            'PULSE': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 300}),
            'TEMPERATURE': forms.NumberInput(attrs={'class': 'form-control', 'min': 30, 'max': 45, 'step': 0.1}),
            'BLOODPRESSURE_SYS': forms.NumberInput(attrs={'class': 'form-control', 'min': 40, 'max': 250}),
            'BLOODPRESSURE_DIAS': forms.NumberInput(attrs={'class': 'form-control', 'min': 20, 'max': 150}),
            'RESPRATE': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'SPO2': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'FIO2': forms.NumberInput(attrs={'class': 'form-control', 'min': 21, 'max': 100}),
            
            # Physical measurements
            'WEIGHT': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 300, 'step': 0.1}),
            'HEIGHT': forms.NumberInput(attrs={'class': 'form-control', 'min': 50, 'max': 250, 'step': 0.1}),
            'BMI': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'max': 60, 'step': 0.1}),
            
            # Support durations
            'OXYMASKDURATION': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'HFNCNIVDURATION': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'VENTILATORDURATION': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            
            # Fluid volumes
            'CRYSTAL6HRS': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'COL6HRS': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'CRYSTAL24HRS': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'COL24HRS': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            
            # Boolean fields
            'VASOMEDS': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'HYPOTENSION': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'RESPISUPPORT': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'RESUSFLUID': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'VASOINOTROPES': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'DIALYSIS': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'DRAINAGE': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'PRIORANTIBIOTIC': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'INITIALANTIBIOTIC': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'INITIALABXAPPROP': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, siteid=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get version for optimistic locking
        if self.instance and self.instance.pk:
            self.fields['version'].initial = self.instance.version
            # Get SITEID from related ENR_CASE if not provided
            if not siteid:
                try:
                    siteid = self.instance.USUBJID.SITEID
                except:
                    pass
        
        # Set department choices based on SITEID
        dept_choices = [('', '---------')]  # Empty choice first
        dept_choices.extend(get_department_choices(siteid))
        self.fields['ADMISDEPT'].widget.choices = dept_choices
        
        # Set initial for SUPPORTTYPE (ArrayField)
        if self.instance and self.instance.pk:
            # SUPPORTTYPE is already handled by model
            pass
        
        # Add form-control to all fields without specific class
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'
    
    def clean(self):
        """
        Form validation - only UI-specific checks
        Model.clean() handles business logic
        """
        cleaned_data = super().clean()
        
        # Check version conflict (optimistic locking)
        if self.instance and self.instance.pk:
            submitted_version = cleaned_data.get('version')
            if submitted_version is not None and submitted_version != self.instance.version:
                raise ValidationError(
                    _('This record has been modified by another user. Please reload and try again.'),
                    code='version_conflict'
                )
        
        # Let Model.clean() handle the rest
        return cleaned_data
    
    def save(self, commit=True):
        """Handle ArrayField SUPPORTTYPE"""
        instance = super().save(commit=False)
        
        # SUPPORTTYPE is MultipleChoiceField â†’ list
        # Django should handle this automatically, but ensure it's set
        supporttype_data = self.cleaned_data.get('SUPPORTTYPE', [])
        if supporttype_data:
            instance.SUPPORTTYPE = supporttype_data
        else:
            instance.SUPPORTTYPE = []
        
        if commit:
            instance.save()
        return instance


# ==========================================
# HISTORY SYMPTOM FORM (1-1 with CLI_CASE)
# ==========================================

class HistorySymptomForm(forms.ModelForm):
    """
    Form for patient symptoms at admission
    OneToOne relationship with CLI_CASE
    """
    
    class Meta:
        model = HistorySymptom
        exclude = ['USUBJID']  # Set by view
        widgets = {
            'SPECIFYOTHERSYMPTOM': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Specify other symptoms')
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add class for all checkboxes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
    
    def clean(self):
        """Validate other symptom specification"""
        cleaned_data = super().clean()
        
        if cleaned_data.get('OTHERSYMPTOM'):
            if not cleaned_data.get('SPECIFYOTHERSYMPTOM', '').strip():
                raise ValidationError({
                    'SPECIFYOTHERSYMPTOM': _('Please specify other symptoms when checked')
                })
        
        return cleaned_data


# ==========================================
# SYMPTOM 72H FORM (1-1 with CLI_CASE)
# ==========================================

class Symptom72HForm(forms.ModelForm):
    """
    Form for clinical examination findings within 72 hours
    OneToOne relationship with CLI_CASE
    """
    
    class Meta:
        model = Symptom_72H
        exclude = ['USUBJID']  # Set by view
        widgets = {
            'SPECIFYOTHERSYMPTOM_2': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Specify other clinical findings')
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add class for all checkboxes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
    
    def clean(self):
        """Validate other symptom specification"""
        cleaned_data = super().clean()
        
        if cleaned_data.get('OTHERSYMPTOM_2'):
            if not cleaned_data.get('SPECIFYOTHERSYMPTOM_2', '').strip():
                raise ValidationError({
                    'SPECIFYOTHERSYMPTOM_2': _('Please specify other findings when checked')
                })
        
        return cleaned_data


# ==========================================
# ANTIBIOTIC FORMS (1-N with CLI_CASE)
# ==========================================

class BaseSEQUENCEForm(forms.ModelForm):
    """Base class for forms with SEQUENCE field"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # SEQUENCE is auto-generated and hidden, not required for validation
        if 'SEQUENCE' in self.fields:
            self.fields['SEQUENCE'].required = False


class PriorAntibioticForm(BaseSEQUENCEForm):
    """Form for prior antibiotics"""
    
    class Meta:
        model = PriorAntibiotic
        fields = ['SEQUENCE', 'PRIORANTIBIONAME', 'PRIORANTIBIODOSAGE', 
                  'PRIORANTIBIOSTARTDTC', 'PRIORANTIBIOENDDTC']
        widgets = {
            'SEQUENCE': forms.HiddenInput(),  # Hidden field to ensure value is submitted
            'PRIORANTIBIONAME': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Antibiotic name')
            }),
            'PRIORANTIBIODOSAGE': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Dosage')
            }),
            'PRIORANTIBIOSTARTDTC': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'placeholder': 'YYYY-MM-DD'
            }),
            'PRIORANTIBIOENDDTC': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'placeholder': 'YYYY-MM-DD'
            }),
        }
    
    def clean_PRIORANTIBIONAME(self):
        """
        Normalize antibiotic name
         FIX: Allow empty if entire form is empty (extra form not used)
        """
        name = self.cleaned_data.get('PRIORANTIBIONAME', '') or ''
        name = name.strip()
        
        #  Check if ANY other field has data
        has_other_data = any([
            self.cleaned_data.get('PRIORANTIBIODOSAGE'),
            self.cleaned_data.get('PRIORANTIBIOSTARTDTC'),
            self.cleaned_data.get('PRIORANTIBIOENDDTC'),
        ])
        
        # Only require name if there's other data OR name itself is provided
        if not name and has_other_data:
            raise ValidationError(_('Antibiotic name is required when other fields are filled'))
        
        return name.title() if name else ''


class InitialAntibioticForm(BaseSEQUENCEForm):
    """Form for initial antibiotics"""
    
    class Meta:
        model = InitialAntibiotic
        fields = ['SEQUENCE', 'INITIALANTIBIONAME', 'INITIALANTIBIODOSAGE', 
                  'INITIALANTIBIOSTARTDTC', 'INITIALANTIBIOENDDTC']
        widgets = {
            'SEQUENCE': forms.HiddenInput(),  # Hidden field to ensure value is submitted
            'INITIALANTIBIONAME': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Antibiotic name')
            }),
            'INITIALANTIBIODOSAGE': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Dosage')
            }),
            'INITIALANTIBIOSTARTDTC': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'placeholder': 'YYYY-MM-DD'
            }),
            'INITIALANTIBIOENDDTC': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'placeholder': 'YYYY-MM-DD'
            }),
        }
    
    def clean_INITIALANTIBIONAME(self):
        """
        Normalize antibiotic name
         FIX: Allow empty if entire form is empty
        """
        name = self.cleaned_data.get('INITIALANTIBIONAME', '') or ''
        name = name.strip()
        
        #  Check if ANY other field has data
        has_other_data = any([
            self.cleaned_data.get('INITIALANTIBIODOSAGE'),
            self.cleaned_data.get('INITIALANTIBIOSTARTDTC'),
            self.cleaned_data.get('INITIALANTIBIOENDDTC'),
        ])
        
        # Only require name if there's other data OR name itself is provided
        if not name and has_other_data:
            raise ValidationError(_('Antibiotic name is required when other fields are filled'))
        
        return name.title() if name else ''


class MainAntibioticForm(BaseSEQUENCEForm):
    """Form for main antibiotics"""
    
    class Meta:
        model = MainAntibiotic
        fields = ['SEQUENCE', 'MAINANTIBIONAME', 'MAINANTIBIODOSAGE', 
                  'MAINANTIBIOSTARTDTC', 'MAINANTIBIOENDDTC']
        widgets = {
            'SEQUENCE': forms.HiddenInput(),  # Hidden field to ensure value is submitted
            'MAINANTIBIONAME': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Antibiotic name')
            }),
            'MAINANTIBIODOSAGE': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Dosage')
            }),
            'MAINANTIBIOSTARTDTC': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'placeholder': 'YYYY-MM-DD'
            }),
            'MAINANTIBIOENDDTC': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'placeholder': 'YYYY-MM-DD'
            }),
        }
    
    def clean_MAINANTIBIONAME(self):
        """
        Normalize antibiotic name
         FIX: Allow empty if entire form is empty
        """
        name = self.cleaned_data.get('MAINANTIBIONAME', '') or ''
        name = name.strip()
        
        #  Check if ANY other field has data
        has_other_data = any([
            self.cleaned_data.get('MAINANTIBIODOSAGE'),
            self.cleaned_data.get('MAINANTIBIOSTARTDTC'),
            self.cleaned_data.get('MAINANTIBIOENDDTC'),
        ])
        
        # Only require name if there's other data OR name itself is provided
        if not name and has_other_data:
            raise ValidationError(_('Antibiotic name is required when other fields are filled'))
        
        return name.title() if name else ''


# ==========================================
# ANTIBIOTIC FORMSETS
# ==========================================

class BaseAntibioticFormSet(BaseInlineFormSet):
    """Base formset with duplicate detection and empty form skipping"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Field name to check (override in subclasses)
        self.name_field = 'DRUGNAME'  # Default
    
    def clean(self):
        """
        Prevent duplicate antibiotic names
         FIX: Skip validation for completely empty forms
        """
        if any(self.errors):
            return
        
        names = []
        for form in self.forms:
            #  Skip if form is marked for deletion
            if form.cleaned_data.get('DELETE', False):
                continue
            
            #  Skip completely empty forms (extra forms not filled)
            name = form.cleaned_data.get(self.name_field)
            if not name or not name.strip():
                # Check if ANY field has data
                has_data = any(
                    form.cleaned_data.get(field) 
                    for field in form.cleaned_data 
                    if field not in ['DELETE', 'id', 'SEQUENCE', 'USUBJID']
                )
                if not has_data:
                    continue  # Skip this empty form
            
            # Validate non-empty forms
            if name:
                name_lower = name.strip().lower()
                if name_lower in names:
                    raise ValidationError(
                        _('Duplicate antibiotic: "%(name)s"'),
                        params={'name': name},
                        code='duplicate_antibiotic'
                    )
                names.append(name_lower)


class PriorAntibioticFormSetBase(BaseAntibioticFormSet):  #  Đổi tên
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name_field = 'PRIORANTIBIONAME'


class InitialAntibioticFormSetBase(BaseAntibioticFormSet):  #  Đổi tên
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name_field = 'INITIALANTIBIONAME'


class MainAntibioticFormSetBase(BaseAntibioticFormSet):  #  Đổi tên
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name_field = 'MAINANTIBIONAME'


# FormSet factories - GHI ĐÈ với tên mới
PriorAntibioticFormSet = inlineformset_factory(
    CLI_CASE,
    PriorAntibiotic,
    form=PriorAntibioticForm,
    formset=PriorAntibioticFormSetBase,  #  Dùng tên base class
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
    max_num=10,
)

InitialAntibioticFormSet = inlineformset_factory(
    CLI_CASE,
    InitialAntibiotic,
    form=InitialAntibioticForm,
    formset=InitialAntibioticFormSetBase,  #  Dùng tên base class
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
    max_num=10,
)

MainAntibioticFormSet = inlineformset_factory(
    CLI_CASE,
    MainAntibiotic,
    form=MainAntibioticForm,
    formset=MainAntibioticFormSetBase,  #  Dùng tên base class
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
    max_num=10,
)


# ==========================================
# VASOACTIVE DRUG FORM
# ==========================================

class VasoIDrugForm(BaseSEQUENCEForm):
    """Form for vasoactive/inotropic drugs"""
    
    class Meta:
        model = VasoIDrug
        fields = ['SEQUENCE', 'VASOIDRUGNAME', 'VASOIDOSE', 'VASOIDURATION']
        widgets = {
            'SEQUENCE': forms.HiddenInput(),
            'VASOIDRUGNAME': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Drug name (e.g., Norepinephrine)')
            }),
            'VASOIDOSE': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Total dose (µg/kg/min)')
            }),
            'VASOIDURATION': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Duration (days)')
            }),
        }
    
    def clean_VASOIDRUGNAME(self):
        """
        Normalize drug name
         FIX: Allow empty if entire form is empty
        """
        name = self.cleaned_data.get('VASOIDRUGNAME', '') or ''
        name = name.strip()
        
        #  Check if ANY other field has data
        has_other_data = any([
            self.cleaned_data.get('VASOIDOSE'),
            self.cleaned_data.get('VASOIDURATION'),
        ])
        
        # Only require name if there's other data OR name itself is provided
        if not name and has_other_data:
            raise ValidationError(_('Drug name is required when other fields are filled'))
        
        return name.title() if name else ''
    
    def clean_VASOIDURATION(self):
        """Validate duration format"""
        duration = self.cleaned_data.get('VASOIDURATION')
        
        # Handle None or empty values
        if duration is None or duration == '':
            return ''
        
        # Convert to string and strip if needed
        duration_str = str(duration).strip() if duration else ''
        
        if duration_str:
            try:
                duration_val = int(duration_str)
                if duration_val < 0:
                    raise ValidationError(_('Duration must be a positive number'))
            except (ValueError, TypeError):
                raise ValidationError(_('Duration must be a valid number'))
        
        return duration_str


class BaseVasoIDrugFormSet(BaseInlineFormSet):
    """Formset with duplicate detection"""
    
    def clean(self):
        """Prevent duplicate drug names"""
        if any(self.errors):
            return
        
        names = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                name = form.cleaned_data.get('VASOIDRUGNAME')
                if name:
                    name_lower = name.strip().lower()
                    if name_lower in names:
                        raise ValidationError(
                            _('Duplicate drug: "%(name)s"'),
                            params={'name': name},
                            code='duplicate_drug'
                        )
                    names.append(name_lower)


VasoIDrugFormSet = inlineformset_factory(
    CLI_CASE,
    VasoIDrug,
    form=VasoIDrugForm,
    formset=BaseVasoIDrugFormSet,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
    max_num=10,
)


# ==========================================
# SYMPTOM IMPROVEMENT FORM
# ==========================================

class ImproveSymptForm(BaseSEQUENCEForm):
    """Form for symptom improvement tracking"""
    
    class Meta:
        model = ImproveSympt
        fields = ['SEQUENCE', 'SYMPTS', 'IMPROVE_CONDITIONS', 'SYMPTSDTC']  # REMOVED: IMPROVE_SYMPTS (commented in model)
        widgets = {
            'SEQUENCE': forms.HiddenInput(),  # Hidden field to ensure value is submitted
            'SYMPTS': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('List symptoms that improved')
            }),
            'IMPROVE_CONDITIONS': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('Describe improvement conditions')
            }),
            'SYMPTSDTC': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'placeholder': 'YYYY-MM-DD'
            }),
        }
    
    def clean(self):
        """Validate improvement details"""
        cleaned_data = super().clean()
        
        if cleaned_data.get('IMPROVE_SYMPTS') == 'yes':
            if not cleaned_data.get('SYMPTS') and not cleaned_data.get('IMPROVE_CONDITIONS'):
                raise ValidationError(
                    _('Please specify symptoms or conditions that improved')
                )
        
        return cleaned_data


ImproveSymptFormSet = inlineformset_factory(
    CLI_CASE,
    ImproveSympt,
    form=ImproveSymptForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
    max_num=20,
)


# ==========================================
# HOSPITALIZATION PROCESS FORM
# ==========================================

class HospiProcessForm(BaseSEQUENCEForm):
    """
    Form for hospitalization process - department transfers
    """
    
    class Meta:
        model = HospiProcess
        fields = ['SEQUENCE', 'DEPTNAME', 'STARTDTC', 'ENDDTC', 'TRANSFER_REASON']
        widgets = {
            'SEQUENCE': forms.HiddenInput(),  # Hidden field to ensure value is submitted
            'DEPTNAME': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Department name (e.g., ICU, Emergency)')
            }),
            'STARTDTC': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'placeholder': 'YYYY-MM-DD'
            }),
            'ENDDTC': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'placeholder': 'YYYY-MM-DD'
            }),
            'TRANSFER_REASON': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('Reason for transfer')
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # ENDDTC not required if patient still in department
        self.fields['ENDDTC'].required = False
        self.fields['TRANSFER_REASON'].required = False
    
    def clean_DEPTNAME(self):
        """Normalize department name"""
        dept = self.cleaned_data.get('DEPTNAME', '').strip()
        if not dept:
            raise ValidationError(_('Department name is required'))
        return dept.title()


class BaseHospiProcessFormSet(BaseInlineFormSet):
    """Formset with overlap detection"""
    
    def clean(self):
        """Prevent overlapping dates"""
        if any(self.errors):
            return
        
        departments = []
        
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                dept_name = form.cleaned_data.get('DEPTNAME')
                start_date = form.cleaned_data.get('STARTDTC')
                end_date = form.cleaned_data.get('ENDDTC')
                
                if dept_name and start_date:
                    departments.append({
                        'name': dept_name,
                        'start': start_date,
                        'end': end_date,
                        'form': form
                    })
        
        # Check overlapping dates
        for i, dept1 in enumerate(departments):
            for dept2 in departments[i+1:]:
                if self._dates_overlap(dept1, dept2):
                    dept1['form'].add_error('STARTDTC',
                        _('Department stay dates overlap with another department'))
    
    def _dates_overlap(self, dept1, dept2):
        """Check if two department stays overlap"""
        start1, end1 = dept1['start'], dept1['end']
        start2, end2 = dept2['start'], dept2['end']
        
        # If either doesn't have end date, can't determine overlap
        if not end1 or not end2:
            return False
        
        # Check if ranges overlap
        return not (end1 < start2 or end2 < start1)


HospiProcessFormSet = inlineformset_factory(
    CLI_CASE,
    HospiProcess,
    form=HospiProcessForm,
    formset=BaseHospiProcessFormSet,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
    max_num=20,
)


# ==========================================
# ADVERSE EVENT FORM
# ==========================================

class AEHospEventForm(BaseSEQUENCEForm):
    """
    Form for adverse events during hospitalization
    """
    
    class Meta:
        model = AEHospEvent
        fields = ['SEQUENCE', 'AENAME', 'AEDETAILS', 'AEDTC']
        widgets = {
            'SEQUENCE': forms.HiddenInput(),  # Hidden field to ensure value is submitted
            'AENAME': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Event name (e.g., Anaphylaxis, GI bleeding)')
            }),
            'AEDETAILS': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Event details, clinical course, management...')
            }),
            'AEDTC': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'placeholder': 'YYYY-MM-DD'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # AEDETAILS not required
        self.fields['AEDETAILS'].required = False
    
    def clean_AENAME(self):
        """Normalize event name"""
        name = self.cleaned_data.get('AENAME', '') or ''
        name = name.strip()
        if not name:
            raise ValidationError(_('Event name is required'))
        return name.title()


class BaseAEHospEventFormSet(BaseInlineFormSet):
    """Formset with duplicate detection"""
    
    def clean(self):
        """Prevent duplicate events on same date"""
        if any(self.errors):
            return
        
        ae_dates = []
        
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                ae_name = form.cleaned_data.get('AENAME')
                ae_date = form.cleaned_data.get('AEDTC')
                
                if ae_name and ae_date:
                    # Check for duplicate events on same date
                    if (ae_name, ae_date) in ae_dates:
                        form.add_error('AENAME',
                            _('This event has already been recorded on this date'))
                    else:
                        ae_dates.append((ae_name, ae_date))


AEHospEventFormSet = inlineformset_factory(
    CLI_CASE,
    AEHospEvent,
    form=AEHospEventForm,
    formset=BaseAEHospEventFormSet,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
    max_num=20,
)