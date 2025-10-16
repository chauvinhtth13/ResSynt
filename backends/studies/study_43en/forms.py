from django import forms
from django.utils.translation import gettext_lazy as _
from datetime import date, timezone


from .models.patient import (
    ScreeningCase, EnrollmentCase, DischargeCase, EndCaseCRF,FollowUpCase, FollowUpCase90,
    FollowUpAntibiotic, FollowUpAntibiotic90,ClinicalCase,SampleCollection,
    Rehospitalization, Rehospitalization90, OtherTest, MainAntibiotic,LAB_Microbiology,
    InitialAntibiotic, DischargeICD, PriorAntibiotic,AEHospEvent,LaboratoryTest,CLI_Microbiology,MedHisDrug,
    VasoIDrug,AntibioticSensitivity,HospiProcess,ImproveSympt

)


SITEID_CHOICES = [
    ('003', '003'),
    ('011', '011'),
    ('020', '020'),
]

class ScreeningCaseForm(forms.ModelForm):
    """
    Form for ScreeningCase model
    """

    SITEID = forms.ChoiceField(choices=SITEID_CHOICES, label="Mã cơ sở")

    # Override các BooleanField thành ChoiceField để xử lý chính xác
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
            'KPNISOUNTREATEDSTABLE', 'CONSENTTOSTUDY', 'SCREENINGFORMDATE','UNRECRUITED_REASON',
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
        
        # Đặt required cho các trường bắt buộc
        required_fields = ['STUDYID', 'SITEID', 'SUBJID', 'INITIAL', 
                        'UPPER16AGE', 'INFPRIOR2OR48HRSADMIT', 
                        'ISOLATEDKPNFROMINFECTIONORBLOOD', 
                        'KPNISOUNTREATEDSTABLE', 'CONSENTTOSTUDY']
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True
        
        # Đặt giá trị mặc định là '0' (Không) cho các trường boolean cho form mới
        if not self.instance.pk:  # Chỉ áp dụng cho form tạo mới
            # Đặt initial value cho các boolean fields
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
        
        # Mô tả rõ ràng hơn cho các trường
        self.fields['STUDYID'].label = _('Mã nghiên cứu')
        self.fields['SITEID'].label = _('Mã cơ sở')

        self.fields['INITIAL'].label = _('Chữ cái đầu')
        self.fields['SCREENINGFORMDATE'].label = _('Ngày sàng lọc')
        self.fields['COMPLETEDBY'].label = _('Người hoàn thành')
        self.fields['COMPLETEDDATE'].label = _('Ngày hoàn thành')
    
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

        # Áp dụng điều kiện mới cho CONSENTTOSTUDY
        if (
            cleaned_data.get('UPPER16AGE') and
            cleaned_data.get('INFPRIOR2OR48HRSADMIT') and
            cleaned_data.get('ISOLATEDKPNFROMINFECTIONORBLOOD') and
            not cleaned_data.get('KPNISOUNTREATEDSTABLE')
        ):
            # Cho phép CONSENTTOSTUDY là True hoặc False (theo người dùng chọn)
            pass
        else:
            # Nếu không đủ điều kiện, không cho chọn "Có" CONSENTTOSTUDY
            if cleaned_data.get('CONSENTTOSTUDY'):
                self.add_error(
                    'CONSENTTOSTUDY',
                    _("Chỉ được chọn 'Có' khi: Tuổi trên 16, Nhiễm khuẩn trước 2h hoặc sau 48h nhập viện, Phân lập KPN từ nhiễm khuẩn/máu đều là 'Có' và 'KPN chưa điều trị ổn định' là 'Không'")
                )
                cleaned_data['CONSENTTOSTUDY'] = False

        return cleaned_data

UNDERLYING_CHOICES = [
    ('HEARTFAILURE', 'Suy tim'),
    ('DIABETES', 'Đái tháo đường'),
    ('COPD', 'COPD'),
    ('HEPATITIS', 'Viêm gan'),
    ('CAD', 'Bệnh mạch vành'),
    ('KIDNEYDISEASE', 'Bệnh thận'),
    ('ASTHMA', 'Hen'),
    ('CIRRHOSIS', 'Xơ gan'),
    ('HYPERTENSION', 'Tăng huyết áp'),
    ('AUTOIMMUNE', 'Tự miễn'),
    ('CANCER', 'Ung thư'),
    ('ALCOHOLISM', 'Nghiện rượu'),
    ('HIV', 'HIV'),
    ('ADRENALINSUFFICIENCY', 'Suy thượng thận'),
    ('BEDRIDDEN', 'Nằm liệt giường'),
    ('PEPTICULCER', 'Loét dạ dày'),
    ('COLITIS_IBS', 'Viêm đại tràng/IBS'),
    ('SENILITY', 'Lão suy'),
    ('MALNUTRITION_WASTING', 'Suy dinh dưỡng'),
    ('OTHERDISEASE', 'Khác'),
]

class EnrollmentCaseForm(forms.ModelForm):
    # Khai báo từng trường bệnh nền là BooleanField
    HEARTFAILURE = forms.BooleanField(label=_("Suy tim"), required=False)
    DIABETES = forms.BooleanField(label=_("Đái tháo đường"), required=False)
    COPD = forms.BooleanField(label=_("COPD"), required=False)
    HEPATITIS = forms.BooleanField(label=_("Viêm gan"), required=False)
    CAD = forms.BooleanField(label=_("Bệnh mạch vành"), required=False)
    KIDNEYDISEASE = forms.BooleanField(label=_("Bệnh thận"), required=False)
    ASTHMA = forms.BooleanField(label=_("Hen"), required=False)
    CIRRHOSIS = forms.BooleanField(label=_("Xơ gan"), required=False)
    HYPERTENSION = forms.BooleanField(label=_("Tăng huyết áp"), required=False)
    AUTOIMMUNE = forms.BooleanField(label=_("Tự miễn"), required=False)
    CANCER = forms.BooleanField(label=_("Ung thư"), required=False)
    ALCOHOLISM = forms.BooleanField(label=_("Nghiện rượu"), required=False)
    HIV = forms.BooleanField(label=_("HIV"), required=False)
    ADRENALINSUFFICIENCY = forms.BooleanField(label=_("Suy thượng thận"), required=False)
    BEDRIDDEN = forms.BooleanField(label=_("Nằm liệt giường"), required=False)
    PEPTICULCER = forms.BooleanField(label=_("Loét dạ dày"), required=False)
    COLITIS_IBS = forms.BooleanField(label=_("Viêm đại tràng/IBS"), required=False)
    SENILITY = forms.BooleanField(label=_("Lão suy"), required=False)
    MALNUTRITION_WASTING = forms.BooleanField(label=_("Suy dinh dưỡng"), required=False)
    OTHERDISEASE = forms.BooleanField(label=_("Khác"), required=False)
    OTHERDISEASESPECIFY = forms.CharField(label=_("Chi tiết bệnh khác"), required=False)


    class Meta:
        model = EnrollmentCase
        exclude = ['USUBJID']
        widgets = {
            'SEX': forms.Select(choices=[
                ('Male', _('Nam')),
                ('Female', _('Nữ')),
                ('Other', _('Khác'))
            ]),
            'FULLNAME': forms.TextInput(attrs={'class': 'form-control'}),
            'ADDRESS': forms.TextInput(attrs={'class': 'form-control'}),
            'PHONE': forms.TextInput(attrs={'class': 'form-control'}),
        }



    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)
        # Chỉ set initial cho các trường bệnh nền nếu có instance và LISTUNDERLYING
        if instance and hasattr(instance, 'LISTUNDERLYING') and instance.LISTUNDERLYING:
            underlying = instance.LISTUNDERLYING
            if isinstance(underlying, str):
                underlying = [x.strip() for x in underlying.split(',') if x.strip()]
            for cond in [
                'HEARTFAILURE', 'DIABETES', 'COPD', 'HEPATITIS', 'CAD', 'KIDNEYDISEASE',
                'ASTHMA', 'CIRRHOSIS', 'HYPERTENSION', 'AUTOIMMUNE', 'CANCER', 'ALCOHOLISM',
                'HIV', 'ADRENALINSUFFICIENCY', 'BEDRIDDEN', 'PEPTICULCER', 'COLITIS_IBS',
                'SENILITY', 'MALNUTRITION_WASTING', 'OTHERDISEASE'
            ]:
                if cond in self.fields:
                    self.fields[cond].initial = cond in underlying
                    # Thêm class cho checkbox để đẹp hơn
                    self.fields[cond].widget.attrs.update({'class': 'form-check-input'})
        # Thêm class cho các trường nhập liệu (trừ checkbox/radio)
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)):
                field.widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Mapping các trường bệnh nền vào LISTUNDERLYING
        conditions = []
        for field in [
            'HEARTFAILURE', 'DIABETES', 'COPD', 'HEPATITIS', 'CAD', 'KIDNEYDISEASE',
            'ASTHMA', 'CIRRHOSIS', 'HYPERTENSION', 'AUTOIMMUNE', 'CANCER', 'ALCOHOLISM',
            'HIV', 'ADRENALINSUFFICIENCY', 'BEDRIDDEN', 'PEPTICULCER', 'COLITIS_IBS',
            'SENILITY', 'MALNUTRITION_WASTING', 'OTHERDISEASE'
        ]:
            if self.cleaned_data.get(field):
                conditions.append(field)
        instance.LISTUNDERLYING = conditions
        instance.OTHERDISEASESPECIFY = self.cleaned_data.get('OTHERDISEASESPECIFY', '')
        if commit:
            instance.save()
        return instance
    

class MedHisDrugForm(forms.ModelForm):
    class Meta:
        model = MedHisDrug
        fields = [
            'SEQUENCE',
            'DRUGNAME',
            'DOSAGE',
            'USAGETIME',
            'USAGEREASON',
        ]
        widgets = {
            'DRUGNAME': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên thuốc'}),
            'DOSAGE': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Liều dùng'}),
            'USAGETIME': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Thời gian dùng'}),
            'USAGEREASON': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Lý do dùng', 'rows': 2}),
        }

MedHisDrugFormSet = forms.inlineformset_factory(
    EnrollmentCase,
    MedHisDrug,
    form=MedHisDrugForm,
    extra=1,
    can_delete=True
)

class ClinicalCaseForm(forms.ModelForm):
    """Form cho ClinicalCase model với xử lý đặc biệt cho các triệu chứng"""

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

    class Meta:
        model = ClinicalCase
        fields = '__all__'
        widgets = {
            'ADMISDATE': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'autocomplete': 'off',
                'placeholder': 'YYYY-MM-DD'
            }),
            'SYMPTOMONSETDATE': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'autocomplete': 'off',
                'placeholder': 'YYYY-MM-DD'
            }),
            'COMPLETEDDATE': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'autocomplete': 'off',
                'placeholder': 'YYYY-MM-DD'
            }),
            'INFECTFOCUS48H': forms.Select(attrs={'class': 'form-control select2'}),
            'INFECTSRC': forms.Select(attrs={'class': 'form-control select2'}),
            'FLUID6HOURS': forms.Select(attrs={'class': 'form-control select2'}),
            'FLUID24HOURS': forms.Select(attrs={'class': 'form-control select2'}),
            'DRAINAGETYPE': forms.Select(attrs={'class': 'form-control select2'})
        }
    
    # Định nghĩa các trường checkbox cho triệu chứng nhóm 1
    FEVER = forms.BooleanField(label=_("Sốt"), required=False)
    FATIGUE = forms.BooleanField(label=_("Mệt mỏi"), required=False)
    MUSCLEPAIN = forms.BooleanField(label=_("Đau cơ"), required=False)
    LOSSAPPETITE = forms.BooleanField(label=_("Chán ăn"), required=False)
    COUGH = forms.BooleanField(label=_("Ho"), required=False)
    CHESTPAIN = forms.BooleanField(label=_("Đau ngực"), required=False)
    SHORTBREATH = forms.BooleanField(label=_("Khó thở"), required=False)
    JAUNDICE = forms.BooleanField(label=_("Vàng da"), required=False)
    PAINURINATION = forms.BooleanField(label=_("Đau khi đi tiểu"), required=False)
    BLOODYURINE = forms.BooleanField(label=_("Tiểu máu"), required=False)
    CLOUDYURINE = forms.BooleanField(label=_("Tiểu đục"), required=False)
    EPIGASTRICPAIN = forms.BooleanField(label=_("Đau thượng vị"), required=False)
    LOWERABDPAIN = forms.BooleanField(label=_("Đau bụng dưới"), required=False)
    FLANKPAIN = forms.BooleanField(label=_("Đau hông lưng"), required=False)
    URINARYHESITANCY = forms.BooleanField(label=_("Tiểu khó"), required=False)
    SUBCOSTALPAIN = forms.BooleanField(label=_("Đau dưới sườn"), required=False)
    HEADACHE = forms.BooleanField(label=_("Đau đầu"), required=False)
    POORCONTACT = forms.BooleanField(label=_("Tiếp xúc kém"), required=False)
    DELIRIUMAGITATION = forms.BooleanField(label=_("Kích động/mê sảng"), required=False)
    VOMITING = forms.BooleanField(label=_("Nôn"), required=False)
    SEIZURES = forms.BooleanField(label=_("Co giật"), required=False)
    EYEPAIN = forms.BooleanField(label=_("Đau mắt"), required=False)
    REDEYES = forms.BooleanField(label=_("Mắt đỏ"), required=False)
    NAUSEA = forms.BooleanField(label=_("Buồn nôn"), required=False)
    BLURREDVISION = forms.BooleanField(label=_("Mờ mắt"), required=False)
    SKINLESIONS = forms.BooleanField(label=_("Tổn thương da"), required=False)
    
    # Định nghĩa các trường checkbox cho triệu chứng nhóm 2
    FEVER_2 = forms.BooleanField(label=_("Sốt"), required=False)
    RASH = forms.BooleanField(label=_("Phát ban"), required=False)
    SKINBLEEDING = forms.BooleanField(label=_("Xuất huyết da"), required=False)
    MUCOSALBLEEDING = forms.BooleanField(label=_("Xuất huyết niêm mạc"), required=False)
    SKINLESIONS_2 = forms.BooleanField(label=_("Tổn thương da"), required=False)
    LUNGCRACKLES = forms.BooleanField(label=_("Ran ở phổi"), required=False)
    CONSOLIDATIONSYNDROME = forms.BooleanField(label=_("Hội chứng đông đặc"), required=False)
    PLEURALEFFUSION = forms.BooleanField(label=_("Tràn dịch màng phổi"), required=False)
    PNEUMOTHORAX = forms.BooleanField(label=_("Tràn khí màng phổi"), required=False)
    HEARTMURMUR = forms.BooleanField(label=_("Tiếng thổi tim"), required=False)
    ABNORHEARTSOUNDS = forms.BooleanField(label=_("Tiếng tim bất thường"), required=False)
    JUGULARVEINDISTENTION = forms.BooleanField(label=_("Giãn tĩnh mạch cổ"), required=False)
    LIVERFAILURESIGNS = forms.BooleanField(label=_("Dấu hiệu suy gan"), required=False)
    PORTALHYPERTENSIONSIGNS = forms.BooleanField(label=_("Dấu hiệu tăng áp tĩnh mạch cửa"), required=False)
    HEPATOSPLENOMEGALY = forms.BooleanField(label=_("Gan lách to"), required=False)
    CONSCIOUSNESSDISTURBANCE = forms.BooleanField(label=_("Rối loạn ý thức"), required=False)
    LIMBWEAKNESSPARALYSIS = forms.BooleanField(label=_("Yếu/liệt chi"), required=False)
    CRANIALNERVEPARALYSIS = forms.BooleanField(label=_("Liệt dây thần kinh sọ"), required=False)
    MENINGEALSIGNS = forms.BooleanField(label=_("Dấu hiệu màng não"), required=False)
    REDEYES_2 = forms.BooleanField(label=_("Mắt đỏ"), required=False)
    HYPOPYON = forms.BooleanField(label=_("Mủ tiền phòng"), required=False)
    EDEMA = forms.BooleanField(label=_("Phù"), required=False)
    CUSHINGOIDAPPEARANCE = forms.BooleanField(label=_("Hình dạng Cushing"), required=False)
    EPIGASTRICPAIN_2 = forms.BooleanField(label=_("Đau thượng vị"), required=False)
    LOWERABDPAIN_2 = forms.BooleanField(label=_("Đau bụng dưới"), required=False)
    FLANKPAIN_2 = forms.BooleanField(label=_("Đau hông lưng"), required=False)
    SUBCOSTALPAIN_2 = forms.BooleanField(label=_("Đau dưới sườn"), required=False)
    
    # Định nghĩa các trường bổ sung mới

    THREE_STATE_CHOICES = [
        ('yes', 'Có'),
        ('no', 'Không'),
        ('unknown', 'Không biết'),
    ]

    BLOODINFECT = forms.ChoiceField(
        choices=THREE_STATE_CHOICES,
        widget=forms.HiddenInput,
        label=_("Nhiễm khuẩn huyết"),
        required=False
    )
    SEPTICSHOCK = forms.ChoiceField(
        choices=THREE_STATE_CHOICES,
        widget=forms.HiddenInput,
        label=_("Sốc nhiễm khuẩn"),
        required=False
    )

    RESPISUPPORT = forms.BooleanField(
        required=False,
        label=_("Hỗ trợ hô hấp")
    )

    RESUSFLUID = forms.BooleanField(
        widget=forms.CheckboxInput(),
        label=_("Dịch truyền hồi sức"),
        required=False
    )

    VASOINOTROPES = forms.BooleanField(
        label=_("Sử dụng thuốc vận mạch"),
        required=False,
        widget=forms.CheckboxInput()
    )

    SPECIFYOTHERDRAINAGE = forms.CharField(
        label=_("Chi tiết dẫn lưu khác"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    DIALYSIS = forms.BooleanField(label=_("Lọc máu"), required=False)
    DRAINAGE = forms.BooleanField(label=_("Dẫn lưu"), required=False)
    PRIORANTIBIOTIC = forms.BooleanField(label=_("Kháng sinh trước"), required=False)
    INITIALANTIBIOTIC = forms.BooleanField(label=_("Kháng sinh ban đầu"), required=False)
    INITIALABXAPPROP = forms.BooleanField(label=_("Kháng sinh ban đầu phù hợp"), required=False)
    
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field, forms.BooleanField):
                field.widget.attrs.update({'class': 'form-control'})
        if instance:
            # Nhóm 1
            for symptom in instance.LISTBASICSYMTOMS or []:
                if symptom in self.fields:
                    self.fields[symptom].initial = True
            # Nhóm 2
            for symptom in instance.LISTCLINISYMTOMS or []:
                if symptom in self.fields:
                    self.fields[symptom].initial = True
            # SUPPORTTYPE
            if instance.SUPPORTTYPE:
                self.fields['SUPPORTTYPE'].initial = instance.SUPPORTTYPE



    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.SUPPORTTYPE = self.cleaned_data.get('SUPPORTTYPE', [])
        LISTBASICSYMTOMS  = []
        LISTCLINISYMTOMS = []
        for field_name in [
            'FEVER', 'FATIGUE', 'MUSCLEPAIN', 'LOSSAPPETITE', 'COUGH', 'CHESTPAIN',
            'SHORTBREATH', 'JAUNDICE', 'PAINURINATION', 'BLOODYURINE', 'CLOUDYURINE',
            'EPIGASTRICPAIN', 'LOWERABDPAIN', 'FLANKPAIN', 'URINARYHESITANCY',
            'SUBCOSTALPAIN', 'HEADACHE', 'POORCONTACT', 'DELIRIUMAGITATION', 'VOMITING',
            'SEIZURES', 'EYEPAIN', 'REDEYES', 'NAUSEA', 'BLURREDVISION', 'SKINLESIONS'
        ]:
            if self.cleaned_data.get(field_name, False):
                LISTBASICSYMTOMS .append(field_name)
        for field_name in [
            'FEVER_2', 'RASH', 'SKINBLEEDING', 'MUCOSALBLEEDING', 'SKINLESIONS_2',
            'LUNGCRACKLES', 'CONSOLIDATIONSYNDROME', 'PLEURALEFFUSION', 'PNEUMOTHORAX',
            'HEARTMURMUR', 'ABNORHEARTSOUNDS', 'JUGULARVEINDISTENTION', 'LIVERFAILURESIGNS',
            'PORTALHYPERTENSIONSIGNS', 'HEPATOSPLENOMEGALY', 'CONSCIOUSNESSDISTURBANCE',
            'LIMBWEAKNESSPARALYSIS', 'CRANIALNERVEPARALYSIS', 'MENINGEALSIGNS', 'REDEYES_2',
            'HYPOPYON', 'EDEMA', 'CUSHINGOIDAPPEARANCE', 'EPIGASTRICPAIN_2', 'LOWERABDPAIN_2',
            'FLANKPAIN_2', 'SUBCOSTALPAIN_2'
        ]:
            if self.cleaned_data.get(field_name, False):
                LISTCLINISYMTOMS.append(field_name)
        instance.LISTBASICSYMTOMS = LISTBASICSYMTOMS 
        instance.LISTCLINISYMTOMS = LISTCLINISYMTOMS
        if commit:
            instance.save()
        return instance



class LaboratoryTestForm(forms.ModelForm):
    class Meta:
        model = LaboratoryTest
        fields = ['LAB_TYPE', 'CATEGORY', 'TESTTYPE', 'PERFORMED', 'PERFORMEDDATE', 'RESULT']
        widgets = {
            'LAB_TYPE': forms.Select(attrs={'class': 'form-control'}),
            'PERFORMEDDATE': forms.DateInput(attrs={
                'class': 'form-control datepicker',
                'autocomplete': 'off'
            }),
            'RESULT': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Nhập kết quả...'
            }),
            'CATEGORY': forms.Select(attrs={'class': 'form-control'}),
            'TESTTYPE': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['PERFORMED'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['TESTTYPE'].widget.attrs.update({'data-category-dependent': 'true'})
        
        # Nếu giá trị TESTTYPE hiện tại không có trong choices, thêm vào để tránh lỗi khi render
        testtype_field = self.fields['TESTTYPE']
        current_value = self.initial.get('TESTTYPE') or self.instance.TESTTYPE
        if current_value and current_value not in dict(testtype_field.choices):
            testtype_field.choices = [(current_value, f"{current_value} (Không xác định)")] + list(testtype_field.choices)

            
LaboratoryTestFormSet = forms.modelformset_factory(
    LaboratoryTest,
    form=LaboratoryTestForm,
    extra=0,
    can_delete=False
)


class OtherTestForm(forms.ModelForm):
    class Meta:
        model = OtherTest
        fields = [
            'SEQUENCE', 'LAB_TYPE', 'CATEGORY', 'OTHERTESTNAME',
            'OTHERTESTPERFORMED', 'OTHERTESTDTC', 'OTHERTESTRESULT'
        ]
        widgets = {
            'SEQUENCE': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
            'LAB_TYPE': forms.Select(attrs={'class': 'form-control'}),
            'CATEGORY': forms.Select(attrs={'class': 'form-control'}),
            'OTHERTESTNAME': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên xét nghiệm khác'}),
            'OTHERTESTPERFORMED': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'OTHERTESTDTC': forms.DateInput(attrs={'class': 'form-control datepicker', 'autocomplete': 'off'}),
            'OTHERTESTRESULT': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Nhập kết quả...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Nếu SEQUENCE chưa có, set readonly và tự động tăng
        self.fields['SEQUENCE'].required = False
        self.fields['OTHERTESTPERFORMED'].widget.attrs.update({'class': 'form-check-input'})
        # Nếu CATEGORY chỉ có 1 lựa chọn, có thể ẩn hoặc readonly
        if len(self.fields['CATEGORY'].choices) == 1:
            self.fields['CATEGORY'].widget.attrs['readonly'] = True

OtherTestFormSet = forms.modelformset_factory(
    OtherTest,
    form=OtherTestForm,
    extra=0,
    can_delete=False
)

class MicrobiologyCultureForm(forms.ModelForm):
    """Form nhập thông tin nuôi cấy vi sinh"""
    class Meta:
        model = CLI_Microbiology
        fields = [
            'USUBJID', 'SPECIMENTYPE', 'OTHERSPECIMEN', 'PERFORMEDDATE', 'SPECIMENID',
            'RESULT', 'RESULTDETAILS', 'ORDEREDBYDEPT', 'DEPTDIAGSENT',
            'BACSTRAINISOLDATE', 'COMPLETEDBY', 'COMPLETEDDATE'
        ]
        widgets = {
            'PERFORMEDDATE': forms.DateInput(attrs={'class': 'form-control datepicker', 'placeholder': 'nn/tt/nnnn'}),
            'SPECIMENID': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mã số bệnh phẩm'}),
            'RESULTDETAILS': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Chi tiết kết quả'}),
            'OTHERSPECIMEN': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Loại bệnh phẩm khác'}),
            'ORDEREDBYDEPT': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Khoa chỉ định'}),
            'DEPTDIAGSENT': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Chẩn đoán gửi khoa'}),
            'BACSTRAINISOLDATE': forms.DateInput(attrs={'class': 'form-control datepicker', 'placeholder': 'nn/tt/nnnn'}),
            'COMPLETEDBY': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Người hoàn thành'}),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'form-control datepicker', 'placeholder': 'nn/tt/nnnn'}),
        }

class LAB_MicrobiologyForm(forms.ModelForm):
    """
    Form cho LAB_Microbiology - Laboratory Culture for Antibiotic Sensitivity Testing
    """
    
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
            # Read-only fields
            'EVENT': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'STUDYIDS': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'SITEID': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'SUBJID': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'INITIAL': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'LAB_CASE_SEQ': forms.NumberInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            
            # Date fields
            'SPECSAMPDATE': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'autocomplete': 'off',
                'placeholder': 'YYYY-MM-DD'
            }),
            'BACSTRAINISOLDATE': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'autocomplete': 'off',
                'placeholder': 'YYYY-MM-DD'
            }),
            'COMPLETEDDATE': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'autocomplete': 'off',
                'placeholder': 'YYYY-MM-DD'
            }),
            
            # Select fields
            'SPECSAMPLOC': forms.Select(attrs={
                'class': 'form-control select2'
            }),
            
            # Text fields
            'SPECIMENID': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'OTHERSPECIMEN': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'ORDEREDBYDEPT': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'DEPTDIAGSENT': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'COMPLETEDBY': forms.TextInput(attrs={
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default values for new forms
        if not self.instance.pk:
            self.fields['EVENT'].initial = 'LAB_CULTURE'
            self.fields['STUDYIDS'].initial = '43EN'
            
            from datetime import date
            self.fields['COMPLETEDDATE'].initial = date.today()
        
        # OTHERSPECIMEN chỉ required khi SPECSAMPLOC = OTHER
        self.fields['OTHERSPECIMEN'].required = False
        
        # Set readonly fields
        readonly_fields = ['EVENT', 'STUDYIDS', 'SITEID', 'SUBJID', 'INITIAL', 'LAB_CASE_SEQ']
        for field_name in readonly_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['readonly'] = True
                self.fields[field_name].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate OTHERSPECIMEN when SPECSAMPLOC is OTHER
        specsamploc = cleaned_data.get('SPECSAMPLOC')
        otherspecimen = cleaned_data.get('OTHERSPECIMEN')
        
        if specsamploc == 'OTHER' and not otherspecimen:
            self.add_error('OTHERSPECIMEN', 
                          'Please specify other specimen type when selecting "Other"')
        
        # Validate dates
        specsampdate = cleaned_data.get('SPECSAMPDATE')
        bacstrainisoldate = cleaned_data.get('BACSTRAINISOLDATE')
        
        if specsampdate and bacstrainisoldate:
            if bacstrainisoldate < specsampdate:
                self.add_error('BACSTRAINISOLDATE',
                              'Bacterial isolation date cannot be before specimen sample date')
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Auto-populate fields from USUBJID if available
        if instance.USUBJID:
            enrollment = instance.USUBJID
            if not instance.SITEID:
                instance.SITEID = enrollment.SITEID
            if not instance.SUBJID:
                instance.SUBJID = enrollment.USUBJID.SUBJID
            if not instance.INITIAL:
                instance.INITIAL = enrollment.USUBJID.INITIAL
        
        if commit:
            instance.save()
        
        return instance


# FormSet để quản lý nhiều LAB_Microbiology records cho 1 bệnh nhân
LAB_MicrobiologyFormSet = forms.inlineformset_factory(
    EnrollmentCase,
    LAB_Microbiology,
    form=LAB_MicrobiologyForm,
    extra=1,
    can_delete=True,
    validate_min=False,
    validate_max=False
)


# FormSet read-only cho display
LAB_MicrobiologyFormSetReadOnly = forms.inlineformset_factory(
    EnrollmentCase,
    LAB_Microbiology,
    form=LAB_MicrobiologyForm,
    extra=0,
    can_delete=False
)


class AntibioticSensitivityForm(forms.ModelForm):
    """Form cho kết quả nhạy cảm kháng sinh"""
    
    class Meta:
        model = AntibioticSensitivity
        fields = [
            'TIER', 'ANTIBIOTIC_NAME', 'OTHER_ANTIBIOTIC_NAME', 
            'SENSITIVITY_LEVEL', 'IZDIAM', 'MIC', 'SEQUENCE'
        ]
        widgets = {
            'TIER': forms.Select(attrs={'class': 'form-control'}),
            'ANTIBIOTIC_NAME': forms.Select(attrs={'class': 'form-control'}),
            'OTHER_ANTIBIOTIC_NAME': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'SENSITIVITY_LEVEL': forms.Select(attrs={'class': 'form-control'}),
            'IZDIAM': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'mm'
            }),
            'MIC': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'μg/ml'
            }),
            'SEQUENCE': forms.NumberInput(attrs={
                'class': 'form-control',
                'readonly': True
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # OTHER_ANTIBIOTIC_NAME chỉ required khi chọn OTHER
        self.fields['OTHER_ANTIBIOTIC_NAME'].required = False
        self.fields['SEQUENCE'].required = False
        
        # Dynamic show/hide OTHER_ANTIBIOTIC_NAME
        self.fields['ANTIBIOTIC_NAME'].widget.attrs.update({
            'onchange': 'toggleOtherAntibioticName(this)'
        })
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate OTHER_ANTIBIOTIC_NAME when ANTIBIOTIC_NAME is OTHER
        antibiotic_name = cleaned_data.get('ANTIBIOTIC_NAME')
        other_name = cleaned_data.get('OTHER_ANTIBIOTIC_NAME')
        
        if antibiotic_name == 'OTHER' and not other_name:
            self.add_error('OTHER_ANTIBIOTIC_NAME',
                          'Please specify antibiotic name')
        
        return cleaned_data


# Updated FormSet with better configuration
AntibioticSensitivityFormSet = forms.inlineformset_factory(
    LAB_Microbiology,
    AntibioticSensitivity,
    form=AntibioticSensitivityForm,
    extra=3,  # Start with 3 antibiotics
    can_delete=True,
    validate_min=False,
    validate_max=False,
    fields=[
        'TIER', 'ANTIBIOTIC_NAME', 'OTHER_ANTIBIOTIC_NAME',
        'SENSITIVITY_LEVEL', 'IZDIAM', 'MIC', 'SEQUENCE'
    ]
)


# Read-only version
AntibioticSensitivityFormSetReadOnly = forms.inlineformset_factory(
    LAB_Microbiology,
    AntibioticSensitivity,
    form=AntibioticSensitivityForm,
    extra=0,
    can_delete=False
)

class PriorAntibioticForm(forms.ModelForm):
    """Form for prior antibiotics"""
    class Meta:
        model = PriorAntibiotic
        fields = ['PRIORANTIBIONAME', 'PRIORANTIBIODOSAGE', 'PRIORANTIBIOSTARTDTC', 'PRIORANTIBIOENDDTC']
        widgets = {
            'PRIORANTIBIOSTARTDTC': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'autocomplete': 'off',
                'placeholder': 'YYYY-MM-DD'
            }),
            'PRIORANTIBIOENDDTC': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'autocomplete': 'off',
                'placeholder': 'YYYY-MM-DD'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Áp dụng class form-control cho tất cả các trường
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class InitialAntibioticForm(forms.ModelForm):
    """Form for initial antibiotics"""
    class Meta:
        model = InitialAntibiotic
        fields = ['INITIALANTIBIONAME', 'INITIALANTIBIODOSAGE', 'INITIALANTIBIOSTARTDTC', 'INITIALANTIBIOENDDTC']
        widgets = {
            'INITIALANTIBIOSTARTDTC': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'autocomplete': 'off',
                'placeholder': 'YYYY-MM-DD'
            }),
            'INITIALANTIBIOENDDTC': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'autocomplete': 'off',
                'placeholder': 'YYYY-MM-DD'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Áp dụng class form-control cho tất cả các trường
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class MainAntibioticForm(forms.ModelForm):
    """Form for main antibiotics"""
    class Meta:
        model = MainAntibiotic
        fields = ['MAINANTIBIONAME', 'MAINANTIBIODOSAGE', 'MAINANTIBIOSTARTDTC', 'MAINANTIBIOENDDTC']
        widgets = {
            'MAINANTIBIOSTARTDTC': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'autocomplete': 'off',
                'placeholder': 'YYYY-MM-DD'
            }),
            'MAINANTIBIOENDDTC': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'autocomplete': 'off',
                'placeholder': 'YYYY-MM-DD'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Áp dụng class form-control cho tất cả các trường
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

# Formsets
PriorAntibioticFormSet = forms.inlineformset_factory(
    ClinicalCase,
    PriorAntibiotic,
    form= PriorAntibioticForm,
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
            'VASOIDRUGSTARTDTC': forms.DateInput(attrs={'class': 'datepicker'}),
            'VASOIDRUGENDDTC': forms.DateInput(attrs={'class': 'datepicker'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        
        # Mô tả rõ ràng hơn cho các trường
        self.fields['VASOIDRUGNAME'].label = _('Tên thuốc')
        self.fields['VASOIDRUGDOSAGE'].label = _('Liều dùng')
        self.fields['VASOIDRUGSTARTDTC'].label = _('Ngày bắt đầu')
        self.fields['VASOIDRUGENDDTC'].label = _('Ngày kết thúc')

VasoIDrugFormSet = forms.inlineformset_factory(
    ClinicalCase,
    VasoIDrug,
    form=VasoIDrugForm,
    extra=0,
    can_delete=True
)

class HospiProcessForm(forms.ModelForm):
    class Meta:
        model = HospiProcess
        fields = ['DEPTNAME', 'STARTDTC', 'ENDDTC', 'TRANSFER_REASON']
        widgets = {
            'DEPTNAME': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên khoa'}),
            'STARTDTC': forms.DateInput(attrs={'class': 'form-control datepicker', 'autocomplete': 'off', 'placeholder': 'YYYY-MM-DD'}),
            'ENDDTC': forms.DateInput(attrs={'class': 'form-control datepicker', 'autocomplete': 'off', 'placeholder': 'YYYY-MM-DD'}),
            'TRANSFER_REASON': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Lý do chuyển'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

HospiProcessFormSet = forms.inlineformset_factory(
    ClinicalCase,
    HospiProcess,
    form=HospiProcessForm,
    extra=0,  # hoặc số dòng trống mong muốn
    can_delete=True
)

class AEHospEventForm(forms.ModelForm):
    class Meta:
        model = AEHospEvent
        fields = ['AENAME', 'AEDETAILS', 'AEDTC']
        widgets = {
            'AENAME': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên biến cố'}),
            'AEDETAILS': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Chi tiết biến cố'}),
            'AEDTC': forms.DateInput(attrs={'class': 'form-control datepicker', 'autocomplete': 'off', 'placeholder': 'YYYY-MM-DD'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

AEHospEventFormSet = forms.inlineformset_factory(
    ClinicalCase,
    AEHospEvent,
    form=AEHospEventForm,
    extra=0,
    can_delete=True
)

class ImproveSymptForm(forms.ModelForm):
    class Meta:
        model = ImproveSympt
        fields = ['IMPROVE_SYMPTS', 'SYMPTS', 'IMPROVE_CONDITIONS', 'SYMPTSDTC']
        widgets = {
            'IMPROVE_SYMPTS': forms.Select(attrs={'class': 'form-control'}),
            'SYMPTS': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Triệu chứng'}),
            'IMPROVE_CONDITIONS': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Tình trạng cải thiện'}),
            'SYMPTSDTC': forms.DateInput(attrs={'class': 'form-control datepicker', 'autocomplete': 'off', 'placeholder': 'YYYY-MM-DD'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

ImproveSymptFormSet = forms.inlineformset_factory(
    ClinicalCase,
    ImproveSympt,
    form=ImproveSymptForm,
    extra=0,
    can_delete=True
)

class SampleCollectionForm(forms.ModelForm):
    class Meta:
        model = SampleCollection
        exclude = ('USUBJID',)  # hoặc liệt kê fields cụ thể
        widgets = {
            'SAMPLE_TYPE': forms.RadioSelect(),
            'SAMPLE': forms.RadioSelect(choices=((True, _('Có')), (False, _('Không')))),
            'REASONIFNO': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Vui lòng ghi rõ lý do không thu nhận được mẫu')}),
            'STOOLDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'THROATSWABDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'RECTSWABDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'BLOODDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'CULTRES_1': forms.RadioSelect(),
            'CULTRES_2': forms.RadioSelect(),
            'CULTRES_3': forms.RadioSelect(),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Thay đổi giao diện cho các trường boolean
        for field_name in [
            'STOOL', 'THROATSWAB', 'RECTSWAB', 'BLOOD',
            'KLEBPNEU_1', 'OTHERRES_1', 'KLEBPNEU_2', 'OTHERRES_2', 'KLEBPNEU_3', 'OTHERRES_3'
        ]:
            if field_name in self.fields:
                self.fields[field_name].widget = forms.CheckboxInput(attrs={'class': 'form-check-input'})
                
        # Đặt giá trị mặc định cho COMPLETEDDATE là ngày hiện tại nếu chưa có
        if not self.initial.get('COMPLETEDDATE'):
            self.initial['COMPLETEDDATE'] = timezone.now().date()
    

class FollowUpCaseForm(forms.ModelForm):
    """Form cho FollowUpCase model, tên trường trùng hoàn toàn với model"""

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
    MOBILITY = forms.ChoiceField(
        choices=[('Normal', 'Bình thường'), ('Problem', 'Có vấn đề'), ('Bedridden', 'Nằm một chỗ')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5a. Vận động (đi lại)')
    )
    PERHYGIENE = forms.ChoiceField(
        choices=[('Normal', 'Bình thường'), ('Problem', 'Có vấn đề'), ('Bedridden', 'Nằm một chỗ')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5b. Vệ sinh cá nhân (tự tắm rửa, thay quần áo)')
    )
    DAILYACTIV = forms.ChoiceField(
        choices=[('Normal', 'Bình thường'), ('Problem', 'Có vấn đề'), ('Bedridden', 'Nằm một chỗ')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5c. Sinh hoạt hằng ngày (làm việc, học tập, việc nhà, hoạt động vui chơi)')
    )
    PAINDISCOMF = forms.ChoiceField(
        choices=[('Normal', 'Bình thường'), ('Problem', 'Có vấn đề'), ('Bedridden', 'Nằm một chỗ')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5d. Đau/ khó chịu')
    )
    ANXIETY_DEPRESSION = forms.ChoiceField(
        choices=[('None', 'Không'), ('Moderate', 'Trung bình'), ('Severe', 'Nhiều')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5e. Lo lắng/ Trầm cảm')
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
            'REHOSPCOUNT': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'ANTIBIOCOUNT': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'COMPLETEDBY': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set required=False cho tất cả để tránh validation error
        for field_name, field in self.fields.items():
            field.required = False

        # Set initial cho các trường radio
        if self.instance and self.instance.pk:
            for field_name in ['ASSESSED', 'REHOSP', 'DECEASED', 'USEDANTIBIO', 'FUNCASSESS']:
                self.fields[field_name].initial = getattr(self.instance, field_name) or 'No'
            for field_name in ['MOBILITY', 'PERHYGIENE', 'DAILYACTIV', 'PAINDISCOMF']:
                self.fields[field_name].initial = getattr(self.instance, field_name) or 'Normal'
            self.fields['ANXIETY_DEPRESSION'].initial = getattr(self.instance, 'ANXIETY_DEPRESSION', 'None')
        else:
            for field_name in ['ASSESSED', 'REHOSP', 'DECEASED', 'USEDANTIBIO', 'FUNCASSESS']:
                self.fields[field_name].initial = 'No'
            for field_name in ['MOBILITY', 'PERHYGIENE', 'DAILYACTIV', 'PAINDISCOMF']:
                self.fields[field_name].initial = 'Normal'
            self.fields['ANXIETY_DEPRESSION'].initial = 'None'

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('ASSESSED') == 'Yes' and not cleaned_data.get('ASSESSDATE'):
            self.add_error('ASSESSDATE', 'Vui lòng nhập ngày đánh giá')
        if cleaned_data.get('DECEASED') == 'Yes':
            if not cleaned_data.get('DEATHDATE'):
                self.add_error('DEATHDATE', 'Vui lòng nhập ngày tử vong')
            if not cleaned_data.get('DEATHCAUSE'):
                self.add_error('DEATHCAUSE', 'Vui lòng nhập nguyên nhân tử vong')
        return cleaned_data


class RehospitalizationForm(forms.ModelForm):
    """Form cho thông tin tái nhập viện - theo style hiện tại"""
    
    class Meta:
        model = Rehospitalization
        fields = ['EPISODE', 'REHOSPDATE', 'REHOSPREASONFOR', 'REHOSPLOCATION', 'REHOSPSTAYDUR']
        
        widgets = {
            'REHOSPDATE': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'autocomplete': 'off',
                'placeholder': 'YYYY-MM-DD'
            }),
            'REHOSPREASONFOR': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Lý do tái nhập viện...'
            }),
            'REHOSPLOCATION': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nơi tái nhập viện...'
            }),
            'REHOSPSTAYDUR': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Thời gian nằm viện (ví dụ: 5 ngày)'
            }),
            'EPISODE': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'readonly': True
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Đảm bảo EPISODE không bắt buộc để tránh lỗi validation
        self.fields['EPISODE'].required = False
        
        # Labels chi tiết hơn
        self.fields['EPISODE'].label = _('Đợt')
        self.fields['REHOSPDATE'].label = _('Ngày tái nhập viện')
        self.fields['REHOSPREASONFOR'].label = _('Lý do tái nhập viện')
        self.fields['REHOSPLOCATION'].label = _('Nơi tái nhập viện')
        self.fields['REHOSPSTAYDUR'].label = _('Thời gian nằm viện')


class FollowUpAntibioticForm(forms.ModelForm):
    """Form cho thông tin kháng sinh - theo style hiện tại"""
    
    class Meta:
        model = FollowUpAntibiotic
        fields = ['EPISODE', 'ANTIBIONAME', 'ANTIBIOREASONFOR', 'ANTIBIODUR']
        
        widgets = {
            'ANTIBIONAME': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tên thuốc kháng sinh...'
            }),
            'ANTIBIOREASONFOR': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Lý do sử dụng...'
            }),
            'ANTIBIODUR': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Thời gian sử dụng (ví dụ: 7 ngày)'
            }),
            'EPISODE': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'readonly': True
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Đảm bảo EPISODE không bắt buộc để tránh lỗi validation
        self.fields['EPISODE'].required = False
        
        # Labels chi tiết hơn
        self.fields['EPISODE'].label = _('Đợt')
        self.fields['ANTIBIONAME'].label = _('Tên thuốc')
        self.fields['ANTIBIOREASONFOR'].label = _('Lý do sử dụng')
        self.fields['ANTIBIODUR'].label = _('Thời gian sử dụng')


class FollowUpCase90Form(forms.ModelForm):
    """Form cho FollowUpCase90 model, đồng bộ hoàn toàn với FollowUpCaseForm"""

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
    MOBILITY = forms.ChoiceField(
        choices=[('Normal', 'Bình thường'), ('Problem', 'Có vấn đề'), ('Bedridden', 'Nằm một chỗ')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5a. Vận động (đi lại)')
    )
    PERHYGIENE = forms.ChoiceField(
        choices=[('Normal', 'Bình thường'), ('Problem', 'Có vấn đề'), ('Bedridden', 'Nằm một chỗ')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5b. Vệ sinh cá nhân (tự tắm rửa, thay quần áo)')
    )
    DAILYACTIV = forms.ChoiceField(
        choices=[('Normal', 'Bình thường'), ('Problem', 'Có vấn đề'), ('Bedridden', 'Nằm một chỗ')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5c. Sinh hoạt hằng ngày (làm việc, học tập, việc nhà, hoạt động vui chơi)')
    )
    PAINDISCOMF = forms.ChoiceField(
        choices=[('Normal', 'Bình thường'), ('Problem', 'Có vấn đề'), ('Bedridden', 'Nằm một chỗ')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5d. Đau/ khó chịu')
    )
    ANXIETY_DEPRESSION = forms.ChoiceField(
        choices=[('None', 'Không'), ('Moderate', 'Trung bình'), ('Severe', 'Nhiều')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5e. Lo lắng/ Trầm cảm')
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
            'REHOSPCOUNT': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'ANTIBIOCOUNT': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'COMPLETEDBY': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set required=False cho tất cả để tránh validation error
        for field_name, field in self.fields.items():
            field.required = False

        # Set initial cho các trường radio
        if self.instance and self.instance.pk:
            for field_name in ['ASSESSED', 'REHOSP', 'DECEASED', 'USEDANTIBIO', 'FUNCASSESS']:
                self.fields[field_name].initial = getattr(self.instance, field_name) or 'No'
            for field_name in ['MOBILITY', 'PERHYGIENE', 'DAILYACTIV', 'PAINDISCOMF']:
                self.fields[field_name].initial = getattr(self.instance, field_name) or 'Normal'
            self.fields['ANXIETY_DEPRESSION'].initial = getattr(self.instance, 'ANXIETY_DEPRESSION', 'None')
        else:
            for field_name in ['ASSESSED', 'REHOSP', 'DECEASED', 'USEDANTIBIO', 'FUNCASSESS']:
                self.fields[field_name].initial = 'No'
            for field_name in ['MOBILITY', 'PERHYGIENE', 'DAILYACTIV', 'PAINDISCOMF']:
                self.fields[field_name].initial = 'Normal'
            self.fields['ANXIETY_DEPRESSION'].initial = 'None'

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('ASSESSED') == 'Yes' and not cleaned_data.get('ASSESSDATE'):
            self.add_error('ASSESSDATE', 'Vui lòng nhập ngày đánh giá')
        if cleaned_data.get('DECEASED') == 'Yes':
            if not cleaned_data.get('DEATHDATE'):
                self.add_error('DEATHDATE', 'Vui lòng nhập ngày tử vong')
            if not cleaned_data.get('DEATHCAUSE'):
                self.add_error('DEATHCAUSE', 'Vui lòng nhập nguyên nhân tử vong')
        return cleaned_data


class Rehospitalization90Form(forms.ModelForm):
    """Form cho thông tin tái nhập viện 90 ngày - giống hệt RehospitalizationForm"""
    
    class Meta:
        model = Rehospitalization90
        fields = ['EPISODE', 'REHOSPDATE', 'REHOSPREASONFOR', 'REHOSPLOCATION', 'REHOSPSTAYDUR']
        
        widgets = {
            'REHOSPDATE': forms.DateInput(attrs={
                'class': 'datepicker form-control',
                'autocomplete': 'off',
                'placeholder': 'YYYY-MM-DD'
            }),
            'REHOSPREASONFOR': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Lý do tái nhập viện...'
            }),
            'REHOSPLOCATION': forms.TextInput(attrs={
               
                'class': 'form-control',
                'placeholder': 'Nơi tái nhập viện...'
            }),
            'REHOSPSTAYDUR': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Thời gian nằm viện (ví dụ: 5 ngày)'
            }),
            'EPISODE': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'readonly': True
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Đảm bảo EPISODE không bắt buộc để tránh lỗi validation
        self.fields['EPISODE'].required = False
        
        # Labels chi tiết hơn
        self.fields['EPISODE'].label = _('Đợt')
        self.fields['REHOSPDATE'].label = _('Ngày tái nhập viện')
        self.fields['REHOSPREASONFOR'].label = _('Lý do tái nhập viện')
        self.fields['REHOSPLOCATION'].label = _('Nơi tái nhập viện')
        self.fields['REHOSPSTAYDUR'].label = _('Thời gian nằm viện')


class FollowUpAntibiotic90Form(forms.ModelForm):
    """Form cho thông tin kháng sinh 90 ngày - giống hệt FollowUpAntibioticForm"""
    
    class Meta:
        model = FollowUpAntibiotic90
        fields = ['EPISODE', 'ANTIBIONAME', 'ANTIBIOREASONFOR', 'ANTIBIODUR']
        
        widgets = {
            'ANTIBIONAME': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tên thuốc kháng sinh...'
            }),
            'ANTIBIOREASONFOR': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Lý do sử dụng...'
            }),
            'ANTIBIODUR': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Thời gian sử dụng (ví dụ: 7 ngày)'
            }),
            'EPISODE': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'readonly': True
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Đảm bảo EPISODE không bắt buộc để tránh lỗi validation
        self.fields['EPISODE'].required = False
        
        # Labels chi tiết hơn
        self.fields['EPISODE'].label = _('Đợt')
        self.fields['ANTIBIONAME'].label = _('Tên thuốc')
        self.fields['ANTIBIOREASONFOR'].label = _('Lý do sử dụng')
        self.fields['ANTIBIODUR'].label = _('Thời gian sử dụng')


# Ghi đè BaseInlineFormSet để tự động đặt EPISODE
class BaseRehospitalizationFormSet(forms.BaseInlineFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        if not form.instance.pk:
            form.instance.EPISODE = index + 1
    
    def save_new(self, form, commit=True):
        """Ghi đè phương thức save_new để đảm bảo lưu đúng các form mới"""
        instance = super().save_new(form, commit=False)
        
        # Chỉ lưu nếu có dữ liệu thực sự
        if (instance.REHOSPDATE or instance.REHOSPLOCATION or 
            instance.REHOSPREASONFOR or instance.REHOSPSTAYDUR):
            if commit:
                instance.save()
            return instance
        return None
    
    def save_existing(self, form, instance, commit=True):
        """Ghi đè phương thức save_existing để đảm bảo lưu đúng các form hiện có"""
        return super().save_existing(form, instance, commit)


class BaseFollowUpAntibioticFormSet(forms.BaseInlineFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        if not form.instance.pk:
            form.instance.EPISODE = index + 1
    
    def save_new(self, form, commit=True):
        """Ghi đè phương thức save_new để đảm bảo lưu đúng các form mới"""
        instance = super().save_new(form, commit=False)
        
        # Chỉ lưu nếu có dữ liệu thực sự
        if (instance.ANTIBIONAME or instance.ANTIBIODUR or 
            instance.ANTIBIOREASONFOR):
            if commit:
                instance.save()
            return instance
        return None
    
    def save_existing(self, form, instance, commit=True):
        """Ghi đè phương thức save_existing để đảm bảo lưu đúng các form hiện có"""
        return super().save_existing(form, instance, commit)


# FormSet cho chế độ chỉnh sửa (có extra form)
RehospitalizationFormSet = forms.inlineformset_factory(
    FollowUpCase,
    Rehospitalization,
    form=RehospitalizationForm,
    formset=BaseRehospitalizationFormSet,
    extra=1,
    can_delete=True,
    validate_min=False,
    validate_max=False,
    fields=['EPISODE', 'REHOSPDATE', 'REHOSPLOCATION', 'REHOSPREASONFOR', 'REHOSPSTAYDUR']
)


RehospitalizationFormSetReadOnly = forms.inlineformset_factory(
    FollowUpCase,
    Rehospitalization,
    form=RehospitalizationForm,
    extra=0,
    can_delete=False,
    fields=['EPISODE', 'REHOSPDATE', 'REHOSPLOCATION', 'REHOSPREASONFOR', 'REHOSPSTAYDUR']
)


FollowUpAntibioticFormSet = forms.inlineformset_factory(
    FollowUpCase,
    FollowUpAntibiotic,
    form=FollowUpAntibioticForm,
    formset=BaseFollowUpAntibioticFormSet,
    extra=1,
    can_delete=True,
    validate_min=False,
    validate_max=False,
    fields=['EPISODE', 'ANTIBIONAME', 'ANTIBIOREASONFOR', 'ANTIBIODUR']
)


FollowUpAntibioticFormSetReadOnly = forms.inlineformset_factory(
    FollowUpCase,
    FollowUpAntibiotic,
    form=FollowUpAntibioticForm,
    extra=0,
    can_delete=False,
    fields=['EPISODE', 'ANTIBIONAME', 'ANTIBIOREASONFOR', 'ANTIBIODUR']
)


# FormSet cho chế độ chỉnh sửa (có extra form) - giống hệt Form 28
Rehospitalization90FormSet = forms.inlineformset_factory(
    FollowUpCase90,
    Rehospitalization90,
    form=Rehospitalization90Form,
    formset=BaseRehospitalizationFormSet,  # Sử dụng cùng BaseRehospitalizationFormSet
    extra=1,
    can_delete=True,
    validate_min=False,
    validate_max=False,
    fields=['EPISODE', 'REHOSPDATE', 'REHOSPLOCATION', 'REHOSPREASONFOR', 'REHOSPSTAYDUR']
)


Rehospitalization90FormSetReadOnly = forms.inlineformset_factory(
    FollowUpCase90,
    Rehospitalization90,
    form=Rehospitalization90Form,
    extra=0,
    can_delete=False,
    fields=['EPISODE', 'REHOSPDATE', 'REHOSPLOCATION', 'REHOSPREASONFOR', 'REHOSPSTAYDUR']
)


FollowUpAntibiotic90FormSet = forms.inlineformset_factory(
    FollowUpCase90,
    FollowUpAntibiotic90,
    form=FollowUpAntibiotic90Form,
    formset=BaseFollowUpAntibioticFormSet,  # Sử dụng cùng BaseFollowUpAntibioticFormSet
    extra=1,
    can_delete=True,
    validate_min=False,
    validate_max=False,
    fields=['EPISODE', 'ANTIBIONAME', 'ANTIBIOREASONFOR', 'ANTIBIODUR']
)


FollowUpAntibiotic90FormSetReadOnly = forms.inlineformset_factory(
    FollowUpCase90,
    FollowUpAntibiotic90,
    form=FollowUpAntibiotic90Form,
    extra=0,
    can_delete=False,
    fields=['EPISODE', 'ANTIBIONAME', 'ANTIBIOREASONFOR', 'ANTIBIODUR']
)


class DischargeCaseForm(forms.ModelForm):
    """Form cho DischargeCase model theo style của FollowUpCaseForm"""
    
    # Override các CharField thành ChoiceField với RadioSelect - theo pattern FollowUpCase
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
            'DISCHDATE',
            'DISCHSTATUS', 'DISCHSTATUSDETAIL',
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
        
        # Set required=False cho tất cả để tránh validation error - theo pattern FollowUpCase
        for field_name, field in self.fields.items():
            field.required = False
        
        # Nếu có instance, đặt giá trị ban đầu cho các radio buttons
        if self.instance and self.instance.pk:
            if self.instance.TRANSFERHOSP:
                self.fields['TRANSFERHOSP'].initial = self.instance.TRANSFERHOSP
            else:
                self.fields['TRANSFERHOSP'].initial = 'No'
                
            if self.instance.DEATHATDISCH:
                self.fields['DEATHATDISCH'].initial = self.instance.DEATHATDISCH
            else:
                self.fields['DEATHATDISCH'].initial = 'No'
        else:
            # Giá trị mặc định cho form mới
            self.fields['TRANSFERHOSP'].initial = 'No'
            self.fields['DEATHATDISCH'].initial = 'No'
            
            # Set default values
            self.fields['EVENT'].initial = 'DISCHARGE'
            self.fields['STUDYID'].initial = '43EN'
            
            # Set completed_date mặc định là hôm nay
            from datetime import date
            self.fields['COMPLETEDDATE'].initial = date.today()
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validation cho transfer hospital
        transferred = cleaned_data.get('TRANSFERHOSP')
        if transferred == 'Yes':
            if not cleaned_data.get('TRANSFERREASON'):
                self.add_error('TRANSFERREASON', 'Vui lòng nhập lý do chuyển viện')
            if not cleaned_data.get('TRANSFERLOCATION'):
                self.add_error('TRANSFERLOCATION', 'Vui lòng nhập nơi chuyển viện')
        
        # Validation cho death
        died = cleaned_data.get('DEATHATDISCH')
        if died == 'Yes':
            if not cleaned_data.get('DEATHCAUSE'):
                self.add_error('DEATHCAUSE', 'Vui lòng nhập nguyên nhân tử vong')
        
        return cleaned_data


class DischargeICDForm(forms.ModelForm):
    class Meta:
        model = DischargeICD
        # Thêm 'id' vào fields
        fields = ['id', 'ICD_SEQUENCE', 'ICDCODE', 'ICDDETAIL']
        widgets = {
            'ICD_SEQUENCE': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'readonly': True
            }),
            'ICDCODE': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Mã ICD-10'
            }),
            'ICDDETAIL': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Chi tiết chẩn đoán...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Đảm bảo EPISODE không bắt buộc để tránh lỗi validation
        self.fields['ICD_SEQUENCE'].required = False
        
        # Labels chi tiết hơn - GIỐNG pattern cũ
        self.fields['ICD_SEQUENCE'].label = _('Thứ tự')
        self.fields['ICDCODE'].label = _('Mã ICD-10')
        self.fields['ICDDETAIL'].label = _('Chi tiết chẩn đoán')


# Ghi đè BaseInlineFormSet để tự động đặt EPISODE - theo pattern cũ
class BaseDischargeICDFormSet(forms.BaseInlineFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        if not form.instance.pk:
            form.instance.EPISODE = index + 1

    def save_new(self, form, commit=True):
        """Ghi đè phương thức save_new để đảm bảo lưu đúng các form mới"""
        instance = super().save_new(form, commit=False)
        
        # Chỉ lưu nếu có dữ liệu thực sự
        if instance and (instance.ICDCODE or instance.ICDDETAIL):
            if commit:
                instance.save()
            return instance
        return None
    
    def save_existing(self, form, instance, commit=True):
        """Ghi đè phương thức save_existing để đảm bảo lưu đúng các form hiện có"""
        # Luôn lưu các form hiện có để tránh mất dữ liệu
        return super().save_existing(form, instance, commit)
    
    def save(self, commit=True):
        """Override save method để handle tốt hơn"""
        if not commit:
            return super().save(commit)
        
        # Lưu từng instance một cách an toàn
        instances = []
        
        # Lưu các form hiện có
        for form in self.initial_forms:
            if form.has_changed():
                instance = self.save_existing(form, form.instance, commit)
                if instance:
                    instances.append(instance)
            elif not self._should_delete_form(form):
                instances.append(form.instance)
        
        # Lưu các form mới
        for form in self.extra_forms:
            if form.has_changed():
                instance = self.save_new(form, commit)
                if instance:
                    instances.append(instance)
        
        # Xử lý xóa
        for form in self.deleted_forms:
            if form.instance.pk:
                form.instance.delete()
        
        return instances


# FormSet cho chế độ chỉnh sửa (có extra form) - GIỐNG pattern cũ
DischargeICDFormSet = forms.inlineformset_factory(
    DischargeCase,
    DischargeICD,
    form=DischargeICDForm,
    formset=BaseDischargeICDFormSet,
    extra=1,
    can_delete=True,
    validate_min=False,
    validate_max=False,
    # Thêm 'id' vào fields
    fields=['id', 'ICD_SEQUENCE', 'ICDCODE', 'ICDDETAIL']
)


# FormSet cho chế độ chỉ xem (không có extra form) - GIỐNG pattern cũ
DischargeICDFormSetReadOnly = forms.inlineformset_factory(
    DischargeCase,
    DischargeICD,
    form=DischargeICDForm,
    extra=0,
    can_delete=False,
    fields=['id', 'ICD_SEQUENCE', 'ICDCODE', 'ICDDETAIL']
)

# FormSet cho chế độ tạo mới (sinh 1 ICD đầu tiên)
DischargeICDFormSetCreate = forms.inlineformset_factory(
    DischargeCase,
    DischargeICD,
    form=DischargeICDForm,
    formset=BaseDischargeICDFormSet,
    extra=1,           # Chỉ sinh 1 ICD đầu tiên khi tạo mới
    can_delete=False,  # Không cho xóa ICD
    fields=['id', 'ICD_SEQUENCE', 'ICDCODE', 'ICDDETAIL']
)

# FormSet cho chế độ chỉnh sửa (chỉ load ICD đã lưu, không sinh thêm)
DischargeICDFormSetEdit = forms.inlineformset_factory(
    DischargeCase,
    DischargeICD,
    form=DischargeICDForm,
    formset=BaseDischargeICDFormSet,
    extra=0,           # Không sinh thêm ICD khi edit
    can_delete=False,  # Không cho xóa ICD
    fields=['id', 'ICD_SEQUENCE', 'ICDCODE', 'ICDDETAIL']
)


class EndCaseCRFForm(forms.ModelForm):
    class Meta:
        model = EndCaseCRF
        fields = [
            'ENDDATE',
            'ENDFORMDATE',
            'VICOMPLETED',
            'V2COMPLETED',
            'V3COMPLETED',
            'V4COMPLETED',
            'WITHDRAWREASON',
            'INCOMPLETE',
            'INCOMPLETEDEATH',
            'INCOMPLETEMOVED',
            'INCOMPLETEOTHER',
            'LOSTTOFOLLOWUP',
        ]
        widgets = {
            'ENDDATE': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'ENDFORMDATE': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'VICOMPLETED': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'V2COMPLETED': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'V3COMPLETED': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'V4COMPLETED': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'WITHDRAWREASON': forms.RadioSelect(choices=[
                ('withdraw', _('Rút khỏi nghiên cứu')),
                ('forced', _('Bị rút khỏi')),
                ('na', _('Không áp dụng')),
            ]),
            'INCOMPLETE': forms.RadioSelect(choices=[
                ('yes', _('Có')),
                ('no', _('Không')),
                ('na', _('Không áp dụng')),
            ]),
            'INCOMPLETEDEATH': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'INCOMPLETEMOVED': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'INCOMPLETEOTHER': forms.TextInput(attrs={'class': 'form-control'}),
            'LOSTTOFOLLOWUP': forms.RadioSelect(choices=[
                ('yes', _('Có')),
                ('no', _('Không')),
                ('na', _('Không áp dụng')),
            ]),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Label adjustments
        self.fields['WITHDRAWREASON'].label = _("Người tham gia rút khỏi hoặc bị yêu cầu rút khỏi nghiên cứu?")
        self.fields['INCOMPLETE'].label = _("Người tham gia không thể hoàn tất nghiên cứu?")
        self.fields['INCOMPLETEDEATH'].label = _("Người tham gia tử vong")
        self.fields['INCOMPLETEMOVED'].label = _("Người tham gia không thể đến địa điểm nghiên cứu (ví dụ thay đổi nơi sinh sống)")
        self.fields['INCOMPLETEOTHER'].label = _("Khác, ghi rõ:")
        self.fields['LOSTTOFOLLOWUP'].label = _("Người tham gia bị mất liên lạc?")
        
        # Set required=False for dependent fields
        self.fields['INCOMPLETEDEATH'].required = False
        self.fields['INCOMPLETEMOVED'].required = False
        self.fields['INCOMPLETEOTHER'].required = False

        # Set default values for radio buttons
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
                raise forms.ValidationError(_("Vui lòng chọn ít nhất một lý do không hoàn tất nghiên cứu."))
        return cleaned_data