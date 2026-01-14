# backends/studies/study_43en/forms/contact/ContactSample.py

from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError 
from datetime import date, timedelta
from backends.studies.study_43en.models.contact import SAM_CONTACT
import logging

logger = logging.getLogger(__name__)


class ContactSampleCollectionForm(forms.ModelForm):
    """
    Optimized form for Contact Sample Collection
    
    Similar to patient sample form but:
    - Less strict date validation
    - More flexible window compliance
    - Contact-specific context
    
    Features:
    - Auto-calculated expected dates with visual indicators
    - Conditional field display based on selections
    - Comprehensive cross-field validation
    - Smart defaults based on sample type
    - Real-time window compliance checking (informational only)
    - Accessibility enhancements
    - Responsive design ready
    
    Usage:
        form = ContactSampleCollectionForm(instance=sample, contact=contact_obj)
        if form.is_valid():
            sample = form.save()
    """
    
    class Meta:
        model = SAM_CONTACT
        fields = [
            'SAMPLE_TYPE',
            'SAMPLE_STATUS',
            'SAMPLE',
            'REASONIFNO',
            # Stool
            'STOOL',
            'STOOLDATE',
            'CULTRES_1',
            'KLEBPNEU_1',
            'OTHERRES_1',
            'OTHERRESSPECIFY_1',
            # Rectal
            'RECTSWAB',
            'RECTSWABDATE',
            'CULTRES_2',
            'KLEBPNEU_2',
            'OTHERRES_2',
            'OTHERRESSPECIFY_2',
            # Throat
            'THROATSWAB',
            'THROATSWABDATE',
            'CULTRES_3',
            'KLEBPNEU_3',
            'OTHERRES_3',
            'OTHERRESSPECIFY_3',
            # Blood
            'BLOOD',
            'BLOODDATE',
        ]
        
        widgets = {
            # Sample Type - with icons
            'SAMPLE_TYPE': forms.RadioSelect(attrs={
                'class': 'form-check-input',
                'data-toggle': 'collapse-sample-info'
            }),
            
            # Sample Status - auto-updated
            'SAMPLE_STATUS': forms.Select(attrs={
                'class': 'form-select',
                'disabled': 'disabled'
            }),
            
            # Sample collected - prominent
            'SAMPLE': forms.RadioSelect(
                choices=((True, _('Yes - Collected')), (False, _('No - Not Collected'))),
                attrs={
                    'class': 'form-check-input',
                    'data-toggle': 'collapse-reason'
                }
            ),
            
            # Reason if not collected - conditional
            'REASONIFNO': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Please provide reason for not collecting sample...'),
                'maxlength': 500,
                'data-depends-on': 'SAMPLE',
                'data-depends-value': 'false'
            }),
            
            # ==========================================
            # STOOL SAMPLE WIDGETS
            # ==========================================
            'STOOL': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'data-toggle': 'collapse-stool-details'
            }),
            
            'STOOLDATE': forms.DateInput(format='%d/%m/%Y', attrs={
                'class': 'form-control datepicker',
                'type': 'text',
                'placeholder': 'DD/MM/YYYY',
                'data-window-check': 'true',
                'data-sample-type': 'stool',
                'autocomplete': 'off'
            }),
            
            'CULTRES_1': forms.RadioSelect(attrs={
                'class': 'form-check-input',
                'data-toggle': 'collapse-stool-organisms'
            }),
            
            'KLEBPNEU_1': forms.CheckboxInput(attrs={
                'class': 'form-check-input organism-checkbox',
                'data-organism': 'klebsiella',
                'data-sample': 'stool'
            }),
            
            'OTHERRES_1': forms.CheckboxInput(attrs={
                'class': 'form-check-input organism-checkbox',
                'data-organism': 'other',
                'data-sample': 'stool',
                'data-toggle': 'collapse-stool-other-spec'
            }),
            
            'OTHERRESSPECIFY_1': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Specify organism name...'),
                'maxlength': 255,
                'data-depends-on': 'OTHERRES_1'
            }),
            
            # ==========================================
            # RECTAL SWAB WIDGETS
            # ==========================================
            'RECTSWAB': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'data-toggle': 'collapse-rectal-details'
            }),
            
            'RECTSWABDATE': forms.DateInput(format='%d/%m/%Y', attrs={
                'class': 'form-control datepicker',
                'type': 'text',
                'placeholder': 'DD/MM/YYYY',
                'data-window-check': 'true',
                'data-sample-type': 'rectal',
                'autocomplete': 'off'
            }),
            
            'CULTRES_2': forms.RadioSelect(attrs={
                'class': 'form-check-input',
                'data-toggle': 'collapse-rectal-organisms'
            }),
            
            'KLEBPNEU_2': forms.CheckboxInput(attrs={
                'class': 'form-check-input organism-checkbox',
                'data-organism': 'klebsiella',
                'data-sample': 'rectal'
            }),
            
            'OTHERRES_2': forms.CheckboxInput(attrs={
                'class': 'form-check-input organism-checkbox',
                'data-organism': 'other',
                'data-sample': 'rectal',
                'data-toggle': 'collapse-rectal-other-spec'
            }),
            
            'OTHERRESSPECIFY_2': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Specify organism name...'),
                'maxlength': 255,
                'data-depends-on': 'OTHERRES_2'
            }),
            
            # ==========================================
            # THROAT SWAB WIDGETS
            # ==========================================
            'THROATSWAB': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'data-toggle': 'collapse-throat-details'
            }),
            
            'THROATSWABDATE': forms.DateInput(format='%d/%m/%Y', attrs={
                'class': 'form-control datepicker',
                'type': 'text',
                'placeholder': 'DD/MM/YYYY',
                'data-window-check': 'true',
                'data-sample-type': 'throat',
                'autocomplete': 'off'
            }),
            
            'CULTRES_3': forms.RadioSelect(attrs={
                'class': 'form-check-input',
                'data-toggle': 'collapse-throat-organisms'
            }),
            
            'KLEBPNEU_3': forms.CheckboxInput(attrs={
                'class': 'form-check-input organism-checkbox',
                'data-organism': 'klebsiella',
                'data-sample': 'throat'
            }),
            
            'OTHERRES_3': forms.CheckboxInput(attrs={
                'class': 'form-check-input organism-checkbox',
                'data-organism': 'other',
                'data-sample': 'throat',
                'data-toggle': 'collapse-throat-other-spec'
            }),
            
            'OTHERRESSPECIFY_3': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Specify organism name...'),
                'maxlength': 255,
                'data-depends-on': 'OTHERRES_3'
            }),
            
            # ==========================================
            # BLOOD SAMPLE WIDGETS
            # ==========================================
            'BLOOD': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'data-toggle': 'collapse-blood-details'
            }),
            
            'BLOODDATE': forms.DateInput(format='%d/%m/%Y', attrs={
                'class': 'form-control datepicker',
                'type': 'text',
                'placeholder': 'DD/MM/YYYY',
                'data-window-check': 'true',
                'data-sample-type': 'blood',
                'autocomplete': 'off'
            }),
        }
        
        labels = {
            'SAMPLE_TYPE': _('Sample Collection Type'),
            'SAMPLE_STATUS': _('Collection Status (Auto-calculated)'),
            'SAMPLE': _('Was sample collected?'),
            'REASONIFNO': _('Reason for not collecting sample'),
            
            # Stool
            'STOOL': _('Stool Sample'),
            'STOOLDATE': _('Stool Collection Date'),
            'CULTRES_1': _('Stool Culture Result'),
            'KLEBPNEU_1': _('Klebsiella pneumoniae detected'),
            'OTHERRES_1': _('Other organism detected'),
            'OTHERRESSPECIFY_1': _('Specify other organism'),
            
            # Rectal
            'RECTSWAB': _('Rectal Swab'),
            'RECTSWABDATE': _('Rectal Swab Collection Date'),
            'CULTRES_2': _('Rectal Swab Culture Result'),
            'KLEBPNEU_2': _('Klebsiella pneumoniae detected'),
            'OTHERRES_2': _('Other organism detected'),
            'OTHERRESSPECIFY_2': _('Specify other organism'),
            
            # Throat
            'THROATSWAB': _('Throat Swab'),
            'THROATSWABDATE': _('Throat Swab Collection Date'),
            'CULTRES_3': _('Throat Swab Culture Result'),
            'KLEBPNEU_3': _('Klebsiella pneumoniae detected'),
            'OTHERRES_3': _('Other organism detected'),
            'OTHERRESSPECIFY_3': _('Specify other organism'),
            
            # Blood
            'BLOOD': _('Blood Sample'),
            'BLOODDATE': _('Blood Collection Date'),
        }
        
        help_texts = {
            'SAMPLE_TYPE': _(
                'Select the sample collection timepoint for this contact.'
            ),
            'SAMPLE': _(
                'Indicate whether any sample was collected for this timepoint.'
            ),
            'REASONIFNO': _(
                'Provide reason if no sample was collected (e.g., contact refused, unavailable, etc.)'
            ),
            'STOOLDATE': _(
                'Enter actual collection date. Date validation is flexible for contacts.'
            ),
            'CULTRES_1': _(
                'Select culture result. If organisms detected, specify below.'
            ),
            'KLEBPNEU_1': _(
                'Check if Klebsiella pneumoniae was isolated.'
            ),
            'OTHERRESSPECIFY_1': _(
                'Specify organism name (e.g., E. coli, Pseudomonas, etc.)'
            ),
        }
        
        error_messages = {
            'SAMPLE_TYPE': {
                'required': _('Sample type must be selected'),
                'invalid_choice': _('Invalid sample type selected'),
            },
            'STOOLDATE': {
                'invalid': _('Invalid date format. Use DD/MM/YYYY'),
            },
        }

    def __init__(self, *args, contact=None, **kwargs):
        """
        Initialize form with contact context
        
        Args:
            contact: ENR_CONTACT instance for calculating expected dates
            *args, **kwargs: Standard form arguments
        """
        # Auto-detect contact from instance if not provided
        if contact is None and 'instance' in kwargs and kwargs['instance']:
            contact = getattr(kwargs['instance'], 'USUBJID', None)
        
        self.contact = contact
        super().__init__(*args, **kwargs)
        
        # 🚀 Set date input formats for dd/mm/yyyy (bootstrap-datepicker format)
        date_fields = ['STOOLDATE', 'RECTSWABDATE', 'THROATSWABDATE', 'BLOODDATE']
        for field_name in date_fields:
            if field_name in self.fields:
                self.fields[field_name].input_formats = ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
        
        self._setup_initial_values()
        self._setup_field_properties()
        self._setup_conditional_fields()
        self._setup_window_warnings()

    def _setup_initial_values(self):
        """Setup smart initial values based on context"""
        
        if not self.instance.pk and self.contact:
            # Check which samples already exist
            existing_types = set(
                SAM_CONTACT.objects.filter(
                    USUBJID=self.contact
                ).values_list('SAMPLE_TYPE', flat=True)
            )
            
            # Suggest next logical sample type
            all_types = ['1', '2', '3', '4']
            remaining = [t for t in all_types if t not in existing_types]
            
            if remaining:
                self.fields['SAMPLE_TYPE'].initial = remaining[0]
                self.fields['SAMPLE_TYPE'].help_text = _(
                    f'Suggested next collection: {SAM_CONTACT.SampleTypeChoices(remaining[0]).label}'
                )

    def _setup_field_properties(self):
        """Setup additional field properties for better UX"""
        
        # Make sample status read-only (auto-calculated)
        self.fields['SAMPLE_STATUS'].disabled = True
        self.fields['SAMPLE_STATUS'].required = False
        
        # Make SAMPLE_TYPE readonly when editing existing sample
        if self.instance and self.instance.pk:
            self.fields['SAMPLE_TYPE'].disabled = True
            self.fields['SAMPLE_TYPE'].required = False
            self.fields['SAMPLE_TYPE'].widget.attrs['readonly'] = True
        
        # Add CSS classes for field grouping
        stool_fields = ['STOOL', 'STOOLDATE', 'CULTRES_1', 'KLEBPNEU_1', 'OTHERRES_1', 'OTHERRESSPECIFY_1']
        rectal_fields = ['RECTSWAB', 'RECTSWABDATE', 'CULTRES_2', 'KLEBPNEU_2', 'OTHERRES_2', 'OTHERRESSPECIFY_2']
        throat_fields = ['THROATSWAB', 'THROATSWABDATE', 'CULTRES_3', 'KLEBPNEU_3', 'OTHERRES_3', 'OTHERRESSPECIFY_3']
        blood_fields = ['BLOOD', 'BLOODDATE']
        
        for field_name in stool_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['data-group'] = 'stool'
        
        for field_name in rectal_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['data-group'] = 'rectal'
        
        for field_name in throat_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['data-group'] = 'throat'
        
        for field_name in blood_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['data-group'] = 'blood'

    def _setup_conditional_fields(self):
        """Setup conditional field display logic"""
        
        if self.instance and self.instance.pk:
            # If sample not collected, show reason field prominently
            if not self.instance.SAMPLE:
                self.fields['REASONIFNO'].required = True
                self.fields['REASONIFNO'].widget.attrs['class'] += ' border-warning'
            
            # If samples collected, make dates required
            if self.instance.STOOL:
                self.fields['STOOLDATE'].required = True
            if self.instance.RECTSWAB:
                self.fields['RECTSWABDATE'].required = True
            if self.instance.THROATSWAB:
                self.fields['THROATSWABDATE'].required = True
            if self.instance.BLOOD:
                self.fields['BLOODDATE'].required = True
            
            # If other organism detected, make specification required
            if self.instance.OTHERRES_1:
                self.fields['OTHERRESSPECIFY_1'].required = True
            if self.instance.OTHERRES_2:
                self.fields['OTHERRESSPECIFY_2'].required = True
            if self.instance.OTHERRES_3:
                self.fields['OTHERRESSPECIFY_3'].required = True

    def _setup_window_warnings(self):
        """
        Add warnings for dates outside acceptable window
        
        NOTE: Informational only for contacts - not blocking
        """
        
        if not self.instance or not self.instance.pk:
            return
        
        try:
            window_status = self.instance.is_within_collection_window
            if not window_status:
                return
            
            # Add info class (not warning) to dates outside window
            for sample_type, in_window in window_status.items():
                if not in_window:
                    field_map = {
                        'stool': 'STOOLDATE',
                        'rectal': 'RECTSWABDATE',
                        'throat': 'THROATSWABDATE',
                        'blood': 'BLOODDATE'
                    }
                    
                    field_name = field_map.get(sample_type)
                    if field_name and field_name in self.fields:
                        # Use info instead of warning for contacts
                        self.fields[field_name].widget.attrs['class'] += ' border-info'
                        
                        days_diff = self.instance.days_from_expected.get(sample_type, 0)
                        if days_diff > 0:
                            info = _('ℹ️ Collected {days} days after expected date').format(days=days_diff)
                        else:
                            info = _('ℹ️ Collected {days} days before expected date').format(days=abs(days_diff))
                        
                        current_help = self.fields[field_name].help_text
                        self.fields[field_name].help_text = f"{current_help} {info}"
        except AttributeError as e:
            logger.warning(f"Could not setup window warnings for contact: {e}")

    # ==========================================
    # FIELD-SPECIFIC VALIDATION (LESS STRICT)
    # ==========================================
    
    def clean_STOOLDATE(self):
        """Validate stool collection date"""
        date_value = self.cleaned_data.get('STOOLDATE')
        stool_collected = self.cleaned_data.get('STOOL')
        
        if stool_collected and not date_value:
            raise ValidationError(_('Collection date is required when stool is collected'))
        
        if date_value:
            self._validate_collection_date(date_value, 'stool')
        
        return date_value

    def clean_RECTSWABDATE(self):
        """Validate rectal swab collection date"""
        date_value = self.cleaned_data.get('RECTSWABDATE')
        rectal_collected = self.cleaned_data.get('RECTSWAB')
        
        if rectal_collected and not date_value:
            raise ValidationError(_('Collection date is required when rectal swab is collected'))
        
        if date_value:
            self._validate_collection_date(date_value, 'rectal')
        
        return date_value

    def clean_THROATSWABDATE(self):
        """Validate throat swab collection date"""
        date_value = self.cleaned_data.get('THROATSWABDATE')
        throat_collected = self.cleaned_data.get('THROATSWAB')
        
        if throat_collected and not date_value:
            raise ValidationError(_('Collection date is required when throat swab is collected'))
        
        if date_value:
            self._validate_collection_date(date_value, 'throat')
        
        return date_value

    def clean_BLOODDATE(self):
        """Validate blood collection date"""
        date_value = self.cleaned_data.get('BLOODDATE')
        blood_collected = self.cleaned_data.get('BLOOD')
        
        if blood_collected and not date_value:
            raise ValidationError(_('Collection date is required when blood is collected'))
        
        if date_value:
            self._validate_collection_date(date_value, 'blood')
        
        return date_value

    def _validate_collection_date(self, date_value, sample_type):
        """
        Common validation logic for collection dates
        
        NOTE: LESS STRICT than patient validation
        
        Args:
            date_value: Date to validate
            sample_type: Type of sample (for error messages)
        """
        #  LESS STRICT: Only check if way in future (more than 1 year)
        future_limit = date.today() + timedelta(days=365)
        if date_value > future_limit:
            raise ValidationError(_('Collection date seems too far in the future'))
        
        #  LESS STRICT: Allow dates slightly before enrollment with grace period
        if self.contact:
            enr_date = getattr(self.contact, 'ENRDATE', None)
            if enr_date:
                # Grace period of 7 days before enrollment
                grace_period = enr_date - timedelta(days=7)
                if date_value < grace_period:
                    raise ValidationError(
                        _('Collection date is significantly before enrollment date ({enr_date})').format(
                            enr_date=enr_date.strftime('%Y-%m-%d')
                        )
                    )

    def clean_CULTRES_1(self):
        """Validate stool culture result"""
        result = self.cleaned_data.get('CULTRES_1')
        kleb = self.cleaned_data.get('KLEBPNEU_1')
        
        if kleb and result != 'Pos':
            raise ValidationError(
                _('Culture result must be Positive if Klebsiella pneumoniae was detected')
            )
        
        return result

    def clean_CULTRES_2(self):
        """Validate rectal culture result"""
        result = self.cleaned_data.get('CULTRES_2')
        kleb = self.cleaned_data.get('KLEBPNEU_2')
        
        if kleb and result != 'Pos':
            raise ValidationError(
                _('Culture result must be Positive if Klebsiella pneumoniae was detected')
            )
        
        return result

    def clean_CULTRES_3(self):
        """Validate throat culture result"""
        result = self.cleaned_data.get('CULTRES_3')
        kleb = self.cleaned_data.get('KLEBPNEU_3')
        
        if kleb and result != 'Pos':
            raise ValidationError(
                _('Culture result must be Positive if Klebsiella pneumoniae was detected')
            )
        
        return result

    def clean(self):
        """
        Comprehensive cross-field validation
        
        NOTE: Less strict than patient validation
        """
        cleaned_data = super().clean()
        errors = {}
        
        # ==========================================
        # 1. SAMPLE COLLECTION VALIDATION
        # ==========================================
        sample_collected = cleaned_data.get('SAMPLE')
        reason_not_collected = cleaned_data.get('REASONIFNO')
        
        # Check at least one sample type if sample collected
        any_sample = any([
            cleaned_data.get('STOOL'),
            cleaned_data.get('RECTSWAB'),
            cleaned_data.get('THROATSWAB'),
            cleaned_data.get('BLOOD')
        ])
        
        #  LESS STRICT: Warning only, not hard error
        if sample_collected and not any_sample:
            logger.warning("Contact sample marked as collected but no sample types selected")
        
        if not sample_collected and not reason_not_collected:
            errors['REASONIFNO'] = _(
                'Reason should be provided if no sample was collected'
            )
        
        if not sample_collected and any_sample:
            errors['SAMPLE'] = _(
                'Sample status is "Not Collected" but sample types are selected. Please correct.'
            )
        
        # ==========================================
        # 2. CULTURE RESULT VALIDATION
        # ==========================================
        
        POS = 'Pos'
        
        # Stool culture
        if cleaned_data.get('STOOL'):
            cultres_1 = cleaned_data.get('CULTRES_1')
            kleb_1 = cleaned_data.get('KLEBPNEU_1')
            other_1 = cleaned_data.get('OTHERRES_1')
            
            if (kleb_1 or other_1) and cultres_1 != POS:
                errors['CULTRES_1'] = _(
                    'Culture result must be Positive if organisms were detected'
                )
            
            #  LESS STRICT: Warning only
            if cultres_1 == POS and not (kleb_1 or other_1):
                logger.warning("Contact stool culture positive but no organisms specified")
        
        # Rectal culture
        if cleaned_data.get('RECTSWAB'):
            cultres_2 = cleaned_data.get('CULTRES_2')
            kleb_2 = cleaned_data.get('KLEBPNEU_2')
            other_2 = cleaned_data.get('OTHERRES_2')
            
            if (kleb_2 or other_2) and cultres_2 != POS:
                errors['CULTRES_2'] = _(
                    'Culture result must be Positive if organisms were detected'
                )
            
            if cultres_2 == POS and not (kleb_2 or other_2):
                logger.warning("Contact rectal culture positive but no organisms specified")
        
        # Throat culture
        if cleaned_data.get('THROATSWAB'):
            cultres_3 = cleaned_data.get('CULTRES_3')
            kleb_3 = cleaned_data.get('KLEBPNEU_3')
            other_3 = cleaned_data.get('OTHERRES_3')
            
            if (kleb_3 or other_3) and cultres_3 != POS:
                errors['CULTRES_3'] = _(
                    'Culture result must be Positive if organisms were detected'
                )
            
            if cultres_3 == POS and not (kleb_3 or other_3):
                logger.warning("Contact throat culture positive but no organisms specified")
        
        # ==========================================
        # 3. DATE SEQUENCE VALIDATION (INFORMATIONAL)
        # ==========================================
        
        collection_dates = []
        if cleaned_data.get('STOOLDATE'):
            collection_dates.append(('Stool', cleaned_data['STOOLDATE']))
        if cleaned_data.get('RECTSWABDATE'):
            collection_dates.append(('Rectal', cleaned_data['RECTSWABDATE']))
        if cleaned_data.get('THROATSWABDATE'):
            collection_dates.append(('Throat', cleaned_data['THROATSWABDATE']))
        if cleaned_data.get('BLOODDATE'):
            collection_dates.append(('Blood', cleaned_data['BLOODDATE']))
        
        #  LESS STRICT: Just log, don't error
        if len(collection_dates) > 1:
            dates_only = [d[1] for d in collection_dates]
            min_date = min(dates_only)
            max_date = max(dates_only)
            
            if (max_date - min_date).days > 7:
                logger.info(f"Contact collection dates span {(max_date - min_date).days} days")
        
        if errors:
            raise ValidationError(errors)
        
        return cleaned_data

    def get_collection_summary(self):
        """
        Get summary of collection status
        
        Returns:
            dict: Summary information
        """
        if not self.instance or not self.instance.pk:
            return {
                'total_collected': 0,
                'completeness': 0,
                'has_klebsiella': False,
                'all_in_window': None
            }
        
        try:
            return {
                'total_collected': self.instance.total_samples_collected,
                'completeness': self.instance.collection_completeness,
                'has_klebsiella': self.instance.has_klebsiella,
                'klebsiella_sites': self.instance.klebsiella_sites,
                'all_in_window': self._check_all_in_window()
            }
        except AttributeError as e:
            logger.warning(f"Could not get collection summary for contact: {e}")
            return {
                'total_collected': 0,
                'completeness': 0,
                'has_klebsiella': False,
                'all_in_window': None
            }

    def _check_all_in_window(self):
        """Check if all collected samples are within window"""
        if not self.instance or not self.instance.pk:
            return None
        
        try:
            window_status = self.instance.is_within_collection_window
            if not window_status:
                return None
            return all(window_status.values())
        except AttributeError:
            return None


# ==========================================
# FORMSET FOR MULTIPLE CONTACT SAMPLES
# ==========================================

from django.forms import modelformset_factory

ContactSampleCollectionFormSet = modelformset_factory(
    SAM_CONTACT,
    form=ContactSampleCollectionForm,
    extra=0,
    can_delete=False,
    max_num=4,
    validate_max=True
)


# ==========================================
# INLINE FORMSET FOR ADMIN
# ==========================================

from django.forms import BaseInlineFormSet

class ContactSampleCollectionInlineFormSet(BaseInlineFormSet):
    """
    Custom inline formset for Django admin
    
    Features:
    - Validates sample type uniqueness
    - Auto-orders by sample type
    - Provides helpful error messages
    """
    
    def clean(self):
        """Validate formset-level rules"""
        if any(self.errors):
            return
        
        sample_types = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                sample_type = form.cleaned_data.get('SAMPLE_TYPE')
                if sample_type:
                    if sample_type in sample_types:
                        raise ValidationError(
                            _('Each sample type can only be collected once per contact')
                        )
                    sample_types.append(sample_type)