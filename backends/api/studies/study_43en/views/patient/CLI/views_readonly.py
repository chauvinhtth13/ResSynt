# backends/studies/study_43en/views/patient/CLI/views_readonly.py
"""
Clinical Case Read-only View

View-only access to clinical data
"""
import logging
from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# Import audit decorator
from backends.studies.study_43en.utils.audit.decorators import audit_log

# Import forms
from backends.studies.study_43en.forms.patient.CLI import (
    ClinicalCaseForm,
    HistorySymptomForm,
    Symptom72HForm,
    PriorAntibioticFormSet,
    InitialAntibioticFormSet,
    MainAntibioticFormSet,
    VasoIDrugFormSet,
    HospiProcessFormSet,
    AEHospEventFormSet,
    ImproveSymptFormSet,
)

# Import utilities
from backends.studies.study_43en.utils.permission_decorators import (
    require_crf_view,
    check_instance_site_access,
)

# Import helpers
from .helpers import (
    get_clinical_with_related,
    get_or_create_symptom_records,
    make_form_readonly,
    make_formset_readonly,
)

logger = logging.getLogger(__name__)


@login_required
@require_crf_view('cli_case', redirect_to='study_43en:patient_list')
@audit_log(model_name='CLINICALCASE', get_patient_id_from='usubjid')
def clinical_case_view(request, usubjid):
    """
    View clinical case (read-only)
    
    Permission: view_clinicalcase
    """
    logger.info(f"=== CLINICAL VIEW (READ-ONLY) ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get clinical with related data
    screening_case, enrollment_case, clinical_case = get_clinical_with_related(request,usubjid)
    
    if not clinical_case:
        messages.error(request, f'Bệnh nhân {usubjid} chưa có thông tin lâm sàng.')
        return redirect('study_43en:patient_detail', usubjid=usubjid)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        clinical_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    # Get symptom records
    history_symptom, symptom_72h = get_or_create_symptom_records(clinical_case)
    
    # Create read-only forms
    clinical_form = ClinicalCaseForm(instance=clinical_case)
    history_symptom_form = HistorySymptomForm(instance=history_symptom)
    symptom_72h_form = Symptom72HForm(instance=symptom_72h)
    
    # Create read-only formsets
    prior_antibiotic_formset = PriorAntibioticFormSet(
        prefix='priorantibiotic_set', instance=clinical_case
    )
    initial_antibiotic_formset = InitialAntibioticFormSet(
        prefix='initialantibiotic_set', instance=clinical_case
    )
    main_antibiotic_formset = MainAntibioticFormSet(
        prefix='mainantibiotic_set', instance=clinical_case
    )
    vaso_drug_formset = VasoIDrugFormSet(
        prefix='vasoidrug_set', instance=clinical_case
    )
    hospi_process_formset = HospiProcessFormSet(
        prefix='hospiprocess_set', instance=clinical_case
    )
    ae_hosp_event_formset = AEHospEventFormSet(
        prefix='aehospevent_set', instance=clinical_case
    )
    improve_sympt_formset = ImproveSymptFormSet(
        prefix='improvesympt_set', instance=clinical_case
    )
    
    # Make everything readonly
    make_form_readonly(clinical_form)
    make_form_readonly(history_symptom_form)
    make_form_readonly(symptom_72h_form)
    make_formset_readonly(prior_antibiotic_formset)
    make_formset_readonly(initial_antibiotic_formset)
    make_formset_readonly(main_antibiotic_formset)
    make_formset_readonly(vaso_drug_formset)
    make_formset_readonly(hospi_process_formset)
    make_formset_readonly(ae_hosp_event_formset)
    make_formset_readonly(improve_sympt_formset)
    
    context = {
        'clinical_form': clinical_form,  # FIX: Template expects 'clinical_form' not 'form'
        'history_symptom_form': history_symptom_form,
        'symptom_72h_form': symptom_72h_form,
        'prior_antibiotic_formset': prior_antibiotic_formset,
        'initial_antibiotic_formset': initial_antibiotic_formset,
        'main_antibiotic_formset': main_antibiotic_formset,
        'vaso_drug_formset': vaso_drug_formset,
        'hospi_process_formset': hospi_process_formset,
        'ae_hosp_event_formset': ae_hosp_event_formset,
        'improve_sympt_formset': improve_sympt_formset,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'clinical_case': clinical_case,
        'is_create': False,
        'is_readonly': True,
        'selected_site_id': screening_case.SITEID,
        'today': date.today(),
    }
    
    return render(request, 'studies/study_43en/CRF/patient/clinical_form.html', context)