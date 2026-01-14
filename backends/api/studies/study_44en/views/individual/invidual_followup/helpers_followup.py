"""
Helper functions for Individual Follow-up views
Contains all save/load logic for symptoms, hospitalizations, and medications

ORGANIZATION:
1. Constants - Mapping dictionaries
2. Utility functions  
3. Save functions - Symptoms, Hospitalizations, Medications
4. Load functions - Symptoms, Hospitalizations, Medications
5. NEW: Change Detection Functions for Audit Log
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


# ==========================================
# NEW: CHANGE DETECTION FOR AUDIT LOG
# ==========================================

def detect_followup_form_field_changes(request, followup):
    """
    Detect changes in follow-up form fields (VISIT_TIME, ASSESSED, ASSESSMENT_DATE)
    
    Returns:
        list: List of change dicts [{field, old_value, new_value, old_display, new_display}]
    """
    changes = []
    
    # CRITICAL: Refresh from DB to get actual stored values
    followup.refresh_from_db()
    
    # VISIT_TIME
    old_visit_time = str(getattr(followup, 'VISIT_TIME', '') or '').strip()
    if 'VISIT_TIME' in request.POST:
        new_visit_time = request.POST.get('VISIT_TIME', '').strip()
    else:
        new_visit_time = old_visit_time
    
    if old_visit_time != new_visit_time:
        changes.append({
            'field': 'VISIT_TIME',
            'old_value': old_visit_time or '(trống)',
            'new_value': new_visit_time or '(trống)',
            'old_display': old_visit_time or '(trống)',
            'new_display': new_visit_time or '(trống)',
        })
    
    # ASSESSED
    old_assessed = str(getattr(followup, 'ASSESSED', '') or '').strip().lower()
    if 'ASSESSED' in request.POST:
        new_assessed = request.POST.get('ASSESSED', '').strip().lower()
    else:
        new_assessed = old_assessed
    
    if old_assessed != new_assessed:
        changes.append({
            'field': 'ASSESSED',
            'old_value': old_assessed or '(trống)',
            'new_value': new_assessed or '(trống)',
            'old_display': old_assessed or '(trống)',
            'new_display': new_assessed or '(trống)',
        })
    
    # ASSESSMENT_DATE
    old_date = getattr(followup, 'ASSESSMENT_DATE', None)
    old_date_str = old_date.strftime('%d/%m/%Y') if old_date else ''
    
    if 'ASSESSMENT_DATE' in request.POST:
        new_date_str = request.POST.get('ASSESSMENT_DATE', '').strip()
    else:
        new_date_str = old_date_str
    
    if old_date_str != new_date_str:
        changes.append({
            'field': 'ASSESSMENT_DATE',
            'old_value': old_date_str or '(trống)',
            'new_value': new_date_str or '(trống)',
            'old_display': old_date_str or '(trống)',
            'new_display': new_date_str or '(trống)',
        })
    
    return changes


def detect_followup_flat_field_changes(request, followup):
    """
    Detect changes in follow-up flat fields (symptoms, hospitalizations, medications)
    
    Compares POST data with database data for:
    - Symptoms (has_symptoms radio + checkboxes)
    - Hospitalizations (hospitalized_since radio + checkboxes + duration)
    - Medications (medication_since radio + checkboxes + text)
    
    ⚠️ CRITICAL: The followup object passed in may have been modified by Django form binding.
    We MUST refresh from DB to get the actual stored values.
    
    Returns:
        list: List of change dicts [{field, old_value, new_value, old_display, new_display}]
    """
    changes = []
    
    # CRITICAL FIX: Refresh followup from database to get actual stored values
    followup.refresh_from_db()
    
    # Load old data from database
    old_symptom_data = load_symptoms(followup)
    old_hosp_data = load_followup_hospitalizations(followup)
    old_med_data = load_followup_medications(followup)
    
    # ==========================================
    # 1. Symptoms
    # ==========================================
    
    # has_symptoms radio
    old_has_symptoms = str(old_symptom_data.get('has_symptoms', '') or '').strip().lower()
    if 'has_symptoms' in request.POST:
        new_has_symptoms = request.POST.get('has_symptoms', '').strip().lower()
    else:
        new_has_symptoms = old_has_symptoms
    
    logger.info(f"🔍 has_symptoms: old='{old_has_symptoms}', new='{new_has_symptoms}', in_POST={'has_symptoms' in request.POST}")
    
    if old_has_symptoms != new_has_symptoms:
        changes.append({
            'field': 'has_symptoms',
            'old_value': old_has_symptoms or '(trống)',
            'new_value': new_has_symptoms or '(trống)',
            'old_display': old_has_symptoms or '(trống)',
            'new_display': new_has_symptoms or '(trống)',
        })
    
    # Symptom checkboxes
    for symptom_key in SYMPTOM_MAPPING.keys():
        field_name = f'symptom_{symptom_key}'
        old_val = old_symptom_data.get(field_name, False)
        new_val = request.POST.get(field_name) == 'on'
        
        if old_val != new_val:
            changes.append({
                'field': field_name,
                'old_value': old_val,
                'new_value': new_val,
                'old_display': 'Có' if old_val else 'Không',
                'new_display': 'Có' if new_val else 'Không',
            })
    
    # Symptom other text
    old_symptom_other = old_symptom_data.get('symptom_other_text', '')
    new_symptom_other = request.POST.get('symptom_other_text', '').strip()
    if str(old_symptom_other or '').strip() != str(new_symptom_other or '').strip():
        changes.append({
            'field': 'symptom_other_text',
            'old_value': old_symptom_other,
            'new_value': new_symptom_other,
            'old_display': old_symptom_other or '(trống)',
            'new_display': new_symptom_other or '(trống)',
        })
    
    # ==========================================
    # 2. Hospitalizations
    # ==========================================
    
    # hospitalized_since radio
    old_hospitalized = str(old_hosp_data.get('hospitalized_since', '') or '').strip().lower()
    if 'hospitalized_since' in request.POST:
        new_hospitalized = request.POST.get('hospitalized_since', '').strip().lower()
    else:
        new_hospitalized = old_hospitalized
    
    logger.info(f"🔍 hospitalized_since: old='{old_hospitalized}', new='{new_hospitalized}', in_POST={'hospitalized_since' in request.POST}")
    
    if old_hospitalized != new_hospitalized:
        changes.append({
            'field': 'hospitalized_since',
            'old_value': old_hospitalized or '(trống)',
            'new_value': new_hospitalized or '(trống)',
            'old_display': old_hospitalized or '(trống)',
            'new_display': new_hospitalized or '(trống)',
        })
    
    # Hospital checkboxes and duration
    for hosp_key in FOLLOWUP_HOSPITAL_MAPPING.keys():
        # Checkbox
        field_name = f'fu_hosp_{hosp_key}'
        old_val = old_hosp_data.get(field_name, False)
        new_val = request.POST.get(field_name) == 'on'
        
        if old_val != new_val:
            changes.append({
                'field': field_name,
                'old_value': old_val,
                'new_value': new_val,
                'old_display': 'Có' if old_val else 'Không',
                'new_display': 'Có' if new_val else 'Không',
            })
        
        # Duration radio
        duration_field = f'fu_hosp_{hosp_key}_duration'
        old_duration = old_hosp_data.get(duration_field, '')
        new_duration = request.POST.get(duration_field, '').strip()
        if str(old_duration or '').strip() != str(new_duration or '').strip():
            changes.append({
                'field': duration_field,
                'old_value': old_duration,
                'new_value': new_duration,
                'old_display': old_duration or '(trống)',
                'new_display': new_duration or '(trống)',
            })
    
    # Hospital other text
    old_hosp_other = old_hosp_data.get('fu_hosp_other_text', '')
    new_hosp_other = request.POST.get('fu_hosp_other_text', '').strip()
    if str(old_hosp_other or '').strip() != str(new_hosp_other or '').strip():
        changes.append({
            'field': 'fu_hosp_other_text',
            'old_value': old_hosp_other,
            'new_value': new_hosp_other,
            'old_display': old_hosp_other or '(trống)',
            'new_display': new_hosp_other or '(trống)',
        })
    
    # ==========================================
    # 3. Medications
    # ==========================================
    
    # medication_since radio
    old_medication = str(old_med_data.get('medication_since', '') or '').strip().lower()
    if 'medication_since' in request.POST:
        new_medication = request.POST.get('medication_since', '').strip().lower()
    else:
        new_medication = old_medication
    
    logger.info(f"🔍 medication_since: old='{old_medication}', new='{new_medication}', in_POST={'medication_since' in request.POST}")
    
    if old_medication != new_medication:
        changes.append({
            'field': 'medication_since',
            'old_value': old_medication or '(trống)',
            'new_value': new_medication or '(trống)',
            'old_display': old_medication or '(trống)',
            'new_display': new_medication or '(trống)',
        })
    
    # Medication checkboxes and text fields
    med_fields = [
        ('med_antibiotics_fu', 'med_antibiotics_type'),
        ('med_steroids_fu', 'med_steroids_type'),
        ('med_other_fu', 'med_other_type'),
    ]
    
    for checkbox_field, text_field in med_fields:
        # Checkbox
        old_checked = old_med_data.get(checkbox_field, False)
        new_checked = request.POST.get(checkbox_field) == 'on'
        
        if old_checked != new_checked:
            changes.append({
                'field': checkbox_field,
                'old_value': old_checked,
                'new_value': new_checked,
                'old_display': 'Có' if old_checked else 'Không',
                'new_display': 'Có' if new_checked else 'Không',
            })
        
        # Text field
        old_text = old_med_data.get(text_field, '')
        new_text = request.POST.get(text_field, '').strip()
        if str(old_text or '').strip() != str(new_text or '').strip():
            changes.append({
                'field': text_field,
                'old_value': old_text,
                'new_value': new_text,
                'old_display': old_text or '(trống)',
                'new_display': new_text or '(trống)',
            })
    
    logger.info(f"🔍 detect_followup_flat_field_changes: Found {len(changes)} changes")
    return changes


# ==========================================
# EXPORTS
# ==========================================

__all__ = [
    'set_audit_metadata',
    'make_form_readonly',
    'save_symptoms',
    'save_followup_hospitalizations',
    'save_followup_medications',
    'load_symptoms',
    'load_followup_hospitalizations',
    'load_followup_medications',
    # NEW: Change detection for audit log
    'detect_followup_form_field_changes',
    'detect_followup_flat_field_changes',
]
