# backends/studies/study_43en/models/__init__.py
"""
Main models package for study_43en
Import all model subpackages for Django registry
"""

# Import patient models
from .patient import (
    ScreeningCase, EnrollmentCase, MedHisDrug, UnderlyingCondition,
    ClinicalCase, HospiProcess, ImproveSympt, LaboratoryTest, OtherTest,
    CLI_Microbiology, AEHospEvent, HistorySymptom, Symptom_72H,
    PriorAntibiotic, InitialAntibiotic, MainAntibiotic, VasoIDrug,
    SampleCollection, LAB_Microbiology, AntibioticSensitivity,
    FollowUpCase, FollowUpCase90, FollowUpAntibiotic, FollowUpAntibiotic90,
    Rehospitalization, Rehospitalization90, DischargeCase, DischargeICD, EndCaseCRF
)

# Import contact models  
from .contact import (
    ScreeningContact, EnrollmentContact, ContactMedHisDrug,
    ContactSampleCollection, ContactFollowUp28, ContactFollowUp90,
    ContactMedicationHistory28, ContactMedicationHistory90,
    ContactEndCaseCRF, ContactUnderlyingCondition
)

# Import standalone models
from .audit_log import AuditLog
from .schedule import FollowUpSchedule

# Define what gets exported when using "from models import *"
__all__ = [
    # Patient models
    'ScreeningCase', 'EnrollmentCase', 'MedHisDrug', 'UnderlyingCondition',
    'ClinicalCase', 'HospiProcess', 'ImproveSympt', 'LaboratoryTest', 'OtherTest',
    'CLI_Microbiology', 'AEHospEvent', 'HistorySymptom', 'Symptom_72H',
    'PriorAntibiotic', 'InitialAntibiotic', 'MainAntibiotic', 'VasoIDrug',
    'SampleCollection', 'LAB_Microbiology', 'AntibioticSensitivity',
    'FollowUpCase', 'FollowUpCase90', 'FollowUpAntibiotic', 'FollowUpAntibiotic90',
    'Rehospitalization', 'Rehospitalization90', 'DischargeCase', 'DischargeICD', 'EndCaseCRF',
    # Contact models
    'ScreeningContact', 'EnrollmentContact', 'ContactMedHisDrug',
    'ContactSampleCollection', 'ContactFollowUp28', 'ContactFollowUp90',
    'ContactMedicationHistory28', 'ContactMedicationHistory90',
    'ContactEndCaseCRF', 'ContactUnderlyingCondition',
    # Standalone models
    'AuditLog', 'FollowUpSchedule',
]