import logging
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.translation import gettext as _

# Import models
from backends.studies.study_43en.models.patient import (
    ScreeningCase, EnrollmentCase,
)
from backends.studies.study_43en.models.contact import (
    ScreeningContact, EnrollmentContact
)

# Import forms
from backends.studies.study_43en.forms_patient import ScreeningCaseForm
from backends.studies.study_43en.forms_contact import ScreeningContactForm

# Import utils
from backends.studies.study_43en.utils.audit_log_cross_db import audit_log_decorator

logger = logging.getLogger(__name__)


# ============================================
# PATIENT SCREENING VIEWS
# ============================================

@login_required
@audit_log_decorator(model_name='SCREENINGCASE')
def screening_case_list(request):
    """Danh sách các bệnh nhân sàng lọc"""
    enrolled = request.GET.get('enrolled', '') == 'true'
    query = request.GET.get('q', '').strip()
    site_id = request.session.get('selected_site_id', 'all')

    # Lấy queryset và lọc theo site
    if site_id and site_id != 'all':
        cases = ScreeningCase.site_objects.filter_by_site(site_id)
    else:
        cases = ScreeningCase.objects.all()

    # Lọc theo trạng thái đã đăng ký
    if enrolled:
        cases = cases.filter(
            UPPER16AGE=True,
            INFPRIOR2OR48HRSADMIT=True,
            ISOLATEDKPNFROMINFECTIONORBLOOD=True,
            KPNISOUNTREATEDSTABLE=False,
            CONSENTTOSTUDY=True
        )

    # ⚠️ PERFORMANCE ISSUE - Cần xem xét
    # Hiện tại: Convert queryset → list → sort/filter trong Python
    # Với nhiều records sẽ chậm vì load hết vào memory
    
    def normalize_SCRID(sid):
        """Extract số từ SCRID format PS0001 → 1"""
        match = re.match(r'PS0*(\d+)', sid or '')
        return int(match.group(1)) if match else -1

    # Tìm kiếm
    if query:
        try:
            query_num = int(query)
            # ⚠️ Convert to list để filter trong Python
            cases = [c for c in cases if normalize_SCRID(c.SCRID) == query_num]
        except ValueError:
            # ⚠️ Convert to list để filter trong Python
            cases = [c for c in cases if 
                     query.lower() in (c.SCRID or '').lower() or 
                     query.lower() in (c.USUBJID or '').lower() or 
                     query.lower() in (c.INITIAL or '').lower()]

    # ⚠️ Sort trong Python thay vì database
    cases = sorted(cases, key=lambda c: normalize_SCRID(c.SCRID))

    # Thống kê
    total_cases = len(cases)
    eligible_cases = len([
        c for c in cases if 
        c.UPPER16AGE and 
        c.INFPRIOR2OR48HRSADMIT and 
        c.ISOLATEDKPNFROMINFECTIONORBLOOD and 
        not c.KPNISOUNTREATEDSTABLE and 
        c.CONSENTTOSTUDY
    ])

    # Phân trang
    paginator = Paginator(cases, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'studies/study_43en/CRF/screening_case_list.html', {
        'page_obj': page_obj,
        'total_cases': total_cases,
        'eligible_cases': eligible_cases,
        'query': query,
        'view_type': 'enrolled' if enrolled else 'screening'
    })


@login_required
@audit_log_decorator(model_name='SCREENINGCASE')
def screening_case_create(request):
    """Tạo mới ScreeningCase với SCRID được sinh tự động"""
    selected_site_id = request.session.get('selected_site_id', 'all')

    if request.method == 'POST':
        form = ScreeningCaseForm(request.POST)
        if form.is_valid():
            screening_case = form.save(commit=False)
            
            # Chỉ set SITEID nếu chọn site cụ thể
            if selected_site_id != 'all':
                screening_case.SITEID = selected_site_id
            
            screening_case.save()
            messages.success(request, f'Đã tạo mới bệnh nhân {screening_case.SCRID} thành công.')

            # Kiểm tra eligibility và consent
            is_eligible = (
                form.cleaned_data.get('UPPER16AGE') and
                form.cleaned_data.get('INFPRIOR2OR48HRSADMIT') and
                form.cleaned_data.get('ISOLATEDKPNFROMINFECTIONORBLOOD') and
                not form.cleaned_data.get('KPNISOUNTREATEDSTABLE')
            )
            consent = form.cleaned_data.get('CONSENTTOSTUDY')

            if is_eligible and consent and screening_case.USUBJID:
                messages.info(request, 'Bệnh nhân đủ điều kiện và đã đồng ý tham gia. Vui lòng nhập thông tin chi tiết.')
                return redirect('study_43en:enrollment_case_create', usubjid=screening_case.USUBJID)
            
            return redirect('study_43en:screening_case_list')
    else:
        # Sinh SCRID mới
        all_ids = ScreeningCase.objects.values_list('SCRID', flat=True)
        max_num = 0
        for sid in all_ids:
            m = re.match(r'PS(\d+)', str(sid))
            if m:
                num = int(m.group(1))
                if num > max_num:
                    max_num = num
        
        new_SCRID = f"PS{max_num + 1:04d}"
        instance = ScreeningCase(SCRID=new_SCRID)
        initial_data = {'STUDYID': '43EN'}
        
        # Chỉ set SITEID mặc định nếu chọn site cụ thể
        if selected_site_id != 'all':
            initial_data['SITEID'] = selected_site_id
        
        form = ScreeningCaseForm(instance=instance, initial=initial_data)

    return render(request, 'studies/study_43en/CRF/screening_form.html', {
        'form': form,
        'is_create': True,
        'selected_site_id': selected_site_id
    })


@login_required
@audit_log_decorator(model_name='SCREENINGCASE')
def screening_case_update(request, usubjid):
    """Cập nhật thông tin ScreeningCase"""
    # Note: usubjid parameter ở đây thực chất là SCRID
    screening_case = get_object_or_404(ScreeningCase, SCRID=usubjid)
    
    # Lưu giá trị cũ để kiểm tra thay đổi
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
            create_usubjid = form.save()
            messages.success(request, f'Đã cập nhật thông tin bệnh nhân {screening_case.SCRID} thành công.')
            
            # Kiểm tra eligibility
            is_eligible = (
                form.cleaned_data.get('UPPER16AGE') and 
                form.cleaned_data.get('INFPRIOR2OR48HRSADMIT') and
                form.cleaned_data.get('ISOLATEDKPNFROMINFECTIONORBLOOD') and
                not form.cleaned_data.get('KPNISOUNTREATEDSTABLE')
            )
            consent = form.cleaned_data.get('CONSENTTOSTUDY')
            
            # ⚠️ LOGIC ISSUE - Edge case:
            # Chỉ check consent thay đổi, không check eligibility thay đổi
            # VD: Nếu trước đó consent=True nhưng không eligible,
            #     sau đó update eligible=True → không trigger enrollment
            newly_eligible_and_consented = (
                is_eligible and
                consent and
                not old_values['CONSENTTOSTUDY']  # Chỉ check consent change
            )
            
            # Nếu không đủ điều kiện hoặc không đồng ý
            if not is_eligible or not consent:
                messages.warning(request, 'Bệnh nhân không đủ điều kiện hoặc không đồng ý tham gia nghiên cứu. Đã lưu thông tin sàng lọc.')
                return redirect('study_43en:screening_case_list')
            
            # Nếu mới đủ điều kiện và đồng ý
            if newly_eligible_and_consented and create_usubjid:
                has_enrollment = EnrollmentCase.objects.filter(USUBJID=screening_case).exists()
                if not has_enrollment:
                    messages.info(request, 'Bệnh nhân đã đủ điều kiện và đồng ý tham gia. Vui lòng nhập thông tin chi tiết.')
                    return redirect('study_43en:enrollment_case_create', usubjid=screening_case.USUBJID)
            
            # Nếu đã có USUBJID, chuyển đến patient detail
            if screening_case.USUBJID:
                return redirect('study_43en:patient_detail', usubjid=screening_case.USUBJID)
            
            return redirect('study_43en:screening_case_list')
    else:
        form = ScreeningCaseForm(instance=screening_case)
    
    return render(request, 'studies/study_43en/CRF/screening_form.html', {
        'form': form,
        'is_create': False
    })


@login_required
@audit_log_decorator(model_name='SCREENINGCASE')
def screening_case_view(request, SCRID):
    """Xem thông tin ScreeningCase (read-only)"""
    screening_case = get_object_or_404(ScreeningCase, SCRID=SCRID)
    form = ScreeningCaseForm(instance=screening_case)
    
    # Set readonly cho tất cả fields
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True
        if hasattr(field.widget, 'choices'):
            field.widget.attrs['onclick'] = 'return false;'
    
    return render(request, 'studies/study_43en/CRF/screening_form.html', {
        'form': form,
        'is_create': False,
        'is_readonly': True,
        'screening_case': screening_case,
        'selected_site_id': request.session.get('selected_site_id', 'all'),
    })


@login_required
@audit_log_decorator(model_name='SCREENINGCASE')
def screening_case_delete(request, usubjid):
    """Xóa ScreeningCase"""
    # Note: usubjid parameter ở đây thực chất là SCRID
    screening_case = get_object_or_404(ScreeningCase, SCRID=usubjid)
    
    if request.method == 'POST':
        screening_case.delete()
        messages.success(request, f'Đã xóa bệnh nhân {screening_case.SCRID} thành công.')
        return redirect('study_43en:screening_case_list')
    
    return render(request, 'studies/study_43en/CRF/screening_case_confirm_delete.html', {
        'screening_case': screening_case
    })


# ============================================
# CONTACT SCREENING VIEWS
# ============================================

@login_required
def screening_contact_list(request):
    """Danh sách người tiếp xúc sàng lọc"""
    query = request.GET.get('q', '').strip()
    site_id = request.session.get('selected_site_id', 'all')
    
    # Lấy contacts với site filter
    contacts = ScreeningContact.site_objects.filter_by_site(site_id).order_by('SCRID')

    # Tìm kiếm
    if query:
        contacts = contacts.filter(
            Q(SCRID__icontains=query) |
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
    page_obj = paginator.get_page(request.GET.get('page'))

    # Thêm thông tin enrollment status
    for contact in page_obj:
        contact.has_enropllment = hasattr(contact, 'enrollmentcontact') and contact.enrollmentcontact is not None

    return render(request, 'studies/study_43en/CRF/screening_contact_list.html', {
        'page_obj': page_obj,
        'total_contacts': total_contacts,
        'eligible_contacts': eligible_contacts,
        'enrolled_contacts': enrolled_contacts,
        'query': query,
        'view_type': 'screening_contacts'
    })


@login_required
@audit_log_decorator(model_name='SCREENINGCONTACT')
def screening_contact_create(request):
    """Tạo mới thông tin người tiếp xúc"""
    selected_site_id = request.session.get('selected_site_id', 'all')
    patient_id = request.GET.get('patient_id')
    
    if request.method == 'POST':
        form = ScreeningContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            
            # Chỉ set SITEID nếu chọn site cụ thể
            if selected_site_id != 'all':
                contact.SITEID = selected_site_id
            
            created_usubjid = contact.save()
            
            if created_usubjid:
                messages.success(request, f'Đã tạo mới người tiếp xúc thành công với mã {contact.USUBJID}')
            else:
                messages.success(request, 'Đã tạo mới thông tin người tiếp xúc thành công.')
            
            # Kiểm tra eligibility và consent
            is_eligible = (
                form.cleaned_data.get('LIVEIN5DAYS3MTHS') and
                form.cleaned_data.get('MEALCAREONCEDAY')
            )
            consent = form.cleaned_data.get('CONSENTTOSTUDY')
            
            if is_eligible and consent:
                messages.info(request, 'Contact đủ điều kiện và đã đồng ý tham gia. Vui lòng nhập thông tin chi tiết.')
                return redirect('study_43en:enrollment_contact_create', usubjid=contact.USUBJID)
            else:
                if not is_eligible:
                    messages.warning(request, 'Contact không đủ điều kiện tham gia nghiên cứu. Đã lưu thông tin sàng lọc.')
                elif not consent:
                    messages.warning(request, 'Contact không đồng ý tham gia nghiên cứu. Đã lưu thông tin sàng lọc.')
                
                return redirect('study_43en:screening_contact_list')
    else:
        initial_data = {'STUDYID': '43EN'}
        
        # Chỉ set SITEID mặc định nếu chọn site cụ thể
        if selected_site_id != 'all':
            initial_data['SITEID'] = selected_site_id
        
        # Nếu có patient_id, link với bệnh nhân chính
        if patient_id:
            try:
                patient = ScreeningCase.objects.get(USUBJID=patient_id)
                initial_data['SUBJIDENROLLSTUDY'] = patient.pk
            except ScreeningCase.DoesNotExist:
                pass
        
        form = ScreeningContactForm(initial=initial_data)

    return render(request, 'studies/study_43en/CRF/screening_contact_form.html', {
        'form': form,
        'title': _('Tạo mới người tiếp xúc'),
        'selected_site_id': selected_site_id,
        'is_create': True
    })


@login_required
@audit_log_decorator(model_name='SCREENINGCONTACT')
def screening_contact_update(request, SCRID):
    """Cập nhật thông tin người tiếp xúc"""
    contact = get_object_or_404(ScreeningContact, SCRID=SCRID)
    
    # Lưu giá trị cũ để kiểm tra thay đổi
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
                messages.success(request, f'Đã cập nhật thông tin và tạo mã {contact.USUBJID} thành công.')
            else:
                messages.success(request, 'Đã cập nhật thông tin người tiếp xúc thành công.')
            
            # Kiểm tra eligibility
            is_eligible = (
                form.cleaned_data.get('LIVEIN5DAYS3MTHS') and
                form.cleaned_data.get('MEALCAREONCEDAY')
            )
            consent = form.cleaned_data.get('CONSENTTOSTUDY')
            
            # ⚠️ LOGIC ISSUE - Cùng edge case như screening_case_update
            newly_eligible_and_consented = (
                is_eligible and
                consent and
                not old_values['CONSENTTOSTUDY']
            )
            
            # Nếu không đủ điều kiện hoặc không đồng ý
            if not is_eligible or not consent:
                messages.warning(request, 'Contact không đủ điều kiện hoặc không đồng ý tham gia nghiên cứu. Đã lưu thông tin sàng lọc.')
                return redirect('study_43en:screening_contact_list')
            
            # Nếu mới đủ điều kiện và đồng ý
            if newly_eligible_and_consented:
                has_enrollment = EnrollmentContact.objects.filter(USUBJID=contact).exists()
                if not has_enrollment:
                    messages.info(request, 'Contact đã đủ điều kiện và đồng ý tham gia. Vui lòng nhập thông tin chi tiết.')
                    return redirect('study_43en:enrollment_contact_create', usubjid=contact.USUBJID)
            
            # Nếu đã có USUBJID, chuyển đến contact detail
            if is_eligible and consent:
                return redirect('study_43en:contact_detail', usubjid=contact.USUBJID)
            
            return redirect('study_43en:screening_contact_list')
    else:
        form = ScreeningContactForm(instance=contact)

    return render(request, 'studies/study_43en/CRF/screening_contact_form.html', {
        'form': form,
        'contact': contact,
        'title': _('Cập nhật người tiếp xúc')
    })


@login_required
@audit_log_decorator(model_name='SCREENINGCONTACT')
def screening_contact_view(request, SCRID):
    """Xem chi tiết thông tin người tiếp xúc (read-only)"""
    contact = get_object_or_404(ScreeningContact, SCRID=SCRID)
    form = ScreeningContactForm(instance=contact)
    
    # Set readonly cho tất cả fields
    for field in form.fields.values():
        field.widget.attrs['disabled'] = True
        field.widget.attrs['readonly'] = True
    
    return render(request, 'studies/study_43en/CRF/screening_contact_form.html', {
        'form': form,
        'contact': contact,
        'title': _('Chi tiết người tiếp xúc'),
        'is_view_only': True
    })


@login_required
@audit_log_decorator(model_name='SCREENINGCONTACT')
def screening_contact_delete(request, SCRID):
    """Xóa thông tin người tiếp xúc"""
    contact = get_object_or_404(ScreeningContact, SCRID=SCRID)
    
    if request.method == 'POST':
        contact.delete()
        messages.success(request, 'Đã xóa thông tin người tiếp xúc thành công.')
        return redirect('study_43en:screening_contact_list')
    
    # Thống kê cho confirm page
    total_patients = ScreeningCase.objects.filter(SUBJID__startswith='A-').count()
    total_contacts = ScreeningContact.objects.count()
    eligible_contacts = ScreeningContact.objects.filter(
        CONSENTTOSTUDY=True,
        LIVEIN5DAYS3MTHS=True,
        MEALCAREONCEDAY=True
    ).count()
    
    return render(request, 'studies/study_43en/CRF/screening_contact_confirm_delete.html', {
        'contact': contact,
        'total_patients': total_patients,
        'total_contacts': total_contacts,
        'eligible_contacts': eligible_contacts
    })