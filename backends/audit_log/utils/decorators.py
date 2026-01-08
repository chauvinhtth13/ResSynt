# backends/audit_log/utils/decorators.py
"""
🌐 BASE Audit Log Decorator - Shared across all studies

FIXED: Audit log decorator - Proper data structure for checksum
Generic decorator that works with any study by accepting model classes as parameters
"""
import logging
from functools import wraps
from django.db import transaction
from backends.audit_log.models import AuditLog, AuditLogDetail
from .helpers import get_client_ip

logger = logging.getLogger(__name__)


def audit_log(model_name: str, get_patient_id_from: str = 'usubjid', 
              scr_case_model=None, scr_contact_model=None):
    """
    🌐 GENERIC Audit log decorator with automatic CREATE/VIEW logging
    
    Works with any study by accepting model classes as parameters.
    Automatically detects CREATE action from URL pattern (e.g., /create/, /enrollment_case_create/)
    
    Args:
        model_name: Name of the model (e.g., 'SCREENINGCASE')
        get_patient_id_from: Parameter name in URL kwargs for patient ID (default 'usubjid')
        scr_case_model: Optional - SCR_CASE model class for SITEID lookup (patient)
        scr_contact_model: Optional - SCR_CONTACT model class for SITEID lookup (contact)
    
    Example:
        # In study_43en views:
        from backends.studies.study_43en.models.patient import SCR_CASE
        from backends.studies.study_43en.models.contact import SCR_CONTACT
        
        @audit_log('SCREENINGCASE', get_patient_id_from='usubjid', 
                   scr_case_model=SCR_CASE, scr_contact_model=SCR_CONTACT)
        def my_view(request, usubjid):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 🔧 FIX: Get patient_id with case-insensitive lookup
            patient_id = kwargs.get(get_patient_id_from)
            
            # ✅ If not found, try case-insensitive search
            if not patient_id:
                for key, value in kwargs.items():
                    if key.lower() == get_patient_id_from.lower():
                        patient_id = value
                        break
            
            logger.debug(f"[AuditLog] View: {view_func.__name__} | Patient ID param: {get_patient_id_from} | Found: {patient_id}")
            
            # Call view FIRST to let it set audit_data
            response = view_func(request, *args, **kwargs)
            
            # Get audit_data from request
            audit_data = getattr(request, 'audit_data', {})
            
            # Determine action - Priority order:
            # 1. From audit_data (set by view) - Most accurate
            # 2. Auto-detect CREATE from URL pattern
            # 3. From request method + patient_id - Fallback
            if audit_data.get('action'):
                action = audit_data.get('action')
            elif request.method == 'GET':
                action = 'VIEW'
            elif request.method == 'POST':
                # Auto-detect CREATE from URL path
                path = request.path.lower()
                if '/create' in path or '_create' in path:
                    action = 'CREATE'
                else:
                    action = 'UPDATE'
            else:
                action = 'UNKNOWN'
            
            # ✅ NEW: Auto-log CREATE and VIEW even without audit_data
            if request.user.is_authenticated:
                if action == 'UPDATE' and audit_data:
                    # UPDATE with changes → full audit log
                    try:
                        _create_audit_log_with_details(
                            request=request,
                            action=action,
                            model_name=model_name,
                            patient_id=patient_id or audit_data.get('patient_id'),
                            audit_data=audit_data,
                            scr_case_model=scr_case_model,
                            scr_contact_model=scr_contact_model
                        )
                    except Exception as e:
                        logger.error(f"Audit log error: {e}", exc_info=True)
                
                elif action == 'CREATE':
                    # CREATE → log without details (no "changes")
                    try:
                        _create_simple_audit_log(
                            request=request,
                            action=action,
                            model_name=model_name,
                            patient_id=patient_id,
                            scr_case_model=scr_case_model,
                            scr_contact_model=scr_contact_model
                        )
                    except Exception as e:
                        logger.error(f"CREATE audit log error: {e}", exc_info=True)
                
                elif action == 'VIEW':
                    # VIEW → log without details
                    try:
                        _create_simple_audit_log(
                            request=request,
                            action=action,
                            model_name=model_name,
                            patient_id=patient_id,
                            scr_case_model=scr_case_model,
                            scr_contact_model=scr_contact_model
                        )
                    except Exception as e:
                        logger.error(f"VIEW audit log error: {e}", exc_info=True)
            
            return response
        
        return _wrapped_view
    return decorator


def _create_simple_audit_log(request, action, model_name, patient_id,
                             scr_case_model=None, scr_contact_model=None):
    """
    🌐 GENERIC Create simple audit log for CREATE/VIEW (no change details)
    
    Automatically extracts site_id from multiple sources.
    Uses provided model classes for SITEID lookup.
    """
    # Get site_id - Priority order:
    # 1. From audit_data (set by view)
    # 2. Query from database using patient_id (if models provided)
    # 3. From session
    # 4. Extract from patient_id string pattern
    audit_data = getattr(request, 'audit_data', {})
    site_id = audit_data.get('site_id')
    
    # 🔧 FIX: Try to query from database with patient_id (USUBJID or SCRID)
    if not site_id and patient_id:
        try:
            patient_id_str = str(patient_id)
            
            # Try USUBJID format (e.g., 011-A-001) using SCR_CASE model
            if scr_case_model:
                scr_case = scr_case_model.objects.filter(USUBJID=patient_id_str).values_list('SITEID', flat=True).first()
                if scr_case:
                    site_id = scr_case
                    logger.debug(f"Got SITEID from SCR_CASE (USUBJID): {site_id}")
                
                # ✅ Try SCRID format for patient screening (e.g., PS-011-0001)
                if not site_id and patient_id_str.startswith('PS-'):
                    scr_case = scr_case_model.objects.filter(SCRID=patient_id_str).values_list('SITEID', flat=True).first()
                    if scr_case:
                        site_id = scr_case
                        logger.debug(f"Got SITEID from SCR_CASE (SCRID): {site_id}")
            
            # ✅ Try SCRID format for contact screening (e.g., CS-011-0001) using SCR_CONTACT model
            if not site_id and scr_contact_model and patient_id_str.startswith('CS-'):
                scr_contact = scr_contact_model.objects.filter(SCRID=patient_id_str).values_list('SITEID', flat=True).first()
                if scr_contact:
                    site_id = scr_contact
                    logger.debug(f"Got SITEID from SCR_CONTACT (SCRID): {site_id}")
                    
        except Exception as e:
            logger.debug(f"Could not query SITEID from database: {e}")
    
    if not site_id:
        site_id = request.session.get('selected_site_id')
    
    if not site_id or site_id == 'all':
        # Try extract from patient_id string (format: 020-A-001)
        if patient_id:
            parts = str(patient_id).split('-')
            if len(parts) > 1:
                site_id = parts[0]
    
    # Create audit log (no details)
    audit_log_entry = AuditLog(
        user_id=request.user.id,
        username=request.user.username,
        action=action,
        model_name=model_name,
        patient_id=str(patient_id) if patient_id else 'unknown',
        SITEID=site_id,
        reason=f'{action} action',  # Simple reason
        ip_address=get_client_ip(request),
        session_id=request.session.session_key if hasattr(request, 'session') else None,
    )
    
    # Generate checksum for simple log
    audit_log_entry._temp_checksum_data = {
        'user_id': request.user.id,
        'username': request.user.username,
        'action': action,
        'model_name': model_name,
        'patient_id': str(patient_id) if patient_id else 'unknown',
        'timestamp': '',
        'old_data': {},
        'new_data': {},
        'reason': f'{action} action',
    }
    
    audit_log_entry.save()
    
    logger.info(
        f"✅ Simple audit log: {request.user.username} {action} "
        f"{model_name} {patient_id}"
    )


def _create_audit_log_with_details(request, action, model_name, 
                                   patient_id, audit_data,
                                   scr_case_model=None, scr_contact_model=None):
    """
    🌐 GENERIC Create audit log with proper data structure
    
    Uses provided model classes for SITEID lookup.
    """
    
    site_id = audit_data.get('site_id')
    if not site_id and patient_id:
        parts = str(patient_id).split('-')
        if len(parts) > 1:
            site_id = parts[0]
    
    if not site_id:
        site_id = request.session.get('selected_site_id')
    
    # Prepare details BEFORE creating audit log
    changes = audit_data.get('changes', [])
    reasons = audit_data.get('reasons_json', {})
    
    details_list = []
    old_data_dict = {}
    new_data_dict = {}
    
    for change in changes:
        field_name = change['field']
        old_value = change.get('old_value', '')
        new_value = change.get('new_value', '')
        reason = reasons.get(field_name, '')
        
        # Build details
        details_list.append({
            'field_name': field_name,
            'old_value': str(old_value),
            'new_value': str(new_value),
            'reason': reason
        })
        
        # Build old_data and new_data for checksum
        old_data_dict[field_name] = old_value
        new_data_dict[field_name] = new_value
    
    with transaction.atomic():
        # Create audit log with proper data
        audit_log_entry = AuditLog(
            user_id=request.user.id,
            username=request.user.username,
            action=action,
            model_name=model_name,
            patient_id=str(patient_id) if patient_id else 'unknown',
            SITEID=site_id,
            reason=audit_data.get('reason', ''),
            ip_address=get_client_ip(request),
            session_id=request.session.session_key if hasattr(request, 'session') else None,
        )
        
        # Pass proper structure for checksum
        audit_log_entry._temp_checksum_data = {
            'user_id': request.user.id,
            'username': request.user.username,
            'action': action,
            'model_name': model_name,
            'patient_id': str(patient_id) if patient_id else 'unknown',
            'timestamp': '',  # Will be filled by save()
            'old_data': old_data_dict,
            'new_data': new_data_dict,
            'reason': audit_data.get('reason', ''),
        }
        
        # Store details for later
        audit_log_entry._temp_details = details_list
        
        # Save main log (will generate checksum using _temp_checksum_data)
        audit_log_entry.save()
        
        # Create details
        for detail_data in details_list:
            AuditLogDetail.objects.create(
                audit_log=audit_log_entry,
                field_name=detail_data['field_name'],
                old_value=detail_data['old_value'],
                new_value=detail_data['new_value'],
                reason=detail_data['reason']
            )
        
        logger.info(
            f"✅ Audit log created: {request.user.username} {action} "
            f"{model_name} {patient_id} ({len(details_list)} changes)"
        )
