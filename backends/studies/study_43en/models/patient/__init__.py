# backends/studies/study_43en/models/patient/__init__.py
"""
Patient models package
Import all patient-related models for Django registry
"""

# Screening & Enrollment
from .Screening import ScreeningCase
from .ENR_Enrollment import EnrollmentCase
from .ENR_MedHisDrug import MedHisDrug
from .ENR_Underlying import UnderlyingCondition

# Clinical Information
from .CLI_ClinicalCase import ClinicalCase
from .CLI_HospiProcess import HospiProcess
from .CLI_ImproveSympt import ImproveSympt
from .CLI_LaboratoryTest import LaboratoryTest, OtherTest
from .CLI_Microbiology import CLI_Microbiology
from .CLI_AEHospEvent import AEHospEvent
from .CLI_HistorySymptom import HistorySymptom
from .CLI_Symptom_72H import Symptom_72H

# Antibiotics & Drugs
from .CLI_Antibiotic import PriorAntibiotic, InitialAntibiotic, MainAntibiotic
from .CLI_VasoIDrug import VasoIDrug

# Sample Collection
from .SAM_SampleCollection import SampleCollection

# Laboratory
from .LAB_Case import LAB_Microbiology
from .LAB_AntibioticSensitivity import AntibioticSensitivity

# Aliases for backwards compatibility (forms.py uses prefixed names)
ENR_MedHisDrug = MedHisDrug
CLI_ClinicalCase = ClinicalCase
CLI_HospiProcess = HospiProcess
CLI_ImproveSympt = ImproveSympt
CLI_LaboratoryTest = LaboratoryTest
CLI_AEHospEvent = AEHospEvent
CLI_Antibiotic = InitialAntibiotic  # Default to InitialAntibiotic
CLI_VasoIDrug = VasoIDrug
SAM_SampleCollection = SampleCollection
LAB_AntibioticSensitivity = AntibioticSensitivity

# Follow-up
from .FU_FollowUp_28_90 import FollowUpCase, FollowUpCase90
from .FU_Antibiotic_28_90 import FollowUpAntibiotic, FollowUpAntibiotic90
from .FU_Rehospital_28_90 import Rehospitalization, Rehospitalization90

# Discharge & End
from .Discharge import DischargeCase, DischargeICD
from .EndCaseCRF import EndCaseCRF

# Export all models
__all__ = [
    # Screening & Enrollment
    'ScreeningCase',
    'EnrollmentCase',
    'MedHisDrug',
    'ENR_MedHisDrug',  # Alias
    
    # Clinical
    'ClinicalCase',
    'CLI_ClinicalCase',  # Alias
    'HospiProcess',
    'CLI_HospiProcess',  # Alias
    'ImproveSympt',
    'CLI_ImproveSympt',  # Alias
    'LaboratoryTest',
    'CLI_LaboratoryTest',  # Alias
    'OtherTest',
    'CLI_Microbiology',
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
    'SampleCollection',
    'SAM_SampleCollection',  # Alias
    'LAB_Microbiology',
    'AntibioticSensitivity',
    'LAB_AntibioticSensitivity',  # Alias
    
    # Follow-up
    'FollowUpCase',
    'FollowUpCase90',
    'FollowUpAntibiotic',
    'FollowUpAntibiotic90',
    'Rehospitalization',
    'Rehospitalization90',
    
    # Discharge & End
    'DischargeCase',
    'DischargeICD',
    'EndCaseCRF',
]
