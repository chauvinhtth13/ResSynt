# from django.db import models
# from django.utils.translation import gettext_lazy as _
# from django.db.models import JSONField
# from datetime import datetime, date, timedelta
# import json
# from django.utils import timezone
# from django.contrib.auth.models import User
# from django.contrib.postgres.fields import ArrayField
# import json
# from encrypted_model_fields.fields import EncryptedCharField

# from utils.audit_log_utils import safe_json_loads

# class ScreeningCase(models.Model):
#     SCRID = models.CharField(_("Mã sàng lọc"), max_length=50, primary_key=True)
#     USUBJID = models.CharField(_("USUBJID"), max_length=50, unique=True) 
#     STUDYID = models.CharField(_("Mã nghiên cứu"), max_length=50)
#     SITEID = models.CharField(_("Mã cơ sở"), max_length=20)
#     SUBJID = models.CharField(_("Mã bệnh nhân"), max_length=50)
#     INITIAL = models.CharField(_("Viết tắt"), max_length=10)
#     UPPER16AGE = models.BooleanField(_("Trên 16 tuổi"))
#     INFPRIOR2OR48HRSADMIT = models.BooleanField(_("Nhiễm trùng trước nhập viện 2 hoặc 48 giờ"))
#     ISOLATEDKPNFROMINFECTIONORBLOOD = models.BooleanField(_("Phân lập KPN từ nhiễm trùng hoặc máu"))
#     KPNISOUNTREATEDSTABLE = models.BooleanField(_("KPN chưa điều trị, ổn định"))
#     CONSENTTOSTUDY = models.BooleanField(_("Đồng ý tham gia nghiên cứu"))
#     SCREENINGFORMDATE = models.DateField(_("Ngày điền phiếu sàng lọc"), null=True, blank=True)
#     COMPLETEDBY = models.CharField(_("Người hoàn thành"), max_length=50, null=True, blank=True)
#     COMPLETEDDATE = models.DateField(_("Ngày hoàn thành"), null=True, blank=True)
#     ENTRY = models.IntegerField(_("Entry"), null=True, blank=True)
#     ENTEREDTIME = models.DateTimeField(_("Thời gian nhập"), null=True, blank=True)
#     CONFIRMED = models.BooleanField(_("Đã xác nhận"), null=True, blank=True)
#     UNRECRUITED_REASON = models.CharField(_("Lý do không tuyển"), max_length=255, null=True, blank=True)
#     WARD = models.CharField(_("Khoa/Phòng"), max_length=255, null=True, blank=True)
#     is_confirmed = models.BooleanField(_("Đã xác nhận"), default=False)

#     def save(self, *args, **kwargs):
#         if not self.SCRID:
#             import re
#             all_ids = ScreeningCase.objects.values_list('SCRID', flat=True)
#             max_num = 0
#             for sid in all_ids:
#                 m = re.match(r'PS(\d+)', str(sid))
#                 if m:
#                     num = int(m.group(1))
#                     if num > max_num:
#                         max_num = num
#             self.SCRID = f"PS{max_num + 1:04d}"
#         super().save(*args, **kwargs)

#         create_usubjid = False
#         # Chỉ sinh SUBJID và USUBJID khi đủ điều kiện và đồng ý tham gia nghiên cứu
#         if (
#             self.UPPER16AGE and self.INFPRIOR2OR48HRSADMIT and
#             self.ISOLATEDKPNFROMINFECTIONORBLOOD and not self.KPNISOUNTREATEDSTABLE and
#             self.CONSENTTOSTUDY
#         ):
#             # Sinh SUBJID nếu chưa có
#             if not self.SUBJID:
#                 # Tìm SUBJID lớn nhất dạng A-xxx trong site này
#                 last_case = (
#                     ScreeningCase.objects
#                     .filter(SITEID=self.SITEID)
#                     .exclude(SUBJID__isnull=True)
#                     .exclude(SUBJID__exact='')
#                     .filter(SUBJID__startswith='A-')
#                     .order_by('-SUBJID')
#                     .first()
#                 )
#                 if last_case and last_case.SUBJID and last_case.SUBJID.startswith('A-'):
#                     try:
#                         last_number = int(last_case.SUBJID.split('-')[-1])
#                         next_number = last_number + 1
#                     except (ValueError, IndexError):
#                         next_number = 1
#                 else:
#                     next_number = 1
#                 self.SUBJID = f"A-{next_number:03d}"

#             # Sinh USUBJID nếu chưa có
#             if not self.USUBJID:
#                 create_usubjid = True
#                 if not self.SITEID or not self.SUBJID:
#                     raise ValueError("SITEID và SUBJID phải được cung cấp để tạo USUBJID")
#                 self.USUBJID = f"{self.SITEID}-{self.SUBJID}"
#                 # Đảm bảo không trùng USUBJID
#                 while ScreeningCase.objects.filter(USUBJID=self.USUBJID).exclude(pk=self.pk).exists():
#                     # Nếu trùng, tăng số thứ tự SUBJID lên
#                     try:
#                         subjid_number = int(self.SUBJID.split('-')[-1])
#                     except (ValueError, IndexError):
#                         subjid_number = 1
#                     subjid_number += 1
#                     self.SUBJID = f"A-{subjid_number:03d}"
#                     self.USUBJID = f"{self.SITEID}-{self.SUBJID}"

#             self.is_confirmed = True
#         else:
#             # Nếu chưa đủ điều kiện, SUBJID và USUBJID phải để trống
#             self.SUBJID = None
#             self.USUBJID = None
#             self.is_confirmed = False

#         super().save(*args, **kwargs)
#         return create_usubjid
    
#     def __str__(self):
#         return self.USUBJID if self.USUBJID else f"PS{self.SCRID}"
    
# class EnrollmentCase(models.Model):
#     """
#     Mô hình lưu trữ thông tin bệnh nhân tham gia nghiên cứu 43EN-KPN 
#     sau khi đã qua sàng lọc và đủ điều kiện
#     """
#     # PK là USUBJID từ ScreeningCase - thêm to_field để chỉ định rõ
#     USUBJID = models.OneToOneField(
#         'study_43en.ScreeningCase', 
#         on_delete=models.CASCADE, 
#         primary_key=True,
#         to_field='USUBJID',
#         verbose_name=_("USUBJID")
#     )
    
    
#     # Thông tin chung
#     FULLNAME = EncryptedCharField(_("Họ và tên"), max_length=100, null=True, blank=True)
#     ENRDATE = models.DateField(_("Ngày tuyển bệnh nhân"), null=True, blank=True)
#     RECRUITDEPT = models.CharField(_("Khoa tuyển bệnh nhân"), max_length=50, null=True, blank=True)
#     DAYOFBIRTH = models.IntegerField(_("Ngày sinh"), null=True, blank=True)
#     MONTHOFBIRTH = models.IntegerField(_("Tháng sinh"), null=True, blank=True)
#     YEAROFBIRTH = models.IntegerField(_("Năm sinh"), null=True, blank=True)
#     AGEIFDOBUNKNOWN = models.FloatField(_("Tuổi (nếu không biết ngày sinh)"), null=True, blank=True)
#     SEX = models.CharField(_("Giới tính"), max_length=10, choices=[
#         ('Male', _('Nam')), 
#         ('Female', _('Nữ')), 
#         ('Other', _('Khác'))
#     ], null=True, blank=True)
#     ETHNICITY = models.CharField(_("Dân tộc"), max_length=50, null=True, blank=True)
#     # SPECIFYIFOTHERETHNI = models.CharField(_("Chi tiết dân tộc khác"), max_length=100, null=True, blank=True)
#     MEDRECORDID = EncryptedCharField(_("Mã hồ sơ y tế"), max_length=50, null=True, blank=True)
#     OCCUPATION = models.CharField(_("Nghề nghiệp"), max_length=100, null=True, blank=True)
    
#     # Thông tin nhập viện
#     FROMOTHERHOSPITAL = models.BooleanField(_("Chuyển từ bệnh viện khác"), default=False)
#     PRIORHOSPIADMISDATE = models.DateField(_("Ngày nhập viện trước"), null=True, blank=True)
#     HEALFACILITYNAME = models.CharField(_("Tên cơ sở y tế trước"), max_length=100, null=True, blank=True)
#     REASONFORADM = models.TextField(_("Lý do nhập viện"), null=True, blank=True)
    
#     # Địa chỉ
#     ADDRESS = EncryptedCharField(_("Địa chỉ"), max_length=255, null=True, blank=True)
#     WARD = models.CharField(_("Phường/Xã"), max_length=100, null=True, blank=True)
#     DISTRICT = models.CharField(_("Quận/Huyện"), max_length=100, null=True, blank=True)
#     PROVINCECITY = models.CharField(_("Tỉnh/Thành phố"), max_length=100, null=True, blank=True)
#     # Thông tin liên hệ
#     PHONE = EncryptedCharField(_("Điện thoại"), max_length=20, blank=True, null=True)
    
#     # Thông tin vệ sinh
#     TOILETNUM = models.FloatField(_("Số nhà vệ sinh"), null=True, blank=True)
#     SHAREDTOILET = models.BooleanField(_("Dùng chung nhà vệ sinh"), default=False)
    
#     # Thông tin nơi ở và làm việc
#     RESIDENCE_TYPE_CHOICES = [
#         ('urban', _('Đô thị')),
#         ('suburban', _('Cận đô thị')),
#         ('rural', _('Nông thôn')),
#     ]
#     RESIDENCETYPE = models.CharField(
#         _("Loại nơi cư trú"),
#         max_length=20,
#         choices=RESIDENCE_TYPE_CHOICES,
#         null=True, blank=True
#     )

#     WORKPLACE_TYPE_CHOICES = [
#         ('indoor', _('Trong nhà')),
#         ('outdoor', _('Ngoài trời')),
#     ]
#     WORKPLACETYPE = models.CharField(
#         _("Loại nơi làm việc"),
#         max_length=20,
#         choices=WORKPLACE_TYPE_CHOICES,
#         null=True, blank=True
#     )
    
#     # Yếu tố nguy cơ
#     THREE_STATE_CHOICES = [
#         ('yes', _('Có')),
#         ('no', _('Không')),
#         ('unknown', _('Không biết')),
#     ]

#     HOSP2D6M = models.CharField(_("Nhập viện ≥2 ngày trong 6 tháng qua"), max_length=10, choices=THREE_STATE_CHOICES, null=True, blank=True)
#     DIAL3M = models.CharField(_("Lọc máu trong 3 tháng qua"), max_length=10, choices=THREE_STATE_CHOICES, null=True, blank=True)
#     CATHETER3M = models.CharField(_("Đặt catheter trong 3 tháng qua"), max_length=10, choices=THREE_STATE_CHOICES, null=True, blank=True)
#     SONDE3M = models.CharField(_("Đặt sonde trong 3 tháng qua"), max_length=10, choices=THREE_STATE_CHOICES, null=True, blank=True)
#     HOMEWOUNDCARE = models.CharField(_("Chăm sóc vết thương tại nhà"), max_length=10, choices=THREE_STATE_CHOICES, null=True, blank=True)
#     LONGTERMCAREFACILITY = models.CharField(_("Ở cơ sở chăm sóc dài hạn"), max_length=10, choices=THREE_STATE_CHOICES, null=True, blank=True)
#     CORTICOIDPPI = models.CharField(_("Dùng corticoid hoặc PPI"), max_length=10, choices=THREE_STATE_CHOICES, null=True, blank=True)
    
#     # Bệnh nền - sử dụng JSONField của PostgreSQL thay vì TextField
#     UNDERLYINGCONDS = models.BooleanField(_("Có bệnh nền"), default=False)
#     LISTUNDERLYING = JSONField(_("Các bệnh nền"), default=list, null=True, blank=True)
    
#     # Mô tả khác về bệnh nền
#     OTHERDISEASESPECIFY = models.TextField(_("Chi tiết bệnh khác"), null=True, blank=True)
    
#     # Thông tin hoàn thành
#     COMPLETEDBY = models.CharField(_("Người hoàn thành"), max_length=100, null=True, blank=True)
#     COMPLETEDDATE = models.DateField(_("Ngày hoàn thành"), null=True, blank=True)

#     # Thông tin nhập dữ liệu
#     ENTRY = models.IntegerField(_("ENTRY"), null=True, blank=True)
#     ENTEREDTIME = models.DateTimeField(_("ENTEREDTIME"), null=True, blank=True)

#     # Property getters for underlying conditions
#     @property
#     def DIABETES(self):
#         return 'DIABETES' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     @property
#     def COPD(self):
#         return 'COPD' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     @property
#     def HEPATITIS(self):
#         return 'HEPATITIS' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     @property
#     def CAD(self):
#         return 'CAD' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     @property
#     def KIDNEYDISEASE(self):
#         return 'KIDNEYDISEASE' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     @property
#     def ASTHMA(self):
#         return 'ASTHMA' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     @property
#     def CIRRHOSIS(self):
#         return 'CIRRHOSIS' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     @property
#     def HYPERTENSION(self):
#         return 'HYPERTENSION' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     @property
#     def AUTOIMMUNE(self):
#         return 'AUTOIMMUNE' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     @property
#     def CANCER(self):
#         return 'CANCER' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     @property
#     def ALCOHOLISM(self):
#         return 'ALCOHOLISM' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     @property
#     def HIV(self):
#         return 'HIV' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     @property
#     def ADRENALINSUFFICIENCY(self):
#         return 'ADRENALINSUFFICIENCY' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     @property
#     def BEDRIDDEN(self):
#         return 'BEDRIDDEN' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     @property
#     def PEPTICULCER(self):
#         return 'PEPTICULCER' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     @property
#     def COLITIS_IBS(self):
#         return 'COLITIS_IBS' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     @property
#     def SENILITY(self):
#         return 'SENILITY' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     @property
#     def MALNUTRITION_WASTING(self):
#         return 'MALNUTRITION_WASTING' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     @property
#     def OTHERDISEASE(self):
#         return 'OTHERDISEASE' in self.LISTUNDERLYING if self.LISTUNDERLYING else False
    
#     def save(self, *args, **kwargs):
#         super().save(*args, **kwargs)
        
#     class Meta:
#         db_table = 'study_43en_enrollmentcase'
#         verbose_name = _("Đăng ký bệnh nhân")
#         verbose_name_plural = _("Đăng ký bệnh nhân")
    

# class MedHisDrug(models.Model):
#     ENROLLCASE = models.ForeignKey(
#         'study_43en.EnrollmentCase',
#         on_delete=models.CASCADE,
#         related_name='medhisdrug_set',
#         to_field='USUBJID',
#         db_column='ENROLLCASE_USUBJID',
#         verbose_name=_("Bệnh nhân")
#     )
#     SEQ = models.IntegerField(_("STT thuốc"), null=True, blank=True)
#     DRUGNAME = models.CharField(_("Tên thuốc"), max_length=255, null=True, blank=True)
#     DOSAGE = models.CharField(_("Liều dùng"), max_length=100, null=True, blank=True)
#     USAGETIME = models.CharField(_("Thời gian dùng"), max_length=100, null=True, blank=True)
#     USAGEREASON = models.TextField(_("Lý do dùng"), null=True, blank=True)
#     ENTRY = models.IntegerField(null=True, blank=True)
#     ENTEREDTIME = models.DateTimeField(null=True, blank=True)

#     class Meta:
#         db_table = 'study_43en_medhisdrug'
#         verbose_name = _("Lịch sử dùng thuốc")
#         verbose_name_plural = _("Lịch sử dùng thuốc")

#     def __str__(self):
#         return f"{self.ENROLLCASE} - {self.DRUGNAME}"

# class ClinicalCase(models.Model):
#     """
#     Mô hình lưu trữ thông tin lâm sàng của bệnh nhân trong nghiên cứu 43EN-KPN
#     """
#     # PK là USUBJID từ ScreeningCase - thêm to_field
#     USUBJID = models.OneToOneField(
#         'study_43en.EnrollmentCase', 
#         on_delete=models.CASCADE, 
#         primary_key=True,
#         to_field='USUBJID', 
#         verbose_name=_("USUBJID")
#     )

#     THREE_STATE_CHOICES = [
#         ('yes', 'Có'),
#         ('no', 'Không'),
#         ('unknown', 'Không biết'),
#     ]
    
#     # Thông tin chung
#     EVENT = models.CharField(_("Sự kiện"), max_length=50, default="CASE")
#     STUDYID = models.CharField(_("Study ID"), max_length=10, null=True, blank=True)
#     SITEID = models.CharField(_("Site ID"), max_length=5, null=True, blank=True)
#     SUBJID = models.CharField(_("Subject ID"), max_length=10, null=True, blank=True)
#     INITIAL = models.CharField(_("Patient Initials"), max_length=10, null=True, blank=True)
    
#     # Thông tin nhập viện
#     ADMISDATE = models.DateField(_("Ngày nhập viện"), null=True, blank=True)
#     ADMISREASON = models.TextField(_("Lý do nhập viện"), null=True, blank=True)
#     SYMPTOMONSETDATE = models.DateField(_("Ngày bắt đầu triệu chứng"), null=True, blank=True)
#     ADMISDEPT = models.CharField(_("Khoa nhập viện"), max_length=50, null=True, blank=True)
#     OUTPATIENT_ERDEPT = models.TextField(_("Khoa cấp cứu/ngoại trú"), null=True, blank=True)
#     SYMPTOMADMISDEPT = models.TextField(_("Triệu chứng khi nhập viện"), null=True, blank=True)
    
#     # Thông tin trạng thái bệnh nhân
#     AWARENESS = models.TextField(_("Tỉnh táo"), null=True, blank=True)
#     GCS = models.IntegerField(_("GCS"), null=True, blank=True)
#     EYES = models.IntegerField(_("Mắt"), null=True, blank=True)
#     MOTOR = models.IntegerField(_("Vận động"), null=True, blank=True)
#     VERBAL = models.IntegerField(_("Lời nói"), null=True, blank=True)
    
#     # Thông số sinh hiệu
#     PULSE = models.FloatField(_("Mạch"), null=True, blank=True)
#     AMPLITUDE = models.CharField(_("Biên độ"), max_length=50, null=True, blank=True)
#     CAPILLARYMOIS = models.CharField(_("Độ ẩm mao mạch"), max_length=50, null=True, blank=True)
#     CRT = models.FloatField(_("Thời gian làm đầy mao mạch"), null=True, blank=True)
#     TEMPERATURE = models.FloatField(_("Nhiệt độ"), null=True, blank=True)
#     BLOODPRESSURE_SYS = models.FloatField(_("Huyết áp tâm thu"), null=True, blank=True)
#     BLOODPRESSURE_DIAS = models.FloatField(_("Huyết áp tâm trương"), null=True, blank=True)
#     RESPRATE = models.FloatField(_("Nhịp thở"), null=True, blank=True)
#     SPO2 = models.FloatField(_("SpO2"), null=True, blank=True)
#     FIO2 = models.FloatField(_("FiO2"), null=True, blank=True)
    
#     # Hô hấp
#     RESPPATTERN = models.CharField(_("Kiểu thở"), max_length=50, null=True, blank=True)
#     RESPPATTERNOTHERSPEC = models.TextField(_("Chi tiết kiểu thở khác"), null=True, blank=True)
#     RESPSUPPORT = models.CharField(_("Hỗ trợ hô hấp"), max_length=50, null=True, blank=True)
    
#     # Các thông số đánh giá
#     VASOMEDS = models.BooleanField(_("Thuốc vận mạch"), default=False)
#     HYPOTENSION = models.BooleanField(_("Hạ huyết áp"), default=False)
#     QSOFA = models.IntegerField(_("qSOFA"), null=True, blank=True)
#     NEWS2 = models.CharField(_("NEWS2"), max_length=50, null=True, blank=True)
    
#     # Các triệu chứng nhóm 1 - sử dụng JSONField của PostgreSQL thay vì TextField
#     LISTBASICSYMTOMS = JSONField(_("Triệu chứng nhóm 1"), default=list, null=True, blank=True)

#     # Các triệu chứng khác nhóm 1
#     OTHERSYMPTOM = models.BooleanField(_("Triệu chứng khác"), default=False)
#     SPECIFYOTHERSYMPTOM = models.TextField(_("Chi tiết triệu chứng khác"), null=True, blank=True)
    
#     # Chỉ số thể chất
#     WEIGHT = models.FloatField(_("Cân nặng (kg)"), null=True, blank=True)
#     HEIGHT = models.FloatField(_("Chiều cao (cm)"), null=True, blank=True)
#     BMI = models.FloatField(_("BMI"), null=True, blank=True)
    
#     # Các triệu chứng nhóm 2 - sử dụng JSONField của PostgreSQL thay vì TextField
#     LISTCLINISYMTOMS = JSONField(_("Triệu chứng nhóm 2"), default=list, null=True, blank=True)
    
#     # Các triệu chứng khác nhóm 2
#     OTHERSYMPTOM_2 = models.BooleanField(_("Triệu chứng khác (nhóm 2)"), default=False)
#     SPECIFYOTHERSYMPTOM_2 = models.TextField(_("Chi tiết triệu chứng khác (nhóm 2)"), null=True, blank=True)
    
#     TOTALCULTURERES = models.IntegerField(_("Tổng số kết quả nuôi cấy"), null=True, blank=True)

#     # Thông tin nhiễm khuẩn và kháng sinh - phần mới từ INFECTFOCUS48H
#     INFECTFOCUS48H_CHOICES = [
#         ('AbdAbscess', _('Áp xe ổ bụng')),
#         ('Empyema', _('Tràn mủ màng phổi')),
#         ('Meningitis', _('Viêm mủ nội nhãn')),
#         ('NTTKTW', _('NTTKTW')),
#         ('Peritonitis', _('Viêm phúc mạc')),
#         ('Osteomyelitis', _('Viêm xương/tủy xương')),
#         ('Other', _('Khác')),
#         ('Pneumonia', _('Viêm phổi/Áp xe phổi')),
#         ('SoftTissue', _('Da/mô mềm')),
#         ('Unk', _('Không rõ')),
#         ('UTI', _('Nhiễm trùng tiết niệu')),
#     ]
#     INFECTFOCUS48H = models.CharField(_("Nguồn nhiễm khuẩn sau 48 giờ"), max_length=50, 
#                                      choices=INFECTFOCUS48H_CHOICES, null=True, blank=True)
#     SPECIFYOTHERINFECT48H = models.TextField(_("Chi tiết nguồn nhiễm khác"), null=True, blank=True)
#     BLOODINFECT = models.CharField(_("Nhiễm khuẩn huyết"), max_length=10, choices=THREE_STATE_CHOICES, null=True, blank=True)
#     SOFABASELINE = models.IntegerField(_("Điểm SOFA nền"), null=True, blank=True)
#     DIAGSOFA = models.IntegerField(_("Điểm SOFA lúc chẩn đoán"), null=True, blank=True)
#     SEPTICSHOCK = models.CharField(_("Sốc nhiễm khuẩn"), max_length=10, choices=THREE_STATE_CHOICES, null=True, blank=True)
    
#     INFECTSRC_CHOICES = [
#         ('Community', _('Cộng đồng')),
#         ('HealthcareAssociated', _('Liên quan đến chăm sóc y tế')),
#     ]
#     INFECTSRC = models.CharField(_("Nguồn nhiễm"), max_length=50, 
#                                choices=INFECTSRC_CHOICES, null=True, blank=True)
    
#     # Thông tin hỗ trợ hô hấp
#     RESPISUPPORT = models.BooleanField(_("Hỗ trợ hô hấp"), default=False)
#     SUPPORTTYPE_CHOICES = [
#         ('Oxy mũi/mask', _('Oxy mũi/mask')),
#         ('HFNC/NIV', _('HFNC/NIV')),
#         ('Thở máy', _('Thở máy')),
#     ]

#     SUPPORTTYPE = ArrayField(
#         models.CharField(max_length=50, choices=SUPPORTTYPE_CHOICES),
#         verbose_name=_("Loại hỗ trợ"),
#         default=list,
#         blank=True,
#         null=True
#     )

#     OXYMASKDURATION = models.IntegerField(_("Thời gian sử dụng mặt nạ oxy (ngày)"), null=True, blank=True)
#     HFNCNIVDURATION = models.IntegerField(_("Thời gian sử dụng HFNC/NIV (ngày)"), null=True, blank=True)
#     VENTILATORDURATION = models.IntegerField(_("Thời gian sử dụng máy thở (ngày)"), null=True, blank=True)

#     # Thông tin dịch truyền
#     RESUSFLUID = models.BooleanField(_("Dịch truyền hồi sức"), default=False)
#     FLUID_CHOICES = [
#         ('Crystal', _('Tinh thể')),
#         ('Colloid', _('Keo')),
#     ]
#     FLUID6HOURS = models.CharField(_("Loại dịch truyền 6 giờ"), max_length=50, 
#                                  choices=FLUID_CHOICES, null=True, blank=True)
#     CRYSTAL6HRS = models.FloatField(_("Lượng dịch tinh thể 6 giờ (ml)"), null=True, blank=True)
#     COL6HRS = models.FloatField(_("Lượng dịch keo 6 giờ (ml)"), null=True, blank=True)
#     FLUID24HOURS = models.CharField(_("Loại dịch truyền 24 giờ"), max_length=50, 
#                                   choices=FLUID_CHOICES, null=True, blank=True)
#     CRYSTAL24HRS = models.FloatField(_("Lượng dịch tinh thể 24 giờ (ml)"), null=True, blank=True)
#     COL24HRS = models.FloatField(_("Lượng dịch keo 24 giờ (ml)"), null=True, blank=True)
    
#     # Thông tin điều trị khác
#     VASOINOTROPES = models.BooleanField(_("Sử dụng thuốc vận mạch"), default=False)
#     DIALYSIS = models.BooleanField(_("Lọc máu"), default=False)
#     DRAINAGE = models.BooleanField(_("Dẫn lưu"), default=False)
#     DRAINAGETYPE_CHOICES = [
#         ('Abscess', _('Áp xe')),
#         ('Empyema', _('Mủ màng phổi')),
#         ('Other', _('Khác')),
#     ]
#     DRAINAGETYPE = models.CharField(_("Loại dẫn lưu"), max_length=50, 
#                                   choices=DRAINAGETYPE_CHOICES, null=True, blank=True)
#     SPECIFYOTHERDRAINAGE = models.TextField(_("Chi tiết dẫn lưu khác"), null=True, blank=True)
    
#     # Thông tin kháng sinh
#     PRIORANTIBIOTIC = models.BooleanField(_("Kháng sinh trước"), default=False)
#     INITIALANTIBIOTIC = models.BooleanField(_("Kháng sinh ban đầu"), default=False)
#     INITIALABXAPPROP = models.BooleanField(_("Kháng sinh ban đầu phù hợp"), default=False)
    
#     # Thông tin hoàn thành
#     COMPLETEDBY = models.CharField(_("Người hoàn thành"), max_length=100, null=True, blank=True)
#     COMPLETEDDATE = models.DateField(_("Ngày hoàn thành"), null=True, blank=True)

#     # Thông tin nhập liệu
#     ENTRY = models.CharField(_("Người nhập liệu"), max_length=100, null=True, blank=True)
#     ENTEREDTIME = models.DateTimeField(_("Thời gian nhập liệu"), null=True, blank=True)

#     # Property getter cho từng triệu chứng cụ thể trong nhóm 1
#     @property
#     def FEVER(self):
#         return 'FEVER' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
#     @property
#     def FATIGUE(self):
#         return 'FATIGUE' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
#     @property
#     def MUSCLEPAIN(self):
#         return 'MUSCLEPAIN' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
#     @property
#     def LOSSAPPETITE(self):
#         return 'LOSSAPPETITE' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
        
#     @property
#     def COUGH(self):
#         return 'COUGH' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
#     @property
#     def CHESTPAIN(self):
#         return 'CHESTPAIN' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
#     @property
#     def SHORTBREATH(self):
#         return 'SHORTBREATH' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
        
#     @property
#     def JAUNDICE(self):
#         return 'JAUNDICE' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
#     @property
#     def PAINURINATION(self):
#         return 'PAINURINATION' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
#     @property
#     def BLOODYURINE(self):
#         return 'BLOODYURINE' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
        
#     @property
#     def CLOUDYURINE(self):
#         return 'CLOUDYURINE' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
#     @property
#     def EPIGASTRICPAIN(self):
#         return 'EPIGASTRICPAIN' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
#     @property
#     def LOWERABDPAIN(self):
#         return 'LOWERABDPAIN' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
        
#     @property
#     def FLANKPAIN(self):
#         return 'FLANKPAIN' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
#     @property
#     def URINARYHESITANCY(self):
#         return 'URINARYHESITANCY' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
#     @property
#     def SUBCOSTALPAIN(self):
#         return 'SUBCOSTALPAIN' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
        
#     @property
#     def HEADACHE(self):
#         return 'HEADACHE' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
#     @property
#     def POORCONTACT(self):
#         return 'POORCONTACT' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
#     @property
#     def DELIRIUMAGITATION(self):
#         return 'DELIRIUMAGITATION' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
        
#     @property
#     def VOMITING(self):
#         return 'VOMITING' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
#     @property
#     def SEIZURES(self):
#         return 'SEIZURES' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
#     @property
#     def EYEPAIN(self):
#         return 'EYEPAIN' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
        
#     @property
#     def REDEYES(self):
#         return 'REDEYES' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
#     @property
#     def NAUSEA(self):
#         return 'NAUSEA' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
#     @property
#     def BLURREDVISION(self):
#         return 'BLURREDVISION' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
        
#     @property
#     def SKINLESIONS(self):
#         return 'SKINLESIONS' in self.LISTBASICSYMTOMS if self.LISTBASICSYMTOMS else False
    
#     # Property getter cho từng triệu chứng cụ thể trong nhóm 2
#     @property
#     def FEVER_2(self):
#         return 'FEVER_2' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     @property
#     def RASH(self):
#         return 'RASH' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     @property
#     def SKINBLEEDING(self):
#         return 'SKINBLEEDING' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     @property
#     def MUCOSALBLEEDING(self):
#         return 'MUCOSALBLEEDING' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
        
#     @property
#     def SKINLESIONS_2(self):
#         return 'SKINLESIONS_2' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     @property
#     def LUNGCRACKLES(self):
#         return 'LUNGCRACKLES' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     @property
#     def CONSOLIDATIONSYNDROME(self):
#         return 'CONSOLIDATIONSYNDROME' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
        
#     @property
#     def PLEURALEFFUSION(self):
#         return 'PLEURALEFFUSION' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     @property
#     def PNEUMOTHORAX(self):
#         return 'PNEUMOTHORAX' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     @property
#     def HEARTMURMUR(self):
#         return 'HEARTMURMUR' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
        
#     @property
#     def ABNORHEARTSOUNDS(self):
#         return 'ABNORHEARTSOUNDS' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     @property
#     def JUGULARVEINDISTENTION(self):
#         return 'JUGULARVEINDISTENTION' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     @property
#     def LIVERFAILURESIGNS(self):
#         return 'LIVERFAILURESIGNS' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
        
#     @property
#     def PORTALHYPERTENSIONSIGNS(self):
#         return 'PORTALHYPERTENSIONSIGNS' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     @property
#     def HEPATOSPLENOMEGALY(self):
#         return 'HEPATOSPLENOMEGALY' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     @property
#     def CONSCIOUSNESSDISTURBANCE(self):
#         return 'CONSCIOUSNESSDISTURBANCE' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
        
#     @property
#     def LIMBWEAKNESSPARALYSIS(self):
#         return 'LIMBWEAKNESSPARALYSIS' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     @property
#     def CRANIALNERVEPARALYSIS(self):
#         return 'CRANIALNERVEPARALYSIS' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     @property
#     def MENINGEALSIGNS(self):
#         return 'MENINGEALSIGNS' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
        
#     @property
#     def REDEYES_2(self):
#         return 'REDEYES_2' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     @property
#     def HYPOPYON(self):
#         return 'HYPOPYON' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     @property
#     def EDEMA(self):
#         return 'EDEMA' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
        
#     @property
#     def CUSHINGOIDAPPEARANCE(self):
#         return 'CUSHINGOIDAPPEARANCE' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     @property
#     def EPIGASTRICPAIN_2(self):
#         return 'EPIGASTRICPAIN_2' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     @property
#     def LOWERABDPAIN_2(self):
#         return 'LOWERABDPAIN_2' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
        
#     @property
#     def FLANKPAIN_2(self):
#         return 'FLANKPAIN_2' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     @property
#     def SUBCOSTALPAIN_2(self):
#         return 'SUBCOSTALPAIN_2' in self.LISTCLINISYMTOMS if self.LISTCLINISYMTOMS else False
    
#     def __str__(self):
#         return f"Clinical Case: {self.USUBJID}"
    
#     class Meta:
#         db_table = 'study_43en_clinicalcase'

# class LaboratoryTest(models.Model):
#     """
#     Mô hình lưu trữ kết quả các xét nghiệm và chẩn đoán hình ảnh của bệnh nhân
#     """
#     # Kết nối với EnrollmentCase
#     USUBJID = models.ForeignKey(
#         'study_43en.EnrollmentCase',
#         to_field='USUBJID',
#         on_delete=models.CASCADE,
#         db_column='USUBJID',
#         verbose_name=_("USUBJID"),
#     )

#     LAB_TYPE_CHOICES = (
#         ('1', _('Lần 1 (24h đầu nhập viện)')),
#         ('2', _('Lần 2 (48-72h điều trị kháng sinh ban đầu)')),
#         ('3', _('Lần 3 (trước xuất viện hoặc trong vòng 72h trước xuất viện)')),
#     )
#     LAB_TYPE = models.CharField(_('Lần xét nghiệm'), max_length=1, choices=LAB_TYPE_CHOICES)
#     # Category của xét nghiệm
#     CATEGORY_CHOICES = [
#         ('BLOOD_COAGULATION', '11. Đông máu'),
#         ('COMPLETE_BLOOD_COUNT', '12. Tổng phân tích tế bào máu'),
#         ('BIOCHEMISTRY', '13. Sinh hóa, miễn dịch'),
#         ('BLOOD_GAS_ANALYSIS', '14. Khí máu động mạch'),
#         ('LACTATE', '15. Lactate động mạch'),
#         ('URINE_ANALYSIS', '16. Tổng phân tích nước tiểu'),
#         ('PLEURAL_FLUID', '17. Dịch màng bụng'),
#         ('PLEURAL_FLUID_ANALYSIS', '18. Dịch màng phổi'),
#         ('CSF_ANALYSIS', '19. Dịch não tủy'),
#         ('CHEST_XRAY', '20. X-quang ngực thẳng'),
#         ('ABDOMINAL_ULTRASOUND', '21. Siêu âm bụng'),
#         ('BRAIN_CT_MRI', '22. CT scan so não/MRI não'),
#         ('CHEST_ABDOMEN_CT', '23. CT ngực bụng'),
#         ('ECHOCARDIOGRAPHY', '24. Siêu âm tim'),
#         ('SOFT_TISSUE_ULTRASOUND', '25. Siêu âm mô mềm'),
#     ]
    
#     # Loại xét nghiệm chi tiết trong từng category
#     TEST_TYPE_CHOICES = [
#         # 11. Đông máu
#         ('INR', 'INR'),
#         ('DIC', 'DIC'),
        
#         # 12. Tổng phân tích tế bào máu
#         ('WBC', 'Bạch cầu máu'),
#         ('NEU', 'Neu'),
#         ('LYM', 'Lym'),
#         ('EOS', 'Eos'),
#         ('RBC', 'Hồng cầu'),
#         ('HEMOGLOBIN', 'Hemoglobin'),
#         ('PLATELETS', 'Tiểu cầu'),
        
#         # 13. Sinh hóa, miễn dịch
#         ('NATRI', 'Natri máu'),
#         ('KALI', 'Kali máu'),
#         ('CLO', 'Clo máu'),
#         ('MAGNE', 'Magne máu'),
#         ('URE', 'Ure máu'),
#         ('CREATININE', 'Creatinine máu'),
#         ('AST', 'AST'),
#         ('ALT', 'ALT'),
#         ('GLUCOSEBLOOD', 'Glucose máu'),
#         ('BEDSIDE_GLUCOSE', 'Đường huyết tại giường'),
#         ('BILIRUBIN_TP', 'Bilirubin TP'),
#         ('BILIRUBIN_TT', 'Bilirubin TT'),
#         ('PROTEIN', 'Protein máu'),
#         ('ALBUMIN', 'Albumin máu'),
#         ('CRP_QUALITATIVE', 'Ceton máu định tính'),
#         ('CRP_QUANTITATIVE', 'Ceton máu định lượng'),
#         ('CRP', 'CRP'),
#         ('PROCALCITONIN', 'Procalcitonin'),
#         ('HBA1C', 'HbA1c'),
#         ('CORTISOL', 'Cortisol máu'),
#         ('HIV', 'HIV'),
#         ('CD4', 'CD4'),
        
#         # 14. Khí máu động mạch
#         ('PH', 'pH'),
#         ('PCO2', 'pCO2'),
#         ('PO2', 'pO2'),
#         ('HCO3', 'HCO3'),
#         ('BE', 'BE'),
#         ('AADO2', 'AaDO2'),
        
#         # 15. Lactate động mạch
#         ('LACTATE_ARTERIAL', 'Lactate động mạch'),
        
#         # 16. Tổng phân tích nước tiểu
#         ('URINE_PH', 'pH'),
#         ('NITRIT', 'Nitrit'),
#         ('URINE_PROTEIN', 'Protein'),
#         ('LEU', 'LEU'),
#         ('URINE_RBC', 'Hồng cầu'),
#         ('SEDIMENT', 'Cặn lắng'),
        
#         # 17. Dịch màng bụng
#         ('PERITONEAL_WBC', 'Bạch cầu'),
#         ('PERITONEAL_NEU', 'Bạch cầu đa nhân'),
#         ('PERITONEAL_MONO', 'Bạch cầu đơn nhân'),
#         ('PERITONEAL_RBC', 'Hồng cầu'),
#         ('PERITONEAL_PROTEIN', 'Protein'),
#         ('PERITONEAL_PROTEIN_BLOOD', 'Protein máu'),
#         ('PERITONEAL_ALBUMIN', 'Albumin'),
#         ('PERITONEAL_ALBUMIN_BLOOD', 'Albumin máu'),
#         ('PERITONEAL_ADA', 'ADA'),
#         ('PERITONEAL_CELLBLOCK', 'Cell block'),
        
#         # 18. Dịch màng phổi
#         ('PLEURAL_WBC', 'Bạch cầu'),
#         ('PLEURAL_NEU', 'Bạch cầu đa nhân'),
#         ('PLEURAL_MONO', 'Bạch cầu đơn nhân'),
#         ('PLEURAL_EOS', 'Eos'),
#         ('PLEURAL_RBC', 'Hồng cầu'),
#         ('PLEURAL_PROTEIN', 'Protein'),
#         ('PLEURAL_LDH', 'LDH'),
#         ('PLEURAL_LDH_BLOOD', 'LDH máu'),
#         ('PLEURAL_ADA', 'ADA'),
#         ('PLEURAL_CELLBLOCK', 'Cell block'),
        
#         # 19. Dịch não tủy
#         ('CSF_WBC', 'Bạch cầu'),
#         ('CSF_NEU', 'Bạch cầu đa nhân'),
#         ('CSF_MONO', 'Bạch cầu đơn nhân'),
#         ('CSF_EOS', 'Eos'),
#         ('CSF_RBC', 'Hồng cầu'),
#         ('CSF_PROTEIN', 'Protein'),
#         ('CSF_GLUCOSE', 'Glucose'),
#         ('CSF_LACTATE', 'Lactate'),
#         ('CSF_GRAM_STAIN', 'Nhuộm Gram'),
        
#         # 20-25. Chẩn đoán hình ảnh
#         ('CHEST_XRAY', 'X-quang ngực thẳng'),
#         ('ABDOMINAL_ULTRASOUND', 'Siêu âm bụng'),
#         ('BRAIN_CT_MRI', 'CT scan so não/MRI không'),
#         ('CHEST_ABDOMEN_CT', 'CT ngực bụng'),
#         ('ECHOCARDIOGRAPHY', 'Siêu âm tim'),
#         ('SOFT_TISSUE_ULTRASOUND', 'Siêu âm mô mềm'),
#     ]
    
#     CATEGORY = models.CharField(_("Nhóm xét nghiệm"), max_length=50, choices=CATEGORY_CHOICES)
#     TESTTYPE = models.CharField(_("Loại xét nghiệm"), max_length=50, choices=TEST_TYPE_CHOICES)
#     PERFORMED = models.BooleanField(_("Đã thực hiện"), default=False)
#     PERFORMEDDATE = models.DateField(_("Ngày thực hiện"), null=True, blank=True)
#     RESULT = models.TextField(_("Kết quả"), null=True, blank=True)

#     # Metadata
#     CREATEDAT = models.DateTimeField(auto_now_add=True)
#     UPDATEDAT = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'study_43en_laboratorytest'
#         unique_together = ['USUBJID', 'TESTTYPE', 'LAB_TYPE']
#         ordering = ['CATEGORY', 'TESTTYPE', 'LAB_TYPE']
#         verbose_name = _("Xét nghiệm")
#         verbose_name_plural = _("Các xét nghiệm")
    
#     def __str__(self):
#         return f"{self.USUBJID_id} - {self.get_TESTTYPE_display()}"

#     def save(self, *args, **kwargs):
#         # Tự động gán category dựa trên test_type
#         if not self.CATEGORY:
#             self.CATEGORY = self._get_category_from_test_type()
#         super().save(*args, **kwargs)
    
#     def _get_category_from_test_type(self):
#         """Tự động xác định category dựa trên test_type"""
#         category_mapping = {
#             # Đông máu
#             'INR': 'BLOOD_COAGULATION',
#             'DIC': 'BLOOD_COAGULATION',
            
#             # Tổng phân tích tế bào máu
#             'WBC': 'COMPLETE_BLOOD_COUNT',
#             'NEU': 'COMPLETE_BLOOD_COUNT',
#             'LYM': 'COMPLETE_BLOOD_COUNT',
#             'EOS': 'COMPLETE_BLOOD_COUNT',
#             'RBC': 'COMPLETE_BLOOD_COUNT',
#             'HEMOGLOBIN': 'COMPLETE_BLOOD_COUNT',
#             'PLATELETS': 'COMPLETE_BLOOD_COUNT',
            
#             # Sinh hóa, miễn dịch
#             'NATRI': 'BIOCHEMISTRY',
#             'KALI': 'BIOCHEMISTRY',
#             'CLO': 'BIOCHEMISTRY',
#             'MAGNE': 'BIOCHEMISTRY',
#             'URE': 'BIOCHEMISTRY',
#             'CREATININE': 'BIOCHEMISTRY',
#             'AST': 'BIOCHEMISTRY',
#             'ALT': 'BIOCHEMISTRY',
#             'GLUCOSEBLOOD': 'BIOCHEMISTRY',
#             'BEDSIDE_GLUCOSE': 'BIOCHEMISTRY',
#             'BILIRUBIN_TP': 'BIOCHEMISTRY',
#             'BILIRUBIN_TT': 'BIOCHEMISTRY',
#             'PROTEIN': 'BIOCHEMISTRY',
#             'ALBUMIN': 'BIOCHEMISTRY',
#             'CRP_QUALITATIVE': 'BIOCHEMISTRY',
#             'CRP_QUANTITATIVE': 'BIOCHEMISTRY',
#             'CRP': 'BIOCHEMISTRY',
#             'PROCALCITONIN': 'BIOCHEMISTRY',
#             'HBA1C': 'BIOCHEMISTRY',
#             'CORTISOL': 'BIOCHEMISTRY',
#             'HIV': 'BIOCHEMISTRY',
#             'CD4': 'BIOCHEMISTRY',
            
#             # Khí máu động mạch
#             'PH': 'BLOOD_GAS_ANALYSIS',
#             'PCO2': 'BLOOD_GAS_ANALYSIS',
#             'PO2': 'BLOOD_GAS_ANALYSIS',
#             'HCO3': 'BLOOD_GAS_ANALYSIS',
#             'BE': 'BLOOD_GAS_ANALYSIS',
#             'AADO2': 'BLOOD_GAS_ANALYSIS',
            
#             # Lactate động mạch
#             'LACTATE_ARTERIAL': 'LACTATE',
            
#             # Tổng phân tích nước tiểu
#             'URINE_PH': 'URINE_ANALYSIS',
#             'NITRIT': 'URINE_ANALYSIS',
#             'URINE_PROTEIN': 'URINE_ANALYSIS',
#             'LEU': 'URINE_ANALYSIS',
#             'URINE_RBC': 'URINE_ANALYSIS',
#             'SEDIMENT': 'URINE_ANALYSIS',
            
#             # Chẩn đoán hình ảnh
#             'CHEST_XRAY': 'CHEST_XRAY',
#             'ABDOMINAL_ULTRASOUND': 'ABDOMINAL_ULTRASOUND',
#             'BRAIN_CT_MRI': 'BRAIN_CT_MRI',
#             'CHEST_ABDOMEN_CT': 'CHEST_ABDOMEN_CT',
#             'ECHOCARDIOGRAPHY': 'ECHOCARDIOGRAPHY',
#             'SOFT_TISSUE_ULTRASOUND': 'SOFT_TISSUE_ULTRASOUND',
#         }
        
#         # Xử lý các trường có prefix
#         if self.TESTTYPE.startswith('PERITONEAL_'):
#             return 'PLEURAL_FLUID'
#         elif self.TESTTYPE.startswith('PLEURAL_'):
#             return 'PLEURAL_FLUID_ANALYSIS'
#         elif self.TESTTYPE.startswith('CSF_'):
#             return 'CSF_ANALYSIS'
#         else:
#             return category_mapping.get(self.TESTTYPE, 'BIOCHEMISTRY')

#     def is_imaging_test(self):
#         """Kiểm tra xem có phải là chẩn đoán hình ảnh không"""
#         imaging_categories = [
#             'CHEST_XRAY', 'ABDOMINAL_ULTRASOUND', 'BRAIN_CT_MRI', 
#             'CHEST_ABDOMEN_CT', 'ECHOCARDIOGRAPHY', 'SOFT_TISSUE_ULTRASOUND'
#         ]
#         return self.CATEGORY in imaging_categories


# class OtherTest(models.Model):
#     USUBJID = models.ForeignKey(
#         'study_43en.EnrollmentCase',
#         to_field='USUBJID',
#         on_delete=models.CASCADE,
#         db_column='USUBJID',
#         verbose_name="USUBJID"
#     )
#     SEQUENCE = models.IntegerField("Thứ tự", default=1)
#     LAB_TYPE_CHOICES = (
#         ('1', _('Lần 1 (24h đầu nhập viện)')),
#         ('2', _('Lần 2 (48-72h điều trị kháng sinh ban đầu)')),
#         ('3', _('Lần 3 (trước xuất viện hoặc trong vòng 72h trước xuất viện)')),
#     )
#     LAB_TYPE = models.CharField(_('Lần xét nghiệm'), max_length=1, choices=LAB_TYPE_CHOICES, default='1')
#     CATEGORY_CHOICES = [
#         ('OTHER', 'Xét nghiệm khác'),
#     ]
#     CATEGORY = models.CharField(_("Nhóm xét nghiệm"), max_length=50, choices=CATEGORY_CHOICES, default='OTHER')
#     OTHERTESTNAME = models.CharField("Tên xét nghiệm khác", max_length=255)
#     OTHERTESTPERFORMED = models.BooleanField("Đã thực hiện", default=False)
#     OTHERTESTDTC = models.DateField("Ngày thực hiện", null=True, blank=True)
#     OTHERTESTRESULT = models.TextField("Kết quả", null=True, blank=True)
#     entry = models.IntegerField("Entry", null=True, blank=True)
#     enteredtime = models.DateTimeField("Thời gian nhập", null=True, blank=True)

#     class Meta:
#         db_table = 'study_43en_othertest'
#         verbose_name = "Xét nghiệm khác"
#         verbose_name_plural = "Các xét nghiệm khác"
#         unique_together = ['USUBJID', 'SEQUENCE']

#     def save(self, *args, **kwargs):
#         if not self.SEQUENCE:
#             last_seq = (
#                 OtherTest.objects
#                 .filter(USUBJID=self.USUBJID)
#                 .aggregate(models.Max('SEQUENCE'))['SEQUENCE__max']
#             )
#             self.SEQUENCE = (last_seq or 0) + 1
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return f"{self.USUBJID_id} - {self.OTHERTESTNAME} - #{self.SEQUENCE}"

# class MicrobiologyCulture(models.Model):
#     """Kết quả nuôi cấy vi sinh của bệnh nhân"""
#     USUBJID = models.ForeignKey('study_43en.EnrollmentCase', to_field='USUBJID', on_delete=models.CASCADE, related_name='microbiology_cultures')

#     SPECIMENTYPE_CHOICES = [
#         ('BLOOD', 'Máu'),
#         ('URINE', 'Nước tiểu'),
#         ('PLEURAL_FLUID', 'Dịch màng bụng'),
#         ('PERITONEAL_FLUID', 'Dịch màng phổi'),
#         ('PUS', 'Đàm'),
#         ('BRONCHIAL', 'Dịch rửa phế quản'),
#         ('CSF', 'Dịch não tủy'),
#         ('WOUND', 'Dịch vết thương'),
#         ('OTHER', 'Khác')
#     ]
#     SPECIMENTYPE = models.CharField(_("Loại bệnh phẩm"), max_length=20, choices=SPECIMENTYPE_CHOICES)
#     OTHERSPECIMEN = models.CharField(_("Loại bệnh phẩm khác"), max_length=100, blank=True, null=True)

#     PERFORMEDDATE = models.DateField(_("Ngày thực hiện (nn/tt/nnnn)"), null=True, blank=True)
#     SPECIMENID = models.CharField(_("Mã số bệnh phẩm (SID)"), max_length=50, blank=True, null=True)

#     RESULT_TYPE_CHOICES = [
#         ('POSITIVE', 'Dương tính'),
#         ('NEGATIVE', 'Âm tính')
#     ]
#     RESULT = models.CharField(_("Kết quả"), max_length=20, choices=RESULT_TYPE_CHOICES, blank=True, null=True)
#     RESULTDETAILS = models.CharField(_("Chi tiết kết quả"), max_length=455, blank=True, null=True)

#     SEQUENCE = models.IntegerField(_("Thứ tự"), default=1)

#     ORDEREDBYDEPT = models.CharField(_("Khoa chỉ định"), max_length=100, blank=True, null=True)
#     DEPTDIAGSENT = models.CharField(_("Chẩn đoán gửi khoa"), max_length=255, blank=True, null=True)
#     BACSTRAINISOLDATE = models.DateField(_("Ngày phân lập vi khuẩn"), blank=True, null=True)
#     COMPLETEDBY = models.CharField(_("Người hoàn thành"), max_length=100, blank=True, null=True)
#     COMPLETEDDATE = models.DateField(_("Ngày hoàn thành"), blank=True, null=True)

#     CREATED_AT = models.DateTimeField(auto_now_add=True)
#     CREATEDAT = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'study_43en_microbiologyculture'
#         unique_together = ['USUBJID', 'SPECIMENTYPE', 'SEQUENCE']
#         ordering = ['USUBJID', 'SPECIMENTYPE', 'SEQUENCE']
#         verbose_name = _("Nuôi cấy vi sinh")
#         verbose_name_plural = _("Nuôi cấy vi sinh")

#     def save(self, *args, **kwargs):
#         if not self.SEQUENCE:
#             last_seq = (
#                 MicrobiologyCulture.objects
#                 .filter(USUBJID=self.USUBJID, SPECIMENTYPE=self.SPECIMENTYPE)
#                 .aggregate(models.Max('SEQUENCE'))['SEQUENCE__max']
#             )
#             self.SEQUENCE = (last_seq or 0) + 1
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return f"{self.get_SPECIMENTYPE_display()} - {self.USUBJID_id} - #{self.SEQUENCE}"

#     def is_positive(self):
#         """Kiểm tra xem kết quả nuôi cấy có dương tính không"""
#         return self.RESULT == 'POSITIVE'

#     def get_sensitivity_by_tier(self):
#         """Lấy các kết quả độ nhạy kháng sinh phân nhóm theo tier"""
#         if not self.is_positive():
#             return {}

#         results = {}
#         for tier, _ in AntibioticSensitivity.TIER_CHOICES:
#             sensitivities = self.antibiotic_sensitivities.filter(tier=tier).order_by('SEQUENCE')
#             results[tier] = list(sensitivities)

#         return results

#     def get_sensitivity_count(self):
#         """Đếm số kết quả độ nhạy kháng sinh đã có"""
#         return self.antibiotic_sensitivities.count()

# class AntibioticSensitivity(models.Model):
#     """
#     Kết quả độ nhạy cảm kháng sinh với mẫu nuôi cấy vi sinh dương tính
#     """
#     # Liên kết với MicrobiologyCulture
#     CULTURE = models.ForeignKey(
#         'study_43en.MicrobiologyCulture',
#         on_delete=models.CASCADE,
#         related_name='antibiotic_sensitivities'
#     )

#     TIER_CHOICES = [
#         ('TIER1', _('Tier 1')),
#         ('TIER2', _('Tier 2')),
#         ('TIER3', _('Tier 3')),
#         ('TIER4', _('Tier 4')),
#         ('COLISTIN', _('Colistin')),
#         ('URINE_ONLY', _('Chỉ dành cho nước tiểu')),
#         ('OTHER', _('Kháng sinh khác')),
#     ]
#     TIER = models.CharField(_("Nhóm kháng sinh"), max_length=20, choices=TIER_CHOICES)

#     ANTIBIOTIC_CHOICES = [
#         # Tier 1
#         ('Ampicillin', _('Ampicillin')),
#         ('Cefazolin', _('Cefazolin')),
#         ('Cefotaxime', _('Cefotaxime')),
#         ('Ceftriaxone', _('Ceftriaxone')),
#         ('AmoxicillinClavulanate', _('Amoxicillin-Clavulanate')),
#         ('AmpicillinSulbactam', _('Ampicillin-Sulbactam')),
#         ('PiperacillinTazobactam', _('Piperacillin-Tazobactam')),
#         ('Gentamicin', _('Gentamicin')),
#         ('Ciprofloxacin', _('Ciprofloxacin')),
#         ('Levofloxacin', _('Levofloxacin')),
#         ('TrimethoprimSulfamethoxazole', _('Trimethoprim-Sulfamethoxazole')),
#         # Tier 2
#         ('Cefepime', _('Cefepime')),
#         ('Imipenem', _('Imipenem')),
#         ('Meropenem', _('Meropenem')),
#         ('Cefuroxime', _('Cefuroxime')),
#         ('Ertapenem', _('Ertapenem')),
#         ('Cefoxitin', _('Cefoxitin')),
#         ('Tobramycin', _('Tobramycin')),
#         ('Amikacin', _('Amikacin')),
#         ('Cefotetan', _('Cefotetan')),
#         ('Tetracycline', _('Tetracycline')),
#         # Tier 3
#         ('Cefiderocol', _('Cefiderocol')),
#         ('CeftazidimeAvibactam', _('Ceftazidime-Avibactam')),
#         ('ImipenemRelebactam', _('Imipenem-Relebactam')),
#         ('MeropenemVaborbactam', _('Meropenem-Vaborbactam')),
#         ('Plazomicin', _('Plazomicin')),
#         # Tier 4
#         ('Aztreonam', _('Aztreonam')),
#         ('Ceftaroline', _('Ceftaroline')),
#         ('Ceftazidime', _('Ceftazidime')),
#         ('CeftolozaneTazobactam', _('Ceftolozane-Tazobactam')),
#         # Colistin
#         ('Colistin', _('Colistin')),
#         # Urine Only
#         ('Cefazolin_Urine', _('Cefazolin (Nước tiểu)')),
#         ('Nitrofurantoin', _('Nitrofurantoin')),
#         ('Fosfomycin', _('Fosfomycin')),
#         # Các kháng sinh khác phổ biến
#         ('Ceftriazone', _('Ceftriazone')),
#         ('Tigecycline', _('Tigecycline')),
#         ('TicarcillinClavulanic', _('Ticarcillin-Clavulanic')),
#         ('CefoperazoneSulbactam', _('Cefoperazone-Sulbactam')),
#         ('OTHER', _('Kháng sinh khác')),
#     ]
#     ANTIBIOTIC_NAME = models.CharField(_("Tên kháng sinh"), max_length=50, choices=ANTIBIOTIC_CHOICES)
#     OTHER_ANTIBIOTIC_NAME = models.CharField(_("Tên kháng sinh khác"), max_length=100, null=True, blank=True)

#     SENSITIVITY_CHOICES = [
#         ('S', _('Nhạy cảm (S)')),
#         ('I', _('Trung gian (I)')),
#         ('R', _('Kháng thuốc (R)')),
#         ('ND', _('Không xác định (ND)')),
#         ('U', _('Không biết (U)')),
#     ]
#     SENSITIVITY_LEVEL = models.CharField(_("Mức độ nhạy cảm"), max_length=2, choices=SENSITIVITY_CHOICES, default='ND')

#     IZDIAM= models.CharField(_("Đường kính vòng vô khuẩn (mm)"), max_length=10, null=True, blank=True)
#     MIC = models.CharField(_("MIC"), max_length=10, null=True, blank=True)
#     SEQUENCE = models.IntegerField(_("Thứ tự"), default=1)

#     CREATED_AT = models.DateTimeField(auto_now_add=True)
#     UPDATED_AT = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'study_43en_antibioticsensitivity'
#         ordering = ['TIER', 'SEQUENCE', 'ANTIBIOTIC_NAME']
#         verbose_name = _("Kết quả nhạy cảm kháng sinh")
#         verbose_name_plural = _("Kết quả nhạy cảm kháng sinh")
#         unique_together = ['CULTURE', 'ANTIBIOTIC_NAME', 'OTHER_ANTIBIOTIC_NAME']

#     def __str__(self):
#         antibiotic_display = self.get_antibiotic_display_name()
#         return f"{antibiotic_display} - {self.get_SENSITIVITY_LEVEL_display()}"

#     def get_antibiotic_display_name(self):
#         """Trả về tên hiển thị của kháng sinh"""
#         if self.ANTIBIOTIC_NAME == 'OTHER':
#             return self.OTHER_ANTIBIOTIC_NAME or _("Kháng sinh khác")
#         return dict(self.ANTIBIOTIC_CHOICES).get(self.ANTIBIOTIC_NAME, self.ANTIBIOTIC_NAME)


# class PriorAntibiotic(models.Model):
#     """Model for prior antibiotics data"""
#     USUBJID = models.ForeignKey('study_43en.EnrollmentCase',to_field='USUBJID', on_delete=models.CASCADE, related_name='prior_antibiotics')
#     PRIORANTIBIONAME = models.CharField(_("Tên kháng sinh trước"), max_length=100, null=True, blank=True)
#     PRIORANTIBIODOSAGE = models.CharField(_("Liều kháng sinh trước"), max_length=100, null=True, blank=True)
#     PRIORANTIBIOSTARTDTC = models.DateField(_("Ngày bắt đầu kháng sinh trước"), null=True, blank=True)
#     PRIORANTIBIOENDDTC = models.DateField(_("Ngày kết thúc kháng sinh trước"), null=True, blank=True)

#     def __str__(self):
#         return f"{self.PRIORANTIBIONAME} - {self.PRIORANTIBIODOSAGE}"

#     class Meta:
#         db_table = 'study_43en_priorantibiotic'
#         verbose_name = _("Kháng sinh trước")
#         verbose_name_plural = _("Kháng sinh trước")


# class InitialAntibiotic(models.Model):
#     """Model for initial antibiotics data"""
#     USUBJID = models.ForeignKey('study_43en.EnrollmentCase',to_field='USUBJID', on_delete=models.CASCADE, related_name='initial_antibiotics')
#     INITIALANTIBIONAME = models.CharField(_("Tên kháng sinh ban đầu"), max_length=100, null=True, blank=True)
#     INITIALANTIBIODOSAGE = models.CharField(_("Liều kháng sinh ban đầu"), max_length=100, null=True, blank=True)
#     INITIALANTIBIOSTARTDTC = models.DateField(_("Ngày bắt đầu kháng sinh ban đầu"), null=True, blank=True)
#     INITIALANTIBIOENDDTC = models.DateField(_("Ngày kết thúc kháng sinh ban đầu"), null=True, blank=True)

#     def __str__(self):
#         return f"{self.INITIALANTIBIONAME} - {self.INITIALANTIBIODOSAGE}"

#     class Meta:
#         db_table = 'study_43en_initialantibiotic'
#         verbose_name = _("Kháng sinh ban đầu")
#         verbose_name_plural = _("Kháng sinh ban đầu")



# class MainAntibiotic(models.Model):
#     """Model for main antibiotics data"""
#     USUBJID = models.ForeignKey('study_43en.EnrollmentCase',to_field='USUBJID', on_delete=models.CASCADE, related_name='main_antibiotics')
#     MAINANTIBIONAME = models.CharField(_("Tên kháng sinh chính"), max_length=100, null=True, blank=True)
#     MAINANTIBIODOSAGE = models.CharField(_("Liều kháng sinh chính"), max_length=100, null=True, blank=True)
#     MAINANTIBIOSTARTDTC = models.DateField(_("Ngày bắt đầu kháng sinh chính"), null=True, blank=True)
#     MAINANTIBIOENDDTC = models.DateField(_("Ngày kết thúc kháng sinh chính"), null=True, blank=True)

#     def __str__(self):
#         return f"{self.MAINANTIBIONAME} - {self.MAINANTIBIODOSAGE}"

#     class Meta:
#         db_table = 'study_43en_mainantibiotic'
#         verbose_name = _("Kháng sinh chính")
#         verbose_name_plural = _("Kháng sinh chính")



# class VasoIDrug(models.Model):
#     """Model for vasoactive drugs data"""
#     USUBJID = models.ForeignKey('study_43en.EnrollmentCase',to_field='USUBJID', on_delete=models.CASCADE, related_name='vaso_drugs')
#     VASOIDRUGNAME = models.CharField(_("Tên thuốc vận mạch"), max_length=100, null=True, blank=True)
#     VASOIDRUGDOSAGE = models.CharField(_("Liều thuốc vận mạch"), max_length=100, null=True, blank=True)
#     VASOIDRUGSTARTDTC = models.DateField(_("Ngày bắt đầu thuốc vận mạch"), null=True, blank=True)
#     VASOIDRUGENDDTC = models.DateField(_("Ngày kết thúc thuốc vận mạch"), null=True, blank=True)

#     def __str__(self):
#         return f"{self.VASOIDRUGNAME} - {self.VASOIDRUGDOSAGE}"

#     class Meta:
#         db_table = 'study_43en_vasoidrug'
#         verbose_name = _("Thuốc vận mạch")
#         verbose_name_plural = _("Thuốc vận mạch")

# class AEHospEvent(models.Model):
#     USUBJID = models.ForeignKey('study_43en.EnrollmentCase', to_field='USUBJID', on_delete=models.CASCADE, related_name='AEHospEvent')
#     AENAME = models.CharField(max_length=255, verbose_name="Biến cố")
#     AEDETAILS = models.TextField(verbose_name="Chi tiết biến cố", blank=True, null=True)
#     AEDTC = models.DateField(verbose_name="Thời gian đánh giá", blank=True, null=True)

#     class Meta:
#         db_table = 'study_43en_aehospevent'
#         verbose_name = "Biến cố trong quá trình nằm viện"
#         verbose_name_plural = "Biến cố trong quá trình nằm viện"

# class ImproveSympt(models.Model):
#     USUBJID = models.ForeignKey('study_43en.EnrollmentCase', to_field='USUBJID', on_delete=models.CASCADE, related_name='ImproveSympt')
#     YESNO_CHOICES = (
#         ('yes', 'Có'),
#         ('no', 'Không'),
#     )
#     IMPROVE_SYMPTS = models.CharField(max_length=3, choices=YESNO_CHOICES, verbose_name="Cải thiện triệu chứng thực thể ban đầu?")
#     SYMPTS = models.TextField(verbose_name="Triệu chứng", blank=True, null=True)
#     IMPROVE_CONDITIONS = models.TextField(verbose_name="Tình trạng cải thiện", blank=True, null=True)
#     SYMPTSDTC = models.DateField(verbose_name="Thời gian đánh giá", blank=True, null=True)

#     class Meta:
#         db_table = 'study_43en_improvesympt'
#         verbose_name = "Cải thiện triệu chứng thực thể ban đầu"
#         verbose_name_plural = "Cải thiện triệu chứng thực thể ban đầu"

# class HospiProcess(models.Model):
#     USUBJID = models.ForeignKey('study_43en.EnrollmentCase', to_field='USUBJID', on_delete=models.CASCADE, related_name='hospiprocesses')
#     DEPTNAME = models.CharField(max_length=255, verbose_name="Khoa")
#     STARTDTC = models.DateField(verbose_name="Từ thời gian", blank=True, null=True)
#     ENDDTC = models.DateField(verbose_name="Đến thời gian", blank=True, null=True)
#     TRANSFER_REASON = models.TextField(verbose_name="Lý do chuyển", blank=True, null=True)

#     class Meta:
#         db_table = 'study_43en_hospiprocess'
#         verbose_name = "Quá trình nằm viện"
#         verbose_name_plural = "Quá trình nằm viện"

# class SampleCollection(models.Model):
#     # Kết nối với bệnh nhân
#     USUBJID = models.ForeignKey('study_43en.EnrollmentCase',to_field='USUBJID', on_delete=models.CASCADE, related_name='sample_collections')
    
#     # Thông tin mẫu - sử dụng tên từ CSV
#     SAMPLE_TYPE_CHOICES = (
#         ('1', _('Mẫu lần 1 (Thời điểm tham gia nghiên cứu)')),
#         ('2', _('Mẫu lần 2 (10 ± 3 ngày sau tham gia)')),
#         ('3', _('Mẫu lần 3 (28 ± 3 ngày sau tham gia)')),
#         ('4', _('Mẫu lần 4 (90 ± 3 ngày sau tham gia)')),
#     )
#     SAMPLE_TYPE = models.CharField(_('Loại mẫu'), max_length=1, choices=SAMPLE_TYPE_CHOICES)
    
#     # Mẫu lần 1
#     SAMPLE = models.BooleanField(_('Mẫu lần thu nhận'), default=True)
#     STOOL = models.BooleanField(_('Phân'), default=False)
#     STOOLDATE = models.DateField(_('Ngày lấy mẫu phân'), null=True, blank=True)
#     RECTSWAB = models.BooleanField(_('Phết trực tràng'), default=False)
#     RECTSWABDATE = models.DateField(_('Ngày lấy mẫu phết trực tràng'), null=True, blank=True)
#     THROATSWAB = models.BooleanField(_('Phết họng'), default=False)
#     THROATSWABDATE = models.DateField(_('Ngày lấy mẫu phết họng'), null=True, blank=True)
#     BLOOD = models.BooleanField(_('Mẫu máu'), default=False)
#     BLOODDATE = models.DateField(_('Ngày lấy mẫu máu'), null=True, blank=True)
#     REASONIFNO = models.TextField(_('Lý do không thu nhận được mẫu'), null=True, blank=True)
    
#     # Kết quả nuôi cấy cho các loại mẫu
#     CULTURE_RESULT_CHOICES = (
#         ('Pos', _('Dương tính')),
#         ('Neg', _('Âm tính')),
#         ('NoApply', _('Không áp dụng')),
#         ('NotPerformed', _('Không thực hiện')),
#     )
#     # Kết quả nuôi cấy mẫu phân 
#     CULTRES_1 = models.CharField(_('Kết quả nuôi cấy mẫu phân'), 
#                                   max_length=20, 
#                                   choices=CULTURE_RESULT_CHOICES,
#                                   null=True, blank=True)


#     # Phân lập được Klebsiella cho phân 
#     KLEBPNEU_1 = models.BooleanField(_('Klebsiella pneumoniae'), default=False)
#     OTHERRES_1 = models.BooleanField(_('Khác'), default=False)
#     OTHERRESSPECIFY_1 = models.CharField(_('Ghi rõ'), max_length=255, null=True, blank=True)
    
#     # Kết quả nuôi cấy mẫu phết trực tràng 
#     CULTRES_2 = models.CharField(_('Kết quả nuôi cấy mẫu phết trực tràng'), 
#                                      max_length=20, 
#                                      choices=CULTURE_RESULT_CHOICES,
#                                      null=True, blank=True)
    
#     # Phân lập được Klebsiella cho phết trực tràng
#     KLEBPNEU_2 = models.BooleanField(_('Klebsiella pneumoniae'), default=False)
#     OTHERRES_2 = models.BooleanField(_('Khác'), default=False)
#     OTHERRESSPECIFY_2 = models.CharField(_('Ghi rõ'), max_length=255, null=True, blank=True)

#     # Kết quả nuôi cấy mẫu phết họng 
#     CULTRES_3 = models.CharField(_('Kết quả nuôi cấy mẫu phết họng'), 
#                                       max_length=20, 
#                                       choices=CULTURE_RESULT_CHOICES,
#                                       null=True, blank=True)
    
    
#     # Phân lập được Klebsiella cho mẫu phết họng
#     KLEBPNEU_3 = models.BooleanField(_('Klebsiella pneumoniae cho phết họng'), default=False)
#     OTHERRES_3 = models.BooleanField(_('Khác cho phết họng'), default=False)
#     OTHERRESSPECIFY_3 = models.CharField(_('Ghi rõ cho phết họng'), max_length=255, null=True, blank=True)


#     # Thông tin người điền
#     COMPLETEDBY = models.CharField(_('Người hoàn thành'), max_length=50, null=True, blank=True)
#     COMPLETEDDATE = models.DateField(_('Ngày hoàn thành'), default=timezone.now)
    
#     class Meta:
#         db_table = 'study_43en_samplecollection'
#         verbose_name = _('Mẫu thu thập')
#         verbose_name_plural = _('Mẫu thu thập')
#         unique_together = ('USUBJID', 'SAMPLE_TYPE')
        
#     def __str__(self):
#         return f"Mẫu {self.get_sample_type_display()} - {self.USUBJID}"


# class ScreeningContact(models.Model):
#     """
#     Mô hình lưu trữ thông tin người tiếp xúc của bệnh nhân trong nghiên cứu 43EN-KPN
#     """
#     # Mã sàng lọc là primary key
#     SCRID = models.CharField(_("Mã sàng lọc"), max_length=10, primary_key=True)
    
#     # USUBJID không còn là primary key, chỉ là trường thông thường có thể null
#     USUBJID = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name=_("USUBJID"))
    
#     # Thông tin cơ bản
#     EVENT = models.CharField(_("Sự kiện"), max_length=50, default="CONTACT")
#     STUDYID = models.CharField(_("Study ID"), max_length=10, default="43EN")
#     SITEID = models.CharField(_("Site ID"), max_length=5)
#     SUBJID = models.CharField(_("Subject ID"), max_length=10, blank=True)
#     INITIAL = models.CharField(_("Patient Initials"), max_length=10)
    
#     # Mối quan hệ với bệnh nhân trong nghiên cứu
#     SUBJIDENROLLSTUDY = models.ForeignKey('study_43en.ScreeningCase', on_delete=models.CASCADE, 
#                                          related_name='contacts',
#                                          verbose_name=_("Bệnh nhân liên quan"),
#                                          to_field='USUBJID')
    
#     # Điều kiện sàng lọc
#     LIVEIN5DAYS3MTHS = models.BooleanField(_("Sống chung ít nhất 5 ngày trong 3 tháng"), default=False)
#     MEALCAREONCEDAY = models.BooleanField(_("Ăn cùng/chăm sóc ít nhất 1 lần/ngày"), default=False)
#     CONSENTTOSTUDY = models.BooleanField(_("Đồng ý tham gia nghiên cứu"), default=False)
    
#     # Ngày sàng lọc
#     SCREENINGFORMDATE = models.DateField(_("Ngày sàng lọc"), null=True, blank=True)
    
#     # Thông tin người hoàn thành
#     COMPLETEDBY = models.CharField(_("Người hoàn thành"), max_length=100, null=True, blank=True)
#     COMPLETEDDATE = models.DateField(_("Ngày hoàn thành"), null=True, blank=True)
    
#     # Metadata
#     ENTRY = models.IntegerField(_("Entry"), null=True, blank=True)
#     ENTEREDTIME = models.DateTimeField(_("Thời gian nhập"), auto_now_add=True)
    
#     # Trạng thái xác nhận
#     is_confirmed = models.BooleanField(_("Đã xác nhận"), default=False)

#     def __str__(self):
#         return self.USUBJID if self.USUBJID else f"CS-{self.SCRID}"
    
    
#     def save(self, *args, **kwargs):
#         # Tạo SCRID nếu chưa có
#         if not self.SCRID:
#             last_screening = ScreeningContact.objects.order_by('-SCRID').first()
#             if last_screening and last_screening.SCRID and last_screening.SCRID.startswith('CS-'):
#                 try:
#                     last_num = int(last_screening.SCRID[3:])
#                     self.SCRID = f"CS-{last_num + 1:03d}"
#                 except ValueError:
#                     self.SCRID = "CS-001"
#             else:
#                 self.SCRID = "CS-001"

#         create_usubjid = False
#         if self.LIVEIN5DAYS3MTHS and self.MEALCAREONCEDAY and self.CONSENTTOSTUDY and self.SUBJIDENROLLSTUDY:
#             if not self.USUBJID:
#                 create_usubjid = True
#                 # Đảm bảo có SITEID
#                 if not hasattr(self, 'SITEID') or not self.SITEID:
#                     self.SITEID = self.SUBJIDENROLLSTUDY.SITEID
#                 # Lấy USUBJID của bệnh nhân liên quan
#                 related_usubjid = self.SUBJIDENROLLSTUDY.USUBJID  # ví dụ: 003-A-003
#                 # Tách thành các phần
#                 parts = related_usubjid.split('-')
#                 if len(parts) == 3 and parts[1] == 'A':
#                     # Đổi 'A' thành 'B'
#                     contact_usubjid_base = f"{parts[0]}-B-{parts[2]}"
#                 else:
#                     # fallback: thay ký tự A đầu tiên thành B
#                     contact_usubjid_base = related_usubjid.replace('-A-', '-B-', 1)
#                 # Đếm số người liên quan đã có của bệnh nhân này
#                 existing_contacts = ScreeningContact.objects.filter(USUBJID__startswith=contact_usubjid_base + '-').count()
#                 next_index = existing_contacts + 1
#                 self.USUBJID = f"{contact_usubjid_base}-{next_index}"
#                 # Đảm bảo không trùng USUBJID
#                 while ScreeningContact.objects.filter(USUBJID=self.USUBJID).exists():
#                     next_index += 1
#                     self.USUBJID = f"{contact_usubjid_base}-{next_index}"
#                 # Tạo SUBJID nếu chưa có
#                 if not self.SUBJID:
#                     self.SUBJID = f"B-{parts[2]}-{next_index}"
#                 self.is_confirmed = True
#         super().save(*args, **kwargs)
#         return create_usubjid
    
#     class Meta:
#         db_table = 'study_43en_screeningcontact'
#         verbose_name = _("Người tiếp xúc")
#         verbose_name_plural = _("Người tiếp xúc")
#         ordering = ['-SCREENINGFORMDATE', 'SITEID', 'SUBJID']

# class EnrollmentContact(models.Model):
#     USUBJID = models.OneToOneField(
#         'study_43en.ScreeningContact',
#         on_delete=models.CASCADE,
#         to_field='USUBJID',
#         db_column='USUBJID',
#         primary_key=True,
#         verbose_name=_("USUBJID (mã người tiếp xúc)")
#     )
#     # Thêm trường liên kết với bệnh nhân chính
#     SUBJIDENROLLSTUDY = models.ForeignKey(
#         'study_43en.ScreeningCase',
#         on_delete=models.SET_NULL,
#         to_field='USUBJID',
#         null=True, blank=True,
#         verbose_name=_("Bệnh nhân chính liên quan")
#     )

#     ENRDATE = models.DateField(_("Ngày tham gia nghiên cứu"), null=True, blank=True)
#     RELATIONSHIP = models.CharField(_("Mối quan hệ với bệnh nhân"), max_length=100, null=True, blank=True)
#     DAYOFBIRTH = models.IntegerField(_("Ngày sinh"), null=True, blank=True)
#     MONTHOFBIRTH = models.IntegerField(_("Tháng sinh"), null=True, blank=True)
#     YEAROFBIRTH = models.IntegerField(_("Năm sinh"), null=True, blank=True)
#     AGEIFDOBUNKNOWN = models.FloatField(_("Tuổi (nếu không biết ngày sinh)"), null=True, blank=True)
#     SEX = models.CharField(_("Giới tính"), max_length=10, choices=[
#         ('Male', _('Nam')),
#         ('Female', _('Nữ')),
#         ('Other', _('Khác'))
#     ], null=True, blank=True)
#     ETHNICITY = models.CharField(_("Dân tộc"), max_length=50, null=True, blank=True)
#     SPECIFYIFOTHERETHNI = models.CharField(_("Chi tiết dân tộc khác"), max_length=100, null=True, blank=True)
#     OCCUPATION = models.CharField(_("Nghề nghiệp"), max_length=100, null=True, blank=True)

#     # Các trường yếu tố nguy cơ/tiền sử y tế
#     HOSP2D6M = models.BooleanField(_("Nhập viện ≥2 ngày trong 6 tháng qua"), default=False)
#     DIAL3M = models.BooleanField(_("Lọc máu trong 3 tháng qua"), default=False)
#     CATHETER3M = models.BooleanField(_("Đặt catheter trong 3 tháng qua"), default=False)
#     SONDE3M = models.BooleanField(_("Đặt sonde trong 3 tháng qua"), default=False)
#     HOMEWOUNDCARE = models.BooleanField(_("Chăm sóc vết thương tại nhà"), default=False)
#     LONGTERMCAREFACILITY = models.BooleanField(_("Ở cơ sở chăm sóc dài hạn"), default=False)
#     CORTICOIDPPI = models.BooleanField(_("Dùng corticoid hoặc PPI"), default=False)

#     # Bệnh nền - đồng bộ tên trường với EnrollmentCase
#     UNDERLYINGCONDS = models.BooleanField(_("Có bệnh nền"), default=False)
#     LISTUNDERLYING = models.JSONField(_("Các bệnh nền"), default=list, null=True, blank=True)
#     OTHERDISEASESPECIFY = models.TextField(_("Chi tiết bệnh khác"), null=True, blank=True)

#     # Tiền sử sử dụng thuốc
#     MEDHISDRUG = models.TextField(_("Lịch sử dùng thuốc"), null=True, blank=True)

#     # Thông tin hoàn thành
#     COMPLETEDBY = models.CharField(_("Người hoàn thành"), max_length=100, null=True, blank=True)
#     COMPLETEDDATE = models.DateField(_("Ngày hoàn thành"), null=True, blank=True)

#     # Thêm metadata nhập liệu
#     ENTRY = models.IntegerField(_("ENTRY"), null=True, blank=True)
#     ENTEREDTIME = models.DateTimeField(_("ENTEREDTIME"), null=True, blank=True)

#     # Property getters for underlying conditions (giữ nguyên)
#     @property
#     def DIABETES(self):
#         return 'DIABETES' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     @property
#     def HEARTFAILURE(self):
#         return 'HEARTFAILURE' in self.LISTUNDERLYING if self.LISTUNDERLYING else False


#     @property
#     def COPD(self):
#         return 'COPD' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     @property
#     def HEPATITIS(self):
#         return 'HEPATITIS' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     @property
#     def CAD(self):
#         return 'CAD' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     @property
#     def KIDNEYDISEASE(self):
#         return 'KIDNEYDISEASE' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     @property
#     def ASTHMA(self):
#         return 'ASTHMA' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     @property
#     def CIRRHOSIS(self):
#         return 'CIRRHOSIS' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     @property
#     def HYPERTENSION(self):
#         return 'HYPERTENSION' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     @property
#     def AUTOIMMUNE(self):
#         return 'AUTOIMMUNE' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     @property
#     def CANCER(self):
#         return 'CANCER' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     @property
#     def ALCOHOLISM(self):
#         return 'ALCOHOLISM' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     @property
#     def HIV(self):
#         return 'HIV' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     @property
#     def ADRENALINSUFFICIENCY(self):
#         return 'ADRENALINSUFFICIENCY' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     @property
#     def BEDRIDDEN(self):
#         return 'BEDRIDDEN' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     @property
#     def PEPTICULCER(self):
#         return 'PEPTICULCER' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     @property
#     def COLITIS_IBS(self):
#         return 'COLITIS_IBS' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     @property
#     def SENILITY(self):
#         return 'SENILITY' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     @property
#     def MALNUTRITION_WASTING(self):
#         return 'MALNUTRITION_WASTING' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     @property
#     def OTHERDISEASE(self):
#         return 'OTHERDISEASE' in self.LISTUNDERLYING if self.LISTUNDERLYING else False

#     class Meta:
#         db_table = 'study_43en_enrollmentcontact'
#         verbose_name = _("Đăng ký người tiếp xúc")
#         verbose_name_plural = _("Đăng ký người tiếp xúc")

#     def __str__(self):
#         return f"EnrollmentContact: {self.contact.USUBJID if self.contact else ''}"
    
#     def __str__(self):
#         return f"{self.USUBJID.USUBJID}"
    
# class ContactMedHisDrug(models.Model):
#     ENROLLCONTACT = models.ForeignKey(
#         'study_43en.EnrollmentContact',
#         on_delete=models.CASCADE,
#         related_name='medhisdrug_set',
#         to_field='USUBJID',
#         db_column='ENROLLCONTACT_USUBJID',
#         verbose_name=_("Người tiếp xúc")
#     )
#     SEQ = models.IntegerField(_("STT thuốc"), null=True, blank=True)
#     DRUGNAME = models.CharField(_("Tên thuốc"), max_length=255, null=True, blank=True)
#     DOSAGE = models.CharField(_("Liều dùng"), max_length=100, null=True, blank=True)
#     USAGETIME = models.CharField(_("Thời gian dùng"), max_length=100, null=True, blank=True)
#     USAGEREASON = models.TextField(_("Lý do dùng"), null=True, blank=True)
#     ENTRY = models.IntegerField(null=True, blank=True)
#     ENTEREDTIME = models.DateTimeField(null=True, blank=True)

#     class Meta:
#         db_table = 'study_43en_contactmedhisdrug'
#         verbose_name = _("Lịch sử dùng thuốc (người tiếp xúc)")
#         verbose_name_plural = _("Lịch sử dùng thuốc (người tiếp xúc)")

#     def __str__(self):
#         return f"{self.ENROLLCONTACT} - {self.DRUGNAME}"

# class FollowUpCase(models.Model):
#     """
#     Mô hình lưu trữ thông tin follow-up của bệnh nhân
#     """
#     # PK là USUBJID từ EnrollmentCase 
#     USUBJID = models.OneToOneField(
#         'study_43en.EnrollmentCase', 
#         on_delete=models.CASCADE, 
#         primary_key=True,
#         to_field='USUBJID',
#         verbose_name=_("USUBJID")
#     )
    
    
#     # 1. Bệnh nhân được đánh giá tình trạng tại ngày 28?
#     ASSESSED_CHOICES = [
#         ('Yes', _('Có')),
#         ('No', _('Không')),
#         ('NA', _('Không áp dụng')),
#     ]

#     ASSESSED = models.CharField(
#         _("Bệnh nhân được đánh giá tình trạng tại ngày 28?"),
#         max_length=3,
#         choices=ASSESSED_CHOICES,
#         null=True, blank=True
#     )
#     ASSESSDATE = models.DateField(_("Ngày đánh giá (nn/tt/nnnn)"), null=True, blank=True)
    
#     # Tình trạng bệnh nhân tổng quát
#     PATIENT_STATUS_CHOICES = [
#         ('Alive', _('Sống')),
#         ('Rehospitalized', _('Tái nhập viện')), 
#         ('Deceased', _('Tử vong')),
#         ('LostToFollowUp', _('Không liên hệ được')),
#     ]
#     PATSTATUS = models.CharField(
#         _("Tình trạng bệnh nhân"),
#         max_length=20,
#         choices=PATIENT_STATUS_CHOICES,
#         null=True, blank=True
#     )
    
#     # 2. Bệnh nhân tái nhập viện?
#     REHOSP = models.CharField(
#         _("Bệnh nhân tái nhập viện?"),
#         max_length=3,
#         choices=ASSESSED_CHOICES,
#         null=True, blank=True
#     )
#     REHOSPCOUNT = models.IntegerField(_("Bao nhiều lần tái nhập viện?"), null=True, blank=True)
    
#     # 3. Bệnh nhân tử vong?
#     DECEASED = models.CharField(
#         _("Bệnh nhân tử vong?"),
#         max_length=3,
#         choices=ASSESSED_CHOICES,
#         null=True, blank=True
#     )
#     DEATHDATE = models.DateField(_("Ngày tử vong (nn/tt/nnnn)"), null=True, blank=True)
#     DEATHCAUSE = models.TextField(_("Nguyên nhân tử vong"), null=True, blank=True)

#     # 4. Bệnh nhân có sử dụng kháng sinh từ lần khám gần nhất?
#     USEDANTIBIO = models.CharField(
#         _("Bệnh nhân có sử dụng kháng sinh từ lần khám gần nhất?"),
#         max_length=3,
#         choices=ASSESSED_CHOICES,
#         null=True, blank=True
#     )
#     ANTIBIOCOUNT = models.IntegerField(_("Bao nhiều đợt kháng sinh?"), null=True, blank=True)
    
#     # 5. Đánh giá tình trạng chức năng tại ngày 28
#     FUNCASSESS = models.CharField(
#         _("Đánh giá tình trạng chức năng tại ngày 28?"),
#         max_length=3,
#         choices=ASSESSED_CHOICES,
#         null=True, blank=True
#     )
    
#     # 5a-5e: Các khía cạnh chức năng
#     FUNCTIONAL_STATUS_CHOICES = [
#         ('Normal', _('Bình thường')),
#         ('Problem', _('Có vấn đề')),
#         ('Bedridden', _('Nằm một chỗ')),
#     ]
    
#     MOBILITY = models.CharField(
#         _("5a. Vận động (đi lại)"),
#         max_length=20,
#         choices=FUNCTIONAL_STATUS_CHOICES,
#         null=True, blank=True
#     )
    
#     PERHYGIENE = models.CharField(
#         _("5b. Vệ sinh cá nhân (tự tắm rửa, thay quần áo)"),
#         max_length=20,
#         choices=FUNCTIONAL_STATUS_CHOICES,
#         null=True, blank=True
#     )
    
#     DAILYACTIV = models.CharField(
#         _("5c. Sinh hoạt hằng ngày (làm việc, học tập, việc nhà, hoạt động vui chơi)"),
#         max_length=20,
#         choices=FUNCTIONAL_STATUS_CHOICES,
#         null=True, blank=True
#     )

#     PAINDISCOMF = models.CharField(
#         _("5d. Đau/ khó chịu"),
#         max_length=20,
#         choices=FUNCTIONAL_STATUS_CHOICES,
#         null=True, blank=True
#     )
    
#     ANXIETY_DEPRESSION_CHOICES = [
#         ('None', _('Không')),
#         ('Moderate', _('Trung bình')),
#         ('Severe', _('Nhiều')),
#     ]

#     ANXIETY_DEPRESSION = models.CharField(
#         _("5e. Lo lắng/ Trầm cảm"),
#         max_length=20,
#         choices=ANXIETY_DEPRESSION_CHOICES,
#         null=True, blank=True
#     )
    
#     # 5f. FBSI Score (0-7) - theo đúng form
#     FBSI_SCORE_CHOICES = [
#         (7, _('7. Xuất viện; cơ bản khỏe mạnh; có thể hoàn thành các hoạt động hằng ngày mức độ cao')),
#         (6, _('6. Xuất viện; có triệu chứng/ dấu hiệu bệnh trung bình; không thể hoàn thành các hoạt động hằng ngày')),
#         (5, _('5. Xuất viện; tàn tật nghiêm trọng; yêu cầu chăm sóc và hỗ trợ hằng ngày mức độ cao')),
#         (4, _('4. Nhập viện nhưng không nằm ở ICU')),
#         (3, _('3. Nhập viện và nằm ở ICU')),
#         (2, _('2. Nhập khoa thở máy kéo dài')),
#         (1, _('1. Chăm sóc giảm nhẹ trong giai đoạn cuối đời (ở bệnh viện hoặc ở nhà)')),
#         (0, _('0. Tử vong'))
#     ]

#     FBSISCORE = models.IntegerField(_("5f. FBSI Score"),
#                                       choices=FBSI_SCORE_CHOICES,
#                                       null=True, blank=True)
    
#     # Thông tin hoàn thành - theo pattern hiện tại
#     COMPLETEDBY = models.CharField(_("Người hoàn thành"), max_length=100, null=True, blank=True)
#     COMPLETEDDATE = models.DateField(_("Ngày hoàn thành"), null=True, blank=True)
    
#     class Meta:
#         db_table = 'study_43en_followupcase'
#         verbose_name = _("Theo dõi bệnh nhân ngày 28")
#         verbose_name_plural = _("Theo dõi bệnh nhân ngày 28")
    
#     def __str__(self):
#         return f"Follow-up 28 ngày: {self.USUBJID}"


# class Rehospitalization(models.Model):
#     """
#     Mô hình lưu trữ thông tin tái nhập viện trong follow-up
#     """
    
#     USUBJID = models.ForeignKey('study_43en.FollowUpCase', on_delete=models.CASCADE, 
#                                  related_name='rehospitalization')
    
#     # Thông tin tái nhập viện - theo naming convention
#     EPISODE = models.IntegerField(_("Đợt"), default=1)
#     REHOSPDATE = models.DateField(_("Ngày tái nhập viện"), null=True, blank=True)
#     REHOSPREASONFOR = models.TextField(_("Lý do tái nhập viện"), null=True, blank=True)
#     REHOSPLOCATION = models.CharField(_("Nơi tái nhập viện"), max_length=255, null=True, blank=True)
#     REHOSPSTAYDUR = models.CharField(_("Thời gian nằm viện"), max_length=50, null=True, blank=True)
    
#     class Meta:
#         db_table = 'study_43en_rehospitalization'
#         unique_together = ['USUBJID', 'EPISODE']
#         ordering = ['EPISODE']
#         verbose_name = _("Tái nhập viện")
#         verbose_name_plural = _("Tái nhập viện")
    
#     def __str__(self):
#         return f"Tái nhập viện đợt {self.EPISODE} - {self.USUBJID}"


# class FollowUpAntibiotic(models.Model):
#     """
#     Mô hình lưu trữ thông tin sử dụng kháng sinh trong follow-up
#     """
    
#     USUBJID = models.ForeignKey('study_43en.FollowUpCase', on_delete=models.CASCADE, 
#                                  related_name='antibiotics')
    
#     # Thông tin kháng sinh - theo naming convention
#     EPISODE = models.IntegerField(_("Đợt"), default=1)
#     ANTIBIONAME = models.CharField(_("Tên thuốc"), max_length=255, null=True, blank=True)
#     ANTIBIOREASONFOR = models.TextField(_("Lý do sử dụng"), null=True, blank=True)
#     ANTIBIODUR = models.CharField(_("Thời gian sử dụng"), max_length=50, null=True, blank=True)
    
#     class Meta:
#         db_table = 'study_43en_followupantibiotic'
#         unique_together = ['USUBJID', 'EPISODE']
#         ordering = ['EPISODE']
#         verbose_name = _("Kháng sinh follow-up")
#         verbose_name_plural = _("Kháng sinh follow-up")
    
#     def __str__(self):
#         return f"Kháng sinh đợt {self.EPISODE} ({self.ANTIBIONAME}) - {self.USUBJID}"


# class FollowUpCase90(models.Model):
#     """
#     Mô hình lưu trữ thông tin follow-up 90 ngày của bệnh nhân
#     """
#     # PK là USUBJID từ EnrollmentCase
#     USUBJID = models.OneToOneField(
#         'study_43en.EnrollmentCase', 
#         on_delete=models.CASCADE, 
#         primary_key=True,
#         to_field='USUBJID',
#         verbose_name=_("USUBJID")
#     )
    
#     # 1. Bệnh nhân được đánh giá tình trạng tại thời điểm ngày 90?
#     ASSESSED_CHOICES = [
#         ('Yes', _('Có')),
#         ('No', _('Không')),
#         ('NA', _('Không áp dụng')),
#     ]
    
#     ASSESSED = models.CharField(
#         _("Bệnh nhân được đánh giá tình trạng tại ngày 90?"),
#         max_length=3,
#         choices=ASSESSED_CHOICES,
#         null=True, blank=True
#     )
#     ASSESSDATE = models.DateField(_("Ngày đánh giá (nn/tt/nnnn)"), null=True, blank=True)
    
#     # Tình trạng bệnh nhân tổng quát
#     PATIENT_STATUS_CHOICES = [
#         ('Alive', _('Sống')),
#         ('Rehospitalized', _('Tái nhập viện')), 
#         ('Deceased', _('Tử vong')),
#         ('LostToFollowUp', _('Không liên hệ được')),
#     ]
#     PATSTATUS = models.CharField(
#         _("Tình trạng bệnh nhân"),
#         max_length=20,
#         choices=PATIENT_STATUS_CHOICES,
#         null=True, blank=True
#     )
    
#     # 2. Bệnh nhân tái nhập viện?
#     REHOSP = models.CharField(
#         _("Bệnh nhân tái nhập viện?"),
#         max_length=3,
#         choices=ASSESSED_CHOICES,
#         null=True, blank=True
#     )
#     REHOSPCOUNT = models.IntegerField(_("Bao nhiều lần tái nhập viện?"), null=True, blank=True)
    
#     # 3. Bệnh nhân tử vong?
#     DECEASED = models.CharField(
#         _("Bệnh nhân tử vong?"),
#         max_length=3,
#         choices=ASSESSED_CHOICES,
#         null=True, blank=True
#     )
#     DEATHDATE = models.DateField(_("Ngày tử vong (nn/tt/nnnn)"), null=True, blank=True)
#     DEATHCAUSE = models.TextField(_("Nguyên nhân tử vong"), null=True, blank=True)
    
#     # 4. Bệnh nhân có sử dụng kháng sinh từ lần khám gần nhất?
#     USEDANTIBIO = models.CharField(
#         _("Bệnh nhân có sử dụng kháng sinh từ lần khám gần nhất?"),
#         max_length=3,
#         choices=ASSESSED_CHOICES,
#         null=True, blank=True
#     )
#     ANTIBIOCOUNT = models.IntegerField(_("Bao nhiều đợt kháng sinh?"), null=True, blank=True)
    
#     # 5. Đánh giá tình trạng chức năng tại thời điểm ngày 90
#     FUNCASSESS = models.CharField(
#         _("Đánh giá tình trạng chức năng tại ngày 90?"),
#         max_length=3,
#         choices=ASSESSED_CHOICES,
#         null=True, blank=True
#     )
    
#     # 5a-5e: Các khía cạnh chức năng
#     FUNCTIONAL_STATUS_CHOICES = [
#         ('Normal', _('Bình thường')),
#         ('Problem', _('Có vấn đề')),
#         ('Bedridden', _('Nằm một chỗ')),
#     ]
    
#     MOBILITY = models.CharField(
#         _("5a. Vận động (đi lại)"),
#         max_length=20,
#         choices=FUNCTIONAL_STATUS_CHOICES,
#         null=True, blank=True
#     )
    
#     PERHYGIENE = models.CharField(
#         _("5b. Vệ sinh cá nhân (tự tắm rửa, thay quần áo)"),
#         max_length=20,
#         choices=FUNCTIONAL_STATUS_CHOICES,
#         null=True, blank=True
#     )
    
#     DAILYACTIV = models.CharField(
#         _("5c. Sinh hoạt hằng ngày (làm việc, học tập, việc nhà, hoạt động vui chơi)"),
#         max_length=20,
#         choices=FUNCTIONAL_STATUS_CHOICES,
#         null=True, blank=True
#     )
    
#     PAINDISCOMF = models.CharField(
#         _("5d. Đau/ khó chịu"),
#         max_length=20,
#         choices=FUNCTIONAL_STATUS_CHOICES,
#         null=True, blank=True
#     )
    
#     ANXIETY_DEPRESSION_CHOICES = [
#         ('None', _('Không')),
#         ('Moderate', _('Trung bình')),
#         ('Severe', _('Nhiều')),
#     ]
    
#     ANXIETY_DEPRESSION = models.CharField(
#         _("5e. Lo lắng/ Trầm cảm"),
#         max_length=20,
#         choices=ANXIETY_DEPRESSION_CHOICES,
#         null=True, blank=True
#     )
    
#     # 5f. FBSI Score (0-7) - theo đúng form
#     FBSI_SCORE_CHOICES = [
#         (7, _('7. Xuất viện; cơ bản khỏe mạnh; có thể hoàn thành các hoạt động hằng ngày mức độ cao')),
#         (6, _('6. Xuất viện; có triệu chứng/ dấu hiệu bệnh trung bình; không thể hoàn thành các hoạt động hằng ngày')),
#         (5, _('5. Xuất viện; tàn tật nghiêm trọng; yêu cầu chăm sóc và hỗ trợ hằng ngày mức độ cao')),
#         (4, _('4. Nhập viện nhưng không nằm ở ICU')),
#         (3, _('3. Nhập viện và nằm ở ICU')),
#         (2, _('2. Nhập khoa thở máy kéo dài')),
#         (1, _('1. Chăm sóc giảm nhẹ trong giai đoạn cuối đời (ở bệnh viện hoặc ở nhà)')),
#         (0, _('0. Tử vong'))
#     ]

#     FBSISCORE = models.IntegerField(
#         _("5f. FBSI Score"),
#         choices=FBSI_SCORE_CHOICES,
#         null=True, blank=True
#     )
    
#     # Thông tin hoàn thành - theo pattern hiện tại
#     COMPLETEDBY = models.CharField(_("Người hoàn thành"), max_length=100, null=True, blank=True)
#     COMPLETEDDATE = models.DateField(_("Ngày hoàn thành"), null=True, blank=True)
    
#     class Meta:
#         db_table = 'study_43en_followupcase90'
#         verbose_name = _("Theo dõi bệnh nhân ngày 90")
#         verbose_name_plural = _("Theo dõi bệnh nhân ngày 90")
    
#     def __str__(self):
#         return f"Follow-up 90 ngày: {self.USUBJID}"


# class Rehospitalization90(models.Model):
#     """
#     Mô hình lưu trữ thông tin tái nhập viện trong follow-up 90 ngày
#     """

#     USUBJID = models.ForeignKey(
#         'study_43en.FollowUpCase90',
#         on_delete=models.CASCADE,
#         related_name='rehospitalization'
#     )

#     # Thông tin tái nhập viện - theo naming convention
#     EPISODE = models.IntegerField(_("Đợt"), default=1)
#     REHOSPDATE = models.DateField(_("Ngày tái nhập viện"), null=True, blank=True)
#     REHOSPREASONFOR = models.TextField(_("Lý do tái nhập viện"), null=True, blank=True)
#     REHOSPLOCATION = models.CharField(_("Nơi tái nhập viện"), max_length=255, null=True, blank=True)
#     REHOSPSTAYDUR = models.CharField(_("Thời gian nằm viện"), max_length=50, null=True, blank=True)
    
#     class Meta:
#         db_table = 'study_43en_rehospitalization90'
#         unique_together = ['USUBJID', 'EPISODE']
#         ordering = ['EPISODE']
#         verbose_name = _("Tái nhập viện (90 ngày)")
#         verbose_name_plural = _("Tái nhập viện (90 ngày)")
    
#     def __str__(self):
#         return f"Tái nhập viện đợt {self.EPISODE} - {self.USUBJID} (90 ngày)"


# class FollowUpAntibiotic90(models.Model):
#     """
#     Mô hình lưu trữ thông tin sử dụng kháng sinh trong follow-up 90 ngày
#     """

#     USUBJID = models.ForeignKey(
#         'study_43en.FollowUpCase90',
#         on_delete=models.CASCADE,
#         related_name='antibiotics'
#     )

#     # Thông tin kháng sinh - theo naming convention
#     EPISODE = models.IntegerField(_("Đợt"), default=1)
#     ANTIBIONAME = models.CharField(_("Tên thuốc"), max_length=255, null=True, blank=True)
#     ANTIBIOREASONFOR = models.TextField(_("Lý do sử dụng"), null=True, blank=True)
#     ANTIBIODUR = models.CharField(_("Thời gian sử dụng"), max_length=50, null=True, blank=True)

#     class Meta:
#         db_table = 'study_43en_followupantibiotic90'
#         unique_together = ['USUBJID', 'EPISODE']
#         ordering = ['EPISODE']
#         verbose_name = _("Kháng sinh follow-up (90 ngày)")
#         verbose_name_plural = _("Kháng sinh follow-up (90 ngày)")

#     def __str__(self):
#         return f"Kháng sinh đợt {self.EPISODE} ({self.ANTIBIONAME}) - {self.USUBJID} (90 ngày)"
    
    
# class DischargeCase(models.Model):
#     """
#     Model cho thông tin xuất viện - Discharge Case
#     Theo pattern của các model FollowUpCase, FollowUpCase90, ClinicalCase
#     """
    
#     # Primary key liên kết với ScreeningCase - theo pattern chuẩn
#     USUBJID = models.OneToOneField(
#         'study_43en.EnrollmentCase', 
#         on_delete=models.CASCADE, 
#         primary_key=True,
#         to_field='USUBJID',
#         verbose_name=_('USUBJID')
#     )
    
#     # Thông tin header form - theo pattern ClinicalCase
#     EVENT = models.CharField(_("Sự kiện"), max_length=50, default="DISCHARGE")
#     STUDYID = models.CharField(_("Study ID"), max_length=10, null=True, blank=True)
#     SITEID = models.CharField(_("Site ID"), max_length=5, null=True, blank=True)
#     SUBJID = models.CharField(_("Subject ID"), max_length=10, null=True, blank=True)
#     INITIAL = models.CharField(_("Patient Initials"), max_length=10, null=True, blank=True)
    
#     # 1. Ngày xuất viện
#     DISCHDATE = models.DateField(
#         _("1. Ngày xuất viện (nn/tt/nnnn)"),
#         null=True, blank=True
#     )
    
#     # 3. Tình trạng khi xuất viện
#     DISCHARGE_STATUS_CHOICES = [
#         ('Recovered', _('Xuất viện và hồi phục hoàn toàn')),
#         ('Improved', _('Xuất viện mà chưa hồi phục hoàn toàn')),
#         ('Died', _('Tử vong hoặc hấp hối')),
#         ('TransferredLeft', _('Bộ viện/Xin ra viện khi chưa hoàn thành điều trị')),
#     ]
    
#     DISCHSTATUS = models.CharField(
#         _("3. Tình trạng khi xuất viện"),
#         max_length=20,
#         choices=DISCHARGE_STATUS_CHOICES,
#         null=True, blank=True
#     )
    
#     DISCHSTATUSDETAIL = models.TextField(
#         _("Chi tiết về tình trạng khi xuất viện"),
#         null=True, blank=True
#     )
    
#     # 4. Bệnh nhân chuyển sang bệnh viện khác? - theo pattern Yes/No/NA
#     TRANSFER_CHOICES = [
#         ('Yes', _('Có')),
#         ('No', _('Không')),
#         ('NA', _('Không áp dụng')),
#     ]
    
#     TRANSFERHOSP = models.CharField(
#         _("4. Bệnh nhân chuyển sang bệnh viện khác?"),
#         max_length=3,
#         choices=TRANSFER_CHOICES,
#         default='No'
#     )
    
#     # 4a. Lý do chuyển viện
#     TRANSFERREASON = models.TextField(
#         _("4a. Lý do chuyển viện"),
#         null=True, blank=True
#     )
    
#     # 4b. Nơi chuyển viện
#     TRANSFERLOCATION = models.CharField(
#         _("4b. Nơi chuyển viện"),
#         max_length=200,
#         null=True, blank=True
#     )
    
#     # 5. Bệnh nhân tử vong tại thời điểm ra viện? - theo pattern Yes/No/NA
#     DEATHATDISCH = models.CharField(
#         _("5. Bệnh nhân tử vong tại thời điểm ra viện?"),
#         max_length=3,
#         choices=TRANSFER_CHOICES,  # Sử dụng chung choices Yes/No/NA
#         default='No'
#     )
    
#     # 5. Nếu Có, nguyên nhân tử vong
#     DEATHCAUSE = models.TextField(
#         _("5. Nếu Có, nguyên nhân tử vong"),
#         null=True, blank=True
#     )
    
#     # Thông tin hoàn thành - theo pattern chuẩn của tất cả model
#     COMPLETEDBY = models.CharField(
#         _("Người hoàn thành"),
#         max_length=100,
#         null=True, blank=True
#     )
    
#     COMPLETEDDATE = models.DateField(
#         _("Ngày hoàn thành"),
#         null=True, blank=True
#     )
    
#     # Metadata - theo pattern của các model khác
#     CREATEDDATE = models.DateTimeField(auto_now_add=True, verbose_name=_('Ngày tạo'))
#     UPDATEDDATE = models.DateTimeField(auto_now=True, verbose_name=_('Ngày cập nhật'))
    
#     class Meta:
#         db_table = 'study_43en_dischargecase'
#         verbose_name = _("Discharge Case")
#         verbose_name_plural = _("Discharge Cases")
#         ordering = ['-COMPLETEDDATE']
    
#     def __str__(self):
#         return f"Discharge - {self.USUBJID}"
    
#     @property
#     def has_death_info(self):
#         """Kiểm tra xem có thông tin tử vong không"""
#         return self.DEATHATDISCH == 'Yes' and self.DEATHCAUSE
    
#     @property
#     def has_transfer_info(self):
#         """Kiểm tra xem có thông tin chuyển viện không"""
#         return self.TRANSFERHOSP == 'Yes' and (self.TRANSFERREASON or self.TRANSFERLOCATION)
    
#     def save(self, *args, **kwargs):
#         # Auto-populate từ ScreeningCase nếu cần - theo pattern ClinicalCase
#         if self.USUBJID:
#             screening = self.USUBJID
#             if not self.STUDYID:
#                 self.STUDYID = screening.STUDYID
#             if not self.SITEID:
#                 self.SITEID = screening.SITEID
#             if not self.SUBJID:
#                 self.SUBJID = screening.SUBJID
#             if not self.INITIAL:
#                 self.INITIAL = screening.INITIAL
        
#         super().save(*args, **kwargs)


# class DischargeICD(models.Model):
#     """
#     Model cho các mã ICD-10 trong xuất viện - sử dụng ForeignKey để có thể có nhiều ICD
#     Theo pattern của các model related như Rehospitalization, FollowUpAntibiotic
#     """
    
#     discharge_case = models.ForeignKey(
#         'study_43en.DischargeCase',
#         on_delete=models.CASCADE,
#         related_name='icd_codes',
#         verbose_name=_('Discharge Case')
#     )
    
#     # Thứ tự ICD (1-6)
#     EPISODE = models.IntegerField(_("Thứ tự ICD"), default=1)
    
#     # 2. Chẩn đoán khi xuất viện - mã ICD-10
#     ICDCODE = models.CharField(
#         _("Mã ICD-10"), 
#         max_length=20, 
#         null=True, blank=True
#     )
    
#     ICDDETAIL = models.TextField(
#         _("Chi tiết chẩn đoán"), 
#         null=True, blank=True
#     )
    
#     class Meta:
#         db_table = 'study_43en_dischargeicd'
#         unique_together = ['discharge_case', 'EPISODE']
#         ordering = ['EPISODE']
#         verbose_name = _("Mã ICD xuất viện")
#         verbose_name_plural = _("Mã ICD xuất viện")
    
#     def __str__(self):
#         return f"ICD-10.{self.EPISODE}: {self.ICDCODE} - {self.discharge_case.USUBJID}"


# class ContactSampleCollection(models.Model):
#     """
#     Model lưu trữ thông tin lấy mẫu cho Contact - giống SampleCollection nhưng chỉ có sample_type 1, 3, 4
#     """
#     USUBJID = models.ForeignKey(
#         'study_43en.EnrollmentContact',
#         on_delete=models.CASCADE,
#         related_name='sample_collections',
#         to_field='USUBJID',
#         verbose_name=_('Contact Case')
#     )

#     SAMPLE_TYPE_CHOICES = (
#         ('1', _('Mẫu lần 1 (Thời điểm tham gia nghiên cứu)')),
#         ('3', _('Mẫu lần 3 (28 ± 3 ngày sau tham gia)')),
#         ('4', _('Mẫu lần 4 (90 ± 3 ngày sau tham gia)')),
#     )
#     SAMPLE_TYPE = models.CharField(_('Loại mẫu'), max_length=1, choices=SAMPLE_TYPE_CHOICES)

#     # Lần 1
#     SAMPLE = models.BooleanField(_('Mẫu lần thu nhận'), default=True)
#     STOOL = models.BooleanField(_('Phân'), default=False)
#     STOOLDATE = models.DateField(_('Ngày lấy mẫu phân'), null=True, blank=True)
#     RECTSWAB = models.BooleanField(_('Phết trực tràng'), default=False)
#     RECTSWABDATE = models.DateField(_('Ngày lấy mẫu phết trực tràng'), null=True, blank=True)
#     THROATSWAB = models.BooleanField(_('Phết họng'), default=False)
#     THROATSWABDATE = models.DateField(_('Ngày lấy mẫu phết họng'), null=True, blank=True)
#     BLOOD = models.BooleanField(_('Mẫu máu'), default=False)  # CHỈ CHO LẦN 1
#     BLOODDATE = models.DateField(_('Ngày lấy mẫu máu'), null=True, blank=True)  # CHỈ CHO LẦN 1
#     REASONIFNO = models.TextField(_('Lý do không thu nhận được mẫu'), null=True, blank=True)

#     # Kết quả nuôi cấy cho các loại mẫu
#     CULTURE_RESULT_CHOICES = (
#         ('Pos', _('Dương tính')),
#         ('Neg', _('Âm tính')),
#         ('NoApply', _('Không áp dụng')),
#         ('NotPerformed', _('Không thực hiện')),
#     )
#     # Kết quả nuôi cấy mẫu phân 
#     CULTRES_1 = models.CharField(_('Kết quả nuôi cấy mẫu phân'), 
#                                   max_length=20, 
#                                   choices=CULTURE_RESULT_CHOICES,
#                                   null=True, blank=True)
#     KLEBPNEU_1 = models.BooleanField(_('Klebsiella pneumoniae'), default=False)
#     OTHERRES_1 = models.BooleanField(_('Khác'), default=False)
#     OTHERRESSPECIFY_1 = models.CharField(_('Ghi rõ'), max_length=255, null=True, blank=True)

#     # Kết quả nuôi cấy mẫu phết trực tràng 
#     CULTRES_2 = models.CharField(_('Kết quả nuôi cấy mẫu phết trực tràng'), 
#                                      max_length=20, 
#                                      choices=CULTURE_RESULT_CHOICES,
#                                      null=True, blank=True)
#     KLEBPNEU_2 = models.BooleanField(_('Klebsiella pneumoniae'), default=False)
#     OTHERRES_2 = models.BooleanField(_('Khác'), default=False)
#     OTHERRESSPECIFY_2 = models.CharField(_('Ghi rõ'), max_length=255, null=True, blank=True)

#     # Kết quả nuôi cấy mẫu phết họng 
#     CULTRES_3 = models.CharField(_('Kết quả nuôi cấy mẫu phết họng'), 
#                                       max_length=20, 
#                                       choices=CULTURE_RESULT_CHOICES,
#                                       null=True, blank=True)
#     KLEBPNEU_3 = models.BooleanField(_('Klebsiella pneumoniae cho phết họng'), default=False)
#     OTHERRES_3 = models.BooleanField(_('Khác cho phết họng'), default=False)
#     OTHERRESSPECIFY_3 = models.CharField(_('Ghi rõ cho phết họng'), max_length=255, null=True, blank=True)

#     # Thông tin người điền
#     COMPLETEDBY = models.CharField(_('Người hoàn thành'), max_length=50, null=True, blank=True)
#     COMPLETEDDATE = models.DateField(_('Ngày hoàn thành'), default=timezone.now)

#     ENTRY = models.IntegerField(null=True, blank=True)
#     ENTEREDTIME = models.DateTimeField(null=True, blank=True)

#     class Meta:
#         db_table = 'study_43en_contactsamplecollection'
#         verbose_name = _('Mẫu thu thập Contact')
#         verbose_name_plural = _('Mẫu thu thập Contact')
#         unique_together = ('USUBJID', 'SAMPLE_TYPE')

#     def __str__(self):
#         return f"Mẫu Contact {self.get_SAMPLE_TYPE_display()} - {self.USUBJID}"

# class ContactFollowUp28(models.Model):
#     """
#     Model lưu trữ thông tin theo dõi người tiếp xúc gần tại ngày 28
#     """
#     # Kết nối với EnrollmentContact
#     USUBJID = models.OneToOneField(
#         'study_43en.EnrollmentContact',
#         on_delete=models.CASCADE,
#         primary_key=True,
#         verbose_name=_('Contact Case')
#     )
    
#     # 1. Người tiếp xúc gần được đánh giá tại ngày 28?
#     ASSESSED_CHOICES = [
#         ('Yes', _('Có')),
#         ('No', _('Không')),
#         ('NA', _('Không áp dụng')),
#     ]
    
#     ASSESSED = models.CharField(
#         _("Người tiếp xúc gần được đánh giá tại ngày 28?"),
#         max_length=3,
#         choices=ASSESSED_CHOICES,
#         null=True, blank=True
#     )
    
#     ASSESSDATE = models.DateField(
#         _("Ngày đánh giá (nn/tt/nnnn)"),
#         null=True, blank=True
#     )
    
#     # 2. Người tiếp xúc gần có từng tiếp xúc với Chăm sóc Y tế kể từ lần đánh giá trước?
#     HOSP2D = models.BooleanField(
#         _("Nằm viện ≥ 2 ngày"),
#         default=False
#     )
    
#     DIAL = models.BooleanField(
#         _("Chạy thận định kỳ"),
#         default=False
#     )
    
#     CATHETER = models.BooleanField(
#         _("Đặt catheter tĩnh mạch"),
#         default=False
#     )
    
#     SONDE = models.BooleanField(
#         _("Đặt sonde tiểu lưu"),
#         default=False
#     )
    
#     HOMEWOUNDCARE = models.BooleanField(
#         _("Chăm sóc vết thương tại nhà"),
#         default=False
#     )
    
#     LONGTERMCAREFACILITY = models.BooleanField(
#         _("Sống ở CSYT chăm sóc dài hạn"),
#         default=False
#     )
    
#     # 3. Sử dụng thuốc (corticoid, PPI, kháng sinh,...)?
#     MEDICATIONUSE = models.BooleanField(
#         _("Sử dụng thuốc (corticoid, PPI, kháng sinh,...)"),
#         default=False
#     )
    
#     # Thông tin hoàn thành
#     COMPLETEDBY = models.CharField(
#         _("Người hoàn thành"),
#         max_length=100,
#         null=True, blank=True
#     )
    
#     COMPLETEDDATE = models.DateField(
#         _("Ngày hoàn thành"),
#         null=True, blank=True
#     )
    
#     # Metadata
#     CREATEDAT = models.DateTimeField(auto_now_add=True)
#     UPDATEDAT = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         db_table = 'study_43en_contactfollowup28'
#         verbose_name = _("Theo dõi Contact ngày 28")
#         verbose_name_plural = _("Theo dõi Contact ngày 28")
    
#     def __str__(self):
#         return f"Follow Up 28 - {self.USUBJID}"
    
#     def save(self, *args, **kwargs):
#         # Auto-populate từ EnrollmentContact nếu cần
#         if not self.pk:
#             self.USUBJID = self.USUBJID
#         super().save(*args, **kwargs)

# class ContactFollowUp90(models.Model):
#     """
#     Model lưu trữ thông tin theo dõi người tiếp xúc gần tại thời điểm ngày 90
#     """
#     # Kết nối với EnrollmentContact
#     USUBJID = models.OneToOneField(
#         'study_43en.EnrollmentContact',
#         on_delete=models.CASCADE,
#         primary_key=True,
#         verbose_name=_('Contact Case')
#     )
    
#     # 4. Người tiếp xúc gần được đánh giá tại ngày 90?
#     ASSESSED_CHOICES = [
#         ('Yes', _('Có')),
#         ('No', _('Không')),
#         ('NA', _('Không áp dụng')),
#     ]
    
#     ASSESSED = models.CharField(
#         _("Người tiếp xúc gần được đánh giá tại ngày 90?"),
#         max_length=3,
#         choices=ASSESSED_CHOICES,
#         null=True, blank=True
#     )
    
#     ASSESSDATE = models.DateField(
#         _("Ngày đánh giá (nn/tt/nnnn)"),
#         null=True, blank=True
#     )
    
#     # 5. Người tiếp xúc gần có từng tiếp xúc với Chăm sóc Y tế kể từ lần đánh giá trước?
#     # (Tương tự như EnrollmentCase - các yếu tố nguy cơ)
#     HOSP2D = models.BooleanField(
#         _("Nằm viện ≥ 2 ngày"),
#         default=False
#     )
    
#     DIAL = models.BooleanField(
#         _("Chạy thận định kỳ"),
#         default=False
#     )
    
#     CATHETER = models.BooleanField(
#         _("Đặt catheter tĩnh mạch"),
#         default=False
#     )
    
#     SONDE = models.BooleanField(
#         _("Đặt sonde tiểu lưu"),
#         default=False
#     )
    
#     HOMEWOUNDCARE = models.BooleanField(
#         _("Chăm sóc vết thương tại nhà"),
#         default=False
#     )
    
#     LONGTERMCAREFACILITY = models.BooleanField(
#         _("Sống ở CSYT chăm sóc dài hạn"),
#         default=False
#     )
    
#     # 6. Sử dụng thuốc (corticoid, PPI, kháng sinh,...)?
#     MEDICATIONUSE = models.BooleanField(
#         _("Sử dụng thuốc (corticoid, PPI, kháng sinh,...)"),
#         default=False
#     )
    
#     # Thông tin hoàn thành
#     COMPLETEDBY = models.CharField(
#         _("Người hoàn thành"),
#         max_length=100,
#         null=True, blank=True
#     )
    
#     COMPLETEDDATE = models.DateField(
#         _("Ngày hoàn thành"),
#         null=True, blank=True
#     )
    
#     # Metadata
#     CREATEDAT = models.DateTimeField(auto_now_add=True)
#     UPDATEDAT = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         db_table = 'study_43en_contactfollowup90'
#         verbose_name = _("Theo dõi Contact ngày 90")
#         verbose_name_plural = _("Theo dõi Contact ngày 90")
    
#     def __str__(self):
#         return f"Follow Up 90 - {self.USUBJID}"
    
#     def save(self, *args, **kwargs):
#         # Auto-populate từ EnrollmentContact nếu cần
#         if not self.pk:
#             self.USUBJID = self.USUBJID
#         super().save(*args, **kwargs)


# class ContactMedicationHistory(models.Model):
#     """
#     Model lưu trữ lịch sử sử dụng thuốc của Contact trong Follow Up
#     """
#     # Relationship với Contact Follow Up
#     follow_up_28 = models.ForeignKey(
#         'study_43en.ContactFollowUp28',
#         on_delete=models.CASCADE,
#         related_name='medications_28',
#         null=True, blank=True,
#         verbose_name=_('Follow Up 28')
#     )
    
#     follow_up_90 = models.ForeignKey(
#         'study_43en.ContactFollowUp90',
#         on_delete=models.CASCADE,
#         related_name='medications_90',
#         null=True, blank=True,
#         verbose_name=_('Follow Up 90')
#     )
    
#     # Thông tin thuốc
#     MEDICATIONNAME = models.CharField(
#         _("Tên thuốc"), 
#         max_length=255,
#         null=True, blank=True
#     )
    
#     DOSAGE = models.CharField(
#         _("Liều thuốc"), 
#         max_length=100,
#         null=True, blank=True
#     )
#     USAGE_PERIOD = models.CharField(
#         _("Thời gian sử dụng"),
#         max_length=100,
#         null=True, blank=True
#     )

#     REASON = models.TextField(
#         _("Lý do sử dụng"), 
#         null=True, blank=True
#     )
    
#     # Metadata
#     CREATEDAT = models.DateTimeField(auto_now_add=True)
#     UPDATEDAT = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         db_table = 'study_43en_contactmedicationhistory'
#         ordering = ['CREATEDAT']
#         verbose_name = _("Lịch sử thuốc Contact")
#         verbose_name_plural = _("Lịch sử thuốc Contact")
    
#     def __str__(self):
#         return f"{self.MEDICATIONNAME} - {self.follow_up_28 or self.follow_up_90}"
    

# class ExpectedDates(models.Model):
#     USUBJID = models.OneToOneField(
#         'study_43en.EnrollmentCase', 
#         on_delete=models.CASCADE, 
#         related_name='expected_dates',
#         to_field='USUBJID',
#         verbose_name=_("Bệnh nhân")
#     )
#     ENROLLMENT_DATE = models.DateField(_("Enrollment Date"), null=True, blank=True)
#     V2_EXPECTED_FROM = models.DateField(_("V2 Expected From"), null=True, blank=True)
#     V2_EXPECTED_TO = models.DateField(_("V2 Expected To"), null=True, blank=True)
#     V2_EXPECTED_DATE = models.DateField(_("V2 Expected Date"), null=True, blank=True)
#     V3_EXPECTED_FROM = models.DateField(_("V3 Expected From"), null=True, blank=True)
#     V3_EXPECTED_TO = models.DateField(_("V3 Expected To"), null=True, blank=True)
#     V3_EXPECTED_DATE = models.DateField(_("V3 Expected Date"), null=True, blank=True)
#     V4_EXPECTED_FROM = models.DateField(_("V4 Expected From"), null=True, blank=True)
#     V4_EXPECTED_TO = models.DateField(_("V4 Expected To"), null=True, blank=True)
#     V4_EXPECTED_DATE = models.DateField(_("V4 Expected Date"), null=True, blank=True)
#     CREATED_AT = models.DateTimeField(auto_now_add=True)
#     UPDATED_AT = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'study_43en_expecteddates'
#         verbose_name = _("Ngày dự kiến")
#         verbose_name_plural = _("Ngày dự kiến")

#     def __str__(self):
#         return f"Lịch dự kiến của {self.USUBJID.USUBJID}"

#     def auto_map_from_calendar(self):
#         """
#         Tự động mapping dữ liệu từ ExpectedCalendar dựa trên ENROLLMENT_DATE
#         """
#         if not self.ENROLLMENT_DATE:
#             return False

#         calendar = ExpectedCalendar.objects.filter(ENROLLMENT_DATE=self.ENROLLMENT_DATE).first()
#         if not calendar:
#             return False

#         self.V2_EXPECTED_FROM = calendar.V2_EXPECTED_FROM
#         self.V2_EXPECTED_TO = calendar.V2_EXPECTED_TO
#         self.V2_EXPECTED_DATE = calendar.V2_EXPECTED_DATE
#         self.V3_EXPECTED_FROM = calendar.V3_EXPECTED_FROM
#         self.V3_EXPECTED_TO = calendar.V3_EXPECTED_TO
#         self.V3_EXPECTED_DATE = calendar.V3_EXPECTED_DATE
#         self.V4_EXPECTED_FROM = calendar.V4_EXPECTED_FROM
#         self.V4_EXPECTED_TO = calendar.V4_EXPECTED_TO
#         self.V4_EXPECTED_DATE = calendar.V4_EXPECTED_DATE
#         self.save(update_fields=[
#             'V2_EXPECTED_FROM', 'V2_EXPECTED_TO', 'V2_EXPECTED_DATE',
#             'V3_EXPECTED_FROM', 'V3_EXPECTED_TO', 'V3_EXPECTED_DATE',
#             'V4_EXPECTED_FROM', 'V4_EXPECTED_TO', 'V4_EXPECTED_DATE'
#         ])
#         return True

#     @classmethod
#     def auto_map_all(cls):
#         """
#         Mapping tất cả các bản ghi ExpectedDates từ ExpectedCalendar
#         """
#         for obj in cls.objects.all():
#             obj.auto_map_from_calendar()

# class ContactExpectedDates(models.Model):
#     USUBJID = models.OneToOneField(
#         'study_43en.EnrollmentContact', 
#         on_delete=models.CASCADE, 
#         related_name='expected_dates',
#         to_field='USUBJID',
#         verbose_name=_("Bệnh nhân")
#     )
#     ENROLLMENT_DATE = models.DateField(_("Enrollment Date"), null=True, blank=True)
#     V2_EXPECTED_FROM = models.DateField(_("V2 Expected From"), null=True, blank=True)
#     V2_EXPECTED_TO = models.DateField(_("V2 Expected To"), null=True, blank=True)
#     V2_EXPECTED_DATE = models.DateField(_("V2 Expected Date"), null=True, blank=True)
#     V3_EXPECTED_FROM = models.DateField(_("V3 Expected From"), null=True, blank=True)
#     V3_EXPECTED_TO = models.DateField(_("V3 Expected To"), null=True, blank=True)
#     V3_EXPECTED_DATE = models.DateField(_("V3 Expected Date"), null=True, blank=True)
#     CREATED_AT = models.DateTimeField(auto_now_add=True)
#     UPDATED_AT = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'study_43en_contactexpecteddates'
#         verbose_name = _("Ngày dự kiến (Contact)")
#         verbose_name_plural = _("Ngày dự kiến (Contact)")

#     def __str__(self):
#         return f"Lịch dự kiến của {self.USUBJID.USUBJID}"

#     def auto_map_from_calendar(self):
#         """
#         Tự động mapping dữ liệu từ ExpectedCalendar dựa trên ENROLLMENT_DATE
#         """
#         if not self.ENROLLMENT_DATE:
#             return False

#         calendar = ExpectedCalendar.objects.filter(ENROLLMENT_DATE=self.ENROLLMENT_DATE).first()
#         if not calendar:
#             return False

#         self.V2_EXPECTED_FROM = calendar.V2_EXPECTED_FROM
#         self.V2_EXPECTED_TO = calendar.V2_EXPECTED_TO
#         self.V2_EXPECTED_DATE = calendar.V2_EXPECTED_DATE
#         self.V3_EXPECTED_FROM = calendar.V3_EXPECTED_FROM
#         self.V3_EXPECTED_TO = calendar.V3_EXPECTED_TO
#         self.V3_EXPECTED_DATE = calendar.V3_EXPECTED_DATE
#         self.save(update_fields=[
#             'V2_EXPECTED_FROM', 'V2_EXPECTED_TO', 'V2_EXPECTED_DATE',
#             'V3_EXPECTED_FROM', 'V3_EXPECTED_TO', 'V3_EXPECTED_DATE'
#         ])
#         return True

#     @classmethod
#     def auto_map_all(cls):
#         """
#         Mapping tất cả các bản ghi ExpectedDates từ ExpectedCalendar
#         """
#         for obj in cls.objects.all():
#             obj.auto_map_from_calendar()


# class ExpectedCalendar(models.Model):
#     ENROLLMENT_DATE = models.DateField(verbose_name="Enrollment Date", null=True, blank=True)
#     V2_EXPECTED_FROM = models.DateField(verbose_name="V2 Expected From", null=True, blank=True)
#     V2_EXPECTED_TO = models.DateField(verbose_name="V2 Expected To", null=True, blank=True)
#     V2_EXPECTED_DATE = models.DateField(verbose_name="V2 Expected Date", null=True, blank=True)
#     V3_EXPECTED_FROM = models.DateField(verbose_name="V3 Expected From", null=True, blank=True)
#     V3_EXPECTED_TO = models.DateField(verbose_name="V3 Expected To", null=True, blank=True)
#     V3_EXPECTED_DATE = models.DateField(verbose_name="V3 Expected Date", null=True, blank=True)
#     V4_EXPECTED_FROM = models.DateField(verbose_name="V4 Expected From", null=True, blank=True)
#     V4_EXPECTED_TO = models.DateField(verbose_name="V4 Expected To", null=True, blank=True)
#     V4_EXPECTED_DATE = models.DateField(verbose_name="V4 Expected Date", null=True, blank=True)

#     class Meta:
#         db_table = 'study_43en_expectedcalender'
#         verbose_name = "Expected Calender"
#         verbose_name_plural = "Expected Calender"

#     def __str__(self):
#         return f"{self.ENROLLMENT_DATE}"
    


# class EndCaseCRF(models.Model):
#     USUBJID = models.OneToOneField(
#         'study_43en.EnrollmentCase',
#         on_delete=models.CASCADE,
#         to_field='USUBJID',
#         primary_key=True,
#         verbose_name=_("USUBJID")
#     )

#     ENDDATE = models.DateField(_("Ngày ghi nhận kết thúc"), null=True, blank=True)
#     ENDFORMDATE = models.DateField(_("Ngày kết thúc nghiên cứu"), null=True, blank=True)

#     VICOMPLETED = models.BooleanField(_("V1 (Tham gia nghiên cứu)"), default=False)
#     V2COMPLETED = models.BooleanField(_("V2 (Ngày 10±3)"), default=False)
#     V3COMPLETED = models.BooleanField(_("V3 (Ngày 28±3)"), default=False)
#     V4COMPLETED = models.BooleanField(_("V4 (Ngày 90±3)"), default=False)

#     WITHDRAWREASON_CHOICES = [
#         ('withdraw', _('Rút khỏi nghiên cứu')),
#         ('forced', _('Bị rút khỏi')),
#         ('na', _('Không áp dụng')),
#     ]
#     WITHDRAWREASON = models.CharField(
#         _("Lý do rút khỏi nghiên cứu"),
#         max_length=10,
#         choices=WITHDRAWREASON_CHOICES,
#         default='na'
#     )

#     INCOMPLETE_CHOICES = [
#         ('yes', _('Có')),
#         ('no', _('Không')),
#         ('na', _('Không áp dụng')),
#     ]
#     INCOMPLETE = models.CharField(
#         _("Không thể hoàn tất nghiên cứu"),
#         max_length=3,
#         choices=INCOMPLETE_CHOICES,
#         default='na'
#     )
#     INCOMPLETEDEATH = models.BooleanField(_("Người tham gia tử vong"), default=False)
#     INCOMPLETEMOVED = models.BooleanField(_("Người tham gia không thể đến địa điểm nghiên cứu ( ví dụ thay đổi nơi sinh sống)"), default=False)
#     INCOMPLETEOTHER = models.CharField(_("Khác, ghi rõ"), max_length=255, null=True, blank=True)

#     LOSTTOFOLLOWUP_CHOICES = [
#         ('yes', _('Có')),
#         ('no', _('Không')),
#         ('na', _('Không áp dụng')),
#     ]
#     LOSTTOFOLLOWUP = models.CharField(
#         _("Người tham gia bị mất liên lạc"),
#         max_length=3,
#         choices=LOSTTOFOLLOWUP_CHOICES,
#         default='na'
#     )

#     CREATEDAT = models.DateTimeField(auto_now_add=True)
#     UPDATEDAT = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'study_43en_endcasecrf'
#         verbose_name = _("Phiếu kết thúc nghiên cứu")
#         verbose_name_plural = _("Phiếu kết thúc nghiên cứu")

#     def __str__(self):
#         return f"END-CASE: {self.USUBJID.USUBJID}"
    

# class ContactEndCaseCRF(models.Model):
#     USUBJID = models.OneToOneField(
#         'study_43en.EnrollmentContact',
#         on_delete=models.CASCADE,
#         to_field='USUBJID',
#         primary_key=True,
#         verbose_name=_("USUBJID")
#     )

#     ENDDATE = models.DateField(_("Ngày ghi nhận kết thúc"), null=True, blank=True)
#     ENDFORMDATE = models.DateField(_("Ngày kết thúc nghiên cứu"), null=True, blank=True)

#     VICOMPLETED = models.BooleanField(_("V1 (Tham gia nghiên cứu)"), default=False)
#     V2COMPLETED = models.BooleanField(_("V2 (Ngày 28±3)"), default=False)
#     V3COMPLETED = models.BooleanField(_("V3 (Ngày 90±3)"), default=False)

#     WITHDRAWREASON_CHOICES = [
#         ('withdraw', _('Rút khỏi nghiên cứu')),
#         ('forced', _('Bị rút khỏi')),
#         ('na', _('Không áp dụng')),
#     ]
#     WITHDRAWREASON = models.CharField(
#         _("Lý do rút khỏi nghiên cứu"),
#         max_length=10,
#         choices=WITHDRAWREASON_CHOICES,
#         default='na'
#     )

#     INCOMPLETE_CHOICES = [
#         ('yes', _('Có')),
#         ('no', _('Không')),
#         ('na', _('Không áp dụng')),
#     ]
#     INCOMPLETE = models.CharField(
#         _("Không thể hoàn tất nghiên cứu"),
#         max_length=3,
#         choices=INCOMPLETE_CHOICES,
#         default='na'
#     )
#     INCOMPLETEDEATH = models.BooleanField(_("Người tham gia tử vong"), default=False)
#     INCOMPLETEMOVED = models.BooleanField(_("Người tham gia không thể đến địa điểm nghiên cứu (ví dụ thay đổi nơi sinh sống)"), default=False)
#     INCOMPLETEOTHER = models.CharField(_("Khác, ghi rõ"), max_length=255, null=True, blank=True)

#     LOSTTOFOLLOWUP_CHOICES = [
#         ('yes', _('Có')),
#         ('no', _('Không')),
#         ('na', _('Không áp dụng')),
#     ]
#     LOSTTOFOLLOWUP = models.CharField(
#         _("Người tham gia bị mất liên lạc"),
#         max_length=3,
#         choices=LOSTTOFOLLOWUP_CHOICES,
#         default='na'
#     )

#     CREATEDAT = models.DateTimeField(auto_now_add=True)
#     UPDATEDAT = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = 'study_43en_contactendcasecrf'
#         verbose_name = _("Phiếu kết thúc nghiên cứu (Contact)")
#         verbose_name_plural = _("Phiếu kết thúc nghiên cứu (Contact)")

#     def __str__(self):
#         return f"CONTACT-END-CASE: {self.USUBJID.USUBJID}"
    

# class AuditLog(models.Model):
#     """Model lưu trữ nhật ký hoạt động của người dùng"""
#     ACTION_CHOICES = (
#         ('CREATE', 'Tạo mới'),
#         ('UPDATE', 'Cập nhật'),
#         ('DELETE', 'Xóa'),
#         ('VIEW', 'Xem'),
#     )
    
#     user = models.ForeignKey(
#         User, 
#         on_delete=models.SET_NULL, 
#         null=True, 
#         blank=True, 
#         verbose_name=_('Người dùng'),
#         db_constraint=False
#     )
#     username = models.CharField(max_length=150, null=True, blank=True, verbose_name=_('Tên người dùng'))
#     timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('Thời gian'))
#     action = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name=_('Hành động'))
#     model_name = models.CharField(max_length=100, verbose_name=_('Tên model/bảng'))
#     patient_id = models.CharField(max_length=100, verbose_name=_('ID bệnh nhân'))
#     old_data = models.JSONField(null=True, blank=True, verbose_name=_('Dữ liệu cũ'))
#     new_data = models.JSONField(null=True, blank=True, verbose_name=_('Dữ liệu mới'))
#     ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_('Địa chỉ IP'))
#     reason = models.TextField(null=True, blank=True, verbose_name="Lý do thay đổi") 
#     reasons_json = models.JSONField(null=True, blank=True, verbose_name="Lý do từng trường") 
    
#     class Meta:
#         verbose_name = _('Nhật ký hoạt động')
#         verbose_name_plural = _('Nhật ký hoạt động')
#         ordering = ['-timestamp']
    
#     def __str__(self):
#         username = self.username or (self.user.username if self.user else "unknown")
#         return f"{username} - {self.action} {self.model_name} #{self.patient_id} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    
#     def save(self, *args, **kwargs):
#         if self.user and not self.username:
#             self.username = self.user.username
#         super().save(*args, **kwargs)
    
#     def get_old_data_dict(self):
#         if not self.old_data:
#             return {}
#         if isinstance(self.old_data, dict):
#             return self.old_data
#         return flatten_formset_data(safe_json_loads(self.old_data, {}))

#     def get_new_data_dict(self):
#         if not self.new_data:
#             return {}
#         if isinstance(self.new_data, dict):
#             return self.new_data
#         return flatten_formset_data(safe_json_loads(self.new_data, {}))

# def flatten_formset_data(data):
#     """Chuyển các mảng formset thành dict key-value"""
#     if not isinstance(data, dict):
#         return {}
            
#     result = {}
    
#     if 'main' in data:
#         for k, v in data.get('main', {}).items():
#             result[k] = v
            
#         antibiotics = data.get('antibiotic', [])
#         for idx, item in enumerate(antibiotics):
#             if item:
#                 for field, value in item.items():
#                     result[f"antibiotic_{idx}_{field}"] = value
                    
#         rehospitalizations = data.get('rehospitalization', [])
#         for idx, item in enumerate(rehospitalizations):
#             if item:
#                 for field, value in item.items():
#                     result[f"rehospitalization_{idx}_{field}"] = value
#     else:
#         for k, v in data.items():
#             if isinstance(v, list):
#                 for idx, row in enumerate(v):
#                     if row:
#                         for field, value in row.items():
#                             result[f"{k}_{idx}_{field}"] = value
#             else:
#                 result[k] = v
                
#     return result
    
#     # def get_changes(self):
#     #     """Trả về danh sách các thay đổi giữa dữ liệu cũ và mới"""
#     #     old_data = self.get_old_data_dict()
#     #     new_data = self.get_new_data_dict()
        
#     #     changes = []
#     #     # Tìm các trường đã thay đổi
#     #     for key in set(old_data.keys()) | set(new_data.keys()):
#     #         old_value = old_data.get(key)
#     #         new_value = new_data.get(key)
            
#     #         if old_value != new_value:
#     #             changes.append({
#     #                 'field': key,
#     #                 'old_value': old_value,
#     #                 'new_value': new_value
#     #             })
                
#     #     return changes
    


# class FollowUpStatus(models.Model):
#     """Model hiển thị trạng thái theo dõi bệnh nhân và người tiếp xúc"""
#     SUBJECT_TYPE_CHOICES = [
#         ('PATIENT', 'Bệnh nhân'),
#         ('CONTACT', 'Người tiếp xúc'),
#     ]
    
#     VISIT_CHOICES = [
#         ('V2', 'Thăm khám V2'),
#         ('V3', 'Thăm khám V3'),
#         ('V4', 'Thăm khám V4'),
#     ]
    
#     STATUS_CHOICES = [
#         ('COMPLETED', 'Hoàn thành'),
#         ('LATE', 'Trễ hẹn'),
#         ('MISSED', 'Không hoàn thành'),
#         ('UPCOMING', 'Sắp tới'),
#     ]
    
#     # Thông tin đối tượng
#     USUBJID = models.CharField(_("USUBJID"), max_length=50)
#     SUBJECT_TYPE = models.CharField(_("Loại đối tượng"), max_length=10, choices=SUBJECT_TYPE_CHOICES)
#     INITIAL = models.CharField(_("Viết tắt"), max_length=50, blank=True, null=True)
    
#     # Thông tin lần thăm
#     VISIT = models.CharField(_("Lần thăm"), max_length=10, choices=VISIT_CHOICES)
    
#     # Khoảng thời gian dự kiến - lấy từ ExpectedDates/ContactExpectedDates
#     EXPECTED_FROM = models.DateField(_("Từ ngày"), null=True, blank=True)
#     EXPECTED_TO = models.DateField(_("Đến ngày"), null=True, blank=True)
#     EXPECTED_DATE = models.DateField(_("Ngày dự kiến"), null=True, blank=True)
    
#     # Thông tin thực tế
#     ACTUAL_DATE = models.DateField(_("Ngày thực tế"), null=True, blank=True)
#     STATUS = models.CharField(_("Trạng thái"), max_length=20, choices=STATUS_CHOICES, default='UPCOMING')
    
#     # Thông tin liên hệ
#     PHONE = models.CharField(_("Điện thoại"), max_length=20, blank=True, null=True)
    
#     # Metadata
#     CREATED_AT = models.DateTimeField(auto_now_add=True)
#     UPDATED_AT = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         unique_together = ('USUBJID', 'SUBJECT_TYPE', 'VISIT')
#         verbose_name = _("Trạng thái theo dõi")
#         verbose_name_plural = _("Trạng thái theo dõi")
#         ordering = ['SUBJECT_TYPE', 'EXPECTED_DATE']
    
#     def __str__(self):
#         subject_type = "Bệnh nhân" if self.SUBJECT_TYPE == "PATIENT" else "Người tiếp xúc"
#         return f"{self.USUBJID} ({subject_type}) - {self.get_VISIT_display()}"
    
#     def save(self, *args, **kwargs):
#         # Nếu STATUS đã được set từ signals, không tính toán lại
#         update_fields = kwargs.get('update_fields', None)
#         if update_fields and 'STATUS' in update_fields:
#             super().save(*args, **kwargs)
#             return
            
#         # Không tự tính toán STATUS nếu nó đã được set là COMPLETED hoặc MISSED
#         if self.STATUS in ['COMPLETED', 'MISSED']:
#             super().save(*args, **kwargs)
#             return
            
#         # Cập nhật trạng thái dựa trên ngày thực tế và khoảng thời gian
#         today = date.today()
        
#         if self.ACTUAL_DATE:
#             self.STATUS = 'COMPLETED'
#         elif self.EXPECTED_TO and today > self.EXPECTED_TO:
#             self.STATUS = 'MISSED'
#         elif self.EXPECTED_FROM and today >= self.EXPECTED_FROM:
#             self.STATUS = 'LATE'
#         else:
#             self.STATUS = 'UPCOMING'
        
#         super().save(*args, **kwargs)