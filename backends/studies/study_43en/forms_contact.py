from django import forms
from django.utils.translation import gettext_lazy as _
from datetime import date

from .models.patient import ScreeningCase
from .models.contact import (
    ScreeningContact, 
    EnrollmentContact,
    ContactUnderlyingCondition,
    ContactMedHisDrug,
    ContactFollowUp28, 
    ContactFollowUp90,
    ContactMedicationHistory28,
    ContactMedicationHistory90,
    ContactEndCaseCRF, 
    ContactSampleCollection,
)

# ==========================================
# COMMON CHOICES
# ==========================================

SITEID_CHOICES = [
    ('003', '003'),
    ('011', '011'),
    ('020', '020'),
]


# ==========================================
# SCREENING FORMS
# ==========================================

class ScreeningContactForm(forms.ModelForm):
    """Form for ScreeningContact model"""
    
    SITEID = forms.ChoiceField(
        choices=SITEID_CHOICES,
        label=_("Mã cơ sở"),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    
    # Override BooleanField thành ChoiceField để xử lý chính xác
    LIVEIN5DAYS3MTHS = forms.ChoiceField(
        choices=[('0', 'Không'), ('1', 'Có')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Sống chung ≥5 ngày trong 3 tháng')
    )
    
    MEALCAREONCEDAY = forms.ChoiceField(
        choices=[('0', 'Không'), ('1', 'Có')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Ăn cùng/chăm sóc ≥1 lần/ngày')
    )
    
    CONSENTTOSTUDY = forms.ChoiceField(
        choices=[('0', 'Không'), ('1', 'Có')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Đồng ý tham gia nghiên cứu')
    )
    
    class Meta:
        model = ScreeningContact
        fields = [
            'SCRID', 'SITEID', 'INITIAL', 'SUBJIDENROLLSTUDY',
            'LIVEIN5DAYS3MTHS', 'MEALCAREONCEDAY', 'CONSENTTOSTUDY',
            'SCREENINGFORMDATE', 'COMPLETEDBY', 'COMPLETEDDATE'
        ]
        widgets = {
            'SCREENINGFORMDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'SUBJIDENROLLSTUDY': forms.Select(attrs={'class': 'form-control select2'}),
            'SCRID': forms.TextInput(attrs={'readonly': True, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Tạo mã SCRID mới cho form tạo mới
        if not self.instance.pk:
            last_screening = ScreeningContact.objects.order_by('-SCRID').first()
            new_SCRID = "CS-001"
            
            if last_screening and last_screening.SCRID:
                try:
                    import re
                    match = re.search(r'CS-(\d+)', last_screening.SCRID)
                    if match:
                        last_num = int(match.group(1))
                        new_SCRID = f"CS-{last_num + 1:03d}"
                except (ValueError, AttributeError):
                    pass
            
            self.fields['SCRID'].initial = new_SCRID
            self.fields['SCRID'].help_text = _("Mã screening contact được tạo tự động")
        
        # Nếu đã có USUBJID, hiển thị nó trong form
        if self.instance.pk and self.instance.USUBJID:
            self.fields['USUBJID'] = forms.CharField(
                required=False,
                disabled=True,
                label=_("USUBJID"),
                initial=self.instance.USUBJID
            )
        
        # Thêm các class CSS cho form fields
        for field in self.fields.values():
            if not hasattr(field.widget, 'input_type') or field.widget.input_type != 'radio':
                if 'class' not in field.widget.attrs:
                    field.widget.attrs.update({'class': 'form-control'})
        
        # Đặt giá trị mặc định cho form mới
        if not self.instance.pk:
            boolean_fields = ['LIVEIN5DAYS3MTHS', 'MEALCAREONCEDAY', 'CONSENTTOSTUDY']
            for field_name in boolean_fields:
                self.fields[field_name].initial = '0'
        else:
            # Đối với form cập nhật, chuyển giá trị boolean thành string
            for field_name in ['LIVEIN5DAYS3MTHS', 'MEALCAREONCEDAY', 'CONSENTTOSTUDY']:
                if hasattr(self.instance, field_name):
                    self.fields[field_name].initial = '1' if getattr(self.instance, field_name) else '0'
        
        # Lọc danh sách bệnh nhân - hiển thị tất cả bệnh nhân đã sàng lọc
        available_patients = ScreeningCase.objects.filter(
            SUBJID__startswith='A-'
        ).order_by('INITIAL', 'USUBJID')
        self.fields['SUBJIDENROLLSTUDY'].queryset = available_patients
        self.fields['SUBJIDENROLLSTUDY'].label_from_instance = lambda obj: f"{obj.INITIAL} ({obj.USUBJID})"
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Chuyển đổi ChoiceField string "0"/"1" thành boolean
        boolean_fields = ['LIVEIN5DAYS3MTHS', 'MEALCAREONCEDAY', 'CONSENTTOSTUDY']
        for field_name in boolean_fields:
            value = cleaned_data.get(field_name)
            if value is not None:
                cleaned_data[field_name] = (value == '1')
        
        return cleaned_data


# ==========================================
# ENROLLMENT FORMS
# ==========================================

class EnrollmentContactForm(forms.ModelForm):
    """Form cho EnrollmentContact model - không bao gồm underlying conditions"""
    
    class Meta:
        model = EnrollmentContact
        exclude = ['USUBJID', 'LISTUNDERLYING']  # Exclude LISTUNDERLYING vì giờ là model riêng
        widgets = {
            'ENRDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'ENTEREDTIME': forms.DateTimeInput(attrs={'class': 'form-control'}),
            'SEX': forms.Select(attrs={'class': 'form-control'}),
            'ETHNICITY': forms.TextInput(attrs={'class': 'form-control'}),
            'SPECIFYIFOTHERETHNI': forms.TextInput(attrs={'class': 'form-control'}),
            'OCCUPATION': forms.TextInput(attrs={'class': 'form-control'}),
            'RELATIONSHIP': forms.TextInput(attrs={'class': 'form-control'}),
            'MEDHISDRUG': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'OTHERDISEASESPECIFY': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Thêm class cho các trường nhập liệu
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs.update({'class': 'form-control'})


class ContactUnderlyingConditionForm(forms.ModelForm):
    """Form riêng cho ContactUnderlyingCondition - OneToOne với EnrollmentContact"""
    
    class Meta:
        model = ContactUnderlyingCondition
        exclude = ['USUBJID', 'ENTRY', 'ENTEREDTIME']
        widgets = {
            'OTHERDISEASESPECIFY': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Thêm class cho các checkbox
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
        
        # Thêm labels tiếng Việt
        labels = {
            'HEARTFAILURE': 'Suy tim',
            'DIABETES': 'Đái tháo đường',
            'COPD': 'COPD/VPQ mạn',
            'HEPATITIS': 'Viêm gan mạn',
            'CAD': 'Bệnh mạch vành',
            'KIDNEYDISEASE': 'Bệnh thận mạn',
            'ASTHMA': 'Hen',
            'CIRRHOSIS': 'Xơ gan',
            'HYPERTENSION': 'Tăng huyết áp',
            'AUTOIMMUNE': 'Bệnh tự miễn',
            'CANCER': 'Ung thư',
            'ALCOHOLISM': 'Nghiện rượu',
            'HIV': 'HIV',
            'ADRENALINSUFFICIENCY': 'Suy thượng thận',
            'BEDRIDDEN': 'Nằm liệt giường',
            'PEPTICULCER': 'Loét dạ dày',
            'COLITIS_IBS': 'Viêm loét đại tràng/IBS',
            'SENILITY': 'Lão suy',
            'MALNUTRITION_WASTING': 'Suy dinh dưỡng/suy mòn',
            'OTHERDISEASE': 'Khác, ghi rõ',
            'OTHERDISEASESPECIFY': 'Chi tiết bệnh khác',
        }
        for field_name, label in labels.items():
            if field_name in self.fields:
                self.fields[field_name].label = _(label)


class ContactMedHisDrugForm(forms.ModelForm):
    """Form cho ContactMedHisDrug model"""
    
    class Meta:
        model = ContactMedHisDrug
        fields = ['SEQUENCE', 'DRUGNAME', 'DOSAGE', 'USAGETIME', 'USAGEREASON']
        widgets = {
            'DRUGNAME': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên thuốc'}),
            'DOSAGE': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Liều dùng'}),
            'USAGETIME': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Thời gian dùng'}),
            'USAGEREASON': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Lý do dùng', 'rows': 2}),
            'SEQUENCE': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['SEQUENCE'].required = False


ContactMedHisDrugFormSet = forms.inlineformset_factory(
    EnrollmentContact,
    ContactMedHisDrug,
    form=ContactMedHisDrugForm,
    extra=1,
    can_delete=True
)


# ==========================================
# SAMPLE COLLECTION FORMS
# ==========================================

class ContactSampleCollectionForm(forms.ModelForm):
    """Form for ContactSampleCollection model"""
    
    class Meta:
        model = ContactSampleCollection
        exclude = ('USUBJID',)
        widgets = {
            'SAMPLE_TYPE': forms.RadioSelect(),
            'SAMPLE': forms.RadioSelect(choices=((True, _('Có')), (False, _('Không')))),
            'STOOL': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'STOOLDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'RECTSWAB': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'RECTSWABDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'THROATSWAB': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'THROATSWABDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'BLOOD': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'BLOODDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'REASONIFNO': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'CULTRES_1': forms.RadioSelect(),
            'KLEBPNEU_1': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'OTHERRES_1': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'OTHERRESSPECIFY_1': forms.TextInput(attrs={'class': 'form-control'}),
            'CULTRES_2': forms.RadioSelect(),
            'KLEBPNEU_2': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'OTHERRES_2': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'OTHERRESSPECIFY_2': forms.TextInput(attrs={'class': 'form-control'}),
            'CULTRES_3': forms.RadioSelect(),
            'KLEBPNEU_3': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'OTHERRES_3': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'OTHERRESSPECIFY_3': forms.TextInput(attrs={'class': 'form-control'}),
            'COMPLETEDBY': forms.TextInput(attrs={'class': 'form-control'}),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Ẩn BLOOD/BLOODDATE nếu không phải lần 1
        if self.instance and self.instance.SAMPLE_TYPE != '1':
            self.fields.pop('BLOOD', None)
            self.fields.pop('BLOODDATE', None)
        
        # COMPLETEDDATE không required
        self.fields['COMPLETEDDATE'].required = False
        
        # Set initial cho COMPLETEDDATE nếu chưa có
        if not self.initial.get('COMPLETEDDATE'):
            self.initial['COMPLETEDDATE'] = date.today()
    
    def clean_COMPLETEDDATE(self):
        completed_date = self.cleaned_data.get('COMPLETEDDATE')
        if not completed_date:
            return date.today()
        return completed_date


# ==========================================
# FOLLOW-UP FORMS
# ==========================================

class ContactFollowUp28Form(forms.ModelForm):
    """Form for ContactFollowUp28 model"""
    
    class Meta:
        model = ContactFollowUp28
        fields = [
            'ASSESSED', 'ASSESSDATE',
            'HOSP2D', 'DIAL', 'CATHETER', 'SONDE',
            'HOMEWOUNDCARE', 'LONGTERMCAREFACILITY',
            'MEDICATIONUSE', 'COMPLETEDBY', 'COMPLETEDDATE'
        ]
        widgets = {
            'ASSESSED': forms.Select(attrs={'class': 'form-control'}),
            'ASSESSDATE': forms.DateInput(attrs={'class': 'form-control datepicker', 'autocomplete': 'off'}),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'form-control datepicker', 'autocomplete': 'off'}),
            'COMPLETEDBY': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ASSESSED'].choices = [
            ('', '-- Chọn --'),
            ('Yes', 'Có'),
            ('No', 'Không'),
            ('NA', 'Không áp dụng'),
        ]
        
        # Thêm class cho checkboxes
        for field_name in ['HOSP2D', 'DIAL', 'CATHETER', 'SONDE', 'HOMEWOUNDCARE', 'LONGTERMCAREFACILITY', 'MEDICATIONUSE']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({'class': 'form-check-input'})


class ContactFollowUp90Form(forms.ModelForm):
    """Form for ContactFollowUp90 model"""
    
    class Meta:
        model = ContactFollowUp90
        fields = [
            'ASSESSED', 'ASSESSDATE',
            'HOSP2D', 'DIAL', 'CATHETER', 'SONDE',
            'HOMEWOUNDCARE', 'LONGTERMCAREFACILITY',
            'MEDICATIONUSE', 'COMPLETEDBY', 'COMPLETEDDATE'
        ]
        widgets = {
            'ASSESSED': forms.Select(attrs={'class': 'form-control'}),
            'ASSESSDATE': forms.DateInput(attrs={'class': 'form-control datepicker', 'autocomplete': 'off'}),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'form-control datepicker', 'autocomplete': 'off'}),
            'COMPLETEDBY': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ASSESSED'].choices = [
            ('', '-- Chọn --'),
            ('Yes', 'Có'),
            ('No', 'Không'),
            ('NA', 'Không áp dụng'),
        ]
        
        # Thêm class cho checkboxes
        for field_name in ['HOSP2D', 'DIAL', 'CATHETER', 'SONDE', 'HOMEWOUNDCARE', 'LONGTERMCAREFACILITY', 'MEDICATIONUSE']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({'class': 'form-check-input'})


# ==========================================
# MEDICATION HISTORY FORMS
# ==========================================

class ContactMedicationHistory28Form(forms.ModelForm):
    """Form for ContactMedicationHistory28 model"""
    
    class Meta:
        model = ContactMedicationHistory28
        fields = ['EPISODE', 'MEDICATIONNAME', 'DOSAGE', 'USAGE_PERIOD', 'REASON']
        widgets = {
            'EPISODE': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'readonly': True}),
            'MEDICATIONNAME': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Tên thuốc'}),
            'DOSAGE': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Liều dùng'}),
            'USAGE_PERIOD': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Thời gian dùng'}),
            'REASON': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2, 'placeholder': 'Lý do dùng'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['EPISODE'].required = False


class ContactMedicationHistory90Form(forms.ModelForm):
    """Form for ContactMedicationHistory90 model"""
    
    class Meta:
        model = ContactMedicationHistory90
        fields = ['EPISODE', 'MEDICATIONNAME', 'DOSAGE', 'USAGE_PERIOD', 'REASON']
        widgets = {
            'EPISODE': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'readonly': True}),
            'MEDICATIONNAME': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Tên thuốc'}),
            'DOSAGE': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Liều dùng'}),
            'USAGE_PERIOD': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Thời gian dùng'}),
            'REASON': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2, 'placeholder': 'Lý do dùng'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['EPISODE'].required = False


class ContactMedicationHistoryFormSet(forms.BaseInlineFormSet):
    """Custom FormSet with validation"""
    
    def add_fields(self, form, index):
        """Auto-set EPISODE field"""
        super().add_fields(form, index)
        if not form.instance.pk:
            form.instance.EPISODE = index + 1
    
    def clean(self):
        super().clean()
        
        if not any(self.forms):
            return
        
        # Check if at least one medication is entered
        has_medication = False
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                if form.cleaned_data.get('MEDICATIONNAME'):
                    has_medication = True
                    break
        
        # If parent has MEDICATIONUSE=True, require at least one medication
        parent = getattr(self, 'instance', None)
        if parent and hasattr(parent, 'MEDICATIONUSE') and parent.MEDICATIONUSE:
            if not has_medication:
                raise forms.ValidationError(
                    _("Vui lòng nhập ít nhất một loại thuốc khi 'Sử dụng thuốc' được chọn")
                )


ContactMedicationHistory28FormSet = forms.inlineformset_factory(
    ContactFollowUp28,
    ContactMedicationHistory28,
    form=ContactMedicationHistory28Form,
    formset=ContactMedicationHistoryFormSet,
    extra=1,
    can_delete=True,
    validate_min=False,
    validate_max=False,
    fields=['EPISODE', 'MEDICATIONNAME', 'DOSAGE', 'USAGE_PERIOD', 'REASON']
)

ContactMedicationHistory90FormSet = forms.inlineformset_factory(
    ContactFollowUp90,
    ContactMedicationHistory90,
    form=ContactMedicationHistory90Form,
    formset=ContactMedicationHistoryFormSet,
    extra=1,
    can_delete=True,
    validate_min=False,
    validate_max=False,
    fields=['EPISODE', 'MEDICATIONNAME', 'DOSAGE', 'USAGE_PERIOD', 'REASON']
)


# ==========================================
# END CASE FORMS
# ==========================================

class ContactEndCaseCRFForm(forms.ModelForm):
    """Form for ContactEndCaseCRF model"""
    
    class Meta:
        model = ContactEndCaseCRF
        fields = [
            'ENDDATE', 'ENDFORMDATE',
            'VICOMPLETED', 'V2COMPLETED', 'V3COMPLETED',
            'WITHDRAWREASON', 'INCOMPLETE',
            'INCOMPLETEDEATH', 'INCOMPLETEMOVED', 'INCOMPLETEOTHER',
            'LOSTTOFOLLOWUP',
        ]
        widgets = {
            'ENDDATE': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'ENDFORMDATE': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'VICOMPLETED': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'V2COMPLETED': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'V3COMPLETED': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'WITHDRAWREASON': forms.RadioSelect(),
            'INCOMPLETE': forms.RadioSelect(),
            'INCOMPLETEDEATH': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'INCOMPLETEMOVED': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'INCOMPLETEOTHER': forms.TextInput(attrs={'class': 'form-control'}),
            'LOSTTOFOLLOWUP': forms.RadioSelect(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set labels
        self.fields['WITHDRAWREASON'].label = _("Người tham gia rút khỏi hoặc bị yêu cầu rút khỏi nghiên cứu?")
        self.fields['INCOMPLETE'].label = _("Người tham gia không thể hoàn tất nghiên cứu?")
        self.fields['INCOMPLETEDEATH'].label = _("Người tham gia tử vong")
        self.fields['INCOMPLETEMOVED'].label = _("Người tham gia không thể đến địa điểm nghiên cứu")
        self.fields['INCOMPLETEOTHER'].label = _("Khác, ghi rõ:")
        self.fields['LOSTTOFOLLOWUP'].label = _("Người tham gia bị mất liên lạc?")
        
        # Set required=False for dependent fields
        self.fields['INCOMPLETEDEATH'].required = False
        self.fields['INCOMPLETEMOVED'].required = False
        self.fields['INCOMPLETEOTHER'].required = False
        
        # Set default values for new forms
        if not self.instance.pk:
            self.fields['WITHDRAWREASON'].initial = 'na'
            self.fields['INCOMPLETE'].initial = 'na'
            self.fields['LOSTTOFOLLOWUP'].initial = 'na'
    
    def clean(self):
        cleaned_data = super().clean()
        
        # If INCOMPLETE is 'yes', at least one reason must be selected
        if cleaned_data.get('INCOMPLETE') == 'yes':
            if not (
                cleaned_data.get('INCOMPLETEDEATH') or
                cleaned_data.get('INCOMPLETEMOVED') or
                cleaned_data.get('INCOMPLETEOTHER')
            ):
                raise forms.ValidationError(
                    _("Vui lòng chọn ít nhất một lý do không hoàn tất nghiên cứu.")
                )
        
        return cleaned_data