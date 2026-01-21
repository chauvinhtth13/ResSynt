# backends/studies/study_43en/forms/CLI_laboratory.py

from django import forms
from django.forms import modelformset_factory, BaseModelFormSet
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.models.patient import (
    LaboratoryTest,
    OtherTest,
    ENR_CASE,
)


# ==========================================
# LABORATORY TEST FORM
# ==========================================

class LaboratoryTestForm(forms.ModelForm):
    """Form for individual laboratory test"""
    
    class Meta:
        model = LaboratoryTest
        fields = ['id', 'PERFORMED', 'PERFORMEDDATE', 'RESULT']
        widgets = {
            'id': forms.HiddenInput(),
            'PERFORMED': forms.CheckboxInput(attrs={
                'class': 'form-check-input lab-performed-checkbox'
            }),
            'PERFORMEDDATE': forms.DateInput(
                format='%d/%m/%Y',
                attrs={
                    'type': 'text',
                    'class': 'form-control datepicker',
                    'placeholder': 'DD/MM/YYYY'
                }
            ),
            'RESULT': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('Nhập kết quả xét nghiệm')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        #  CRITICAL: Make id field not required to prevent validation errors
        if 'id' in self.fields:
            self.fields['id'].required = False
        
        # Make fields not required initially
        self.fields['PERFORMEDDATE'].required = False
        self.fields['PERFORMEDDATE'].input_formats = ['%d/%m/%Y', '%d-%m-%Y']
        self.fields['RESULT'].required = False

    
    def clean(self):
        """Validate PERFORMED requirements"""
        cleaned_data = super().clean()
        performed = cleaned_data.get('PERFORMED', False)
        
        if performed:
            # Date is required
            if not cleaned_data.get('PERFORMEDDATE'):
                self.add_error('PERFORMEDDATE', 
                    _('Ngày thực hiện là bắt buộc khi xét nghiệm đã thực hiện'))
            
            # Result is required
            result = cleaned_data.get('RESULT')
            if not result or not result.strip():
                self.add_error('RESULT', 
                    _('Kết quả là bắt buộc khi xét nghiệm đã thực hiện'))
        else:
            # Clear fields if not performed
            cleaned_data['PERFORMEDDATE'] = None
            cleaned_data['RESULT'] = None
        
        return cleaned_data
    
    def clean_RESULT(self):
        """Normalize result text"""
        result = self.cleaned_data.get('RESULT')
        if result:
            return result.strip()
        return result


# ==========================================
# BASE FORMSET
# ==========================================

class BaseLaboratoryTestFormSet(BaseModelFormSet):
    """Base formset for laboratory tests"""
    
    def __init__(self, *args, **kwargs):
        """
         CRITICAL FIX: Inject missing id fields BEFORE forms are created
        
        Problem: Template may not render all form.id fields due to conditional logic
        Solution: Inject missing ids into POST data before BaseModelFormSet.__init__ creates forms
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Get data from either args[0] or kwargs['data']
        data = None
        if len(args) > 0 and args[0] is not None:
            data = args[0]
        elif 'data' in kwargs and kwargs['data'] is not None:
            data = kwargs['data']
        
        # Handle missing id fields BEFORE calling super().__init__
        if data:
            queryset = kwargs.get('queryset')
            
            # Only inject if we have bound data and a queryset
            if queryset is not None:
                prefix = kwargs.get('prefix', self.get_default_prefix())
                
                # Make data mutable
                if hasattr(data, '_mutable'):
                    mutable_backup = data._mutable
                    data._mutable = True
                else:
                    mutable_backup = None
                
                injected_count = 0
                
                # Get all instances from queryset
                instances = list(queryset)
                
                for i, instance in enumerate(instances):
                    id_field_name = f"{prefix}-{i}-id"
                    
                    # If instance has pk but id field missing in POST
                    if instance.pk and id_field_name not in data:
                        data[id_field_name] = str(instance.pk)
                        injected_count += 1
                        logger.warning(
                            "Injecting missing id for form %d: %s=%s (TESTTYPE=%s)",
                            i, id_field_name, instance.pk, 
                            getattr(instance, 'TESTTYPE', 'UNKNOWN')
                        )
                
                # Restore mutability
                if mutable_backup is not None:
                    data._mutable = mutable_backup
                
                if injected_count > 0:
                    logger.info(f" Injected {injected_count} missing 'id' fields BEFORE form initialization")
                else:
                    logger.debug("✓ All form id fields present in POST data")
        
        # Now call parent __init__ which will create forms with injected data
        super().__init__(*args, **kwargs)
        
        if self.queryset is not None:
            self.queryset = self.queryset.order_by('CATEGORY', 'TESTTYPE')
    
    def clean(self):
        """
        Formset-level validation
        
        FIX: Add proper None checks and handle model validation errors
        """
        if any(self.errors):
            return
        
        incomplete_tests = []
        
        for form in self.forms:
            # Skip if no cleaned_data or form is being deleted
            if not form.cleaned_data or form.cleaned_data.get('DELETE'):
                continue
            
            # Get values with None handling
            performed = form.cleaned_data.get('PERFORMED', False)
            performeddate = form.cleaned_data.get('PERFORMEDDATE')
            result = form.cleaned_data.get('RESULT')
            
            # FIX: Safe strip with None check
            if performed:
                result_text = result.strip() if result else ''
                
                if not performeddate or not result_text:
                    if form.instance and form.instance.TESTTYPE:
                        test_name = form.instance.get_TESTTYPE_display()
                        incomplete_tests.append(test_name)
        
        if incomplete_tests:
            # Show only first 5 incomplete tests
            raise ValidationError(
                _('Các xét nghiệm sau đã đánh dấu "Đã thực hiện" nhưng thiếu thông tin: %(tests)s'),
                params={'tests': ', '.join(incomplete_tests[:5])},
                code='incomplete_tests'
            )
    
    def _should_delete_form(self, form):
        """Override to prevent accidental deletion"""
        return False


# ==========================================
# FORMSET FACTORY
# ==========================================

LaboratoryTestFormSet = modelformset_factory(
    LaboratoryTest,
    form=LaboratoryTestForm,
    formset=BaseLaboratoryTestFormSet,
    extra=0,
    can_delete=False,
    can_order=False,
)


# ==========================================
# OTHER TEST FORM
# ==========================================

class OtherTestForm(forms.ModelForm):
    """Form for custom/other tests"""
    
    class Meta:
        model = OtherTest
        fields = ['SEQUENCE', 'LAB_TYPE', 'OTHERTESTNAME', 
                  'OTHERTESTPERFORMED', 'OTHERTESTDTC', 'OTHERTESTRESULT']
        widgets = {
            'SEQUENCE': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'readonly': True,
            }),
            'LAB_TYPE': forms.Select(attrs={
                'class': 'form-control',
            }),
            'OTHERTESTNAME': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., Procalcitonin, D-Dimer'),
            }),
            'OTHERTESTDTC': forms.DateInput(format='%d/%m/%Y', attrs={
                'type': 'text',
                'class': 'form-control datepicker',
                'placeholder': 'DD/MM/YYYY',
            }),
            'OTHERTESTRESULT': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['SEQUENCE'].required = False
        # Set date input format
        if 'OTHERTESTDTC' in self.fields:
            self.fields['OTHERTESTDTC'].input_formats = ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
        if self.instance and self.instance.pk and not self.instance.OTHERTESTPERFORMED:
            self.fields['OTHERTESTDTC'].required = False
            self.fields['OTHERTESTRESULT'].required = False
    
    def clean(self):
        """Validate test requirements"""
        cleaned_data = super().clean()
        
        test_name = cleaned_data.get('OTHERTESTNAME', '').strip()
        if not test_name:
            raise ValidationError({
                'OTHERTESTNAME': _('Test name is required')
            })
        
        performed = cleaned_data.get('OTHERTESTPERFORMED', False)
        if performed:
            if not cleaned_data.get('OTHERTESTDTC'):
                raise ValidationError({
                    'OTHERTESTDTC': _('Test date is required')
                })
            
            result = cleaned_data.get('OTHERTESTRESULT')
            result_text = result.strip() if result else ''
            if not result_text:
                raise ValidationError({
                    'OTHERTESTRESULT': _('Result is required')
                })
        
        return cleaned_data


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def initialize_laboratory_tests(enrollment_case, lab_type='1'):
    """
    Initialize ALL standard laboratory test records
    
    Returns: count of tests created
    """
    count = 0
    
    for test_type_value, test_type_label in LaboratoryTest.TestTypeChoices.choices:
        if not LaboratoryTest.objects.filter(
            USUBJID=enrollment_case,
            TESTTYPE=test_type_value,
            LAB_TYPE=lab_type
        ).exists():
            LaboratoryTest.objects.create(
                USUBJID=enrollment_case,
                LAB_TYPE=lab_type,
                TESTTYPE=test_type_value,
                PERFORMED=False,
            )
            count += 1
    
    return count


def get_laboratory_tests_by_category(enrollment_case, lab_type='1'):
    """Get tests grouped by category"""
    tests = LaboratoryTest.objects.filter(
        USUBJID=enrollment_case,
        LAB_TYPE=lab_type
    ).select_related('USUBJID').order_by('CATEGORY', 'TESTTYPE')
    
    tests_by_category = {}
    for test in tests:
        category = test.CATEGORY
        if category not in tests_by_category:
            tests_by_category[category] = []
        tests_by_category[category].append(test)
    
    return tests_by_category


def get_laboratory_summary(enrollment_case):
    """Get summary statistics"""
    from django.db.models import Count, Q
    
    total_tests = LaboratoryTest.objects.filter(USUBJID=enrollment_case).count()
    performed_tests = LaboratoryTest.objects.filter(
        USUBJID=enrollment_case, 
        PERFORMED=True
    ).count()
    
    incomplete_tests = LaboratoryTest.objects.filter(
        USUBJID=enrollment_case,
        PERFORMED=True
    ).filter(
        Q(RESULT__isnull=True) | Q(RESULT__exact='')
    ).count()
    
    by_timepoint = {}
    for lab_type_value, lab_type_label in LaboratoryTest.LabTypeChoices.choices:
        total = LaboratoryTest.objects.filter(
            USUBJID=enrollment_case,
            LAB_TYPE=lab_type_value
        ).count()
        
        performed = LaboratoryTest.objects.filter(
            USUBJID=enrollment_case,
            LAB_TYPE=lab_type_value,
            PERFORMED=True
        ).count()
        
        by_timepoint[lab_type_value] = {
            'label': lab_type_label,
            'total': total,
            'performed': performed,
            'percentage': round(performed / total * 100) if total > 0 else 0
        }
    
    other_tests_count = OtherTest.objects.filter(USUBJID=enrollment_case).count()
    
    return {
        'total_tests': total_tests,
        'performed_tests': performed_tests,
        'incomplete_tests': incomplete_tests,
        'completion_percentage': round(performed_tests / total_tests * 100) if total_tests > 0 else 0,
        'by_timepoint': by_timepoint,
        'other_tests_count': other_tests_count,
    }


# ==========================================
# FILTER FORM
# ==========================================

class LaboratoryFilterForm(forms.Form):
    """Filter form for laboratory test views"""
    
    lab_type = forms.ChoiceField(
        choices=[('', _('All Timepoints'))] + list(LaboratoryTest.LabTypeChoices.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='1'
    )
    
    category = forms.ChoiceField(
        choices=[('', _('All Categories'))] + list(LaboratoryTest.CategoryChoices.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    performed_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


# ==========================================
# OTHER TEST FORMSET
# ==========================================

class BaseOtherTestFormSet(BaseModelFormSet):
    """Base formset for other tests"""
    
    def clean(self):
        """Prevent duplicate test names"""
        if any(self.errors):
            return
        
        test_combinations = []
        
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get('DELETE'):
                continue
            
            test_name = form.cleaned_data.get('OTHERTESTNAME')
            lab_type = form.cleaned_data.get('LAB_TYPE')
            
            if test_name and lab_type:
                combination = (test_name.strip().lower(), lab_type)
                
                if combination in test_combinations:
                    lab_type_display = dict(OtherTest.LabTypeChoices.choices).get(lab_type, lab_type)
                    form.add_error('OTHERTESTNAME',
                        _('Test "%(name)s" already exists for %(timepoint)s') % {
                            'name': test_name,
                            'timepoint': lab_type_display
                        }
                    )
                else:
                    test_combinations.append(combination)


OtherTestFormSet = modelformset_factory(
    OtherTest,
    form=OtherTestForm,
    formset=BaseOtherTestFormSet,
    extra=1,  # Show 1 empty form
    can_delete=True,  # Can delete custom tests
    can_order=False,
)