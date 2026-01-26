# backends/studies/study_43en/models/patient/__init__.py
"""
Patient models package
Import all patient-related models for Django registry
"""

# Screening & Enrollment
from .SCR_CASE import SCR_CASE
from .ENR_CASE import ENR_CASE
from .ENR_CASE_MedHisDrug import ENR_CASE_MedHisDrug
from .ENR_Underlying import UnderlyingCondition

# Clinical Information
from .CLI_CASE import CLI_CASE
from .CLI_HospiProcess import HospiProcess
from .CLI_ImproveSympt import ImproveSympt
from .CLI_LaboratoryTest import LaboratoryTest, OtherTest
from .CLI_AEHospEvent import AEHospEvent
from .CLI_HistorySymptom import HistorySymptom
from .CLI_Symptom_72H import Symptom_72H

# Antibiotics & Drugs
from .CLI_Antibiotic import PriorAntibiotic, InitialAntibiotic, MainAntibiotic
from .CLI_VasoIDrug import VasoIDrug

# Sample Collection
from .SAM_CASE import SAM_CASE

# Laboratory
from .LAB_Case import LAB_Microbiology
from .LAB_AntibioticSensitivity import AntibioticSensitivity



# Aliases for backwards compatibility (forms.py uses prefixed names)
ENR_CASE_MedHisDrug = ENR_CASE_MedHisDrug
CLI_ClinicalCase = CLI_CASE
CLI_HospiProcess = HospiProcess
CLI_ImproveSympt = ImproveSympt
CLI_LaboratoryTest = LaboratoryTest
CLI_AEHospEvent = AEHospEvent
CLI_Antibiotic = InitialAntibiotic  # Default to InitialAntibiotic
CLI_VasoIDrug = VasoIDrug
SAM_CASE = SAM_CASE
LAB_AntibioticSensitivity = AntibioticSensitivity

# Follow-up
from .FU_CASE_28 import FU_CASE_28
from .FU_CASE_90 import FU_CASE_90
from .FU_Antibiotic_28 import FollowUpAntibiotic
from .FU_Antibiotic_90 import FollowUpAntibiotic90
from .FU_Rehospital_28 import Rehospitalization
from .FU_Rehospital_90 import Rehospitalization90

# Discharge & End
from .DISCH_CASE import DISCH_CASE, DischargeICD
from .EndCaseCRF import EndCaseCRF

# Personal Data
from .PERSONAL_DATA import PERSONAL_DATA


# Export all models
__all__ = [
    # Screening & Enrollment
    'SCR_CASE',
    'ENR_CASE',
    'ENR_CASE_MedHisDrug',
    'ENR_CASE_MedHisDrug',  # Alias
    
    # Clinical
    'CLI_CASE',
    'CLI_ClinicalCase',  # Alias
    'HospiProcess',
    'CLI_HospiProcess',  # Alias
    'ImproveSympt',
    'CLI_ImproveSympt',  # Alias
    'LaboratoryTest',
    'CLI_LaboratoryTest',  # Alias
    'OtherTest',
    'AEHospEvent',
    'CLI_AEHospEvent',  # Alias
    
    # Antibiotics & Drugs
    'PriorAntibiotic',
    'InitialAntibiotic',
    'MainAntibiotic',
    'CLI_Antibiotic',  # Alias
    'VasoIDrug',
    'CLI_VasoIDrug',  # Alias
    
    # Sample & Lab
    'SAM_CASE',
    'SAM_CASE',  # Alias
    'LAB_Microbiology',
    'AntibioticSensitivity',
    'LAB_AntibioticSensitivity',  # Alias
    
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
]
