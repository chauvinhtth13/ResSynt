import json
import logging
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError

# Import models
from backends.studies.study_43en.models.patient import (
    ScreeningCase, EnrollmentCase
)
from backends.studies.study_43en.models.contact import (
    ScreeningContact, EnrollmentContact
)

# Import forms
from backends.studies.study_43en.forms_patient import (
    ScreeningCaseForm, EnrollmentCaseForm, MedHisDrugFormSet
)
from backends.studies.study_43en.forms_contact import (
    EnrollmentContactForm, ContactMedHisDrugFormSet
)

# Import utils
from backends.studies.study_43en.utils.audit_log_utils import safe_json_loads
from backends.studies.study_43en.utils.audit_log_cross_db import audit_log_decorator
from backends.studies.study_43en.utils import get_site_filtered_object_or_404

logger = logging.getLogger(__name__)


# ============================================
# PATIENT ENROLLMENT VIEWS
# ============================================

@login_required
@audit_log_decorator(model_name='ENROLLMENTCASE')
def enrollment_case_create(request, usubjid):
    """Tạo mới EnrollmentCase cho bệnh nhân đã được screening"""
    
    # Lấy site_id từ session
    site_id = request.session.get('selected_site_id', 'all')
    
    # Lấy screening case với site filter
    screening_case = get_site_filtered_object_or_404(
        ScreeningCase, site_id, USUBJID=usubjid, is_confirmed=True
    )
    
    # Kiểm tra điều kiện tham gia
    if not (screening_case.UPPER16AGE and 
            screening_case.INFPRIOR2OR48HRSADMIT and 
            screening_case.ISOLATEDKPNFROMINFECTIONORBLOOD and 
            not screening_case.KPNISOUNTREATEDSTABLE and
            screening_case.CONSENTTOSTUDY):
        messages.error(request, f'Bệnh nhân {usubjid} không đủ điều kiện hoặc không đồng ý tham gia nghiên cứu.')
        return redirect('study_43en:screening_case_list')
    
    # Kiểm tra đã có enrollment chưa
    try:
        if site_id and site_id != 'all':
            EnrollmentCase.site_objects.filter_by_site(site_id).get(USUBJID=screening_case)
        else:
            EnrollmentCase.objects.get(USUBJID=screening_case)
        
        messages.warning(request, f'Bệnh nhân {usubjid} đã có thông tin chi tiết. Chuyển tới trang cập nhật.')
        return redirect('study_43en:enrollment_case_update', usubjid=usubjid)
    except EnrollmentCase.DoesNotExist:
        pass

    if request.method == 'POST':
        form = EnrollmentCaseForm(request.POST)
        medhisdrug_formset = MedHisDrugFormSet(request.POST, instance=None)
        
        if form.is_valid() and medhisdrug_formset.is_valid():
            try:
                enrollment_case = form.save(commit=False)
                enrollment_case.USUBJID = screening_case
                enrollment_case.save()
                
                medhisdrug_formset.instance = enrollment_case
                medhisdrug_formset.save()
                
                messages.success(request, f'Đã tạo thông tin chi tiết cho bệnh nhân {usubjid} thành công.')
                return redirect('study_43en:patient_detail', usubjid=usubjid)
            except IntegrityError:
                messages.error(request, f'Bệnh nhân {usubjid} đã có thông tin chi tiết.')
                return redirect('study_43en:enrollment_case_update', usubjid=usubjid)
        else:
            # Log formset errors
            if medhisdrug_formset.errors:
                logger.error(f"MedHisDrug formset errors: {medhisdrug_formset.errors}")
    else:
        initial_data = {
            'ENRDATE': screening_case.SCREENINGFORMDATE,
            'INITIAL': screening_case.INITIAL,
            'COMPLETEDBY': screening_case.COMPLETEDBY,
        }
        form = EnrollmentCaseForm(initial=initial_data)
        medhisdrug_formset = MedHisDrugFormSet(instance=None)
    
    return render(request, 'studies/study_43en/CRF/enrollment_form.html', {
        'form': form,
        'medhisdrug_formset': medhisdrug_formset,
        'screening_case': screening_case,
        'is_create': True,
    })


@login_required
@audit_log_decorator(model_name='ENROLLMENTCASE')
def enrollment_case_update(request, usubjid):
    """Cập nhật thông tin EnrollmentCase"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    
    if request.method == 'POST':
        # Chuẩn bị audit data
        old_data = safe_json_loads(request.POST.get('oldDataJson', '{}'))
        new_data = safe_json_loads(request.POST.get('newDataJson', '{}'))
        reasons_json = safe_json_loads(request.POST.get('reasonsJson', '{}'))
        change_reason = request.POST.get('change_reason', '')
        
        # Loại bỏ USUBJID khỏi audit data
        old_data = {k: v for k, v in old_data.items() if k.upper() != 'USUBJID'}
        new_data = {k: v for k, v in new_data.items() if k.upper() != 'USUBJID'}
        
        request.audit_data = {
            'old_data': old_data,
            'new_data': new_data,
            'reasons_json': reasons_json,
            'reason': change_reason
        }
        
        form = EnrollmentCaseForm(request.POST, instance=enrollment_case)
        medhisdrug_formset = MedHisDrugFormSet(request.POST, instance=enrollment_case)
        
        if form.is_valid() and medhisdrug_formset.is_valid():
            form.save()
            medhisdrug_formset.save()
            messages.success(request, f'Đã cập nhật thông tin chi tiết cho bệnh nhân {usubjid} thành công.')
            return redirect('study_43en:patient_detail', usubjid=usubjid)
        else:
            if medhisdrug_formset.errors:
                logger.error(f"MedHisDrug formset errors: {medhisdrug_formset.errors}")
    else:
        form = EnrollmentCaseForm(instance=enrollment_case)
        medhisdrug_formset = MedHisDrugFormSet(instance=enrollment_case)
    
    return render(request, 'studies/study_43en/CRF/enrollment_form.html', {
        'form': form,
        'medhisdrug_formset': medhisdrug_formset,
        'enrollment_case': enrollment_case,
        'screening_case': screening_case,
        'is_create': False,
    })


@login_required
@audit_log_decorator(model_name='ENROLLMENTCASE')
def enrollment_case_view(request, usubjid):
    """Xem thông tin EnrollmentCase (read-only)"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    try:
        enrollment_case = EnrollmentCase.objects.get(USUBJID=screening_case)
    except EnrollmentCase.DoesNotExist:
        messages.error(request, f'Bệnh nhân {usubjid} chưa có thông tin chi tiết.')
        return redirect('study_43en:patient_detail', usubjid=usubjid)
    
    form = EnrollmentCaseForm(instance=enrollment_case)
    medhisdrug_formset = MedHisDrugFormSet(instance=enrollment_case)
    
    # Set readonly cho form
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True
    
    # Set readonly cho formset
    for form_instance in medhisdrug_formset.forms:
        for field in form_instance.fields.values():
            field.widget.attrs['readonly'] = True
            field.widget.attrs['disabled'] = True
    
    return render(request, 'studies/study_43en/CRF/enrollment_form.html', {
        'form': form,
        'medhisdrug_formset': medhisdrug_formset,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'is_view_only': True,
        'today': date.today(),
    })


@login_required
@audit_log_decorator(model_name='ENROLLMENTCASE')
def enrollment_case_delete(request, usubjid):
    """Xóa EnrollmentCase"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    
    if request.method == 'POST':
        enrollment_case.delete()
        messages.success(request, f'Đã xóa thông tin chi tiết của bệnh nhân {usubjid} thành công.')
        return redirect('study_43en:patient_detail', usubjid=usubjid)
    
    return render(request, 'studies/study_43en/CRF/enrollment_case_confirm_delete.html', {
        'enrollment_case': enrollment_case,
        'screening_case': screening_case
    })


# ============================================
# CONTACT ENROLLMENT VIEWS
# ============================================

@login_required
@audit_log_decorator(model_name='ENROLLMENTCONTACT')
def enrollment_contact_create(request, usubjid):
    """Tạo mới EnrollmentContact cho contact đã được screening"""
    contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    
    # Kiểm tra điều kiện tham gia
    if not (contact.LIVEIN5DAYS3MTHS and 
            contact.MEALCAREONCEDAY and 
            contact.CONSENTTOSTUDY):
        messages.error(request, f'Contact {usubjid} không đủ điều kiện hoặc không đồng ý tham gia nghiên cứu.')
        return redirect('study_43en:screening_contact_list')
    
    # Kiểm tra đã có EnrollmentContact chưa
    try:
        EnrollmentContact.objects.get(USUBJID=contact)
        messages.warning(request, f'Contact {usubjid} đã có thông tin chi tiết. Chuyển tới trang cập nhật.')
        return redirect('study_43en:enrollment_contact_update', usubjid=usubjid)
    except EnrollmentContact.DoesNotExist:
        pass

    if request.method == 'POST':
        form = EnrollmentContactForm(request.POST)
        medication_formset = ContactMedHisDrugFormSet(request.POST, instance=None)
        
        # Chuẩn bị audit data
        request.audit_data = {
            'old_data': safe_json_loads(request.POST.get('oldDataJson', '{}')),
            'new_data': safe_json_loads(request.POST.get('newDataJson', '{}')),
            'reasons_json': safe_json_loads(request.POST.get('reasonsJson', '{}')),
            'reason': request.POST.get('change_reason', '')
        }
        
        if form.is_valid() and medication_formset.is_valid():
            try:
                enrollment = form.save(commit=False)
                enrollment.USUBJID = contact
                enrollment.save()
                
                # Save medication formset
                medication_formset.instance = enrollment
                medication_formset.save()
                
                messages.success(request, f'Đã tạo thông tin chi tiết cho contact {usubjid} thành công.')
                return redirect('study_43en:contact_detail', usubjid=usubjid)
            except IntegrityError:
                messages.error(request, f'Contact {usubjid} đã có thông tin chi tiết.')
                return redirect('study_43en:enrollment_contact_update', usubjid=usubjid)
        else:
            if medication_formset.errors:
                logger.error(f"Medication formset errors: {medication_formset.errors}")
    else:
        initial_data = {
            'ENRDATE': contact.SCREENINGFORMDATE,
            'COMPLETEDBY': contact.COMPLETEDBY,
        }
        form = EnrollmentContactForm(initial=initial_data)
        medication_formset = ContactMedHisDrugFormSet(instance=None)

    return render(request, 'studies/study_43en/CRF/enrollment_contact_form.html', {
        'form': form,
        'medication_formset': medication_formset,
        'contact': contact,
        'screening_contact': contact,
        'is_create': True,
    })


@login_required
@audit_log_decorator(model_name='ENROLLMENTCONTACT')
def enrollment_contact_update(request, usubjid):
    """Cập nhật thông tin EnrollmentContact"""
    contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    enrollment = get_object_or_404(EnrollmentContact, USUBJID=contact)
    
    if request.method == 'POST':
        form = EnrollmentContactForm(request.POST, instance=enrollment)
        medication_formset = ContactMedHisDrugFormSet(request.POST, instance=enrollment)
        
        # Chuẩn bị audit data
        request.audit_data = {
            'old_data': safe_json_loads(request.POST.get('oldDataJson', '{}')),
            'new_data': safe_json_loads(request.POST.get('newDataJson', '{}')),
            'reasons_json': safe_json_loads(request.POST.get('reasonsJson', '{}')),
            'reason': request.POST.get('change_reason', '')
        }
        
        if form.is_valid() and medication_formset.is_valid():
            enrollment = form.save()
            medication_formset.save()
            
            messages.success(request, f'Đã cập nhật thông tin đăng ký cho người tiếp xúc {usubjid}')
            return redirect('study_43en:contact_detail', usubjid=usubjid)
        else:
            if medication_formset.errors:
                logger.error(f"Medication formset errors: {medication_formset.errors}")
    else:
        form = EnrollmentContactForm(instance=enrollment)
        medication_formset = ContactMedHisDrugFormSet(instance=enrollment)
    
    return render(request, 'studies/study_43en/CRF/enrollment_contact_form.html', {
        'form': form,
        'medication_formset': medication_formset,
        'contact': contact,
        'is_create': False,
    })


@login_required
@audit_log_decorator(model_name='ENROLLMENTCONTACT')
def enrollment_contact_view(request, usubjid):
    """Xem thông tin EnrollmentContact (read-only)"""
    contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    enrollment = get_object_or_404(EnrollmentContact, USUBJID=contact)
    
    form = EnrollmentContactForm(instance=enrollment)
    medication_formset = ContactMedHisDrugFormSet(instance=enrollment)
    
    # Set readonly cho form
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True
    
    # Set readonly cho formset
    for medication_form in medication_formset.forms:
        for field in medication_form.fields.values():
            field.widget.attrs['readonly'] = True
            field.widget.attrs['disabled'] = True
    
    return render(request, 'studies/study_43en/CRF/enrollment_contact_form.html', {
        'form': form,
        'medication_formset': medication_formset,
        'contact': contact,
        'is_view_only': True,
    })