# backends/studies/study_44en/models/__init__.py
"""
Main models package for study_44en

AuditLog and AuditLogDetail are created via factory function from audit_logs.
This ensures makemigrations study_44en includes audit tables.
"""

# ==========================================
# AUDIT LOG MODELS (Created via factory)
# ==========================================
from backends.audit_logs.models import create_audit_models
AuditLog, AuditLogDetail = create_audit_models('study_44en')

# ==========================================
# BASE MODELS (MIXINS)
# ==========================================
from .base_models import (
    AuditFieldsMixin,   
    TimestampMixin,
    SiteFilteredMixin,
    SiteFilteredManager,
    SiteFilteredQuerySet,
)

# ==========================================
# STUDY 44EN - HOUSEHOLD MODELS
# ==========================================
from .household import (
    # Main household
    HH_CASE,
    HH_Member,
    
    # Exposure
    HH_Exposure,
    HH_WaterSource,
    HH_WaterTreatment,
    HH_Animal,
    
    # Food
    HH_FoodFrequency,
    HH_FoodSource,
)

# ==========================================
# STUDY 44EN - INDIVIDUAL MODELS
# ==========================================
from .individual import (
    # Main individual
    Individual,
    Individual_Exposure,
    
    # Water
    Individual_WaterSource,
    Individual_WaterTreatment,
    
    # Medical history
    Individual_Comorbidity,
    Individual_Vaccine,
    Individual_Hospitalization,
    Individual_Medication,
    
    # Lifestyle
    Individual_FoodFrequency,
    Individual_Travel,
    
    # Follow-up
    Individual_FollowUp,
    Individual_Symptom,
    Individual_Sample,
    FollowUp_Hospitalization,
)

# ==========================================
# PERSONAL DATA (PII - Encrypted)
# ==========================================
from .per_data import HH_PERSONAL_DATA


# ==========================================
# EXPORTS
# ==========================================
__all__ = [
    # Audit Log
    'AuditLog',
    'AuditLogDetail',
    
    # Base Models
    'AuditFieldsMixin',
    'TimestampMixin',
    'SiteFilteredMixin',
    'SiteFilteredManager',
    'SiteFilteredQuerySet',
    
    # Household Models
    'HH_CASE',
    'HH_Member',
    'HH_Exposure',
    'HH_WaterSource',
    'HH_WaterTreatment',
    'HH_Animal',
    'HH_FoodFrequency',
    'HH_FoodSource',
    'HH_PERSONAL_DATA',
    
    # Individual Models
    'Individual',
    'Individual_Exposure',
    'Individual_WaterSource',
    'Individual_WaterTreatment',
    'Individual_Comorbidity',
    'Individual_Vaccine',
    'Individual_Hospitalization',
    'Individual_Medication',
    'Individual_FoodFrequency',
    'Individual_Travel',
    'Individual_FollowUp',
    'Individual_Symptom',
    'Individual_Sample',
    'FollowUp_Hospitalization',
]