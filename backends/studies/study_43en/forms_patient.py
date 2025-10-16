from django import forms
from django.utils.translation import gettext_lazy as _
from datetime import date

# Import models from refactored structure
from backends.studies.study_43en.models.patient import (
    # Screening
    ScreeningCase,
    
    # Enrollment
    EnrollmentCase,
    MedHisDrug,
    UnderlyingCondition,
    
    # Clinical
    ClinicalCase,
    HistorySymptom,
    Symptom_72H,
    ImproveSympt,
    PriorAntibiotic,
    InitialAntibiotic,
    MainAntibiotic,
    VasoIDrug,
    LaboratoryTest,
    OtherTest,
    CLI_Microbiology,
    AEHospEvent,
    HospiProcess,
    
    # Discharge
    DischargeCase,
    DischargeICD,
    
    # Follow-up
    FollowUpCase,
    FollowUpCase90,
    FollowUpAntibiotic,
    FollowUpAntibiotic90,
    Rehospitalization,
    Rehospitalization90,
    
    # Laboratory
    LAB_Microbiology,
    AntibioticSensitivity,
    
    # Sample
    SampleCollection,
    
    # EndCase
    EndCaseCRF,
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

class ScreeningCaseForm(forms.ModelForm):
    """Form for ScreeningCase model"""

    SITEID = forms.ChoiceField(choices=SITEID_CHOICES, label="Mã cơ sở")

    # Override BooleanField thành ChoiceField để xử lý chính xác
    UPPER16AGE = forms.ChoiceField(
        choices=[('0', 'Không'), ('1', 'Có')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Tuổi trên 16')
    )
    INFPRIOR2OR48HRSADMIT = forms.ChoiceField(
        choices=[('0', 'Không'), ('1', 'Có')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Nhiễm khuẩn trước 2h hoặc sau 48h nhập viện')
    )
    ISOLATEDKPNFROMINFECTIONORBLOOD = forms.ChoiceField(
        choices=[('0', 'Không'), ('1', 'Có')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Phân lập được KPN từ nhiễm khuẩn/máu')
    )
    KPNISOUNTREATEDSTABLE = forms.ChoiceField(
        choices=[('0', 'Không'), ('1', 'Có')],
        widget=forms.RadioSelect,
        required=True,
        label=_('KPN chưa điều trị ổn định')
    )
    CONSENTTOSTUDY = forms.ChoiceField(
        choices=[('0', 'Không'), ('1', 'Có')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Đồng ý tham gia nghiên cứu')
    )
    
    class Meta:
        model = ScreeningCase
        fields = [
            'SCRID', 'STUDYID', 'SITEID', 'INITIAL',
            'UPPER16AGE', 'INFPRIOR2OR48HRSADMIT', 'ISOLATEDKPNFROMINFECTIONORBLOOD',
            'KPNISOUNTREATEDSTABLE', 'CONSENTTOSTUDY', 'SCREENINGFORMDATE', 'UNRECRUITED_REASON',
            'COMPLETEDBY', 'COMPLETEDDATE'
        ]
        widgets = {
            'SCREENINGFORMDATE': forms.DateInput(attrs={'class': 'datepicker'}),
            'SCRID': forms.TextInput(attrs={'readonly': True, 'class': 'form-control'}),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'datepicker'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Nếu đã có SUBJID, chỉ hiển thị readonly
        if self.instance.pk and self.instance.SUBJID:
            self.fields['SUBJID'] = forms.CharField(
                required=False,
                disabled=True,
                label=_("Mã bệnh nhân"),
                initial=self.instance.SUBJID
            )

        # Nếu đã có USUBJID, hiển thị nó trong form
        if self.instance.pk and self.instance.USUBJID:
            self.fields['USUBJID'] = forms.CharField(
                required=False, 
                disabled=True,
                label=_("Mã bệnh nhân"),
                initial=self.instance.USUBJID
            )
        
        # Thêm các class CSS cho form fields
        for field in self.fields.values():
            if not hasattr(field.widget, 'input_type') or field.widget.input_type != 'radio':
                field.widget.attrs.update({'class': 'form-control'})
        
        # Đặt giá trị mặc định cho form mới
        if not self.instance.pk:
            boolean_fields = ['UPPER16AGE', 'INFPRIOR2OR48HRSADMIT', 
                            'ISOLATEDKPNFROMINFECTIONORBLOOD', 'KPNISOUNTREATEDSTABLE', 'CONSENTTOSTUDY']
            for field_name in boolean_fields:
                self.fields[field_name].initial = '0'
        else:
            # Đối với form cập nhật, chuyển giá trị boolean thành string
            if hasattr(self.instance, 'UPPER16AGE'):
                self.fields['UPPER16AGE'].initial = '1' if self.instance.UPPER16AGE else '0'
            if hasattr(self.instance, 'INFPRIOR2OR48HRSADMIT'):
                self.fields['INFPRIOR2OR48HRSADMIT'].initial = '1' if self.instance.INFPRIOR2OR48HRSADMIT else '0'
            if hasattr(self.instance, 'ISOLATEDKPNFROMINFECTIONORBLOOD'):
                self.fields['ISOLATEDKPNFROMINFECTIONORBLOOD'].initial = '1' if self.instance.ISOLATEDKPNFROMINFECTIONORBLOOD else '0'
            if hasattr(self.instance, 'KPNISOUNTREATEDSTABLE'):
                self.fields['KPNISOUNTREATEDSTABLE'].initial = '1' if self.instance.KPNISOUNTREATEDSTABLE else '0'
            if hasattr(self.instance, 'CONSENTTOSTUDY'):
                self.fields['CONSENTTOSTUDY'].initial = '1' if self.instance.CONSENTTOSTUDY else '0'
    
    def clean(self):
        cleaned_data = super().clean()
        boolean_fields = [
            'UPPER16AGE', 'INFPRIOR2OR48HRSADMIT',
            'ISOLATEDKPNFROMINFECTIONORBLOOD', 'KPNISOUNTREATEDSTABLE', 'CONSENTTOSTUDY'
        ]
        for field_name in boolean_fields:
            value = cleaned_data.get(field_name)
            if value == '1':
                cleaned_data[field_name] = True
            else:
                cleaned_data[field_name] = False

        # Validation cho CONSENTTOSTUDY
        if (
            cleaned_data.get('UPPER16AGE') and
            cleaned_data.get('INFPRIOR2OR48HRSADMIT') and
            cleaned_data.get('ISOLATEDKPNFROMINFECTIONORBLOOD') and
            not cleaned_data.get('KPNISOUNTREATEDSTABLE')
        ):
            pass
        else:
            if cleaned_data.get('CONSENTTOSTUDY'):
                self.add_error(
                    'CONSENTTOSTUDY',
                    _("Chỉ được chọn 'Có' khi: Tuổi trên 16, Nhiễm khuẩn trước 2h hoặc sau 48h nhập viện, Phân lập KPN từ nhiễm khuẩn/máu đều là 'Có' và 'KPN chưa điều trị ổn định' là 'Không'")
                )
                cleaned_data['CONSENTTOSTUDY'] = False

        return cleaned_data


# ==========================================
# ENROLLMENT FORMS
# ==========================================

class EnrollmentCaseForm(forms.ModelForm):
    """Form cho EnrollmentCase model - không bao gồm underlying conditions"""

    class Meta:
        model = EnrollmentCase
        exclude = ['USUBJID', 'LISTUNDERLYING']  # Exclude LISTUNDERLYING vì giờ là model riêng
        widgets = {
            'ENRDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'PRIORHOSPIADMISDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'ENTEREDTIME': forms.DateTimeInput(attrs={'class': 'form-control'}),
            'SEX': forms.Select(attrs={'class': 'form-control'}),
            'RESIDENCETYPE': forms.Select(attrs={'class': 'form-control'}),
            'WORKPLACETYPE': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Thêm class cho các trường nhập liệu
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)):
                field.widget.attrs.update({'class': 'form-control'})


class UnderlyingConditionForm(forms.ModelForm):
    """Form riêng cho UnderlyingCondition - OneToOne với EnrollmentCase"""
    
    class Meta:
        model = UnderlyingCondition
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


class MedHisDrugForm(forms.ModelForm):
    """Form cho MedHisDrug model"""
    
    class Meta:
        model = MedHisDrug
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


MedHisDrugFormSet = forms.inlineformset_factory(
    EnrollmentCase,
    MedHisDrug,
    form=MedHisDrugForm,
    extra=1,
    can_delete=True
)


# ==========================================
# CLINICAL FORMS
# ==========================================

class ClinicalCaseForm(forms.ModelForm):
    """Form cho ClinicalCase model - không bao gồm symptoms"""

    SUPPORTTYPE = forms.MultipleChoiceField(
        choices=[
            ('Oxy mũi/mask', _('Oxy mũi/mask')),
            ('HFNC/NIV', _('HFNC/NIV')),
            ('Thở máy', _('Thở máy')),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label=_("Loại hỗ trợ hô hấp")
    )

    THREE_STATE_CHOICES = [
        ('yes', 'Có'),
        ('no', 'Không'),
        ('unknown', 'Không biết'),
    ]

    BLOODINFECT = forms.ChoiceField(
        choices=THREE_STATE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_("Nhiễm khuẩn huyết"),
        required=False
    )
    SEPTICSHOCK = forms.ChoiceField(
        choices=THREE_STATE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_("Sốc nhiễm khuẩn"),
        required=False
    )

    class Meta:
        model = ClinicalCase
        exclude = ['USUBJID', 'LISTBASICSYMTOMS', 'LISTCLINISYMTOMS']  # Exclude vì giờ là models riêng
        widgets = {
            'ADMISDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'SYMPTOMONSETDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'ENTEREDTIME': forms.DateTimeInput(attrs={'class': 'form-control'}),
            'INFECTFOCUS48H': forms.Select(attrs={'class': 'form-control select2'}),
            'INFECTSRC': forms.Select(attrs={'class': 'form-control select2'}),
            'FLUID6HOURS': forms.Select(attrs={'class': 'form-control select2'}),
            'FLUID24HOURS': forms.Select(attrs={'class': 'form-control select2'}),
            'DRAINAGETYPE': forms.Select(attrs={'class': 'form-control select2'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field, forms.BooleanField):
                if not field.widget.attrs.get('class'):
                    field.widget.attrs.update({'class': 'form-control'})

        # Set initial cho SUPPORTTYPE
        if self.instance and self.instance.pk and self.instance.SUPPORTTYPE:
            self.fields['SUPPORTTYPE'].initial = self.instance.SUPPORTTYPE

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.SUPPORTTYPE = self.cleaned_data.get('SUPPORTTYPE', [])
        if commit:
            instance.save()
        return instance


class HistorySymptomForm(forms.ModelForm):
    """Form riêng cho HistorySymptom - OneToOne với ClinicalCase"""
    
    class Meta:
        model = HistorySymptom
        exclude = ['USUBJID', 'ENTRY', 'ENTEREDTIME']
        widgets = {
            'SPECIFYOTHERSYMPTOM': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Thêm class cho các checkbox
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})


class Symptom72HForm(forms.ModelForm):
    """Form riêng cho Symptom_72H - OneToOne với ClinicalCase"""
    
    class Meta:
        model = Symptom_72H
        exclude = ['USUBJID', 'ENTRY', 'ENTEREDTIME']
        widgets = {
            'SPECIFYOTHERSYMPTOM_2': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Thêm class cho các checkbox
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})


class PriorAntibioticForm(forms.ModelForm):
    """Form for prior antibiotics"""
    
    class Meta:
        model = PriorAntibiotic
        fields = ['PRIORANTIBIONAME', 'PRIORANTIBIODOSAGE', 'PRIORANTIBIOSTARTDTC', 'PRIORANTIBIOENDDTC']
        widgets = {
            'PRIORANTIBIOSTARTDTC': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'PRIORANTIBIOENDDTC': forms.DateInput(attrs={'class': 'datepicker form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not field.widget.attrs.get('class'):
                field.widget.attrs.update({'class': 'form-control'})


class InitialAntibioticForm(forms.ModelForm):
    """Form for initial antibiotics"""
    
    class Meta:
        model = InitialAntibiotic
        fields = ['INITIALANTIBIONAME', 'INITIALANTIBIODOSAGE', 'INITIALANTIBIOSTARTDTC', 'INITIALANTIBIOENDDTC']
        widgets = {
            'INITIALANTIBIOSTARTDTC': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'INITIALANTIBIOENDDTC': forms.DateInput(attrs={'class': 'datepicker form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not field.widget.attrs.get('class'):
                field.widget.attrs.update({'class': 'form-control'})


class MainAntibioticForm(forms.ModelForm):
    """Form for main antibiotics"""
    
    class Meta:
        model = MainAntibiotic
        fields = ['MAINANTIBIONAME', 'MAINANTIBIODOSAGE', 'MAINANTIBIOSTARTDTC', 'MAINANTIBIOENDDTC']
        widgets = {
            'MAINANTIBIOSTARTDTC': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'MAINANTIBIOENDDTC': forms.DateInput(attrs={'class': 'datepicker form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not field.widget.attrs.get('class'):
                field.widget.attrs.update({'class': 'form-control'})


# Formsets for antibiotics
PriorAntibioticFormSet = forms.inlineformset_factory(
    ClinicalCase,
    PriorAntibiotic,
    form=PriorAntibioticForm,
    extra=0,
    can_delete=True
)

InitialAntibioticFormSet = forms.inlineformset_factory(
    ClinicalCase,
    InitialAntibiotic,
    form=InitialAntibioticForm,
    extra=0,
    can_delete=True
)

MainAntibioticFormSet = forms.inlineformset_factory(
    ClinicalCase,
    MainAntibiotic,
    form=MainAntibioticForm,
    extra=0,
    can_delete=True
)


class VasoIDrugForm(forms.ModelForm):
    """Form for VasoIDrug model"""
    
    class Meta:
        model = VasoIDrug
        fields = ['VASOIDRUGNAME', 'VASOIDRUGDOSAGE', 'VASOIDRUGSTARTDTC', 'VASOIDRUGENDDTC']
        widgets = {
            'VASOIDRUGSTARTDTC': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'VASOIDRUGENDDTC': forms.DateInput(attrs={'class': 'datepicker form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not field.widget.attrs.get('class'):
                field.widget.attrs.update({'class': 'form-control'})


VasoIDrugFormSet = forms.inlineformset_factory(
    ClinicalCase,
    VasoIDrug,
    form=VasoIDrugForm,
    extra=0,
    can_delete=True
)


class ImproveSymptForm(forms.ModelForm):
    """Form for ImproveSympt model"""
    
    class Meta:
        model = ImproveSympt
        fields = ['IMPROVE_SYMPTS', 'SYMPTS', 'IMPROVE_CONDITIONS', 'SYMPTSDTC']
        widgets = {
            'IMPROVE_SYMPTS': forms.Select(attrs={'class': 'form-control'}),
            'SYMPTS': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'IMPROVE_CONDITIONS': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'SYMPTSDTC': forms.DateInput(attrs={'class': 'form-control datepicker'}),
        }


ImproveSymptFormSet = forms.inlineformset_factory(
    ClinicalCase,
    ImproveSympt,
    form=ImproveSymptForm,
    extra=0,
    can_delete=True
)

# ==========================================
# HOSPITALIZATION PROCESS FORMS
# ==========================================

class HospiProcessForm(forms.ModelForm):
    """
    Form cho quá trình nằm viện - tracking department transfers
    Ghi lại các khoa mà bệnh nhân đã chuyển qua trong quá trình điều trị
    """
    
    class Meta:
        model = HospiProcess  # Bạn cần import model này
        fields = ['DEPTNAME', 'STARTDTC', 'ENDDTC', 'TRANSFER_REASON']
        widgets = {
            'DEPTNAME': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tên khoa (VD: Khoa Hồi sức cấp cứu)'
            }),
            'STARTDTC': forms.DateInput(attrs={
                'class': 'form-control datepicker',
                'autocomplete': 'off',
                'placeholder': 'YYYY-MM-DD'
            }),
            'ENDDTC': forms.DateInput(attrs={
                'class': 'form-control datepicker',
                'autocomplete': 'off',
                'placeholder': 'YYYY-MM-DD'
            }),
            'TRANSFER_REASON': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Lý do chuyển khoa...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Labels tiếng Việt
        self.fields['DEPTNAME'].label = _('Tên khoa')
        self.fields['STARTDTC'].label = _('Ngày bắt đầu')
        self.fields['ENDDTC'].label = _('Ngày kết thúc')
        self.fields['TRANSFER_REASON'].label = _('Lý do chuyển khoa')
        
        # Không bắt buộc ENDDTC nếu bệnh nhân vẫn còn ở khoa đó
        self.fields['ENDDTC'].required = False
        self.fields['TRANSFER_REASON'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('STARTDTC')
        end_date = cleaned_data.get('ENDDTC')
        
        # Validation: End date phải sau Start date
        if start_date and end_date:
            if end_date < start_date:
                self.add_error('ENDDTC', 
                    _('Ngày kết thúc phải sau ngày bắt đầu'))
        
        return cleaned_data


# Base FormSet để tự động quản lý sequence/ordering
class BaseHospiProcessFormSet(forms.BaseInlineFormSet):
    """
    Custom formset để xử lý logic đặc biệt cho HospiProcess
    """
    
    def clean(self):
        """
        Validation cho toàn bộ formset:
        - Không được có ngày chồng chéo giữa các khoa
        - Phải có ít nhất 1 khoa nếu form được submit
        """
        if any(self.errors):
            return
        
        departments = []
        has_data = False
        
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
                
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                dept_name = form.cleaned_data.get('DEPTNAME')
                start_date = form.cleaned_data.get('STARTDTC')
                end_date = form.cleaned_data.get('ENDDTC')
                
                if dept_name or start_date:  # Có dữ liệu
                    has_data = True
                    
                    if not dept_name:
                        form.add_error('DEPTNAME', 
                            _('Vui lòng nhập tên khoa'))
                    if not start_date:
                        form.add_error('STARTDTC', 
                            _('Vui lòng nhập ngày bắt đầu'))
                    
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
                        _('Thời gian nằm viện tại khoa này bị trùng với khoa khác'))
    
    def _dates_overlap(self, dept1, dept2):
        """Check if two department stays overlap"""
        start1, end1 = dept1['start'], dept1['end']
        start2, end2 = dept2['start'], dept2['end']
        
        # If either doesn't have end date, can't determine overlap
        if not end1 or not end2:
            return False
        
        # Check if ranges overlap
        return not (end1 < start2 or end2 < start1)
    
    def save_new(self, form, commit=True):
        """Chỉ lưu form nếu có dữ liệu thực sự"""
        instance = super().save_new(form, commit=False)
        
        if instance and (instance.DEPTNAME or instance.STARTDTC):
            if commit:
                instance.save()
            return instance
        return None


# FormSet cho chế độ chỉnh sửa
HospiProcessFormSet = forms.inlineformset_factory(
    ClinicalCase,  # Parent model
    HospiProcess,  # Child model
    form=HospiProcessForm,
    formset=BaseHospiProcessFormSet,
    extra=1,  # Hiển thị 1 form trống để thêm mới
    can_delete=True,
    validate_min=False,
    validate_max=False,
    fields=['DEPTNAME', 'STARTDTC', 'ENDDTC', 'TRANSFER_REASON']
)


# FormSet cho chế độ xem (read-only)
HospiProcessFormSetReadOnly = forms.inlineformset_factory(
    ClinicalCase,
    HospiProcess,
    form=HospiProcessForm,
    extra=0,
    can_delete=False,
    fields=['DEPTNAME', 'STARTDTC', 'ENDDTC', 'TRANSFER_REASON']
)


# ==========================================
# ADVERSE EVENT / HOSPITALIZATION EVENT FORMS
# ==========================================

class AEHospEventForm(forms.ModelForm):
    """
    Form cho biến cố bất lợi trong quá trình nằm viện
    Adverse Events / Serious Adverse Events during hospitalization
    """
    
    class Meta:
        model = AEHospEvent  # Bạn cần import model này
        fields = ['AENAME', 'AEDETAILS', 'AEDTC']
        widgets = {
            'AENAME': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tên biến cố (VD: Sốc phản vệ, Xuất huyết tiêu hóa)'
            }),
            'AEDETAILS': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Mô tả chi tiết biến cố, diễn biến, xử trí...'
            }),
            'AEDTC': forms.DateInput(attrs={
                'class': 'form-control datepicker',
                'autocomplete': 'off',
                'placeholder': 'YYYY-MM-DD'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Labels tiếng Việt
        self.fields['AENAME'].label = _('Tên biến cố')
        self.fields['AEDETAILS'].label = _('Chi tiết biến cố')
        self.fields['AEDTC'].label = _('Ngày xảy ra')
        
        # AEDETAILS không bắt buộc
        self.fields['AEDETAILS'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        ae_name = cleaned_data.get('AENAME')
        ae_date = cleaned_data.get('AEDTC')
        
        # Nếu có tên biến cố thì phải có ngày
        if ae_name and not ae_date:
            self.add_error('AEDTC', 
                _('Vui lòng nhập ngày xảy ra biến cố'))
        
        # Nếu có ngày thì phải có tên
        if ae_date and not ae_name:
            self.add_error('AENAME', 
                _('Vui lòng nhập tên biến cố'))
        
        return cleaned_data


# Base FormSet để xử lý logic đặc biệt
class BaseAEHospEventFormSet(forms.BaseInlineFormSet):
    """
    Custom formset để xử lý adverse events
    """
    
    def clean(self):
        """
        Validation cho toàn bộ formset
        """
        if any(self.errors):
            return
        
        ae_dates = []
        
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
                
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                ae_name = form.cleaned_data.get('AENAME')
                ae_date = form.cleaned_data.get('AEDTC')
                
                if ae_name and ae_date:
                    # Check for duplicate events on same date
                    if (ae_name, ae_date) in ae_dates:
                        form.add_error('AENAME',
                            _('Biến cố này đã được ghi nhận vào cùng ngày'))
                    else:
                        ae_dates.append((ae_name, ae_date))
    
    def save_new(self, form, commit=True):
        """Chỉ lưu form nếu có dữ liệu thực sự"""
        instance = super().save_new(form, commit=False)
        
        if instance and (instance.AENAME or instance.AEDTC):
            if commit:
                instance.save()
            return instance
        return None


# FormSet cho chế độ chỉnh sửa
AEHospEventFormSet = forms.inlineformset_factory(
    ClinicalCase,  # Parent model
    AEHospEvent,   # Child model
    form=AEHospEventForm,
    formset=BaseAEHospEventFormSet,
    extra=1,  # Hiển thị 1 form trống để thêm mới
    can_delete=True,
    validate_min=False,
    validate_max=False,
    fields=['AENAME', 'AEDETAILS', 'AEDTC']
)


# FormSet cho chế độ xem (read-only)
AEHospEventFormSetReadOnly = forms.inlineformset_factory(
    ClinicalCase,
    AEHospEvent,
    form=AEHospEventForm,
    extra=0,
    can_delete=False,
    fields=['AENAME', 'AEDETAILS', 'AEDTC']
)


class LaboratoryTestForm(forms.ModelForm):
    """Form for LaboratoryTest model"""
    
    class Meta:
        model = LaboratoryTest
        fields = ['LAB_TYPE', 'CATEGORY', 'TESTTYPE', 'PERFORMED', 'PERFORMEDDATE', 'RESULT']
        widgets = {
            'LAB_TYPE': forms.Select(attrs={'class': 'form-control'}),
            'CATEGORY': forms.Select(attrs={'class': 'form-control'}),
            'TESTTYPE': forms.Select(attrs={'class': 'form-control'}),
            'PERFORMEDDATE': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'RESULT': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['PERFORMED'].widget.attrs.update({'class': 'form-check-input'})


LaboratoryTestFormSet = forms.modelformset_factory(
    LaboratoryTest,
    form=LaboratoryTestForm,
    extra=0,
    can_delete=False
)


class OtherTestForm(forms.ModelForm):
    """Form for OtherTest model"""
    
    class Meta:
        model = OtherTest
        fields = ['SEQUENCE', 'LAB_TYPE', 'CATEGORY', 'OTHERTESTNAME', 
                  'OTHERTESTPERFORMED', 'OTHERTESTDTC', 'OTHERTESTRESULT']
        widgets = {
            'SEQUENCE': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
            'LAB_TYPE': forms.Select(attrs={'class': 'form-control'}),
            'CATEGORY': forms.Select(attrs={'class': 'form-control'}),
            'OTHERTESTNAME': forms.TextInput(attrs={'class': 'form-control'}),
            'OTHERTESTDTC': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'OTHERTESTRESULT': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['SEQUENCE'].required = False
        self.fields['OTHERTESTPERFORMED'].widget.attrs.update({'class': 'form-check-input'})


OtherTestFormSet = forms.modelformset_factory(
    OtherTest,
    form=OtherTestForm,
    extra=0,
    can_delete=False
)


class MicrobiologyCultureForm(forms.ModelForm):
    """Form for CLI_Microbiology (Clinical microbiology)"""
    
    class Meta:
        model = CLI_Microbiology
        fields = [
            'USUBJID', 'SPECIMENTYPE', 'OTHERSPECIMEN', 'PERFORMEDDATE', 'SPECIMENID',
            'RESULT', 'RESULTDETAILS', 'ORDEREDBYDEPT', 'DEPTDIAGSENT',
            'BACSTRAINISOLDATE', 'COMPLETEDBY', 'COMPLETEDDATE'
        ]
        widgets = {
            'PERFORMEDDATE': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'BACSTRAINISOLDATE': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'SPECIMENTYPE': forms.Select(attrs={'class': 'form-control'}),
            'RESULT': forms.Select(attrs={'class': 'form-control'}),
            'RESULTDETAILS': forms.TextInput(attrs={'class': 'form-control'}),
        }


# ==========================================
# LABORATORY FORMS
# ==========================================

class LAB_MicrobiologyForm(forms.ModelForm):
    """Form for LAB_Microbiology (Laboratory microbiology for sensitivity testing)"""
    
    class Meta:
        model = LAB_Microbiology
        fields = [
            'USUBJID', 'LAB_CASE_SEQ', 'EVENT',
            'STUDYIDS', 'SITEID', 'SUBJID', 'INITIAL',
            'ORDEREDBYDEPT', 'DEPTDIAGSENT',
            'SPECIMENID', 'SPECSAMPLOC', 'OTHERSPECIMEN',
            'SPECSAMPDATE', 'BACSTRAINISOLDATE',
            'COMPLETEDBY', 'COMPLETEDDATE'
        ]
        
        widgets = {
            'EVENT': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'STUDYIDS': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'SITEID': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'SUBJID': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'INITIAL': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'LAB_CASE_SEQ': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
            'SPECSAMPDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'BACSTRAINISOLDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'SPECSAMPLOC': forms.Select(attrs={'class': 'form-control select2'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if not self.instance.pk:
            self.fields['EVENT'].initial = 'LAB_CULTURE'
            self.fields['STUDYIDS'].initial = '43EN'
            self.fields['COMPLETEDDATE'].initial = date.today()
        
        self.fields['OTHERSPECIMEN'].required = False
        
        readonly_fields = ['EVENT', 'STUDYIDS', 'SITEID', 'SUBJID', 'INITIAL', 'LAB_CASE_SEQ']
        for field_name in readonly_fields:
            if field_name in self.fields:
                self.fields[field_name].required = False


LAB_MicrobiologyFormSet = forms.inlineformset_factory(
    EnrollmentCase,
    LAB_Microbiology,
    form=LAB_MicrobiologyForm,
    extra=1,
    can_delete=True
)


class AntibioticSensitivityForm(forms.ModelForm):
    """Form for AntibioticSensitivity"""
    
    class Meta:
        model = AntibioticSensitivity
        fields = [
            'TIER', 'ANTIBIOTIC_NAME', 'OTHER_ANTIBIOTIC_NAME', 
            'SENSITIVITY_LEVEL', 'IZDIAM', 'MIC', 'SEQUENCE'
        ]
        widgets = {
            'TIER': forms.Select(attrs={'class': 'form-control'}),
            'ANTIBIOTIC_NAME': forms.Select(attrs={'class': 'form-control'}),
            'OTHER_ANTIBIOTIC_NAME': forms.TextInput(attrs={'class': 'form-control'}),
            'SENSITIVITY_LEVEL': forms.Select(attrs={'class': 'form-control'}),
            'IZDIAM': forms.TextInput(attrs={'class': 'form-control'}),
            'MIC': forms.TextInput(attrs={'class': 'form-control'}),
            'SEQUENCE': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['OTHER_ANTIBIOTIC_NAME'].required = False
        self.fields['SEQUENCE'].required = False


AntibioticSensitivityFormSet = forms.inlineformset_factory(
    LAB_Microbiology,
    AntibioticSensitivity,
    form=AntibioticSensitivityForm,
    extra=3,
    can_delete=True
)


# ==========================================
# DISCHARGE FORMS
# ==========================================

class DischargeCaseForm(forms.ModelForm):
    """Form for DischargeCase model"""
    
    TRANSFERHOSP = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Bệnh nhân chuyển sang bệnh viện khác?')
    )
    
    DEATHATDISCH = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Bệnh nhân tử vong tại thời điểm ra viện?')
    )
    
    class Meta:
        model = DischargeCase
        fields = [
            'EVENT', 'STUDYID', 'SITEID', 'SUBJID', 'INITIAL',
            'DISCHDATE', 'DISCHSTATUS', 'DISCHSTATUSDETAIL',
            'TRANSFERHOSP', 'TRANSFERREASON', 'TRANSFERLOCATION',
            'DEATHATDISCH', 'DEATHCAUSE',
            'COMPLETEDBY', 'COMPLETEDDATE'
        ]
        
        widgets = {
            'DISCHDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'EVENT': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'STUDYID': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'SITEID': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'SUBJID': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'INITIAL': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'DISCHSTATUS': forms.Select(attrs={'class': 'form-control select2'}),
            'DISCHSTATUSDETAIL': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'TRANSFERREASON': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'TRANSFERLOCATION': forms.TextInput(attrs={'class': 'form-control'}),
            'DEATHCAUSE': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'COMPLETEDBY': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            field.required = False
        
        if self.instance and self.instance.pk:
            self.fields['TRANSFERHOSP'].initial = self.instance.TRANSFERHOSP or 'No'
            self.fields['DEATHATDISCH'].initial = self.instance.DEATHATDISCH or 'No'
        else:
            self.fields['TRANSFERHOSP'].initial = 'No'
            self.fields['DEATHATDISCH'].initial = 'No'
            self.fields['EVENT'].initial = 'DISCHARGE'
            self.fields['STUDYID'].initial = '43EN'
            self.fields['COMPLETEDDATE'].initial = date.today()
    
    def clean(self):
        cleaned_data = super().clean()
        
        transferred = cleaned_data.get('TRANSFERHOSP')
        if transferred == 'Yes':
            if not cleaned_data.get('TRANSFERREASON'):
                self.add_error('TRANSFERREASON', 'Vui lòng nhập lý do chuyển viện')
            if not cleaned_data.get('TRANSFERLOCATION'):
                self.add_error('TRANSFERLOCATION', 'Vui lòng nhập nơi chuyển viện')
        
        died = cleaned_data.get('DEATHATDISCH')
        if died == 'Yes':
            if not cleaned_data.get('DEATHCAUSE'):
                self.add_error('DEATHCAUSE', 'Vui lòng nhập nguyên nhân tử vong')
        
        return cleaned_data


class DischargeICDForm(forms.ModelForm):
    """Form for DischargeICD"""
    
    class Meta:
        model = DischargeICD
        fields = ['id', 'ICD_SEQUENCE', 'ICDCODE', 'ICDDETAIL']
        widgets = {
            'ICD_SEQUENCE': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
            'ICDCODE': forms.TextInput(attrs={'class': 'form-control'}),
            'ICDDETAIL': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ICD_SEQUENCE'].required = False


class BaseDischargeICDFormSet(forms.BaseInlineFormSet):
    """Base formset for DischargeICD"""
    
    def add_fields(self, form, index):
        super().add_fields(form, index)
        if not form.instance.pk:
            form.instance.ICD_SEQUENCE = index + 1


DischargeICDFormSet = forms.inlineformset_factory(
    DischargeCase,
    DischargeICD,
    form=DischargeICDForm,
    formset=BaseDischargeICDFormSet,
    extra=1,
    can_delete=True
)


# ==========================================
# FOLLOW-UP FORMS  
# ==========================================

class FollowUpCaseForm(forms.ModelForm):
    """Form for FollowUpCase model (Day 28)"""

    ASSESSED = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Bệnh nhân được đánh giá tình trạng tại ngày 28?')
    )
    REHOSP = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Bệnh nhân tái nhập viện?')
    )
    DECEASED = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Bệnh nhân tử vong?')
    )
    USEDANTIBIO = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Bệnh nhân có sử dụng kháng sinh từ lần khám gần nhất?')
    )
    FUNCASSESS = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Đánh giá tình trạng chức năng tại ngày 28?')
    )

    class Meta:
        model = FollowUpCase
        fields = [
            'ASSESSED', 'ASSESSDATE', 'PATSTATUS',
            'REHOSP', 'REHOSPCOUNT',
            'DECEASED', 'DEATHDATE', 'DEATHCAUSE',
            'USEDANTIBIO', 'ANTIBIOCOUNT',
            'FUNCASSESS', 'MOBILITY', 'PERHYGIENE',
            'DAILYACTIV', 'PAINDISCOMF', 'ANXIETY_DEPRESSION',
            'FBSISCORE', 'COMPLETEDBY', 'COMPLETEDDATE'
        ]
        widgets = {
            'ASSESSDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'DEATHDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'PATSTATUS': forms.Select(attrs={'class': 'form-control select2'}),
            'FBSISCORE': forms.Select(attrs={'class': 'form-control select2'}),
            'DEATHCAUSE': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'MOBILITY': forms.RadioSelect(),
            'PERHYGIENE': forms.RadioSelect(),
            'DAILYACTIV': forms.RadioSelect(),
            'PAINDISCOMF': forms.RadioSelect(),
            'ANXIETY_DEPRESSION': forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            field.required = False

        if self.instance and self.instance.pk:
            for field_name in ['ASSESSED', 'REHOSP', 'DECEASED', 'USEDANTIBIO', 'FUNCASSESS']:
                self.fields[field_name].initial = getattr(self.instance, field_name) or 'No'
        else:
            for field_name in ['ASSESSED', 'REHOSP', 'DECEASED', 'USEDANTIBIO', 'FUNCASSESS']:
                self.fields[field_name].initial = 'No'


class RehospitalizationForm(forms.ModelForm):
    """Form for Rehospitalization"""
    
    class Meta:
        model = Rehospitalization
        fields = ['EPISODE', 'REHOSPDATE', 'REHOSPREASONFOR', 'REHOSPLOCATION', 'REHOSPSTAYDUR']
        widgets = {
            'EPISODE': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
            'REHOSPDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'REHOSPREASONFOR': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'REHOSPLOCATION': forms.TextInput(attrs={'class': 'form-control'}),
            'REHOSPSTAYDUR': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['EPISODE'].required = False


class FollowUpAntibioticForm(forms.ModelForm):
    """Form for FollowUpAntibiotic"""
    
    class Meta:
        model = FollowUpAntibiotic
        fields = ['EPISODE', 'ANTIBIONAME', 'ANTIBIOREASONFOR', 'ANTIBIODUR']
        widgets = {
            'EPISODE': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
            'ANTIBIONAME': forms.TextInput(attrs={'class': 'form-control'}),
            'ANTIBIOREASONFOR': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'ANTIBIODUR': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['EPISODE'].required = False


class BaseRehospitalizationFormSet(forms.BaseInlineFormSet):
    """Base formset for Rehospitalization"""
    
    def add_fields(self, form, index):
        super().add_fields(form, index)
        if not form.instance.pk:
            form.instance.EPISODE = index + 1


class BaseFollowUpAntibioticFormSet(forms.BaseInlineFormSet):
    """Base formset for FollowUpAntibiotic"""
    
    def add_fields(self, form, index):
        super().add_fields(form, index)
        if not form.instance.pk:
            form.instance.EPISODE = index + 1


RehospitalizationFormSet = forms.inlineformset_factory(
    FollowUpCase,
    Rehospitalization,
    form=RehospitalizationForm,
    formset=BaseRehospitalizationFormSet,
    extra=1,
    can_delete=True
)

FollowUpAntibioticFormSet = forms.inlineformset_factory(
    FollowUpCase,
    FollowUpAntibiotic,
    form=FollowUpAntibioticForm,
    formset=BaseFollowUpAntibioticFormSet,
    extra=1,
    can_delete=True
)


# Day 90 Forms (same structure as Day 28)
class FollowUpCase90Form(forms.ModelForm):
    """Form for FollowUpCase90 model (Day 90)"""

    ASSESSED = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Bệnh nhân được đánh giá tình trạng tại ngày 90?')
    )
    REHOSP = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Bệnh nhân tái nhập viện?')
    )
    DECEASED = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Bệnh nhân tử vong?')
    )
    USEDANTIBIO = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Bệnh nhân có sử dụng kháng sinh từ lần khám gần nhất?')
    )
    FUNCASSESS = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Đánh giá tình trạng chức năng tại ngày 90?')
    )

    class Meta:
        model = FollowUpCase90
        fields = [
            'ASSESSED', 'ASSESSDATE', 'PATSTATUS',
            'REHOSP', 'REHOSPCOUNT',
            'DECEASED', 'DEATHDATE', 'DEATHCAUSE',
            'USEDANTIBIO', 'ANTIBIOCOUNT',
            'FUNCASSESS', 'MOBILITY', 'PERHYGIENE',
            'DAILYACTIV', 'PAINDISCOMF', 'ANXIETY_DEPRESSION',
            'FBSISCORE', 'COMPLETEDBY', 'COMPLETEDDATE'
        ]
        widgets = {
            'ASSESSDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'DEATHDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'PATSTATUS': forms.Select(attrs={'class': 'form-control select2'}),
            'FBSISCORE': forms.Select(attrs={'class': 'form-control select2'}),
            'DEATHCAUSE': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'MOBILITY': forms.RadioSelect(),
            'PERHYGIENE': forms.RadioSelect(),
            'DAILYACTIV': forms.RadioSelect(),
            'PAINDISCOMF': forms.RadioSelect(),
            'ANXIETY_DEPRESSION': forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            field.required = False

        if self.instance and self.instance.pk:
            for field_name in ['ASSESSED', 'REHOSP', 'DECEASED', 'USEDANTIBIO', 'FUNCASSESS']:
                self.fields[field_name].initial = getattr(self.instance, field_name) or 'No'
        else:
            for field_name in ['ASSESSED', 'REHOSP', 'DECEASED', 'USEDANTIBIO', 'FUNCASSESS']:
                self.fields[field_name].initial = 'No'


class Rehospitalization90Form(forms.ModelForm):
    """Form for Rehospitalization90"""
    
    class Meta:
        model = Rehospitalization90
        fields = ['EPISODE', 'REHOSPDATE', 'REHOSPREASONFOR', 'REHOSPLOCATION', 'REHOSPSTAYDUR']
        widgets = {
            'EPISODE': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
            'REHOSPDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'REHOSPREASONFOR': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'REHOSPLOCATION': forms.TextInput(attrs={'class': 'form-control'}),
            'REHOSPSTAYDUR': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['EPISODE'].required = False


class FollowUpAntibiotic90Form(forms.ModelForm):
    """Form for FollowUpAntibiotic90"""
    
    class Meta:
        model = FollowUpAntibiotic90
        fields = ['EPISODE', 'ANTIBIONAME', 'ANTIBIOREASONFOR', 'ANTIBIODUR']
        widgets = {
            'EPISODE': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
            'ANTIBIONAME': forms.TextInput(attrs={'class': 'form-control'}),
            'ANTIBIOREASONFOR': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'ANTIBIODUR': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['EPISODE'].required = False


Rehospitalization90FormSet = forms.inlineformset_factory(
    FollowUpCase90,
    Rehospitalization90,
    form=Rehospitalization90Form,
    formset=BaseRehospitalizationFormSet,
    extra=1,
    can_delete=True
)

FollowUpAntibiotic90FormSet = forms.inlineformset_factory(
    FollowUpCase90,
    FollowUpAntibiotic90,
    form=FollowUpAntibiotic90Form,
    formset=BaseFollowUpAntibioticFormSet,
    extra=1,
    can_delete=True
)


# ==========================================
# SAMPLE COLLECTION FORMS
# ==========================================

class SampleCollectionForm(forms.ModelForm):
    """Form for SampleCollection model"""
    
    class Meta:
        model = SampleCollection
        exclude = ('USUBJID',)
        widgets = {
            'SAMPLE_TYPE': forms.RadioSelect(),
            'SAMPLE': forms.RadioSelect(choices=((True, _('Có')), (False, _('Không')))),
            'REASONIFNO': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'STOOLDATE': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'THROATSWABDATE': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'RECTSWABDATE': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'BLOODDATE': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'CULTRES_1': forms.RadioSelect(),
            'CULTRES_2': forms.RadioSelect(),
            'CULTRES_3': forms.RadioSelect(),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'form-control datepicker'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for field_name in [
            'STOOL', 'THROATSWAB', 'RECTSWAB', 'BLOOD',
            'KLEBPNEU_1', 'OTHERRES_1', 'KLEBPNEU_2', 'OTHERRES_2', 'KLEBPNEU_3', 'OTHERRES_3'
        ]:
            if field_name in self.fields:
                self.fields[field_name].widget = forms.CheckboxInput(attrs={'class': 'form-check-input'})


# ==========================================
# ENDCASE FORMS
# ==========================================

class EndCaseCRFForm(forms.ModelForm):
    """Form for EndCaseCRF model"""
    
    class Meta:
        model = EndCaseCRF
        fields = [
            'ENDDATE', 'ENDFORMDATE',
            'VICOMPLETED', 'V2COMPLETED', 'V3COMPLETED', 'V4COMPLETED',
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
            'V4COMPLETED': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'WITHDRAWREASON': forms.RadioSelect(),
            'INCOMPLETE': forms.RadioSelect(),
            'INCOMPLETEDEATH': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'INCOMPLETEMOVED': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'INCOMPLETEOTHER': forms.TextInput(attrs={'class': 'form-control'}),
            'LOSTTOFOLLOWUP': forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['INCOMPLETEDEATH'].required = False
        self.fields['INCOMPLETEMOVED'].required = False
        self.fields['INCOMPLETEOTHER'].required = False

        if not self.instance.pk:
            self.fields['WITHDRAWREASON'].initial = 'na'
            self.fields['INCOMPLETE'].initial = 'na'
            self.fields['LOSTTOFOLLOWUP'].initial = 'na'

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('INCOMPLETE') == 'yes':
            if not (
                cleaned_data.get('INCOMPLETEDEATH') or
                cleaned_data.get('INCOMPLETEMOVED') or
                cleaned_data.get('INCOMPLETEOTHER')
            ):
                raise forms.ValidationError(_("Vui lòng chọn ít nhất một lý do không hoàn tất nghiên cứu."))
        return cleaned_data