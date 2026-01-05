"""
Helper functions for Individual Follow-up views
Contains all save/load logic for symptoms, hospitalizations, and medications

ORGANIZATION:
1. Constants - Mapping dictionaries
2. Utility functions  
3. Save functions - Symptoms, Hospitalizations, Medications
4. Load functions - Symptoms, Hospitalizations, Medications
"""

import logging
from backends.studies.study_44en.models.individual import (
    Individual_Symptom,
    FollowUp_Hospitalization,
)

logger = logging.getLogger(__name__)


# ==========================================
# CONSTANTS - Mapping Dictionaries
# ==========================================

# Symptom mappings (template name → database choice value)
SYMPTOM_MAPPING = {
    'fatigue': 'fatigue',
    'fever': 'fever',
    'cough': 'cough',
    'eye_pain': 'eye_pain',
    'red_eye': 'red_eyes',
    'muscle_pain': 'muscle_pain',
    'anorexia': 'anorexia',
    'dyspnea': 'dyspnea',
    'jaundice': 'jaundice',
    'headache': 'headache',
    'dysuria': 'dysuria',
    'hematuria': 'hematuria',
    'difficult_urination': 'difficult_urination',
    'cloudy_urine': 'pyuria',
    'vomiting': 'vomiting',
    'nausea': 'nausea',
    'diarrhea': 'diarrhea',
    'abdominal_pain': 'abdominal_pain',
    'other': 'other',
}

# Hospital type mappings
FOLLOWUP_HOSPITAL_MAPPING = {
    'central': 'central',
    'city': 'city',
    'district': 'district',
    'private': 'private',
    'other': 'other',
}

# Duration mappings
DURATION_MAPPING = {
    '1-3': '1-3',
    '3-5': '3-5',
    '5-7': '5-7',
    '7+': '>7',
}

DURATION_REVERSE_MAPPING = {v: k for k, v in DURATION_MAPPING.items()}


# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def set_audit_metadata(instance, user):
    """Set audit fields for tracking changes"""
    if hasattr(instance, 'last_modified_by_id'):
        instance.last_modified_by_id = user.id
    if hasattr(instance, 'last_modified_by_username'):
        instance.last_modified_by_username = user.username


def make_form_readonly(form):
    """Make all form fields readonly for view mode"""
    for field in form.fields.values():
        field.disabled = True


# ==========================================
# SAVE FUNCTIONS
# ==========================================

def save_symptoms(request, followup):
    """
    Parse and save symptoms from hardcoded template checkboxes
    Template fields: has_symptoms (radio), symptom_{type} (checkboxes), symptom_other_text
    """
    # Clear existing symptoms
    Individual_Symptom.objects.filter(FOLLOW_UP=followup).delete()
    
    # Update HAS_SYMPTOMS on followup record
    has_symptoms = request.POST.get('has_symptoms', '').strip()
    if has_symptoms:
        followup.HAS_SYMPTOMS = has_symptoms
        followup.save()
    
    # Only save details if 'yes' selected
    if has_symptoms != 'yes':
        return 0
    
    count = 0
    for symptom_key, symptom_choice in SYMPTOM_MAPPING.items():
        if request.POST.get(f'symptom_{symptom_key}') == 'on':
            # Get other symptom text if applicable
            other_text = None
            if symptom_key == 'other':
                other_text = request.POST.get('symptom_other_text', '').strip()
            
            # Create symptom record
            symptom = Individual_Symptom(
                FOLLOW_UP=followup,
                SYMPTOM_TYPE=symptom_choice,
                SYMPTOM_OTHER=other_text
            )
            set_audit_metadata(symptom, request.user)
            symptom.save()
            
            logger.info(f"Saved symptom: {symptom_choice}, OTHER='{other_text}'")
            count += 1
    
    logger.info(f"Saved {count} symptoms")
    return count


def save_followup_hospitalizations(request, followup):
    """
    Parse and save hospitalizations from hardcoded template
    Template fields: hospitalized_since (radio), fu_hosp_{type} (checkboxes), fu_hosp_{type}_duration (radio)
    """
    # Clear existing records
    FollowUp_Hospitalization.objects.filter(FOLLOW_UP=followup).delete()
    
    # Update hospitalization status on followup
    hospitalized_since = request.POST.get('hospitalized_since', '').strip()
    if hospitalized_since:
        followup.HOSPITALIZED = hospitalized_since
        followup.save()
    
    # Only save details if 'yes' selected
    if hospitalized_since != 'yes':
        return 0
    
    count = 0
    for hosp_key, hosp_choice in FOLLOWUP_HOSPITAL_MAPPING.items():
        if request.POST.get(f'fu_hosp_{hosp_key}') == 'on':
            # Get duration
            duration = request.POST.get(f'fu_hosp_{hosp_key}_duration', '').strip()
            mapped_duration = DURATION_MAPPING.get(duration)
            
            # Get other hospital text if applicable
            other_text = None
            if hosp_key == 'other':
                other_text = request.POST.get('fu_hosp_other_text', '').strip()
                logger.info(f"🔍 Followup Hospitalization OTHER: fu_hosp_other_text = '{other_text}'")
            
            # Create hospitalization record
            hosp = FollowUp_Hospitalization(
                FOLLOW_UP=followup,
                HOSPITAL_TYPE=hosp_choice,
                HOSPITAL_OTHER=other_text,
                DURATION=mapped_duration
            )
            set_audit_metadata(hosp, request.user)
            hosp.save()
            
            logger.info(f"Saved followup hospitalization: {hosp_choice}, OTHER='{other_text}', DURATION={mapped_duration}")
            count += 1
    
    logger.info(f"Saved {count} followup hospitalizations")
    return count


def save_followup_medications(request, followup):
    """
    Parse and save medication data from hardcoded template
    Template fields: medication_since (radio), med_antibiotics_fu, med_steroids_fu, med_other_fu (checkboxes)
                     med_antibiotics_type, med_steroids_type, med_other_type (text inputs)
    
    This saves to the followup record fields: ANTIBIOTIC_TYPE, STEROID_TYPE, OTHER_MEDICATION
    """
    # Update medication status
    medication_since = request.POST.get('medication_since', '').strip()
    if medication_since:
        followup.USED_MEDICATION = medication_since
    
    # Clear medication fields if not 'yes'
    if medication_since != 'yes':
        followup.ANTIBIOTIC_TYPE = None
        followup.STEROID_TYPE = None
        followup.OTHER_MEDICATION = None
        followup.save()
        return 0
    
    # Save medication details
    antibiotic_checked = request.POST.get('med_antibiotics_fu') == 'on'
    steroid_checked = request.POST.get('med_steroids_fu') == 'on'
    other_checked = request.POST.get('med_other_fu') == 'on'
    
    if antibiotic_checked:
        followup.ANTIBIOTIC_TYPE = request.POST.get('med_antibiotics_type', '').strip()
    else:
        followup.ANTIBIOTIC_TYPE = None
    
    if steroid_checked:
        followup.STEROID_TYPE = request.POST.get('med_steroids_type', '').strip()
    else:
        followup.STEROID_TYPE = None
    
    if other_checked:
        followup.OTHER_MEDICATION = request.POST.get('med_other_type', '').strip()
    else:
        followup.OTHER_MEDICATION = None
    
    followup.save()
    
    count = sum([antibiotic_checked, steroid_checked, other_checked])
    logger.info(f"Saved {count} medication types")
    return count


# ==========================================
# LOAD FUNCTIONS
# ==========================================

def load_symptoms(followup):
    """
    Load symptom data for template display
    Returns dict with has_symptoms and symptom_{type} keys
    """
    symptom_data = {}
    
    # Load symptom status
    symptom_data['has_symptoms'] = followup.HAS_SYMPTOMS if followup.HAS_SYMPTOMS else ''
    
    # Load individual symptoms
    symptoms = Individual_Symptom.objects.filter(FOLLOW_UP=followup)
    type_reverse_map = {v: k for k, v in SYMPTOM_MAPPING.items()}
    
    logger.info(f"📖 Loading {symptoms.count()} symptoms")
    
    for symptom in symptoms:
        template_key = type_reverse_map.get(symptom.SYMPTOM_TYPE, 'other')
        symptom_data[f'symptom_{template_key}'] = True
        
        if symptom.SYMPTOM_TYPE == 'other' and symptom.SYMPTOM_OTHER:
            symptom_data['symptom_other_text'] = symptom.SYMPTOM_OTHER
            logger.info(f"📖 Loaded OTHER symptom: text='{symptom.SYMPTOM_OTHER}'")
    
    logger.info(f"📖 Symptom data keys: {list(symptom_data.keys())}")
    return symptom_data


def load_followup_hospitalizations(followup):
    """
    Load hospitalization data for template display
    Returns dict with hospitalized_since and fu_hosp_{type} keys
    """
    hosp_data = {}
    
    # Load hospitalization status
    hosp_data['hospitalized_since'] = followup.HOSPITALIZED if followup.HOSPITALIZED else ''
    
    # Load individual hospitalizations
    hospitalizations = FollowUp_Hospitalization.objects.filter(FOLLOW_UP=followup)
    type_reverse_map = {v: k for k, v in FOLLOWUP_HOSPITAL_MAPPING.items()}
    
    logger.info(f"📖 Loading {hospitalizations.count()} followup hospitalizations")
    
    for hosp in hospitalizations:
        template_key = type_reverse_map.get(hosp.HOSPITAL_TYPE, 'other')
        hosp_data[f'fu_hosp_{template_key}'] = True
        
        # Map duration back to template values
        if hosp.DURATION:
            hosp_data[f'fu_hosp_{template_key}_duration'] = DURATION_REVERSE_MAPPING.get(hosp.DURATION, '')
        
        if hosp.HOSPITAL_TYPE == 'other' and hosp.HOSPITAL_OTHER:
            hosp_data['fu_hosp_other_text'] = hosp.HOSPITAL_OTHER
            logger.info(f"📖 Loaded OTHER followup hospitalization: text='{hosp.HOSPITAL_OTHER}'")
    
    logger.info(f"📖 Followup hospitalization data keys: {list(hosp_data.keys())}")
    return hosp_data


def load_followup_medications(followup):
    """
    Load medication data for template display
    Returns dict with medication_since and medication type keys
    """
    med_data = {}
    
    # Load medication status
    med_data['medication_since'] = followup.USED_MEDICATION if followup.USED_MEDICATION else ''
    
    # Load medication details
    if followup.ANTIBIOTIC_TYPE:
        med_data['med_antibiotics_fu'] = True
        med_data['med_antibiotics_type'] = followup.ANTIBIOTIC_TYPE
    
    if followup.STEROID_TYPE:
        med_data['med_steroids_fu'] = True
        med_data['med_steroids_type'] = followup.STEROID_TYPE
    
    if followup.OTHER_MEDICATION:
        med_data['med_other_fu'] = True
        med_data['med_other_type'] = followup.OTHER_MEDICATION
    
    logger.info(f"📖 Medication data keys: {list(med_data.keys())}")
    return med_data


__all__ = [
    'set_audit_metadata',
    'make_form_readonly',
    'save_symptoms',
    'save_followup_hospitalizations',
    'save_followup_medications',
    'load_symptoms',
    'load_followup_hospitalizations',
    'load_followup_medications',
]
