# backends/studies/study_43en/models/__init__.py
"""
Main models package for study_43en
Import all model subpackages for Django registry

AuditLog and AuditLogDetail are created via factory function from audit_logs.
This ensures makemigrations study_43en includes audit tables.
"""

# ==========================================
# AUDIT LOG MODELS (Created via factory)
# ==========================================
from backends.audit_logs.models.base import create_audit_models
AuditLog, AuditLogDetail = create_audit_models('study_43en')


# ==========================================
# BASE MODELS (MIXINS)
# ==========================================
from .base_models import AuditFieldsMixin, TimestampMixin, SiteFilteredMixin

# ==========================================
# STUDY 43EN MODELS
# ==========================================
# Import patient models
from .patient import *

# Import contact models  
from .contact import *

# Import standalone models
from .schedule import *


# ==========================================
# EXPORTS
# ==========================================
__all__ = [
    # ==========================================
    # AUDIT LOG MODELS
    # ==========================================
    'AuditLog',
    'AuditLogDetail',
    
    # ==========================================
    # BASE MODELS
    # ==========================================
    'AuditFieldsMixin',
    'TimestampMixin',
    'SiteFilteredMixin',
    
    # ==========================================
    # STUDY 43EN PATIENT MODELS
    # ==========================================
    # Screening & Enrollment
    'SCR_CASE',
    'ENR_CASE',
    'ENR_CASE_MedHisDrug',
    'UnderlyingCondition',
    
    # Clinical
    'CLI_CASE',
    'HospiProcess',
    'ImproveSympt',
    'LaboratoryTest',
    'OtherTest',
    'AEHospEvent',
    'HistorySymptom',
    'Symptom_72H',
    
    # Antibiotics & Drugs
    'PriorAntibiotic',
    'InitialAntibiotic',
    'MainAntibiotic',
    'VasoIDrug',
    
    # Sample & Lab
    'SAM_CASE',
    'LAB_Microbiology',
    'AntibioticSensitivity',
    
    # Follow-up
    'FU_CASE_28',
    'FU_CASE_90',
    'FollowUpAntibiotic',
    'FollowUpAntibiotic90',
    'Rehospitalization',
    'Rehospitalization90',
    
    # Discharge & End
    'DISCH_CASE',
    'DischargeICD',
    'EndCaseCRF',
    
    # Personal Data
    'PERSONAL_DATA',
    
    # ==========================================
    # STUDY 43EN CONTACT MODELS
    # ==========================================
    # (imported via contact subpackage)
]