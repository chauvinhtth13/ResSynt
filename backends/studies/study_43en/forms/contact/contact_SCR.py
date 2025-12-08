# backends/studies/study_43en/forms/contact/SCR_CONTACT.py

from django import forms
from django.utils.translation import gettext_lazy as _
from backends.studies.study_43en.models.contact import SCR_CONTACT
from backends.studies.study_43en.models.patient import SCR_CASE


# ==========================================
# COMMON CHOICES
# ==========================================

SITEID_CHOICES = [
    ('003', '003'),
    ('011', '011'),
    ('020', '020'),
]


# ==========================================
# CONTACT SCREENING FORM
# ==========================================

class ScreeningContactForm(forms.ModelForm):
    """
    Contact screening form - similar to patient but with 3 criteria
    
    Differences from Patient:
    - 3 eligibility criteria instead of 5
    - Related to a patient (SUBJIDENROLLSTUDY)
    - USUBJID format: SITE-B-XXX-Y (e.g., 003-B-001-1)
    
     NEW: SITEID and STUDYID are locked (readonly)
    """
    
    # ⚠️ SITEID field - will be configured in __init__
    SITEID = forms.ChoiceField(
        choices=SITEID_CHOICES,
        label=_("Mã cơ sở"),
        required=True
    )
    
    # Radio buttons for 3 boolean fields
    LIVEIN5DAYS3MTHS = forms.ChoiceField(
        choices=[('0', 'Không'), ('1', 'Có')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Sống chung ≥5 ngày trong 3 tháng qua')
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
        label=_('Đồng ý tham gia')
    )
    
    SCREENINGFORMDATE = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control datepicker'}),
        label=_('Ngày Screening')
    )
    
    # Optimistic locking
    version = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
        initial=0
    )
    
    class Meta:
        model = SCR_CONTACT
        fields = [
            'STUDYID', 'SITEID', 'INITIAL', 'SUBJIDENROLLSTUDY',
            'LIVEIN5DAYS3MTHS', 'MEALCAREONCEDAY', 'CONSENTTOSTUDY',
            'SCREENINGFORMDATE', 'UNRECRUITED_REASON'
        ]
        widgets = {
            'STUDYID': forms.TextInput(attrs={
                'readonly': 'readonly',  # ⚠️ Only readonly, NOT disabled
                'class': 'form-control',
                'style': 'background-color: #e9ecef;'
            }),
            'INITIAL': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 10}),
            'SUBJIDENROLLSTUDY': forms.Select(attrs={'class': 'form-control select2'}),
            'UNRECRUITED_REASON': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # ⚠️ FIX: STUDYID is readonly but must be included in POST
        self.fields['STUDYID'].widget.attrs.update({
            'readonly': 'readonly',
            'style': 'background-color: #e9ecef;'
        })
        self.fields['STUDYID'].required = True
        
        # ⚠️ FIX: SITEID is readonly but must be included in POST
        # Lock SITEID field (cannot be changed after creation)
        if self.instance.SITEID:
            self.fields['SITEID'].widget.attrs.update({
                'readonly': 'readonly',
                'style': 'background-color: #e9ecef;'
            })
            self.fields['SITEID'].disabled = True  # For display only
            self.fields['SITEID'].initial = self.instance.SITEID
        
        # Set version for optimistic locking
        if self.instance and self.instance.pk:
            self.fields['version'].initial = self.instance.version
        
        #  ALWAYS show SCRID (both CREATE and UPDATE)
        if self.instance.SCRID:
            self.fields['SCRID'] = forms.CharField(
                required=False,
                disabled=True,
                label=_("Contact Screening ID"),
                initial=self.instance.SCRID,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'readonly': True,
                    'style': 'background-color: #e9ecef;'
                })
            )
        
        # Show readonly SUBJID if exists
        if self.instance.pk and self.instance.SUBJID:
            self.fields['SUBJID'] = forms.CharField(
                required=False,
                disabled=True,
                label=_("Mã contact"),
                initial=self.instance.SUBJID,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'readonly': True,
                    'style': 'background-color: #e9ecef;'
                })
            )
        
        # Show readonly USUBJID if exists
        if self.instance.pk and self.instance.USUBJID:
            self.fields['USUBJID'] = forms.CharField(
                required=False,
                disabled=True,
                label=_("Mã contact duy nhất"),
                initial=self.instance.USUBJID,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'readonly': True,
                    'style': 'background-color: #e9ecef;'
                })
            )
        
        # Apply form-control class
        for field_name, field in self.fields.items():
            if not hasattr(field.widget, 'input_type') or field.widget.input_type != 'radio':
                existing_class = field.widget.attrs.get('class', '')
                if 'form-control' not in existing_class:
                    field.widget.attrs['class'] = f"{existing_class} form-control".strip()
        
        # Set default values for new forms
        if not self.instance.pk:
            boolean_fields = ['LIVEIN5DAYS3MTHS', 'MEALCAREONCEDAY', 'CONSENTTOSTUDY']
            for field_name in boolean_fields:
                self.fields[field_name].initial = '0'
        else:
            # Convert boolean to string for existing records
            self.fields['LIVEIN5DAYS3MTHS'].initial = '1' if self.instance.LIVEIN5DAYS3MTHS else '0'
            self.fields['MEALCAREONCEDAY'].initial = '1' if self.instance.MEALCAREONCEDAY else '0'
            self.fields['CONSENTTOSTUDY'].initial = '1' if self.instance.CONSENTTOSTUDY else '0'
        
        #  Filter available patients by SITEID (only enrolled patients from same site)
        available_patients = SCR_CASE.objects.filter(
            SUBJID__startswith='A-',
            is_confirmed=True
        )
        
        # Filter by SITEID if set
        if self.instance.SITEID:
            available_patients = available_patients.filter(SITEID=self.instance.SITEID)
        
        available_patients = available_patients.order_by('SITEID', 'INITIAL', 'USUBJID')
        
        self.fields['SUBJIDENROLLSTUDY'].queryset = available_patients
        self.fields['SUBJIDENROLLSTUDY'].label_from_instance = lambda obj: f"{obj.INITIAL} ({obj.USUBJID})"
    
    def clean_SCREENINGFORMDATE(self):
        """Validate screening date"""
        from django.utils import timezone
        
        date_value = self.cleaned_data.get('SCREENINGFORMDATE')
        
        if date_value:
            # Cannot be in the future
            if date_value > timezone.now().date():
                raise forms.ValidationError("Ngày screening không được ở tương lai")
            
            # Cannot be too old (e.g., more than 2 years ago)
            two_years_ago = timezone.now().date().replace(year=timezone.now().year - 2)
            if date_value < two_years_ago:
                raise forms.ValidationError("Ngày screening quá cũ (>2 năm)")
        
        return date_value
    
    def clean(self):
        """Full validation with optimistic locking"""
        cleaned_data = super().clean()
        
        # ==========================================
        # 1. OPTIMISTIC LOCKING CHECK
        # ==========================================
        if self.instance.pk:
            submitted_version = cleaned_data.get('version')
            
            try:
                current_record = SCR_CONTACT.objects.get(pk=self.instance.pk)
                
                if submitted_version != current_record.version:
                    raise forms.ValidationError(
                        " Record đã bị thay đổi bởi user khác. "
                        "Vui lòng refresh trang và thử lại."
                    )
            except SCR_CONTACT.DoesNotExist:
                raise forms.ValidationError("Record không tồn tại")
        
        # ==========================================
        # 2. CONVERT BOOLEAN FIELDS
        # ==========================================
        boolean_fields = ['LIVEIN5DAYS3MTHS', 'MEALCAREONCEDAY', 'CONSENTTOSTUDY']
        for field_name in boolean_fields:
            value = cleaned_data.get(field_name)
            cleaned_data[field_name] = (value == '1')
        
        # ==========================================
        # 3. ELIGIBILITY VALIDATION (3 criteria)
        # ==========================================
        is_eligible = (
            cleaned_data.get('LIVEIN5DAYS3MTHS') and
            cleaned_data.get('MEALCAREONCEDAY') and
            cleaned_data.get('CONSENTTOSTUDY')
        )
        
        # ==========================================
        # 4. UNRECRUITED_REASON VALIDATION
        # ==========================================
        if not is_eligible:
            # Not recruited - reason is required
            if not cleaned_data.get('UNRECRUITED_REASON'):
                self.add_error(
                    'UNRECRUITED_REASON',
                    "Phải nhập lý do khi contact không được tuyển dụng"
                )
        
        return cleaned_data