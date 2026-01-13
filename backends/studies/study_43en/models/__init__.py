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
# STUDY 43EN MODELS (EXISTING)
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
    # STUDY 44EN - HOUSEHOLD MODELS (8 models)
    # ==========================================
    'HH_CASE',                  # Main household
    'HH_Member',                # Household members
    'HH_Exposure',              # Household exposure
    'HH_WaterSource',           # Water sources (normalized)
    'HH_WaterTreatment',        # Water treatment (normalized)
    'HH_Animal',                # Animals (normalized)
    'HH_FoodFrequency',         # Food frequency
    'HH_FoodSource',            # Food sources
    
    # ==========================================
    # STUDY 44EN - INDIVIDUAL MODELS (13 models)
    # ==========================================
    # Demographics & Basic Info
    'Individual',               # Individual demographic info
    'Individual_Exposure',      # Individual exposure factors
    
    # Water & Sanitation
    'Individual_WaterSource',   # Individual water sources
    'Individual_WaterTreatment', # Individual water treatment
    
    # Medical History
    'Individual_Comorbidity',   # Comorbidities
    'Individual_Vaccine',       # Vaccination records
    'Individual_Hospitalization', # Hospitalization (3 months)
    'Individual_Medication',    # Medication use (3 months)
    
    # Lifestyle & Behavior
    'Individual_FoodFrequency', # Individual food frequency
    'Individual_Travel',        # Travel history
    
    # Follow-up & Monitoring
    'Individual_FollowUp',      # Follow-up visits (Day 14, 28, 90)
    'Individual_Symptom',       # Symptoms at follow-up
    'Individual_Sample',        # Sample collection
    
    # ==========================================
    # STUDY 43EN MODELS (EXISTING)
    # ==========================================
    # Note: patient.__all__, contact.__all__, etc. are included
]