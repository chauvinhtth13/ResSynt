import json
import logging
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext as _

# Import models từ study app
from backends.studies.study_43en.models.patient import (
    EnrollmentCase, SampleCollection,

)
from backends.studies.study_43en.models.contact import (
    ScreeningContact, EnrollmentContact, 
    ContactSampleCollection
)
from backends.studies.study_43en.forms_patient import (
    SampleCollectionForm
)
from backends.studies.study_43en.forms_contact import (
    ContactSampleCollectionForm,
)

# Import utils từ study app
from backends.studies.study_43en.utils.audit_log_cross_db import audit_log_decorator


logger = logging.getLogger(__name__)

@login_required
def sample_collection_list(request, usubjid):
    """Hiển thị danh sách các mẫu đã thu thập của bệnh nhân"""
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID__USUBJID=usubjid)
    mode = request.GET.get('mode', 'edit')
    is_view_only = mode == 'view'
    
    sample_types = SampleCollection.SAMPLE_TYPE_CHOICES
    samples = SampleCollection.objects.filter(USUBJID=enrollment_case)
    samples_by_type = {sample.SAMPLE_TYPE: sample for sample in samples}

    return render(request, 'studies/study_43en/CRF/sample_collection_list.html', {
        'usubjid': usubjid,
        'enrollment_case': enrollment_case,
        'sample_types': sample_types,
        'samples': samples,
        'samples_by_type': samples_by_type,
        'is_view_only': is_view_only,
    })

@login_required
@audit_log_decorator(model_name='SAMPLECOLLECTION')
# @require_POST
def sample_collection_create(request, usubjid, sample_type):
    """Tạo mới mẫu thu thập"""
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID__USUBJID=usubjid)

    try:
        sample = SampleCollection.objects.get(USUBJID=enrollment_case, SAMPLE_TYPE=sample_type)
        return redirect('sample_collection_update', usubjid=usubjid, sample_type=sample_type)
    except SampleCollection.DoesNotExist:
        sample = SampleCollection(USUBJID=enrollment_case, SAMPLE_TYPE=sample_type)

    if request.method == 'POST':
        print(f"POST Data: {request.POST}")
        post_data = request.POST.copy()

        # Xử lý các trường boolean
        for field_name in [
            'STOOL', 'THROATSWAB', 'RECTSWAB', 'BLOOD',
            'KLEBPNEU_1', 'OTHERRES_1', 'KLEBPNEU_2', 'OTHERRES_2', 'KLEBPNEU_3', 'OTHERRES_3'
        ]:
            post_data[field_name] = 'True' if field_name in post_data and post_data[field_name] == 'on' else 'False'

        # Đảm bảo ngày hoàn thành
        if not post_data.get('COMPLETEDDATE') or post_data.get('COMPLETEDDATE') == '':
            post_data['COMPLETEDDATE'] = date.today().strftime('%Y-%m-%d')

        post_data['SAMPLE_TYPE'] = sample_type

        form = SampleCollectionForm(post_data, instance=sample)
        if form.is_valid():
            sample = form.save(commit=False)
            sample.USUBJID = enrollment_case
            sample.SAMPLE_TYPE = sample_type

            # Nếu SAMPLE = False, xóa các thông tin mẫu
            if not sample.SAMPLE:
                sample.STOOL = False
                sample.THROATSWAB = False
                sample.RECTSWAB = False
                sample.BLOOD = False
                sample.CULTRES_1 = 'NoApply'
                sample.CULTRES_2 = 'NoApply'
                sample.CULTRES_3 = 'NoApply'
                sample.KLEBPNEU_1 = False
                sample.KLEBPNEU_2 = False
                sample.KLEBPNEU_3 = False
                sample.OTHERRES_1 = False
                sample.OTHERRES_2 = False
                sample.OTHERRES_3 = False
                sample.OTHERRESSPECIFY_1 = ''
                sample.OTHERRESSPECIFY_2 = ''
                sample.OTHERRESSPECIFY_3 = ''

            # Xóa ngày nếu không chọn mẫu tương ứng
            if not sample.STOOL:
                sample.STOOLDATE = None
            if not sample.THROATSWAB:
                sample.THROATSWABDATE = None
            if not sample.RECTSWAB:
                sample.RECTSWABDATE = None
            if not sample.BLOOD or sample.SAMPLE_TYPE == '4':
                sample.BLOOD = False
                sample.BLOODDATE = None

            # Lưu người hoàn thành
            if not sample.COMPLETEDBY:
                sample.COMPLETEDBY = request.user.username

            sample.save()
            messages.success(request, 'Đã tạo mới thông tin mẫu thành công!')
            return redirect('sample_collection_list', usubjid=usubjid)
        else:
            print("Form không hợp lệ!")
            print("POST Data:", post_data)
            print("Form errors:", form.errors)
            messages.error(request, f"Lỗi: {form.errors}")
    else:
        form = SampleCollectionForm(instance=sample)

    return render(request, 'studies/study_43en/CRF/sample_collection_form.html', {
        'form': form,
        'sample': sample,
        'enrollment_case': enrollment_case,
        'is_new': True,
        'usubjid': usubjid,
        'sample_type': sample_type,
        'today': date.today(),
    })

@login_required
@audit_log_decorator(model_name='SAMPLECOLLECTION')
# @require_POST
def sample_collection_update(request, usubjid, sample_type):
    """Cập nhật mẫu thu thập"""
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID__USUBJID=usubjid)
    sample = get_object_or_404(SampleCollection, USUBJID=enrollment_case, SAMPLE_TYPE=sample_type)
    
    if request.method == 'GET':
        # Hiển thị form cập nhật
        form = SampleCollectionForm(instance=sample)
        return render(request, 'studies/study_43en/CRF/sample_collection_form.html', {
            'form': form,
            'sample': sample,
            'enrollment_case': enrollment_case,
            'is_new': False,
            'usubjid': usubjid,
            'sample_type': sample_type,
            'today': date.today(),
        })
    
    elif request.method == 'POST':
        # Xử lý cập nhật từ form POST
        try:
            print(f"POST Data: {request.POST}")

            # Lấy old_data từ model nếu không có trong request
            old_data = request.POST.get('oldDataJson', '')
            if not old_data:
                old_data = {
                    'SAMPLE_TYPE': sample.SAMPLE_TYPE,
                    'SAMPLE': str(sample.SAMPLE),
                    'STOOL': str(sample.STOOL),
                    'STOOLDATE': sample.STOOLDATE.isoformat() if sample.STOOLDATE else '',
                    'RECTSWAB': str(sample.RECTSWAB),
                    'RECTSWABDATE': sample.RECTSWABDATE.isoformat() if sample.RECTSWABDATE else '',
                    'THROATSWAB': str(sample.THROATSWAB),
                    'THROATSWABDATE': sample.THROATSWABDATE.isoformat() if sample.THROATSWABDATE else '',
                    'BLOOD': str(sample.BLOOD),
                    'BLOODDATE': sample.BLOODDATE.isoformat() if sample.BLOODDATE else '',
                    'REASONIFNO': sample.REASONIFNO or '',
                    'CULTRES_1': sample.CULTRES_1 or '',
                    'KLEBPNEU_1': str(sample.KLEBPNEU_1),
                    'OTHERRES_1': str(sample.OTHERRES_1),
                    'OTHERRESSPECIFY_1': sample.OTHERRESSPECIFY_1 or '',
                    'CULTRES_2': sample.CULTRES_2 or '',
                    'KLEBPNEU_2': str(sample.KLEBPNEU_2),
                    'OTHERRES_2': str(sample.OTHERRES_2),
                    'OTHERRESSPECIFY_2': sample.OTHERRESSPECIFY_2 or '',
                    'CULTRES_3': sample.CULTRES_3 or '',
                    'KLEBPNEU_3': str(sample.KLEBPNEU_3),
                    'OTHERRES_3': str(sample.OTHERRES_3),
                    'OTHERRESSPECIFY_3': sample.OTHERRESSPECIFY_3 or '',
                    'COMPLETEDBY': sample.COMPLETEDBY or '',
                    'COMPLETEDDATE': sample.COMPLETEDDATE.isoformat() if sample.COMPLETEDDATE else ''
                }
                request.POST = request.POST.copy()
                request.POST['oldDataJson'] = json.dumps(old_data)

            post_data = request.POST.copy()

            # Xử lý các trường boolean
            for field_name in [
                'STOOL', 'THROATSWAB', 'RECTSWAB', 'BLOOD',
                'KLEBPNEU_1', 'OTHERRES_1', 'KLEBPNEU_2', 'OTHERRES_2', 'KLEBPNEU_3', 'OTHERRES_3'
            ]:
                post_data[field_name] = 'True' if field_name in post_data and post_data[field_name] == 'on' else 'False'

            # Đảm bảo ngày hoàn thành
            if not post_data.get('COMPLETEDDATE') or post_data.get('COMPLETEDDATE') == '':
                post_data['COMPLETEDDATE'] = date.today().strftime('%Y-%m-%d')

            post_data['SAMPLE_TYPE'] = sample_type

            form = SampleCollectionForm(post_data, instance=sample)
            if form.is_valid():
                sample = form.save(commit=False)
                sample.USUBJID = enrollment_case
                sample.SAMPLE_TYPE = sample_type

                # Nếu SAMPLE = False, xóa các thông tin mẫu
                if not sample.SAMPLE:
                    sample.STOOL = False
                    sample.THROATSWAB = False
                    sample.RECTSWAB = False
                    sample.BLOOD = False
                    sample.CULTRES_1 = 'NoApply'
                    sample.CULTRES_2 = 'NoApply'
                    sample.CULTRES_3 = 'NoApply'
                    sample.KLEBPNEU_1 = False
                    sample.KLEBPNEU_2 = False
                    sample.KLEBPNEU_3 = False
                    sample.OTHERRES_1 = False
                    sample.OTHERRES_2 = False
                    sample.OTHERRES_3 = False
                    sample.OTHERRESSPECIFY_1 = ''
                    sample.OTHERRESSPECIFY_2 = ''
                    sample.OTHERRESSPECIFY_3 = ''

                # Xóa ngày nếu không chọn mẫu tương ứng
                if not sample.STOOL:
                    sample.STOOLDATE = None
                if not sample.THROATSWAB:
                    sample.THROATSWABDATE = None
                if not sample.RECTSWAB:
                    sample.RECTSWABDATE = None
                if not sample.BLOOD or sample.SAMPLE_TYPE == '4':
                    sample.BLOOD = False
                    sample.BLOODDATE = None

                # Lưu người hoàn thành
                if not sample.COMPLETEDBY:
                    sample.COMPLETEDBY = request.user.username

                sample.save()
                
                # Áp dụng audit log sau khi lưu thành công
                if hasattr(request, 'audit_data'):
                    from study_43en.models import AuditLog
                    AuditLog.objects.create(
                        user=request.user,
                        model_name='SAMPLECOLLECTION',
                        record_id=sample.id,
                        old_data=request.audit_data.get('old_data', '{}'),
                        new_data=request.audit_data.get('new_data', '{}'),
                        change_reason=request.audit_data.get('change_reason', ''),
                        action='UPDATE'
                    )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Cập nhật thông tin mẫu thu thập thành công!'
                })
            else:
                print("Form không hợp lệ!")
                print("POST Data:", post_data)
                print("Form errors:", form.errors)
                return JsonResponse({
                    'success': False,
                    'message': f'Lỗi: {form.errors.as_text()}'
                }, status=400)
        except Exception as e:
            import traceback
            print(f"Error in sample_collection_update: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'message': f'Lỗi khi cập nhật: {str(e)}'
            }, status=500)

@login_required
def sample_collection_view(request, usubjid, sample_type):
    """Xem thông tin mẫu ở chế độ chỉ đọc"""
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID__USUBJID=usubjid)
    sample = get_object_or_404(SampleCollection, USUBJID=enrollment_case, SAMPLE_TYPE=sample_type)
    form = SampleCollectionForm(instance=sample)
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True
    return render(request, 'studies/study_43en/CRF/sample_collection_form.html', {
        'form': form,
        'sample': sample,
        'enrollment_case': enrollment_case,
        'is_view_only': True,
        'usubjid': usubjid,
        'sample_type': sample_type,
    })


    
@login_required
def contact_sample_collection_list(request, usubjid):
    """Hiển thị danh sách các mẫu đã thu thập của người tiếp xúc"""
    screening_contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    
    try:
        enrollment_contact = EnrollmentContact.objects.get(USUBJID=screening_contact)
    except EnrollmentContact.DoesNotExist:
        messages.error(request, f'Người tiếp xúc {usubjid} chưa có thông tin ghi danh.')
        return redirect('study_43en:contact_detail', usubjid=usubjid)
    
    mode = request.GET.get('mode', 'edit')
    is_view_only = mode == 'view'
    
    sample_types = ContactSampleCollection.SAMPLE_TYPE_CHOICES
    samples = ContactSampleCollection.objects.filter(USUBJID=enrollment_contact)
    samples_by_type = {sample.SAMPLE_TYPE: sample for sample in samples}

    return render(request, 'studies/study_43en/CRF/contact_sample_collection_list.html', {
        'usubjid': usubjid,
        'screening_contact': screening_contact,
        'enrollment_contact': enrollment_contact,
        'sample_types': sample_types,
        'samples': samples,
        'samples_by_type': samples_by_type,
        'is_view_only': is_view_only,
    })

@login_required
@audit_log_decorator(model_name='CONTACTSAMPLECOLLECTION')
def contact_sample_collection_create(request, usubjid, sample_type):
    """Tạo mới mẫu thu thập của người tiếp xúc"""
    screening_contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    
    try:
        enrollment_contact = EnrollmentContact.objects.get(USUBJID=screening_contact)
    except EnrollmentContact.DoesNotExist:
        messages.error(request, f'Người tiếp xúc {usubjid} chưa có thông tin ghi danh.')
        return redirect('study_43en:contact_detail', usubjid=usubjid)

    try:
        sample = ContactSampleCollection.objects.get(USUBJID=enrollment_contact, SAMPLE_TYPE=sample_type)
        return redirect('contact_sample_collection_update', usubjid=usubjid, sample_type=sample_type)
    except ContactSampleCollection.DoesNotExist:
        sample = ContactSampleCollection(USUBJID=enrollment_contact, SAMPLE_TYPE=sample_type)

    if request.method == 'POST':
        print(f"POST Data: {request.POST}")
        post_data = request.POST.copy()

        # Xử lý các trường boolean
        for field_name in [
            'STOOL', 'THROATSWAB', 'RECTSWAB', 'BLOOD',
            'KLEBPNEU_1', 'OTHERRES_1', 'KLEBPNEU_2', 'OTHERRES_2', 'KLEBPNEU_3', 'OTHERRES_3'
        ]:
            post_data[field_name] = 'True' if field_name in post_data and post_data[field_name] == 'on' else 'False'

        # Đảm bảo ngày hoàn thành
        if not post_data.get('COMPLETEDDATE') or post_data.get('COMPLETEDDATE') == '':
            post_data['COMPLETEDDATE'] = date.today().strftime('%Y-%m-%d')

        post_data['SAMPLE_TYPE'] = sample_type

        form = ContactSampleCollectionForm(post_data, instance=sample)
        if form.is_valid():
            sample = form.save(commit=False)
            sample.USUBJID = enrollment_contact
            sample.SAMPLE_TYPE = sample_type

            # Nếu SAMPLE = False, xóa các thông tin mẫu
            if not sample.SAMPLE:
                sample.STOOL = False
                sample.THROATSWAB = False
                sample.RECTSWAB = False
                sample.BLOOD = False
                sample.CULTRES_1 = 'NoApply'
                sample.CULTRES_2 = 'NoApply'
                sample.CULTRES_3 = 'NoApply'
                sample.KLEBPNEU_1 = False
                sample.KLEBPNEU_2 = False
                sample.KLEBPNEU_3 = False
                sample.OTHERRES_1 = False
                sample.OTHERRES_2 = False
                sample.OTHERRES_3 = False
                sample.OTHERRESSPECIFY_1 = ''
                sample.OTHERRESSPECIFY_2 = ''
                sample.OTHERRESSPECIFY_3 = ''

            # Xóa ngày nếu không chọn mẫu tương ứng
            if not sample.STOOL:
                sample.STOOLDATE = None
            if not sample.THROATSWAB:
                sample.THROATSWABDATE = None
            if not sample.RECTSWAB:
                sample.RECTSWABDATE = None
            if not sample.BLOOD or sample.SAMPLE_TYPE != '1':
                sample.BLOOD = False
                sample.BLOODDATE = None

            # Lưu người hoàn thành
            if not sample.COMPLETEDBY:
                sample.COMPLETEDBY = request.user.username

            sample.save()
            messages.success(request, 'Đã tạo mới thông tin mẫu thành công!')
            return redirect('contact_sample_collection_list', usubjid=usubjid)
        else:
            print("Form không hợp lệ!")
            print("POST Data:", post_data)
            print("Form errors:", form.errors)
            messages.error(request, f"Lỗi: {form.errors}")
    else:
        form = ContactSampleCollectionForm(instance=sample)

    return render(request, 'studies/study_43en/CRF/contact_sample_collection_form.html', {
        'form': form,
        'sample': sample,
        'screening_contact': screening_contact,
        'enrollment_contact': enrollment_contact,
        'is_new': True,
        'usubjid': usubjid,
        'sample_type': sample_type,
        'today': date.today(),
    })

@login_required
@audit_log_decorator(model_name='CONTACTSAMPLECOLLECTION')
def contact_sample_collection_update(request, usubjid, sample_type):
    """Cập nhật mẫu thu thập của người tiếp xúc"""
    screening_contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    
    try:
        enrollment_contact = EnrollmentContact.objects.get(USUBJID=screening_contact)
    except EnrollmentContact.DoesNotExist:
        messages.error(request, f'Người tiếp xúc {usubjid} chưa có thông tin ghi danh.')
        return redirect('study_43en:contact_detail', usubjid=usubjid)

    sample = get_object_or_404(ContactSampleCollection, USUBJID=enrollment_contact, SAMPLE_TYPE=sample_type)
    
    if request.method == 'GET':
        form = ContactSampleCollectionForm(instance=sample)
        return render(request, 'studies/study_43en/CRF/contact_sample_collection_form.html', {
            'form': form,
            'sample': sample,
            'screening_contact': screening_contact,
            'enrollment_contact': enrollment_contact,
            'is_new': False,
            'usubjid': usubjid,
            'sample_type': sample_type,
            'today': date.today(),
        })
    
    elif request.method == 'POST':
        try:
            print(f"POST Data: {request.POST}")

            # Lấy old_data từ model nếu không có trong request
            old_data = request.POST.get('oldDataJson', '')
            if not old_data:
                old_data = {
                    'SAMPLE_TYPE': sample.SAMPLE_TYPE,
                    'SAMPLE': str(sample.SAMPLE),
                    'STOOL': str(sample.STOOL),
                    'STOOLDATE': sample.STOOLDATE.isoformat() if sample.STOOLDATE else '',
                    'RECTSWAB': str(sample.RECTSWAB),
                    'RECTSWABDATE': sample.RECTSWABDATE.isoformat() if sample.RECTSWABDATE else '',
                    'THROATSWAB': str(sample.THROATSWAB),
                    'THROATSWABDATE': sample.THROATSWABDATE.isoformat() if sample.THROATSWABDATE else '',
                    'BLOOD': str(sample.BLOOD),
                    'BLOODDATE': sample.BLOODDATE.isoformat() if sample.BLOODDATE else '',
                    'REASONIFNO': sample.REASONIFNO or '',
                    'CULTRES_1': sample.CULTRES_1 or '',
                    'KLEBPNEU_1': str(sample.KLEBPNEU_1),
                    'OTHERRES_1': str(sample.OTHERRES_1),
                    'OTHERRESSPECIFY_1': sample.OTHERRESSPECIFY_1 or '',
                    'CULTRES_2': sample.CULTRES_2 or '',
                    'KLEBPNEU_2': str(sample.KLEBPNEU_2),
                    'OTHERRES_2': str(sample.OTHERRES_2),
                    'OTHERRESSPECIFY_2': sample.OTHERRESSPECIFY_2 or '',
                    'CULTRES_3': sample.CULTRES_3 or '',
                    'KLEBPNEU_3': str(sample.KLEBPNEU_3),
                    'OTHERRES_3': str(sample.OTHERRES_3),
                    'OTHERRESSPECIFY_3': sample.OTHERRESSPECIFY_3 or '',
                    'COMPLETEDBY': sample.COMPLETEDBY or '',
                    'COMPLETEDDATE': sample.COMPLETEDDATE.isoformat() if sample.COMPLETEDDATE else ''
                }
                request.POST = request.POST.copy()
                request.POST['oldDataJson'] = json.dumps(old_data)

            post_data = request.POST.copy()

            # Xử lý các trường boolean
            for field_name in [
                'STOOL', 'THROATSWAB', 'RECTSWAB', 'BLOOD',
                'KLEBPNEU_1', 'OTHERRES_1', 'KLEBPNEU_2', 'OTHERRES_2', 'KLEBPNEU_3', 'OTHERRES_3'
            ]:
                post_data[field_name] = 'True' if field_name in post_data and post_data[field_name] == 'on' else 'False'

            # Đảm bảo ngày hoàn thành
            if not post_data.get('COMPLETEDDATE') or post_data.get('COMPLETEDDATE') == '':
                post_data['COMPLETEDDATE'] = date.today().strftime('%Y-%m-%d')

            post_data['SAMPLE_TYPE'] = sample_type

            form = ContactSampleCollectionForm(post_data, instance=sample)
            if form.is_valid():
                sample = form.save(commit=False)
                sample.USUBJID = enrollment_contact
                sample.SAMPLE_TYPE = sample_type

                # Nếu SAMPLE = False, xóa các thông tin mẫu
                if not sample.SAMPLE:
                    sample.STOOL = False
                    sample.THROATSWAB = False
                    sample.RECTSWAB = False
                    sample.BLOOD = False
                    sample.CULTRES_1 = 'NoApply'
                    sample.CULTRES_2 = 'NoApply'
                    sample.CULTRES_3 = 'NoApply'
                    sample.KLEBPNEU_1 = False
                    sample.KLEBPNEU_2 = False
                    sample.KLEBPNEU_3 = False
                    sample.OTHERRES_1 = False
                    sample.OTHERRES_2 = False
                    sample.OTHERRES_3 = False
                    sample.OTHERRESSPECIFY_1 = ''
                    sample.OTHERRESSPECIFY_2 = ''
                    sample.OTHERRESSPECIFY_3 = ''

                # Xóa ngày nếu không chọn mẫu tương ứng
                if not sample.STOOL:
                    sample.STOOLDATE = None
                if not sample.THROATSWAB:
                    sample.THROATSWABDATE = None
                if not sample.RECTSWAB:
                    sample.RECTSWABDATE = None
                if not sample.BLOOD or sample.SAMPLE_TYPE != '1':
                    sample.BLOOD = False
                    sample.BLOODDATE = None

                # Lưu người hoàn thành
                if not sample.COMPLETEDBY:
                    sample.COMPLETEDBY = request.user.username

                sample.save()
                
                # Áp dụng audit log sau khi lưu thành công
                if hasattr(request, 'audit_data'):
                    from .....studies.study_43en.models import AuditLog
                    AuditLog.objects.create(
                        user=request.user,
                        model_name='CONTACTSAMPLECOLLECTION',
                        record_id=sample.id,
                        old_data=request.audit_data.get('old_data', '{}'),
                        new_data=request.audit_data.get('new_data', '{}'),
                        change_reason=request.audit_data.get('change_reason', ''),
                        action='UPDATE'
                    )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Cập nhật thông tin mẫu thu thập thành công!'
                })
            else:
                print("Form không hợp lệ!")
                print("POST Data:", post_data)
                print("Form errors:", form.errors)
                return JsonResponse({
                    'success': False,
                    'message': f'Lỗi: {form.errors.as_text()}'
                }, status=400)
        except Exception as e:
            import traceback
            print(f"Error in contact_sample_collection_update: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'message': f'Lỗi khi cập nhật: {str(e)}'
            }, status=500)

@login_required
def contact_sample_collection_view(request, usubjid, sample_type):
    """Xem thông tin mẫu ở chế độ chỉ đọc"""
    screening_contact = get_object_or_404(ScreeningContact, USUBJID=usubjid)
    
    try:
        enrollment_contact = EnrollmentContact.objects.get(USUBJID=screening_contact)
    except EnrollmentContact.DoesNotExist:
        messages.error(request, f'Người tiếp xúc {usubjid} chưa có thông tin ghi danh.')
        return redirect('study_43en:contact_detail', usubjid=usubjid)
    
    sample = get_object_or_404(ContactSampleCollection, USUBJID=enrollment_contact, SAMPLE_TYPE=sample_type)
    
    form = ContactSampleCollectionForm(instance=sample)
    
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True
    
    return render(request, 'studies/study_43en/CRF/contact_sample_collection_form.html', {
        'form': form,
        'sample': sample,
        'screening_contact': screening_contact,
        'enrollment_contact': enrollment_contact,
        'is_view_only': True,
        'usubjid': usubjid,
        'sample_type': sample_type,
    })