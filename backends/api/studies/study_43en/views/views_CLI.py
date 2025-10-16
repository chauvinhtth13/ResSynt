import logging
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext as _

# Import models từ study app
from backends.studies.study_43en.models.patient import (
    ScreeningCase, EnrollmentCase, ClinicalCase,

)


from backends.studies.study_43en.forms_patient import (
    ClinicalCaseForm,
    PriorAntibioticFormSet, InitialAntibioticFormSet, 
    MainAntibioticFormSet, VasoIDrugFormSet,
    HospiProcessFormSet,
    AEHospEventFormSet, ImproveSymptFormSet, 


)



# Import utils từ study app
from backends.studies.study_43en.utils.audit_log_utils import (
    safe_json_loads
)
from backends.studies.study_43en.utils.audit_log_cross_db import audit_log_decorator
from backends.studies.study_43en.utils import get_site_filtered_object_or_404

logger = logging.getLogger(__name__)





@login_required
@audit_log_decorator(model_name='CLINICALCASE')
def clinical_case_update(request, usubjid):
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    clinical_case = get_object_or_404(ClinicalCase, USUBJID=enrollment_case)
    
    # Lấy audit data và loại bỏ USUBJID
    old_data = safe_json_loads(request.POST.get('oldDataJson', '{}'))
    new_data = safe_json_loads(request.POST.get('newDataJson', '{}'))
    reasons_json = safe_json_loads(request.POST.get('reasonsJson', '{}'))
    change_reason = request.POST.get('change_reason', '')
    
    # Loại bỏ các trường USUBJID khỏi old_data và new_data
    old_data = {k: v for k, v in old_data.items() if 'USUBJID' not in k.upper()}
    new_data = {k: v for k, v in new_data.items() if 'USUBJID' not in k.upper()}
    
    print("DEBUG - clinical_case_update - old_data:", old_data)
    print("DEBUG - clinical_case_update - new_data:", new_data)
    print("DEBUG - clinical_case_update - reasons_json:", reasons_json)
    print("DEBUG - clinical_case_update - change_reason:", change_reason)
    
    request.audit_data = {
        'old_data': old_data,
        'new_data': new_data,
        'reasons_json': reasons_json,
        'reason': change_reason
    }

    if request.method == 'POST':
        form = ClinicalCaseForm(request.POST, instance=clinical_case)
        prior_antibiotic_formset = PriorAntibioticFormSet(
            request.POST, 
            prefix='priorantibiotic_set',
            instance=enrollment_case
        )
        initial_antibiotic_formset = InitialAntibioticFormSet(
            request.POST, 
            prefix='initialantibiotic_set',
            instance=enrollment_case
        )
        main_antibiotic_formset = MainAntibioticFormSet(
            request.POST, 
            prefix='mainantibiotic_set',
            instance=enrollment_case
        )
        vaso_drug_formset = VasoIDrugFormSet(
            request.POST,
            prefix='vasoidrug_set',
            instance=enrollment_case
        )
        hospiprocess_formset = HospiProcessFormSet(
            request.POST, 
            prefix='hospiprocess_formset', 
            instance=enrollment_case
        )
        aehospevent_formset = AEHospEventFormSet(
            request.POST,
            prefix='aehospevent_set',
            instance=enrollment_case
        )
        improvesympt_formset = ImproveSymptFormSet(
            request.POST,
            prefix='improvesympt_set',
            instance=enrollment_case
        )

        formsets_valid = (
            prior_antibiotic_formset.is_valid() and
            initial_antibiotic_formset.is_valid() and
            main_antibiotic_formset.is_valid() and
            vaso_drug_formset.is_valid() and
            aehospevent_formset.is_valid() and
            improvesympt_formset.is_valid() and
            hospiprocess_formset.is_valid()
        )
        
        if form.is_valid() and formsets_valid:
            clinical_case = form.save()
            prior_antibiotic_formset.save()
            initial_antibiotic_formset.save()
            main_antibiotic_formset.save()
            vaso_drug_formset.save()
            hospiprocess_formset.save()
            aehospevent_formset.save()
            improvesympt_formset.save()
            
            messages.success(request, f'Đã cập nhật thông tin lâm sàng cho bệnh nhân {usubjid} thành công.')
            return redirect('study_43en:patient_detail', usubjid=usubjid)
    else:
        form = ClinicalCaseForm(instance=clinical_case)
        prior_antibiotic_formset = PriorAntibioticFormSet(
            prefix='priorantibiotic_set',
            instance=enrollment_case
        )
        initial_antibiotic_formset = InitialAntibioticFormSet(
            prefix='initialantibiotic_set',
            instance=enrollment_case
        )
        main_antibiotic_formset = MainAntibioticFormSet(
            prefix='mainantibiotic_set',
            instance=enrollment_case
        )
        vaso_drug_formset = VasoIDrugFormSet(
            prefix='vasoidrug_set',
            instance=enrollment_case
        )
        hospiprocess_formset = HospiProcessFormSet(
            prefix='hospiprocess_formset',
            instance=enrollment_case
        )
        aehospevent_formset = AEHospEventFormSet(
            prefix='aehospevent_set',
            instance=enrollment_case
        )
        improvesympt_formset = ImproveSymptFormSet(
            prefix='improvesympt_set',
            instance=enrollment_case
        )
    
    return render(request, 'studies/study_43en/CRF/clinical_case_form.html', {
        'form': form,
        'prior_antibiotic_formset': prior_antibiotic_formset,
        'initial_antibiotic_formset': initial_antibiotic_formset,
        'main_antibiotic_formset': main_antibiotic_formset,
        'hospiprocess_formset': hospiprocess_formset,
        'vaso_drug_formset': vaso_drug_formset,
        'aehospevent_formset': aehospevent_formset,
        'improvesympt_formset': improvesympt_formset,
        'clinical_case': clinical_case,
        'enrollment_case': enrollment_case,
        'is_create': False,
        'today': date.today(),
    })

@login_required
@audit_log_decorator(model_name='CLINICALCASE')
def clinical_case_create(request, usubjid):

    
    # Lấy site_id từ session, mặc định là 'all'
    site_id = request.session.get('selected_site_id', 'all')
    
    # Sử dụng hàm tiện ích
    screening_case = get_site_filtered_object_or_404(ScreeningCase, site_id, USUBJID=usubjid)
    enrollment_case = get_site_filtered_object_or_404(EnrollmentCase, site_id, USUBJID=screening_case)
    
    try:
        # Sử dụng filter_by_site hoặc objects tùy thuộc vào site_id
        if site_id and site_id != 'all':
            clinical_case = ClinicalCase.site_objects.filter_by_site(site_id).get(USUBJID=enrollment_case)
        else:
            clinical_case = ClinicalCase.objects.get(USUBJID=enrollment_case)
            
        messages.warning(request, f'Bệnh nhân {usubjid} đã có thông tin lâm sàng. Chuyển tới trang cập nhật.')
        return redirect('clinical_case_update', usubjid=usubjid)
    except ClinicalCase.DoesNotExist:
        if request.method == 'POST':
            form = ClinicalCaseForm(request.POST)
            prior_antibiotic_formset = PriorAntibioticFormSet(request.POST, prefix='priorantibiotic_set')
            initial_antibiotic_formset = InitialAntibioticFormSet(request.POST, prefix='initialantibiotic_set')
            main_antibiotic_formset = MainAntibioticFormSet(request.POST, prefix='mainantibiotic_set')
            vaso_drug_formset = VasoIDrugFormSet(request.POST, prefix='vasoidrug_set')
            hospiprocess_formset = HospiProcessFormSet(request.POST, prefix='hospiprocess_formset')
            aehospevent_formset = AEHospEventFormSet(request.POST, prefix='aehospevent_set')
            improvesympt_formset = ImproveSymptFormSet(request.POST, prefix='improvesympt_set')
            
            formsets_valid = (
                prior_antibiotic_formset.is_valid() and
                initial_antibiotic_formset.is_valid() and
                main_antibiotic_formset.is_valid() and
                vaso_drug_formset.is_valid() and
                hospiprocess_formset.is_valid() and
                aehospevent_formset.is_valid() and
                improvesympt_formset.is_valid()
            )
            
            if form.is_valid() and formsets_valid:
                clinical_case = form.save(commit=False)            
                clinical_case.USUBJID = enrollment_case
                clinical_case.save()
                
                prior_antibiotic_instances = prior_antibiotic_formset.save(commit=False)
                for instance in prior_antibiotic_instances:
                    instance.USUBJID = enrollment_case
                    instance.save()
                
                initial_antibiotic_instances = initial_antibiotic_formset.save(commit=False)
                for instance in initial_antibiotic_instances:
                    instance.USUBJID = enrollment_case
                    instance.save()
                
                main_antibiotic_instances = main_antibiotic_formset.save(commit=False)
                for instance in main_antibiotic_instances:
                    instance.USUBJID = enrollment_case
                    instance.save()
                
                vaso_drug_instances = vaso_drug_formset.save(commit=False)
                for instance in vaso_drug_instances:
                    instance.USUBJID = enrollment_case
                    instance.save()

                hospiprocess_instances = hospiprocess_formset.save(commit=False) 
                for instance in hospiprocess_instances:  
                    instance.USUBJID = enrollment_case  
                    instance.save()

                aehospevent_instances = aehospevent_formset.save(commit=False)
                for instance in aehospevent_instances:
                    instance.USUBJID = enrollment_case
                    instance.save()
                
                improvesympt_instances = improvesympt_formset.save(commit=False)
                for instance in improvesympt_instances:
                    instance.USUBJID = enrollment_case
                    instance.save()
                
                prior_antibiotic_formset.save()
                initial_antibiotic_formset.save()
                main_antibiotic_formset.save()
                vaso_drug_formset.save()
                hospiprocess_formset.save()
                aehospevent_formset.save()
                improvesympt_formset.save()
                
                messages.success(request, f'Đã tạo thông tin lâm sàng cho bệnh nhân {usubjid} thành công.')
                return redirect('laboratory_test_create', usubjid=usubjid)
        else:
            initial_data = {
                'STUDYID': '43EN',
                'SITEID': enrollment_case.USUBJID.SITEID,
                'SUBJID': enrollment_case.USUBJID.SUBJID,
                'INITIAL': enrollment_case.USUBJID.INITIAL,
                'COMPLETEDBY': enrollment_case.COMPLETEDBY,
                'COMPLETEDDATE': date.today(),
            }        
            form = ClinicalCaseForm(initial=initial_data)
            prior_antibiotic_formset = PriorAntibioticFormSet(prefix='priorantibiotic_set')
            initial_antibiotic_formset = InitialAntibioticFormSet(prefix='initialantibiotic_set')
            main_antibiotic_formset = MainAntibioticFormSet(prefix='mainantibiotic_set')
            vaso_drug_formset = VasoIDrugFormSet(prefix='vasoidrug_set')
            hospiprocess_formset = HospiProcessFormSet(prefix='hospiprocess_formset')
            aehospevent_formset = AEHospEventFormSet(prefix='aehospevent_set')
            improvesympt_formset = ImproveSymptFormSet(prefix='improvesympt_set')
    
    return render(request, 'studies/study_43en/CRF/clinical_case_form.html', {
        'form': form,
        'prior_antibiotic_formset': prior_antibiotic_formset,
        'initial_antibiotic_formset': initial_antibiotic_formset,
        'main_antibiotic_formset': main_antibiotic_formset,
        'hospiprocess_formset': hospiprocess_formset,
        'vaso_drug_formset': vaso_drug_formset,
        'aehospevent_formset': aehospevent_formset,
        'improvesympt_formset': improvesympt_formset,
        'clinical_case': {'USUBJID_id': enrollment_case.USUBJID},
        'enrollment_case': enrollment_case,
        'is_create': True,
        'today': date.today(),
    })

@login_required
@audit_log_decorator(model_name='CLINICALCASE')
def clinical_case_detail(request, usubjid):
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case) 
    clinical_case = get_object_or_404(ClinicalCase, USUBJID=enrollment_case)
    
    return render(request, 'studies/study_43en/CRF/clinical_case_detail.html', {
        'clinical_case': clinical_case,
        'enrollment_case': enrollment_case,
    })

@login_required
@audit_log_decorator(model_name='CLINICALCASE')
def clinical_case_delete(request, usubjid):
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    clinical_case = get_object_or_404(ClinicalCase, USUBJID=enrollment_case)
    
    if request.method == 'POST':
        clinical_case.delete()
        messages.success(request, f'Đã xóa thông tin lâm sàng của bệnh nhân {usubjid} thành công.')
        return redirect('study_43en:patient_detail', usubjid=usubjid)
    
    return render(request, 'studies/study_43en/CRF/clinical_case_confirm_delete.html', {
        'clinical_case': clinical_case,
        'enrollment_case': enrollment_case,
    })

@login_required
@audit_log_decorator(model_name='CLINICALCASE')
def clinical_form(request, usubjid, read_only=False):
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    
    try:
        clinical_case = ClinicalCase.objects.get(USUBJID=enrollment_case)
        has_clinical = True
    except ClinicalCase.DoesNotExist:
        clinical_case = None
        has_clinical = False
    
    # Lấy audit data và loại bỏ USUBJID
    old_data = safe_json_loads(request.POST.get('oldDataJson', '{}'))
    new_data = safe_json_loads(request.POST.get('newDataJson', '{}'))
    reasons_json = safe_json_loads(request.POST.get('reasonsJson', '{}'))
    change_reason = request.POST.get('change_reason', '')
    
    # Loại bỏ các trường USUBJID khỏi old_data và new_data
    old_data = {k: v for k, v in old_data.items() if 'USUBJID' not in k.upper()}
    new_data = {k: v for k, v in new_data.items() if 'USUBJID' not in k.upper()}
    
    print("DEBUG - clinical_form - old_data:", old_data)
    print("DEBUG - clinical_form - new_data:", new_data)
    print("DEBUG - clinical_form - reasons_json:", reasons_json)
    print("DEBUG - clinical_form - change_reason:", change_reason)
    
    request.audit_data = {
        'old_data': old_data,
        'new_data': new_data,
        'reasons_json': reasons_json,
        'reason': change_reason
    }

    prior_antibiotic_formset = PriorAntibioticFormSet(
        prefix='priorantibiotic_set',
        instance=enrollment_case if clinical_case else None
    )
    initial_antibiotic_formset = InitialAntibioticFormSet(
        prefix='initialantibiotic_set',
        instance=enrollment_case if clinical_case else None
    )
    main_antibiotic_formset = MainAntibioticFormSet(
        prefix='mainantibiotic_set',
        instance=enrollment_case if clinical_case else None
    )
    vaso_drug_formset = VasoIDrugFormSet(
        prefix='vasoidrug_set',
        instance=enrollment_case if clinical_case else None
    )
    hospiprocess_formset = HospiProcessFormSet(
        prefix='hospiprocess_formset',
        instance=enrollment_case if clinical_case else None
    )
    aehospevent_formset = AEHospEventFormSet(
        prefix='aehospevent_set',
        instance=enrollment_case if clinical_case else None
    )
    improvesympt_formset = ImproveSymptFormSet(
        prefix='improvesympt_set',
        instance=enrollment_case if clinical_case else None
    )
    
    if request.method == 'POST' and not read_only:
        if clinical_case:
            form = ClinicalCaseForm(request.POST, instance=clinical_case)
            prior_antibiotic_formset = PriorAntibioticFormSet(
                request.POST,
                prefix='priorantibiotic_set',
                instance=enrollment_case
            )
            initial_antibiotic_formset = InitialAntibioticFormSet(
                request.POST,
                prefix='initialantibiotic_set',
                instance=enrollment_case
            )
            main_antibiotic_formset = MainAntibioticFormSet(
                request.POST,
                prefix='mainantibiotic_set',
                instance=enrollment_case
            )
            vaso_drug_formset = VasoIDrugFormSet(
                request.POST,
                prefix='vasoidrug_set',
                instance=enrollment_case
            )
            hospiprocess_formset = HospiProcessFormSet(
                request.POST, 
                prefix='hospiprocess_formset', 
                instance=enrollment_case
            )
            aehospevent_formset = AEHospEventFormSet(
                request.POST,
                prefix='aehospevent_set',
                instance=enrollment_case
            )
            improvesympt_formset = ImproveSymptFormSet(
                request.POST,
                prefix='improvesympt_set',
                instance=enrollment_case
            )
        else:
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
            hospiprocess_formset = HospiProcessFormSet(
                request.POST,
                prefix='hospiprocess_formset'
            )
            aehospevent_formset = AEHospEventFormSet(
                request.POST,
                prefix='aehospevent_set'
            )
            improvesympt_formset = ImproveSymptFormSet(
                request.POST,
                prefix='improvesympt_set'
            )

        formsets_valid = (
            prior_antibiotic_formset.is_valid() and
            initial_antibiotic_formset.is_valid() and
            main_antibiotic_formset.is_valid() and
            vaso_drug_formset.is_valid() and
            hospiprocess_formset.is_valid() and
            aehospevent_formset.is_valid() and
            improvesympt_formset.is_valid()
        )
        
        if form.is_valid() and formsets_valid:
            new_clinical_case = form.save(commit=False)
            if not clinical_case:
                new_clinical_case.USUBJID = enrollment_case
            new_clinical_case.save()
            
            prior_antibiotic_instances = prior_antibiotic_formset.save(commit=False)
            for instance in prior_antibiotic_instances:
                instance.USUBJID = enrollment_case
                instance.save()
            prior_antibiotic_formset.save_m2m()
            
            initial_antibiotic_instances = initial_antibiotic_formset.save(commit=False)
            for instance in initial_antibiotic_instances:
                instance.USUBJID = enrollment_case
                instance.save()
            initial_antibiotic_formset.save_m2m()
            
            main_antibiotic_instances = main_antibiotic_formset.save(commit=False)
            for instance in main_antibiotic_instances:
                instance.USUBJID = enrollment_case
                instance.save()
            main_antibiotic_formset.save_m2m()
            
            vaso_drug_instances = vaso_drug_formset.save(commit=False)
            for instance in vaso_drug_instances:
                instance.USUBJID = enrollment_case
                instance.save()
            vaso_drug_formset.save_m2m()

            hospiprocess_instances = hospiprocess_formset.save(commit=False)
            for instance in hospiprocess_instances:
                instance.USUBJID = enrollment_case
                instance.save()
            hospiprocess_formset.save_m2m()

            aehospevent_instances = aehospevent_formset.save(commit=False)
            for instance in aehospevent_instances:
                instance.USUBJID = enrollment_case
                instance.save()
            aehospevent_formset.save_m2m()
            
            improvesympt_instances = improvesympt_formset.save(commit=False)
            for instance in improvesympt_instances:
                instance.USUBJID = enrollment_case
                instance.save()
            improvesympt_formset.save_m2m()
            
            messages.success(request, f'Đã lưu thông tin lâm sàng cho bệnh nhân {usubjid} thành công.')
            return redirect('study_43en:patient_detail', usubjid=usubjid)
    else:
        if clinical_case:
            form = ClinicalCaseForm(instance=clinical_case)
        else:
            initial_data = {
                'STUDYID': '43EN',
                'SITEID': enrollment_case.USUBJID.SITEID,
                'SUBJID': enrollment_case.USUBJID.SUBJID,
                'INITIAL': enrollment_case.USUBJID.INITIAL,
                'COMPLETEDBY': enrollment_case.COMPLETEDBY if enrollment_case.COMPLETEDBY else request.user.username,
                'COMPLETEDDATE': date.today(),
            }
            form = ClinicalCaseForm(initial=initial_data)
    
    if read_only:
        for field in form.fields.values():
            field.widget.attrs['readonly'] = True
            field.widget.attrs['disabled'] = True
        
        for formset in [prior_antibiotic_formset, initial_antibiotic_formset, 
                       main_antibiotic_formset, vaso_drug_formset, hospiprocess_formset,
                       aehospevent_formset, improvesympt_formset]:
            for form_instance in formset.forms:
                for field in form_instance.fields.values():
                    field.widget.attrs['readonly'] = True
                    field.widget.attrs['disabled'] = True
    
    return render(request, 'studies/study_43en/CRF/clinical_form.html', {
        'enrollment_case': enrollment_case,
        'clinical_case': clinical_case,
        'has_clinical': has_clinical,
        'form': form,
        'prior_antibiotic_formset': prior_antibiotic_formset,
        'initial_antibiotic_formset': initial_antibiotic_formset,
        'main_antibiotic_formset': main_antibiotic_formset,
        'vaso_drug_formset': vaso_drug_formset,
        'aehospevent_formset': aehospevent_formset,
        'improvesympt_formset': improvesympt_formset,
        'hospiprocess_formset': hospiprocess_formset,
        'is_readonly': read_only,
        'today': date.today(),
    })

@login_required
@audit_log_decorator(model_name='CLINICALCASE')
def clinical_form_view(request, usubjid):
    if request.method == 'POST':
        messages.error(request, "Không thể submit trong chế độ xem")
        return redirect('study_43en:clinical_form_view', usubjid=usubjid)
    return clinical_form(request, usubjid, read_only=True)