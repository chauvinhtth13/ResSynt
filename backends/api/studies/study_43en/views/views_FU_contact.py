
import json
import logging
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext as _

# Import models từ study app
from backends.studies.study_43en.models.contact import (
    EnrollmentContact, 
    ContactFollowUp28, ContactFollowUp90
)

from backends.studies.study_43en.models.audit_log import AuditLog




from backends.studies.study_43en.forms_contact import (
    ContactFollowUp28Form, ContactFollowUp90Form, ContactMedicationHistoryFormSet, ContactMedicationHistory90FormSet
)

# Import utils từ study app
from backends.studies.study_43en.utils.audit_log_cross_db import audit_log_decorator

logger = logging.getLogger(__name__)





@login_required
def contact_followup_28_create(request, usubjid):
    """Tạo mới follow-up ngày 28 cho contact"""
    enrollment_contact = get_object_or_404(EnrollmentContact, USUBJID=usubjid)

    try:
        followup_28 = ContactFollowUp28.objects.get(USUBJID=enrollment_contact)
        return redirect('study_43en:contact_followup_28_update', usubjid=usubjid)
    except ContactFollowUp28.DoesNotExist:
        followup_28 = ContactFollowUp28(USUBJID=enrollment_contact)

    if request.method == 'POST':
        print(f"POST Data: {request.POST}")
        post_data = request.POST.copy()

        # Xử lý các trường boolean
        for field_name in ['HOSP2D', 'DIAL', 'CATHETER', 'SONDE', 'HOMEWOUNDCARE', 'LONGTERMCAREFACILITY', 'MEDICATIONUSE']:
            post_data[field_name] = 'True' if field_name in post_data and post_data[field_name] == 'on' else 'False'

        # Đảm bảo ngày hoàn thành
        if not post_data.get('COMPLETEDDATE') or post_data.get('COMPLETEDDATE') == '':
            post_data['COMPLETEDDATE'] = date.today().strftime('%Y-%m-%d')

        form = ContactFollowUp28Form(post_data, instance=followup_28)
        medication_formset = ContactMedicationHistoryFormSet(post_data, instance=followup_28)

        if form.is_valid() and medication_formset.is_valid():
            followup_28 = form.save(commit=False)
            followup_28.USUBJID = enrollment_contact

            # Lưu người hoàn thành
            if not followup_28.COMPLETEDBY:
                followup_28.COMPLETEDBY = request.user.username

            followup_28.save()
            medication_formset.instance = followup_28
            medication_formset.save()

            messages.success(request, 'Đã tạo mới follow-up 28 ngày thành công!')
            return redirect('study_43en:contact_detail', usubjid=usubjid)
        else:
            print("Form không hợp lệ!")
            print("Form errors:", form.errors)
            print("Formset errors:", medication_formset.errors)
            messages.error(request, f"Lỗi: {form.errors.as_text()} | Formset: {medication_formset.errors}")
    else:
        form = ContactFollowUp28Form(instance=followup_28)
        medication_formset = ContactMedicationHistoryFormSet(instance=followup_28)

    context = {
        'form': form,
        'medication_formset': medication_formset,
        'enrollment_contact': enrollment_contact,
        'is_new': True,
        'followup_type': '28',
        'today': date.today(),
    }
    return render(request, 'studies/study_43en/CRF/contact_followup_form.html', context)

@login_required
@audit_log_decorator(model_name='CONTACTFOLLOWUP28')
def contact_followup_28_update(request, usubjid):
    """Cập nhật follow-up ngày 28 cho contact"""
    enrollment_contact = get_object_or_404(EnrollmentContact, USUBJID=usubjid)
    followup_28 = get_object_or_404(ContactFollowUp28, USUBJID=enrollment_contact)

    if request.method == 'GET':
        form = ContactFollowUp28Form(instance=followup_28)
        medication_formset = ContactMedicationHistoryFormSet(instance=followup_28)
        context = {
            'form': form,
            'medication_formset': medication_formset,
            'enrollment_contact': enrollment_contact,
            'is_new': False,
            'followup_type': '28',
            'today': date.today(),
        }
        return render(request, 'studies/study_43en/CRF/contact_followup_form.html', context)

    elif request.method == 'POST':
        try:
            print(f"POST Data: {request.POST}")

            # Lấy old_data từ request hoặc model
            old_data = request.POST.get('oldDataJson', '')
            if not old_data:
                old_data = {
                    'ASSESSED': followup_28.ASSESSED or '',
                    'ASSESSDATE': followup_28.ASSESSDATE.isoformat() if followup_28.ASSESSDATE else '',
                    'HOSP2D': str(followup_28.HOSP2D),
                    'DIAL': str(followup_28.DIAL),
                    'CATHETER': str(followup_28.CATHETER),
                    'SONDE': str(followup_28.SONDE),
                    'HOMEWOUNDCARE': str(followup_28.HOMEWOUNDCARE),
                    'LONGTERMCAREFACILITY': str(followup_28.LONGTERMCAREFACILITY),
                    'MEDICATIONUSE': str(followup_28.MEDICATIONUSE),
                    'COMPLETEDBY': followup_28.COMPLETEDBY or '',
                    'COMPLETEDDATE': followup_28.COMPLETEDDATE.isoformat() if followup_28.COMPLETEDDATE else '',
                }
                request.POST = request.POST.copy()
                request.POST['oldDataJson'] = json.dumps(old_data)

            post_data = request.POST.copy()

            # Xử lý các trường boolean
            for field_name in ['HOSP2D', 'DIAL', 'CATHETER', 'SONDE', 'HOMEWOUNDCARE', 'LONGTERMCAREFACILITY', 'MEDICATIONUSE']:
                post_data[field_name] = 'True' if field_name in post_data and post_data[field_name] == 'on' else 'False'

            # Đảm bảo ngày hoàn thành
            if not post_data.get('COMPLETEDDATE') or post_data.get('COMPLETEDDATE') == '':
                post_data['COMPLETEDDATE'] = date.today().strftime('%Y-%m-%d')

            form = ContactFollowUp28Form(post_data, instance=followup_28)
            medication_formset = ContactMedicationHistoryFormSet(post_data, instance=followup_28)

            if form.is_valid() and medication_formset.is_valid():
                followup_28 = form.save(commit=False)
                followup_28.USUBJID = enrollment_contact

                # Lưu người hoàn thành
                if not followup_28.COMPLETEDBY:
                    followup_28.COMPLETEDBY = request.user.username

                followup_28.save()
                medication_formset.instance = followup_28
                medication_formset.save()

                # Áp dụng audit log
                if hasattr(request, 'audit_data'):
                    AuditLog.objects.create(
                        user=request.user,
                        model_name='CONTACTFOLLOWUP28',
                        record_id=followup_28.USUBJID_id,
                        old_data=request.audit_data.get('old_data', '{}'),
                        new_data=request.audit_data.get('new_data', '{}'),
                        change_reason=request.audit_data.get('change_reason', ''),
                        action='UPDATE'
                    )

                return JsonResponse({
                    'success': True,
                    'message': 'Cập nhật follow-up 28 ngày thành công!'
                })
            else:
                print("Form không hợp lệ!")
                print("Form errors:", form.errors)
                print("Formset errors:", medication_formset.errors)
                return JsonResponse({
                    'success': False,
                    'message': f'Lỗi: {form.errors.as_text()} | Formset: {medication_formset.errors}'
                }, status=400)
        except Exception as e:
            import traceback
            print(f"Error in contact_followup_28_update: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'message': f'Lỗi khi cập nhật: {str(e)}'
            }, status=500)

@login_required
def contact_followup_28_view(request, usubjid):
    """Xem follow-up ngày 28 cho contact ở chế độ chỉ đọc"""
    enrollment_contact = get_object_or_404(EnrollmentContact, USUBJID=usubjid)
    followup_28 = get_object_or_404(ContactFollowUp28, USUBJID=enrollment_contact)

    form = ContactFollowUp28Form(instance=followup_28)
    medication_formset = ContactMedicationHistoryFormSet(instance=followup_28)

    # Disable tất cả các field để chỉ có thể xem
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True
    for formset_form in medication_formset.forms:
        for field in formset_form.fields.values():
            field.widget.attrs['readonly'] = True
            field.widget.attrs['disabled'] = True

    context = {
        'form': form,
        'medication_formset': medication_formset,
        'enrollment_contact': enrollment_contact,
        'is_view_only': True,
        'followup_type': '28',
    }
    return render(request, 'studies/study_43en/CRF/contact_followup_form.html', context)

@login_required
def contact_followup_90_create(request, usubjid):
    """Tạo mới follow-up ngày 90 cho contact"""
    enrollment_contact = get_object_or_404(EnrollmentContact, USUBJID=usubjid)

    try:
        followup_90 = ContactFollowUp90.objects.get(USUBJID=enrollment_contact)
        return redirect('study_43en:contact_followup_90_update', usubjid=usubjid)
    except ContactFollowUp90.DoesNotExist:
        followup_90 = ContactFollowUp90(USUBJID=enrollment_contact)

    if request.method == 'POST':
        print(f"POST Data: {request.POST}")
        post_data = request.POST.copy()

        # Xử lý các trường boolean
        for field_name in ['HOSP2D', 'DIAL', 'CATHETER', 'SONDE', 'HOMEWOUNDCARE', 'LONGTERMCAREFACILITY', 'MEDICATIONUSE']:
            post_data[field_name] = 'True' if field_name in post_data and post_data[field_name] == 'on' else 'False'

        # Đảm bảo ngày hoàn thành
        if not post_data.get('COMPLETEDDATE') or post_data.get('COMPLETEDDATE') == '':
            post_data['COMPLETEDDATE'] = date.today().strftime('%Y-%m-%d')

        form = ContactFollowUp90Form(post_data, instance=followup_90)
        medication_formset = ContactMedicationHistory90FormSet(post_data, instance=followup_90)

        if form.is_valid() and medication_formset.is_valid():
            followup_90 = form.save(commit=False)
            followup_90.USUBJID = enrollment_contact

            # Lưu người hoàn thành
            if not followup_90.COMPLETEDBY:
                followup_90.COMPLETEDBY = request.user.username

            followup_90.save()
            medication_formset.instance = followup_90
            medication_formset.save()

            messages.success(request, 'Đã tạo mới follow-up 90 ngày thành công!')
            return redirect('study_43en:contact_detail', usubjid=usubjid)
        else:
            print("Form không hợp lệ!")
            print("Form errors:", form.errors)
            print("Formset errors:", medication_formset.errors)
            messages.error(request, f"Lỗi: {form.errors.as_text()} | Formset: {medication_formset.errors}")
    else:
        form = ContactFollowUp90Form(instance=followup_90)
        medication_formset = ContactMedicationHistory90FormSet(instance=followup_90)

    context = {
        'form': form,
        'medication_formset': medication_formset,
        'enrollment_contact': enrollment_contact,
        'is_new': True,
        'followup_type': '90',
        'today': date.today(),
    }
    return render(request, 'studies/study_43en/CRF/contact_followup_90_form.html', context)

@login_required
@audit_log_decorator(model_name='CONTACTFOLLOWUP90')
def contact_followup_90_update(request, usubjid):
    """Cập nhật follow-up ngày 90 cho contact"""
    enrollment_contact = get_object_or_404(EnrollmentContact, USUBJID=usubjid)
    followup_90 = get_object_or_404(ContactFollowUp90, USUBJID=enrollment_contact)

    if request.method == 'GET':
        form = ContactFollowUp90Form(instance=followup_90)
        medication_formset = ContactMedicationHistory90FormSet(instance=followup_90)
        context = {
            'form': form,
            'medication_formset': medication_formset,
            'enrollment_contact': enrollment_contact,
            'is_new': False,
            'followup_type': '90',
            'today': date.today(),
        }
        return render(request, 'studies/study_43en/CRF/contact_followup_90_form.html', context)

    elif request.method == 'POST':
        try:
            print(f"POST Data: {request.POST}")

            # Lấy old_data từ request hoặc model
            old_data = request.POST.get('oldDataJson', '')
            if not old_data:
                old_data = {
                    'ASSESSED': followup_90.ASSESSED or '',
                    'ASSESSDATE': followup_90.ASSESSDATE.isoformat() if followup_90.ASSESSDATE else '',
                    'HOSP2D': str(followup_90.HOSP2D),
                    'DIAL': str(followup_90.DIAL),
                    'CATHETER': str(followup_90.CATHETER),
                    'SONDE': str(followup_90.SONDE),
                    'HOMEWOUNDCARE': str(followup_90.HOMEWOUNDCARE),
                    'LONGTERMCAREFACILITY': str(followup_90.LONGTERMCAREFACILITY),
                    'MEDICATIONUSE': str(followup_90.MEDICATIONUSE),
                    'COMPLETEDBY': followup_90.COMPLETEDBY or '',
                    'COMPLETEDDATE': followup_90.COMPLETEDDATE.isoformat() if followup_90.COMPLETEDDATE else '',
                }
                request.POST = request.POST.copy()
                request.POST['oldDataJson'] = json.dumps(old_data)

            post_data = request.POST.copy()

            # Xử lý các trường boolean
            for field_name in ['HOSP2D', 'DIAL', 'CATHETER', 'SONDE', 'HOMEWOUNDCARE', 'LONGTERMCAREFACILITY', 'MEDICATIONUSE']:
                post_data[field_name] = 'True' if field_name in post_data and post_data[field_name] == 'on' else 'False'

            # Đảm bảo ngày hoàn thành
            if not post_data.get('COMPLETEDDATE') or post_data.get('COMPLETEDDATE') == '':
                post_data['COMPLETEDDATE'] = date.today().strftime('%Y-%m-%d')

            form = ContactFollowUp90Form(post_data, instance=followup_90)
            medication_formset = ContactMedicationHistory90FormSet(post_data, instance=followup_90)

            if form.is_valid() and medication_formset.is_valid():
                followup_90 = form.save(commit=False)
                followup_90.USUBJID = enrollment_contact

                # Lưu người hoàn thành
                if not followup_90.COMPLETEDBY:
                    followup_90.COMPLETEDBY = request.user.username

                followup_90.save()
                medication_formset.instance = followup_90
                medication_formset.save()

                # Áp dụng audit log
                if hasattr(request, 'audit_data'):
                    AuditLog.objects.create(
                        user=request.user,
                        model_name='CONTACTFOLLOWUP90',
                        record_id=followup_90.USUBJID_id,
                        old_data=request.audit_data.get('old_data', '{}'),
                        new_data=request.audit_data.get('new_data', '{}'),
                        change_reason=request.audit_data.get('change_reason', ''),
                        action='UPDATE'
                    )

                return JsonResponse({
                    'success': True,
                    'message': 'Cập nhật follow-up 90 ngày thành công!'
                })
            else:
                print("Form không hợp lệ!")
                print("Form errors:", form.errors)
                print("Formset errors:", medication_formset.errors)
                return JsonResponse({
                    'success': False,
                    'message': f'Lỗi: {form.errors.as_text()} | Formset: {medication_formset.errors}'
                }, status=400)
        except Exception as e:
            import traceback
            print(f"Error in contact_followup_90_update: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'message': f'Lỗi khi cập nhật: {str(e)}'
            }, status=500)

@login_required
def contact_followup_90_view(request, usubjid):
    """Xem follow-up ngày 90 cho contact ở chế độ chỉ đọc"""
    enrollment_contact = get_object_or_404(EnrollmentContact, USUBJID=usubjid)
    followup_90 = get_object_or_404(ContactFollowUp90, USUBJID=enrollment_contact)

    form = ContactFollowUp90Form(instance=followup_90)
    medication_formset = ContactMedicationHistory90FormSet(instance=followup_90)

    # Disable tất cả các field để chỉ có thể xem
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True
    for formset_form in medication_formset.forms:
        for field in formset_form.fields.values():
            field.widget.attrs['readonly'] = True
            field.widget.attrs['disabled'] = True

    context = {
        'form': form,
        'medication_formset': medication_formset,
        'enrollment_contact': enrollment_contact,
        'is_view_only': True,
        'followup_type': '90',
    }
    return render(request, 'studies/study_43en/CRF/contact_followup_90_form.html', context)