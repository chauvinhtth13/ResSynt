import logging
from datetime import date

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.translation import gettext as _

# Import models từ study app
from backends.studies.study_43en.models.patient import (
    ScreeningCase, EnrollmentCase, DischargeCase, EndCaseCRF,FollowUpCase, FollowUpCase90,
    ClinicalCase,SampleCollection,CLI_Microbiology,LaboratoryTest,

)
from backends.studies.study_43en.models.contact import (
    ScreeningContact, EnrollmentContact, 
    ContactFollowUp28, ContactFollowUp90,
    ContactEndCaseCRF, ContactSampleCollection
)





# Import utils từ study app
from backends.studies.study_43en.utils.audit_log_utils import (
    safe_json_loads
)
from backends.studies.study_43en.utils import get_site_filtered_object_or_404

logger = logging.getLogger(__name__)


import pandas as pd
from django.http import HttpResponse
from django.apps import apps
from io import BytesIO
from django.contrib.postgres.fields import JSONField
from django.db.models import DateTimeField
from django.http import HttpResponse







@login_required
def patient_list(request):
    """Danh sách các bệnh nhân đã tham gia nghiên cứu"""
    query = request.GET.get('q', '')
    
    # Lấy site_id từ session
    site_id = request.session.get('selected_site_id', 'all')
    print(f"DEBUG - patient_list - Using site_id: {site_id}")
    
    # Lọc bệnh nhân đủ điều kiện và đã đồng ý
    cases = ScreeningCase.site_objects.filter_by_site(site_id).filter(
        is_confirmed=True 
    ).order_by('USUBJID')
    
    # Tìm kiếm
    if query:
        cases = cases.filter(
            Q(USUBJID__icontains=query) | 
            Q(INITIAL__icontains=query)
        )
    
    # Thống kê
    total_patients = cases.count()
    
    # Phân trang
    paginator = Paginator(cases, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Thêm thông tin trạng thái
    for case in page_obj:
        case.has_enrollment = EnrollmentCase.objects.filter(USUBJID=case).exists()
        enrollment = EnrollmentCase.objects.filter(USUBJID=case).first()
        case.has_clinical = enrollment and ClinicalCase.objects.filter(USUBJID=enrollment).exists()
    
    context = {
        'page_obj': page_obj,
        'total_patients': total_patients,
        'query': query,
        'view_type': 'patients',
        'is_paginated': page_obj.has_other_pages(),
    }
    
    return render(request, 'studies/study_43en/CRF/patient_list.html', context)

@login_required
def patient_detail(request, usubjid):
    """View chi tiết bệnh nhân, bổ sung expected dates vào context"""
    # Lấy site_id từ session hoặc request, mặc định là 'all'
    site_id = request.session.get('selected_site_id', 'all')
    print(f"DEBUG - patient_detail - Using site_id: {site_id}")
    
    
    # Sử dụng hàm tiện ích mới với site_id
    screeningcase = get_site_filtered_object_or_404(ScreeningCase, site_id, USUBJID=usubjid)
    
    # EnrollmentCase
    try:
        # Sử dụng filter_by_site từ site_objects manager
        if site_id and site_id != 'all':
            enrollmentcase = EnrollmentCase.site_objects.filter_by_site(site_id).get(USUBJID=screeningcase)
        else:
            enrollmentcase = EnrollmentCase.objects.get(USUBJID=screeningcase)
            
        has_enrollment = True
        # Lấy expected dates nếu có
        try:
            expecteddates = enrollmentcase.expected_dates
        except Exception:
            expecteddates = None
    except EnrollmentCase.DoesNotExist:
        enrollmentcase = None
        has_enrollment = False
        expecteddates = None
    
    # ClinicalCase
    try:
        if site_id:
            clinicalcase = ClinicalCase.site_objects.filter_by_site(site_id).get(USUBJID=enrollmentcase)
        else:
            clinicalcase = ClinicalCase.objects.get(USUBJID=enrollmentcase)
        has_clinical = True
    except ClinicalCase.DoesNotExist:
        clinicalcase = None
        has_clinical = False
    
    # LaboratoryTest, MicrobiologyCulture, SampleCollection
    if site_id:
        laboratory_count = LaboratoryTest.site_objects.filter_by_site(site_id).filter(USUBJID=enrollmentcase).count() if enrollmentcase else 0
        microbiology_count = CLI_Microbiology.site_objects.filter_by_site(site_id).filter(USUBJID=enrollmentcase).count() if enrollmentcase else 0
        sample_count = SampleCollection.site_objects.filter_by_site(site_id).filter(USUBJID=enrollmentcase).count() if enrollmentcase else 0
    else:
        laboratory_count = LaboratoryTest.objects.filter(USUBJID=enrollmentcase).count() if enrollmentcase else 0
        microbiology_count = CLI_Microbiology.objects.filter(USUBJID=enrollmentcase).count() if enrollmentcase else 0
        sample_count = SampleCollection.objects.filter(USUBJID=enrollmentcase).count() if enrollmentcase else 0
    
    has_laboratory_tests = laboratory_count > 0
    has_microbiology_cultures = microbiology_count > 0

    # FollowUpCase 28 ngày
    try:
        if site_id:
            followupcase = FollowUpCase.site_objects.filter_by_site(site_id).get(USUBJID=enrollmentcase)
        else:
            followupcase = FollowUpCase.objects.get(USUBJID=enrollmentcase)
        has_followup = True
    except FollowUpCase.DoesNotExist:
        followupcase = None
        has_followup = False
    
    # FollowUpCase 90 ngày
    try:
        if site_id:
            followupcase90 = FollowUpCase90.site_objects.filter_by_site(site_id).get(USUBJID=enrollmentcase)
        else:
            followupcase90 = FollowUpCase90.objects.get(USUBJID=enrollmentcase)
        has_followup90 = True
    except FollowUpCase90.DoesNotExist:
        followupcase90 = None
        has_followup90 = False
    
    # DischargeCase
    try:
        if site_id:
            dischargecase = DischargeCase.site_objects.filter_by_site(site_id).get(USUBJID=enrollmentcase)
        else:
            dischargecase = DischargeCase.objects.get(USUBJID=enrollmentcase)
        has_discharge = True
    except DischargeCase.DoesNotExist:
        dischargecase = None
        has_discharge = False
        
    # EndCaseCRF - Thêm phần này
    try:
        if site_id:
            endcasecrf = EndCaseCRF.site_objects.filter_by_site(site_id).get(USUBJID=enrollmentcase)
        else:
            endcasecrf = EndCaseCRF.objects.get(USUBJID=enrollmentcase)
        has_endcasecrf = True
    except EndCaseCRF.DoesNotExist:
        endcasecrf = None
        has_endcasecrf = False

    # Số ngày từ khi enrollment
    if has_enrollment and enrollmentcase.ENRDATE:
        days_since_enrollment = (date.today() - enrollmentcase.ENRDATE).days
    else:
        days_since_enrollment = 0
    
    
    context = {
        'screeningcase': screeningcase,
        'enrollmentcase': enrollmentcase,
        'has_enrollment': has_enrollment,
        'clinicalcase': clinicalcase,
        'has_clinical': has_clinical,
        'laboratory_count': laboratory_count,
        'has_laboratory_tests': has_laboratory_tests,
        'microbiology_count': microbiology_count,
        'has_microbiology_cultures': has_microbiology_cultures,
        'sample_count': sample_count,
        'followupcase': followupcase,
        'has_followup': has_followup,
        'followupcase90': followupcase90,
        'has_followup90': has_followup90,
        'dischargecase': dischargecase, 
        'has_discharge': has_discharge, 
        'days_since_enrollment': days_since_enrollment,
        'expecteddates': expecteddates,  
        'endcasecrf': endcasecrf,        
        'has_endcasecrf': has_endcasecrf 
    }
    
    return render(request, 'studies/study_43en/CRF/patient_detail.html', context)






@login_required
def contact_list(request):
    query = request.GET.get('q', '')
    
    # Lấy site_id từ session để lọc theo site, mặc định là 'all'
    site_id = request.session.get('selected_site_id', 'all')
    print(f"DEBUG - contact_list - Using site_id: {site_id}")
    
    eligible_screening_contacts = ScreeningContact.site_objects.filter_by_site(site_id).filter(
        CONSENTTOSTUDY=True,
        LIVEIN5DAYS3MTHS=True,
        MEALCAREONCEDAY=True
    ).select_related('enrollmentcontact')
    
    if query:
        eligible_screening_contacts = eligible_screening_contacts.filter(
            Q(USUBJID__icontains=query) |
            Q(INITIAL__icontains=query)
        )
    
    # Sắp xếp theo USUBJID từ nhỏ đến lớn
    eligible_screening_contacts = eligible_screening_contacts.order_by('USUBJID')
    
    # Sắp xếp theo ngày sàng lọc
    eligible_screening_contacts = eligible_screening_contacts.order_by('-SCREENINGFORMDATE')

    # Thống kê
    total_contacts = eligible_screening_contacts.count()
    enrolled_contacts = eligible_screening_contacts.filter(enrollmentcontact__isnull=False).count()
    not_enrolled_contacts = total_contacts - enrolled_contacts

    # Phân trang
    paginator = Paginator(eligible_screening_contacts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Thêm thông tin trạng thái cho mỗi contact
    for contact in page_obj:
        # Kiểm tra có enrollment không
        contact.has_enrollment = hasattr(contact, 'enrollmentcontact') and contact.enrollmentcontact is not None
        
        # Kiểm tra có sample collection không
        if contact.has_enrollment:
            contact.has_sample = ContactSampleCollection.objects.filter(USUBJID=contact.enrollmentcontact).exists()
        else:
            contact.has_sample = False

    context = {
        'page_obj': page_obj,
        'total_contacts': total_contacts,
        'enrolled_contacts': enrolled_contacts,
        'not_enrolled_contacts': not_enrolled_contacts,
        'query': query,
        'view_type': 'contacts'
    }

    return render(request, 'studies/study_43en/CRF/contact_list.html', context)


@login_required
def contact_detail(request, usubjid):
    """View chi tiết contact"""
    try:
        screening_contact = ScreeningContact.objects.get(USUBJID=usubjid)
        
        # Kiểm tra enrollment contact
        try:
            enrollment_contact = EnrollmentContact.objects.get(USUBJID=screening_contact)
            has_enrollment = True
            try:
                contactexpecteddates = enrollment_contact.expected_dates
            except Exception:
                contactexpecteddates = None
        except EnrollmentContact.DoesNotExist:
            enrollment_contact = None
            has_enrollment = False
            contactexpecteddates = None

        # Kiểm tra sample collection
        has_sample = False
        sample_collection = None
        sample_count = 0
        if has_enrollment:
            # Kiểm tra xem có mẫu nào không thay vì lấy mẫu cụ thể
            sample_count = ContactSampleCollection.objects.filter(USUBJID=enrollment_contact).count()
            has_sample = sample_count > 0
            if has_sample:
                # Lấy mẫu đầu tiên để hiển thị thông tin
                sample_collection = ContactSampleCollection.objects.filter(USUBJID=enrollment_contact).first()

        # Kiểm tra follow-up 28 ngày
        followup_28 = None
        if has_enrollment:
            try:
                followup_28 = ContactFollowUp28.objects.get(USUBJID=enrollment_contact)
            except ContactFollowUp28.DoesNotExist:
                pass

        # Kiểm tra follow-up 90 ngày
        followup_90 = None
        if has_enrollment:
            try:
                followup_90 = ContactFollowUp90.objects.get(USUBJID=enrollment_contact)
            except ContactFollowUp90.DoesNotExist:
                pass

        # ContactEndCaseCRF
        try:
            contactendcasecrf = ContactEndCaseCRF.objects.get(USUBJID=enrollment_contact)
            has_contactendcasecrf = True
        except ContactEndCaseCRF.DoesNotExist:
            contactendcasecrf = None
            has_contactendcasecrf = False
        

        context = {
            'screening_contact': screening_contact,
            'enrollment_contact': enrollment_contact,
            'has_enrollment': has_enrollment,
            'sample_collection': sample_collection,
            'has_sample': has_sample,
            'sample_count': sample_count,
            'followup_28': followup_28,
            'followup_90': followup_90,
            'contactendcasecrf': contactendcasecrf,
            'has_contactendcasecrf': has_contactendcasecrf,
            'contactexpecteddates': contactexpecteddates
        }

        return render(request, 'studies/study_43en/CRF/contact_detail.html', context)
        
    except ScreeningContact.DoesNotExist:
        messages.error(request, f'Không tìm thấy contact {usubjid}')
        return redirect('study_43en:screening_contact_list')
    





def export_to_excel(request):
    # Tạo buffer để lưu file Excel
    buffer = BytesIO()
    writer = pd.ExcelWriter(buffer, engine='openpyxl')

    # Lấy tất cả các model
    models = apps.get_models()

    # Danh sách các trường nhạy cảm cần loại bỏ
    sensitive_fields = ['FULLNAME', 'PHONE', 'ADDRESS', 'MEDRECORDID']

    # Danh sách các bệnh nền cần kiểm tra
    underlying_conditions = [
        'DIABETES', 'COPD', 'HEPATITIS', 'CAD', 'KIDNEYDISEASE', 
        'ASTHMA', 'CIRRHOSIS', 'HYPERTENSION', 'AUTOIMMUNE', 
        'CANCER', 'ALCOHOLISM', 'HIV', 'ADRENALINSUFFICIENCY', 
        'BEDRIDDEN', 'PEPTICULCER', 'COLITIS_IBS', 'SENILITY',
        'MALNUTRITION_WASTING', 'OTHERDISEASE'
    ]
    
    # Danh sách triệu chứng cơ bản cần kiểm tra (từ ClinicalCase.LISTBASICSYMTOMS)
    basic_symptoms = [
        'FEVER', 'FATIGUE', 'MUSCLEPAIN', 'LOSSAPPETITE', 'COUGH', 
        'CHESTPAIN', 'SHORTBREATH', 'JAUNDICE', 'PAINURINATION', 'BLOODYURINE',
        'CLOUDYURINE', 'EPIGASTRICPAIN', 'LOWERABDPAIN', 'FLANKPAIN', 
        'URINARYHESITANCY', 'SUBCOSTALPAIN', 'HEADACHE', 'POORCONTACT', 
        'DELIRIUMAGITATION', 'VOMITING', 'SEIZURES', 'EYEPAIN', 'REDEYES', 
        'NAUSEA', 'BLURREDVISION', 'SKINLESIONS'
    ]
    
    # Danh sách triệu chứng lâm sàng cần kiểm tra (từ ClinicalCase.LISTCLINISYMTOMS)
    clinical_symptoms = [
        'FEVER_2', 'RASH', 'SKINBLEEDING', 'MUCOSALBLEEDING', 'SKINLESIONS_2',
        'LUNGCRACKLES', 'CONSOLIDATIONSYNDROME', 'PLEURALEFFUSION', 'PNEUMOTHORAX',
        'HEARTMURMUR', 'ABNORHEARTSOUNDS', 'JUGULARVEINDISTENTION', 'LIVERFAILURESIGNS',
        'PORTALHYPERTENSIONSIGNS', 'HEPATOSPLENOMEGALY', 'CONSCIOUSNESSDISTURBANCE',
        'LIMBWEAKNESSPARALYSIS', 'CRANIALNERVEPARALYSIS', 'MENINGEALSIGNS',
        'REDEYES_2', 'HYPOPYON', 'EDEMA', 'CUSHINGOIDAPPEARANCE',
        'EPIGASTRICPAIN_2', 'LOWERABDPAIN_2', 'FLANKPAIN_2', 'SUBCOSTALPAIN_2'
    ]

    for model in models:
        try:
            # Lấy tất cả dữ liệu từ model
            queryset = model.objects.all()
            if not queryset.exists():
                continue
                
            # Chuyển thành list trước khi tạo DataFrame để tránh lỗi
            data = list(queryset.values())
            df = pd.DataFrame(data)
            
            # Loại bỏ các trường nhạy cảm
            for field in sensitive_fields:
                if field in df.columns:
                    df = df.drop(field, axis=1)
            
            # Theo dõi nếu là model EnrollmentCase hoặc ClinicalCase để xử lý đặc biệt
            is_enrollment_case = model.__name__ == 'EnrollmentCase'
            is_clinical_case = model.__name__ == 'ClinicalCase'
            
            # Biến lưu trữ tạm thời trường OTHERDISEASESPECIFY và SPECIFYOTHERSYMPTOM
            otherdiseasespecify_values = None
            specifyothersymptom_values = None
            specifyothersymptom_2_values = None
            
            if is_enrollment_case and 'OTHERDISEASESPECIFY' in df.columns:
                otherdiseasespecify_values = df['OTHERDISEASESPECIFY'].copy()
                
            if is_clinical_case:
                if 'SPECIFYOTHERSYMPTOM' in df.columns:
                    specifyothersymptom_values = df['SPECIFYOTHERSYMPTOM'].copy()
                if 'SPECIFYOTHERSYMPTOM_2' in df.columns:
                    specifyothersymptom_2_values = df['SPECIFYOTHERSYMPTOM_2'].copy()
            
            # Xử lý các trường đặc biệt
            for field in model._meta.get_fields():
                field_name = field.name
                
                # Bỏ qua các trường nhạy cảm
                if field_name in sensitive_fields:
                    continue
                    
                if field_name in df.columns:
                    # Xử lý trường LISTUNDERLYING đặc biệt (danh sách bệnh nền)
                    if field_name == 'LISTUNDERLYING' and 'LISTUNDERLYING' in df.columns:
                        # Tạo các cột mới cho từng bệnh nền
                        for condition in underlying_conditions:
                            if condition != 'OTHERDISEASE':  # Tạm thời bỏ qua OTHERDISEASE
                                df[condition] = False  # Mặc định là False
                            
                        # Cập nhật giá trị TRUE cho các bệnh có trong danh sách
                        for idx, row in df.iterrows():
                            list_value = row.get('LISTUNDERLYING')
                            if isinstance(list_value, (list, str)) and list_value:
                                try:
                                    # Nếu là chuỗi, chuyển thành list
                                    if isinstance(list_value, str):
                                        conditions_list = safe_json_loads(list_value)
                                    else:
                                        conditions_list = list_value
                                    
                                    # Cập nhật các cột điều kiện
                                    if isinstance(conditions_list, list):
                                        for condition in conditions_list:
                                            if condition in underlying_conditions and condition != 'OTHERDISEASE':
                                                df.at[idx, condition] = True
                                except Exception as e:
                                    print(f"Lỗi khi xử lý LISTUNDERLYING của {model.__name__}: {str(e)}")
                        
                        # Xóa cột LISTUNDERLYING gốc sau khi đã chuyển đổi
                        df = df.drop('LISTUNDERLYING', axis=1)
                        
                        # Thêm lại OTHERDISEASE vào cuối các trường bệnh nền
                        df['OTHERDISEASE'] = False
                        for idx, row in df.iterrows():
                            list_value = row.get('LISTUNDERLYING')
                            if isinstance(list_value, (list, str)) and list_value:
                                try:
                                    if isinstance(list_value, str):
                                        conditions_list = safe_json_loads(list_value)
                                    else:
                                        conditions_list = list_value
                                    
                                    if isinstance(conditions_list, list) and 'OTHERDISEASE' in conditions_list:
                                        df.at[idx, 'OTHERDISEASE'] = True
                                except Exception:
                                    pass
                                    
                    # Xử lý trường LISTBASICSYMTOMS đặc biệt (danh sách triệu chứng nhóm 1)
                    elif field_name == 'LISTBASICSYMTOMS' and 'LISTBASICSYMTOMS' in df.columns:
                        # Tạo các cột mới cho từng triệu chứng
                        for symptom in basic_symptoms:
                            df[symptom] = False  # Mặc định là False
                            
                        # Cập nhật giá trị TRUE cho các triệu chứng có trong danh sách
                        for idx, row in df.iterrows():
                            list_value = row.get('LISTBASICSYMTOMS')
                            if isinstance(list_value, (list, str)) and list_value:
                                try:
                                    # Nếu là chuỗi, chuyển thành list
                                    if isinstance(list_value, str):
                                        symptoms_list = safe_json_loads(list_value)
                                    else:
                                        symptoms_list = list_value
                                    
                                    # Cập nhật các cột triệu chứng
                                    if isinstance(symptoms_list, list):
                                        for symptom in symptoms_list:
                                            if symptom in basic_symptoms:
                                                df.at[idx, symptom] = True
                                except Exception as e:
                                    print(f"Lỗi khi xử lý LISTBASICSYMTOMS của {model.__name__}: {str(e)}")
                        
                        # Xóa cột LISTBASICSYMTOMS gốc sau khi đã chuyển đổi
                        df = df.drop('LISTBASICSYMTOMS', axis=1)
                        
                    # Xử lý trường LISTCLINISYMTOMS đặc biệt (danh sách triệu chứng nhóm 2)
                    elif field_name == 'LISTCLINISYMTOMS' and 'LISTCLINISYMTOMS' in df.columns:
                        # Tạo các cột mới cho từng triệu chứng lâm sàng
                        for symptom in clinical_symptoms:
                            df[symptom] = False  # Mặc định là False
                            
                        # Cập nhật giá trị TRUE cho các triệu chứng có trong danh sách
                        for idx, row in df.iterrows():
                            list_value = row.get('LISTCLINISYMTOMS')
                            if isinstance(list_value, (list, str)) and list_value:
                                try:
                                    # Nếu là chuỗi, chuyển thành list
                                    if isinstance(list_value, str):
                                        symptoms_list = safe_json_loads(list_value)
                                    else:
                                        symptoms_list = list_value
                                    
                                    # Cập nhật các cột triệu chứng
                                    if isinstance(symptoms_list, list):
                                        for symptom in symptoms_list:
                                            if symptom in clinical_symptoms:
                                                df.at[idx, symptom] = True
                                except Exception as e:
                                    print(f"Lỗi khi xử lý LISTCLINISYMTOMS của {model.__name__}: {str(e)}")
                        
                        # Xóa cột LISTCLINISYMTOMS gốc sau khi đã chuyển đổi
                        df = df.drop('LISTCLINISYMTOMS', axis=1)
                            
                    elif isinstance(field, JSONField):
                        # Chuyển JSONB thành chuỗi cho các trường JSON khác
                        df[field_name] = df[field_name].apply(lambda x: str(x) if x is not None else '')
                    elif isinstance(field, DateTimeField):
                        # Định dạng timestamp
                        df[field_name] = df[field_name].apply(
                            lambda x: x.strftime('%Y-%m-%d %H:%M:%S %z') if pd.notnull(x) else ''
                        )
            
            # Xử lý đặc biệt cho EnrollmentCase sau khi đã tạo tất cả các cột
            if is_enrollment_case:
                # Sắp xếp lại các cột để các trường bệnh nền liền sau UNDERLYINGCONDS
                all_columns = df.columns.tolist()
                
                # Lọc ra các cột bệnh nền và các cột còn lại
                disease_columns = [col for col in all_columns if col in underlying_conditions]
                
                # Xóa các cột bệnh nền khỏi all_columns để sắp xếp lại
                other_columns = [col for col in all_columns if col not in disease_columns]
                
                # Tìm vị trí của UNDERLYINGCONDS
                try:
                    underlyingconds_index = other_columns.index('UNDERLYINGCONDS')
                    # Sắp xếp lại thứ tự các cột
                    new_columns = other_columns[:underlyingconds_index + 1] + disease_columns + other_columns[underlyingconds_index + 1:]
                    
                    # Áp dụng thứ tự cột mới
                    df = df[new_columns]
                    
                    # Khôi phục lại giá trị OTHERDISEASESPECIFY nếu bị mất
                    if otherdiseasespecify_values is not None and 'OTHERDISEASESPECIFY' in df.columns:
                        df['OTHERDISEASESPECIFY'] = otherdiseasespecify_values
                except ValueError:
                    # Nếu không tìm thấy UNDERLYINGCONDS, giữ nguyên thứ tự cột
                    pass
                        
            # Xử lý đặc biệt cho ClinicalCase - khôi phục các giá trị SPECIFYOTHERSYMPTOM
            if is_clinical_case:
                # Khôi phục lại giá trị SPECIFYOTHERSYMPTOM nếu bị mất
                if specifyothersymptom_values is not None:
                    df['SPECIFYOTHERSYMPTOM'] = specifyothersymptom_values
                
                # Khôi phục lại giá trị SPECIFYOTHERSYMPTOM_2 nếu bị mất
                if specifyothersymptom_2_values is not None:
                    df['SPECIFYOTHERSYMPTOM_2'] = specifyothersymptom_2_values
                    
                # Sắp xếp lại các cột theo thứ tự CSV gốc
                try:
                    # Lấy mẫu thứ tự cột từ CSV
                    csv_column_order = [
                        'EVENT', 'USUBJID', 'STUDYID', 'SITEID', 'SUBJID', 'INITIAL',
                        'ADMISDATE', 'ADMISREASON', 'SYMPTOMONSETDATE', 'ADMISDEPT', 'OUTPATIENT_ERDEPT',
                        'SYMPTOMADMISDEPT', 'AWARENESS', 'GCS', 'EYES', 'MOTOR', 'VERBAL',
                        'PULSE', 'AMPLITUDE', 'CAPILLARYMOIS', 'CRT', 'TEMPERATURE', 'BLOODPRESSURE_SYS',
                        'BLOODPRESSURE_DIAS', 'RESPRATE', 'SPO2', 'FIO2', 'RESPPATTERN',
                        'RESPPATTERNOTHERSPEC', 'RESPSUPPORT', 'VASOMEDS', 'HYPOTENSION',
                        'QSOFA', 'NEWS2', 
                        # Triệu chứng cơ bản (FEVER, FATIGUE, etc.)
                        'FEVER', 'FATIGUE', 'MUSCLEPAIN', 'LOSSAPPETITE', 'COUGH', 
                        'CHESTPAIN', 'SHORTBREATH', 'JAUNDICE', 'PAINURINATION', 'BLOODYURINE',
                        'CLOUDYURINE', 'EPIGASTRICPAIN', 'LOWERABDPAIN', 'FLANKPAIN', 
                        'URINARYHESITANCY', 'SUBCOSTALPAIN', 'HEADACHE', 'POORCONTACT', 
                        'DELIRIUMAGITATION', 'VOMITING', 'SEIZURES', 'EYEPAIN', 'REDEYES', 
                        'NAUSEA', 'BLURREDVISION', 'SKINLESIONS',
                        # Triệu chứng liên quan
                        'OTHERSYMPTOM', 'SPECIFYOTHERSYMPTOM', 'WEIGHT', 'HEIGHT', 'BMI',
                        # Triệu chứng lâm sàng
                        'FEVER_2', 'RASH', 'SKINBLEEDING', 'MUCOSALBLEEDING', 'SKINLESIONS_2',
                        'LUNGCRACKLES', 'CONSOLIDATIONSYNDROME', 'PLEURALEFFUSION', 'PNEUMOTHORAX',
                        'HEARTMURMUR', 'ABNORHEARTSOUNDS', 'JUGULARVEINDISTENTION', 'LIVERFAILURESIGNS',
                        'PORTALHYPERTENSIONSIGNS', 'HEPATOSPLENOMEGALY', 'CONSCIOUSNESSDISTURBANCE',
                        'LIMBWEAKNESSPARALYSIS', 'CRANIALNERVEPARALYSIS', 'MENINGEALSIGNS',
                        'REDEYES_2', 'HYPOPYON', 'EDEMA', 'CUSHINGOIDAPPEARANCE',
                        'EPIGASTRICPAIN_2', 'LOWERABDPAIN_2', 'FLANKPAIN_2', 'SUBCOSTALPAIN_2',
                        # Phần 2 thông tin triệu chứng
                        'OTHERSYMPTOM_2', 'SPECIFYOTHERSYMPTOM_2', 'TOTALCULTURERES',
                        # Trường nhiễm khuẩn
                        'INFECTFOCUS48H', 'SPECIFYOTHERINFECT48H', 'BLOODINFECT',
                        'SOFABASELINE', 'DIAGSOFA', 'SEPTICSHOCK', 'INFECTSRC',
                        # Trường điều trị
                        'RESPISUPPORT', 'SUPPORTTYPE', 'OXYMASKDURATION', 'HFNCNIVDURATION', 'VENTILATORDURATION',
                        'RESUSFLUID', 'FLUID6HOURS', 'CRYSTAL6HRS', 'COL6HRS', 'FLUID24HOURS', 'CRYSTAL24HRS', 'COL24HRS',
                        'VASOINOTROPES', 'DIALYSIS', 'DRAINAGE', 'DRAINAGETYPE', 'SPECIFYOTHERDRAINAGE',
                        'PRIORANTIBIOTIC', 'INITIALANTIBIOTIC', 'INITIALABXAPPROP',
                        # Trường hoàn thành
                        'COMPLETEDBY', 'COMPLETEDDATE', 'ENTRY', 'ENTEREDTIME'
                    ]
                    
                    # Tạo thứ tự cột mới dựa trên csv_column_order
                    new_columns = []
                    
                    # Đầu tiên thêm id nếu có
                    if 'id' in df.columns:
                        new_columns.append('id')
                        
                    # Sau đó thêm các cột theo thứ tự CSV
                    for col in csv_column_order:
                        if col in df.columns:
                            new_columns.append(col)
                            
                    # Cuối cùng thêm các cột còn lại không nằm trong csv_column_order
                    for col in df.columns:
                        if col not in new_columns:
                            new_columns.append(col)
                            
                    # Áp dụng thứ tự cột mới
                    df = df[new_columns]
                    
                except Exception as e:
                    print(f"Lỗi khi sắp xếp lại các cột ClinicalCase: {str(e)}")
            
            # Ghi vào sheet Excel
            sheet_name = model.__name__[:31]  # Giới hạn độ dài tên sheet (Excel giới hạn 31 ký tự)
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        except Exception as e:
            # Ghi log lỗi chi tiết
            print(f"Lỗi khi xuất {model.__name__}: {str(e)}")
            continue  # Tiếp tục với model tiếp theo nếu có lỗi

    # Lưu và đóng writer
    writer.close()
    buffer.seek(0)

    # Tạo response để tải file
    response = HttpResponse(
        content=buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="database_export.xlsx"'
    return response