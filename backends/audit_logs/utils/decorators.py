# backends/audit_logs/utils/decorators.py
"""
BASE Audit Log Decorator - Shared across all studies

LIBRARY MODE: Model classes are passed directly as parameters.
Each study passes their own AuditLog/AuditLogDetail models.

Database Schema:
    Audit tables are created in 'logging' schema:
    - logging.audit_log: Main audit log entries
    - logging.audit_log_detail: Field-level change details

Usage:
    from backends.studies.study_43en.models import AuditLog, AuditLogDetail
    
    @audit_log('SCREENINGCASE', audit_log_model=AuditLog, audit_log_detail_model=AuditLogDetail)
    def my_view(request):
        ...
"""
import logging
from functools import wraps
from django.db import transaction
from .helpers import get_client_ip

logger = logging.getLogger(__name__)


# ==========================================
# SHARED UTILITIES
# ==========================================

def resolve_site_id(request, patient_id, scr_case_model=None, scr_contact_model=None):
    """
    Resolve SITEID from multiple sources - shared utility to avoid duplication
    
    Priority order:
    1. From audit_data (set by view)
    2. Query from database using patient_id (if models provided)
    3. From session
    4. Extract from patient_id string pattern (format: XXX-X-XXX)
    
    Args:
        request: HttpRequest
        patient_id: Patient identifier (USUBJID or SCRID)
        scr_case_model: Optional - Model class for patient lookup
        scr_contact_model: Optional - Model class for contact lookup
    
    Returns:
        str: Site ID or None
    """
    audit_data = getattr(request, 'audit_data', {})
    site_id = audit_data.get('site_id')
    
    # Try database lookup
    if not site_id and patient_id:
        site_id = _lookup_site_from_db(patient_id, scr_case_model, scr_contact_model)
    
    # Try session
    if not site_id:
        site_id = request.session.get('selected_site_id')
    
    # Try extract from patient_id pattern (XXX-X-XXX)
    if not site_id or site_id == 'all':
        if patient_id:
            parts = str(patient_id).split('-')
            if len(parts) > 1:
                site_id = parts[0]
    
    return site_id


def _lookup_site_from_db(patient_id, scr_case_model=None, scr_contact_model=None):
    """
    Query SITEID from database models with caching
    
    PERFORMANCE: Cache results to avoid repeated DB queries for same patient
    
    Returns:
        str: Site ID or None
    """
    from django.core.cache import cache
    
    patient_id_str = str(patient_id)
    
    # Try cache first
    cache_key = f'site_lookup:{patient_id_str}'
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    site_id = None
    
    try:
        # Try USUBJID format using SCR_CASE model
        if scr_case_model:
            site_id = scr_case_model.objects.filter(
                USUBJID=patient_id_str
            ).values_list('SITEID', flat=True).first()
            
            if not site_id and patient_id_str.startswith('PS-'):
                # Try SCRID format for patient screening (PS-XXX-XXXX)
                site_id = scr_case_model.objects.filter(
                    SCRID=patient_id_str
                ).values_list('SITEID', flat=True).first()
        
        # Try SCRID format for contact screening (CS-XXX-XXXX)
        if not site_id and scr_contact_model and patient_id_str.startswith('CS-'):
            site_id = scr_contact_model.objects.filter(
                SCRID=patient_id_str
            ).values_list('SITEID', flat=True).first()
                
    except Exception as e:
        logger.debug("Could not query SITEID from database: %s", e)
    
    # Cache result (even None to avoid repeated failed lookups)
    if site_id:
        cache.set(cache_key, site_id, 300)  # Cache for 5 minutes
    
    return site_id


def audit_log(model_name: str, get_patient_id_from: str = 'usubjid', 
              scr_case_model=None, scr_contact_model=None,
              audit_log_model=None, audit_log_detail_model=None):
    """
    GENERIC Audit log decorator with automatic CREATE/VIEW logging
    
    Works with any study by accepting model classes as parameters.
    Automatically detects CREATE action from URL pattern.
    
    Args:
        model_name: Name of the model (e.g., 'SCREENINGCASE')
        get_patient_id_from: Parameter name in URL kwargs for patient ID (default 'usubjid')
        scr_case_model: Optional - SCR_CASE model class for SITEID lookup
        scr_contact_model: Optional - SCR_CONTACT model class for SITEID lookup
        audit_log_model: Optional - AuditLog model class (defaults to backends.audit_logs.models.AuditLog)
        audit_log_detail_model: Optional - AuditLogDetail model class (defaults to backends.audit_logs.models.AuditLogDetail)
    
    Example:
        from backends.studies.study_43en.models.patient import SCR_CASE
        
        @audit_log('SCREENINGCASE', 
                   get_patient_id_from='usubjid', 
                   scr_case_model=SCR_CASE)
        def my_view(request, usubjid):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Use provided models - they must be passed from each study
            nonlocal audit_log_model, audit_log_detail_model
            if not audit_log_model or not audit_log_detail_model:
                # Models must be provided - can't use default since they are per-study now
                raise ValueError(
                    "audit_log_model and audit_log_detail_model must be provided. "
                    "Import from your study's models, e.g.: "
                    "from backends.studies.study_43en.models import AuditLog, AuditLogDetail"
                )
            
            # Get patient_id with case-insensitive lookup
            patient_id = kwargs.get(get_patient_id_from)
            
            # If not found, try case-insensitive search
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
            
            # NEW: Auto-log CREATE and VIEW even without audit_data
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
                            scr_contact_model=scr_contact_model,
                            audit_log_model=audit_log_model,
                            audit_log_detail_model=audit_log_detail_model
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
                            scr_contact_model=scr_contact_model,
                            audit_log_model=audit_log_model
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
                            scr_contact_model=scr_contact_model,
                            audit_log_model=audit_log_model
                        )
                    except Exception as e:
                        logger.error(f"VIEW audit log error: {e}", exc_info=True)
            
            return response
        
        return _wrapped_view
    return decorator


def _build_checksum_data(user_id, username, action, model_name, patient_id_str,
                         reason, old_data=None, new_data=None):
    """
    Build checksum data dict - shared utility to avoid duplication
    
    Args:
        user_id: User ID
        username: Username
        action: Action type (CREATE, VIEW, UPDATE)
        model_name: Name of the model
        patient_id_str: Patient ID as string
        reason: Reason text
        old_data: Dict of old values (optional)
        new_data: Dict of new values (optional)
    
    Returns:
        dict: Checksum data structure
    """
    return {
        'user_id': user_id,
        'username': username,
        'action': action,
        'model_name': model_name,
        'patient_id': patient_id_str,
        'timestamp': '',  # Will be filled by save()
        'old_data': old_data or {},
        'new_data': new_data or {},
        'reason': reason,
    }


def _create_simple_audit_log(request, action, model_name, patient_id,
                             scr_case_model=None, scr_contact_model=None,
                             audit_log_model=None):
    """
    GENERIC Create simple audit log for CREATE/VIEW (no change details)
    
    Automatically extracts site_id from multiple sources.
    Uses provided model classes for SITEID lookup.
    
    Args:
        request: Django request object
        action: Action type (CREATE, VIEW)
        model_name: Name of the model
        patient_id: Patient ID 
        scr_case_model: Optional SCR_CASE model for SITEID lookup
        scr_contact_model: Optional SCR_CONTACT model for SITEID lookup
        audit_log_model: REQUIRED - AuditLog model class from study app
    """
    if not audit_log_model:
        logger.warning("_create_simple_audit_log: audit_log_model not provided")
        return
    
    # Use shared utility for SITEID resolution
    site_id = resolve_site_id(request, patient_id, scr_case_model, scr_contact_model)
    
    patient_id_str = str(patient_id) if patient_id else 'unknown'
    
    # Create audit log (no details)
    audit_log_entry = audit_log_model(
        user_id=request.user.id,
        username=request.user.username,
        action=action,
        model_name=model_name,
        patient_id=patient_id_str,
        SITEID=site_id,
        reason=f'{action} action',
        ip_address=get_client_ip(request),
        session_id=request.session.session_key if hasattr(request, 'session') else None,
    )
    
    # Use shared helper for checksum data
    audit_log_entry._temp_checksum_data = _build_checksum_data(
        user_id=request.user.id,
        username=request.user.username,
        action=action,
        model_name=model_name,
        patient_id_str=patient_id_str,
        reason=f'{action} action'
    )
    
    audit_log_entry.save()
    
    logger.info(
        "Simple audit log: %s %s %s %s",
        request.user.username, action, model_name, patient_id
    )


def _create_audit_log_with_details(request, action, model_name, 
                                   patient_id, audit_data,
                                   scr_case_model=None, scr_contact_model=None,
                                   audit_log_model=None, audit_log_detail_model=None):
    """
    GENERIC Create audit log with proper data structure
    
    Uses provided model classes for SITEID lookup.
    
    Args:
        request: Django request object
        action: Action type (UPDATE)
        model_name: Name of the model
        patient_id: Patient ID
        audit_data: Dict containing changes, reasons_json, etc.
        scr_case_model: Optional SCR_CASE model for SITEID lookup
        scr_contact_model: Optional SCR_CONTACT model for SITEID lookup
        audit_log_model: REQUIRED - AuditLog model class from study app
        audit_log_detail_model: REQUIRED - AuditLogDetail model class from study app
    """
    if not audit_log_model or not audit_log_detail_model:
        logger.warning("_create_audit_log_with_details: audit models not provided")
        return
    
    # Use shared utility - but prefer audit_data first
    site_id = audit_data.get('site_id')
    if not site_id:
        site_id = resolve_site_id(request, patient_id, scr_case_model, scr_contact_model)
    
    patient_id_str = str(patient_id) if patient_id else 'unknown'
    
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
        
        details_list.append({
            'field_name': field_name,
            'old_value': str(old_value),
            'new_value': str(new_value),
            'reason': reason
        })
        
        old_data_dict[field_name] = old_value
        new_data_dict[field_name] = new_value
    
    reason_text = audit_data.get('reason', '')
    
    with transaction.atomic():
        audit_log_entry = audit_log_model(
            user_id=request.user.id,
            username=request.user.username,
            action=action,
            model_name=model_name,
            patient_id=patient_id_str,
            SITEID=site_id,
            reason=reason_text,
            ip_address=get_client_ip(request),
            session_id=request.session.session_key if hasattr(request, 'session') else None,
        )
        
        # Use shared helper for checksum data
        audit_log_entry._temp_checksum_data = _build_checksum_data(
            user_id=request.user.id,
            username=request.user.username,
            action=action,
            model_name=model_name,
            patient_id_str=patient_id_str,
            reason=reason_text,
            old_data=old_data_dict,
            new_data=new_data_dict
        )
        
        audit_log_entry._temp_details = details_list
        audit_log_entry.save()
        
        # Bulk create details for better performance
        audit_log_detail_model.objects.bulk_create([
            audit_log_detail_model(
                audit_log=audit_log_entry,
                field_name=d['field_name'],
                old_value=d['old_value'],
                new_value=d['new_value'],
                reason=d['reason']
            ) for d in details_list
        ])
        
        logger.info(
            "Audit log created: %s %s %s %s (%d changes)",
            request.user.username, action, model_name, patient_id, len(details_list)
        )
