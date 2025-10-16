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
    ScreeningCase, EnrollmentCase, EndCaseCRF,

)
from backends.studies.study_43en.models.contact import (
    ScreeningContact, EnrollmentContact, 
    ContactEndCaseCRF
)


from backends.studies.study_43en.forms_patient import (
    EndCaseCRFForm,


)


from backends.studies.study_43en.forms_contact import (
    ContactEndCaseCRFForm
)

# Import utils từ study app
from backends.studies.study_43en.utils.audit_log_utils import (
    safe_json_loads
)
from backends.studies.study_43en.utils.audit_log_cross_db import audit_log_decorator

logger = logging.getLogger(__name__)







@login_required
@audit_log_decorator(model_name='ENDCASECRF')
def endcasecrf_create(request, usubjid):
    """Tạo mới phiếu kết thúc nghiên cứu cho bệnh nhân"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)

    # Kiểm tra xem đã có phiếu kết thúc chưa
    if EndCaseCRF.objects.filter(USUBJID=enrollment_case).exists():
        messages.warning(request, f'Bệnh nhân {usubjid} đã có phiếu kết thúc. Chuyển tới trang cập nhật.')
        return redirect('study_43en:endcasecrf_update', usubjid=usubjid)

    # Chuẩn bị audit data
    old_data = safe_json_loads(request.POST.get('oldDataJson', '{}'))
    new_data = safe_json_loads(request.POST.get('newDataJson', '{}'))
    reasons_json = safe_json_loads(request.POST.get('reasonsJson', '{}'))
    change_reason = request.POST.get('change_reason', '')
    
    print("DEBUG - endcasecrf_create - old_data:", old_data)
    print("DEBUG - endcasecrf_create - new_data:", new_data)
    print("DEBUG - endcasecrf_create - reasons_json:", reasons_json)
    print("DEBUG - endcasecrf_create - change_reason:", change_reason)
    
    request.audit_data = {
        'old_data': old_data,
        'new_data': new_data,
        'reasons_json': reasons_json,
        'reason': change_reason
    }

    if request.method == 'POST':
        form = EndCaseCRFForm(request.POST)
        if form.is_valid():
            endcase = form.save(commit=False)
            endcase.USUBJID = enrollment_case
            endcase.save()
            
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Đã tạo phiếu kết thúc nghiên cứu cho bệnh nhân {usubjid}.',
                    'redirect_url': reverse('study_43en:patient_detail', kwargs={'usubjid': usubjid})
                })
            else:
                messages.success(request, f'Đã tạo phiếu kết thúc nghiên cứu cho bệnh nhân {usubjid}.')
                return redirect('study_43en:patient_detail', usubjid=usubjid)
        else:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                errors = form.errors
                print("DEBUG - Form errors:", errors)
                return JsonResponse({
                    'success': False,
                    'message': 'Có lỗi khi lưu phiếu kết thúc. Vui lòng kiểm tra lại thông tin.',
                    'errors': errors
                }, status=400)
            else:
                messages.error(request, 'Có lỗi khi lưu phiếu kết thúc. Vui lòng kiểm tra lại thông tin.')
    else:
        initial_data = {
            'ENDDATE': date.today(),
            'ENDFORMDATE': date.today(),
            'WITHDRAWREASON': 'na',
            'INCOMPLETE': 'na',
            'LOSTTOFOLLOWUP': 'na',
        }
        form = EndCaseCRFForm(initial=initial_data)

    return render(request, 'studies/study_43en/CRF/endcasecrf_form.html', {
        'form': form,
        'enrollment_case': enrollment_case,
        'is_create': True,
        'today': date.today(),
    })

@login_required
@audit_log_decorator(model_name='ENDCASECRF')
def endcasecrf_update(request, usubjid):
    """Cập nhật phiếu kết thúc nghiên cứu cho bệnh nhân"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    endcase = get_object_or_404(EndCaseCRF, USUBJID=enrollment_case)

    # Chuẩn bị audit data
    old_data = safe_json_loads(request.POST.get('oldDataJson', '{}'))
    new_data = safe_json_loads(request.POST.get('newDataJson', '{}'))
    reasons_json = safe_json_loads(request.POST.get('reasonsJson', '{}'))
    change_reason = request.POST.get('change_reason', '')
    
    print("DEBUG - endcasecrf_update - old_data:", old_data)
    print("DEBUG - endcasecrf_update - new_data:", new_data)
    print("DEBUG - endcasecrf_update - reasons_json:", reasons_json)
    print("DEBUG - endcasecrf_update - change_reason:", change_reason)
    
    request.audit_data = {
        'old_data': old_data,
        'new_data': new_data,
        'reasons_json': reasons_json,
        'reason': change_reason
    }

    if request.method == 'POST':
        form = EndCaseCRFForm(request.POST, instance=endcase)
        if form.is_valid():
            endcase = form.save()
            
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Đã cập nhật phiếu kết thúc nghiên cứu cho bệnh nhân {usubjid}.',
                    'redirect_url': reverse('study_43en:patient_detail', kwargs={'usubjid': usubjid})
                })
            else:
                messages.success(request, f'Đã cập nhật phiếu kết thúc nghiên cứu cho bệnh nhân {usubjid}.')
                return redirect('study_43en:patient_detail', usubjid=usubjid)
        else:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                errors = form.errors
                print("DEBUG - Form errors:", errors)
                return JsonResponse({
                    'success': False,
                    'message': 'Có lỗi khi cập nhật phiếu kết thúc. Vui lòng kiểm tra lại thông tin.',
                    'errors': errors
                }, status=400)
            else:
                messages.error(request, 'Có lỗi khi cập nhật phiếu kết thúc. Vui lòng kiểm tra lại thông tin.')
    else:
        form = EndCaseCRFForm(instance=endcase)

    field_labels = {}
    for field in EndCaseCRF._meta.get_fields():
        if hasattr(field, 'verbose_name'):
            field_labels[field.name] = str(field.verbose_name)

    return render(request, 'studies/study_43en/CRF/endcasecrf_form.html', {
        'form': form,
        'enrollment_case': enrollment_case,
        'is_create': False,
        'today': date.today(),
        'field_labels': field_labels,
    })

@login_required
@audit_log_decorator(model_name='ENDCASECRF')
def endcasecrf_view(request, usubjid):
    """Xem phiếu kết thúc nghiên cứu ở chế độ chỉ đọc"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    endcase = get_object_or_404(EndCaseCRF, USUBJID=enrollment_case)
    
    form = EndCaseCRFForm(instance=endcase)
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True

    return render(request, 'studies/study_43en/CRF/endcasecrf_form.html', {
        'form': form,
        'enrollment_case': enrollment_case,
        'is_view_only': True,
        'today': date.today(),
    })

@login_required
@audit_log_decorator(model_name='CONTACTENDCASECRF')
def contactendcasecrf_create(request, usubjid):
    """Tạo mới phiếu kết thúc nghiên cứu cho người tiếp xúc"""
    screening_contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    enrollment_contact = get_object_or_404(EnrollmentContact, USUBJID=screening_contact)

    # Kiểm tra xem đã có phiếu kết thúc chưa
    if ContactEndCaseCRF.objects.filter(USUBJID=enrollment_contact).exists():
        messages.warning(request, f'Người tiếp xúc {usubjid} đã có phiếu kết thúc. Chuyển tới trang cập nhật.')
        return redirect('study_43en:contactendcasecrf_update', usubjid=usubjid)

    # Chuẩn bị audit data
    old_data = safe_json_loads(request.POST.get('oldDataJson', '{}'))
    new_data = safe_json_loads(request.POST.get('newDataJson', '{}'))
    reasons_json = safe_json_loads(request.POST.get('reasonsJson', '{}'))
    change_reason = request.POST.get('change_reason', '')
    
    print("DEBUG - contactendcasecrf_create - old_data:", old_data)
    print("DEBUG - contactendcasecrf_create - new_data:", new_data)
    print("DEBUG - contactendcasecrf_create - reasons_json:", reasons_json)
    print("DEBUG - contactendcasecrf_create - change_reason:", change_reason)
    
    request.audit_data = {
        'old_data': old_data,
        'new_data': new_data,
        'reasons_json': reasons_json,
        'reason': change_reason
    }

    if request.method == 'POST':
        form = ContactEndCaseCRFForm(request.POST)
        if form.is_valid():
            endcase = form.save(commit=False)
            endcase.USUBJID = enrollment_contact
            endcase.save()
            
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Đã tạo phiếu kết thúc nghiên cứu cho người tiếp xúc {usubjid}.',
                    'redirect_url': reverse('study_43en:contact_detail', kwargs={'usubjid': usubjid})
                })
            else:
                messages.success(request, f'Đã tạo phiếu kết thúc nghiên cứu cho người tiếp xúc {usubjid}.')
                return redirect('study_43en:contact_detail', usubjid=usubjid)
        else:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                errors = form.errors
                print("DEBUG - Form errors:", errors)
                return JsonResponse({
                    'success': False,
                    'message': 'Có lỗi khi lưu phiếu kết thúc. Vui lòng kiểm tra lại thông tin.',
                    'errors': errors
                }, status=400)
            else:
                messages.error(request, 'Có lỗi khi lưu phiếu kết thúc. Vui lòng kiểm tra lại thông tin.')
    else:
        initial_data = {
            'ENDDATE': date.today(),
            'ENDFORMDATE': date.today(),
            'WITHDRAWREASON': 'na',
            'INCOMPLETE': 'na',
            'LOSTTOFOLLOWUP': 'na',
        }
        form = ContactEndCaseCRFForm(initial=initial_data)

    return render(request, 'studies/study_43en/CRF/contactendcasecrf_form.html', {
        'form': form,
        'enrollment_contact': enrollment_contact,
        'is_create': True,
        'today': date.today(),
    })

@login_required
@audit_log_decorator(model_name='CONTACTENDCASECRF')
def contactendcasecrf_create(request, usubjid):
    """Tạo mới phiếu kết thúc nghiên cứu cho người tiếp xúc"""
    screening_contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    enrollment_contact = get_object_or_404(EnrollmentContact, USUBJID=screening_contact)

    # Kiểm tra xem đã có phiếu kết thúc chưa
    if ContactEndCaseCRF.objects.filter(USUBJID=enrollment_contact).exists():
        messages.warning(request, f'Người tiếp xúc {usubjid} đã có phiếu kết thúc. Chuyển tới trang cập nhật.')
        return redirect('study_43en:contactendcasecrf_update', usubjid=usubjid)

    # Chuẩn bị audit data
    old_data = safe_json_loads(request.POST.get('oldDataJson', '{}'))
    new_data = safe_json_loads(request.POST.get('newDataJson', '{}'))
    reasons_json = safe_json_loads(request.POST.get('reasonsJson', '{}'))
    change_reason = request.POST.get('change_reason', '')
    
    print("DEBUG - contactendcasecrf_create - old_data:", old_data)
    print("DEBUG - contactendcasecrf_create - new_data:", new_data)
    print("DEBUG - contactendcasecrf_create - reasons_json:", reasons_json)
    print("DEBUG - contactendcasecrf_create - change_reason:", change_reason)
    
    request.audit_data = {
        'old_data': old_data,
        'new_data': new_data,
        'reasons_json': reasons_json,
        'reason': change_reason
    }

    if request.method == 'POST':
        form = ContactEndCaseCRFForm(request.POST)
        if form.is_valid():
            endcase = form.save(commit=False)
            endcase.USUBJID = enrollment_contact
            endcase.save()
            
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Đã tạo phiếu kết thúc nghiên cứu cho người tiếp xúc {usubjid}.',
                    'redirect_url': reverse('study_43en:contact_detail', kwargs={'usubjid': usubjid})
                })
            else:
                messages.success(request, f'Đã tạo phiếu kết thúc nghiên cứu cho người tiếp xúc {usubjid}.')
                return redirect('study_43en:contact_detail', usubjid=usubjid)
        else:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                errors = form.errors
                print("DEBUG - Form errors:", errors)
                return JsonResponse({
                    'success': False,
                    'message': 'Có lỗi khi lưu phiếu kết thúc. Vui lòng kiểm tra lại thông tin.',
                    'errors': errors
                }, status=400)
            else:
                messages.error(request, 'Có lỗi khi lưu phiếu kết thúc. Vui lòng kiểm tra lại thông tin.')
    else:
        initial_data = {
            'ENDDATE': date.today(),
            'ENDFORMDATE': date.today(),
            'WITHDRAWREASON': 'na',
            'INCOMPLETE': 'na',
            'LOSTTOFOLLOWUP': 'na',
        }
        form = ContactEndCaseCRFForm(initial=initial_data)

    return render(request, 'studies/study_43en/CRF/contactendcasecrf_form.html', {
        'form': form,
        'enrollment_contact': enrollment_contact,
        'is_create': True,
        'today': date.today(),
    })

@login_required
@audit_log_decorator(model_name='CONTACTENDCASECRF')
def contactendcasecrf_update(request, usubjid):
    """Cập nhật phiếu kết thúc nghiên cứu cho người tiếp xúc"""
    screening_contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    enrollment_contact = get_object_or_404(EnrollmentContact, USUBJID=screening_contact)
    endcase = get_object_or_404(ContactEndCaseCRF, USUBJID=enrollment_contact)

    # Chuẩn bị audit data
    old_data = safe_json_loads(request.POST.get('oldDataJson', '{}'))
    new_data = safe_json_loads(request.POST.get('newDataJson', '{}'))
    reasons_json = safe_json_loads(request.POST.get('reasonsJson', '{}'))
    change_reason = request.POST.get('change_reason', '')
    
    print("DEBUG - contactendcasecrf_update - old_data:", old_data)
    print("DEBUG - contactendcasecrf_update - new_data:", new_data)
    print("DEBUG - contactendcasecrf_update - reasons_json:", reasons_json)
    print("DEBUG - contactendcasecrf_update - change_reason:", change_reason)
    
    request.audit_data = {
        'old_data': old_data,
        'new_data': new_data,
        'reasons_json': reasons_json,
        'reason': change_reason
    }

    if request.method == 'POST':
        form = ContactEndCaseCRFForm(request.POST, instance=endcase)
        if form.is_valid():
            form.save()
            
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Đã cập nhật phiếu kết thúc nghiên cứu cho người tiếp xúc {usubjid}.',
                    'redirect_url': reverse('study_43en:contact_detail', kwargs={'usubjid': usubjid})
                })
            else:
                messages.success(request, f'Đã cập nhật phiếu kết thúc nghiên cứu cho người tiếp xúc {usubjid}.')
                return redirect('study_43en:contact_detail', usubjid=usubjid)
        else:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                errors = form.errors
                print("DEBUG - Form errors:", errors)
                return JsonResponse({
                    'success': False,
                    'message': 'Có lỗi khi cập nhật phiếu kết thúc. Vui lòng kiểm tra lại thông tin.',
                    'errors': errors
                }, status=400)
            else:
                messages.error(request, 'Có lỗi khi cập nhật phiếu kết thúc. Vui lòng kiểm tra lại thông tin.')
    else:
        form = ContactEndCaseCRFForm(instance=endcase)

    return render(request, 'studies/study_43en/CRF/contactendcasecrf_form.html', {
        'form': form,
        'enrollment_contact': enrollment_contact,
        'is_create': False,
        'today': date.today(),
    })

@login_required
@audit_log_decorator(model_name='CONTACTENDCASECRF')
def contactendcasecrf_view(request, usubjid):
    """Xem phiếu kết thúc nghiên cứu ở chế độ chỉ đọc cho người tiếp xúc"""
    screening_contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    enrollment_contact = get_object_or_404(EnrollmentContact, USUBJID=screening_contact)
    endcase = get_object_or_404(ContactEndCaseCRF, USUBJID=enrollment_contact)
    
    form = ContactEndCaseCRFForm(instance=endcase)
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True

    return render(request, 'studies/study_43en/CRF/contactendcasecrf_form.html', {
        'form': form,
        'enrollment_contact': enrollment_contact,
        'is_view_only': True,
        'today': date.today(),
    })