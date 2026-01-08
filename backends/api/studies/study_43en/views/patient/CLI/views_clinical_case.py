# backends/studies/study_43en/views/patient/CLI/views_clinical_case.py
"""
Clinical Case CRUD Views - REFACTORED with Universal Audit System

Combines CREATE and UPDATE views with proper audit trail
"""
import logging
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

# Import models
from backends.studies.study_43en.models.patient import (
    SCR_CASE,
    ENR_CASE,
)

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
from backends.audit_log.utils.decorators import audit_log
from backends.audit_log.utils.processors import process_complex_update
from backends.audit_log.utils.permission_decorators import (
    require_crf_add,
    require_crf_change,
    check_instance_site_access,
)

# Import helpers
from .helpers import (
    get_clinical_with_related,
    get_or_create_symptom_records,
    save_clinical_and_related,
    log_all_form_errors,
)

logger = logging.getLogger(__name__)


# ==========================================
# CREATE VIEW (NO AUDIT)
# ==========================================

@login_required
@require_crf_add('cli_case', redirect_to='study_43en:patient_list')
@audit_log(model_name='CLINICALCASE', get_patient_id_from='usubjid')
def clinical_case_create(request, usubjid):
    """
    Create new clinical case
    
    Permission: add_clinicalcase
    
    Workflow:
    1. Check enrollment exists (auto-create if missing)
    2. Check site access
    3. Check if clinical already exists
    4. Process form submission or show blank form
    """
    logger.info("="*80)
    logger.info("===  CLINICAL CREATE START ===")
    logger.info("="*80)
    logger.info(f" User: {request.user.username}, USUBJID: {usubjid}, Method: {request.method}")
    
    # Import site filtering utilities
    from backends.studies.study_43en.utils.site_utils import (
        get_site_filter_params,
        get_site_filtered_object_or_404
    )
    
    # Get screening case (WITH SITE FILTERING)
    logger.info(f" Step 1: Fetching SCR_CASE for {usubjid} (with site filtering)...")
    site_filter, filter_type = get_site_filter_params(request)
    screening_case = get_site_filtered_object_or_404(
        SCR_CASE,
        site_filter,
        filter_type,
        USUBJID=usubjid
    )
    siteid = screening_case.SITEID  # Get SITEID
    logger.info(f" SCR_CASE found: SITEID={siteid}, SUBJID={screening_case.SUBJID}")
    logger.info(f" Site access automatically verified by get_site_filtered_object_or_404()")
    
    #  Get or create ENR_CASE
    logger.info(f" Step 2: Checking ENR_CASE...")
    try:
        enrollment_case = ENR_CASE.objects.get(USUBJID=screening_case)
        logger.info(f" ENR_CASE exists: ID={enrollment_case.pk}, SITEID={enrollment_case.SITEID}")
    except ENR_CASE.DoesNotExist:
        logger.warning(f" ENR_CASE NOT found for {usubjid}, auto-creating...")
        enrollment_case = ENR_CASE.objects.create(
            USUBJID=screening_case,
            STUDYID='43EN',
            SITEID=screening_case.SITEID,
            SUBJID=screening_case.SUBJID,
            created_by=request.user,
            last_modified_by=request.user
        )
        messages.info(
            request, 
            f' Enrollment record auto-created for {usubjid}. Please complete enrollment information later.'
        )
        logger.info(f" Auto-created ENR_CASE: ID={enrollment_case.pk}")
    
    #  REMOVED: check_instance_site_access - Already verified in Step 1
    
    # Check if clinical already exists
    logger.info(f" Step 3: Checking if clinical already exists...")
    if hasattr(enrollment_case, 'clinical_case'):
        logger.warning(f" Clinical already exists for {usubjid}, redirecting to UPDATE")
        messages.info(request, f'Bệnh nhân {usubjid} đã có thông tin lâm sàng.')
        return redirect('study_43en:clinical_case_update', usubjid=usubjid)
    logger.info(f" Clinical does not exist, proceeding with CREATE")
    logger.info(f" Clinical does not exist, proceeding with CREATE")
    
    # POST - Process creation
    if request.method == 'POST':
        logger.info("="*80)
        logger.info("📨 POST REQUEST - Processing form submission...")
        logger.info("="*80)
        
        # Log POST data keys
        logger.info(f" POST data keys: {list(request.POST.keys())[:20]}...")  # First 20 keys
        
        # Initialize all forms
        logger.info(f" Step 5: Initializing forms with POST data...")
        forms_dict = _initialize_forms_for_create(
            request, 
            enrollment_case,
            siteid  # Pass SITEID
        )
        logger.info(f" Forms initialized: {list(forms_dict.keys())}")
        
        # Log formset management form data
        logger.info(" Checking formset management forms in POST data:")
        for prefix in ['priorantibiotic_set', 'initialantibiotic_set', 'mainantibiotic_set',
                       'vasoidrug_set', 'hospiprocess_set', 'aehospevent_set', 'improvesympt_set']:
            total_key = f"{prefix}-TOTAL_FORMS"
            initial_key = f"{prefix}-INITIAL_FORMS"
            total_val = request.POST.get(total_key, 'MISSING')
            initial_val = request.POST.get(initial_key, 'MISSING')
            logger.info(f"  {prefix}: TOTAL={total_val}, INITIAL={initial_val}")
        
        # Validate all forms
        logger.info(f" Step 6: Validating all forms...")
        validation_results = {}
        for form_name, form in forms_dict.items():
            is_valid = form.is_valid()
            validation_results[form_name] = is_valid
            logger.info(f"  {form_name}: {' VALID' if is_valid else ' INVALID'}")
            if not is_valid:
                if hasattr(form, 'errors') and form.errors:
                    try:
                        # form.errors is ErrorDict, convert carefully
                        error_dict = {}
                        for field, errors in form.errors.items():
                            error_dict[field] = list(errors)
                        logger.error(f"    Errors: {error_dict}")
                    except Exception as e:
                        logger.error(f"    Errors (raw): {form.errors}")
                        logger.error(f"    Error logging failed: {e}")
                if hasattr(form, 'non_form_errors'):
                    try:
                        non_form_errs = form.non_form_errors()
                        if non_form_errs:
                            logger.error(f"    Non-form errors: {non_form_errs}")
                    except:
                        pass
        
        all_valid = all(validation_results.values())
        logger.info(f" Overall validation: {' ALL VALID' if all_valid else ' SOME INVALID'}")
        
        if all_valid:
            logger.info(f" Step 7: Calling save_clinical_and_related...")
            clinical = save_clinical_and_related(
                request=request,
                enrollment_case=enrollment_case,
                is_create=True,
                **forms_dict
            )
            
            if clinical:
                logger.info(f" SUCCESS: Clinical created with ID={clinical.pk}, version={clinical.version}")
                messages.success(
                    request,
                    f' Đã tạo thông tin lâm sàng cho bệnh nhân {usubjid} thành công.'
                )
                logger.info(f"🏁 Redirecting to patient_detail...")
                return redirect('study_43en:patient_detail', usubjid=usubjid)
            else:
                logger.error(f" FAILED: save_clinical_and_related returned None")
        else:
            logger.warning(" Validation failed, showing form with errors")
            # Log and show errors
            forms_with_errors = log_all_form_errors({
                'Clinical Case': forms_dict['clinical_form'],
                'History Symptoms': forms_dict['history_symptom_form'],
                '72H Symptoms': forms_dict['symptom_72h_form'],
                'Prior Antibiotics': forms_dict['prior_antibiotic_formset'],
                'Initial Antibiotics': forms_dict['initial_antibiotic_formset'],
                'Main Antibiotics': forms_dict['main_antibiotic_formset'],
                'Vasoactive Drugs': forms_dict['vaso_drug_formset'],
                'Hospitalization': forms_dict['hospi_process_formset'],
                'Adverse Events': forms_dict['ae_hosp_event_formset'],
                'Symptom Improvements': forms_dict['improve_sympt_formset'],
            })
            
            if forms_with_errors:
                error_msg = f'Vui lòng kiểm tra lại: {", ".join(forms_with_errors)}'
                messages.error(request, error_msg)
                logger.error(f" Forms with errors: {forms_with_errors}")
                logger.error(f" Forms with errors: {forms_with_errors}")
    
    # GET - Show blank form
    else:
        logger.info("="*80)
        logger.info(" GET REQUEST - Showing blank form...")
        logger.info("="*80)
        forms_dict = _initialize_forms_for_create(
            request, 
            enrollment_case,
            siteid,  # Pass SITEID
            blank=True
        )
        logger.info(f" Blank forms initialized: {list(forms_dict.keys())}")
    
    # Build context
    logger.info(f" Building context for template...")
    context = _build_context(
        forms_dict,
        screening_case,
        enrollment_case,
        None,
        is_create=True,
        is_readonly=False
    )
    logger.info(f" Context built with {len(context)} items")
    
    logger.info("="*80)
    logger.info("===  CLINICAL CREATE END - Rendering template ===")
    logger.info("="*80)
    return render(request, 'studies/study_43en/CRF/patient/clinical_form.html', context)


# ==========================================
# UPDATE VIEW (WITH UNIVERSAL AUDIT SYSTEM)
# ==========================================

@login_required
@require_crf_change('cli_case', redirect_to='study_43en:patient_list')
@audit_log(model_name='CLINICALCASE', get_patient_id_from='usubjid')
def clinical_case_update(request, usubjid):  #  RENAMED from clinical_update
    """
    Update clinical case WITH UNIVERSAL AUDIT SYSTEM (Tier 3)
    
    Permission: change_clinicalcase
    
    Architecture:
    - 1 main form (CLI_CASE)
    - 2 related forms 1-1 (HistorySymptom, Symptom_72H)
    - 7 formsets:
      * 3 antibiotic formsets (FK to CLI_CASE)
      * 4 clinical formsets (FK to CLI_CASE)
    """
    logger.info("="*80)
    logger.info("=== 📝 CLINICAL UPDATE START ===")
    logger.info("="*80)
    logger.info(f" User: {request.user.username}, USUBJID: {usubjid}, Method: {request.method}")
    
    # Get clinical with related data (WITH SITE FILTERING)
    logger.info(f" Step 1: Fetching clinical with related data (with site filtering)...")
    screening_case, enrollment_case, clinical_case = get_clinical_with_related(request, usubjid)
    siteid = screening_case.SITEID  # Get SITEID
    
    if not clinical_case:
        logger.warning(f" Clinical case NOT found for {usubjid}, redirecting to CREATE")
        messages.warning(request, f'Bệnh nhân {usubjid} chưa có thông tin lâm sàng.')
        return redirect('study_43en:clinical_case_create', usubjid=usubjid)
    
    logger.info(f" Clinical found: ID={clinical_case.pk}, version={clinical_case.version}, SITEID={siteid}")
    logger.info(f"   ENR_CASE: ID={enrollment_case.pk}")
    logger.info(f"   SCR_CASE: SITEID={siteid}")
    
    #  REMOVED: check_instance_site_access - Already handled by get_clinical_with_related()
    logger.info(f" Step 2: Site access already verified by helper function")
    
    # Get or create symptom records (1-1 relationships)
    logger.info(f" Step 3: Getting/creating symptom records...")
    history_symptom, symptom_72h = get_or_create_symptom_records(clinical_case)
    logger.info(f" History symptom: {'EXISTS' if history_symptom.pk else 'NEW'}")
    logger.info(f" 72H symptom: {'EXISTS' if symptom_72h.pk else 'NEW'}")
    logger.info(f" 72H symptom: {'EXISTS' if symptom_72h.pk else 'NEW'}")
    
    # GET - Show current data
    if request.method == 'GET':
        logger.info("="*80)
        logger.info(" GET REQUEST - Loading existing data...")
        logger.info("="*80)
        
        logger.info(f" Step 4: Initializing forms with existing instances...")
        clinical_form = ClinicalCaseForm(
            instance=clinical_case,
            siteid=siteid  # Pass SITEID
        )
        history_symptom_form = HistorySymptomForm(instance=history_symptom)
        symptom_72h_form = Symptom72HForm(instance=symptom_72h)
        logger.info(f" Main forms initialized")
        
        #  FIX: Antibiotic formsets (FK to CLI_CASE - NOT ENR_CASE!)
        logger.info(f" Initializing antibiotic formsets (FK to CLI_CASE)...")
        prior_antibiotic_formset = PriorAntibioticFormSet(
            prefix='priorantibiotic_set',
            instance=clinical_case
        )
        logger.info(f"   Prior antibiotics: {len(prior_antibiotic_formset.queryset)} existing")
        
        initial_antibiotic_formset = InitialAntibioticFormSet(
            prefix='initialantibiotic_set',
            instance=clinical_case
        )
        logger.info(f"   Initial antibiotics: {len(initial_antibiotic_formset.queryset)} existing")
        
        main_antibiotic_formset = MainAntibioticFormSet(
            prefix='mainantibiotic_set',
            instance=clinical_case
        )
        logger.info(f"   Main antibiotics: {len(main_antibiotic_formset.queryset)} existing")
        
        # Clinical formsets (FK to CLI_CASE)
        logger.info(f" Initializing clinical formsets (FK to CLI_CASE)...")
        vaso_drug_formset = VasoIDrugFormSet(
            prefix='vasoidrug_set',
            instance=clinical_case
        )
        logger.info(f"   Vaso drugs: {len(vaso_drug_formset.queryset)} existing")
        
        hospi_process_formset = HospiProcessFormSet(
            prefix='hospiprocess_set',
            instance=clinical_case
        )
        logger.info(f"   Hospi processes: {len(hospi_process_formset.queryset)} existing")
        
        ae_hosp_event_formset = AEHospEventFormSet(
            prefix='aehospevent_set',
            instance=clinical_case
        )
        logger.info(f"   AE events: {len(ae_hosp_event_formset.queryset)} existing")
        
        improve_sympt_formset = ImproveSymptFormSet(
            prefix='improvesympt_set',
            instance=clinical_case
        )
        logger.info(f"   Improve symptoms: {len(improve_sympt_formset.queryset)} existing")
        logger.info(f"   Improve symptoms: {len(improve_sympt_formset.queryset)} existing")
        
        logger.info(f" Building context...")
        context = {
            'clinical_form': clinical_form,
            'form': clinical_form,  # Alias for template
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
            'is_readonly': False,
            'current_version': clinical_case.version,
            'selected_site_id': siteid,  # Add to context
            'today': date.today(),
        }
        logger.info(f" Context built with {len(context)} items")
        
        logger.info("="*80)
        logger.info("=== 📝 CLINICAL UPDATE END (GET) - Rendering template ===")
        logger.info("="*80)
        return render(request, 'studies/study_43en/CRF/patient/clinical_form.html', context)
    
    #  POST - USE UNIVERSAL AUDIT SYSTEM (Tier 3)
    logger.info("="*80)
    logger.info("� POST REQUEST - Using Universal Audit System (Tier 3)...")
    logger.info("="*80)
    logger.info("="*80)
    
    # Log POST data keys
    logger.info(f" POST data keys: {list(request.POST.keys())[:20]}...")  # First 20 keys
    
    # DEBUG: Check for NEWS2 specifically
    news2_value = request.POST.get('NEWS2', 'NOT_IN_POST')
    logger.info(f"🔍 DEBUG: NEWS2 value in POST = '{news2_value}'")
    
    # Log formset management form data
    logger.info(" Checking formset management forms in POST data:")
    for prefix in ['priorantibiotic_set', 'initialantibiotic_set', 'mainantibiotic_set',
                   'vasoidrug_set', 'hospiprocess_set', 'aehospevent_set', 'improvesympt_set']:
        total_key = f"{prefix}-TOTAL_FORMS"
        initial_key = f"{prefix}-INITIAL_FORMS"
        total_val = request.POST.get(total_key, 'MISSING')
        initial_val = request.POST.get(initial_key, 'MISSING')
        logger.info(f"  {prefix}: TOTAL={total_val}, INITIAL={initial_val}")
    
    logger.info(f" Step 4: Building forms_config for Universal Audit System...")
    forms_config = {
        'main': {
            'class': ClinicalCaseForm,
            'instance': clinical_case,
            'kwargs': {'siteid': siteid}  # Pass SITEID
        },
        'related': {
            'history_symptom': {
                'class': HistorySymptomForm,
                'instance': history_symptom
            },
            'symptom_72h': {
                'class': Symptom72HForm,
                'instance': symptom_72h
            }
        },
        'formsets': {
            #  FIX: Antibiotic formsets - FK to CLI_CASE (NOT ENR_CASE!)
            'prior_antibiotics': {
                'class': PriorAntibioticFormSet,
                'instance': clinical_case,
                'prefix': 'priorantibiotic_set',
                'related_name': 'prior_antibiotics'
            },
            'initial_antibiotics': {
                'class': InitialAntibioticFormSet,
                'instance': clinical_case,
                'prefix': 'initialantibiotic_set',
                'related_name': 'initial_antibiotics'
            },
            'main_antibiotics': {
                'class': MainAntibioticFormSet,
                'instance': clinical_case,
                'prefix': 'mainantibiotic_set',
                'related_name': 'main_antibiotics'
            },
            # Clinical formsets - FK to CLI_CASE
            'vaso_drugs': {
                'class': VasoIDrugFormSet,
                'instance': clinical_case,
                'prefix': 'vasoidrug_set',
                'related_name': 'vaso_drugs'
            },
            'hospiprocesses': {
                'class': HospiProcessFormSet,
                'instance': clinical_case,
                'prefix': 'hospiprocess_set',
                'related_name': 'hospiprocesses'
            },
            'ae_hosp_events': {
                'class': AEHospEventFormSet,
                'instance': clinical_case,
                'prefix': 'aehospevent_set',
                'related_name': 'ae_hosp_events'
            },
            'improve_symptoms': {
                'class': ImproveSymptFormSet,
                'instance': clinical_case,
                'prefix': 'improvesympt_set',
                'related_name': 'improve_symptoms'
            }
        }
    }
    logger.info(f" forms_config built with {len(forms_config['formsets'])} formsets")
    logger.info(f" forms_config built with {len(forms_config['formsets'])} formsets")
    
    def save_callback(request, forms_dict):
        """Save clinical case with all related data"""
        logger.info(f" Step 5: save_callback called...")
        logger.info(f"   Forms dict keys: {list(forms_dict.keys())}")
        
        mapped_forms = {
            'clinical_form': forms_dict['main'],
            'history_symptom_form': forms_dict['related']['history_symptom'],
            'symptom_72h_form': forms_dict['related']['symptom_72h'],
            'prior_antibiotic_formset': forms_dict['formsets']['prior_antibiotics'],
            'initial_antibiotic_formset': forms_dict['formsets']['initial_antibiotics'],
            'main_antibiotic_formset': forms_dict['formsets']['main_antibiotics'],
            'vaso_drug_formset': forms_dict['formsets']['vaso_drugs'],
            'hospi_process_formset': forms_dict['formsets']['hospiprocesses'],
            'ae_hosp_event_formset': forms_dict['formsets']['ae_hosp_events'],
            'improve_sympt_formset': forms_dict['formsets']['improve_symptoms'],
        }
        logger.info(f" Mapped forms: {list(mapped_forms.keys())}")
        
        logger.info(f" Calling save_clinical_and_related...")
        clinical = save_clinical_and_related(
            request=request,
            enrollment_case=enrollment_case,
            is_create=False,
            **mapped_forms
        )
        
        success = clinical is not None
        logger.info(f"{' SUCCESS' if success else ' FAILED'}: save_clinical_and_related returned {clinical}")
        return success
    
    # Use Universal Audit System
    logger.info(f" Step 6: Calling process_complex_update...")
    logger.info("="*80)
    logger.info("=== 📝 CLINICAL UPDATE END (POST) - Delegating to Universal Audit System ===")
    logger.info("="*80)
    return process_complex_update(
        request=request,
        main_instance=clinical_case,
        forms_config=forms_config,
        save_callback=save_callback,
        template_name='studies/study_43en/CRF/patient/clinical_form.html',
        redirect_url=reverse('study_43en:patient_detail', kwargs={'usubjid': usubjid}),
        extra_context={
            'screening_case': screening_case,
            'enrollment_case': enrollment_case,
            'clinical_case': clinical_case,
            'selected_site_id': siteid,  # Add to context
            'today': date.today(),
            'current_version': clinical_case.version,
        }
    )


# ==========================================
# HELPER FUNCTIONS FOR CREATE
# ==========================================

def _initialize_forms_for_create(request, enrollment_case, siteid, blank=False):
    """Initialize all forms for create view"""
    logger.info(f" _initialize_forms_for_create called (blank={blank}, siteid={siteid})")
    
    if blank:
        # GET - blank forms
        logger.info(f"   Creating blank forms with initial data...")
        initial_data = {
            'ADMISDATE': date.today(),
        }
        
        forms = {
            'clinical_form': ClinicalCaseForm(
                initial=initial_data,
                siteid=siteid  # Pass SITEID
            ),
            'history_symptom_form': HistorySymptomForm(instance=None),
            'symptom_72h_form': Symptom72HForm(instance=None),
            'prior_antibiotic_formset': PriorAntibioticFormSet(
                prefix='priorantibiotic_set',
                instance=None
            ),
            'initial_antibiotic_formset': InitialAntibioticFormSet(
                prefix='initialantibiotic_set',
                instance=None
            ),
            'main_antibiotic_formset': MainAntibioticFormSet(
                prefix='mainantibiotic_set',
                instance=None
            ),
            'vaso_drug_formset': VasoIDrugFormSet(
                prefix='vasoidrug_set',
                instance=None
            ),
            'hospi_process_formset': HospiProcessFormSet(
                prefix='hospiprocess_set',
                instance=None
            ),
            'ae_hosp_event_formset': AEHospEventFormSet(
                prefix='aehospevent_set',
                instance=None
            ),
            'improve_sympt_formset': ImproveSymptFormSet(
                prefix='improvesympt_set',
                instance=None
            ),
        }
        logger.info(f" Blank forms created: {list(forms.keys())}")
        return forms
    else:
        # POST - with data
        logger.info(f"   Creating forms with POST data...")
        forms = {
            'clinical_form': ClinicalCaseForm(
                request.POST,
                siteid=siteid  # Pass SITEID
            ),
            'history_symptom_form': HistorySymptomForm(request.POST, instance=None),
            'symptom_72h_form': Symptom72HForm(request.POST, instance=None),
            'prior_antibiotic_formset': PriorAntibioticFormSet(
                request.POST,
                prefix='priorantibiotic_set',
                instance=None
            ),
            'initial_antibiotic_formset': InitialAntibioticFormSet(
                request.POST,
                prefix='initialantibiotic_set',
                instance=None
            ),
            'main_antibiotic_formset': MainAntibioticFormSet(
                request.POST,
                prefix='mainantibiotic_set',
                instance=None
            ),
            'vaso_drug_formset': VasoIDrugFormSet(
                request.POST,
                prefix='vasoidrug_set',
                instance=None
            ),
            'hospi_process_formset': HospiProcessFormSet(
                request.POST,
                prefix='hospiprocess_set',
                instance=None
            ),
            'ae_hosp_event_formset': AEHospEventFormSet(
                request.POST,
                prefix='aehospevent_set',
                instance=None
            ),
            'improve_sympt_formset': ImproveSymptFormSet(
                request.POST,
                prefix='improvesympt_set',
                instance=None
            ),
        }
        logger.info(f" POST forms created: {list(forms.keys())}")
        return forms


def _build_context(forms_dict, screening_case, enrollment_case, clinical_case, 
                   is_create, is_readonly):
    """Build context dictionary for template"""
    logger.info(f" _build_context called")
    logger.info(f"   is_create={is_create}, is_readonly={is_readonly}")
    
    context = {
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'clinical_case': clinical_case,
        'is_create': is_create,
        'is_readonly': is_readonly,
        'today': date.today(),
    }
    
    # Add all forms
    context.update(forms_dict)
    
    # Add version if updating
    if clinical_case:
        context['current_version'] = clinical_case.version
        context['selected_site_id'] = screening_case.SITEID
        logger.info(f"   clinical_case: ID={clinical_case.pk}, version={clinical_case.version}")
    
    logger.info(f" Context built with {len(context)} items")
    return context