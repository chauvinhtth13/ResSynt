# backend/studies/study_43en/utils/audit_log_cross_db.py

from functools import wraps
from django.db import transaction
from django.apps import apps
import logging

# Import models từ models package (sử dụng relative imports)
from ..models.audit_log import AuditLog
from ..models.patient import (
    CLI_AEHospEvent,
    CLI_Antibiotic,
    CLI_ClinicalCase,
    CLI_HospiProcess,
    CLI_ImproveSympt,
    CLI_LaboratoryTest,
    CLI_Microbiology,
    CLI_VasoIDrug,
    LAB_AntibioticSensitivity,
    SAM_SampleCollection,
    ScreeningCase, 
    EnrollmentCase, 
    DischargeCase,
    InitialAntibiotic,
    MainAntibiotic,
    FollowUpCase,
    FollowUpCase90,
    Rehospitalization,
    FollowUpAntibiotic,
    Rehospitalization90,
    FollowUpAntibiotic90
)
from ..models.contact import (
    ScreeningContact,
    EnrollmentContact,
    ContactMedHisDrug
)

from .audit_log_utils import safe_json_loads, normalize_value, find_reason_and_label

logger = logging.getLogger(__name__)



def get_client_ip(request):
    """Lấy địa chỉ IP của client."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    logger.debug(f"get_client_ip: IP address: {ip}")
    return ip

def log_action(request, action, model_name, patient_id, old_data=None, new_data=None, reason=None, reasons_dict=None):
    """Ghi nhật ký hành động của người dùng."""
    try:
        user = request.user if request.user.is_authenticated else None
        username = user.username if user else 'anonymous'
        
        old_data_clean = {}
        if old_data:
            for key, value in old_data.items():
                if not isinstance(value, (str, int, float, bool, dict, list, type(None))):
                    old_data_clean[key] = str(value)
                else:
                    old_data_clean[key] = value
        
        new_data_clean = {}
        if new_data:
            for key, value in new_data.items():
                if not isinstance(value, (str, int, float, bool, dict, list, type(None))):
                    new_data_clean[key] = str(value)
                else:
                    new_data_clean[key] = value
        
        # Trích xuất SITEID từ patient_id nếu có định dạng site-xxx
        site_id = None
        if isinstance(patient_id, str):
            parts = patient_id.split('-')
            if len(parts) > 1 and len(parts[0]) == 3:
                site_id = parts[0]
        
        # Lấy site_id từ session nếu không trích xuất được từ patient_id
        if not site_id and hasattr(request, 'session') and 'selected_site_id' in request.session:
            site_id = request.session.get('selected_site_id')
            
        logger.debug(f"log_action: Creating AuditLog: user={username}, action={action}, model_name={model_name}, patient_id={patient_id}, site_id={site_id}")
        logger.debug(f"log_action: old_data={old_data_clean}, new_data={new_data_clean}, reasons_dict={reasons_dict}, reason={reason}")
        
        AuditLog.objects.create(
            user=user,
            username=username,
            action=action,
            model_name=model_name,
            patient_id=str(patient_id),
            SITEID=site_id,
            old_data=old_data_clean or None,
            new_data=new_data_clean or None,
            ip_address=get_client_ip(request),
            reason=reason,
            reasons_json=reasons_dict
        )
    except Exception as e:
        logger.error(f"log_action: Error creating AuditLog: {e}")

def audit_log_decorator(model_name=None):
    """Decorator ghi log cho các view function."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            _model_name = model_name or view_func.__name__.split('_')[0].upper()
            logger.debug(f"audit_log_decorator: view={view_func.__name__}, model_name={_model_name}")
            
            patient_id = None
            for key in ['usubjid', 'id', 'pk', 'SCRID', 'USUBJID', 'ENROLLCONTACT_USUBJID', 'EPISODE']:
                if key in kwargs:
                    patient_id = kwargs[key]
                    break
            logger.debug(f"audit_log_decorator: patient_id={patient_id}")
            
            action = 'VIEW' if request.method == 'GET' else 'CREATE'
            if request.method == 'POST':
                if 'create' in view_func.__name__ or 'create' in request.path:
                    action = 'CREATE'
                elif 'update' in view_func.__name__ or 'update' in request.path:
                    action = 'UPDATE'
                elif 'delete' in view_func.__name__ or 'delete' in request.path:
                    action = 'DELETE'
                elif view_func.__name__ == 'clinical_form' and patient_id:
                    try:
                        screening_case = ScreeningCase.objects.get(USUBJID=patient_id)
                        enrollment_case = EnrollmentCase.objects.get(USUBJID=screening_case)
                        CLI_ClinicalCase.objects.get(USUBJID=enrollment_case)
                        action = 'UPDATE'
                    except (ScreeningCase.DoesNotExist, EnrollmentCase.DoesNotExist, CLI_ClinicalCase.DoesNotExist):
                        action = 'CREATE'
            logger.debug(f"audit_log_decorator: action={action}")
            
            # Lấy audit_data từ request nếu có
            audit_data = getattr(request, 'audit_data', {})
            old_data = audit_data.get('old_data', safe_json_loads(request.POST.get('oldDataJson'), {}))
            new_data = audit_data.get('new_data', safe_json_loads(request.POST.get('newDataJson'), {}))
            
            # Kiểm tra cả hai trường reasons_json và reasonsJson để tương thích với các form khác nhau
            reasons_data = request.POST.get('reasons_json')
            if not reasons_data:
                reasons_data = request.POST.get('reasonsJson')
            reasons_dict = audit_data.get('reasons_json', safe_json_loads(reasons_data, {}))
            
            reason = audit_data.get('reason', request.POST.get('change_reason', ''))

            # Nếu không có audit_data, thử lấy old_data từ model
            if action == 'UPDATE' and not old_data and patient_id:
                try:
                    model_classes = {
                        'SCREENINGCASE': 'ScreeningCase',
                        'ENROLLMENTCASE': 'EnrollmentCase',
                        'ENDCASECRF': 'EndCaseCRF',
                        'CONTACTENDCASECRF': 'ContactEndCaseCRF',
                        'CLINICALCASE': 'ClinicalCase',
                        'LABORATORYTEST': 'LaboratoryTest',
                        'MICROBIOLOGYCULTURE': 'MicrobiologyCulture',
                        'ANTIBIOTICSENSITIVITY': 'AntibioticSensitivity',
                        'VASOIDRUG': 'VasoIDrug',
                        'MAINANTIBIOTIC': 'MainAntibiotic',
                        'PRIORANTIBIOTIC': 'PriorAntibiotic',
                        'INITIALANTIBIOTIC': 'InitialAntibiotic',
                        'AEHOSPEVENT': 'AEHospEvent',
                        'SAMPLECOLLECTION': 'SampleCollection',
                        'FOLLOWUPFORM': 'FollowUpForm',
                        'FOLLOWUPCASE': 'FollowUpCase',
                        'FOLLOWUPCASE90': 'FollowUpCase90',
                        'REHOSPITALIZATION': 'Rehospitalization',
                        'FOLLOWUPANTIBIOTIC': 'FollowUpAntibiotic',
                        'REHOSPITALIZATION90': 'Rehospitalization90',
                        'FOLLOWUPANTIBIOTIC90': 'FollowUpAntibiotic90',
                        'SCREENINGCONTACT': 'ScreeningContact',
                        'ENROLLMENTCONTACT': 'EnrollmentContact',
                        'CONTACTMEDHISDRUG': 'ContactMedHisDrug',
                        'DISCHARGECASE': 'DischargeCase',
                        'IMPROVESYMPT': 'ImproveSympt',
                        'HOSPIPROCESS': 'HospiProcess'
                    }
                    if _model_name in model_classes:
                        model_class = apps.get_model('study_43en', model_classes[_model_name])
                        lookup_kwargs = {}
                        if _model_name == 'SCREENINGCASE':
                            lookup_kwargs['SCRID'] = patient_id
                        elif _model_name == 'SCREENINGCONTACT':
                            lookup_kwargs['SCRID'] = patient_id
                        elif _model_name in ['REHOSPITALIZATION', 'FOLLOWUPANTIBIOTIC', 'REHOSPITALIZATION90', 'FOLLOWUPANTIBIOTIC90', 'CONTACTMEDHISDRUG']:
                            # These models need both USUBJID and EPISODE
                            if 'EPISODE' in kwargs:
                                lookup_kwargs['USUBJID'] = patient_id
                                lookup_kwargs['EPISODE'] = kwargs['EPISODE']
                            else:
                                lookup_kwargs['id'] = patient_id
                        else:
                            lookup_kwargs['USUBJID'] = patient_id
                        # Không lấy first() cho LABORATORYTEST, dựa vào audit_data
                        logger.warning(f"audit_log_decorator: No old_data provided, skipping model fetch for {_model_name}")
                except Exception as e:
                    logger.error(f"audit_log_decorator: Error getting old data: {e}")
            
            # Nếu không có new_data, lấy từ request.POST
            if not new_data and request.method == 'POST':
                new_data = request.POST.dict()
                for field in ['csrfmiddlewaretoken', 'oldDataJson', 'newDataJson', 'reasonsJson', 'reasons_json', 'change_reason']:
                    if field in new_data:
                        del new_data[field]
                new_data = {k: v for k, v in new_data.items() if v.strip() != ''}
                logger.debug(f"audit_log_decorator: Retrieved new_data from POST: {new_data}")
            
            # Gọi view function gốc
            response = view_func(request, *args, **kwargs)
            
            # Ghi log nếu người dùng đã đăng nhập và có patient_id
            if request.user.is_authenticated and patient_id:
                logger.debug(f"audit_log_decorator: Logging action: view={view_func.__name__}, patient_id={patient_id}, action={action}")
                log_action(
                    request=request,
                    action=action,
                    model_name=_model_name,
                    patient_id=patient_id,
                    old_data=old_data,
                    new_data=new_data,
                    reason=reason,
                    reasons_dict=reasons_dict
                )
            
            return response
        return _wrapped_view
    return decorator