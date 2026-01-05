# backends/studies/study_43en/utils/audit/processors.py
"""
Universal Audit System - Handles ALL CRF types

3-tier architecture:
- Tier 1: AuditProcessor (single form)
- Tier 2: MultiFormAuditProcessor (multiple related forms)
- Tier 3: ComplexAuditProcessor (forms + formsets + custom save)
"""

import logging
from typing import Dict, List, Optional, Callable, Any
from django.shortcuts import render, redirect
from django.db import transaction
from django.contrib import messages

from .detector import ChangeDetector
from .validator import ReasonValidator

logger = logging.getLogger(__name__)


# ==========================================
# BASE PROCESSOR (Shared functionality)
# ==========================================

class BaseAuditProcessor:
    """Base class with shared functionality"""
    
    def __init__(self):
        self.detector = ChangeDetector()
        self.validator = ReasonValidator()
        
        # Metadata fields to exclude from change detection
        self.metadata_fields = [
            'id',
            'version',
            'last_modified_by_id',
            'last_modified_by_username',
            'last_modified_at',
            'created_at',
            'updated_at',
        ]
    
    def _collect_reasons(self, request, changes: List[Dict]) -> Dict[str, str]:
        """Collect reasons from POST data"""
        reasons_data = {}
        for change in changes:
            field_name = change['field']
            reason_key = f'reason_{field_name}'
            reason = request.POST.get(reason_key, '').strip()
            if reason:
                reasons_data[field_name] = reason
        return reasons_data
    
    def _validate_reasons(self, reasons_data: Dict, changes: List[Dict]) -> tuple:
        """
        Validate reasons with security sanitization
        
        Returns:
            (is_valid: bool, sanitized_reasons: dict, validation_result: dict)
        """
        required_fields = [c['field'] for c in changes]
        
        validation_result = self.validator.validate_reasons(
            reasons_data,
            required_fields
        )
        
        if not validation_result['valid']:
            return False, {}, validation_result
        
        #  Use SANITIZED reasons
        sanitized_reasons = validation_result.get('sanitized_reasons', reasons_data)
        
        return True, sanitized_reasons, validation_result
    
    def _set_audit_data(self, request, patient_id: str, site_id: str,
                       changes: List[Dict], reasons_data: Dict):
        """Set audit_data for decorator"""
        combined_reason = "\n".join([
            f"{change['field']}: {reasons_data.get(change['field'], 'N/A')}"
            for change in changes
        ])
        
        request.audit_data = {
            'patient_id': patient_id,
            'site_id': site_id,
            'reason': combined_reason,
            'changes': changes,
            'reasons_json': reasons_data,
        }
        
        logger.info(f" Set audit_data with {len(changes)} changes")
    
    def _show_reason_modal(self, request, context: Dict, changes: List[Dict],
                          submitted_reasons: Dict = None):
        """Add reason modal data to context"""
        context['detected_changes'] = changes
        context['show_reason_form'] = True
        if submitted_reasons:
            context['submitted_reasons'] = submitted_reasons
        return context


# ==========================================
# TIER 1: SIMPLE FORM PROCESSOR
# ==========================================

class AuditProcessor(BaseAuditProcessor):
    """
    Tier 1: Process single form updates with audit
    
    Use for:
    - Screening (1 form)
    - Sample (1 form)
    """
    
    def process_form_update(
        self,
        request,
        instance,
        form_class,
        template_name: str,
        redirect_url: str,
        extra_context: Dict = None,
        form_kwargs: Dict = None,
    ):
        """Process single form update with audit"""

        #  THÊM: Handle form_kwargs
        if form_kwargs is None:
            form_kwargs = {}

        # STEP 1: Capture old data
        old_data = self.detector.extract_old_data(instance)
        
        # Remove metadata fields
        old_data = {k: v for k, v in old_data.items() 
                   if k not in self.metadata_fields}
        
        # STEP 2: Validate form
        form = form_class(request.POST, instance=instance, **form_kwargs)
        
        if not form.is_valid():
            logger.error(f"Form validation failed: {form.errors}")
            messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi!')
            
            context = {
                'form': form,
                'is_create': False,
                **(extra_context or {})
            }
            return render(request, template_name, context)
        
        # STEP 3: Detect changes
        new_data = self.detector.extract_new_data(form)
        new_data = {k: v for k, v in new_data.items() 
                   if k not in self.metadata_fields}
        
        changes = self.detector.detect_changes(old_data, new_data)
        
        # STEP 4: No changes → save directly
        if not changes:
            try:
                with transaction.atomic():
                    instance = form.save(commit=False)
                    
                    if hasattr(instance, 'last_modified_by_id'):
                        instance.last_modified_by_id = request.user.id
                    if hasattr(instance, 'last_modified_by_username'):
                        instance.last_modified_by_username = request.user.username
                    
                    instance.save()
                
                messages.success(request, 'Lưu thành công!')
                return redirect(redirect_url)
            except Exception as e:
                logger.error(f"Save failed: {e}", exc_info=True)
                messages.error(request, f'Lỗi khi lưu: {str(e)}')
                return render(request, template_name, {'form': form, **(extra_context or {})})
        
        # STEP 5: Collect and validate reasons
        reasons_data = self._collect_reasons(request, changes)
        
        is_valid, sanitized_reasons, validation_result = self._validate_reasons(
            reasons_data, changes
        )
        
        if not is_valid:
            messages.warning(request, 'Vui lòng nhập lý do thay đổi (tối thiểu 3 ký tự).')
            
            #  FIX: Re-initialize form from current POST data
            # This ensures form reflects the LATEST submission, not the original one
            logger.debug(f"📝 Re-initializing form from POST data")
            logger.debug(f"   POST keys: {list(request.POST.keys())[:10]}")
            
            form = form_class(request.POST, instance=instance, **form_kwargs)
            
            #  Validate to populate cleaned_data
            if not form.is_valid():
                logger.error(f" Form re-validation failed: {form.errors}")
            
            #  CRITICAL FIX: Pass POST data to template for hidden form
            # This allows the modal to resubmit with the same data + reasons
            context = {
                'form': form,
                'is_create': False,
                'edit_post_data': dict(request.POST.items()),  #  Add POST data
                **(extra_context or {})
            }
            context = self._show_reason_modal(request, context, changes, reasons_data)
            
            logger.debug(f" Context includes edit_post_data: {bool(context.get('edit_post_data'))}")
            
            return render(request, template_name, context)
        
        # Show security warnings
        if validation_result.get('warnings'):
            for warning in validation_result['warnings']:
                messages.warning(request, warning)
        
        # STEP 6: Set audit data
        patient_id = self._get_patient_id(instance)
        site_id = getattr(instance, 'SITEID', None)
        
        self._set_audit_data(request, patient_id, site_id, changes, sanitized_reasons)
        
        # STEP 7: Save with audit
        try:
            with transaction.atomic():
                #  DEBUG: Log form data before save
                logger.debug(f"💾 Saving instance with changes:")
                for change in changes:
                    logger.debug(f"   {change['field']}: {change['old_display']} → {change['new_display']}")
                
                instance = form.save(commit=False)
                
                #  DEBUG: Verify instance has new values
                for change in changes:
                    field_name = change['field']
                    if hasattr(instance, field_name):
                        current_value = getattr(instance, field_name)
                        logger.debug(f"   After save(commit=False): {field_name} = {current_value}")
                
                if hasattr(instance, 'last_modified_by_id'):
                    instance.last_modified_by_id = request.user.id
                if hasattr(instance, 'last_modified_by_username'):
                    instance.last_modified_by_username = request.user.username
                
                instance.save()
                
                logger.info(f" Instance saved successfully with {len(changes)} changes")
            
            messages.success(request, 'Cập nhật thành công với audit trail!')
            return redirect(redirect_url)
        except Exception as e:
            logger.error(f"Save failed: {e}", exc_info=True)
            messages.error(request, f'Lỗi khi lưu: {str(e)}')
            return render(request, template_name, {'form': form, **(extra_context or {})})
    
    def _get_patient_id(self, instance):
        """Extract patient ID from instance"""
        # Try common patterns
        if hasattr(instance, 'USUBJID'):
            if hasattr(instance.USUBJID, 'USUBJID'):
                return instance.USUBJID.USUBJID  # ENR_CASE.USUBJID.USUBJID
            return str(instance.USUBJID)  # Direct USUBJID
        
        if hasattr(instance, 'SCRID'):
            return instance.SCRID
        
        # Fallback to PK
        pk_field = instance._meta.pk.name
        return str(getattr(instance, pk_field))


# ==========================================
# TIER 2: MULTI-FORM PROCESSOR
# ==========================================

class MultiFormAuditProcessor(BaseAuditProcessor):
    """
    Tier 2: Process multiple related forms (1-1 relationships)
    
    Use for:
    - Enrollment (main + underlying + medications without formsets)
    
    Config example:
        forms_config = {
            'main': {'class': EnrollmentCaseForm, 'instance': enrollment_case},
            'related': {
                'underlying': {'class': UnderlyingConditionForm, 'instance': underlying},
            }
        }
    """
    
    def process_multi_form_update(
        self,
        request,
        main_instance,
        forms_config: Dict,
        save_callback: Callable,
        template_name: str,
        redirect_url: str,
        extra_context: Dict = None,
        form_kwargs: Dict = None,
    ):
        """Process multiple related forms with audit"""
        
        # STEP 1: Capture OLD data (all forms)
        all_old_data = self._capture_all_old_data(main_instance, forms_config)
        
        # STEP 2: Initialize and validate forms
        forms_dict = self._initialize_all_forms(request, forms_config, form_kwargs)
        
        if not self._validate_all_forms(forms_dict):
            return self._handle_validation_errors(
                request, forms_dict, template_name, extra_context
            )
        
        # STEP 3: Detect changes (all forms)
        all_changes = self._detect_multi_form_changes(all_old_data, forms_dict)
        
        logger.info(f" Total changes: {len(all_changes)}")
        
        # STEP 4: No changes → save directly
        if not all_changes:
            result = save_callback(request, forms_dict)
            if result:
                messages.success(request, 'Cập nhật thành công!')
                return redirect(redirect_url)
            else:
                return self._render_error(request, forms_dict, template_name, extra_context)
        
        # STEP 5: Collect and validate reasons
        reasons_data = self._collect_reasons(request, all_changes)
        
        is_valid, sanitized_reasons, validation_result = self._validate_reasons(
            reasons_data, all_changes
        )
        
        if not is_valid:
            messages.warning(request, 'Vui lòng nhập lý do thay đổi cho tất cả các trường.')
            
            context = self._build_context(forms_dict, extra_context)
            #  CRITICAL FIX: Pass POST data to template for hidden form
            context['edit_post_data'] = dict(request.POST.items())
            context = self._show_reason_modal(request, context, all_changes, reasons_data)
            
            logger.debug(f" Context includes edit_post_data: {bool(context.get('edit_post_data'))}")
            
            return render(request, template_name, context)
        
        # Show security warnings
        if validation_result.get('warnings'):
            for warning in validation_result['warnings']:
                messages.warning(request, warning)
        
        # STEP 6: Set audit data
        patient_id = self._get_patient_id_from_instance(main_instance)
        site_id = getattr(main_instance, 'SITEID', None)
        
        self._set_audit_data(request, patient_id, site_id, all_changes, sanitized_reasons)
        
        # STEP 7: Save with audit
        result = save_callback(request, forms_dict)
        
        if result:
            messages.success(request, 'Cập nhật thành công với audit trail!')
            return redirect(redirect_url)
        else:
            return self._render_error(request, forms_dict, template_name, extra_context)
    
    def _capture_all_old_data(self, main_instance, forms_config):
        """Capture old data from all forms"""
        all_old_data = {
            'main': self.detector.extract_old_data(main_instance)
        }
        
        # Remove metadata
        all_old_data['main'] = {
            k: v for k, v in all_old_data['main'].items()
            if k not in self.metadata_fields
        }
        
        # Personal form (if present)
        if 'personal' in forms_config:
            instance = forms_config['personal']['instance']
            if instance and instance.pk:
                old_data = self.detector.extract_old_data(instance)
                all_old_data['personal'] = {
                    k: v for k, v in old_data.items()
                    if k not in self.metadata_fields
                }
            else:
                all_old_data['personal'] = {}
        
        # Related forms
        for name, config in forms_config.get('related', {}).items():
            instance = config['instance']
            if instance and instance.pk:
                old_data = self.detector.extract_old_data(instance)
                all_old_data[name] = {
                    k: v for k, v in old_data.items()
                    if k not in self.metadata_fields
                }
            else:
                all_old_data[name] = {}
        
        return all_old_data
    
    def _initialize_all_forms(self, request, forms_config, form_kwargs=None):
        """Initialize all forms from POST"""
        if form_kwargs is None:
            form_kwargs = {}
        forms_dict = {}
        
        # Main form
        main_config = forms_config['main']
        main_kwargs = main_config.get('kwargs', {})  # Get extra kwargs (siteid, etc.)
        main_kwargs.update(form_kwargs)
        forms_dict['main'] = main_config['class'](
            request.POST,
            instance=main_config['instance'],
            **main_kwargs  # Pass extra kwargs
        )

        # Add personal form if present in forms_config
        if 'personal' in forms_config:
            personal_config = forms_config['personal']
            personal_kwargs = personal_config.get('kwargs', {})
            personal_kwargs.update(form_kwargs)
            forms_dict['personal'] = personal_config['class'](
                request.POST,
                instance=personal_config['instance'],
                **personal_kwargs
            )
        
        # Related forms
        forms_dict['related'] = {}
        for name, config in forms_config.get('related', {}).items():
            rel_kwargs = config.get('kwargs', {})  # Get extra kwargs
            rel_kwargs.update(form_kwargs)
            forms_dict['related'][name] = config['class'](
                request.POST,
                instance=config['instance'],
                **rel_kwargs  # Pass extra kwargs
            )
        
        return forms_dict
    
    def _validate_all_forms(self, forms_dict):
        """Validate all forms"""
        valid = forms_dict['main'].is_valid()
        
        # Validate personal form if present
        if 'personal' in forms_dict:
            personal_valid = forms_dict['personal'].is_valid()
            if not personal_valid:
                logger.error(f"Personal form errors: {forms_dict['personal'].errors}")
            valid = personal_valid and valid
        
        for form in forms_dict.get('related', {}).values():
            valid = form.is_valid() and valid
        
        return valid
    
    def _detect_multi_form_changes(self, all_old_data, forms_dict):
        """Detect changes across all forms"""
        all_changes = []
        
        # Main form changes
        new_main = self.detector.extract_new_data(forms_dict['main'])
        new_main = {k: v for k, v in new_main.items() if k not in self.metadata_fields}
        
        main_changes = self.detector.detect_changes(all_old_data['main'], new_main)
        all_changes.extend(main_changes)
        
        # Personal form changes (if present)
        if 'personal' in forms_dict:
            new_personal = self.detector.extract_new_data(forms_dict['personal'])
            new_personal = {k: v for k, v in new_personal.items() if k not in self.metadata_fields}
            
            old_personal = all_old_data.get('personal', {})
            personal_changes = self.detector.detect_changes(old_personal, new_personal)
            
            # Prefix field names
            for change in personal_changes:
                change['field'] = f"personal_{change['field']}"
            
            all_changes.extend(personal_changes)
        
        # Related forms changes
        for name, form in forms_dict.get('related', {}).items():
            new_data = self.detector.extract_new_data(form)
            new_data = {k: v for k, v in new_data.items() if k not in self.metadata_fields}
            
            old_data = all_old_data.get(name, {})
            
            changes = self.detector.detect_changes(old_data, new_data)
            
            # Prefix field names
            for change in changes:
                change['field'] = f"{name}_{change['field']}"
            
            all_changes.extend(changes)
        
        return all_changes
    
    def _get_patient_id_from_instance(self, instance):
        """Extract patient ID"""
        if hasattr(instance, 'USUBJID'):
            if hasattr(instance.USUBJID, 'USUBJID'):
                return instance.USUBJID.USUBJID
            return str(instance.USUBJID)
        
        pk_field = instance._meta.pk.name
        return str(getattr(instance, pk_field))
    
    def _build_context(self, forms_dict, extra_context):
        """Build template context with proper form/formset naming"""
        context = {
            'is_create': False,
            **(extra_context or {})
        }
        
        # Add main form with multiple aliases for compatibility
        if 'main' in forms_dict:
            main_form = forms_dict['main']
            context['form'] = main_form  # Generic alias
            context['main'] = main_form  # Audit system alias
            
            #  Add CRF-specific aliases based on form class
            form_class_name = main_form.__class__.__name__
            if 'FollowUp' in form_class_name:
                context['followup_form'] = main_form
            elif 'Enrollment' in form_class_name:
                context['enrollment_form'] = main_form
            elif 'Discharge' in form_class_name:
                context['discharge_form'] = main_form
            elif 'Clinical' in form_class_name:
                context['clinical_form'] = main_form
        
        # Add personal form if present
        if 'personal' in forms_dict:
            context['personal_form'] = forms_dict['personal']
        
        # Add related forms with proper naming
        for name, form in forms_dict.get('related', {}).items():
            context[f'{name}_form'] = form
        
        for name, formset in forms_dict.get('formsets', {}).items():
            if name == 'medications':
                # Support both Patient (medhisdrug_formset) and Contact (medication_formset)
                context['medhisdrug_formset'] = formset  # Patient FU28/90
                context['medication_formset'] = formset   # Contact FU28/90
            elif name == 'rehospitalizations':
                context['rehospitalization_formset'] = formset
            elif name == 'antibiotics':
                context['antibiotic_formset'] = formset
            elif name == 'icd_codes':
                context['icd_formset'] = formset
            elif name == 'laboratory_tests':
                context['formset'] = formset
            elif name == 'prior_antibiotics':
                context['prior_antibiotic_formset'] = formset
            elif name == 'initial_antibiotics':
                context['initial_antibiotic_formset'] = formset
            elif name == 'main_antibiotics':
                context['main_antibiotic_formset'] = formset
            elif name == 'vaso_drugs':
                context['vaso_drug_formset'] = formset
            elif name == 'hospiprocesses':
                context['hospi_process_formset'] = formset
            elif name == 'ae_hosp_events':
                context['ae_hosp_event_formset'] = formset
            elif name == 'improve_symptoms':
                context['improve_sympt_formset'] = formset
            else:
                # Default
                context[f'{name}_formset'] = formset
        
        return context
    
    def _handle_validation_errors(self, request, forms_dict, template_name, extra_context):
        """Handle validation errors - RE-RENDER with correct formsets"""
        messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi.')
        
        #  Use centralized context builder
        context = self._build_context(forms_dict, extra_context)
        
        return render(request, template_name, context)
    
    def _render_error(self, request, forms_dict, template_name, extra_context):
        """Render template with error"""
        context = self._build_context(forms_dict, extra_context)
        return render(request, template_name, context)


# ==========================================
# TIER 3: COMPLEX PROCESSOR (Forms + Formsets)
# ==========================================

class ComplexAuditProcessor(MultiFormAuditProcessor):
    """
    Tier 3: Process complex forms with formsets
    
    Use for:
    - Enrollment (main + underlying + medications formset)
    - Follow-up 28/90 (main + rehospitalizations + antibiotics)
    - Discharge (main + ICD codes)
    - Clinical (main + symptoms + 7 formsets)
    - Laboratory (bulk formset update)
    
    Config example:
        forms_config = {
            'main': {'class': EnrollmentCaseForm, 'instance': enrollment_case},
            'related': {
                'underlying': {'class': UnderlyingConditionForm, 'instance': underlying},
            },
            'formsets': {
                'medications': {
                    'class': MedHisDrugFormSet,
                    'instance': enrollment_case,
                    'prefix': 'medications',
                    'related_name': 'medhisdrug_set'
                }
            }
        }
    """
    
    def process_complex_update(
        self,
        request,
        main_instance,
        forms_config: Dict,
        save_callback: Callable,
        template_name: str,
        redirect_url: str,
        extra_context: Dict = None,
        skip_change_reason=None,
        
        
    ):
        """Process complex forms with formsets"""
        
        # STEP 1: Capture OLD data (including formsets)
        all_old_data = self._capture_complex_old_data(main_instance, forms_config)
        
        # STEP 2: Initialize and validate
        forms_dict = self._initialize_complex_forms(request, forms_config)
        
        if not self._validate_complex_forms(forms_dict):
            return self._handle_validation_errors(
                request, forms_dict, template_name, extra_context
            )
        
        # STEP 3: Detect changes
        all_changes = self._detect_complex_changes(all_old_data, forms_dict)
        
        logger.info(f"Total changes detected: {len(all_changes)}")
        
        #  STEP 3.5: Check if should skip change reason
        should_skip_reason = False
        if skip_change_reason and callable(skip_change_reason):
            try:
                should_skip_reason = skip_change_reason(forms_dict)
                
                if should_skip_reason:
                    logger.info(" Skip change reason: Detected as first data entry")
                    # Force empty changes to skip reason modal
                    all_changes = []
                else:
                    logger.info(" Change reason required: Real update detected")
                    
            except Exception as e:
                logger.error(f"❌ Error in skip_change_reason callable: {e}", exc_info=True)
                # On error, DON'T skip (safer approach)
                should_skip_reason = False
        
        # STEP 4: No changes → save directly
        if not all_changes:
            result = save_callback(request, forms_dict)
            if result:
                messages.success(request, 'Cập nhật thành công!')
                return redirect(redirect_url)
            else:
                return self._render_error(request, forms_dict, template_name, extra_context)
        
        # STEP 5: Collect and validate reasons
        reasons_data = self._collect_reasons(request, all_changes)
        
        is_valid, sanitized_reasons, validation_result = self._validate_reasons(
            reasons_data, all_changes
        )
        
        if not is_valid:
            messages.warning(request, 'Vui lòng nhập lý do thay đổi cho tất cả các trường.')
            
            context = self._build_context(forms_dict, extra_context)
            #  CRITICAL FIX: Pass POST data to template for hidden form
            context['edit_post_data'] = dict(request.POST.items())
            context = self._show_reason_modal(request, context, all_changes, reasons_data)
            
            #  DEBUG: Log context keys
            logger.info(f" Context keys when showing reason modal: {list(context.keys())}")
            logger.info(f" Has 'form': {'form' in context}")
            logger.info(f" Has 'edit_post_data': {'edit_post_data' in context}")
            logger.info(f" Has 'medhisdrug_formset': {'medhisdrug_formset' in context}")
            if 'formsets' in forms_dict:
                logger.info(f" Formsets in forms_dict: {list(forms_dict['formsets'].keys())}")
            
            return render(request, template_name, context)
        
        # Show security warnings
        if validation_result.get('warnings'):
            for warning in validation_result['warnings']:
                messages.warning(request, warning)
        
        # STEP 6: Set audit data
        patient_id = self._get_patient_id_from_instance(main_instance)
        site_id = getattr(main_instance, 'SITEID', None)
        
        self._set_audit_data(request, patient_id, site_id, all_changes, sanitized_reasons)
        
        # STEP 7: Save
        result = save_callback(request, forms_dict)
        
        if result:
            messages.success(request, 'Cập nhật thành công với audit trail!')
            return redirect(redirect_url)
        else:
            return self._render_error(request, forms_dict, template_name, extra_context)
    
    def _capture_complex_old_data(self, main_instance, forms_config):
        """Capture old data including formsets"""
        # Start with multi-form data
        all_old_data = self._capture_all_old_data(main_instance, forms_config)
        
        # Add formsets
        all_old_data['formsets'] = {}
        
        for name, config in forms_config.get('formsets', {}).items():
            formset_old_data = {}
            
            #  Support both InlineFormSet (instance+related_name) and ModelFormSet (queryset)
            instance = config.get('instance')
            queryset = config.get('queryset')
            
            if instance:
                # InlineFormSet pattern: use related_name to get manager
                related_name = config.get('related_name', name)
                manager = getattr(instance, related_name, None)
                
                if manager:
                    for obj in manager.all():
                        old_data = self.detector.extract_old_data(obj)
                        old_data = {k: v for k, v in old_data.items() 
                                   if k not in self.metadata_fields}
                        formset_old_data[obj.pk] = old_data
            
            elif queryset is not None:
                # ModelFormSet pattern: iterate queryset directly
                for obj in queryset:
                    old_data = self.detector.extract_old_data(obj)
                    old_data = {k: v for k, v in old_data.items() 
                               if k not in self.metadata_fields}
                    formset_old_data[obj.pk] = old_data
            
            all_old_data['formsets'][name] = formset_old_data
            logger.info(f" Captured {len(formset_old_data)} old {name}")
        
        return all_old_data
    

    def _initialize_complex_forms(self, request, forms_config):
        """Initialize forms + formsets"""
        # Start with multi-form initialization
        forms_dict = self._initialize_all_forms(request, forms_config)
        
        # Add formsets
        forms_dict['formsets'] = {}
        
        for name, config in forms_config.get('formsets', {}).items():
            formset_class = config['class']
            prefix = config.get('prefix')
            instance = config.get('instance')  # ← Optional for InlineFormSet
            queryset = config.get('queryset')  # ← Optional for ModelFormSet
            formset_kwargs = config.get('kwargs', {})  # Get extra kwargs
            
            #  THÊM: Log formset initialization
            logger.info(f" Initializing formset '{name}':")
            logger.info(f"   Class: {formset_class}")
            logger.info(f"   Prefix: {prefix}")
            logger.info(f"   Instance: {instance}")
            logger.info(f"   Queryset: {queryset}")
            
            #  THÊM: Log POST data for this formset
            if prefix:
                post_keys = [k for k in request.POST.keys() if k.startswith(f'{prefix}-')]
                logger.info(f"   POST keys with prefix '{prefix}': {len(post_keys)}")
                for key in post_keys[:5]:  # Show first 5
                    logger.info(f"      {key}: {request.POST[key]}")
            else:
                post_keys = [k for k in request.POST.keys() if k.startswith('form-')]
                logger.info(f"   POST keys with default prefix 'form-': {len(post_keys)}")
                for key in post_keys[:5]:  # Show first 5
                    logger.info(f"      {key}: {request.POST[key]}")
            
            #  Support both InlineFormSet (instance) and ModelFormSet (queryset)
            kwargs = {'prefix': prefix} if prefix else {}
            
            if instance is not None:
                # InlineFormSet pattern (FU28, FU90, Discharge)
                kwargs['instance'] = instance
            elif queryset is not None:
                # ModelFormSet pattern (Laboratory)
                kwargs['queryset'] = queryset
            
            # Add extra kwargs (like siteid for forms)
            kwargs.update(formset_kwargs)
            
            forms_dict['formsets'][name] = formset_class(request.POST, **kwargs)
            
            #  THÊM: Log formset after creation
            formset = forms_dict['formsets'][name]
            logger.info(f"   Created with {len(formset.forms)} forms")
            logger.info(f"   Management form TOTAL_FORMS: {formset.management_form['TOTAL_FORMS'].value()}")
        
        return forms_dict
    
    def _validate_complex_forms(self, forms_dict):
        """Validate forms + formsets"""
        # Validate main + related
        valid = self._validate_all_forms(forms_dict)
        
        # Log main form
        logger.info(f" Main form valid: {forms_dict['main'].is_valid()}")
        if not forms_dict['main'].is_valid():
            logger.error(f" Main form errors: {forms_dict['main'].errors}")
        
        # Log related forms
        for name, form in forms_dict.get('related', {}).items():
            is_valid = form.is_valid()
            logger.info(f" Related '{name}' valid: {is_valid}")
            if not is_valid:
                logger.error(f" Related '{name}' errors: {form.errors}")
        
        #  FIX: Validate formsets
        for name, formset in forms_dict.get('formsets', {}).items():  # ← .items()
            formset_valid = formset.is_valid()
            logger.info(f" Formset '{name}' valid: {formset_valid}")
            
            if not formset_valid:
                logger.error(f" Formset '{name}' errors: {formset.errors}")
                logger.error(f" Formset '{name}' non_form_errors: {formset.non_form_errors()}")
                
                # Log management form
                mgmt = formset.management_form
                logger.error(f" Management form:")
                logger.error(f"   TOTAL_FORMS: {mgmt['TOTAL_FORMS'].value()}")
                logger.error(f"   INITIAL_FORMS: {mgmt['INITIAL_FORMS'].value()}")
            
            valid = formset_valid and valid
        
        logger.info(f" Overall validation result: {valid}")
        return valid
    
    def _detect_complex_changes(self, all_old_data, forms_dict):
        """Detect changes in forms + formsets"""
        # Start with multi-form changes
        all_changes = self._detect_multi_form_changes(all_old_data, forms_dict)
        
        # Add formset changes
        for name, formset in forms_dict.get('formsets', {}).items():
            formset_old_data = all_old_data['formsets'].get(name, {})
            
            for form in formset.forms:
                if not form.cleaned_data:
                    continue
                
                instance = form.instance
                
                # Check DELETE
                if form.cleaned_data.get('DELETE'):
                    if instance.pk:
                        all_changes.append({
                            'field': f'{name}_{instance.pk}_DELETED',
                            'old_value': str(instance),
                            'new_value': None,
                            'old_display': f'{instance} (Deleted)',
                            'new_display': 'Deleted',
                        })
                    continue
                
                # Check existing item changes
                if instance.pk and instance.pk in formset_old_data:
                    old_data = formset_old_data[instance.pk]
                    new_data = self.detector.extract_new_data(form)
                    new_data = {k: v for k, v in new_data.items() 
                               if k not in self.metadata_fields}
                    
                    #  FIX: Only compare fields present in the form
                    # Filter old_data to match new_data fields
                    old_data_filtered = {k: v for k, v in old_data.items() if k in new_data}
                    
                    changes = self.detector.detect_changes(old_data_filtered, new_data)
                    
                    # Enhanced: Add human-readable display name for formset changes
                    for change in changes:
                        # Keep technical field name for reason collection
                        change['field'] = f"{name}_{instance.pk}_{change['field']}"
                        
                        # Add display_name for modal UI
                        display_name = self._get_formset_display_name(instance, change['field'])
                        if display_name:
                            change['display_name'] = display_name
                    
                    all_changes.extend(changes)
                
                # New item - SKIP (don't require reason for adding new items)
                # elif not instance.pk:
                #     new_data = self.detector.extract_new_data(form)
                #     display_field = self._get_display_field(new_data)
                #     
                #     all_changes.append({
                #         'field': f'{name}_NEW_{display_field}',
                #         'old_value': None,
                #         'new_value': display_field,
                #         'old_display': 'N/A',
                #         'new_display': str(display_field),
                #     })
        
        return all_changes
    
    def _get_formset_display_name(self, instance, technical_field: str) -> str:
        """
        Generate human-readable display name for formset field changes
        
        Args:
            instance: Model instance (e.g., LaboratoryTest)
            technical_field: Full field name like "laboratory_tests_2163_RESULT"
            
        Returns:
            Human-readable name like "Eosinophils - Result"
        """
        # Extract the actual field name from technical_field
        # Format: "formset_name_pk_FIELDNAME"
        parts = technical_field.split('_')
        if len(parts) < 3:
            return None
        
        # Last part is the field name (RESULT, PERFORMED, PERFORMEDDATE, etc.)
        field_name = parts[-1]
        
        # Map field names to Vietnamese labels
        field_labels = {
            'RESULT': 'Kết quả',
            'PERFORMED': 'Đã thực hiện',
            'PERFORMEDDATE': 'Ngày thực hiện',
            'DRUGNAME': 'Tên thuốc',
            'ICDCODE': 'Mã ICD',
            'SPECIMENTYPE': 'Loại mẫu',
            'SENSITIVITY_LEVEL': 'LEVEL',
            'IZDIAM': 'Zone Diameter',
            'MIC': 'MIC',
        }
        
        field_label = field_labels.get(field_name, field_name)
        
        # For AntibioticSensitivity: show AST_ID (e.g., "003-A-001-C3-AMP - LEVEL")
        if hasattr(instance, 'AST_ID') and hasattr(instance, 'ANTIBIOTIC_NAME'):
            try:
                ast_id = instance.AST_ID or 'Unknown'
                return f"{ast_id} - {field_label}"
            except Exception as e:
                logger.warning(f"Failed to get AST_ID: {e}")
        
        # For LaboratoryTest: use get_TESTTYPE_display()
        if hasattr(instance, 'get_TESTTYPE_display'):
            try:
                test_name = instance.get_TESTTYPE_display()
                if test_name:
                    return f"{test_name} - {field_label}"
            except Exception as e:
                logger.warning(f"Failed to get TESTTYPE display: {e}")
        
        # For other models: try TESTTYPE field directly
        if hasattr(instance, 'TESTTYPE'):
            return f"{instance.TESTTYPE} - {field_label}"
        
        # Try DRUGNAME
        elif hasattr(instance, 'DRUGNAME'):
            return f"{instance.DRUGNAME} - {field_label}"
        
        # Try ICDCODE
        elif hasattr(instance, 'ICDCODE'):
            return f"ICD {instance.ICDCODE} - {field_label}"
        
        # Fallback to string representation
        else:
            instance_str = str(instance)
            if instance_str and instance_str != 'None':
                return f"{instance_str} - {field_label}"
            return None
    
    def _get_display_field(self, data):
        """Get display value from form data"""
        # Try common fields
        for field in ['DRUGNAME', 'ICDCODE', 'TESTTYPE', 'SPECIMENTYPE']:
            if field in data:
                return data[field]
        
        # Return first non-empty value
        for value in data.values():
            if value:
                return str(value)
        
        return 'New item'


def process_crf_update(
    request,
    instance,
    form_class,
    template_name: str,
    redirect_url: str,
    extra_context: Dict = None,
    forms_config: Dict = None,
    save_callback: Callable = None,
    form_kwargs: Dict = None,
    skip_change_reason: Optional[Callable] = None, 
):
    """
    Universal CRF update processor - Auto-detects complexity
    
    Args:
        request: HttpRequest
        instance: Main model instance
        form_class: Form class (for simple forms)
        template_name: Template path
        redirect_url: Success redirect URL
        extra_context: Additional template context
        forms_config: Config for complex forms (optional)
        save_callback: Custom save function (optional)
    
    Usage:
        # Simple form (Tier 1 - Screening, Sample)
        return process_crf_update(
            request=request,
            instance=screening_case,
            form_class=ScreeningCaseForm,
            template_name='screening_form.html',
            redirect_url=reverse('...'),
            extra_context={...}
        )
        
        # Complex forms (Tier 3 - Enrollment, Follow-up, Discharge)
        return process_crf_update(
            request=request,
            instance=enrollment_case,
            form_class=None,  # Not used for complex
            template_name='enrollment_form.html',
            redirect_url=reverse('...'),
            forms_config={
                'main': {'class': EnrollmentCaseForm, 'instance': enrollment_case},
                'related': {
                    'underlying': {'class': UnderlyingConditionForm, 'instance': underlying}
                },
                'formsets': {
                    'medications': {
                        'class': MedHisDrugFormSet,
                        'instance': enrollment_case,
                        'prefix': 'medications',
                        'related_name': 'medhisdrug_set'
                    }
                }
            },
            save_callback=save_enrollment_and_related,
            extra_context={...}
        )
    """
    
    # Auto-detect which tier to use
    if forms_config and save_callback:
        # Tier 3: Complex forms with formsets
        logger.info(" Auto-detected: Complex form with formsets (Tier 3)")
        processor = ComplexAuditProcessor()
        return processor.process_complex_update(
            request=request,
            main_instance=instance,
            forms_config=forms_config,
            save_callback=save_callback,
            template_name=template_name,
            redirect_url=redirect_url,
            extra_context=extra_context,
            skip_change_reason=skip_change_reason,
        )
    
    elif forms_config:
        # Tier 2: Multiple related forms
        logger.info(" Auto-detected: Multiple related forms (Tier 2)")
        processor = MultiFormAuditProcessor()
        return processor.process_multi_form_update(
            request=request,
            main_instance=instance,
            forms_config=forms_config,
            save_callback=save_callback,
            template_name=template_name,
            redirect_url=redirect_url,
            extra_context=extra_context
        )
    
    else:
        # Tier 1: Simple single form
        logger.info(" Auto-detected: Simple single form (Tier 1)")
        processor = AuditProcessor()
        return processor.process_form_update(
            request=request,
            instance=instance,
            form_class=form_class,
            template_name=template_name,
            redirect_url=redirect_url,
            extra_context=extra_context,
            form_kwargs=form_kwargs,
        )


def process_crf_create(
    request,
    form_class,
    template_name: str,
    redirect_url: str,
    pre_save_callback: Callable = None,
    post_save_callback: Callable = None,
    extra_context: Dict = None,
    form_kwargs: Dict = None,
):
    """
    Simple CRF creation processor (NO AUDIT)
    
    Creation doesn't need audit trail because there are no "changes" to track.
    Only updates need change tracking.
    
    Args:
        request: HttpRequest
        form_class: Form class
        template_name: Template path
        redirect_url: Success redirect URL
        pre_save_callback: Function called before save(instance)
        post_save_callback: Function called after save(instance), can return HttpResponse
        extra_context: Additional template context
    
    Usage:
        return process_crf_create(
            request=request,
            form_class=ScreeningCaseForm,
            template_name='screening_form.html',
            redirect_url=reverse('...'),
            pre_save_callback=lambda instance: setattr(instance, 'SITEID', 'SITE01'),
            post_save_callback=None,
            extra_context={'is_create': True}
        )
    """
    logger.info("=== CRF CREATE (NO AUDIT) ===")
    
    if request.method != 'POST':
        raise ValueError("process_crf_create requires POST method")
    
    if form_kwargs is None:
        form_kwargs = {}
    
    # Create form
    form = form_class(request.POST, request.FILES, **form_kwargs)
    
    if not form.is_valid():
        logger.error(f" Form validation failed: {form.errors}")
        messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi!')
        
        context = {
            'form': form,
            'is_create': True,
            **(extra_context or {}),
        }
        
        return render(request, template_name, context)
    
    # Save
    try:
        logger.info(" Form valid, creating...")
        
        with transaction.atomic():
            instance = form.save(commit=False)
            
            # Pre-save callback
            if pre_save_callback:
                pre_save_callback(instance)
            
            # Set metadata
            if hasattr(instance, 'version'):
                instance.version = 0
            
            if hasattr(instance, 'last_modified_by_id'):
                instance.last_modified_by_id = request.user.id
            
            if hasattr(instance, 'last_modified_by_username'):
                instance.last_modified_by_username = request.user.username
            
            instance.save()
            
            logger.info(f" Created successfully!")
        
        messages.success(request, 'Tạo mới thành công!')
        
        # Post-save callback
        if post_save_callback:
            result = post_save_callback(instance)
            if result:
                return result
        
        return redirect(redirect_url)
        
    except Exception as e:
        logger.error(f" Create failed: {e}", exc_info=True)
        messages.error(request, f'Lỗi khi tạo: {str(e)}')
        
        context = {
            'form': form,
            'is_create': True,
            **(extra_context or {}),
        }
        
        return render(request, template_name, context)


# ==========================================
# LEGACY ALIASES (for backwards compatibility)
# ==========================================

def process_simple_form_update(request, instance, form_class, template_name,
                               redirect_url, extra_context=None):
    """
    Alias for simple form update (Tier 1)
    Redirects to process_crf_update without forms_config
    """
    return process_crf_update(
        request=request,
        instance=instance,
        form_class=form_class,
        template_name=template_name,
        redirect_url=redirect_url,
        extra_context=extra_context
    )


def process_multi_form_update(request, main_instance, forms_config, save_callback,
                              template_name, redirect_url, extra_context=None):
    """
    Alias for multi-form update (Tier 2)
    Redirects to process_crf_update with forms_config (no formsets)
    """
    return process_crf_update(
        request=request,
        instance=main_instance,
        form_class=None,
        template_name=template_name,
        redirect_url=redirect_url,
        extra_context=extra_context,
        forms_config=forms_config,
        save_callback=save_callback
    )


def process_complex_update(request, main_instance, forms_config, save_callback,
                           template_name, redirect_url, extra_context=None,skip_change_reason=None,):
    """
    Alias for complex form update (Tier 3)
    Redirects to process_crf_update with forms_config (including formsets)
    """
    return process_crf_update(
        request=request,
        instance=main_instance,  #  Map main_instance → instance
        form_class=None,
        template_name=template_name,
        redirect_url=redirect_url,
        extra_context=extra_context,
        forms_config=forms_config,
        save_callback=save_callback,
        skip_change_reason=skip_change_reason
    )