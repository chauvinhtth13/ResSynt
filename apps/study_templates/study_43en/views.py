from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from .models import (
    ScreeningCase, EnrollmentCase, ClinicalCase, 
    PriorAntibiotic, InitialAntibiotic, MainAntibiotic, SampleCollection,
    LaboratoryTest, MicrobiologyCulture, VasoIDrug, ScreeningContact,EnrollmentContact,FollowUpCase,FollowUpAntibiotic,Rehospitalization,FollowUpAntibiotic90,FollowUpCase90,DischargeICD,DischargeCase,ContactSampleCollection,ContactFollowUp28,ContactFollowUp90,ContactMedicationHistory
)
from .forms import (
    ScreeningCaseForm, EnrollmentCaseForm, ClinicalCaseForm,
    PriorAntibioticFormSet, InitialAntibioticFormSet, MainAntibioticFormSet,
    VasoIDrugFormSet, SampleCollectionForm, ScreeningContactForm,EnrollmentContactForm,FollowUpCaseForm,FollowUpAntibioticFormSet,RehospitalizationFormSet,FollowUpAntibioticFormSetReadOnly,RehospitalizationFormSetReadOnly,FollowUpAntibiotic90FormSet,FollowUpCase90Form,Rehospitalization90FormSet,Rehospitalization90FormSetReadOnly,FollowUpAntibiotic90FormSetReadOnly,
    DischargeCaseForm, DischargeICDFormSet,DischargeICDFormSetReadOnly,ContactSampleCollectionForm,EnrollmentContact,EnrollmentCase,ContactFollowUp28Form,ContactFollowUp90Form,ContactMedicationHistoryFormSet,ContactMedicationHistory90FormSet,ContactSampleCollectionForm
)
from datetime import date  # Thêm import này nếu chưa có
from django.http import JsonResponse
from django.utils.translation import gettext as _
from datetime import date, datetime
from django.utils import timezone
import logging


logger = logging.getLogger(__name__)

@login_required
def screening_case_list(request):
    """Danh sách các bệnh nhân sàng lọc (hiển thị cả PS0375 và PS375)"""
    enrolled = request.GET.get('enrolled', '') == 'true'
    query = request.GET.get('q', '').strip()

    # Lấy tất cả cases
    cases = ScreeningCase.objects.all()

    # Nếu lọc theo trạng thái đã đăng ký
    if enrolled:
        cases = cases.filter(
            UPPER16AGE=True,
            INFPRIOR2OR48HRSADMIT=True,
            ISOLATEDKPNFROMINFECTIONORBLOOD=True,
            KPNISOUNTREATEDSTABLE=False,
            CONSENTTOSTUDY=True
        )

    # Chuẩn hóa screening_id về số để sắp xếp và tìm kiếm
    def normalize_screening_id(sid):
        import re
        match = re.match(r'PS0*(\d+)', sid or '')
        return int(match.group(1)) if match else -1

    # Nếu có query, tìm theo số thứ tự screening_id (ví dụ nhập 375 ra cả PS375 và PS0375)
    if query:
        try:
            query_num = int(query)
            cases = [c for c in cases if normalize_screening_id(c.screening_id) == query_num]
        except ValueError:
            cases = [c for c in cases if query.lower() in (c.screening_id or '').lower() or query.lower() in (c.USUBJID or '').lower() or query.lower() in (c.INITIAL or '').lower()]

    # Sắp xếp theo số thứ tự screening_id
    cases = sorted(cases, key=lambda c: normalize_screening_id(c.screening_id))

    # Thống kê
    total_cases = len(cases)
    eligible_cases = len([
        c for c in cases if c.UPPER16AGE and c.INFPRIOR2OR48HRSADMIT and c.ISOLATEDKPNFROMINFECTIONORBLOOD and not c.KPNISOUNTREATEDSTABLE and c.CONSENTTOSTUDY
    ])

    # Phân trang
    paginator = Paginator(cases, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_cases': total_cases,
        'eligible_cases': eligible_cases,
        'query': query,
        'view_type': 'enrolled' if enrolled else 'screening'
    }

    return render(request, 'study_43en/screening_case_list.html', context)

@login_required
def screening_case_create(request):
    """
    Tạo mới một ScreeningCase với screening_id được sinh ngay khi nhấn 'Tạo mới'
    """
    import re

    if request.method == 'POST':
        form = ScreeningCaseForm(request.POST)
        if form.is_valid():
            screening_case = form.save(commit=False)
            # Nếu screening_id chưa có (dự phòng), model sẽ tự sinh
            screening_case.save()
            messages.success(request, f'Đã tạo mới bệnh nhân {screening_case.screening_id} thành công.')

            # Kiểm tra eligibility và consent để chuyển hướng
            is_eligible = (
                form.cleaned_data.get('UPPER16AGE') and
                form.cleaned_data.get('INFPRIOR2OR48HRSADMIT') and
                form.cleaned_data.get('ISOLATEDKPNFROMINFECTIONORBLOOD') and
                not form.cleaned_data.get('KPNISOUNTREATEDSTABLE')
            )
            consent = form.cleaned_data.get('CONSENTTOSTUDY')

            if is_eligible and consent and screening_case.USUBJID:
                messages.info(request, f'Bệnh nhân đủ điều kiện và đã đồng ý tham gia. Vui lòng nhập thông tin chi tiết.')
                return redirect('43en:enrollment_case_create', usubjid=screening_case.USUBJID)
            else:
                return redirect('43en:screening_case_list')
        else:
            print("Form errors:", form.errors)
            print("Form non-field errors:", form.non_field_errors())
    else:
        # Khi nhấn 'Tạo mới', sinh screening_id mới
        all_ids = ScreeningCase.objects.values_list('screening_id', flat=True)
        max_num = 0
        for sid in all_ids:
            m = re.match(r'PS(\d+)', str(sid))
            if m:
                num = int(m.group(1))
                if num > max_num:
                    max_num = num
        new_screening_id = f"PS{max_num + 1:04d}"
        instance = ScreeningCase(screening_id=new_screening_id)
        form = ScreeningCaseForm(instance=instance, initial={'SITEID': '003', 'STUDYID': '43EN'})

    return render(request, 'study_43en/screening_form.html', {'form': form, 'is_create': True})
@login_required
def screening_case_update(request, usubjid):
    """Cập nhật thông tin một ScreeningCase"""
    # Cần thay đổi: tìm bằng screening_id thay vì USUBJID
    screening_case = get_object_or_404(ScreeningCase, screening_id=usubjid)
    
    old_values = {
        'UPPER16AGE': screening_case.UPPER16AGE,
        'INFPRIOR2OR48HRSADMIT': screening_case.INFPRIOR2OR48HRSADMIT,
        'ISOLATEDKPNFROMINFECTIONORBLOOD': screening_case.ISOLATEDKPNFROMINFECTIONORBLOOD,
        'KPNISOUNTREATEDSTABLE': screening_case.KPNISOUNTREATEDSTABLE,
        'CONSENTTOSTUDY': screening_case.CONSENTTOSTUDY
    }
    
    if request.method == 'POST':
        form = ScreeningCaseForm(request.POST, instance=screening_case)
        if form.is_valid():
            # Sử dụng logic từ model
            create_usubjid = form.save()
            messages.success(request, f'Đã cập nhật thông tin bệnh nhân {screening_case.screening_id} thành công.')
            
            # Kiểm tra tất cả 4 tiêu chí đủ điều kiện và sự đồng ý của bệnh nhân
            is_eligible = (
                form.cleaned_data.get('UPPER16AGE') and 
                form.cleaned_data.get('INFPRIOR2OR48HRSADMIT') and
                form.cleaned_data.get('ISOLATEDKPNFROMINFECTIONORBLOOD') and
                not form.cleaned_data.get('KPNISOUNTREATEDSTABLE')
            )
            
            consent = form.cleaned_data.get('CONSENTTOSTUDY')
            
            # Kiểm tra nếu bệnh nhân đã có đủ điều kiện và chuyển từ không đồng ý -> đồng ý tham gia
            newly_eligible_and_consented = (
                is_eligible and
                consent and
                not old_values['CONSENTTOSTUDY']  # Trước đây chưa đồng ý
            )
            
            # Nếu bệnh nhân không đủ điều kiện hoặc không đồng ý tham gia
            if not is_eligible or not consent:
                messages.warning(request, f'Bệnh nhân không đủ điều kiện hoặc không đồng ý tham gia nghiên cứu. Đã lưu thông tin sàng lọc.')
                return redirect('43en:screening_case_list')
            
            # Nếu bệnh nhân mới đủ điều kiện và mới đồng ý tham gia
            if newly_eligible_and_consented and create_usubjid:
                # Kiểm tra xem đã có EnrollmentCase chưa
                has_enrollment = EnrollmentCase.objects.filter(USUBJID=screening_case).exists()
                if not has_enrollment:
                    messages.info(request, f'Bệnh nhân đã đủ điều kiện và đồng ý tham gia. Vui lòng nhập thông tin chi tiết.')
                    return redirect('43en:enrollment_case_create', usubjid=screening_case.USUBJID)
            
            # Nếu đã đủ điều kiện và đã đồng ý từ trước, vẫn chuyển đến trang chi tiết
            if screening_case.USUBJID:
                return redirect('43en:patient_detail', usubjid=screening_case.USUBJID)
            else:
                return redirect('43en:screening_case_list')
    else:
        form = ScreeningCaseForm(instance=screening_case)
    
    return render(request, 'study_43en/screening_form.html', {'form': form, 'is_create': False})


@login_required
def screening_case_delete(request, usubjid):
    """Xóa một ScreeningCase"""
    # Cần thay đổi: tìm bằng screening_id thay vì USUBJID
    screening_case = get_object_or_404(ScreeningCase, screening_id=usubjid)
    
    if request.method == 'POST':
        screening_case.delete()
        messages.success(request, f'Đã xóa bệnh nhân {screening_case.screening_id} thành công.')
        return redirect('43en:screening_case_list')
    
    return render(request, 'study_43en/screening_case_confirm_delete.html', {'screening_case': screening_case})

@login_required
def enrollment_case_create(request, usubjid):
    """Tạo mới thông tin EnrollmentCase cho bệnh nhân đã có ScreeningCase"""
    # Tìm bằng USUBJID (vì đây là bệnh nhân đã có USUBJID)
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid, is_confirmed=True)
    
    # Kiểm tra xem bệnh nhân có đủ điều kiện không (đầy đủ 4 tiêu chí)
    if not (screening_case.UPPER16AGE and screening_case.INFPRIOR2OR48HRSADMIT and 
            screening_case.ISOLATEDKPNFROMINFECTIONORBLOOD and not screening_case.KPNISOUNTREATEDSTABLE and
        screening_case.CONSENTTOSTUDY):
        messages.error(request, f'Bệnh nhân {usubjid} không đủ điều kiện hoặc không đồng ý tham gia nghiên cứu.')
        return redirect('43en:screening_case_list')
    
    # Kiểm tra xem đã có EnrollmentCase chưa
    try:
        enrollment_case = EnrollmentCase.objects.get(USUBJID=screening_case)
        messages.warning(request, f'Bệnh nhân {usubjid} đã có thông tin chi tiết. Chuyển tới trang cập nhật.')
        return redirect('43en:enrollment_case_update', usubjid=usubjid)
    except EnrollmentCase.DoesNotExist:
        pass
        
    if request.method == 'POST':
        form = EnrollmentCaseForm(request.POST)
        if form.is_valid():
            enrollment_case = form.save(commit=False)
            enrollment_case.USUBJID = screening_case
            enrollment_case.save()
            messages.success(request, f'Đã tạo thông tin chi tiết cho bệnh nhân {usubjid} thành công.')
            return redirect('43en:patient_detail', usubjid=usubjid)
    else:
        initial_data = {
            'ENRDATE': screening_case.SCREENINGFORMDATE,
            'INITIAL': screening_case.INITIAL,
            'COMPLETEDBY': screening_case.COMPLETEDBY,
        }
        form = EnrollmentCaseForm(initial=initial_data)
    
    return render(request, 'study_43en/enrollment_form.html', {
        'form': form,
        'screening_case': screening_case,
        'is_create': True,
        'medication_data': []
    })

@login_required
def enrollment_case_update(request, usubjid):
    """Cập nhật thông tin EnrollmentCase cho bệnh nhân"""
    # Tìm bằng USUBJID (vì đây là bệnh nhân đã có USUBJID)
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    
    if request.method == 'POST':
        form = EnrollmentCaseForm(request.POST, instance=enrollment_case)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật thông tin chi tiết cho bệnh nhân {usubjid} thành công.')
            return redirect('43en:patient_detail', usubjid=usubjid)
    else:
        form = EnrollmentCaseForm(instance=enrollment_case)
    
    return render(request, 'study_43en/enrollment_form.html', {
        'form': form,
        'enrollment_case': enrollment_case,
        'screening_case': screening_case,
        'is_create': False,
        'today': date.today(),
    })

@login_required
def enrollment_case_view(request, usubjid):
    """Xem thông tin EnrollmentCase ở chế độ chỉ đọc"""
    # Tìm bằng USUBJID (vì đây là bệnh nhân đã có USUBJID)
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    try:
        enrollment_case = EnrollmentCase.objects.get(USUBJID=screening_case)
    except EnrollmentCase.DoesNotExist:
        messages.error(request, f'Bệnh nhân {usubjid} chưa có thông tin chi tiết.')
        return redirect('43en:patient_detail', usubjid=usubjid)
    
    form = EnrollmentCaseForm(instance=enrollment_case)
    
    return render(request, 'study_43en/enrollment_form.html', {
        'form': form,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'is_view_only': True,
        'today': date.today(),
    })

@login_required
def clinical_case_update(request, usubjid):
    """Cập nhật thông tin ClinicalCase cho bệnh nhân"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    clinical_case = get_object_or_404(ClinicalCase, USUBJID=screening_case)
    if request.method == 'POST':
        form = ClinicalCaseForm(request.POST, instance=clinical_case)
        prior_antibiotic_formset = PriorAntibioticFormSet(
            request.POST, 
            prefix='priorantibiotic_set',
            instance=screening_case
        )
        initial_antibiotic_formset = InitialAntibioticFormSet(
            request.POST, 
            prefix='initialantibiotic_set',
            instance=screening_case
        )
        main_antibiotic_formset = MainAntibioticFormSet(
            request.POST, 
            prefix='mainantibiotic_set',
            instance=screening_case
        )
        vaso_drug_formset = VasoIDrugFormSet(
            request.POST,
            prefix='vasoidrug_set',
            instance=screening_case
        )
        
        formsets_valid = (
            prior_antibiotic_formset.is_valid() and
            initial_antibiotic_formset.is_valid() and
            main_antibiotic_formset.is_valid() and
            vaso_drug_formset.is_valid()
        )
        
        if form.is_valid() and formsets_valid:
            # Lưu clinical case trước
            clinical_case = form.save()
              # Lưu các formset 
            prior_antibiotic_formset.save()
            initial_antibiotic_formset.save()
            main_antibiotic_formset.save()
            vaso_drug_formset.save()
            messages.success(request, f'Đã cập nhật thông tin lâm sàng cho bệnh nhân {usubjid} thành công.')
            # Khi form lâm sàng cuối hoàn thành, trở về trang chi tiết bệnh nhân
            return redirect('43en:patient_detail', usubjid=usubjid)    
    else:
        form = ClinicalCaseForm(instance=clinical_case)
        prior_antibiotic_formset = PriorAntibioticFormSet(
            prefix='priorantibiotic_set',
            instance=screening_case
        )
        initial_antibiotic_formset = InitialAntibioticFormSet(
            prefix='initialantibiotic_set',
            instance=screening_case
        )
        main_antibiotic_formset = MainAntibioticFormSet(
            prefix='mainantibiotic_set',
            instance=screening_case
        )
        vaso_drug_formset = VasoIDrugFormSet(
            prefix='vasoidrug_set',
            instance=screening_case
        )
    return render(request, 'study_43en/clinical_case_form.html', {
        'form': form,
        'prior_antibiotic_formset': prior_antibiotic_formset,
        'initial_antibiotic_formset': initial_antibiotic_formset,
        'main_antibiotic_formset': main_antibiotic_formset,
        'vaso_drug_formset': vaso_drug_formset,
        'clinical_case': clinical_case,
        'screening_case': screening_case,
        'is_create': False,
        'today': date.today(),
    })

@login_required
def enrollment_case_delete(request, usubjid):
    """Xóa thông tin EnrollmentCase cho bệnh nhân"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    
    if request.method == 'POST':
        enrollment_case.delete()
        messages.success(request, f'Đã xóa thông tin chi tiết của bệnh nhân {usubjid} thành công.')
        return redirect('43en:patient_detail', usubjid=usubjid)
    
    return render(request, 'study_43en/enrollment_case_confirm_delete.html', {
        'enrollment_case': enrollment_case,
        'screening_case': screening_case
    })

@login_required
def clinical_case_create(request, usubjid):
    """Tạo mới thông tin ClinicalCase cho bệnh nhân"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    # Kiểm tra xem đã có ClinicalCase chưa
    try:
        clinical_case = ClinicalCase.objects.get(USUBJID=screening_case)
        messages.warning(request, f'Bệnh nhân {usubjid} đã có thông tin lâm sàng. Chuyển tới trang cập nhật.')
        return redirect('clinical_case_update', usubjid=usubjid)
    except ClinicalCase.DoesNotExist:
        pass
        if request.method == 'POST':
            form = ClinicalCaseForm(request.POST)
        prior_antibiotic_formset = PriorAntibioticFormSet(request.POST, prefix='priorantibiotic_set')
        initial_antibiotic_formset = InitialAntibioticFormSet(request.POST, prefix='initialantibiotic_set')
        main_antibiotic_formset = MainAntibioticFormSet(request.POST, prefix='mainantibiotic_set')
        vaso_drug_formset = VasoIDrugFormSet(request.POST, prefix='vasoidrug_set')
        
        formsets_valid = (
            prior_antibiotic_formset.is_valid() and
            initial_antibiotic_formset.is_valid() and
            main_antibiotic_formset.is_valid() and
            vaso_drug_formset.is_valid()
        )
        
        if form.is_valid() and formsets_valid:
            # Lưu clinical case
            clinical_case = form.save(commit=False)            
            clinical_case.USUBJID = screening_case
            clinical_case.save()
            
            # Lưu các formset với liên kết đến screening_case
            prior_antibiotic_instances = prior_antibiotic_formset.save(commit=False)
            for instance in prior_antibiotic_instances:
                instance.USUBJID = screening_case
                instance.save()
            
            initial_antibiotic_instances = initial_antibiotic_formset.save(commit=False)
            for instance in initial_antibiotic_instances:
                instance.USUBJID = screening_case
                instance.save()
            
            main_antibiotic_instances = main_antibiotic_formset.save(commit=False)
            for instance in main_antibiotic_instances:
                instance.USUBJID = screening_case
                instance.save()
              # Save VasoIDrug instances
            vaso_drug_instances = vaso_drug_formset.save(commit=False)
            for instance in vaso_drug_instances:
                instance.USUBJID = screening_case
                instance.save()
                
            # Xử lý các xóa từ formsets
            prior_antibiotic_formset.save()
            initial_antibiotic_formset.save()
            main_antibiotic_formset.save()
            vaso_drug_formset.save()
            
            messages.success(request, f'Đã tạo thông tin lâm sàng cho bệnh nhân {usubjid} thành công.')
            # Chuyển người dùng đến trang xét nghiệm sau khi lưu thông tin lâm sàng
            return redirect('laboratory_test_create', usubjid=usubjid)
        else:
            initial_data = {
            # Điền sẵn một số thông tin
            'STUDYID': '43EN',
            'SITEID': screening_case.SITEID,
            'SUBJID': screening_case.SUBJID,
            'INITIAL': screening_case.INITIAL,
            'COMPLETEDBY': screening_case.COMPLETEDBY,
            'COMPLETEDDATE': date.today(),  # Thêm ngày hiện tại vào dữ liệu khởi tạo
        }        
        form = ClinicalCaseForm(initial=initial_data)
        prior_antibiotic_formset = PriorAntibioticFormSet(prefix='priorantibiotic_set')
        initial_antibiotic_formset = InitialAntibioticFormSet(prefix='initialantibiotic_set')
        main_antibiotic_formset = MainAntibioticFormSet(prefix='mainantibiotic_set')
        vaso_drug_formset = VasoIDrugFormSet(prefix='vasoidrug_set')
    return render(request, 'study_43en/clinical_case_form.html', {
        'form': form,
        'prior_antibiotic_formset': prior_antibiotic_formset,
        'initial_antibiotic_formset': initial_antibiotic_formset,
        'main_antibiotic_formset': main_antibiotic_formset,
        'vaso_drug_formset': vaso_drug_formset,
        'clinical_case': {'USUBJID_id': screening_case.USUBJID},
        'screening_case': screening_case,
        'is_create': True,
        'today': date.today(),  # Thêm biến today vào context
    })

@login_required
def clinical_case_detail(request, usubjid):
    """Hiển thị chi tiết ClinicalCase"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    clinical_case = get_object_or_404(ClinicalCase, USUBJID=screening_case)
    
    return render(request, 'study_43en/clinical_case_detail.html', {
        'clinical_case': clinical_case,
        'screening_case': screening_case,
    })

@login_required
def clinical_case_delete(request, usubjid):
    """Xóa thông tin ClinicalCase cho bệnh nhân"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    clinical_case = get_object_or_404(ClinicalCase, USUBJID=screening_case)
    
    if request.method == 'POST':
        clinical_case.delete()
        messages.success(request, f'Đã xóa thông tin lâm sàng của bệnh nhân {usubjid} thành công.')
        return redirect('43en:patient_detail', usubjid=usubjid)
    
    return render(request, 'study_43en/clinical_case_confirm_delete.html', {
        'clinical_case': clinical_case,
        'screening_case': screening_case
    })

@login_required
def clinical_form(request, usubjid, read_only=False):
    """Hiển thị form lâm sàng ban đầu sử dụng template AdminLTE, có hỗ trợ chế độ chỉ đọc"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    # Kiểm tra xem đã có ClinicalCase chưa
    try:
        clinical_case = ClinicalCase.objects.get(USUBJID=screening_case)
        has_clinical = True
        
        # Lấy dữ liệu formsets
        prior_antibiotic_formset = PriorAntibioticFormSet(
            prefix='priorantibiotic_set',
            instance=screening_case
        )
        initial_antibiotic_formset = InitialAntibioticFormSet(
            prefix='initialantibiotic_set',
            instance=screening_case
        )
        main_antibiotic_formset = MainAntibioticFormSet(
            prefix='mainantibiotic_set',
            instance=screening_case
        )
        vaso_drug_formset = VasoIDrugFormSet(
            prefix='vasoidrug_set',
            instance=screening_case
        )
    except ClinicalCase.DoesNotExist:
        clinical_case = None
        has_clinical = False
        
        # Tạo formset trống nếu không có clinical_case
        prior_antibiotic_formset = PriorAntibioticFormSet(prefix='priorantibiotic_set')
        initial_antibiotic_formset = InitialAntibioticFormSet(prefix='initialantibiotic_set')
        main_antibiotic_formset = MainAntibioticFormSet(prefix='mainantibiotic_set')
        vaso_drug_formset = VasoIDrugFormSet(prefix='vasoidrug_set')
    
    if request.method == 'POST' and not read_only:
        # Xử lý POST request khi không ở chế độ read_only
        if clinical_case:
            # Cập nhật clinical case
            form = ClinicalCaseForm(request.POST, instance=clinical_case)
            prior_antibiotic_formset = PriorAntibioticFormSet(
                request.POST,
                prefix='priorantibiotic_set',
                instance=screening_case
            )
            initial_antibiotic_formset = InitialAntibioticFormSet(
                request.POST,
                prefix='initialantibiotic_set',
                instance=screening_case
            )
            main_antibiotic_formset = MainAntibioticFormSet(
                request.POST,
                prefix='mainantibiotic_set',
                instance=screening_case
            )
            vaso_drug_formset = VasoIDrugFormSet(
                request.POST,
                prefix='vasoidrug_set',
                instance=screening_case
            )
        else:
            # Tạo mới clinical case
            form = ClinicalCaseForm(request.POST)
            prior_antibiotic_formset = PriorAntibioticFormSet(
                request.POST,
                prefix='priorantibiotic_set'
            )
            initial_antibiotic_formset = InitialAntibioticFormSet(
                request.POST,
                prefix='initialantibiotic_set'
            )
            main_antibiotic_formset = MainAntibioticFormSet(
                request.POST,
                prefix='mainantibiotic_set'
            )
            vaso_drug_formset = VasoIDrugFormSet(
                request.POST,
                prefix='vasoidrug_set'
            )
        
        formsets_valid = (
            prior_antibiotic_formset.is_valid() and
            initial_antibiotic_formset.is_valid() and
            main_antibiotic_formset.is_valid() and
            vaso_drug_formset.is_valid()
        )
        
        if form.is_valid() and formsets_valid:
            # Lưu clinical case
            new_clinical_case = form.save(commit=False)
            if not clinical_case:
                new_clinical_case.USUBJID = screening_case
            new_clinical_case.save()
            
            # Lưu các formset
            # Prior Antibiotic
            prior_antibiotic_instances = prior_antibiotic_formset.save(commit=False)
            for instance in prior_antibiotic_instances:
                instance.USUBJID = screening_case
                instance.save()
            prior_antibiotic_formset.save_m2m()
            
            # Initial Antibiotic
            initial_antibiotic_instances = initial_antibiotic_formset.save(commit=False)
            for instance in initial_antibiotic_instances:
                instance.USUBJID = screening_case
                instance.save()
            initial_antibiotic_formset.save_m2m()
            
            # Main Antibiotic
            main_antibiotic_instances = main_antibiotic_formset.save(commit=False)
            for instance in main_antibiotic_instances:
                instance.USUBJID = screening_case
                instance.save()
            main_antibiotic_formset.save_m2m()
            
            # Vaso Drug
            vaso_drug_instances = vaso_drug_formset.save(commit=False)
            for instance in vaso_drug_instances:
                instance.USUBJID = screening_case
                instance.save()
            vaso_drug_formset.save_m2m()
            
            messages.success(request, f'Đã lưu thông tin lâm sàng cho bệnh nhân {usubjid} thành công.')
            # Chuyển hướng đến trang laboratory tests
            return redirect('43en:patient_detail', usubjid=usubjid)
    else:
        # Xử lý GET request hoặc khi ở chế độ read_only
        if clinical_case:
            form = ClinicalCaseForm(instance=clinical_case)
        else:
            # Tạo form với dữ liệu ban đầu
            initial_data = {
                'STUDYID': '43EN',
                'SITEID': screening_case.SITEID,
                'SUBJID': screening_case.SUBJID,
                'INITIAL': screening_case.INITIAL,
                'COMPLETEDBY': screening_case.COMPLETEDBY if screening_case.COMPLETEDBY else request.user.username,
                'COMPLETEDDATE': date.today(),
            }
            form = ClinicalCaseForm(initial=initial_data)
    
    # Đặt readonly cho tất cả các trường khi ở chế độ read_only
    if read_only:
        for field in form.fields.values():
            field.widget.attrs['readonly'] = True
            field.widget.attrs['disabled'] = True
        
        # Đặt readonly cho tất cả các formset
        for formset in [prior_antibiotic_formset, initial_antibiotic_formset, 
                       main_antibiotic_formset, vaso_drug_formset]:
            for form_instance in formset.forms:
                for field in form_instance.fields.values():
                    field.widget.attrs['readonly'] = True
                    field.widget.attrs['disabled'] = True
    
    return render(request, 'study_43en/clinical_form.html', {
        'screening_case': screening_case,
        'clinical_case': clinical_case,
        'has_clinical': has_clinical,
        'form': form,
        'prior_antibiotic_formset': prior_antibiotic_formset,
        'initial_antibiotic_formset': initial_antibiotic_formset,
        'main_antibiotic_formset': main_antibiotic_formset,
        'vaso_drug_formset': vaso_drug_formset,
        'is_readonly': read_only,
        'today': date.today(),  # Biến today cho template
    })

@login_required
def clinical_form_view(request, usubjid):
    """Xem thông tin ClinicalCase ở chế độ chỉ đọc"""
    if request.method == 'POST':
        messages.error(request, "Không thể submit trong chế độ xem")
        return redirect('43en:clinical_form_view', usubjid=usubjid)
    return clinical_form(request, usubjid, read_only=True)

@login_required
def patient_list(request):
    """Danh sách các bệnh nhân đã tham gia nghiên cứu (đủ điều kiện + đồng ý)"""
    query = request.GET.get('q', '')
    
    # Chỉ lấy những bệnh nhân đủ điều kiện và đã đồng ý tham gia
    cases = ScreeningCase.objects.filter(
        is_confirmed=True 
    ).order_by('USUBJID')
    
    # Tìm kiếm nếu có
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
    
    # Thêm thông tin trạng thái cho mỗi bệnh nhân
    for case in page_obj:
        case.has_enrollment = EnrollmentCase.objects.filter(USUBJID=case).exists()
        case.has_clinical = ClinicalCase.objects.filter(USUBJID=case).exists()
    
    context = {
        'page_obj': page_obj,
        'total_patients': total_patients,
        'query': query,
        'view_type': 'patients',
        'is_paginated': page_obj.has_other_pages(),
    }
    
    return render(request, 'study_43en/patient_list.html', context)

@login_required
def patient_detail(request, usubjid):
    """View chi tiết bệnh nhân, bổ sung expected dates vào context"""
    screeningcase = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    # EnrollmentCase
    try:
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
        clinicalcase = ClinicalCase.objects.get(USUBJID=screeningcase)
        has_clinical = True
    except ClinicalCase.DoesNotExist:
        clinicalcase = None
        has_clinical = False
    
    # LaboratoryTest, MicrobiologyCulture, SampleCollection
    laboratory_count = LaboratoryTest.objects.filter(clinical_case=screeningcase).count() if screeningcase else 0
    has_laboratory_tests = laboratory_count > 0
    microbiology_count = MicrobiologyCulture.objects.filter(clinical_case=screeningcase).count() if clinicalcase else 0
    has_microbiology_cultures = microbiology_count > 0
    sample_count = SampleCollection.objects.filter(clinical_case=screeningcase).count() if clinicalcase else 0
    
    # FollowUpCase 28 ngày
    try:
        followupcase = FollowUpCase.objects.get(USUBJID=screeningcase)
        has_followup = True
    except FollowUpCase.DoesNotExist:
        followupcase = None
        has_followup = False
    
    # FollowUpCase 90 ngày
    try:
        followupcase90 = FollowUpCase90.objects.get(USUBJID=screeningcase)
        has_followup90 = True
    except FollowUpCase90.DoesNotExist:
        followupcase90 = None
        has_followup90 = False
    
    # DischargeCase
    try:
        dischargecase = DischargeCase.objects.get(USUBJID=screeningcase)
        has_discharge = True
    except DischargeCase.DoesNotExist:
        dischargecase = None
        has_discharge = False

    # Số ngày từ khi enrollment
    if has_enrollment and enrollmentcase.ENRDATE:
        days_since_enrollment = (date.today() - enrollmentcase.ENRDATE).days
    else:
        days_since_enrollment = 0
    
    # Phần trăm hoàn thành
    completion_steps = 7
    completed_steps = 1  # Screening đã hoàn thành
    if has_enrollment:
        completed_steps += 1
    if has_clinical:
        completed_steps += 1
    if has_laboratory_tests:
        completed_steps += 1
    if has_microbiology_cultures:
        completed_steps += 1
    if has_followup:
        completed_steps += 1
    if has_followup90:
        completed_steps += 1
    if has_discharge:  
        completed_steps += 1
    completion_percentage = int((completed_steps / completion_steps) * 100)
    
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
        'completion_percentage': completion_percentage,
        'expecteddates': expecteddates,  # Thêm dòng này để truyền expected dates cho template
    }
    
    return render(request, 'study_43en/patient_detail.html', context)


@login_required
def screening_case_view(request, screening_id):
    screening_case = get_object_or_404(ScreeningCase, screening_id=screening_id)
    
    # Tạo form với instance nhưng disable tất cả các field
    form = ScreeningCaseForm(instance=screening_case)
    
    # Disable tất cả các field để chỉ có thể xem
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True
        if hasattr(field.widget, 'choices'):
            # Đối với radio buttons, cần xử lý khác
            field.widget.attrs['onclick'] = 'return false;'
    
    return render(request, 'study_43en/screening_form.html', {
        'form': form, 
        'is_create': False, 
        'is_readonly': True,
        'screening_case': screening_case
    })

@login_required
def screening_contact_list(request):
    query = request.GET.get('q', '').strip()
    contacts = ScreeningContact.objects.all().order_by('screening_id')  # Số nhỏ lên trước

    if query:
        contacts = contacts.filter(
            Q(screening_id__icontains=query) |
            Q(USUBJID__icontains=query) |
            Q(INITIAL__icontains=query)
        )

    # Thống kê
    total_contacts = contacts.count()
    eligible_contacts = contacts.filter(
        CONSENTTOSTUDY=True,
        LIVEIN5DAYS3MTHS=True,
        MEALCAREONCEDAY=True
    ).count()
    enrolled_contacts = contacts.filter(enrollmentcontact__isnull=False).count()

    # Phân trang
    paginator = Paginator(contacts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Thêm thông tin trạng thái cho mỗi contact
    for contact in page_obj:
        contact.has_enrollment = hasattr(contact, 'enrollmentcontact') and contact.enrollmentcontact is not None

    context = {
        'page_obj': page_obj,
        'total_contacts': total_contacts,
        'eligible_contacts': eligible_contacts,
        'enrolled_contacts': enrolled_contacts,
        'query': query,
        'view_type': 'screening_contacts'
    }

    return render(request, 'study_43en/screening_contact_list.html', context)



@login_required
def screening_contact_create(request):
    """Tạo mới thông tin người tiếp xúc"""
    patient_id = request.GET.get('patient_id')
    
    if request.method == 'POST':
        form = ScreeningContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            created_usubjid = contact.save()
            
            if created_usubjid:
                messages.success(request, _(f'Đã tạo mới người tiếp xúc thành công với mã {contact.USUBJID}'))
            else:
                messages.success(request, _('Đã tạo mới thông tin người tiếp xúc thành công.'))
            
            # THÊM LOGIC KIỂM TRA ĐIỀU KIỆN GIỐNG PATIENT
            is_eligible = (
                form.cleaned_data.get('LIVEIN5DAYS3MTHS') and
                form.cleaned_data.get('MEALCAREONCEDAY')
            )
            consent = form.cleaned_data.get('CONSENTTOSTUDY')
            
            # Debug logging
            print(f"=== DEBUG CONTACT ELIGIBILITY CHECK ===")
            print(f"LIVEIN5DAYS3MTHS: {form.cleaned_data.get('LIVEIN5DAYS3MTHS')}")
            print(f"MEALCAREONCEDAY: {form.cleaned_data.get('MEALCAREONCEDAY')}")
            print(f"CONSENTTOSTUDY: {consent}")
            print(f"is_eligible: {is_eligible}")
            print(f"will redirect to enrollment: {is_eligible and consent}")
            print("===============================")
            
            # Chỉ khi đủ điều kiện VÀ đồng ý tham gia mới chuyển đến enrollment_contact
            if is_eligible and consent:
                messages.info(request, f'Contact đủ điều kiện và đã đồng ý tham gia. Vui lòng nhập thông tin chi tiết.')
                return redirect('43en:enrollment_contact_create', usubjid=contact.USUBJID)
            else:
                # Hiển thị thông báo phù hợp
                if not is_eligible:
                    messages.warning(request, f'Contact không đủ điều kiện tham gia nghiên cứu. Đã lưu thông tin sàng lọc.')
                elif not consent:
                    messages.warning(request, f'Contact không đồng ý tham gia nghiên cứu. Đã lưu thông tin sàng lọc.')
                
                return redirect('43en:screening_contact_list')
                
            # Trả về response JSON nếu là AJAX request
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Đã tạo mã người tiếp xúc: {contact.USUBJID}',
                    'usubjid': contact.USUBJID
                })
    else:
        # GET request logic remains the same
        initial_data = {}
        if patient_id:
            try:
                patient = ScreeningCase.objects.get(USUBJID=patient_id)
                initial_data['SUBJIDENROLLSTUDY'] = patient.pk
                initial_data['SITEID'] = patient.SITEID
            except ScreeningCase.DoesNotExist:
                pass
                
        form = ScreeningContactForm(initial=initial_data)

    context = {
        'form': form,
        'title': _('Tạo mới người tiếp xúc')
    }
    return render(request, 'study_43en/screening_contact_form.html', context)


@login_required
def screening_contact_view(request, usubjid_or_id):
    """Xem chi tiết thông tin người tiếp xúc"""
    # Tìm theo USUBJID hoặc screening_id
    try:
        if usubjid_or_id.startswith('CS-'):
            contact = get_object_or_404(ScreeningContact, screening_id=usubjid_or_id)
        else:
            contact = get_object_or_404(ScreeningContact, USUBJID=usubjid_or_id)
    except Exception:
        contact = get_object_or_404(ScreeningContact, screening_id=usubjid_or_id)
    
    # Tạo form chỉ để hiển thị (read-only)
    form = ScreeningContactForm(instance=contact)
    for field_name, field in form.fields.items():
        field.widget.attrs['disabled'] = True
        field.widget.attrs['readonly'] = True
    
    context = {
        'form': form,
        'contact': contact,
        'title': _('Chi tiết người tiếp xúc'),
        'is_view_only': True
    }
    
    return render(request, 'study_43en/screening_contact_form.html', context)

@login_required
def screening_contact_update(request, usubjid_or_id):
    """Cập nhật thông tin người tiếp xúc"""
    # Tìm contact
    try:
        if usubjid_or_id.startswith('CS-'):
            contact = get_object_or_404(ScreeningContact, screening_id=usubjid_or_id)
        else:
            contact = get_object_or_404(ScreeningContact, USUBJID=usubjid_or_id)
    except Exception:
        contact = get_object_or_404(ScreeningContact, screening_id=usubjid_or_id)
    
    # Lưu giá trị cũ để so sánh
    old_values = {
        'LIVEIN5DAYS3MTHS': contact.LIVEIN5DAYS3MTHS,
        'MEALCAREONCEDAY': contact.MEALCAREONCEDAY,
        'CONSENTTOSTUDY': contact.CONSENTTOSTUDY
    }
    
    if request.method == 'POST':
        form = ScreeningContactForm(request.POST, instance=contact)
        if form.is_valid():
            contact = form.save(commit=False)
            created_usubjid = contact.save()
            
            if created_usubjid:
                messages.success(request, _(f'Đã cập nhật thông tin và tạo mã {contact.USUBJID} thành công.'))
            else:
                messages.success(request, _('Đã cập nhật thông tin người tiếp xúc thành công.'))
            
            # THÊM LOGIC KIỂM TRA ĐIỀU KIỆN GIỐNG PATIENT
            is_eligible = (
                form.cleaned_data.get('LIVEIN5DAYS3MTHS') and
                form.cleaned_data.get('MEALCAREONCEDAY')
            )
            consent = form.cleaned_data.get('CONSENTTOSTUDY')
            
            # Kiểm tra nếu contact đã có đủ điều kiện và chuyển từ không đồng ý -> đồng ý tham gia
            newly_eligible_and_consented = (
                is_eligible and
                consent and
                not old_values['CONSENTTOSTUDY']  # Trước đây chưa đồng ý
            )
            
            # Nếu contact không đủ điều kiện hoặc không đồng ý tham gia
            if not is_eligible or not consent:
                messages.warning(request, f'Contact không đủ điều kiện hoặc không đồng ý tham gia nghiên cứu. Đã lưu thông tin sàng lọc.')
                return redirect('43en:screening_contact_list')
            
            # Nếu contact mới đủ điều kiện và mới đồng ý tham gia
            if newly_eligible_and_consented:
                # Kiểm tra xem đã có EnrollmentContact chưa
                has_enrollment = EnrollmentContact.objects.filter(USUBJID=contact).exists()
                if not has_enrollment:
                    messages.info(request, f'Contact đã đủ điều kiện và đồng ý tham gia. Vui lòng nhập thông tin chi tiết.')
                    return redirect('43en:enrollment_contact_create', usubjid=contact.USUBJID)
            
            # Nếu đã đủ điều kiện và đã đồng ý từ trước, chuyển đến trang chi tiết
            if is_eligible and consent:
                return redirect('43en:contact_detail', usubjid=contact.USUBJID)
            
            # Trả về response JSON nếu là AJAX request
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Đã tạo mã người tiếp xúc: {contact.USUBJID}',
                    'usubjid': contact.USUBJID
                })
                
            return redirect('43en:screening_contact_list')
    else:
        form = ScreeningContactForm(instance=contact)

    context = {
        'form': form,
        'contact': contact,
        'title': _('Cập nhật người tiếp xúc')
    }
    return render(request, 'study_43en/screening_contact_form.html', context)


@login_required
def screening_contact_delete(request, usubjid_or_id):
    """Xóa thông tin người tiếp xúc"""
    # Tìm theo USUBJID hoặc screening_id
    try:
        if usubjid_or_id.startswith('CS-'):
            contact = get_object_or_404(ScreeningContact, screening_id=usubjid_or_id)
        else:
            contact = get_object_or_404(ScreeningContact, USUBJID=usubjid_or_id)
    except Exception:
        contact = get_object_or_404(ScreeningContact, screening_id=usubjid_or_id)
    
    if request.method == 'POST':
        contact.delete()
        messages.success(request, _('Đã xóa thông tin người tiếp xúc thành công.'))
        return redirect('43en:screening_contact_list')
    
    # Thống kê tổng quan
    total_patients = ScreeningCase.objects.filter(SUBJID__startswith='A-').count()
    total_contacts = ScreeningContact.objects.count()
    eligible_contacts = ScreeningContact.objects.filter(
        CONSENTTOSTUDY=True,
        LIVEIN5DAYS3MTHS=True,
        MEALCAREONCEDAY=True
    ).count()
    
    context = {
        'contact': contact,
        'total_patients': total_patients,
        'total_contacts': total_contacts,
        'eligible_contacts': eligible_contacts
    }
    
    return render(request, 'study_43en/screening_contact_confirm_delete.html', context)

@login_required
def enrollment_contact_create(request, usubjid):
    """Tạo mới thông tin EnrollmentContact cho contact đã có ScreeningContact"""
    contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    
    # THÊM KIỂM TRA ĐIỀU KIỆN GIỐNG PATIENT
    # Kiểm tra xem contact có đủ điều kiện không (đầy đủ 2 tiêu chí + đồng ý)
    if not (contact.LIVEIN5DAYS3MTHS and contact.MEALCAREONCEDAY and contact.CONSENTTOSTUDY):
        messages.error(request, f'Contact {usubjid} không đủ điều kiện hoặc không đồng ý tham gia nghiên cứu.')
        return redirect('43en:screening_contact_list')
    
    # Kiểm tra xem đã có EnrollmentContact chưa
    try:
        enrollment_contact = EnrollmentContact.objects.get(USUBJID=contact)
        messages.warning(request, f'Contact {usubjid} đã có thông tin chi tiết. Chuyển tới trang cập nhật.')
        return redirect('43en:enrollment_contact_update', usubjid=usubjid)
    except EnrollmentContact.DoesNotExist:
        pass

    # Field names cho underlying diseases
    field_names_underlying = [
        "HEARTFAILURE", "DIABETES", "COPD", "HEPATITIS", "CAD", "KIDNEYDISEASE", "ASTHMA",
        "CIRRHOSIS", "HYPERTENSION", "AUTOIMMUNE", "CANCER", "ALCOHOLISM", "HIV",
        "ADRENALINSUFFICIENCY", "BEDRIDDEN", "PEPTICULCER", "COLITIS_IBS", "SENILITY",
        "MALNUTRITION_WASTING", "OTHERDISEASE"
    ]

    if request.method == 'POST':
        form = EnrollmentContactForm(request.POST)
        if form.is_valid():
            enrollment = form.save(commit=False)
            enrollment.USUBJID = contact
            enrollment.save()
            
            messages.success(request, f'Đã tạo thông tin chi tiết cho contact {usubjid} thành công.')
            return redirect('43en:contact_detail', usubjid=usubjid)
    else:
        # Tạo initial data giống như enrollment_case_create
        initial_data = {
            # Điền sẵn một số thông tin từ ScreeningContact
            'ENRDATE': contact.SCREENINGFORMDATE,  # Mặc định ngày tuyển là ngày sàng lọc
            'INITIAL': contact.INITIAL,
            'COMPLETEDBY': contact.COMPLETEDBY,  # Mặc định người nhập giống người sàng lọc
        }
        form = EnrollmentContactForm(initial=initial_data)

    return render(request, 'study_43en/enrollment_contact_form.html', {
        'form': form,
        'contact_case': {'USUBJID_id': contact.USUBJID},  # Giống pattern của patient
        'contact': contact,  # Giữ lại để backward compatibility
        'screening_contact': contact,  # Thêm để template có thể access
        'is_create': True,
        'field_names_underlying': field_names_underlying,
    })


@login_required
def enrollment_contact_update(request, usubjid):
    contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    enrollment = get_object_or_404(EnrollmentContact, USUBJID=contact)
    if request.method == 'POST':
        form = EnrollmentContactForm(request.POST, instance=enrollment)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật thông tin đăng ký cho người tiếp xúc {usubjid}')
            return redirect('screening_contact_list')
    else:
        form = EnrollmentContactForm(instance=enrollment)
    return render(request, 'study_43en/enrollment_contact_form.html', {
        'form': form,
        'contact': contact,
        'is_create': False,
    })

@login_required
def enrollment_contact_view(request, usubjid):
    contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    enrollment = get_object_or_404(EnrollmentContact, USUBJID=contact)
    form = EnrollmentContactForm(instance=enrollment)
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True
    return render(request, 'study_43en/enrollment_contact_form.html', {
        'form': form,
        'contact': contact,
        'is_view_only': True,
    })



from .models import FollowUpCase, Rehospitalization, FollowUpAntibiotic
from .forms import FollowUpCaseForm, RehospitalizationFormSet, FollowUpAntibioticFormSet

@login_required
def followup_case_create(request, usubjid):
    """Tạo mới thông tin FollowUpCase cho bệnh nhân"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    # Kiểm tra xem đã có FollowUpCase chưa
    try:
        followup_case = FollowUpCase.objects.get(USUBJID=screening_case)
        messages.warning(request, f'Bệnh nhân {usubjid} đã có thông tin theo dõi 28 ngày. Chuyển tới trang cập nhật.')
        return redirect('43en:followup_case_update', usubjid=usubjid)
    except FollowUpCase.DoesNotExist:
        pass

    if request.method == 'POST':
        form = FollowUpCaseForm(request.POST)
        rehospitalization_formset = RehospitalizationFormSet(
            request.POST, 
            prefix='rehospitalization_set'
        )
        antibiotic_formset = FollowUpAntibioticFormSet(
            request.POST, 
            prefix='antibiotic_set'
        )

        formsets_valid = (
            rehospitalization_formset.is_valid() and
            antibiotic_formset.is_valid()
        )

        if form.is_valid() and formsets_valid:
            # Lưu followup case
            followup_case = form.save(commit=False)
            followup_case.USUBJID = screening_case
            followup_case.save()

            # Lưu các formset với liên kết đến followup_case
            # Rehospitalization
            rehospitalization_instances = rehospitalization_formset.save(commit=False)
            for i, instance in enumerate(rehospitalization_instances, 1):
                instance.follow_up = followup_case
                instance.EPISODE = i  # Tự động đánh số thứ tự
                instance.save()

            # Antibiotic
            antibiotic_instances = antibiotic_formset.save(commit=False)
            for i, instance in enumerate(antibiotic_instances, 1):
                instance.follow_up = followup_case
                instance.EPISODE = i  # Tự động đánh số thứ tự
                instance.save()

            # Xử lý các xóa từ formsets
            rehospitalization_formset.save()
            antibiotic_formset.save()

            messages.success(request, f'Đã tạo thông tin theo dõi 28 ngày cho bệnh nhân {usubjid} thành công.')
            return redirect('43en:patient_detail', usubjid=usubjid)
    else:
        initial_data = {
            'COMPLETEDBY': screening_case.COMPLETEDBY if screening_case.COMPLETEDBY else request.user.username,
            'COMPLETEDDATE': date.today(),
        }
        form = FollowUpCaseForm(initial=initial_data)
        rehospitalization_formset = RehospitalizationFormSet(prefix='rehospitalization_set')
        antibiotic_formset = FollowUpAntibioticFormSet(prefix='antibiotic_set')

    return render(request, 'study_43en/followup_case_form.html', {
        'form': form,
        'rehospitalization_formset': rehospitalization_formset,
        'antibiotic_formset': antibiotic_formset,
        'followup_case': {'USUBJID_id': screening_case.USUBJID},
        'screening_case': screening_case,
        'is_create': True,
        'today': date.today(),
    })

@login_required
def followup_case_update(request, usubjid):
    """Cập nhật thông tin FollowUpCase cho bệnh nhân"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    followup_case = get_object_or_404(FollowUpCase, USUBJID=screening_case)

    if request.method == 'POST':
        form = FollowUpCaseForm(request.POST, instance=followup_case)
        rehospitalization_formset = RehospitalizationFormSet(
            request.POST,
            prefix='rehospitalization_set',
            instance=followup_case
        )
        antibiotic_formset = FollowUpAntibioticFormSet(
            request.POST,
            prefix='antibiotic_set',
            instance=followup_case
        )

        formsets_valid = (
            rehospitalization_formset.is_valid() and
            antibiotic_formset.is_valid()
        )

        if form.is_valid() and formsets_valid:
            # Lưu followup case trước
            followup_case = form.save()

            # Lưu các formset
            rehospitalization_formset.save()
            antibiotic_formset.save()

            messages.success(request, f'Đã cập nhật thông tin theo dõi 28 ngày cho bệnh nhân {usubjid} thành công.')
            return redirect('43en:patient_detail', usubjid=usubjid)
    else:
        form = FollowUpCaseForm(instance=followup_case)
        rehospitalization_formset = RehospitalizationFormSet(
            prefix='rehospitalization_set',
            instance=followup_case
        )
        antibiotic_formset = FollowUpAntibioticFormSet(
            prefix='antibiotic_set',
            instance=followup_case
        )

    return render(request, 'study_43en/followup_case_form.html', {
        'form': form,
        'rehospitalization_formset': rehospitalization_formset,
        'antibiotic_formset': antibiotic_formset,
        'followup_case': followup_case,
        'screening_case': screening_case,
        'is_create': False,
        'today': date.today(),
    })

@login_required
def followup_case_view(request, usubjid):
    """Xem thông tin FollowUpCase ở chế độ chỉ đọc"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    try:
        followup_case = FollowUpCase.objects.get(USUBJID=screening_case)
    except FollowUpCase.DoesNotExist:
        messages.error(request, f'Bệnh nhân {usubjid} chưa có thông tin theo dõi 28 ngày.')
        return redirect('43en:patient_detail', usubjid=usubjid)

    # Tạo form với instance nhưng set is_view_only=True
    form = FollowUpCaseForm(instance=followup_case)
    rehospitalization_formset = RehospitalizationFormSet(
        prefix='rehospitalization_set',
        instance=followup_case
    )
    antibiotic_formset = FollowUpAntibioticFormSet(
        prefix='antibiotic_set',
        instance=followup_case
    )

    # Đặt readonly cho tất cả các trường
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True

    # Đặt readonly cho tất cả các formset
    for formset in [rehospitalization_formset, antibiotic_formset]:
        for form_instance in formset.forms:
            for field in form_instance.fields.values():
                field.widget.attrs['readonly'] = True
                field.widget.attrs['disabled'] = True

    return render(request, 'study_43en/followup_case_form.html', {
        'form': form,
        'rehospitalization_formset': rehospitalization_formset,
        'antibiotic_formset': antibiotic_formset,
        'screening_case': screening_case,
        'followup_case': followup_case,
        'is_view_only': True,
        'today': date.today(),
    })


@login_required
def followup_form(request, usubjid):
    """View cho follow-up form - hỗ trợ cả theo dõi 28 ngày và 90 ngày"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    # Kiểm tra dữ liệu follow-up 28 ngày
    try:
        followup_case = FollowUpCase.objects.get(USUBJID=screening_case)
        has_followup28 = True
    except FollowUpCase.DoesNotExist:
        followup_case = None
        has_followup28 = False

    # Kiểm tra dữ liệu follow-up 90 ngày
    try:
        followup_case90 = FollowUpCase90.objects.get(USUBJID=screening_case)
        has_followup90 = True
    except FollowUpCase90.DoesNotExist:
        followup_case90 = None
        has_followup90 = False

    # Xác định xem có phải chế độ chỉ đọc không
    is_readonly = request.path.endswith('/view/')

    if request.method == 'POST' and not is_readonly:
        # DEBUG: In ra POST data để kiểm tra
        print("POST DATA:", request.POST)
        
        # POST - Luôn sử dụng FormSet có extra=1 để có thể thêm mới
        if followup_case:
            form = FollowUpCaseForm(request.POST, instance=followup_case)
            rehospitalization_formset = RehospitalizationFormSet(
                request.POST,
                prefix='rehospitalization_set',
                instance=followup_case
            )
            antibiotic_formset = FollowUpAntibioticFormSet(
                request.POST,
                prefix='antibiotic_set',
                instance=followup_case
            )
        else:
            form = FollowUpCaseForm(request.POST)
            # Tạo formset trống cho trường hợp tạo mới
            rehospitalization_formset = RehospitalizationFormSet(
                request.POST,
                prefix='rehospitalization_set'
            )
            antibiotic_formset = FollowUpAntibioticFormSet(
                request.POST,
                prefix='antibiotic_set'
            )

        # DEBUG: In ra management form để kiểm tra số lượng form
        print("REHOSPITALIZATION MANAGEMENT:", rehospitalization_formset.management_form.cleaned_data if rehospitalization_formset.management_form.is_valid() else "Invalid management form")
        print("ANTIBIOTIC MANAGEMENT:", antibiotic_formset.management_form.cleaned_data if antibiotic_formset.management_form.is_valid() else "Invalid management form")

        # Kiểm tra form validity
        form_valid = form.is_valid()
        rehosp_valid = rehospitalization_formset.is_valid()
        antibio_valid = antibiotic_formset.is_valid()

        # Xử lý validation và save
        if form_valid and rehosp_valid and antibio_valid:
            print("FORM IS VALID - Saving data...")
            
            if followup_case:
                saved_instance = form.save()
            else:
                saved_instance = form.save(commit=False)
                saved_instance.USUBJID = screening_case
                saved_instance.save()
                print(f"Created new FollowUpCase: {saved_instance.USUBJID_id}")

            # Thay thế đoạn dưới bằng đoạn bạn cung cấp:
            # Lưu từng form rehospitalization
            episode_counter = 1
            for form_instance in rehospitalization_formset.forms:
                if hasattr(form_instance, 'cleaned_data') and form_instance.cleaned_data and not form_instance.cleaned_data.get('DELETE', False):
                    obj = form_instance.save(commit=False)
                    obj.follow_up = saved_instance
                    # Chỉ gán EPISODE cho instance mới và có dữ liệu thực sự
                    if not obj.pk:
                        if obj.REHOSPDATE or obj.REHOSPREASONFOR or obj.REHOSPLOCATION:
                            obj.EPISODE = episode_counter
                            episode_counter += 1
                            obj.save()
                    else:
                        obj.save()
            for obj in getattr(rehospitalization_formset, 'deleted_objects', []):
                obj.delete()

            # Lưu từng form antibiotic
            episode_counter = 1
            for form_instance in antibiotic_formset.forms:
                if hasattr(form_instance, 'cleaned_data') and form_instance.cleaned_data and not form_instance.cleaned_data.get('DELETE', False):
                    obj = form_instance.save(commit=False)
                    obj.follow_up = saved_instance
                    if not obj.pk:
                        if obj.ANTIBIONAME or obj.ANTIBIOREASONFOR or obj.ANTIBIODUR:
                            obj.EPISODE = episode_counter
                            episode_counter += 1
                            obj.save()
                    else:
                        obj.save()
            for obj in getattr(antibiotic_formset, 'deleted_objects', []):
                obj.delete()
            
            # Đếm số lượng rehospitalization và antibiotic đã lưu
            rehosp_count = saved_instance.rehospitalizations.count()
            antibio_count = saved_instance.antibiotics.count()
            
            print(f"Current rehospitalization count: {rehosp_count}")
            print(f"Current antibiotic count: {antibio_count}")

            # Cập nhật số lượng tái nhập viện và kháng sinh
            if saved_instance.FU28REHOSP == 'Yes' and rehosp_count > 0:
                if saved_instance.FU28REHOSPCOUNT != rehosp_count:
                    saved_instance.FU28REHOSPCOUNT = rehosp_count
                    saved_instance.save(update_fields=['FU28REHOSPCOUNT'])
            
            if saved_instance.FU28USEDANTIBIO == 'Yes' and antibio_count > 0:
                if saved_instance.FU28ANTIBIOCOUNT != antibio_count:
                    saved_instance.FU28ANTIBIOCOUNT = antibio_count
                    saved_instance.save(update_fields=['FU28ANTIBIOCOUNT'])

            # Kiểm tra kết quả cuối cùng
            final_rehosp = saved_instance.rehospitalizations.all()
            final_antibio = saved_instance.antibiotics.all()
            print(f"FINAL CHECK: {final_rehosp.count()} rehospitalizations, {final_antibio.count()} antibiotics")
            for r in final_rehosp:
                print(f"  - Rehospitalization #{r.EPISODE}: {r.REHOSPDATE} at {r.REHOSPLOCATION}")
            for a in final_antibio:
                print(f"  - Antibiotic #{a.EPISODE}: {a.ANTIBIONAME} for {a.ANTIBIODUR}")

            messages.success(request, f'Đã lưu thông tin follow-up cho {usubjid}')
            return redirect('43en:patient_detail', usubjid=usubjid)
        else:
            print("FORM VALIDATION FAILED")
            print("Form errors:", form.errors)
            print("Rehospitalization formset errors:", rehospitalization_formset.errors)
            print("Antibiotic formset errors:", antibiotic_formset.errors)
            
            # Kiểm tra chi tiết từng form trong formset
            print("Checking each rehospitalization form:")
            for i, form_instance in enumerate(rehospitalization_formset.forms):
                print(f"  Form {i}: valid={form_instance.is_valid()}, errors={form_instance.errors}")
                if form_instance.is_valid():
                    print(f"  Data: {form_instance.cleaned_data}")
                else:
                    print(f"  Data: Invalid")
            
            print("Checking each antibiotic form:")
            for i, form_instance in enumerate(antibiotic_formset.forms):
                print(f"  Form {i}: valid={form_instance.is_valid()}, errors={form_instance.errors}")
                if form_instance.is_valid():
                    print(f"  Data: {form_instance.cleaned_data}")
                else:
                    print(f"  Data: Invalid")
            
            messages.error(request, 'Có lỗi trong form')
    else:
        # GET request - Sử dụng FormSet phù hợp
        # Form 28 ngày
        if followup_case:
            form = FollowUpCaseForm(instance=followup_case)
            # Sử dụng FormSet phù hợp với trạng thái
            if is_readonly:
                # Chế độ chỉ đọc - không có form trống
                rehospitalization_formset = RehospitalizationFormSetReadOnly(
                    prefix='rehospitalization_set',
                    instance=followup_case
                )
                antibiotic_formset = FollowUpAntibioticFormSetReadOnly(
                    prefix='antibiotic_set',
                    instance=followup_case
                )
            else:
                # Chế độ chỉnh sửa - có form trống để thêm mới
                rehospitalization_formset = RehospitalizationFormSet(
                    prefix='rehospitalization_set',
                    instance=followup_case
                )
                antibiotic_formset = FollowUpAntibioticFormSet(
                    prefix='antibiotic_set',
                    instance=followup_case
                )
        else:
            initial_data = {
                'COMPLETEDBY': request.user.username,
                'COMPLETEDDATE': date.today(),
            }
            form = FollowUpCaseForm(initial=initial_data)
            # Cho form mới
            rehospitalization_formset = RehospitalizationFormSet(
                prefix='rehospitalization_set'
            )
            antibiotic_formset = FollowUpAntibioticFormSet(
                prefix='antibiotic_set'
            )

        # Form 90 ngày
        if followup_case90:
            form90 = FollowUpCase90Form(instance=followup_case90)
            # Sử dụng FormSet phù hợp với trạng thái
            if is_readonly:
                # Chế độ chỉ đọc - không có form trống
                rehospitalization90_formset = Rehospitalization90FormSetReadOnly(
                    prefix='rehospitalization90_set',
                    instance=followup_case90
                )
                antibiotic90_formset = FollowUpAntibiotic90FormSetReadOnly(
                    prefix='antibiotic90_set',
                    instance=followup_case90
                )
            else:
                # Chế độ chỉnh sửa - có form trống để thêm mới
                rehospitalization90_formset = Rehospitalization90FormSet(
                    prefix='rehospitalization90_set',
                    instance=followup_case90
                )
                antibiotic90_formset = FollowUpAntibiotic90FormSet(
                    prefix='antibiotic90_set',
                    instance=followup_case90
                )
        else:
            initial_data = {
                'COMPLETEDBY': request.user.username,
                'COMPLETEDDATE': date.today(),
            }
            form90 = FollowUpCase90Form(initial=initial_data)
            # Cho form mới
            rehospitalization90_formset = Rehospitalization90FormSet(
                prefix='rehospitalization90_set'
            )
            antibiotic90_formset = FollowUpAntibiotic90FormSet(
                prefix='antibiotic90_set'
            )

        # Nếu là chế độ chỉ đọc, đặt readonly cho tất cả các trường
        if is_readonly:
            # Form 28 ngày
            for field in form.fields.values():
                field.widget.attrs['readonly'] = True
                field.widget.attrs['disabled'] = True

            # Đặt readonly cho tất cả các formset 28 ngày
            for formset in [rehospitalization_formset, antibiotic_formset]:
                for form_instance in formset.forms:
                    for field in form_instance.fields.values():
                        field.widget.attrs['readonly'] = True
                        field.widget.attrs['disabled'] = True
                        
            # Form 90 ngày
            for field in form90.fields.values():
                field.widget.attrs['readonly'] = True
                field.widget.attrs['disabled'] = True

            # Đặt readonly cho tất cả các formset 90 ngày
            for formset in [rehospitalization90_formset, antibiotic90_formset]:
                for form_instance in formset.forms:
                    for field in form_instance.fields.values():
                        field.widget.attrs['readonly'] = True
                        field.widget.attrs['disabled'] = True

    return render(request, 'study_43en/followup_form.html', {
        'screening_case': screening_case,
        'followup_case': followup_case,
        'form': form,
        'rehospitalization_formset': rehospitalization_formset,
        'antibiotic_formset': antibiotic_formset,
        'is_readonly': is_readonly,
        'has_followup28': has_followup28,
        'has_followup90': has_followup90,
        # Thêm các biến cho form 90 ngày
        'followup_case90': followup_case90,
        'form90': form90,
        'rehospitalization90_formset': rehospitalization90_formset,
        'antibiotic90_formset': antibiotic90_formset,
    })


@login_required
def followup_form_view(request, usubjid):
    """View readonly cho follow-up"""
    return followup_form(request, usubjid)


@login_required
def followup_case_detail(request, usubjid):
    """View chi tiết follow-up case - chỉ xem"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    try:
        followup_case = FollowUpCase.objects.get(USUBJID=screening_case)
        has_followup = True
        
        # Lấy related data
        rehospitalizations = followup_case.rehospitalizations.all().order_by('EPISODE')
        antibiotics = followup_case.antibiotics.all().order_by('EPISODE')
        
    except FollowUpCase.DoesNotExist:
        followup_case = None
        has_followup = False
        rehospitalizations = []
        antibiotics = []

    context = {
        'screening_case': screening_case,
        'followup_case': followup_case,
        'has_followup': has_followup,
        'rehospitalizations': rehospitalizations,
        'antibiotics': antibiotics,
        'is_readonly': True,
    }

    return render(request, 'study_43en/followup_case_detail.html', context)

@login_required
def followup_case90_create(request, usubjid):
    """Tạo mới thông tin FollowUpCase90 cho bệnh nhân - GIỐNG HỆT followup_case_create"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    # Kiểm tra xem đã có FollowUpCase90 chưa
    try:
        followup_case = FollowUpCase90.objects.get(USUBJID=screening_case)
        messages.warning(request, f'Bệnh nhân {usubjid} đã có thông tin theo dõi 90 ngày. Chuyển tới trang cập nhật.')
        return redirect('43en:followup_case90_update', usubjid=usubjid)
    except FollowUpCase90.DoesNotExist:
        pass

    if request.method == 'POST':
        form = FollowUpCase90Form(request.POST)
        rehospitalization_formset = Rehospitalization90FormSet(
            request.POST, 
            prefix='rehospitalization_set'  # SỬA: Giống form 28
        )
        antibiotic_formset = FollowUpAntibiotic90FormSet(
            request.POST, 
            prefix='antibiotic_set'  # SỬA: Giống form 28
        )

        formsets_valid = (
            rehospitalization_formset.is_valid() and
            antibiotic_formset.is_valid()
        )

        if form.is_valid() and formsets_valid:
            # Lưu followup case
            followup_case = form.save(commit=False)
            followup_case.USUBJID = screening_case
            followup_case.save()

            # SỬA: Bỏ logic manual assignment, để BaseFormSet tự xử lý
            # Lưu các formset với liên kết đến followup_case - GIỐNG FORM 28
            # Rehospitalization
            rehospitalization_instances = rehospitalization_formset.save(commit=False)
            for i, instance in enumerate(rehospitalization_instances, 1):
                instance.follow_up = followup_case
                instance.EPISODE = i  # Tự động đánh số thứ tự
                instance.save()

            # Antibiotic  
            antibiotic_instances = antibiotic_formset.save(commit=False)
            for i, instance in enumerate(antibiotic_instances, 1):
                instance.follow_up = followup_case
                instance.EPISODE = i  # Tự động đánh số thứ tự
                instance.save()

            # Xử lý các xóa từ formsets
            rehospitalization_formset.save()
            antibiotic_formset.save()

            messages.success(request, f'Đã tạo thông tin theo dõi 90 ngày cho bệnh nhân {usubjid} thành công.')
            return redirect('43en:patient_detail', usubjid=usubjid)
    else:
        initial_data = {
            'COMPLETEDBY': screening_case.COMPLETEDBY if screening_case.COMPLETEDBY else request.user.username,
            'COMPLETEDDATE': date.today(),
        }
        form = FollowUpCase90Form(initial=initial_data)
        rehospitalization_formset = Rehospitalization90FormSet(prefix='rehospitalization_set')  # SỬA: Giống form 28
        antibiotic_formset = FollowUpAntibiotic90FormSet(prefix='antibiotic_set')  # SỬA: Giống form 28

    return render(request, 'study_43en/followup_case90_form.html', {
        'form': form,
        'rehospitalization_formset': rehospitalization_formset,
        'antibiotic_formset': antibiotic_formset,
        'followup_case': {'USUBJID_id': screening_case.USUBJID},
        'screening_case': screening_case,
        'is_create': True,
        'today': date.today(),
    })


@login_required
def followup_case90_update(request, usubjid):
    """Cập nhật thông tin FollowUpCase90 cho bệnh nhân - GIỐNG HỆT followup_case_update"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    followup_case = get_object_or_404(FollowUpCase90, USUBJID=screening_case)

    if request.method == 'POST':
        form = FollowUpCase90Form(request.POST, instance=followup_case)
        rehospitalization_formset = Rehospitalization90FormSet(
            request.POST,
            prefix='rehospitalization_set',  # SỬA: Giống form 28
            instance=followup_case
        )
        antibiotic_formset = FollowUpAntibiotic90FormSet(
            request.POST,
            prefix='antibiotic_set',  # SỬA: Giống form 28
            instance=followup_case
        )

        formsets_valid = (
            rehospitalization_formset.is_valid() and
            antibiotic_formset.is_valid()
        )

        if form.is_valid() and formsets_valid:
            # SỬA: Logic giống hệt form 28 - Bỏ manual assignment
            # Lưu followup case trước
            followup_case = form.save()

            # Lưu các formset
            rehospitalization_formset.save()
            antibiotic_formset.save()

            messages.success(request, f'Đã cập nhật thông tin theo dõi 90 ngày cho bệnh nhân {usubjid} thành công.')
            return redirect('43en:patient_detail', usubjid=usubjid)
    else:
        form = FollowUpCase90Form(instance=followup_case)
        rehospitalization_formset = Rehospitalization90FormSetReadOnly(
            prefix='rehospitalization90_set', 
            instance=followup_case
        )
        antibiotic_formset = FollowUpAntibiotic90FormSetReadOnly(
            prefix='antibiotic90_set',
            instance=followup_case
        )

    return render(request, 'study_43en/followup_case90_form.html', {
        'form': form,
        'rehospitalization_formset': rehospitalization_formset,
        'antibiotic_formset': antibiotic_formset,
        'followup_case': followup_case,
        'screening_case': screening_case,
        'is_create': False,
        'today': date.today(),
    })


@login_required
def followup_case90_view(request, usubjid):
    """Xem thông tin FollowUpCase90 ở chế độ chỉ đọc - GIỐNG HỆT followup_case_view"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    try:
        followup_case = FollowUpCase90.objects.get(USUBJID=screening_case)
    except FollowUpCase90.DoesNotExist:
        messages.error(request, f'Bệnh nhân {usubjid} chưa có thông tin theo dõi 90 ngày.')
        return redirect('43en:patient_detail', usubjid=usubjid)

    # Tạo form với instance nhưng set is_view_only=True - GIỐNG FORM 28
    form = FollowUpCase90Form(instance=followup_case)
    rehospitalization_formset = Rehospitalization90FormSet(
        prefix='rehospitalization_set',  # SỬA: Giống form 28
        instance=followup_case
    )
    antibiotic_formset = FollowUpAntibiotic90FormSet(
        prefix='antibiotic_set',  # SỬA: Giống form 28
        instance=followup_case
    )

    # Đặt readonly cho tất cả các trường - GIỐNG FORM 28
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True

    # Đặt readonly cho tất cả các formset - GIỐNG FORM 28
    for formset in [rehospitalization_formset, antibiotic_formset]:
        for form_instance in formset.forms:
            for field in form_instance.fields.values():
                field.widget.attrs['readonly'] = True
                field.widget.attrs['disabled'] = True

    return render(request, 'study_43en/followup_form90.html', {  # SỬA: Dùng form template thay vì detail
        'form': form,
        'rehospitalization_formset': rehospitalization_formset,
        'antibiotic_formset': antibiotic_formset,
        'screening_case': screening_case,
        'followup_case': followup_case,
        'is_view_only': True,  # SỬA: Giống form 28
        'today': date.today(),
    })


@login_required  
def followup_case90_detail(request, usubjid):
    """View chi tiết follow-up case 90 ngày - chỉ xem - GIỐNG HỆT followup_case_detail"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    try:
        followup_case = FollowUpCase90.objects.get(USUBJID=screening_case)
        has_followup = True
        
        # Lấy related data
        rehospitalizations = followup_case.rehospitalizations.all().order_by('EPISODE')
        antibiotics = followup_case.antibiotics.all().order_by('EPISODE')
        
    except FollowUpCase90.DoesNotExist:
        followup_case = None
        has_followup = False
        rehospitalizations = []
        antibiotics = []

    context = {
        'screening_case': screening_case,
        'followup_case': followup_case,
        'has_followup': has_followup,
        'rehospitalizations': rehospitalizations,
        'antibiotics': antibiotics,
        'is_readonly': True,
    }

    return render(request, 'study_43en/followup_case90_detail.html', context)


@login_required
def followup_form90(request, usubjid):
    """View cho follow-up form 90 ngày - GIỐNG HỆT followup_form()"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    try:
        followup_case90 = FollowUpCase90.objects.get(USUBJID=screening_case)
        has_followup = True
    except FollowUpCase90.DoesNotExist:
        followup_case90 = None
        has_followup = False

    # Xác định xem có phải chế độ chỉ đọc không
    is_readonly = request.path.endswith('/view/')

    if request.method == 'POST' and not is_readonly:
        # DEBUG: In ra POST data để kiểm tra
        print("POST DATA:", request.POST)

        # POST - Luôn sử dụng FormSet có extra=1 để có thể thêm mới - GIỐNG FORM 28
        if followup_case90:
            form = FollowUpCase90Form(request.POST, instance=followup_case90)
            # SỬA: Thay đổi prefix từ rehospitalization_set thành rehospitalization90_set
            rehospitalization_formset = Rehospitalization90FormSet(
                request.POST,
                prefix='rehospitalization90_set',  # SỬA: Đúng prefix
                instance=followup_case90
            )
            # SỬA: Thay đổi prefix từ antibiotic_set thành antibiotic90_set
            antibiotic_formset = FollowUpAntibiotic90FormSet(
                request.POST,
                prefix='antibiotic90_set',  # SỬA: Đúng prefix
                instance=followup_case90
            )
        else:
            form = FollowUpCase90Form(request.POST)
            # SỬA: Thay đổi prefix từ rehospitalization_set thành rehospitalization90_set
            rehospitalization_formset = Rehospitalization90FormSet(
                request.POST,
                prefix='rehospitalization90_set'  # SỬA: Đúng prefix
            )
            # SỬA: Thay đổi prefix từ antibiotic_set thành antibiotic90_set
            antibiotic_formset = FollowUpAntibiotic90FormSet(
                request.POST,
                prefix='antibiotic90_set'  # SỬA: Đúng prefix
            )

        # DEBUG: In ra management form để kiểm tra số lượng form
        print("REHOSPITALIZATION MANAGEMENT:", rehospitalization_formset.management_form.cleaned_data if rehospitalization_formset.management_form.is_valid() else "Invalid management form")
        print("ANTIBIOTIC MANAGEMENT:", antibiotic_formset.management_form.cleaned_data if antibiotic_formset.management_form.is_valid() else "Invalid management form")

        # Kiểm tra form validity
        form_valid = form.is_valid()
        rehosp_valid = rehospitalization_formset.is_valid()
        antibio_valid = antibiotic_formset.is_valid()

        # Xử lý validation và save - LOGIC GIỐNG FORM 28
        if form_valid and rehosp_valid and antibio_valid:
            print("FORM IS VALID - Saving data...")

            if followup_case90:
                saved_instance = form.save()
            else:
                saved_instance = form.save(commit=False)
                saved_instance.USUBJID = screening_case
                saved_instance.save()
                print(f"Created new FollowUpCase90: {saved_instance.USUBJID_id}")

            # Lưu từng form rehospitalization 90
            episode_counter = 1
            for form_instance in rehospitalization_formset.forms:
                if hasattr(form_instance, 'cleaned_data') and form_instance.cleaned_data and not form_instance.cleaned_data.get('DELETE', False):
                    obj = form_instance.save(commit=False)
                    obj.follow_up = saved_instance
                    if not obj.pk:
                        if obj.REHOSPDATE or obj.REHOSPREASONFOR or obj.REHOSPLOCATION or obj.REHOSPSTAYDUR:
                            obj.EPISODE = episode_counter
                            episode_counter += 1
                            obj.save()
                    else:
                        obj.save()
            for obj in getattr(rehospitalization_formset, 'deleted_objects', []):
                obj.delete()

            # Lưu từng form antibiotic 90
            episode_counter = 1
            for form_instance in antibiotic_formset.forms:
                if hasattr(form_instance, 'cleaned_data') and form_instance.cleaned_data and not form_instance.cleaned_data.get('DELETE', False):
                    obj = form_instance.save(commit=False)
                    obj.follow_up = saved_instance
                    if not obj.pk:
                        if obj.ANTIBIONAME or obj.ANTIBIOREASONFOR or obj.ANTIBIODUR:
                            obj.EPISODE = episode_counter
                            episode_counter += 1
                            obj.save()
                    else:
                        obj.save()
            for obj in getattr(antibiotic_formset, 'deleted_objects', []):
                obj.delete()
            
            # Đếm số lượng rehospitalization và antibiotic đã lưu
            rehosp_count = saved_instance.rehospitalizations.count()
            antibio_count = saved_instance.antibiotics.count()
            
            print(f"Current rehospitalization count: {rehosp_count}")
            print(f"Current antibiotic count: {antibio_count}")

            # Cập nhật số lượng tái nhập viện và kháng sinh
            if saved_instance.FU90REHOSP == 'Yes' and rehosp_count > 0:
                if saved_instance.FU90REHOSPCOUNT != rehosp_count:
                    saved_instance.FU90REHOSPCOUNT = rehosp_count
                    saved_instance.save(update_fields=['FU90REHOSPCOUNT'])
            
            if saved_instance.FU90USEDANTIBIO == 'Yes' and antibio_count > 0:
                if saved_instance.FU90ANTIBIOCOUNT != antibio_count:
                    saved_instance.FU90ANTIBIOCOUNT = antibio_count
                    saved_instance.save(update_fields=['FU90ANTIBIOCOUNT'])

            # Kiểm tra kết quả cuối cùng
            final_rehosp = saved_instance.rehospitalizations.all()
            final_antibio = saved_instance.antibiotics.all()
            print(f"FINAL CHECK: {final_rehosp.count()} rehospitalizations, {final_antibio.count()} antibiotics")
            for r in final_rehosp:
                print(f"  - Rehospitalization #{r.EPISODE}: {r.REHOSPDATE} at {r.REHOSPLOCATION}")
            for a in final_antibio:
                print(f"  - Antibiotic #{a.EPISODE}: {a.ANTIBIONAME} for {a.ANTIBIODUR}")

            messages.success(request, f'Đã lưu thông tin follow-up 90 ngày cho {usubjid}')
            return redirect('43en:patient_detail', usubjid=usubjid)
        else:
            print("FORM VALIDATION FAILED")
            print("Form errors:", form.errors)
            print("Rehospitalization formset errors:", rehospitalization_formset.errors)
            print("Antibiotic formset errors:", antibiotic_formset.errors)
            
            # Kiểm tra chi tiết từng form trong formset - GIỐNG FORM 28
            print("Checking each rehospitalization form:")
            for i, form_instance in enumerate(rehospitalization_formset.forms):
                print(f"  Form {i}: valid={form_instance.is_valid()}, errors={form_instance.errors}")
                if form_instance.is_valid():
                    print(f"  Data: {form_instance.cleaned_data}")
                else:
                    print(f"  Data: Invalid")
            
            print("Checking each antibiotic form:")
            for i, form_instance in enumerate(antibiotic_formset.forms):
                print(f"  Form {i}: valid={form_instance.is_valid()}, errors={form_instance.errors}")
                if form_instance.is_valid():
                    print(f"  Data: {form_instance.cleaned_data}")
                else:
                    print(f"  Data: Invalid")
            
            messages.error(request, 'Có lỗi trong form')
    else:
        # GET request - Sử dụng FormSet phù hợp - GIỐNG FORM 28
        if followup_case90:
            form = FollowUpCase90Form(instance=followup_case90)
            
            # Sử dụng FormSet phù hợp với trạng thái
            if is_readonly:
                # Chế độ chỉ đọc - không có form trống
                rehospitalization_formset = Rehospitalization90FormSetReadOnly(
                    prefix='rehospitalization90_set',  # SỬA: Đúng prefix
                    instance=followup_case90
                )
                antibiotic_formset = FollowUpAntibiotic90FormSetReadOnly(
                    prefix='antibiotic90_set',  # SỬA: Đúng prefix
                    instance=followup_case90
                )
            else:
                # Chế độ chỉnh sửa - có form trống để thêm mới
                rehospitalization_formset = Rehospitalization90FormSet(
                    prefix='rehospitalization90_set',  # SỬA: Đúng prefix
                    instance=followup_case90
                )
                antibiotic_formset = FollowUpAntibiotic90FormSet(
                    prefix='antibiotic90_set',  # SỬA: Đúng prefix
                    instance=followup_case90
                )
        else:
            initial_data = {
                'COMPLETEDBY': request.user.username,
                'COMPLETEDDATE': date.today(),
            }
            form = FollowUpCase90Form(initial=initial_data)
            
            # Cho form mới
            rehospitalization_formset = Rehospitalization90FormSet(
                prefix='rehospitalization90_set'  # SỬA: Đúng prefix
            )
            antibiotic_formset = FollowUpAntibiotic90FormSet(
                prefix='antibiotic90_set'  # SỬA: Đúng prefix
            )

        # Nếu là chế độ chỉ đọc, đặt readonly cho tất cả các trường - GIỐNG FORM 28
        if is_readonly:
            for field in form.fields.values():
                field.widget.attrs['readonly'] = True
                field.widget.attrs['disabled'] = True
                
            # Đặt readonly cho tất cả các formset
            for formset in [rehospitalization_formset, antibiotic_formset]:
                for form_instance in formset.forms:
                    for field in form_instance.fields.values():
                        field.widget.attrs['readonly'] = True
                        field.widget.attrs['disabled'] = True

    return render(request, 'study_43en/followup_form90.html', {
        'screening_case': screening_case,
        'followup_case': followup_case90,
        'form': form,
        'rehospitalization_formset': rehospitalization_formset,
        'antibiotic_formset': antibiotic_formset,
        'is_readonly': is_readonly,
        'has_followup': has_followup,
    })


@login_required
def followup_form90_view(request, usubjid):
    """View readonly cho follow-up 90 ngày - GIỐNG HỆT followup_form_view"""
    return followup_form90(request, usubjid)


@login_required
def discharge_case_create(request, usubjid):
    """Tạo mới thông tin DischargeCase cho bệnh nhân - theo pattern followup_case_create"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    # Kiểm tra xem đã có DischargeCase chưa
    try:
        discharge_case = DischargeCase.objects.get(USUBJID=screening_case)
        messages.warning(request, f'Bệnh nhân {usubjid} đã có thông tin xuất viện. Chuyển tới trang cập nhật.')
        return redirect('43en:discharge_case_update', usubjid=usubjid)
    except DischargeCase.DoesNotExist:
        pass

    if request.method == 'POST':
        form = DischargeCaseForm(request.POST)
        icd_formset = DischargeICDFormSet(
            request.POST, 
            prefix='icd_set'
        )

        formsets_valid = icd_formset.is_valid()

        if form.is_valid() and formsets_valid:
            # Lưu discharge case
            discharge_case = form.save(commit=False)
            discharge_case.USUBJID = screening_case
            discharge_case.save()

            # Lưu các formset với liên kết đến discharge_case
            # ICD Codes
            icd_instances = icd_formset.save(commit=False)
            for i, instance in enumerate(icd_instances, 1):
                instance.discharge_case = discharge_case
                instance.EPISODE = i  # Tự động đánh số thứ tự
                instance.save()

            # Xử lý các xóa từ formsets
            icd_formset.save()

            messages.success(request, f'Đã tạo thông tin xuất viện cho bệnh nhân {usubjid} thành công.')
            return redirect('43en:patient_detail', usubjid=usubjid)
    else:
        initial_data = {
            'COMPLETEDBY': screening_case.COMPLETEDBY if screening_case.COMPLETEDBY else request.user.username,
            'COMPLETEDDATE': date.today(),
        }
        form = DischargeCaseForm(initial=initial_data)
        icd_formset = DischargeICDFormSet(prefix='icd_set')

    return render(request, 'study_43en/discharge_case_form.html', {
        'form': form,
        'icd_formset': icd_formset,
        'discharge_case': {'USUBJID_id': screening_case.USUBJID},
        'screening_case': screening_case,
        'is_create': True,
        'today': date.today(),
    })


@login_required
def discharge_case_update(request, usubjid):
    """Cập nhật thông tin DischargeCase cho bệnh nhân - theo pattern followup_case_update"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    discharge_case = get_object_or_404(DischargeCase, USUBJID=screening_case)

    if request.method == 'POST':
        form = DischargeCaseForm(request.POST, instance=discharge_case)
        icd_formset = DischargeICDFormSet(
            request.POST,
            prefix='icd_set',
            instance=discharge_case
        )

        formsets_valid = icd_formset.is_valid()

        if form.is_valid() and formsets_valid:
            # Lưu discharge case trước
            discharge_case = form.save()

            # Lưu các formset
            icd_formset.save()

            messages.success(request, f'Đã cập nhật thông tin xuất viện cho bệnh nhân {usubjid} thành công.')
            return redirect('43en:patient_detail', usubjid=usubjid)
    else:
        form = DischargeCaseForm(instance=discharge_case)
        icd_formset = DischargeICDFormSet(
            prefix='icd_set',
            instance=discharge_case
        )

    return render(request, 'study_43en/discharge_case_form.html', {
        'form': form,
        'icd_formset': icd_formset,
        'discharge_case': discharge_case,
        'screening_case': screening_case,
        'is_create': False,
        'today': date.today(),
    })


@login_required
def discharge_case_view(request, usubjid):
    """Xem thông tin DischargeCase ở chế độ chỉ đọc - theo pattern followup_case_view"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    try:
        discharge_case = DischargeCase.objects.get(USUBJID=screening_case)
    except DischargeCase.DoesNotExist:
        messages.error(request, f'Bệnh nhân {usubjid} chưa có thông tin xuất viện.')
        return redirect('43en:patient_detail', usubjid=usubjid)

    # Tạo form với instance nhưng set is_view_only=True - GIỐNG FORM 28
    form = DischargeCaseForm(instance=discharge_case)
    icd_formset = DischargeICDFormSet(
        prefix='icd_set',
        instance=discharge_case
    )

    # Đặt readonly cho tất cả các trường - GIỐNG FORM 28
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True

    # Đặt readonly cho tất cả các formset - GIỐNG FORM 28
    for form_instance in icd_formset.forms:
        for field in form_instance.fields.values():
            field.widget.attrs['readonly'] = True
            field.widget.attrs['disabled'] = True

    return render(request, 'study_43en/discharge_case_form.html', {
        'form': form,
        'icd_formset': icd_formset,
        'screening_case': screening_case,
        'discharge_case': discharge_case,
        'is_view_only': True,
        'today': date.today(),
    })


@login_required
def discharge_form(request, usubjid):
    """View cho discharge form - theo pattern followup_form"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    try:
        discharge_case = DischargeCase.objects.get(USUBJID=screening_case)
        has_discharge = True
    except DischargeCase.DoesNotExist:
        discharge_case = None
        has_discharge = False

    # Xác định xem có phải chế độ chỉ đọc không
    is_readonly = request.path.endswith('/view/')

    if request.method == 'POST' and not is_readonly:
        # DEBUG: In ra POST data để kiểm tra
        print("POST DATA:", request.POST)

        # POST - Luôn sử dụng FormSet có extra=1 để có thể thêm mới
        if discharge_case:
            form = DischargeCaseForm(request.POST, instance=discharge_case)
            icd_formset = DischargeICDFormSet(
                request.POST,
                prefix='icd_set',
                instance=discharge_case
            )
        else:
            form = DischargeCaseForm(request.POST)
            icd_formset = DischargeICDFormSet(
                request.POST,
                prefix='icd_set'
            )

        # DEBUG: In ra management form để kiểm tra số lượng form
        print("ICD MANAGEMENT:", icd_formset.management_form.cleaned_data if icd_formset.management_form.is_valid() else "Invalid management form")

        # Kiểm tra form validity
        form_valid = form.is_valid()
        icd_valid = icd_formset.is_valid()

        # DEBUG: In ra lỗi nếu có
        if not form_valid:
            print("FORM ERRORS:", form.errors)
        if not icd_valid:
            print("ICD FORMSET ERRORS:", icd_formset.errors)
            print("ICD NON FORM ERRORS:", icd_formset.non_form_errors())

        # Xử lý validation và save
        if form_valid and icd_valid:
            print("FORM IS VALID - Saving data...")
            
            try:
                # Save discharge case trước
                if discharge_case:
                    # Cập nhật existing instance
                    saved_instance = form.save()
                    print(f"Updated existing DischargeCase: {saved_instance.USUBJID_id}")
                else:
                    # Tạo mới instance
                    saved_instance = form.save(commit=False)
                    saved_instance.USUBJID = screening_case
                    saved_instance.save()
                    print(f"Created new DischargeCase: {saved_instance.USUBJID_id}")

                # Lưu ICD formset với proper instance handling
                icd_instances = icd_formset.save(commit=False)
                
                # Xử lý từng instance riêng
                for i, instance in enumerate(icd_instances):
                    if instance:  # Chỉ lưu nếu instance tồn tại
                        instance.discharge_case = saved_instance
                        if not instance.EPISODE:
                            instance.EPISODE = i + 1
                        instance.save()
                        print(f"Saved ICD instance: {instance.EPISODE} - {instance.ICDCODE}")

                # Xử lý xóa các instance được đánh dấu DELETE
                for obj in icd_formset.deleted_objects:
                    if obj.pk:
                        obj.delete()
                        print(f"Deleted ICD instance: {obj.pk}")

                # Đếm số lượng ICD đã lưu
                icd_count = saved_instance.icd_codes.count()
                print(f"Final ICD count: {icd_count}")

                messages.success(request, f'Đã lưu thông tin xuất viện cho {usubjid} thành công.')
                return redirect('43en:patient_detail', usubjid=usubjid)
                
            except Exception as e:
                print(f"ERROR SAVING: {str(e)}")
                messages.error(request, f'Có lỗi khi lưu dữ liệu: {str(e)}')
        else:
            print("FORM VALIDATION FAILED")
            print("Form errors:", form.errors if not form_valid else "No form errors")
            print("ICD formset errors:", icd_formset.errors if not icd_valid else "No formset errors")
            
            messages.error(request, 'Có lỗi trong form. Vui lòng kiểm tra lại.')
    else:
        # GET request - Sử dụng FormSet phù hợp
        if discharge_case:
            form = DischargeCaseForm(instance=discharge_case)
            
            # Sử dụng FormSet phù hợp với trạng thái
            if is_readonly:
                # Chế độ chỉ đọc - không có form trống
                icd_formset = DischargeICDFormSetReadOnly(
                    prefix='icd_set',
                    instance=discharge_case
                )
            else:
                # Chế độ chỉnh sửa - có form trống để thêm mới
                icd_formset = DischargeICDFormSet(
                    prefix='icd_set',
                    instance=discharge_case
                )
        else:
            # Form mới
            initial_data = {
                'EVENT': 'DISCHARGE',
                'STUDYID': '43EN',
                'SITEID': screening_case.SITEID,
                'SUBJID': screening_case.SUBJID,
                'INITIAL': screening_case.INITIAL,
                'COMPLETEDBY': request.user.username,
                'COMPLETEDDATE': date.today(),
            }
            form = DischargeCaseForm(initial=initial_data)
            
            # Cho form mới - tạo formset với ít nhất 1 form trống
            icd_formset = DischargeICDFormSet(
                prefix='icd_set'
            )

        # Nếu là chế độ chỉ đọc, đặt readonly cho tất cả các trường
        if is_readonly:
            for field in form.fields.values():
                field.widget.attrs['readonly'] = True
                field.widget.attrs['disabled'] = True
                
            # Đặt readonly cho tất cả các formset
            for form_instance in icd_formset.forms:
                for field in form_instance.fields.values():
                    field.widget.attrs['readonly'] = True
                    field.widget.attrs['disabled'] = True

    return render(request, 'study_43en/discharge_form.html', {
        'screening_case': screening_case,
        'discharge_case': discharge_case,
        'form': form,
        'icd_formset': icd_formset,
        'is_readonly': is_readonly,
        'has_discharge': has_discharge,
    })


@login_required
def discharge_form_view(request, usubjid):
    """View readonly cho discharge - GIỐNG HỆT followup_form_view"""
    return discharge_form(request, usubjid)

@login_required
def contact_list(request):
    query = request.GET.get('q', '')
    
    eligible_screening_contacts = ScreeningContact.objects.filter(
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
            contact.has_sample = ContactSampleCollection.objects.filter(contact_case=contact.enrollmentcontact).exists()
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

    return render(request, 'study_43en/contact_list.html', context)


@login_required
def contact_detail(request, usubjid):
    """View chi tiết contact"""
    try:
        screening_contact = ScreeningContact.objects.get(USUBJID=usubjid)
        
        # Kiểm tra enrollment contact
        try:
            enrollment_contact = EnrollmentContact.objects.get(USUBJID=screening_contact)
            has_enrollment = True
        except EnrollmentContact.DoesNotExist:
            enrollment_contact = None
            has_enrollment = False

        # Kiểm tra sample collection
        has_sample = False
        sample_collection = None
        sample_count = 0
        if has_enrollment:
            # Kiểm tra xem có mẫu nào không thay vì lấy mẫu cụ thể
            sample_count = ContactSampleCollection.objects.filter(contact_case=enrollment_contact).count()
            has_sample = sample_count > 0
            if has_sample:
                # Lấy mẫu đầu tiên để hiển thị thông tin
                sample_collection = ContactSampleCollection.objects.filter(contact_case=enrollment_contact).first()

        # Kiểm tra follow-up 28 ngày
        followup_28 = None
        if has_enrollment:
            try:
                followup_28 = ContactFollowUp28.objects.get(contact_case=enrollment_contact)
            except ContactFollowUp28.DoesNotExist:
                pass

        # Kiểm tra follow-up 90 ngày
        followup_90 = None
        if has_enrollment:
            try:
                followup_90 = ContactFollowUp90.objects.get(contact_case=enrollment_contact)
            except ContactFollowUp90.DoesNotExist:
                pass
        
        # Tính phần trăm hoàn thành
        completion_steps = 5  # Screening, Enrollment, Sample Collection, Follow-up 28, Follow-up 90
        completed_steps = 1   # Screening đã hoàn thành

        if has_enrollment:
            completed_steps += 1
        if has_sample:
            completed_steps += 1
        if followup_28:
            completed_steps += 1
        if followup_90:
            completed_steps += 1

        completion_percentage = int((completed_steps / completion_steps) * 100)

        context = {
            'screening_contact': screening_contact,
            'enrollment_contact': enrollment_contact,
            'has_enrollment': has_enrollment,
            'sample_collection': sample_collection,
            'has_sample': has_sample,
            'sample_count': sample_count,
            'followup_28': followup_28,
            'followup_90': followup_90,
            'completion_percentage': completion_percentage,
        }

        return render(request, 'study_43en/contact_detail.html', context)
        
    except ScreeningContact.DoesNotExist:
        messages.error(request, f'Không tìm thấy contact {usubjid}')
        return redirect('43en:screening_contact_list')


@login_required
def contact_sample_collection_edit(request, usubjid, sample_type=None):
    """Tạo mới hoặc chỉnh sửa mẫu thu thập của người tiếp xúc"""
    # Lấy thông tin người tiếp xúc
    screening_contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    enrollment_contact = get_object_or_404(EnrollmentContact, USUBJID=screening_contact)
    
    # Kiểm tra xem đã có mẫu cho loại mẫu này chưa
    try:
        sample = ContactSampleCollection.objects.get(contact_case=enrollment_contact, sample_type=sample_type)
        is_new = False
    except ContactSampleCollection.DoesNotExist:
        sample = ContactSampleCollection(contact_case=enrollment_contact, sample_type=sample_type)
        is_new = True
    
    if request.method == 'POST':
        # Debug POST data
        print(f"POST Data: {request.POST}")
        
        # Create a mutable copy of POST data
        post_data = request.POST.copy()
        
        # Get the sample type
        sample_type = post_data.get('sample_type')
        
        # Map the fields based on sample type
        if sample_type == '3':
            # For sample type 3, map STOOL → STOOL_3, etc.
            field_mappings = {
                'STOOL': 'STOOL_3',
                'THROATSWAB': 'THROATSWAB_3',
                'RECTSWAB': 'RECTSWAB_3',
                'STOOLDATE': 'STOOLDATE_3',
                'THROATSWABDATE': 'THROATSWABDATE_3',
                'RECTSWABDATE': 'RECTSWABDATE_3',
                'CULTRESSTOOL': 'CULTRESSTOOL_3',
                'CULTRESTHROATSWAB': 'CULTRESTHROATSWAB_3',
                'CULTRESRECTSWAB': 'CULTRESRECTSWAB_3',
                'KLEBPNEU': 'KLEBPNEU_5',
                'KLEBPNEU_2': 'KLEBPNEU_6',
                'KLEBPNEU_3': 'KLEBPNEU_5',
                'OTHERRES': 'OTHERRES_5',
                'OTHERRES_2': 'OTHERRES_6',
                'OTHERRES_3': 'OTHERRES_5',
                'OTHERRESSPECIFY': 'OTHERRESSPECIFY_5',
                'OTHERRESSPECIFY_2': 'OTHERRESSPECIFY_6',
                'OTHERRESSPECIFY_3': 'OTHERRESSPECIFY_5',
                'REASONIFNO': 'REASONIFNO_3'
            }
            
            # Copy values to the correct fields
            for source, target in field_mappings.items():
                if source in post_data:
                    post_data[target] = post_data[source]
                    
            # Set SAMPLE3 to True if any samples are collected
            if 'STOOL' in post_data and post_data['STOOL'] == 'on':
                post_data['SAMPLE3'] = 'True'
            elif 'THROATSWAB' in post_data and post_data['THROATSWAB'] == 'on':
                post_data['SAMPLE3'] = 'True'
            elif 'RECTSWAB' in post_data and post_data['RECTSWAB'] == 'on':
                post_data['SAMPLE3'] = 'True'
            
        elif sample_type == '4':
            # For sample type 4, map STOOL → STOOL_4, etc.
            field_mappings = {
                'STOOL': 'STOOL_4',
                'THROATSWAB': 'THROATSWAB_4',
                'RECTSWAB': 'RECTSWAB_4',
                'STOOLDATE': 'STOOLDATE_4',
                'THROATSWABDATE': 'THROATSWABDATE_4',
                'RECTSWABDATE': 'RECTSWABDATE_4',
                'CULTRESSTOOL': 'CULTRESSTOOL_4',
                'CULTRESTHROATSWAB': 'CULTRESTHROATSWAB_4',
                'CULTRESRECTSWAB': 'CULTRESRECTSWAB_4',
                'KLEBPNEU': 'KLEBPNEU_7',
                'KLEBPNEU_2': 'KLEBPNEU_8',
                'KLEBPNEU_3': 'KLEBPNEU_7',
                'OTHERRES': 'OTHERRES_7',
                'OTHERRES_2': 'OTHERRES_8',
                'OTHERRES_3': 'OTHERRES_7',
                'OTHERRESSPECIFY': 'OTHERRESSPECIFY_7',
                'OTHERRESSPECIFY_2': 'OTHERRESSPECIFY_8',
                'OTHERRESSPECIFY_3': 'OTHERRESSPECIFY_7',
                'REASONIFNO': 'REASONIFNO_4'
            }
            
            # Copy values to the correct fields
            for source, target in field_mappings.items():
                if source in post_data:
                    post_data[target] = post_data[source]
                    
            # Set SAMPLE4 to True if any samples are collected
            if 'STOOL' in post_data and post_data['STOOL'] == 'on':
                post_data['SAMPLE4'] = 'True'
            elif 'THROATSWAB' in post_data and post_data['THROATSWAB'] == 'on':
                post_data['SAMPLE4'] = 'True'
            elif 'RECTSWAB' in post_data and post_data['RECTSWAB'] == 'on':
                post_data['SAMPLE4'] = 'True'
        
        # Set boolean fields to False if they're not in the POST data
        boolean_fields = [
            'STOOL', 'THROATSWAB', 'RECTSWAB', 'BLOOD',
            'KLEBPNEU', 'OTHERRES', 'KLEBPNEU_2', 'OTHERRES_2', 'KLEBPNEU_3', 'OTHERRES_3',
            'STOOL_3', 'THROATSWAB_3', 'RECTSWAB_3',
            'KLEBPNEU_5', 'OTHERRES_5', 'KLEBPNEU_6', 'OTHERRES_6',
            'STOOL_4', 'THROATSWAB_4', 'RECTSWAB_4',
            'KLEBPNEU_7', 'OTHERRES_7', 'KLEBPNEU_8', 'OTHERRES_8',
            'SAMPLE1', 'SAMPLE3', 'SAMPLE4'
        ]
        
        for field in boolean_fields:
            if field not in post_data or post_data.get(field) == '':
                post_data[field] = False
            elif post_data[field] == 'on':
                post_data[field] = 'True'
        
        # Ensure COMPLETEDDATE is set
        if not post_data.get('COMPLETEDDATE'):
            from datetime import date
            post_data['COMPLETEDDATE'] = date.today().strftime('%Y-%m-%d')
        
        # Use the modified post_data
        form = ContactSampleCollectionForm(post_data, instance=sample)
        
        if form.is_valid():
            sample = form.save(commit=False)
            sample.contact_case = enrollment_contact
            
            # Debug form data
            print(f"Form is valid. BLOOD field: {form.cleaned_data.get('BLOOD')}")
            
            # Logic đồng bộ SAMPLE1/3/4 dựa trên các mẫu được chọn
            sample.SAMPLE1 = any([sample.STOOL, sample.THROATSWAB, sample.RECTSWAB, sample.BLOOD])
            sample.SAMPLE3 = any([sample.STOOL_3, sample.THROATSWAB_3, sample.RECTSWAB_3])
            sample.SAMPLE4 = any([sample.STOOL_4, sample.THROATSWAB_4, sample.RECTSWAB_4])
            
            # Xóa ngày nếu checkbox không chọn
            if not sample.STOOL: sample.STOOLDATE = None
            if not sample.THROATSWAB: sample.THROATSWABDATE = None
            if not sample.RECTSWAB: sample.RECTSWABDATE = None
            if not sample.BLOOD: sample.BLOODDATE = None
            
            if not sample.STOOL_3: sample.STOOLDATE_3 = None
            if not sample.THROATSWAB_3: sample.THROATSWABDATE_3 = None
            if not sample.RECTSWAB_3: sample.RECTSWABDATE_3 = None
            
            if not sample.STOOL_4: sample.STOOLDATE_4 = None
            if not sample.THROATSWAB_4: sample.THROATSWABDATE_4 = None
            if not sample.RECTSWAB_4: sample.RECTSWABDATE_4 = None
            
            # Lưu người hoàn thành nếu chưa có
            if not sample.COMPLETEDBY:
                sample.COMPLETEDBY = request.user.username
            
            # Debug thông tin trước khi lưu
            debug_info = {
                'SAMPLE1': sample.SAMPLE1,
                'STOOL': sample.STOOL,
                'THROATSWAB': sample.THROATSWAB,
                'RECTSWAB': sample.RECTSWAB,
                'BLOOD': sample.BLOOD,
                'BLOODDATE': sample.BLOODDATE,
                'sample_type': sample.sample_type
            }
            
            # Lưu và redirect
            sample.save()
            messages.success(request, f'Đã {"tạo mới" if is_new else "cập nhật"} thông tin mẫu thành công!')
            messages.debug(request, f'Thông tin đã lưu: {debug_info}')
            return redirect('43en:contact_sample_collection_list', usubjid=usubjid)
        else:
            messages.error(request, 'Có lỗi trong biểu mẫu, vui lòng kiểm tra kỹ lại.')
            print(f"Form errors: {form.errors}")
    else:
        form = ContactSampleCollectionForm(instance=sample)
    
    is_readonly = request.GET.get('mode') == 'view'
    if is_readonly:
        for field in form.fields.values():
            field.widget.attrs['readonly'] = True
            field.widget.attrs['disabled'] = True
    
    return render(request, 'study_43en/contact_sample_collection_form.html', {
        'form': form,
        'sample': sample,
        'screening_contact': screening_contact,
        'enrollment_contact': enrollment_contact,
        'is_new': is_new,
        'usubjid': usubjid,
        'sample_type': sample_type,
        'is_readonly': is_readonly,
        'today': timezone.now().date(),
    })


@login_required
def contact_sample_collection_list(request, usubjid):
    """Hiển thị danh sách các mẫu đã thu thập của người tiếp xúc - GIỐNG SAMPLE COLLECTION"""
    screening_contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    
    # Kiểm tra chế độ xem/chỉnh sửa - GIỐNG
    mode = request.GET.get('mode', 'edit')  # Mặc định là chế độ chỉnh sửa
    is_view_only = mode == 'view'  # Xác định chế độ chỉ xem
    
    try:
        enrollment_contact = EnrollmentContact.objects.get(USUBJID=screening_contact)
    except EnrollmentContact.DoesNotExist:
        messages.error(request, f'Người tiếp xúc {usubjid} chưa có thông tin ghi danh.')
        return redirect('43en:contact_detail', usubjid=usubjid)
    
    # Lấy tất cả các loại mẫu có thể thu thập - GIỐNG
    sample_types = ContactSampleCollection.SAMPLE_TYPE_CHOICES
    
    # Lấy tất cả các mẫu của người tiếp xúc - GIỐNG
    samples = ContactSampleCollection.objects.filter(contact_case=enrollment_contact)
    
    # Tạo dictionary để lưu trữ mẫu theo loại - GIỐNG
    samples_by_type = {sample.sample_type: sample for sample in samples}
    
    return render(request, 'study_43en/contact_sample_collection_list.html', {
        'usubjid': usubjid,
        'screening_contact': screening_contact,
        'enrollment_contact': enrollment_contact,
        'sample_types': sample_types,
        'samples': samples,
        'samples_by_type': samples_by_type,
        'is_view_only': is_view_only,
    })

@login_required
def contact_sample_collection_view(request, usubjid, sample_type):
    """Xem thông tin mẫu ở chế độ chỉ đọc - GIỐNG SAMPLE COLLECTION"""
    screening_contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    
    try:
        enrollment_contact = EnrollmentContact.objects.get(USUBJID=screening_contact)
    except EnrollmentContact.DoesNotExist:
        messages.error(request, f'Người tiếp xúc {usubjid} chưa có thông tin ghi danh.')
        return redirect('43en:contact_detail', usubjid=usubjid)
    
    sample = get_object_or_404(ContactSampleCollection, contact_case=enrollment_contact, sample_type=sample_type)
    
    # Tạo form với instance nhưng disable tất cả các field - GIỐNG
    form = ContactSampleCollectionForm(instance=sample)
    
    # Disable tất cả các field để chỉ có thể xem - GIỐNG
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True
    
    return render(request, 'study_43en/contact_sample_collection_form.html', {
        'form': form,
        'sample': sample,
        'screening_contact': screening_contact,
        'enrollment_contact': enrollment_contact,
        'is_view_only': True,
        'usubjid': usubjid,
        'sample_type': sample_type,
    })

# Trong views.py
@login_required
def contact_followup_28_edit(request, usubjid):
    """Tạo mới hoặc chỉnh sửa follow-up ngày 28 cho contact"""
    screening_contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    
    try:
        enrollment_contact = EnrollmentContact.objects.get(USUBJID=screening_contact)
    except EnrollmentContact.DoesNotExist:
        messages.error(request, f'Người tiếp xúc {usubjid} chưa có thông tin ghi danh.')
        return redirect('43en:contact_detail', usubjid=usubjid)
    
    try:
        followup_28 = ContactFollowUp28.objects.get(contact_case=enrollment_contact)
        is_new = False
    except ContactFollowUp28.DoesNotExist:
        followup_28 = None
        is_new = True
    
    if request.method == 'POST':
        form = ContactFollowUp28Form(request.POST, instance=followup_28)
        medication_formset = ContactMedicationHistoryFormSet(
            request.POST, 
            instance=followup_28
        )
        
        if form.is_valid() and medication_formset.is_valid():
            followup_28 = form.save(commit=False)
            followup_28.contact_case = enrollment_contact
            followup_28.save()
            
            medication_formset.instance = followup_28
            medication_formset.save()
            
            messages.success(request, 'Lưu follow-up 28 ngày thành công!')
            return redirect('43en:contact_detail', usubjid=usubjid)
    else:
        form = ContactFollowUp28Form(instance=followup_28)
        medication_formset = ContactMedicationHistoryFormSet(instance=followup_28)
    
    context = {
        'form': form,
        'medication_formset': medication_formset,
        'contact': enrollment_contact,
        'screening_contact': screening_contact,
        'is_new': is_new,
        'followup_type': '28',
    }
    return render(request, 'study_43en/contact_followup_form.html', context)

@login_required
def contact_followup_28_view(request, usubjid):
    """Xem follow-up ngày 28 cho contact ở chế độ chỉ đọc"""
    screening_contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    
    try:
        enrollment_contact = EnrollmentContact.objects.get(USUBJID=screening_contact)
    except EnrollmentContact.DoesNotExist:
        messages.error(request, f'Người tiếp xúc {usubjid} chưa có thông tin ghi danh.')
        return redirect('43en:contact_detail', usubjid=usubjid)
    
    followup_28 = get_object_or_404(ContactFollowUp28, contact_case=enrollment_contact)
    
    # Tạo form với instance nhưng disable tất cả các field
    form = ContactFollowUp28Form(instance=followup_28)
    medication_formset = ContactMedicationHistoryFormSet(instance=followup_28)
    
    # Disable tất cả các field để chỉ có thể xem
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True
    
    context = {
        'form': form,
        'medication_formset': medication_formset,
        'contact': enrollment_contact,
        'screening_contact': screening_contact,
        'is_view_only': True,
        'followup_type': '28',
    }
    return render(request, 'study_43en/contact_followup_form.html', context)

@login_required
def contact_followup_90_edit(request, usubjid):
    """Tạo mới hoặc chỉnh sửa follow-up ngày 90 cho contact"""
    screening_contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    
    try:
        enrollment_contact = EnrollmentContact.objects.get(USUBJID=screening_contact)
    except EnrollmentContact.DoesNotExist:
        messages.error(request, f'Người tiếp xúc {usubjid} chưa có thông tin ghi danh.')
        return redirect('43en:contact_detail', usubjid=usubjid)
    
    try:
        followup_90 = ContactFollowUp90.objects.get(contact_case=enrollment_contact)
        is_new = False
    except ContactFollowUp90.DoesNotExist:
        followup_90 = None
        is_new = True
    
    if request.method == 'POST':
        form = ContactFollowUp90Form(request.POST, instance=followup_90)
        medication_formset = ContactMedicationHistory90FormSet(
            request.POST, 
            instance=followup_90
        )
        
        # Debug: In ra lỗi form nếu có
        if not form.is_valid():
            print("Form errors:", form.errors)
            for field_name, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'Lỗi trường {field_name}: {error}')
        
        if not medication_formset.is_valid():
            print("Formset errors:", medication_formset.errors)
            for form_errors in medication_formset.errors:
                for field_name, errors in form_errors.items():
                    for error in errors:
                        messages.error(request, f'Lỗi thuốc - {field_name}: {error}')
        
        if form.is_valid() and medication_formset.is_valid():
            try:
                followup_90 = form.save(commit=False)
                followup_90.contact_case = enrollment_contact
                followup_90.save()
                
                medication_formset.instance = followup_90
                medication_formset.save()
                
                messages.success(request, 'Lưu follow-up 90 ngày thành công!')
                return redirect('43en:contact_detail', usubjid=usubjid)
            except Exception as e:
                messages.error(request, f'Lỗi khi lưu: {str(e)}')
                print(f"Save error: {e}")
    else:
        form = ContactFollowUp90Form(instance=followup_90)
        medication_formset = ContactMedicationHistory90FormSet(instance=followup_90)
    
    context = {
        'form': form,
        'medication_formset': medication_formset,
        'contact': enrollment_contact,
        'screening_contact': screening_contact,
        'is_new': is_new,
        'followup_type': '90',
    }
    return render(request, 'study_43en/contact_followup_90_form.html', context)

@login_required
def contact_followup_90_view(request, usubjid):
    """Xem follow-up ngày 90 cho contact ở chế độ chỉ đọc"""
    screening_contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    
    try:
        enrollment_contact = EnrollmentContact.objects.get(USUBJID=screening_contact)
    except EnrollmentContact.DoesNotExist:
        messages.error(request, f'Người tiếp xúc {usubjid} chưa có thông tin ghi danh.')
        return redirect('43en:contact_detail', usubjid=usubjid)
    
    followup_90 = get_object_or_404(ContactFollowUp90, contact_case=enrollment_contact)
    
    # Tạo form với instance nhưng disable tất cả các field
    form = ContactFollowUp90Form(instance=followup_90)
    medication_formset = ContactMedicationHistory90FormSet(instance=followup_90)
    
    # Disable tất cả các field để chỉ có thể xem
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True
    
    context = {
        'form': form,
        'medication_formset': medication_formset,
        'contact': enrollment_contact,
        'screening_contact': screening_contact,
        'is_view_only': True,
        'followup_type': '90',
    }
    return render(request, 'study_43en/contact_followup_90_form.html', context)