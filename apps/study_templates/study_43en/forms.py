from django import forms
from django.utils.translation import gettext_lazy as _
from .models import ScreeningCase, EnrollmentCase, ClinicalCase, LaboratoryTest, MicrobiologyCulture, PriorAntibiotic, InitialAntibiotic, MainAntibiotic, VasoIDrug, AntibioticSensitivity, SampleCollection,ScreeningContact,EnrollmentContact,FollowUpAntibiotic,FollowUpCase,Rehospitalization,FollowUpCase90,FollowUpAntibiotic90,Rehospitalization90,DischargeCase,DischargeICD,ContactSampleCollection,ContactFollowUp28,ContactFollowUp90,ContactMedicationHistory
from datetime import date

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
            'screening_id', 'STUDYID', 'SITEID', 'INITIAL',
            'UPPER16AGE', 'INFPRIOR2OR48HRSADMIT', 'ISOLATEDKPNFROMINFECTIONORBLOOD',
            'KPNISOUNTREATEDSTABLE', 'CONSENTTOSTUDY', 'SCREENINGFORMDATE','UNRECRUITED_REASON',
            'COMPLETEDBY', 'COMPLETEDDATE'
        ]
        widgets = {
            'SCREENINGFORMDATE': forms.DateInput(attrs={'class': 'datepicker'}),
            'screening_id': forms.TextInput(attrs={'readonly': True, 'class': 'form-control'}),
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

class EnrollmentCaseForm(forms.ModelForm):
    """Form cho EnrollmentCase model với xử lý đặc biệt cho bệnh nền"""
    
    # Khai báo rõ ràng các trường ngày tháng với input_formats
    ENRDATE = forms.DateField(
        label=_("Ngày tuyển bệnh nhân"),
        required=False,
        widget=forms.DateInput(format='%d/%m/%Y', attrs={'class': 'datepicker'}),
        input_formats=['%d/%m/%Y', '%Y-%m-%d']
    )
    PRIORHOSPIADMISDATE = forms.DateField(
        label=_("Ngày nhập viện trước"),
        required=False,
        widget=forms.DateInput(format='%d/%m/%Y', attrs={'class': 'datepicker'}),
        input_formats=['%d/%m/%Y', '%Y-%m-%d']
    )
    COMPLETEDDATE = forms.DateField(
        label=_("Ngày hoàn thành"),
        required=False,
        widget=forms.DateInput(format='%d/%m/%Y', attrs={'class': 'datepicker'}),
        input_formats=['%d/%m/%Y', '%Y-%m-%d']
    )

    class Meta:
        model = EnrollmentCase
        exclude = ['USUBJID', 'underlying_conditions', 'medication_history']  # Sửa lại exclude list
    
    # Định nghĩa các trường checkbox cho bệnh nền
    HEARTFAILURE = forms.BooleanField(label=_("Suy tim"), required=False)
    DIABETES = forms.BooleanField(label=_("Đái tháo đường"), required=False)
    COPD = forms.BooleanField(label=_("COPD"), required=False)
    HEPATITIS = forms.BooleanField(label=_("Viêm gan"), required=False)
    CAD = forms.BooleanField(label=_("Bệnh động mạch vành"), required=False)
    KIDNEYDISEASE = forms.BooleanField(label=_("Bệnh thận"), required=False)
    ASTHMA = forms.BooleanField(label=_("Hen suyễn"), required=False)
    CIRRHOSIS = forms.BooleanField(label=_("Xơ gan"), required=False)
    HYPERTENSION = forms.BooleanField(label=_("Tăng huyết áp"), required=False)
    AUTOIMMUNE = forms.BooleanField(label=_("Bệnh tự miễn"), required=False)
    CANCER = forms.BooleanField(label=_("Ung thư"), required=False)
    ALCOHOLISM = forms.BooleanField(label=_("Nghiện rượu"), required=False)
    HIV = forms.BooleanField(label=_("HIV"), required=False)
    ADRENALINSUFFICIENCY = forms.BooleanField(label=_("Suy thượng thận"), required=False)
    BEDRIDDEN = forms.BooleanField(label=_("Nằm một chỗ"), required=False)
    PEPTICULCER = forms.BooleanField(label=_("Loét dạ dày"), required=False)
    COLITIS_IBS = forms.BooleanField(label=_("Viêm đại tràng/IBS"), required=False)
    SENILITY = forms.BooleanField(label=_("Lão suy"), required=False)
    MALNUTRITION_WASTING = forms.BooleanField(label=_("Suy dinh dưỡng"), required=False)
    OTHERDISEASE = forms.BooleanField(label=_("Bệnh khác"), required=False)
    
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)
        
        # Áp dụng class form-control cho tất cả các trường
        for field_name, field in self.fields.items():
            if not isinstance(field, forms.BooleanField):
                field.widget.attrs.update({'class': 'form-control'})
        
        # Nếu có instance, cần set initial cho các trường bệnh nền
        if instance and hasattr(instance, 'underlying_conditions'):
            underlying_conditions = instance.underlying_conditions or []
            for condition in underlying_conditions:
                if condition in self.fields:
                    self.fields[condition].initial = True
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Lấy danh sách bệnh nền được chọn
        conditions = []
        for field_name in self.fields:
            if field_name.isupper() and field_name in [
                'HEARTFAILURE', 'DIABETES', 'COPD', 'HEPATITIS', 'CAD',
                'KIDNEYDISEASE', 'ASTHMA', 'CIRRHOSIS', 'HYPERTENSION',
                'AUTOIMMUNE', 'CANCER', 'ALCOHOLISM', 'HIV',
                'ADRENALINSUFFICIENCY', 'BEDRIDDEN', 'PEPTICULCER',
                'COLITIS_IBS', 'SENILITY', 'MALNUTRITION_WASTING',
                'OTHERDISEASE'
            ] and self.cleaned_data.get(field_name):
                conditions.append(field_name)
        
        # Lưu danh sách bệnh nền vào instance
        self.instance.underlying_conditions = conditions
        
        # Xử lý dữ liệu lịch sử dùng thuốc nếu có trong POST data
        medication_data = self.data.get('MEDICATION_DATA')
        if medication_data:
            self.instance.medication_history = medication_data
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Đảm bảo underlying_conditions và medication_history được gán
        if hasattr(self.instance, 'underlying_conditions'):
            instance.underlying_conditions = self.instance.underlying_conditions
        if hasattr(self.instance, 'medication_history'):
            instance.medication_history = self.instance.medication_history
        
        if commit:
            instance.save()
        return instance

class ClinicalCaseForm(forms.ModelForm):
    """Form cho ClinicalCase model với xử lý đặc biệt cho các triệu chứng"""
    class Meta:
        model = ClinicalCase
        exclude = ['_symptoms_group1', '_symptoms_group2']  # Loại trừ các field JSON nội bộ
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
            'SUPPORTTYPE': forms.Select(attrs={'class': 'form-control select2'}),
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
    BLOODINFECT = forms.BooleanField(label=_("Nhiễm khuẩn huyết"), required=False)
    SEPTICSHOCK = forms.BooleanField(label=_("Sốc nhiễm khuẩn"), required=False)
    RESPISUPPORT = forms.BooleanField(label=_("Hỗ trợ hô hấp"), required=False)
    RESUSFLUID = forms.BooleanField(label=_("Dịch truyền hồi sức"), required=False)
    VASOINOTROPES = forms.BooleanField(label=_("Sử dụng thuốc vận mạch"), required=False)
    DIALYSIS = forms.BooleanField(label=_("Lọc máu"), required=False)
    DRAINAGE = forms.BooleanField(label=_("Dẫn lưu"), required=False)
    PRIORANTIBIOTIC = forms.BooleanField(label=_("Kháng sinh trước"), required=False)
    INITIALANTIBIOTIC = forms.BooleanField(label=_("Kháng sinh ban đầu"), required=False)
    INITIALABXAPPROP = forms.BooleanField(label=_("Kháng sinh ban đầu phù hợp"), required=False)
    
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)
        
        # Áp dụng class form-control cho tất cả các trường
        for field_name, field in self.fields.items():
            if not isinstance(field, forms.BooleanField):
                field.widget.attrs.update({'class': 'form-control'})
        
        # Nếu có instance, cần set initial cho các trường triệu chứng
        if instance:
            # Nhóm 1
            symptoms_group1 = instance.symptoms_group1
            for symptom in symptoms_group1:
                if symptom in self.fields:
                    self.fields[symptom].initial = True
            
            # Nhóm 2
            symptoms_group2 = instance.symptoms_group2
            for symptom in symptoms_group2:
                if symptom in self.fields:
                    self.fields[symptom].initial = True
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Lấy danh sách triệu chứng được chọn
        symptoms_group1 = []
        symptoms_group2 = []
        
        # Xác định các triệu chứng nhóm 1
        for field_name in ['FEVER', 'FATIGUE', 'MUSCLEPAIN', 'LOSSAPPETITE', 'COUGH', 'CHESTPAIN',
                        'SHORTBREATH', 'JAUNDICE', 'PAINURINATION', 'BLOODYURINE', 'CLOUDYURINE',
                        'EPIGASTRICPAIN', 'LOWERABDPAIN', 'FLANKPAIN', 'URINARYHESITANCY',
                        'SUBCOSTALPAIN', 'HEADACHE', 'POORCONTACT', 'DELIRIUMAGITATION', 'VOMITING',
                        'SEIZURES', 'EYEPAIN', 'REDEYES', 'NAUSEA', 'BLURREDVISION', 'SKINLESIONS']:
            if self.cleaned_data.get(field_name, False):
                symptoms_group1.append(field_name)
        
        # Xác định các triệu chứng nhóm 2
        for field_name in ['FEVER_2', 'RASH', 'SKINBLEEDING', 'MUCOSALBLEEDING', 'SKINLESIONS_2',
                        'LUNGCRACKLES', 'CONSOLIDATIONSYNDROME', 'PLEURALEFFUSION', 'PNEUMOTHORAX',
                        'HEARTMURMUR', 'ABNORHEARTSOUNDS', 'JUGULARVEINDISTENTION', 'LIVERFAILURESIGNS',
                        'PORTALHYPERTENSIONSIGNS', 'HEPATOSPLENOMEGALY', 'CONSCIOUSNESSDISTURBANCE',
                        'LIMBWEAKNESSPARALYSIS', 'CRANIALNERVEPARALYSIS', 'MENINGEALSIGNS', 'REDEYES_2',
                        'HYPOPYON', 'EDEMA', 'CUSHINGOIDAPPEARANCE', 'EPIGASTRICPAIN_2', 'LOWERABDPAIN_2',
                        'FLANKPAIN_2', 'SUBCOSTALPAIN_2']:
            if self.cleaned_data.get(field_name, False):
                symptoms_group2.append(field_name)
        
        # Cập nhật danh sách triệu chứng vào instance
        instance.symptoms_group1 = symptoms_group1
        instance.symptoms_group2 = symptoms_group2
        
        if commit:
            instance.save()
        
        return instance

class LaboratoryTestForm(forms.ModelForm):
    class Meta:
        model = LaboratoryTest
        fields = ['category', 'test_type', 'performed', 'performed_date', 'result']
        widgets = {
            'performed_date': forms.DateInput(attrs={
                'class': 'form-control datepicker',
                'autocomplete': 'off'
            }),
            'result': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Nhập kết quả...'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'test_type': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['performed'].widget.attrs.update({'class': 'form-check-input'})
        
        # JavaScript để filter test_type theo category
        self.fields['test_type'].widget.attrs.update({
            'data-category-dependent': 'true'
        })

# Form để tạo hàng loạt xét nghiệm theo category
class LaboratoryTestBulkCreateForm(forms.Form):
    """Form để tạo hàng loạt các xét nghiệm theo category"""
    
    categories = forms.MultipleChoiceField(
        label=_("Chọn nhóm xét nghiệm cần tạo"),
        choices=LaboratoryTest.CATEGORY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    
    def get_tests_to_create(self):
        """Trả về danh sách các xét nghiệm cần tạo theo category"""
        category_tests = {
            'BLOOD_COAGULATION': ['INR', 'DIC'],
            'COMPLETE_BLOOD_COUNT': ['WBC', 'NEU', 'LYM', 'EOS', 'RBC', 'HEMOGLOBIN', 'PLATELETS'],
            'BIOCHEMISTRY': [
                'NATRI', 'KALI', 'CLO', 'MAGNE', 'URE', 'CREATININE', 
                'AST', 'ALT', 'GLUCOSEBLOOD', 'BEDSIDE_GLUCOSE',
                'BILIRUBIN_TP', 'BILIRUBIN_TT', 'PROTEIN', 'ALBUMIN',
                'CRP_QUALITATIVE', 'CRP_QUANTITATIVE', 'CRP', 'PROCALCITONIN',
                'HBA1C', 'CORTISOL', 'HIV', 'CD4'
            ],
            'BLOOD_GAS_ANALYSIS': ['PH', 'PCO2', 'PO2', 'HCO3', 'BE', 'AADO2'],
            'LACTATE': ['LACTATE_ARTERIAL'],
            'URINE_ANALYSIS': ['URINE_PH', 'NITRIT', 'URINE_PROTEIN', 'LEU', 'URINE_RBC', 'SEDIMENT'],
            'PLEURAL_FLUID': [
                'PERITONEAL_WBC', 'PERITONEAL_NEU', 'PERITONEAL_MONO', 'PERITONEAL_RBC',
                'PERITONEAL_PROTEIN', 'PERITONEAL_PROTEIN_BLOOD', 'PERITONEAL_ALBUMIN',
                'PERITONEAL_ALBUMIN_BLOOD', 'PERITONEAL_ADA', 'PERITONEAL_CELLBLOCK'
            ],
            'PLEURAL_FLUID_ANALYSIS': [
                'PLEURAL_WBC', 'PLEURAL_NEU', 'PLEURAL_MONO', 'PLEURAL_EOS', 'PLEURAL_RBC',
                'PLEURAL_PROTEIN', 'PLEURAL_LDH', 'PLEURAL_LDH_BLOOD', 'PLEURAL_ADA', 'PLEURAL_CELLBLOCK'
            ],
            'CSF_ANALYSIS': [
                'CSF_WBC', 'CSF_NEU', 'CSF_MONO', 'CSF_EOS', 'CSF_RBC',
                'CSF_PROTEIN', 'CSF_GLUCOSE', 'CSF_LACTATE', 'CSF_GRAM_STAIN'
            ],
            'CHEST_XRAY': ['CHEST_XRAY'],
            'ABDOMINAL_ULTRASOUND': ['ABDOMINAL_ULTRASOUND'],
            'BRAIN_CT_MRI': ['BRAIN_CT_MRI'],
            'CHEST_ABDOMEN_CT': ['CHEST_ABDOMEN_CT'],
            'ECHOCARDIOGRAPHY': ['ECHOCARDIOGRAPHY'],
            'SOFT_TISSUE_ULTRASOUND': ['SOFT_TISSUE_ULTRASOUND'],
        }
        
        tests_to_create = []
        selected_categories = self.cleaned_data.get('categories', [])
        
        for category in selected_categories:
            tests_to_create.extend(category_tests.get(category, []))
        
        return tests_to_create

LaboratoryTestFormSet = forms.modelformset_factory(
    LaboratoryTest,
    form=LaboratoryTestForm,
    extra=0,
    can_delete=False
)

class MicrobiologyCultureForm(forms.ModelForm):
    """Form nhập thông tin nuôi cấy vi sinh"""
    class Meta:
        model = MicrobiologyCulture
        fields = ['sample_type', 'other_sample', 'performed_date', 'sample_id', 
                  'result_type', 'result_details', 'performed']
        widgets = {
            'performed_date': forms.DateInput(attrs={'class': 'form-control datepicker', 'placeholder': 'nn/tt/nnnn'}),
            'sample_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mã số bệnh phẩm'}),
            'result_details': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Chi tiết kết quả'}),
        }

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
    ScreeningCase,
    PriorAntibiotic,
    form=PriorAntibioticForm,
    extra=1,
    can_delete=True
)

InitialAntibioticFormSet = forms.inlineformset_factory(
    ScreeningCase,
    InitialAntibiotic,
    form=InitialAntibioticForm,
    extra=1,
    can_delete=True
)

MainAntibioticFormSet = forms.inlineformset_factory(
    ScreeningCase,
    MainAntibiotic,
    form=MainAntibioticForm,
    extra=1,
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
    ScreeningCase,
    VasoIDrug,
    form=VasoIDrugForm,
    extra=1,
    can_delete=True
)

class AntibioticSensitivityForm(forms.ModelForm):
    """Form cho kết quả nhạy cảm kháng sinh"""
    class Meta:
        model = AntibioticSensitivity
        fields = ['tier', 'antibiotic_name', 'other_antibiotic_name', 
                 'sensitivity_level', 'inhibition_zone_diameter', 'mic_value']
        widgets = {
            'tier': forms.Select(attrs={'class': 'form-control'}),
            'antibiotic_name': forms.Select(attrs={'class': 'form-control'}),
            'other_antibiotic_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nếu chọn kháng sinh khác'}),
            'sensitivity_level': forms.Select(attrs={'class': 'form-control'}),
            'inhibition_zone_diameter': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'mm'}),
            'mic_value': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'μg/ml'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['other_antibiotic_name'].required = False
        
        # Tùy chọn hiển thị field other_antibiotic_name chỉ khi chọn OTHER
        self.fields['antibiotic_name'].widget.attrs.update({
            'onchange': 'toggleOtherAntibioticName(this)'
        })

# FormSet để quản lý nhiều kháng sinh cùng lúc cho một culture
AntibioticSensitivityFormSet = forms.inlineformset_factory(
    MicrobiologyCulture,
    AntibioticSensitivity,
    form=AntibioticSensitivityForm,
    extra=1,
    can_delete=True
)

class SampleCollectionForm(forms.ModelForm):
    class Meta:
        model = SampleCollection
        exclude = ('clinical_case',)
        widgets = {
            'sample_type': forms.RadioSelect(),
            'SAMPLE1': forms.RadioSelect(choices=((True, _('Có')), (False, _('Không')))),
            'REASONIFNO': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Vui lòng ghi rõ lý do không thu nhận được mẫu')}),
            'STOOLDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'THROATSWABDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'RECTSWABDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'BLOODDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'CULTRESSTOOL': forms.RadioSelect(),
            'CULTRESRECTSWAB': forms.RadioSelect(),
            'CULTRESTHROATSWAB': forms.RadioSelect(),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            # Thêm các trường lần 2 (_2)
            'STOOL_2': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'THROATSWAB_2': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'RECTSWAB_2': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'BLOOD_2': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'STOOLDATE_2': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'THROATSWABDATE_2': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'RECTSWABDATE_2': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'BLOODDATE_2': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'CULTRESSTOOL_2': forms.RadioSelect(),
            'CULTRESRECTSWAB_2': forms.RadioSelect(),
            'CULTRESTHROATSWAB_2': forms.RadioSelect(),
            'REASONIFNO_2': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Lý do không thu nhận được mẫu lần 2')}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Thay đổi giao diện cho các trường boolean
        for field_name in [
            'STOOL', 'THROATSWAB', 'RECTSWAB', 'BLOOD', 
            'KLEBPNEU', 'OTHERRES', 'KLEBPNEU_2', 'OTHERRES_2',
            # Thêm các trường lần 2 (_2)
            'STOOL_2', 'THROATSWAB_2', 'RECTSWAB_2', 'BLOOD_2'
        ]:
            if field_name in self.fields:
                self.fields[field_name].widget = forms.CheckboxInput(attrs={'class': 'form-check-input'})
                
        # Đặt giá trị mặc định cho COMPLETEDDATE là ngày hiện tại nếu chưa có
        from datetime import date
        if not self.initial.get('COMPLETEDDATE'):
            self.initial['COMPLETEDDATE'] = date.today()

class ScreeningContactForm(forms.ModelForm):
    """Form cho model ScreeningContact"""
    SITEID = forms.ChoiceField(
        choices=SITEID_CHOICES,
        label=_("Mã cơ sở"),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    # Override các BooleanField thành ChoiceField để xử lý chính xác
    LIVEIN5DAYS3MTHS = forms.ChoiceField(
        choices=[('0', 'Không'), ('1', 'Có')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Sống chung ít nhất 5 ngày trong 3 tháng')
    )
    MEALCAREONCEDAY = forms.ChoiceField(
        choices=[('0', 'Không'), ('1', 'Có')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Ăn cùng/chăm sóc ít nhất 1 lần/ngày')
    )
    CONSENTTOSTUDY = forms.ChoiceField(
        choices=[('0', 'Không'), ('1', 'Có')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Đồng ý tham gia nghiên cứu')
    )
    
    class Meta:
        model = ScreeningContact
        fields = ['screening_id', 'SITEID', 'INITIAL','SITEID', 'SUBJIDENROLLSTUDY',
                 'LIVEIN5DAYS3MTHS', 'MEALCAREONCEDAY', 'CONSENTTOSTUDY',
                 'SCREENINGFORMDATE', 'COMPLETEDBY', 'COMPLETEDDATE']
        widgets = {
            'SCREENINGFORMDATE': forms.DateInput(attrs={'class': 'datepicker'}),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'datepicker'}),
            'SUBJIDENROLLSTUDY': forms.Select(attrs={'class': 'select2'}),
            'screening_id': forms.TextInput(attrs={'readonly': True}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Tạo mã screening_id mới cho form tạo mới
        if not self.instance.pk:
            # Tìm screening_id lớn nhất hiện có
            from django.db.models import Max
            import re
            
            last_screening = ScreeningContact.objects.order_by('-screening_id').first()
            new_screening_id = "CS-001"  # Mặc định
            
            if last_screening and last_screening.screening_id:
                try:
                    # Trích xuất số từ mã CS-XXX
                    match = re.search(r'CS-(\d+)', last_screening.screening_id)
                    if match:
                        last_num = int(match.group(1))
                        new_screening_id = f"CS-{last_num + 1:03d}"
                except (ValueError, AttributeError):
                    pass
            
            # Hiển thị mã screening_id mới trong form
            self.fields['screening_id'].initial = new_screening_id
            self.fields['screening_id'].help_text = _("Mã screening contact được tạo tự động")
        
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
                field.widget.attrs.update({'class': 'form-control'})
        
        # Đánh dấu các trường bắt buộc
        required_fields = ['SITEID', 'INITIAL', 'SUBJIDENROLLSTUDY',
                          'LIVEIN5DAYS3MTHS', 'MEALCAREONCEDAY', 'CONSENTTOSTUDY']
        for field_name in required_fields:
            self.fields[field_name].required = True
            
        # Hiển thị tất cả bệnh nhân có sẵn để chọn
        # Lọc danh sách bệnh nhân - hiển thị tất cả bệnh nhân đã sàng lọc
        available_patients = ScreeningCase.objects.filter(
            SUBJID__startswith='A-'
        ).order_by('INITIAL', 'USUBJID')
        self.fields['SUBJIDENROLLSTUDY'].queryset = available_patients
        
        # Đặt label để hiển thị rõ ràng cho selector
        self.fields['SUBJIDENROLLSTUDY'].label_from_instance = lambda obj: f"{obj.INITIAL} ({obj.USUBJID})"
        
        # Xử lý giá trị mặc định của các radio buttons
        if not self.instance.pk:  # Nếu đây là form tạo mới
            boolean_fields = ['LIVEIN5DAYS3MTHS', 'MEALCAREONCEDAY', 'CONSENTTOSTUDY']
            for field_name in boolean_fields:
                self.fields[field_name].initial = '0'
        else:  # Nếu đây là form chỉnh sửa
            for field_name in ['LIVEIN5DAYS3MTHS', 'MEALCAREONCEDAY', 'CONSENTTOSTUDY']:
                if hasattr(self.instance, field_name):
                    self.fields[field_name].initial = '1' if getattr(self.instance, field_name) else '0'
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Chuyển đổi ChoiceField string "0"/"1" thành boolean cho database
        boolean_fields = ['LIVEIN5DAYS3MTHS', 'MEALCAREONCEDAY', 'CONSENTTOSTUDY']
        
        for field_name in boolean_fields:
            value = cleaned_data.get(field_name)
            
            if value is not None:
                cleaned_data[field_name] = (value == '1')
        
        return cleaned_data

class EnrollmentContactForm(forms.ModelForm):
    # Nếu muốn có các trường checkbox bệnh nền, bạn có thể định nghĩa như EnrollmentCaseForm
    HEARTFAILURE = forms.BooleanField(label=_("Suy tim"), required=False)
    DIABETES = forms.BooleanField(label=_("Đái tháo đường"), required=False)
    COPD = forms.BooleanField(label=_("COPD/VPQ mạn"), required=False)
    HEPATITIS = forms.BooleanField(label=_("Viêm gan mạn"), required=False)
    CAD = forms.BooleanField(label=_("Bệnh mạch vành"), required=False)
    KIDNEYDISEASE = forms.BooleanField(label=_("Bệnh thận mạn"), required=False)
    ASTHMA = forms.BooleanField(label=_("Hen"), required=False)
    CIRRHOSIS = forms.BooleanField(label=_("Xơ gan"), required=False)
    HYPERTENSION = forms.BooleanField(label=_("Tăng huyết áp"), required=False)
    AUTOIMMUNE = forms.BooleanField(label=_("Bệnh tự miễn"), required=False)
    CANCER = forms.BooleanField(label=_("Ung thư"), required=False)
    ALCOHOLISM = forms.BooleanField(label=_("Nghiện rượu"), required=False)
    HIV = forms.BooleanField(label=_("HIV"), required=False)
    ADRENALINSUFFICIENCY = forms.BooleanField(label=_("Suy thượng thận"), required=False)
    BEDRIDDEN = forms.BooleanField(label=_("Nằm liệt giường"), required=False)
    PEPTICULCER = forms.BooleanField(label=_("Loét dạ dày"), required=False)
    COLITIS_IBS = forms.BooleanField(label=_("Viêm loét đại tràng/IBS"), required=False)
    SENILITY = forms.BooleanField(label=_("Lão suy"), required=False)
    MALNUTRITION_WASTING = forms.BooleanField(label=_("Suy dinh dưỡng/suy mòn"), required=False)
    OTHERDISEASE = forms.BooleanField(label=_("Khác, ghi rõ"), required=False)

    class Meta:
        model = EnrollmentContact
        exclude = []
        widgets = {
            'ENRDATE': forms.DateInput(attrs={'class': 'datepicker'}),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'datepicker'}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)
        # Set initial cho các trường bệnh nền nếu có instance
        if instance and instance.underlying_conditions:
            for cond in instance.underlying_conditions:
                if cond in self.fields:
                    self.fields[cond].initial = True

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Lưu danh sách bệnh nền vào underlying_conditions
        conditions = []
        for field in [
            'HEARTFAILURE', 'DIABETES', 'COPD', 'HEPATITIS', 'CAD',
            'KIDNEYDISEASE', 'ASTHMA', 'CIRRHOSIS', 'HYPERTENSION',
            'AUTOIMMUNE', 'CANCER', 'ALCOHOLISM', 'HIV',
            'ADRENALINSUFFICIENCY', 'BEDRIDDEN', 'PEPTICULCER',
            'COLITIS_IBS', 'SENILITY', 'MALNUTRITION_WASTING', 'OTHERDISEASE'
        ]:
            if self.cleaned_data.get(field):
                conditions.append(field)
        instance.underlying_conditions = conditions
        if commit:
            instance.save()
        return instance
    


class FollowUpCaseForm(forms.ModelForm):
    """Form cho FollowUpCase model theo style hiện tại"""
    
    # Override các CharField thành ChoiceField với RadioSelect (theo pattern hiện tại)
    FU28ASSESSED = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Bệnh nhân được đánh giá tình trạng tại thời điểm ngày 28?')
    )
    
    FU28REHOSP = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Bệnh nhân tái nhập viện?')
    )
    
    FU28DECEASED = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Bệnh nhân tử vong?')
    )
    
    FU28USEDANTIBIO = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Bệnh nhân có sử dụng kháng sinh từ lần khám gần nhất?')
    )
    
    FU28FUNCASSESS = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Đánh giá tình trạng chức năng tại ngày 28?')
    )
    
    # RadioSelect cho các đánh giá chức năng
    FU28MOBILITY = forms.ChoiceField(
        choices=[('Normal', 'Bình thường'), ('Problem', 'Có vấn đề'), ('Bedridden', 'Nằm một chỗ')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5a. Vận động (đi lại)')
    )
    
    FU28PERHYGIENE = forms.ChoiceField(
        choices=[('Normal', 'Bình thường'), ('Problem', 'Có vấn đề'), ('Bedridden', 'Nằm một chỗ')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5b. Vệ sinh cá nhân (tự tắm rửa, thay quần áo)')
    )
    
    FU28DAILYACTIV = forms.ChoiceField(
        choices=[('Normal', 'Bình thường'), ('Problem', 'Có vấn đề'), ('Bedridden', 'Nằm một chỗ')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5c. Sinh hoạt hằng ngày (làm việc, học tập, việc nhà, hoạt động vui chơi)')
    )
    
    FU28PAINDISCOMF = forms.ChoiceField(
        choices=[('Normal', 'Bình thường'), ('Problem', 'Có vấn đề'), ('Bedridden', 'Nằm một chỗ')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5d. Đau/ khó chịu')
    )
    
    FU28ANXDEPRESS = forms.ChoiceField(
        choices=[('None', 'Không'), ('Moderate', 'Trung bình'), ('Severe', 'Nhiều')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5e. Lo lắng/ Trầm cảm')
    )

    class Meta:
        model = FollowUpCase
        fields = [
            'FU28ASSESSED', 'FU28ASSESSDATE', 'FU28PATSTATUS',
            'FU28REHOSP', 'FU28REHOSPCOUNT', 
            'FU28DECEASED', 'FU28DEATHDATE', 'FU28DEATHCAUSE',
            'FU28USEDANTIBIO', 'FU28ANTIBIOCOUNT', 
            'FU28FUNCASSESS', 'FU28MOBILITY', 'FU28PERHYGIENE', 
            'FU28DAILYACTIV', 'FU28PAINDISCOMF', 'FU28ANXDEPRESS', 
            'FU28FBSISCORE', 'COMPLETEDBY', 'COMPLETEDDATE'
        ]
        
        widgets = {
            'FU28ASSESSDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'FU28DEATHDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            
            'FU28PATSTATUS': forms.Select(attrs={'class': 'form-control select2'}),
            'FU28FBSISCORE': forms.Select(attrs={'class': 'form-control select2'}),
            'FU28DEATHCAUSE': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'FU28REHOSPCOUNT': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'FU28ANTIBIOCOUNT': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'COMPLETEDBY': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set required=False cho tất cả để tránh validation error
        for field_name, field in self.fields.items():
            field.required = False
            
        # Nếu có instance, đặt giá trị ban đầu cho các radio buttons
        if self.instance and self.instance.pk:
            for field_name in ['FU28ASSESSED', 'FU28REHOSP', 'FU28DECEASED', 'FU28USEDANTIBIO', 'FU28FUNCASSESS']:
                if getattr(self.instance, field_name):
                    self.fields[field_name].initial = getattr(self.instance, field_name)
                else:
                    self.fields[field_name].initial = 'No'
            
            for field_name in ['FU28MOBILITY', 'FU28PERHYGIENE', 'FU28DAILYACTIV', 'FU28PAINDISCOMF']:
                if getattr(self.instance, field_name):
                    self.fields[field_name].initial = getattr(self.instance, field_name)
                else:
                    self.fields[field_name].initial = 'Normal'
            
            if self.instance.FU28ANXDEPRESS:
                self.fields['FU28ANXDEPRESS'].initial = self.instance.FU28ANXDEPRESS
            else:
                self.fields['FU28ANXDEPRESS'].initial = 'None'
        else:
            # Giá trị mặc định cho form mới
            for field_name in ['FU28ASSESSED', 'FU28REHOSP', 'FU28DECEASED', 'FU28USEDANTIBIO', 'FU28FUNCASSESS']:
                self.fields[field_name].initial = 'No'
            
            for field_name in ['FU28MOBILITY', 'FU28PERHYGIENE', 'FU28DAILYACTIV', 'FU28PAINDISCOMF']:
                self.fields[field_name].initial = 'Normal'
            
            self.fields['FU28ANXDEPRESS'].initial = 'None'
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validation logic
        assessed = cleaned_data.get('FU28ASSESSED')
        if assessed == 'Yes':
            if not cleaned_data.get('FU28ASSESSDATE'):
                self.add_error('FU28ASSESSDATE', 'Vui lòng nhập ngày đánh giá')
        
        deceased = cleaned_data.get('FU28DECEASED')
        if deceased == 'Yes':
            if not cleaned_data.get('FU28DEATHDATE'):
                self.add_error('FU28DEATHDATE', 'Vui lòng nhập ngày tử vong')
            if not cleaned_data.get('FU28DEATHCAUSE'):
                self.add_error('FU28DEATHCAUSE', 'Vui lòng nhập nguyên nhân tử vong')
        
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
        # Luôn lưu các form hiện có để tránh mất dữ liệu
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
        # Luôn lưu các form hiện có để tránh mất dữ liệu
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

# FormSet cho chế độ chỉ xem (không có extra form)
RehospitalizationFormSetReadOnly = forms.inlineformset_factory(
    FollowUpCase,
    Rehospitalization,
    form=RehospitalizationForm,
    extra=0,  # KHÔNG có form trống
    can_delete=False,
    fields=['EPISODE', 'REHOSPDATE', 'REHOSPLOCATION', 'REHOSPREASONFOR', 'REHOSPSTAYDUR']
)

# Tương tự cho Antibiotic
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
    extra=0,  # KHÔNG có form trống
    can_delete=False,
    fields=['EPISODE', 'ANTIBIONAME', 'ANTIBIOREASONFOR', 'ANTIBIODUR']
)


class FollowUpCase90Form(forms.ModelForm):
    """Form cho FollowUpCase90 model theo style hiện tại - GIỐNG HỆT FollowUpCaseForm"""
    
    # Override các CharField thành ChoiceField với RadioSelect (theo pattern hiện tại)
    FU90ASSESSED = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Bệnh nhân được đánh giá tình trạng tại thời điểm ngày 90?')
    )
    
    FU90REHOSP = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Bệnh nhân tái nhập viện?')
    )
    
    FU90DECEASED = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Bệnh nhân tử vong?')
    )
    
    FU90USEDANTIBIO = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Bệnh nhân có sử dụng kháng sinh từ lần khám gần nhất?')
    )
    
    FU90FUNCASSESS = forms.ChoiceField(
        choices=[('No', 'Không'), ('Yes', 'Có'), ('NA', 'Không áp dụng')],
        widget=forms.RadioSelect,
        required=True,
        label=_('Đánh giá tình trạng chức năng tại ngày 90?')
    )
    
    # RadioSelect cho các đánh giá chức năng
    FU90MOBILITY = forms.ChoiceField(
        choices=[('Normal', 'Bình thường'), ('Problem', 'Có vấn đề'), ('Bedridden', 'Nằm một chỗ')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5a. Vận động (đi lại)')
    )
    
    FU90PERHYGIENE = forms.ChoiceField(
        choices=[('Normal', 'Bình thường'), ('Problem', 'Có vấn đề'), ('Bedridden', 'Nằm một chỗ')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5b. Vệ sinh cá nhân (tự tắm rửa, thay quần áo)')
    )
    
    FU90DAILYACTIV = forms.ChoiceField(
        choices=[('Normal', 'Bình thường'), ('Problem', 'Có vấn đề'), ('Bedridden', 'Nằm một chỗ')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5c. Sinh hoạt hằng ngày (làm việc, học tập, việc nhà, hoạt động vui chơi)')
    )
    
    FU90PAINDISCOMF = forms.ChoiceField(
        choices=[('Normal', 'Bình thường'), ('Problem', 'Có vấn đề'), ('Bedridden', 'Nằm một chỗ')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5d. Đau/ khó chịu')
    )
    
    FU90ANXDEPRESS = forms.ChoiceField(
        choices=[('None', 'Không'), ('Moderate', 'Trung bình'), ('Severe', 'Nhiều')],
        widget=forms.RadioSelect,
        required=False,
        label=_('5e. Lo lắng/ Trầm cảm')
    )

    class Meta:
        model = FollowUpCase90
        fields = [
            'FU90ASSESSED', 'FU90ASSESSDATE', 'FU90PATSTATUS',
            'FU90REHOSP', 'FU90REHOSPCOUNT', 
            'FU90DECEASED', 'FU90DEATHDATE', 'FU90DEATHCAUSE',
            'FU90USEDANTIBIO', 'FU90ANTIBIOCOUNT', 
            'FU90FUNCASSESS', 'FU90MOBILITY', 'FU90PERHYGIENE', 
            'FU90DAILYACTIV', 'FU90PAINDISCOMF', 'FU90ANXDEPRESS', 
            'FU90FBSISCORE', 'COMPLETEDBY', 'COMPLETEDDATE'
        ]
        
        widgets = {
            'FU90ASSESSDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'FU90DEATHDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'datepicker form-control'}),
            
            'FU90PATSTATUS': forms.Select(attrs={'class': 'form-control select2'}),
            'FU90FBSISCORE': forms.Select(attrs={'class': 'form-control select2'}),
            'FU90DEATHCAUSE': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'FU90REHOSPCOUNT': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'FU90ANTIBIOCOUNT': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'COMPLETEDBY': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set required=False cho tất cả để tránh validation error
        for field_name, field in self.fields.items():
            field.required = False
            
        # Nếu có instance, đặt giá trị ban đầu cho các radio buttons
        if self.instance and self.instance.pk:
            for field_name in ['FU90ASSESSED', 'FU90REHOSP', 'FU90DECEASED', 'FU90USEDANTIBIO', 'FU90FUNCASSESS']:
                if getattr(self.instance, field_name):
                    self.fields[field_name].initial = getattr(self.instance, field_name)
                else:
                    self.fields[field_name].initial = 'No'
            
            for field_name in ['FU90MOBILITY', 'FU90PERHYGIENE', 'FU90DAILYACTIV', 'FU90PAINDISCOMF']:
                if getattr(self.instance, field_name):
                    self.fields[field_name].initial = getattr(self.instance, field_name)
                else:
                    self.fields[field_name].initial = 'Normal'
            
            if self.instance.FU90ANXDEPRESS:
                self.fields['FU90ANXDEPRESS'].initial = self.instance.FU90ANXDEPRESS
            else:
                self.fields['FU90ANXDEPRESS'].initial = 'None'
        else:
            # Giá trị mặc định cho form mới
            for field_name in ['FU90ASSESSED', 'FU90REHOSP', 'FU90DECEASED', 'FU90USEDANTIBIO', 'FU90FUNCASSESS']:
                self.fields[field_name].initial = 'No'
            
            for field_name in ['FU90MOBILITY', 'FU90PERHYGIENE', 'FU90DAILYACTIV', 'FU90PAINDISCOMF']:
                self.fields[field_name].initial = 'Normal'
            
            self.fields['FU90ANXDEPRESS'].initial = 'None'
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validation logic
        assessed = cleaned_data.get('FU90ASSESSED')
        if assessed == 'Yes':
            if not cleaned_data.get('FU90ASSESSDATE'):
                self.add_error('FU90ASSESSDATE', 'Vui lòng nhập ngày đánh giá')
        
        deceased = cleaned_data.get('FU90DECEASED')
        if deceased == 'Yes':
            if not cleaned_data.get('FU90DEATHDATE'):
                self.add_error('FU90DEATHDATE', 'Vui lòng nhập ngày tử vong')
            if not cleaned_data.get('FU90DEATHCAUSE'):
                self.add_error('FU90DEATHCAUSE', 'Vui lòng nhập nguyên nhân tử vong')
        
        return cleaned_data  # SỬA: Thêm dòng này để giống form 28


class Rehospitalization90Form(forms.ModelForm):
    """Form cho thông tin tái nhập viện 90 ngày - GIỐNG HỆT RehospitalizationForm"""
    
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
            'EPISODE': forms.NumberInput(attrs={  # SỬA: Giống form 28
                'class': 'form-control',
                'min': 1,
                'readonly': True
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Đảm bảo EPISODE không bắt buộc để tránh lỗi validation
        self.fields['EPISODE'].required = False
        
        # Labels chi tiết hơn - GIỐNG FORM 28
        self.fields['EPISODE'].label = _('Đợt')
        self.fields['REHOSPDATE'].label = _('Ngày tái nhập viện')
        self.fields['REHOSPREASONFOR'].label = _('Lý do tái nhập viện')
        self.fields['REHOSPLOCATION'].label = _('Nơi tái nhập viện')
        self.fields['REHOSPSTAYDUR'].label = _('Thời gian nằm viện')


class FollowUpAntibiotic90Form(forms.ModelForm):
    """Form cho thông tin kháng sinh 90 ngày - GIỐNG HỆT FollowUpAntibioticForm"""
    
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
            'EPISODE': forms.NumberInput(attrs={  # SỬA: Giống form 28
                'class': 'form-control',
                'min': 1,
                'readonly': True
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Đảm bảo EPISODE không bắt buộc để tránh lỗi validation
        self.fields['EPISODE'].required = False
        
        # Labels chi tiết hơn - GIỐNG FORM 28
        self.fields['EPISODE'].label = _('Đợt')
        self.fields['ANTIBIONAME'].label = _('Tên thuốc')
        self.fields['ANTIBIOREASONFOR'].label = _('Lý do sử dụng')
        self.fields['ANTIBIODUR'].label = _('Thời gian sử dụng')


# Ghi đè BaseInlineFormSet để tự động đặt EPISODE cho form 90 ngày - GIỐNG HỆT FORM 28
class BaseRehospitalization90FormSet(forms.BaseInlineFormSet):
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
        # Luôn lưu các form hiện có để tránh mất dữ liệu
        return super().save_existing(form, instance, commit)


class BaseFollowUpAntibiotic90FormSet(forms.BaseInlineFormSet):
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
        # Luôn lưu các form hiện có để tránh mất dữ liệu
        return super().save_existing(form, instance, commit)


# FormSet cho chế độ chỉnh sửa (có extra form) - GIỐNG HỆT FORM 28
Rehospitalization90FormSet = forms.inlineformset_factory(
    FollowUpCase90,
    Rehospitalization90,
    form=Rehospitalization90Form,
    formset=BaseRehospitalization90FormSet,
    extra=1,
    can_delete=True,
    validate_min=False,
    validate_max=False,
    fields=['EPISODE', 'REHOSPDATE', 'REHOSPLOCATION', 'REHOSPREASONFOR', 'REHOSPSTAYDUR']
)


# FormSet cho chế độ chỉ xem (không có extra form) - GIỐNG HỆT FORM 28
Rehospitalization90FormSetReadOnly = forms.inlineformset_factory(
    FollowUpCase90,
    Rehospitalization90,
    form=Rehospitalization90Form,
    extra=0,  # KHÔNG có form trống
    can_delete=False,
    fields=['EPISODE', 'REHOSPDATE', 'REHOSPLOCATION', 'REHOSPREASONFOR', 'REHOSPSTAYDUR']
)


# Tương tự cho Antibiotic - GIỐNG HỆT FORM 28
FollowUpAntibiotic90FormSet = forms.inlineformset_factory(
    FollowUpCase90,
    FollowUpAntibiotic90,
    form=FollowUpAntibiotic90Form,
    formset=BaseFollowUpAntibiotic90FormSet,
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
    extra=0,  # KHÔNG có form trống
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
    """Form cho DischargeICD model theo style của RehospitalizationForm"""
    
    class Meta:
        model = DischargeICD
        fields = ['EPISODE', 'ICDCODE', 'ICDDETAIL']
        
        widgets = {
            'EPISODE': forms.NumberInput(attrs={
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
        self.fields['EPISODE'].required = False
        
        # Labels chi tiết hơn - GIỐNG pattern cũ
        self.fields['EPISODE'].label = _('Thứ tự')
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
    fields=['EPISODE', 'ICDCODE', 'ICDDETAIL']
)


# FormSet cho chế độ chỉ xem (không có extra form) - GIỐNG pattern cũ
DischargeICDFormSetReadOnly = forms.inlineformset_factory(
    DischargeCase,
    DischargeICD,
    form=DischargeICDForm,
    extra=0,  # KHÔNG có form trống
    can_delete=False,
    fields=['EPISODE', 'ICDCODE', 'ICDDETAIL']
)


from .models import ContactSampleCollection

class ContactSampleCollectionForm(forms.ModelForm):
    class Meta:
        model = ContactSampleCollection
        exclude = ('contact_case',)
        widgets = {
            'sample_type': forms.RadioSelect(),
            # Lần 1 (không suffix)
            'SAMPLE1': forms.RadioSelect(choices=((True, _('Có')), (False, _('Không')))),
            'REASONIFNO': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Vui lòng ghi rõ lý do không thu nhận được mẫu')}),
            'STOOLDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'THROATSWABDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'RECTSWABDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'BLOODDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'CULTRESSTOOL': forms.RadioSelect(),
            'CULTRESRECTSWAB': forms.RadioSelect(),
            'CULTRESTHROATSWAB': forms.RadioSelect(),
            'OTHERRESSPECIFY': forms.TextInput(attrs={'class': 'form-control'}),
            'OTHERRESSPECIFY_2': forms.TextInput(attrs={'class': 'form-control'}),
            # Lần 3 (suffix _3)
            'SAMPLE3': forms.RadioSelect(choices=((True, _('Có')), (False, _('Không')))),
            'REASONIFNO_3': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Vui lòng ghi rõ lý do không thu nhận được mẫu lần 3')}),
            'STOOLDATE_3': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'THROATSWABDATE_3': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'RECTSWABDATE_3': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'CULTRESSTOOL_3': forms.RadioSelect(),
            'CULTRESRECTSWAB_3': forms.RadioSelect(),
            'CULTRESTHROATSWAB_3': forms.RadioSelect(),
            'OTHERRESSPECIFY_5': forms.TextInput(attrs={'class': 'form-control'}),
            'OTHERRESSPECIFY_6': forms.TextInput(attrs={'class': 'form-control'}),
            # Lần 4 (suffix _4)
            'SAMPLE4': forms.RadioSelect(choices=((True, _('Có')), (False, _('Không')))),
            'REASONIFNO_4': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Vui lòng ghi rõ lý do không thu nhận được mẫu lần 4')}),
            'STOOLDATE_4': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'THROATSWABDATE_4': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'RECTSWABDATE_4': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'CULTRESSTOOL_4': forms.RadioSelect(),
            'CULTRESRECTSWAB_4': forms.RadioSelect(),
            'CULTRESTHROATSWAB_4': forms.RadioSelect(),
            'OTHERRESSPECIFY_7': forms.TextInput(attrs={'class': 'form-control'}),
            'OTHERRESSPECIFY_8': forms.TextInput(attrs={'class': 'form-control'}),
            # Chung
            'COMPLETEDDATE': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'COMPLETEDBY': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Thay đổi giao diện cho các trường boolean thành CheckboxInput - GIỐNG
        boolean_fields = [
            'STOOL', 'THROATSWAB', 'RECTSWAB', 'BLOOD',
            'KLEBPNEU', 'OTHERRES', 'KLEBPNEU_2', 'OTHERRES_2',
            'STOOL_3', 'THROATSWAB_3', 'RECTSWAB_3',
            'KLEBPNEU_5', 'OTHERRES_5', 'KLEBPNEU_6', 'OTHERRES_6',
            'STOOL_4', 'THROATSWAB_4', 'RECTSWAB_4',
            'KLEBPNEU_7', 'OTHERRES_7', 'KLEBPNEU_8', 'OTHERRES_8',
        ]
        for field_name in boolean_fields:
            if field_name in self.fields:
                self.fields[field_name].widget = forms.CheckboxInput(attrs={'class': 'form-check-input'})

        # Đặt initial cho COMPLETEDDATE nếu chưa có - GIỐNG
        if not self.initial.get('COMPLETEDDATE'):
            self.initial['COMPLETEDDATE'] = date.today()

        # Logic ẩn BLOOD/BLOODDATE nếu không phải lần 1
        if self.instance.sample_type != '1':
            if 'BLOOD' in self.fields:
                del self.fields['BLOOD']
            if 'BLOODDATE' in self.fields:
                del self.fields['BLOODDATE']

        # Làm COMPLETEDDATE không required (fix lỗi "This field is required.")
        self.fields['COMPLETEDDATE'].required = False

    def clean_COMPLETEDDATE(self):
        completed_date = self.cleaned_data.get('COMPLETEDDATE')
        if not completed_date:  # Nếu empty, set default
            return date.today()
        return completed_date



class ContactFollowUp28Form(forms.ModelForm):
    """Form cho ContactFollowUp28 model"""
    
    class Meta:
        model = ContactFollowUp28
        fields = [
            'FU28ASSESSED', 'FU28ASSESSDATE',
            'HOSP2D6M', 'DIAL3M', 'CATHETER3M', 'SONDE3M', 
            'HOMEWOUNDCARE', 'LONGTERMCAREFACILITY',
            'MEDICATIONUSE', 'COMPLETEDBY', 'COMPLETEDDATE'
        ]
        widgets = {
            'FU28ASSESSED': forms.Select(attrs={'class': 'form-control'}),
            'FU28ASSESSDATE': forms.DateInput(attrs={
                'class': 'form-control datepicker',
                'autocomplete': 'off',
                'placeholder': 'DD/MM/YYYY'
            }),
            'COMPLETEDDATE': forms.DateInput(attrs={
                'class': 'form-control datepicker',
                'autocomplete': 'off',
                'placeholder': 'DD/MM/YYYY'
            }),
            'COMPLETEDBY': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set choices for FU28ASSESSED
        self.fields['FU28ASSESSED'].choices = [
            ('', '-- Chọn --'),
            ('Yes', 'Có'),
            ('No', 'Không'),
            ('NA', 'Không áp dụng'),
        ]


class ContactFollowUp90Form(forms.ModelForm):
    """Form cho ContactFollowUp90 model"""
    
    class Meta:
        model = ContactFollowUp90
        fields = [
            'FU90ASSESSED', 'FU90ASSESSDATE',
            'HOSP2D6M_90', 'DIAL3M_90', 'CATHETER3M_90', 'SONDE3M_90', 
            'HOMEWOUNDCARE_90', 'LONGTERMCAREFACILITY_90',
            'MEDICATIONUSE_90', 'COMPLETEDBY', 'COMPLETEDDATE'
        ]
        widgets = {
            'FU90ASSESSED': forms.Select(attrs={'class': 'form-control'}),
            'FU90ASSESSDATE': forms.DateInput(attrs={
                'class': 'form-control datepicker',
                'autocomplete': 'off',
                'placeholder': 'DD/MM/YYYY'
            }),
            'COMPLETEDDATE': forms.DateInput(attrs={
                'class': 'form-control datepicker',
                'autocomplete': 'off',
                'placeholder': 'DD/MM/YYYY'
            }),
            'COMPLETEDBY': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set choices for FU90ASSESSED
        self.fields['FU90ASSESSED'].choices = [
            ('', '-- Chọn --'),
            ('Yes', 'Có'),
            ('No', 'Không'),
            ('NA', 'Không áp dụng'),
        ]


class ContactMedicationHistoryForm(forms.ModelForm):
    """Form cho ContactMedicationHistory model"""
    
    class Meta:
        model = ContactMedicationHistory
        fields = ['medication_name', 'dosage', 'usage_period', 'reason']
        widgets = {
            'medication_name': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Tên thuốc'
            }),
            'dosage': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Liều dùng'
            }),
            'usage_period': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Thời gian sử dụng'
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control form-control-sm',
                'rows': 2,
                'placeholder': 'Lý do sử dụng'
            }),
        }


# FormSets cho medication history
ContactMedicationHistoryFormSet = forms.inlineformset_factory(
    ContactFollowUp28,
    ContactMedicationHistory,
    form=ContactMedicationHistoryForm,
    extra=1,
    can_delete=True,
    fields=['medication_name', 'dosage', 'usage_period', 'reason']
)

ContactMedicationHistory90FormSet = forms.inlineformset_factory(
    ContactFollowUp90,
    ContactMedicationHistory,
    form=ContactMedicationHistoryForm,
    extra=1,
    can_delete=True,
    fields=['medication_name', 'dosage', 'usage_period', 'reason']
)


# Custom FormSet cho medication history với validation
class BaseContactMedicationHistoryFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        # Kiểm tra ít nhất một thuốc được nhập
        has_data = False
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                if form.cleaned_data.get('medication_name'):
                    has_data = True
                    break
        
        # Nếu có form được submit nhưng không có dữ liệu thuốc
        if self.forms and not has_data:
            raise forms.ValidationError("Vui lòng nhập ít nhất một loại thuốc.")


ContactMedicationHistoryFormSet = forms.inlineformset_factory(
    ContactFollowUp28,
    ContactMedicationHistory,
    form=ContactMedicationHistoryForm,
    formset=BaseContactMedicationHistoryFormSet,
    extra=1,
    can_delete=True,
    fields=['medication_name', 'dosage', 'usage_period', 'reason']
)

ContactMedicationHistory90FormSet = forms.inlineformset_factory(
    ContactFollowUp90,
    ContactMedicationHistory,
    form=ContactMedicationHistoryForm,
    formset=BaseContactMedicationHistoryFormSet,
    extra=1,
    can_delete=True,
    fields=['medication_name', 'dosage', 'usage_period', 'reason']
)