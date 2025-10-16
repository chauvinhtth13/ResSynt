import logging
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.utils.translation import gettext as _

# Import models từ study app
from backends.studies.study_43en.models.patient import (
    ScreeningCase, EnrollmentCase, DischargeCase, DischargeICD,

)


from backends.studies.study_43en.forms_patient import (
    DischargeCaseForm,DischargeICDFormSet

)



# Import utils từ study app
from backends.studies.study_43en.utils.audit_log_utils import (
    safe_json_loads
)
from backends.studies.study_43en.utils.audit_log_cross_db import audit_log_decorator

logger = logging.getLogger(__name__)





@login_required
@audit_log_decorator(model_name='DISCHARGECASE')
def discharge_case_create(request, usubjid):
    """Tạo mới thông tin xuất viện cho bệnh nhân"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    
    try:
        discharge_case = DischargeCase.objects.get(USUBJID=enrollment_case)
        messages.warning(request, f'Bệnh nhân {usubjid} đã có thông tin xuất viện. Chuyển tới trang cập nhật.')
        return redirect('study_43en:discharge_case_update', usubjid=usubjid)
    except DischargeCase.DoesNotExist:
        discharge_case = None

    # Chuẩn bị audit data
    old_data = safe_json_loads(request.POST.get('oldDataJson', '{}'))
    new_data = safe_json_loads(request.POST.get('newDataJson', '{}'))
    reasons_json = safe_json_loads(request.POST.get('reasonsJson', '{}'))
    change_reason = request.POST.get('change_reason', '')
    
    request.audit_data = {
        'old_data': old_data,
        'new_data': new_data,
        'reasons_json': reasons_json,
        'reason': change_reason
    }

    if request.method == 'POST':
        form = DischargeCaseForm(request.POST)
        icd_formset = DischargeICDFormSet(request.POST, prefix='icd_set')
        
        if form.is_valid() and icd_formset.is_valid():
            discharge_case = form.save(commit=False)
            discharge_case.USUBJID = enrollment_case
            discharge_case.save()
            
            icd_instances = icd_formset.save(commit=False)
            for i, instance in enumerate(icd_instances, 1):
                instance.discharge_case = discharge_case
                instance.EPISODE = i
                instance.save()
            icd_formset.save()

            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Đã tạo thông tin xuất viện cho bệnh nhân {usubjid} thành công!',
                    'redirect_url': reverse('study_43en:patient_detail', kwargs={'usubjid': usubjid})
                })
            else:
                messages.success(request, f'Đã tạo thông tin xuất viện cho bệnh nhân {usubjid} thành công.')
                return redirect('study_43en:patient_detail', usubjid=usubjid)
        else:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                errors = {}
                if form.errors:
                    errors.update(form.errors)
                if icd_formset.errors:
                    errors['icd'] = icd_formset.errors
                return JsonResponse({
                    'success': False,
                    'message': 'Có lỗi trong form, vui lòng kiểm tra lại.',
                    'errors': errors
                }, status=400)
            else:
                messages.error(request, 'Có lỗi trong form, vui lòng kiểm tra lại.')
    else:
        initial_data = {
            'EVENT': 'DISCHARGE',
            'STUDYID': '43EN',
            'SITEID': enrollment_case.USUBJID.SITEID,
            'SUBJID': enrollment_case.USUBJID.SUBJID,
            'INITIAL': enrollment_case.USUBJID.INITIAL,
            'COMPLETEDBY': request.user.username,
            'COMPLETEDDATE': date.today(),
        }
        form = DischargeCaseForm(initial=initial_data)
        icd_formset = DischargeICDFormSet(
            prefix='icd_set',
            queryset=DischargeICD.objects.none(),
            initial=[{'EPISODE': 1}]
        )

    return render(request, 'studies/study_43en/CRF/discharge_form.html', {
        'form': form,
        'icd_formset': icd_formset,
        'discharge_case': {'USUBJID_id': enrollment_case.USUBJID},
        'enrollment_case': enrollment_case,
        'is_create': True,
        'today': date.today(),
    })

@login_required
@audit_log_decorator(model_name='DISCHARGECASE')
def discharge_case_update(request, usubjid):
    """Cập nhật thông tin xuất viện cho bệnh nhân"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    discharge_case = get_object_or_404(DischargeCase, USUBJID=enrollment_case)

    # Chuẩn bị audit data
    old_data = safe_json_loads(request.POST.get('oldDataJson', '{}'))
    new_data = safe_json_loads(request.POST.get('newDataJson', '{}'))
    reasons_json = safe_json_loads(request.POST.get('reasonsJson', '{}'))
    change_reason = request.POST.get('change_reason', '')
    
    print("DEBUG - old_data:", old_data)
    print("DEBUG - new_data:", new_data)
    print("DEBUG - reasons_json:", reasons_json)
    print("DEBUG - change_reason:", change_reason)
    
    request.audit_data = {
        'old_data': old_data,
        'new_data': new_data,
        'reasons_json': reasons_json,
        'reason': change_reason
    }

    if request.method == 'POST':
        form = DischargeCaseForm(request.POST, instance=discharge_case)
        icd_formset = DischargeICDFormSet(request.POST, prefix='icd_set', instance=discharge_case)
        
        if form.is_valid() and icd_formset.is_valid():
            discharge_case = form.save()
            icd_instances = icd_formset.save(commit=False)
            for i, instance in enumerate(icd_instances, 1):
                instance.discharge_case = discharge_case
                instance.EPISODE = i
                instance.save()
            icd_formset.save()

            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Đã cập nhật thông tin xuất viện cho bệnh nhân {usubjid} thành công!',
                    'redirect_url': reverse('study_43en:patient_detail', kwargs={'usubjid': usubjid})
                })
            else:
                messages.success(request, f'Đã cập nhật thông tin xuất viện cho bệnh nhân {usubjid} thành công.')
                return redirect('study_43en:patient_detail', usubjid=usubjid)
        else:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                errors = {}
                if form.errors:
                    errors.update(form.errors)
                if icd_formset.errors:
                    errors['icd'] = icd_formset.errors
                print("DEBUG - Returning errors:", errors)
                return JsonResponse({
                    'success': False,
                    'message': 'Có lỗi trong form, vui lòng kiểm tra lại.',
                    'errors': errors
                }, status=400)
            else:
                messages.error(request, 'Có lỗi trong form, vui lòng kiểm tra lại.')
    else:
        form = DischargeCaseForm(instance=discharge_case)
        icd_formset = DischargeICDFormSet(prefix='icd_set', instance=discharge_case)

    return render(request, 'studies/study_43en/CRF/discharge_form.html', {
        'form': form,
        'icd_formset': icd_formset,
        'discharge_case': discharge_case,
        'enrollment_case': enrollment_case,
        'is_create': False,
        'today': date.today(),
    })

@login_required
@audit_log_decorator(model_name='DISCHARGECASE')
def discharge_form(request, usubjid):
    """View cho discharge form - hỗ trợ cả tạo mới và cập nhật"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    
    try:
        discharge_case = DischargeCase.objects.get(USUBJID=enrollment_case)
        has_discharge = True
    except DischargeCase.DoesNotExist:
        discharge_case = None
        has_discharge = False

    is_readonly = request.path.endswith('/view/')

    # Chuẩn bị audit data
    old_data = safe_json_loads(request.POST.get('oldDataJson', '{}'))
    new_data = safe_json_loads(request.POST.get('newDataJson', '{}'))
    reasons_json = safe_json_loads(request.POST.get('reasonsJson', '{}'))
    change_reason = request.POST.get('change_reason', '')
    
    print("DEBUG - discharge_form - old_data:", old_data)
    print("DEBUG - discharge_form - new_data:", new_data)
    print("DEBUG - discharge_form - reasons_json:", reasons_json)
    print("DEBUG - discharge_form - change_reason:", change_reason)
    
    request.audit_data = {
        'old_data': old_data,
        'new_data': new_data,
        'reasons_json': reasons_json,
        'reason': change_reason
    }

    if request.method == 'POST' and not is_readonly:
        if discharge_case:
            form = DischargeCaseForm(request.POST, instance=discharge_case)
            icd_formset = DischargeICDFormSet(request.POST, prefix='icd_set', instance=discharge_case)
        else:
            form = DischargeCaseForm(request.POST)
            icd_formset = DischargeICDFormSet(request.POST, prefix='icd_set')

        form_valid = form.is_valid()
        icd_valid = icd_formset.is_valid()

        if not form_valid:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'Lỗi trường {field}: {error}')
        
        if not icd_valid:
            for i, form_errors in enumerate(icd_formset.errors):
                for field, errors in form_errors.items():
                    for error in errors:
                        messages.error(request, f'Lỗi ICD #{i+1} - {field}: {error}')
            if icd_formset.non_form_errors():
                for error in icd_formset.non_form_errors():
                    messages.error(request, f'Lỗi formset ICD: {error}')

        if form_valid and icd_valid:
            if discharge_case:
                saved_instance = form.save()
            else:
                saved_instance = form.save(commit=False)
                saved_instance.USUBJID = enrollment_case
                saved_instance.save()

            existing_episodes = set(DischargeICD.objects.filter(
                discharge_case=saved_instance
            ).values_list('EPISODE', flat=True))
            
            next_episode = 1
            while next_episode in existing_episodes:
                next_episode += 1
            
            icd_instances = icd_formset.save(commit=False)
            for instance in icd_instances:
                if not instance.id:
                    instance.EPISODE = next_episode
                    next_episode += 1
                    while next_episode in existing_episodes:
                        next_episode += 1
                
                instance.discharge_case = saved_instance
                instance.save()
            icd_formset.save()

            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Đã lưu thông tin xuất viện cho {usubjid} thành công!',
                    'redirect_url': reverse('study_43en:patient_detail', kwargs={'usubjid': usubjid})
                })
            else:
                messages.success(request, f'Đã lưu thông tin xuất viện cho {usubjid} thành công.')
                return redirect('study_43en:patient_detail', usubjid=usubjid)
        else:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                errors = {}
                if form.errors:
                    errors.update(form.errors)
                if icd_formset.errors:
                    errors['icd'] = icd_formset.errors
                return JsonResponse({
                    'success': False,
                    'message': 'Có lỗi trong form, vui lòng kiểm tra lại.',
                    'errors': errors
                }, status=400)
            else:
                messages.error(request, 'Có lỗi trong form, vui lòng kiểm tra lại.')
    else:
        initial_data = {
            'EVENT': 'DISCHARGE',
            'STUDYID': '43EN',
            'SITEID': enrollment_case.USUBJID.SITEID,
            'SUBJID': enrollment_case.USUBJID.SUBJID,
            'INITIAL': enrollment_case.USUBJID.INITIAL,
            'COMPLETEDBY': request.user.username,
            'COMPLETEDDATE': date.today(),
        }
        if discharge_case:
            form = DischargeCaseForm(instance=discharge_case)
            if is_readonly:
                icd_formset = DischargeICDFormSet(prefix='icd_set', instance=discharge_case)
            else:
                icd_formset = DischargeICDFormSet(prefix='icd_set', instance=discharge_case)
        else:
            form = DischargeCaseForm(initial=initial_data)
            icd_formset = DischargeICDFormSet(
                prefix='icd_set',
                queryset=DischargeICD.objects.none(),
                initial=[{'EPISODE': 1}]
            )

        if is_readonly:
            for field in form.fields.values():
                field.widget.attrs['readonly'] = True
                field.widget.attrs['disabled'] = True
            for form_instance in icd_formset.forms:
                for field in form_instance.fields.values():
                    field.widget.attrs['readonly'] = True
                    field.widget.attrs['disabled'] = True

    return render(request, 'studies/study_43en/CRF/discharge_form.html', {
        'enrollment_case': enrollment_case,
        'discharge_case': discharge_case,
        'form': form,
        'icd_formset': icd_formset,
        'is_readonly': is_readonly,
        'has_discharge': has_discharge,
        'today': date.today(),
    })

@login_required
def discharge_form_view(request, usubjid):
    """View readonly cho discharge form"""
    return discharge_form(request, usubjid)
