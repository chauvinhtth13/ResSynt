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
    ScreeningCase, EnrollmentCase, FollowUpCase, FollowUpCase90,

)


from backends.studies.study_43en.forms_patient import (
    FollowUpCaseForm,
    FollowUpAntibioticFormSet, RehospitalizationFormSet,
    Rehospitalization90FormSet,FollowUpCase90Form,FollowUpAntibiotic90FormSet,


)



# Import utils từ study app
from backends.studies.study_43en.utils.audit_log_utils import (
    safe_json_loads
)
from backends.studies.study_43en.utils.audit_log_cross_db import audit_log_decorator

logger = logging.getLogger(__name__)






@login_required
@audit_log_decorator(model_name='FOLLOWUPCASE')
def followup_case_create(request, usubjid):
    """Tạo mới thông tin FollowUpCase cho bệnh nhân"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    # Kiểm tra xem đã có FollowUpCase chưa
    try:
        followup_case = FollowUpCase.objects.get(USUBJID=enrollment_case)
        messages.warning(request, f'Bệnh nhân {usubjid} đã có thông tin theo dõi 28 ngày. Chuyển tới trang cập nhật.')
        return redirect('study_43en:followup_case_update', usubjid=usubjid)
    except FollowUpCase.DoesNotExist:
        pass

    if request.method == 'POST':
        form = FollowUpCaseForm(request.POST)
        rehospitalization_formset = RehospitalizationFormSet(request.POST, prefix='rehospitalization_set')
        antibiotic_formset = FollowUpAntibioticFormSet(request.POST, prefix='antibiotic_set')

        formsets_valid = (
            rehospitalization_formset.is_valid() and
            antibiotic_formset.is_valid()
        )

        if form.is_valid() and formsets_valid:
            followup_case = form.save(commit=False)
            followup_case.USUBJID = enrollment_case
            followup_case.save()

            # Gán đúng FK cho các instance con
            rehospitalization_instances = rehospitalization_formset.save(commit=False)
            for i, instance in enumerate(rehospitalization_instances, 1):
                instance.USUBJID = followup_case
                instance.EPISODE = i
                instance.save()
            antibiotic_instances = antibiotic_formset.save(commit=False)
            for i, instance in enumerate(antibiotic_instances, 1):
                instance.USUBJID = followup_case
                instance.EPISODE = i
                instance.save()
            rehospitalization_formset.save()
            antibiotic_formset.save()

            messages.success(request, f'Đã tạo thông tin theo dõi 28 ngày cho bệnh nhân {usubjid} thành công.')
            return redirect('study_43en:patient_detail', usubjid=usubjid)
    else:
        initial_data = {
            'COMPLETEDBY': enrollment_case.COMPLETEDBY if enrollment_case.COMPLETEDBY else request.user.username,
            'COMPLETEDDATE': date.today(),
        }
        form = FollowUpCaseForm(initial=initial_data)
        rehospitalization_formset = RehospitalizationFormSet(prefix='rehospitalization_set')
        antibiotic_formset = FollowUpAntibioticFormSet(prefix='antibiotic_set')

    return render(request, 'studies/study_43en/CRF/followup_case_form.html', {
        'form': form,
        'rehospitalization_formset': rehospitalization_formset,
        'antibiotic_formset': antibiotic_formset,
        'followup_case': {'USUBJID_id': enrollment_case.USUBJID},
        'enrollment_case': enrollment_case,
        'is_create': True,
        'today': date.today(),
    })

@login_required
@audit_log_decorator(model_name='FOLLOWUPCASE')
def followup_case_update(request, usubjid):
    """Cập nhật thông tin FollowUpCase cho bệnh nhân"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    followup_case = get_object_or_404(FollowUpCase, USUBJID=enrollment_case)

    print(f"POST Data: {request.POST}")

    # Lấy old_data từ form nếu có
    old_data = safe_json_loads(request.POST.get('oldDataJson', '{}'))
    new_data = safe_json_loads(request.POST.get('newDataJson', '{}'))
    reasons_json = safe_json_loads(request.POST.get('reasonsJson', '{}'))
    change_reason = request.POST.get('change_reason', '')
    
    # Debug audit data
    print("DEBUG - old_data:", old_data)
    print("DEBUG - new_data:", new_data)
    print("DEBUG - reasons_json:", reasons_json)
    print("DEBUG - change_reason:", change_reason)
    
    # Đặt audit_data vào request để audit_log_decorator có thể sử dụng
    request.audit_data = {
        'old_data': old_data,
        'new_data': new_data,
        'reasons_json': reasons_json,
        'reason': change_reason
    }

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
            followup_case = form.save()
            rehospitalization_formset.save()
            antibiotic_formset.save()
            
            # Kiểm tra xem đây có phải là AJAX request hay không
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Đã cập nhật thông tin theo dõi 28 ngày cho bệnh nhân {usubjid} thành công!',
                    'redirect_url': reverse('study_43en:patient_detail', kwargs={'usubjid': usubjid})
                })
            else:
                messages.success(request, f'Đã cập nhật thông tin theo dõi 28 ngày cho bệnh nhân {usubjid} thành công.')
                return redirect('study_43en:patient_detail', usubjid=usubjid)
        else:
            # Nếu form không valid, trả về lỗi qua AJAX nếu là AJAX request
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                errors = {}
                if form.errors:
                    errors.update(form.errors)
                if rehospitalization_formset.errors:
                    errors['rehospitalization'] = rehospitalization_formset.errors
                if antibiotic_formset.errors:
                    errors['antibiotic'] = antibiotic_formset.errors
                
                return JsonResponse({
                    'success': False,
                    'message': 'Có lỗi trong form, vui lòng kiểm tra lại.',
                    'errors': errors
                }, status=400)
            else:
                messages.error(request, 'Có lỗi trong form, vui lòng kiểm tra lại.')
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

    return render(request, 'studies/study_43en/CRF/followup_case_form.html', {
        'form': form,
        'rehospitalization_formset': rehospitalization_formset,
        'antibiotic_formset': antibiotic_formset,
        'followup_case': followup_case,
        'enrollment_case': enrollment_case,
        'is_create': False,
        'today': date.today(),
    })

@login_required
@audit_log_decorator(model_name='FOLLOWUPCASE')
def followup_case_view(request, usubjid):
    """Xem thông tin FollowUpCase ở chế độ chỉ đọc"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    try:
        followup_case = FollowUpCase.objects.get(USUBJID=enrollment_case)
    except FollowUpCase.DoesNotExist:
        messages.error(request, f'Bệnh nhân {usubjid} chưa có thông tin theo dõi 28 ngày.')
        return redirect('study_43en:patient_detail', usubjid=usubjid)

    form = FollowUpCaseForm(instance=followup_case)
    rehospitalization_formset = RehospitalizationFormSet(
        prefix='rehospitalization_set',
        instance=followup_case
    )
    antibiotic_formset = FollowUpAntibioticFormSet(
        prefix='antibiotic_set',
        instance=followup_case
    )

    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True

    for formset in [rehospitalization_formset, antibiotic_formset]:
        for form_instance in formset.forms:
            for field in form_instance.fields.values():
                field.widget.attrs['readonly'] = True
                field.widget.attrs['disabled'] = True

    return render(request, 'studies/study_43en/CRF/followup_case_form.html', {
        'form': form,
        'rehospitalization_formset': rehospitalization_formset,
        'antibiotic_formset': antibiotic_formset,
        'enrollment_case': enrollment_case,
        'followup_case': followup_case,
        'is_view_only': True,
        'today': date.today(),
    })

@login_required
@audit_log_decorator(model_name='FOLLOWUPCASE')
def followup_form(request, usubjid):
    """View cho follow-up form - hỗ trợ cả theo dõi 28 ngày và 90 ngày"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)

    # Lấy audit data nếu có
    old_data = safe_json_loads(request.POST.get('oldDataJson', '{}'))
    new_data = safe_json_loads(request.POST.get('newDataJson', '{}'))
    reasons_json = safe_json_loads(request.POST.get('reasonsJson', '{}'))
    change_reason = request.POST.get('change_reason', '')
    
    # Debug audit data
    print("DEBUG - followup_form - old_data:", old_data)
    print("DEBUG - followup_form - new_data:", new_data)
    print("DEBUG - followup_form - reasons_json:", reasons_json)
    print("DEBUG - followup_form - change_reason:", change_reason)
    
    # Đặt audit_data vào request để audit_log_decorator có thể sử dụng
    request.audit_data = {
        'old_data': old_data,
        'new_data': new_data,
        'reasons_json': reasons_json,
        'reason': change_reason
    }

    # Khởi tạo các biến 90 ngày để tránh lỗi UnboundLocalError
    form90 = None
    rehospitalization90_formset = None
    antibiotic90_formset = None

    # Kiểm tra dữ liệu follow-up 28 ngày
    try:
        followup_case = FollowUpCase.objects.get(USUBJID=enrollment_case)
        has_followup28 = True
    except FollowUpCase.DoesNotExist:
        followup_case = None
        has_followup28 = False

    # Kiểm tra dữ liệu follow-up 90 ngày
    try:
        followup_case90 = FollowUpCase90.objects.get(USUBJID=enrollment_case)
        has_followup90 = True
    except FollowUpCase90.DoesNotExist:
        followup_case90 = None
        has_followup90 = False

    is_readonly = request.path.endswith('/view/')

    if request.method == 'POST' and not is_readonly:
        # 28 ngày
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
            rehospitalization_formset = RehospitalizationFormSet(
                request.POST,
                prefix='rehospitalization_set'
            )
            antibiotic_formset = FollowUpAntibioticFormSet(
                request.POST,
                prefix='antibiotic_set'
            )

        form_valid = form.is_valid()
        rehosp_valid = rehospitalization_formset.is_valid()
        antibio_valid = antibiotic_formset.is_valid()

        if form_valid and rehosp_valid and antibio_valid:
            if followup_case:
                saved_instance = form.save()
            else:
                saved_instance = form.save(commit=False)
                saved_instance.USUBJID = enrollment_case
                saved_instance.save()

            # Lưu rehospitalization
            episode_counter = 1
            for form_instance in rehospitalization_formset.forms:
                if hasattr(form_instance, 'cleaned_data') and form_instance.cleaned_data and not form_instance.cleaned_data.get('DELETE', False):
                    obj = form_instance.save(commit=False)
                    if obj.REHOSPDATE or obj.REHOSPREASONFOR or obj.REHOSPLOCATION:
                        obj.USUBJID = saved_instance
                        obj.EPISODE = episode_counter
                        obj.save()
                        episode_counter += 1
            for obj in getattr(rehospitalization_formset, 'deleted_objects', []):
                obj.delete()

            # Lưu antibiotic
            episode_counter = 1
            for form_instance in antibiotic_formset.forms:
                if hasattr(form_instance, 'cleaned_data') and form_instance.cleaned_data and not form_instance.cleaned_data.get('DELETE', False):
                    obj = form_instance.save(commit=False)
                    if obj.ANTIBIONAME or obj.ANTIBIOREASONFOR or obj.ANTIBIODUR:
                        obj.USUBJID = saved_instance
                        obj.EPISODE = episode_counter
                        obj.save()
                        episode_counter += 1
            for obj in getattr(antibiotic_formset, 'deleted_objects', []):
                obj.delete()

            # Kiểm tra nếu là AJAX request
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Đã lưu thông tin follow-up cho {usubjid}',
                    'redirect_url': reverse('study_43en:patient_detail', kwargs={'usubjid': usubjid})
                })
            else:
                messages.success(request, f'Đã lưu thông tin follow-up cho {usubjid}')
                return redirect('study_43en:patient_detail', usubjid=usubjid)
        else:
            # Xử lý lỗi form
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                errors = {}
                if not form_valid:
                    errors.update(form.errors)
                if not rehosp_valid:
                    errors['rehospitalization'] = rehospitalization_formset.errors
                if not antibio_valid:
                    errors['antibiotic'] = antibiotic_formset.errors
                
                return JsonResponse({
                    'success': False,
                    'message': 'Có lỗi trong form, vui lòng kiểm tra lại.',
                    'errors': errors
                }, status=400)
            else:
                messages.error(request, 'Có lỗi trong form')
    else:
        # GET request
        if followup_case:
            form = FollowUpCaseForm(instance=followup_case)
            if is_readonly:
                rehospitalization_formset = RehospitalizationFormSet(
                    prefix='rehospitalization_set',
                    instance=followup_case
                )
                antibiotic_formset = FollowUpAntibioticFormSet(
                    prefix='antibiotic_set',
                    instance=followup_case
                )
            else:
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
            rehospitalization_formset = RehospitalizationFormSet(
                prefix='rehospitalization_set'
            )
            antibiotic_formset = FollowUpAntibioticFormSet(
                prefix='antibiotic_set'
            )

        # 90 ngày
        if followup_case90:
            form90 = FollowUpCase90Form(instance=followup_case90)
            if is_readonly:
                rehospitalization90_formset = Rehospitalization90FormSet(
                    prefix='rehospitalization90_set',
                    instance=followup_case90
                )
                antibiotic90_formset = FollowUpAntibiotic90FormSet(
                    prefix='antibiotic90_set',
                    instance=followup_case90
                )
            else:
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
            rehospitalization90_formset = Rehospitalization90FormSet(
                prefix='rehospitalization90_set'
            )
            antibiotic90_formset = FollowUpAntibiotic90FormSet(
                prefix='antibiotic90_set'
            )

        # Nếu là chế độ chỉ đọc, đặt readonly cho tất cả các trường
        if is_readonly:
            for field in form.fields.values():
                field.widget.attrs['readonly'] = True
                field.widget.attrs['disabled'] = True
            for formset in [rehospitalization_formset, antibiotic_formset]:
                for form_instance in formset.forms:
                    for field in form_instance.fields.values():
                        field.widget.attrs['readonly'] = True
                        field.widget.attrs['disabled'] = True
            for field in form90.fields.values():
                field.widget.attrs['readonly'] = True
                field.widget.attrs['disabled'] = True
            for formset in [rehospitalization90_formset, antibiotic90_formset]:
                for form_instance in formset.forms:
                    for field in form_instance.fields.values():
                        field.widget.attrs['readonly'] = True
                        field.widget.attrs['disabled'] = True

    return render(request, 'studies/study_43en/CRF/followup_form.html', {
        'enrollment_case': enrollment_case,
        'followup_case': followup_case,
        'form': form,
        'rehospitalization_formset': rehospitalization_formset,
        'antibiotic_formset': antibiotic_formset,
        'is_readonly': is_readonly,
        'has_followup28': has_followup28,
        'has_followup90': has_followup90,
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
@audit_log_decorator(model_name='FOLLOWUPCASE90')
def followup_case90_create(request, usubjid):
    """Tạo mới thông tin FollowUpCase90 cho bệnh nhân"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    
    # Kiểm tra xem đã có FollowUpCase90 chưa
    try:
        followup_case = FollowUpCase90.objects.get(USUBJID=enrollment_case)
        messages.warning(request, f'Bệnh nhân {usubjid} đã có thông tin theo dõi 90 ngày. Chuyển tới trang cập nhật.')
        return redirect('study_43en:followup_case90_update', usubjid=usubjid)
    except FollowUpCase90.DoesNotExist:
        pass

    # Chuẩn bị audit data trước khi xử lý POST
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
        form = FollowUpCase90Form(request.POST)
        rehospitalization_formset = Rehospitalization90FormSet(request.POST, prefix='rehospitalization90_set')
        antibiotic_formset = FollowUpAntibiotic90FormSet(request.POST, prefix='antibiotic90_set')

        formsets_valid = rehospitalization_formset.is_valid() and antibiotic_formset.is_valid()

        # Validation bổ sung cho REHOSPCOUNT và ANTIBIOCOUNT
        if form.is_valid() and formsets_valid:
            cleaned_data = form.cleaned_data
            if cleaned_data.get('REHOSP') == 'Yes' and not cleaned_data.get('REHOSPCOUNT'):
                form.add_error('REHOSPCOUNT', 'Vui lòng nhập số lần tái nhập viện.')
                formsets_valid = False
            if cleaned_data.get('USEDANTIBIO') == 'Yes' and not cleaned_data.get('ANTIBIOCOUNT'):
                form.add_error('ANTIBIOCOUNT', 'Vui lòng nhập số đợt kháng sinh.')
                formsets_valid = False

        if form.is_valid() and formsets_valid:
            followup_case = form.save(commit=False)
            followup_case.USUBJID = enrollment_case
            followup_case.save()

            # Lưu formset
            rehospitalization_instances = rehospitalization_formset.save(commit=False)
            for i, instance in enumerate(rehospitalization_instances, 1):
                instance.USUBJID = followup_case
                instance.EPISODE = i
                instance.save()
            antibiotic_instances = antibiotic_formset.save(commit=False)
            for i, instance in enumerate(antibiotic_instances, 1):
                instance.USUBJID = followup_case
                instance.EPISODE = i
                instance.save()
            rehospitalization_formset.save()
            antibiotic_formset.save()

            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Đã tạo thông tin theo dõi 90 ngày cho bệnh nhân {usubjid} thành công!',
                    'redirect_url': reverse('study_43en:patient_detail', kwargs={'usubjid': usubjid})
                })
            else:
                messages.success(request, f'Đã tạo thông tin theo dõi 90 ngày cho bệnh nhân {usubjid} thành công.')
                return redirect('study_43en:patient_detail', usubjid=usubjid)
        else:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                errors = {}
                if form.errors:
                    errors.update(form.errors)
                if rehospitalization_formset.errors:
                    errors['rehospitalization'] = rehospitalization_formset.errors
                if antibiotic_formset.errors:
                    errors['antibiotic'] = antibiotic_formset.errors
                return JsonResponse({
                    'success': False,
                    'message': 'Có lỗi trong form, vui lòng kiểm tra lại.',
                    'errors': errors
                }, status=400)
            else:
                messages.error(request, 'Có lỗi trong form, vui lòng kiểm tra lại.')
    else:
        initial_data = {
            'COMPLETEDBY': enrollment_case.COMPLETEDBY if enrollment_case.COMPLETEDBY else request.user.username,
            'COMPLETEDDATE': date.today(),
        }
        form = FollowUpCase90Form(initial=initial_data)
        rehospitalization_formset = Rehospitalization90FormSet(prefix='rehospitalization90_set')
        antibiotic_formset = FollowUpAntibiotic90FormSet(prefix='antibiotic90_set')

    return render(request, 'studies/study_43en/CRF/followup_form90.html', {
        'form': form,
        'rehospitalization_formset': rehospitalization_formset,
        'antibiotic_formset': antibiotic_formset,
        'followup_case': {'USUBJID_id': enrollment_case.USUBJID},
        'enrollment_case': enrollment_case,
        'is_create': True,
        'today': date.today(),
    })

@login_required
@audit_log_decorator(model_name='FOLLOWUPCASE90')
def followup_case90_update(request, usubjid):
    """Cập nhật thông tin FollowUpCase90 cho bệnh nhân"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    followup_case = get_object_or_404(FollowUpCase90, USUBJID=enrollment_case)

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
        form = FollowUpCase90Form(request.POST, instance=followup_case)
        rehospitalization_formset = Rehospitalization90FormSet(
            request.POST, 
            instance=followup_case, 
            prefix='rehospitalization90_set'
        )
        antibiotic_formset = FollowUpAntibiotic90FormSet(
            request.POST, 
            instance=followup_case, 
            prefix='antibiotic90_set'
        )

        formsets_valid = rehospitalization_formset.is_valid() and antibiotic_formset.is_valid()

        # Validation bổ sung cho REHOSPCOUNT và ANTIBIOCOUNT
        if form.is_valid() and formsets_valid:
            cleaned_data = form.cleaned_data
            if cleaned_data.get('REHOSP') == 'Yes' and not cleaned_data.get('REHOSPCOUNT'):
                form.add_error('REHOSPCOUNT', 'Vui lòng nhập số lần tái nhập viện.')
                formsets_valid = False
            if cleaned_data.get('USEDANTIBIO') == 'Yes' and not cleaned_data.get('ANTIBIOCOUNT'):
                form.add_error('ANTIBIOCOUNT', 'Vui lòng nhập số đợt kháng sinh.')
                formsets_valid = False

        if form.is_valid() and formsets_valid:
            followup_case = form.save()
            rehospitalization_formset.save()
            antibiotic_formset.save()

            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Đã cập nhật thông tin theo dõi 90 ngày cho bệnh nhân {usubjid} thành công!',
                    'redirect_url': reverse('study_43en:patient_detail', kwargs={'usubjid': usubjid})
                })
            else:
                messages.success(request, f'Đã cập nhật thông tin theo dõi 90 ngày cho bệnh nhân {usubjid} thành công.')
                return redirect('study_43en:patient_detail', usubjid=usubjid)
        else:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                errors = {}
                if form.errors:
                    errors.update(form.errors)
                if rehospitalization_formset.errors:
                    errors['rehospitalization'] = rehospitalization_formset.errors
                if antibiotic_formset.errors:
                    errors['antibiotic'] = antibiotic_formset.errors
                return JsonResponse({
                    'success': False,
                    'message': 'Có lỗi trong form, vui lòng kiểm tra lại.',
                    'errors': errors
                }, status=400)
            else:
                messages.error(request, 'Có lỗi trong form, vui lòng kiểm tra lại.')
    else:
        form = FollowUpCase90Form(instance=followup_case)
        rehospitalization_formset = Rehospitalization90FormSet(
            instance=followup_case, 
            prefix='rehospitalization90_set'
        )
        antibiotic_formset = FollowUpAntibiotic90FormSet(
            instance=followup_case, 
            prefix='antibiotic90_set'
        )

    return render(request, 'studies/study_43en/CRF/followup_form90.html', {
        'form': form,
        'rehospitalization_formset': rehospitalization_formset,
        'antibiotic_formset': antibiotic_formset,
        'enrollment_case': enrollment_case,
        'followup_case': followup_case,
        'is_create': False,
        'today': date.today(),
    })



@login_required
@audit_log_decorator(model_name='FOLLOWUPCASE90')
def followup_case90_view(request, usubjid):
    """Xem thông tin FollowUpCase90 ở chế độ chỉ đọc"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    try:
        followup_case = FollowUpCase90.objects.get(USUBJID=enrollment_case)
    except FollowUpCase90.DoesNotExist:
        messages.error(request, f'Bệnh nhân {usubjid} chưa có thông tin theo dõi 90 ngày.')
        return redirect('study_43en:patient_detail', usubjid=usubjid)

    form = FollowUpCase90Form(instance=followup_case)
    rehospitalization_formset = Rehospitalization90FormSet(
        prefix='rehospitalization90_set',
        instance=followup_case
    )
    antibiotic_formset = FollowUpAntibiotic90FormSet(
        prefix='antibiotic90_set',
        instance=followup_case
    )

    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True

    for formset in [rehospitalization_formset, antibiotic_formset]:
        for form_instance in formset.forms:
            for field in form_instance.fields.values():
                field.widget.attrs['readonly'] = True
                field.widget.attrs['disabled'] = True

    return render(request, 'studies/study_43en/CRF/followup_form90.html', {
        'form': form,
        'rehospitalization_formset': rehospitalization_formset,
        'antibiotic_formset': antibiotic_formset,
        'enrollment_case': enrollment_case,
        'followup_case': followup_case,
        'is_view_only': True,
        'today': date.today(),
    })


@login_required
@audit_log_decorator(model_name='FOLLOWUPCASE90')
def followup_form90(request, usubjid):
    """View cho follow-up form 90 ngày - hỗ trợ cả 28 và 90 ngày"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)

    # Lấy audit data
    old_data = safe_json_loads(request.POST.get('oldDataJson', '{}'))
    new_data = safe_json_loads(request.POST.get('newDataJson', '{}'))
    reasons_json = safe_json_loads(request.POST.get('reasonsJson', '{}'))
    change_reason = request.POST.get('change_reason', '')
    
    print("DEBUG - followup_form90 - old_data:", old_data)
    print("DEBUG - followup_form90 - new_data:", new_data)
    print("DEBUG - followup_form90 - reasons_json:", reasons_json)
    print("DEBUG - followup_form90 - change_reason:", change_reason)
    
    request.audit_data = {
        'old_data': old_data,
        'new_data': new_data,
        'reasons_json': reasons_json,
        'reason': change_reason
    }

    # Kiểm tra dữ liệu follow-up 28 ngày
    try:
        followup_case = FollowUpCase.objects.get(USUBJID=enrollment_case)
        has_followup28 = True
    except FollowUpCase.DoesNotExist:
        followup_case = None
        has_followup28 = False

    # Kiểm tra dữ liệu follow-up 90 ngày
    try:
        followup_case90 = FollowUpCase90.objects.get(USUBJID=enrollment_case)
        has_followup90 = True
    except FollowUpCase90.DoesNotExist:
        followup_case90 = None
        has_followup90 = False

    is_readonly = request.path.endswith('/view/')

    if request.method == 'POST' and not is_readonly:
        # 28 ngày
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
            rehospitalization_formset = RehospitalizationFormSet(
                request.POST,
                prefix='rehospitalization_set'
            )
            antibiotic_formset = FollowUpAntibioticFormSet(
                request.POST,
                prefix='antibiotic_set'
            )

        # 90 ngày
        if followup_case90:
            form90 = FollowUpCase90Form(request.POST, instance=followup_case90)
            rehospitalization90_formset = Rehospitalization90FormSet(
                request.POST,
                prefix='rehospitalization90_set',
                instance=followup_case90
            )
            antibiotic90_formset = FollowUpAntibiotic90FormSet(
                request.POST,
                prefix='antibiotic90_set',
                instance=followup_case90
            )
        else:
            form90 = FollowUpCase90Form(request.POST)
            rehospitalization90_formset = Rehospitalization90FormSet(
                request.POST,
                prefix='rehospitalization90_set'
            )
            antibiotic90_formset = FollowUpAntibiotic90FormSet(
                request.POST,
                prefix='antibiotic90_set'
            )

        form_valid = form.is_valid() if form else True
        rehosp_valid = rehospitalization_formset.is_valid() if rehospitalization_formset else True
        antibio_valid = antibiotic_formset.is_valid() if antibiotic_formset else True
        form90_valid = form90.is_valid() if form90 else True
        rehosp90_valid = rehospitalization90_formset.is_valid() if rehospitalization90_formset else True
        antibio90_valid = antibiotic90_formset.is_valid() if antibiotic90_formset else True

        if form_valid and rehosp_valid and antibio_valid and form90_valid and rehosp90_valid and antibio90_valid:
            if form and form_valid:
                if followup_case:
                    saved_instance = form.save()
                else:
                    saved_instance = form.save(commit=False)
                    saved_instance.USUBJID = enrollment_case
                    saved_instance.save()

                episode_counter = 1
                for form_instance in rehospitalization_formset.forms:
                    if hasattr(form_instance, 'cleaned_data') and form_instance.cleaned_data and not form_instance.cleaned_data.get('DELETE', False):
                        obj = form_instance.save(commit=False)
                        if obj.REHOSPDATE or obj.REHOSPREASONFOR or obj.REHOSPLOCATION:
                            obj.USUBJID = saved_instance
                            obj.EPISODE = episode_counter
                            obj.save()
                            episode_counter += 1
                for obj in getattr(rehospitalization_formset, 'deleted_objects', []):
                    obj.delete()

                episode_counter = 1
                for form_instance in antibiotic_formset.forms:
                    if hasattr(form_instance, 'cleaned_data') and form_instance.cleaned_data and not form_instance.cleaned_data.get('DELETE', False):
                        obj = form_instance.save(commit=False)
                        if obj.ANTIBIONAME or obj.ANTIBIOREASONFOR or obj.ANTIBIODUR:
                            obj.USUBJID = saved_instance
                            obj.EPISODE = episode_counter
                            obj.save()
                            episode_counter += 1
                for obj in getattr(antibiotic_formset, 'deleted_objects', []):
                    obj.delete()

            if form90 and form90_valid:
                if followup_case90:
                    saved_instance90 = form90.save()
                else:
                    saved_instance90 = form90.save(commit=False)
                    saved_instance90.USUBJID = enrollment_case
                    saved_instance90.save()

                episode_counter = 1
                for form_instance in rehospitalization90_formset.forms:
                    if hasattr(form_instance, 'cleaned_data') and form_instance.cleaned_data and not form_instance.cleaned_data.get('DELETE', False):
                        obj = form_instance.save(commit=False)
                        if obj.REHOSPDATE or obj.REHOSPREASONFOR or obj.REHOSPLOCATION:
                            obj.USUBJID = saved_instance90
                            obj.EPISODE = episode_counter
                            obj.save()
                            episode_counter += 1
                for obj in getattr(rehospitalization90_formset, 'deleted_objects', []):
                    obj.delete()

                episode_counter = 1
                for form_instance in antibiotic90_formset.forms:
                    if hasattr(form_instance, 'cleaned_data') and form_instance.cleaned_data and not form_instance.cleaned_data.get('DELETE', False):
                        obj = form_instance.save(commit=False)
                        if obj.ANTIBIONAME or obj.ANTIBIOREASONFOR or obj.ANTIBIODUR:
                            obj.USUBJID = saved_instance90
                            obj.EPISODE = episode_counter
                            obj.save()
                            episode_counter += 1
                for obj in getattr(antibiotic90_formset, 'deleted_objects', []):
                    obj.delete()

            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Đã lưu thông tin follow-up cho {usubjid}',
                    'redirect_url': reverse('study_43en:patient_detail', kwargs={'usubjid': usubjid})
                })
            else:
                messages.success(request, f'Đã lưu thông tin follow-up cho {usubjid}')
                return redirect('study_43en:patient_detail', usubjid=usubjid)
        else:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                errors = {}
                if form and not form_valid:
                    errors.update(form.errors)
                if rehospitalization_formset and not rehosp_valid:
                    errors['rehospitalization'] = rehospitalization_formset.errors
                if antibiotic_formset and not antibio_valid:
                    errors['antibiotic'] = antibiotic_formset.errors
                if form90 and not form90_valid:
                    errors.update(form90.errors)
                if rehospitalization90_formset and not rehosp90_valid:
                    errors['rehospitalization90'] = rehospitalization90_formset.errors
                if antibiotic90_formset and not antibio90_valid:
                    errors['antibiotic90'] = antibiotic90_formset.errors
                return JsonResponse({
                    'success': False,
                    'message': 'Có lỗi trong form, vui lòng kiểm tra lại.',
                    'errors': errors
                }, status=400)
            else:
                messages.error(request, 'Có lỗi trong form')
    else:
        initial_data = {
            'COMPLETEDBY': request.user.username,
            'COMPLETEDDATE': date.today(),
        }
        if followup_case:
            form = FollowUpCaseForm(instance=followup_case)
            if is_readonly:
                rehospitalization_formset = RehospitalizationFormSet(
                    prefix='rehospitalization_set',
                    instance=followup_case
                )
                antibiotic_formset = FollowUpAntibioticFormSet(
                    prefix='antibiotic_set',
                    instance=followup_case
                )
            else:
                rehospitalization_formset = RehospitalizationFormSet(
                    prefix='rehospitalization_set',
                    instance=followup_case
                )
                antibiotic_formset = FollowUpAntibioticFormSet(
                    prefix='antibiotic_set',
                    instance=followup_case
                )
        else:
            form = FollowUpCaseForm(initial=initial_data)
            rehospitalization_formset = RehospitalizationFormSet(
                prefix='rehospitalization_set'
            )
            antibiotic_formset = FollowUpAntibioticFormSet(
                prefix='antibiotic_set'
            )

        if followup_case90:
            form90 = FollowUpCase90Form(instance=followup_case90)
            if is_readonly:
                rehospitalization90_formset = Rehospitalization90FormSet(
                    prefix='rehospitalization90_set',
                    instance=followup_case90
                )
                antibiotic90_formset = FollowUpAntibiotic90FormSet(
                    prefix='antibiotic90_set',
                    instance=followup_case90
                )
            else:
                rehospitalization90_formset = Rehospitalization90FormSet(
                    prefix='rehospitalization90_set',
                    instance=followup_case90
                )
                antibiotic90_formset = FollowUpAntibiotic90FormSet(
                    prefix='antibiotic90_set',
                    instance=followup_case90
                )
        else:
            form90 = FollowUpCase90Form(initial=initial_data)
            rehospitalization90_formset = Rehospitalization90FormSet(
                prefix='rehospitalization90_set'
            )
            antibiotic90_formset = FollowUpAntibiotic90FormSet(
                prefix='antibiotic90_set'
            )

        if is_readonly:
            for field in form.fields.values():
                field.widget.attrs['readonly'] = True
                field.widget.attrs['disabled'] = True
            for formset in [rehospitalization_formset, antibiotic_formset]:
                for form_instance in formset.forms:
                    for field in form_instance.fields.values():
                        field.widget.attrs['readonly'] = True
                        field.widget.attrs['disabled'] = True
            for field in form90.fields.values():
                field.widget.attrs['readonly'] = True
                field.widget.attrs['disabled'] = True
            for formset in [rehospitalization90_formset, antibiotic90_formset]:
                for form_instance in formset.forms:
                    for field in form_instance.fields.values():
                        field.widget.attrs['readonly'] = True
                        field.widget.attrs['disabled'] = True

    return render(request, 'studies/study_43en/CRF/followup_form90.html', {  # Sử dụng template chung
        'enrollment_case': enrollment_case,
        'followup_case': followup_case,
        'form': form,
        'rehospitalization_formset': rehospitalization_formset,
        'antibiotic_formset': antibiotic_formset,
        'is_readonly': is_readonly,
        'has_followup28': has_followup28,
        'has_followup90': has_followup90,
        'followup_case90': followup_case90,
        'form90': form90,
        'rehospitalization90_formset': rehospitalization90_formset,
        'antibiotic90_formset': antibiotic90_formset,
    })


@login_required
def followup_form90_view(request, usubjid):
    """View readonly cho follow-up 90 ngày - GIỐNG HỆT followup_form_view"""
    return followup_form90(request, usubjid)