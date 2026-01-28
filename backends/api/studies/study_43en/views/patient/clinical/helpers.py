# backends/api/studies/study_43en/views/patient/clinical/helpers.py
"""
Helper functions for clinical views.

Provides transaction handlers and form utilities.
"""
import logging
from django import forms as django_forms
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction

from backends.studies.study_43en.models.patient import (
    SCR_CASE, ENR_CASE, CLI_CASE,
    HistorySymptom, Symptom_72H,
)
from backends.studies.study_43en.utils.site_utils import (
    get_site_filter_params, get_filtered_queryset,
    get_site_filtered_object_or_404,
)

# Use shared utilities
from backends.api.studies.study_43en.views.shared import (
    set_audit_metadata,
    make_form_readonly as _make_form_readonly,
    make_formset_readonly as _make_formset_readonly,
)

logger = logging.getLogger(__name__)


# ==========================================
# DATA RETRIEVAL
# ==========================================

def get_clinical_with_related(request, usubjid):
    """
    Get clinical case with optimized queries and site filtering
    
    Args:
        request: HttpRequest object (for site filtering)
        usubjid: Patient USUBJID
        
    Returns:
        tuple: (screening_case, enrollment_case, clinical_case)
               clinical_case will be None if not exists
               
    Raises:
        Http404: If screening/enrollment not found OR user doesn't have site access
    """
    from backends.studies.study_43en.utils.site_utils import (
        get_site_filter_params,
        get_filtered_queryset,
        get_site_filtered_object_or_404
    )
    
    # Get site filtering parameters
    site_filter, filter_type = get_site_filter_params(request)
    
    # Get screening with site check
    screening_case = get_site_filtered_object_or_404(
        SCR_CASE,
        site_filter,
        filter_type,
        USUBJID=usubjid
    )
    
    # Get enrollment with site check
    enrollment_case = get_site_filtered_object_or_404(
        ENR_CASE,
        site_filter,
        filter_type,
        USUBJID=screening_case
    )
    
    # Get clinical case with site filtering
    try:
        clinical_queryset = get_filtered_queryset(
            CLI_CASE,
            site_filter,
            filter_type
        ).select_related(
            'USUBJID',
            'USUBJID__USUBJID'
        ).prefetch_related(
            'History_Symptom',
            'Symptom_72H',
            'vaso_drugs',
            'hospiprocesses',
            'ae_hosp_events',
            'improve_symptoms'
        )
        
        clinical_case = clinical_queryset.get(USUBJID=enrollment_case)
        return screening_case, enrollment_case, clinical_case
        
    except CLI_CASE.DoesNotExist:
        return screening_case, enrollment_case, None


def get_or_create_symptom_records(clinical_case):
    """Get or create symptom records (1-1 relationships)"""
    try:
        history_symptom = clinical_case.History_Symptom
    except HistorySymptom.DoesNotExist:
        history_symptom = HistorySymptom(USUBJID=clinical_case)
    
    try:
        symptom_72h = clinical_case.Symptom_72H
    except Symptom_72H.DoesNotExist:
        symptom_72h = Symptom_72H(USUBJID=clinical_case)
    
    return history_symptom, symptom_72h


# ==========================================
# FORM UTILITIES
# ==========================================

def make_form_readonly(form):
    """
    Make all form fields readonly - ENHANCED
    Handles all widget types properly
    """
    from django import forms as django_forms
    
    for field_name, field in form.fields.items():
        # Disable field
        field.disabled = True
        
        # Update widget attributes based on type
        widget = field.widget
        widget_attrs = widget.attrs if hasattr(widget, 'attrs') else {}
        
        # Common attributes
        widget_attrs['disabled'] = 'disabled'
        widget_attrs['readonly'] = 'readonly'
        
        # Special handling for different widget types
        if isinstance(widget, (django_forms.CheckboxInput, django_forms.RadioSelect)):
            # Checkboxes and radios - only disable, no readonly
            widget_attrs.pop('readonly', None)
            widget_attrs['onclick'] = 'return false;'
            
        elif isinstance(widget, django_forms.CheckboxSelectMultiple):
            # Multiple checkboxes
            widget_attrs.pop('readonly', None)
            widget_attrs['onclick'] = 'return false;'
            
        elif isinstance(widget, django_forms.Select):
            # Select dropdowns
            widget_attrs.pop('readonly', None)
            widget_attrs['style'] = widget_attrs.get('style', '') + ' pointer-events: none;'
            
        elif isinstance(widget, django_forms.Textarea):
            # Textarea
            widget_attrs['style'] = widget_attrs.get('style', '') + ' resize: none;'
            
        # Update widget attrs
        widget.attrs = widget_attrs


def make_formset_readonly(formset):
    """
    Make all formset fields readonly - ENHANCED
    Also hides add/delete buttons
    """
    # Make all forms readonly
    for form in formset.forms:
        make_form_readonly(form)
        
        # Hide DELETE checkbox
        if hasattr(form, 'fields') and 'DELETE' in form.fields:
            form.fields['DELETE'].widget = django_forms.HiddenInput()
    
    # Prevent adding new forms
    formset.can_delete = False
    formset.extra = 0
    formset.max_num = len(formset.forms)


# ==========================================
# TRANSACTION HANDLER - ENHANCED
# ==========================================

def save_clinical_and_related(
    request,
    clinical_form,
    history_symptom_form,
    symptom_72h_form,
    prior_antibiotic_formset,
    initial_antibiotic_formset,
    main_antibiotic_formset,
    vaso_drug_formset,
    hospi_process_formset,
    ae_hosp_event_formset,
    improve_sympt_formset,
    enrollment_case,
    is_create=False
):
    """
     ENHANCED: Save clinical and all related forms in transaction
    Now compatible with Universal Audit System
    """
    try:
        with transaction.atomic():
            # 1. Save clinical case (main)
            clinical = clinical_form.save(commit=False)
            
            if is_create:
                clinical.USUBJID = enrollment_case
            
            set_audit_metadata(clinical, request.user)
            
            #  Increment version for update
            if not is_create:
                clinical.version += 1
            
            clinical.save()
            
            logger.info(
                f"{'Created' if is_create else 'Updated'} clinical: "
                f"{clinical.USUBJID.USUBJID.USUBJID} (version {clinical.version})"
            )
            
            # 2. Save history symptoms (1-1)
            if history_symptom_form.has_changed():
                history_symptom = history_symptom_form.save(commit=False)
                history_symptom.USUBJID = clinical
                set_audit_metadata(history_symptom, request.user)
                
                if hasattr(history_symptom, 'version') and not is_create:
                    history_symptom.version += 1
                
                history_symptom.save()
                logger.info(f"Saved history symptoms (count: {history_symptom.symptom_count})")
            
            # 3. Save 72h symptoms (1-1)
            if symptom_72h_form.has_changed():
                symptom_72h = symptom_72h_form.save(commit=False)
                symptom_72h.USUBJID = clinical
                set_audit_metadata(symptom_72h, request.user)
                
                if hasattr(symptom_72h, 'version') and not is_create:
                    symptom_72h.version += 1
                
                symptom_72h.save()
                logger.info(f"Saved 72h symptoms (count: {symptom_72h.symptom_count})")
            
            #  FIX: Save antibiotics (FK to CLI_CASE - NOT ENR_CASE!)
            _save_antibiotic_formset(prior_antibiotic_formset, clinical, request.user, 'prior')
            _save_antibiotic_formset(initial_antibiotic_formset, clinical, request.user, 'initial')
            _save_antibiotic_formset(main_antibiotic_formset, clinical, request.user, 'main')
            
            # 5. Save related models (FK to CLI_CASE)
            _save_related_formset(vaso_drug_formset, clinical, request.user, 'vasoactive drugs')
            _save_related_formset(hospi_process_formset, clinical, request.user, 'hospitalization processes')
            _save_related_formset(ae_hosp_event_formset, clinical, request.user, 'adverse events')
            _save_related_formset(improve_sympt_formset, clinical, request.user, 'symptom improvements')
            
            return clinical
            
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        messages.error(request, f'Lỗi validation: {e}')
        return None
        
    except Exception as e:
        logger.error(f"Error saving clinical: {e}", exc_info=True)
        messages.error(request, f'Lỗi khi lưu thông tin lâm sàng: {str(e)}')
        return None


def _save_antibiotic_formset(formset, clinical_case, user, antibiotic_type):
    """ FIX: Helper to save antibiotic formsets (FK to CLI_CASE)"""
    instances = formset.save(commit=False)
    for instance in instances:
        instance.USUBJID = clinical_case  #  FIX: FK to CLI_CASE (not ENR_CASE)
        set_audit_metadata(instance, user)
        
        #  CRITICAL: Preserve SEQUENCE for existing records
        if instance.pk and not instance.SEQUENCE:
            # Fetch current SEQUENCE from database
            model_class = type(instance)
            try:
                existing = model_class.objects.get(pk=instance.pk)
                instance.SEQUENCE = existing.SEQUENCE
                logger.info(f"Preserved SEQUENCE={existing.SEQUENCE} for {antibiotic_type} antibiotic pk={instance.pk}")
            except model_class.DoesNotExist:
                pass
        
        #  Increment version
        if hasattr(instance, 'version') and instance.pk:
            instance.version += 1
        
        instance.save()
    

        logger.info(f"Deleted {antibiotic_type} antibiotic: {obj}")
    
    formset.save_m2m()
    logger.info(f"Saved {len(instances)} {antibiotic_type} antibiotics")


def _save_related_formset(formset, clinical_case, user, entity_name):
    """Helper to save related formsets"""
    instances = formset.save(commit=False)
    for instance in instances:
        instance.USUBJID = clinical_case
        set_audit_metadata(instance, user)
        
        #  CRITICAL: Preserve SEQUENCE for existing records
        if instance.pk and not instance.SEQUENCE:
            # Fetch current SEQUENCE from database
            model_class = type(instance)
            try:
                existing = model_class.objects.get(pk=instance.pk)
                instance.SEQUENCE = existing.SEQUENCE
                logger.info(f"Preserved SEQUENCE={existing.SEQUENCE} for {entity_name} pk={instance.pk}")
            except model_class.DoesNotExist:
                pass
        
        #  Increment version
        if hasattr(instance, 'version') and instance.pk:
            instance.version += 1
        
        instance.save()
    

        logger.info(f"Deleted {entity_name}: {obj}")
    
    formset.save_m2m()
    logger.info(f"Saved {len(instances)} {entity_name}")


# ==========================================
# VALIDATION HELPERS
# ==========================================

def log_form_errors(form, form_name):
    """
    Log form validation errors
     FIX: Handle both regular forms (dict) and formsets (list of dicts)
    """
    # For formsets - check each form's errors
    if hasattr(form, 'forms'):
        formset_has_errors = False
        form_errors_list = []
        
        for idx, subform in enumerate(form.forms):
            if hasattr(subform, 'errors') and subform.errors:
                # Check if error dict has actual content
                if isinstance(subform.errors, dict) and any(subform.errors.values()):
                    form_errors_list.append(subform.errors)
                    formset_has_errors = True
        
        # Also check non_form_errors
        if hasattr(form, 'non_form_errors'):
            try:
                non_form_errs = form.non_form_errors()
                if non_form_errs:
                    logger.warning(f"{form_name} non-form errors: {non_form_errs}")
                    formset_has_errors = True
            except:
                pass
        
        if formset_has_errors and form_errors_list:
            logger.warning(f"{form_name} errors: {form_errors_list}")
            return True
    
    # For regular forms - errors is a dict
    elif hasattr(form, 'errors') and form.errors:
        # Check if errors is a dict and has actual content
        if isinstance(form.errors, dict) and any(form.errors.values()):
            logger.warning(f"{form_name} errors: {form.errors}")
            return True
    
    return False


def log_all_form_errors(forms_dict):
    """Log all form validation errors"""
    forms_with_errors = []
    
    for name, form in forms_dict.items():
        if log_form_errors(form, name):
            forms_with_errors.append(name)
    
    return forms_with_errors
