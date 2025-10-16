import json
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.utils.translation import gettext as _

# Import models
from backends.studies.study_43en.models.patient import (
    EnrollmentCase,LaboratoryTest,SampleCollection
)

# Import forms
from backends.studies.study_43en.forms_patient import (
    LaboratoryTestFormSet,
    SampleCollectionForm
)

# Import utils
from backends.studies.study_43en.utils.audit_log_cross_db import audit_log_decorator
from backends.studies.study_43en.utils.audit_log_utils import safe_json_loads

logger = logging.getLogger(__name__)


from datetime import date




@login_required
@audit_log_decorator(model_name='LABORATORYTEST')
def laboratory_test_create(request, usubjid, lab_type):
    """Tạo mới tất cả các xét nghiệm cho một lần LAB_TYPE (1, 2, 3)"""
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID__USUBJID=usubjid)
    default_test_types = [t[0] for t in LaboratoryTest.TEST_TYPE_CHOICES]
    created_count = 0

    # Tự động tạo xét nghiệm cho cả GET và POST request
    for test_type in default_test_types:
        if not LaboratoryTest.objects.filter(
            USUBJID=enrollment_case,
            LAB_TYPE=lab_type,
            TESTTYPE=test_type
        ).exists():
            temp_lab_test = LaboratoryTest(TESTTYPE=test_type)
            category = temp_lab_test._get_category_from_test_type()
            LaboratoryTest.objects.create(
                USUBJID=enrollment_case,
                LAB_TYPE=lab_type,
                TESTTYPE=test_type,
                CATEGORY=category,
                PERFORMED=False
            )
            created_count += 1
            logger.debug(f"Created laboratory test: {test_type} for {usubjid}, lab_type={lab_type}")
    
    # Chuẩn bị audit data cho decorator
    request.audit_data = {
        'old_data': {},
        'new_data': {'created_count': created_count, 'lab_type': lab_type},
        'reasons_json': {},
        'reason': f'Tạo {created_count} xét nghiệm mới cho lần {lab_type}'
    }
    
    # Hiển thị message và redirect
    if created_count > 0:
        messages.success(request, f'Đã tạo {created_count} xét nghiệm cho lần {lab_type} thành công.')
    else:
        messages.info(request, f'Xét nghiệm cho lần {lab_type} đã tồn tại.')
    
    # Sau khi tạo, chuyển hướng đến trang bulk-update để nhập dữ liệu
    return redirect('study_43en:laboratory_test_bulk_update', usubjid=usubjid, lab_type=lab_type)

@login_required
@audit_log_decorator(model_name='LABORATORYTEST')
def laboratory_test_create_category(request, usubjid, lab_type):
    """Tạo mới các xét nghiệm cho một category cụ thể trong một lần LAB_TYPE"""
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID__USUBJID=usubjid)
    
    # Chuẩn bị audit data
    old_data = safe_json_loads(request.POST.get('oldDataJson', '{}'))
    new_data = safe_json_loads(request.POST.get('newDataJson', '{}'))
    reasons_json = safe_json_loads(request.POST.get('reasonsJson', '{}'))
    change_reason = request.POST.get('change_reason', '')
    
    print("DEBUG - laboratory_test_create_category - old_data:", old_data)
    print("DEBUG - laboratory_test_create_category - new_data:", new_data)
    print("DEBUG - laboratory_test_create_category - reasons_json:", reasons_json)
    print("DEBUG - laboratory_test_create_category - change_reason:", change_reason)
    
    request.audit_data = {
        'old_data': old_data,
        'new_data': new_data,
        'reasons_json': reasons_json,
        'reason': change_reason
    }

    if request.method != 'POST':
        return redirect('study_43en:laboratory_test_bulk_update', usubjid=usubjid, lab_type=lab_type)
        
    category = request.POST.get('category')
    created_count = 0
    
    # Lấy danh sách các test type thuộc category này
    all_test_types = [t for t in LaboratoryTest.TEST_TYPE_CHOICES]
    category_test_types = []
    
    temp_lab_test = LaboratoryTest()
    for test_type, test_name in all_test_types:
        temp_lab_test.TESTTYPE = test_type
        if temp_lab_test._get_category_from_test_type() == category:
            category_test_types.append(test_type)
    
    # Tạo mới các xét nghiệm
    for test_type in category_test_types:
        if not LaboratoryTest.objects.filter(
            USUBJID=enrollment_case,
            LAB_TYPE=lab_type,
            TESTTYPE=test_type
        ).exists():
            LaboratoryTest.objects.create(
                USUBJID=enrollment_case,
                LAB_TYPE=lab_type,
                TESTTYPE=test_type,
                CATEGORY=category,
                PERFORMED=False
            )
            created_count += 1
            
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if is_ajax:
        return JsonResponse({
            'success': True,
            'message': f'Đã tạo {created_count} xét nghiệm trong nhóm thành công.',
            'redirect_url': reverse('study_43en:laboratory_test_bulk_update', kwargs={'usubjid': usubjid, 'lab_type': lab_type})
        })
    else:
        if created_count > 0:
            messages.success(request, f'Đã tạo {created_count} xét nghiệm trong nhóm thành công.')
        else:
            messages.info(request, 'Không có xét nghiệm mới nào được tạo.')
        return redirect('study_43en:laboratory_test_bulk_update', usubjid=usubjid, lab_type=lab_type)

@login_required
@audit_log_decorator(model_name='LABORATORYTEST')
def laboratory_test_list(request, usubjid):
    """Hiển thị danh sách các lần xét nghiệm (LAB_TYPE) của bệnh nhân"""
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID__USUBJID=usubjid)
    lab_types = LaboratoryTest.LAB_TYPE_CHOICES
    all_tests = LaboratoryTest.objects.filter(USUBJID=enrollment_case)
    tests_by_lab_type = {lab_type[0]: [] for lab_type in lab_types}
    for test in all_tests:
        tests_by_lab_type.setdefault(test.LAB_TYPE, []).append(test)

    return render(request, 'studies/study_43en/CRF/laboratory_test_list.html', {
        'usubjid': usubjid,
        'enrollment_case': enrollment_case,
        'lab_types': lab_types,
        'tests_by_lab_type': tests_by_lab_type,
    })

@login_required
@audit_log_decorator(model_name='LABORATORYTEST')
def laboratory_test_bulk_update(request, usubjid, lab_type):
    """Cập nhật hàng loạt các xét nghiệm theo lần"""
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID__USUBJID=usubjid)
    lab_tests = LaboratoryTest.objects.filter(
        USUBJID=enrollment_case,
        LAB_TYPE=lab_type
    )

    # Chuẩn bị audit data
    old_data = safe_json_loads(request.POST.get('oldDataJson', '{}'))
    new_data = safe_json_loads(request.POST.get('newDataJson', '{}'))
    reasons_json = safe_json_loads(request.POST.get('reasonsJson', '{}'))
    change_reason = request.POST.get('change_reason', '')
    
    print("DEBUG - laboratory_test_bulk_update - old_data:", old_data)
    print("DEBUG - laboratory_test_bulk_update - new_data:", new_data)
    print("DEBUG - laboratory_test_bulk_update - reasons_json:", reasons_json)
    print("DEBUG - laboratory_test_bulk_update - change_reason:", change_reason)
    
    request.audit_data = {
        'old_data': old_data,
        'new_data': new_data,
        'reasons_json': reasons_json,
        'reason': change_reason
    }

    # Tạo dict để mapping từ category code -> danh sách test types
    category_test_map = {}
    for test_code, _ in LaboratoryTest.TEST_TYPE_CHOICES:
        temp_lab_test = LaboratoryTest(TESTTYPE=test_code)
        category = temp_lab_test._get_category_from_test_type()
        if category not in category_test_map:
            category_test_map[category] = []
        category_test_map[category].append(test_code)

    # Tạo dict để mapping từ test code -> form
    test_form_map = {}

    if request.method == 'POST':
        logger.debug("POST data: %s", request.POST)
        formset = LaboratoryTestFormSet(request.POST, queryset=lab_tests)
        
        if formset.is_valid():
            formset.save()
            
            # Xử lý các xét nghiệm mới
            new_tests = request.POST.getlist('new_tests')
            created_count = 0
            for test_info in new_tests:
                try:
                    test_code, category_code = test_info.split('|')
                    performed = request.POST.get(f'new_performed_{test_code}') == 'true'
                    if performed:
                        date = request.POST.get(f'new_date_{test_code}')
                        result = request.POST.get(f'new_result_{test_code}')
                        logger.debug(f"Creating new test: {test_code}, date: {date}, result: {result}")
                        LaboratoryTest.objects.create(
                            USUBJID=enrollment_case,
                            LAB_TYPE=lab_type,
                            TESTTYPE=test_code,
                            CATEGORY=category_code,
                            PERFORMED=True,
                            PERFORMEDDATE=date if date else None,
                            RESULT=result
                        )
                        created_count += 1
                except Exception as e:
                    logger.error(f"Lỗi khi tạo xét nghiệm mới {test_info}: {e}")

            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Đã cập nhật tất cả xét nghiệm thành công. Đã tạo thêm {created_count} xét nghiệm mới.',
                    'redirect_url': reverse('study_43en:laboratory_test_list', kwargs={'usubjid': usubjid})
                })
            else:
                messages.success(request, f'Đã cập nhật tất cả xét nghiệm thành công. Đã tạo thêm {created_count} xét nghiệm mới.')
                return redirect('study_43en:laboratory_test_list', usubjid=usubjid)
        else:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                errors = formset.errors
                logger.error("Formset errors: %s", errors)
                return JsonResponse({
                    'success': False,
                    'message': 'Có lỗi khi lưu xét nghiệm. Vui lòng kiểm tra lại.',
                    'errors': errors
                }, status=400)
            else:
                logger.error("Formset errors: %s", formset.errors)
                messages.error(request, f"Lỗi dữ liệu: {formset.errors}")
    else:
        formset = LaboratoryTestFormSet(queryset=lab_tests)

    # Tạo test_form_map từ formset
    for form in formset:
        test_code = form.instance.TESTTYPE
        test_form_map[test_code] = form

    return render(request, 'studies/study_43en/CRF/laboratory_test_bulk_update.html', {
        'formset': formset,
        'enrollment_case': enrollment_case,
        'lab_type': lab_type,
        'lab_type_choices': LaboratoryTest.LAB_TYPE_CHOICES,
        'all_categories': LaboratoryTest.CATEGORY_CHOICES,
        'all_test_types': LaboratoryTest.TEST_TYPE_CHOICES,
        'category_test_map': category_test_map,
        'test_form_map': test_form_map,
        'is_update': lab_tests.exists(),
    })

@login_required
@audit_log_decorator(model_name='LABORATORYTEST')
def laboratory_test_category_tests(request, usubjid, category):
    """Lấy danh sách các loại xét nghiệm thuộc một nhóm"""
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID__USUBJID=usubjid)
    try:
        all_test_types = dict(LaboratoryTest.TEST_TYPE_CHOICES)
        existing_tests = LaboratoryTest.objects.filter(
            USUBJID=enrollment_case,
            CATEGORY=category
        ).values_list('TESTTYPE', flat=True)
        temp = LaboratoryTest()
        category_tests = []
        for key, value in all_test_types.items():
            temp.TESTTYPE = key
            if temp._get_category_from_test_type() == category:
                if key not in existing_tests:
                    category_tests.append({
                        'value': key,
                        'label': value
                    })
        return JsonResponse({
            'success': True,
            'tests': category_tests
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)
