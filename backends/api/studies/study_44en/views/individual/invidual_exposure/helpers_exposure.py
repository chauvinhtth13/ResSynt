"""
Helper functions for Individual Exposure views
Contains all save/load logic for normalized tables

ORGANIZATION:
1. Constants - Mapping dictionaries
2. Utility functions
3. Save functions (EXP 1/3) - Water & Comorbidities
4. Load functions (EXP 1/3)
5. Save functions (EXP 2/3) - Vaccination & Hospitalization
6. Load functions (EXP 2/3)
7. Save functions (EXP 3/3) - Food & Travel
8. Load functions (EXP 3/3)
9. ✅ NEW: Change Detection Functions for Audit Log
"""

import logging
from backends.studies.study_44en.models.individual import (
    Individual_WaterSource,
    Individual_WaterTreatment,
    Individual_Comorbidity,
    Individual_Vaccine,
    Individual_Hospitalization,
    Individual_Medication,
    Individual_FoodFrequency,
    Individual_Travel,
)

logger = logging.getLogger(__name__)


# ==========================================
# CONSTANTS - Mapping Dictionaries
# ==========================================

# Water source mappings
WATER_SOURCE_MAPPING = {
    'tap': 'TAP',
    'bottle': 'BOTTLED',
    'well': 'WELL',
    'rain': 'RAIN',
    'river': 'RIVER',
    'pond': 'POND',
    'other': 'OTHER',
}

# Water treatment mappings
WATER_TREATMENT_MAPPING = {
    'boil': 'BOILING',
    'filter': 'FILTER_MACHINE',
    'pitcher': 'FILTER_PORTABLE',
    'chemical': 'CHEMICAL',
    'sodis': 'SODIS',
    'other': 'OTHER',
}

# Comorbidity mappings
COMORBIDITY_MAPPING = {
    'hypertension': 'HYPERTENSION',
    'diabetes': 'DIABETES',
    'heart': 'CARDIOVASCULAR',
    'kidney': 'CHRONIC_KIDNEY',
    'liver': 'CHRONIC_HEPATITIS',
    'asthma': 'COPD',
}

# Vaccine mappings
VACCINE_MAPPING = {
    'bcg': 'BCG',
    'flu': 'FLU',
    'rubella': 'RUBELLA',
    'hepa': 'HEPATITIS_A',
    'hepb': 'HEPATITIS_B',
    'hib': 'HIB',
    'chickenpox': 'CHICKENPOX',
    'polio': 'POLIO',
    'je': 'JAPANESE_ENCEPHALITIS',
    'diphtheria': 'DIPHTHERIA',
    'measles': 'MEASLES',
    'meningitis': 'MENINGITIS',
    'tetanus': 'TETANUS',
    'mumps': 'MUMPS',
    'rabies': 'RABIES',
    'rotavirus': 'ROTAVIRUS',
    'pertussis': 'PERTUSSIS',
    'pneumococcal': 'PNEUMOCOCCAL',
    'other': 'OTHER',
}

# Vaccination status mappings
VACCINATION_STATUS_MAPPING = {
    'never': 'never',
    'unsure': 'not_remember',
    'unknown_type': 'vaccinated_not_remember',
    'known': 'vaccinated_specific',
}

# Hospital type mappings
HOSPITAL_MAPPING = {
    'central': 'CENTRAL',
    'city': 'CITY',
    'district': 'DISTRICT',
    'private': 'PRIVATE',
    'other': 'OTHER',
}

# Medication type mappings
MEDICATION_MAPPING = {
    'antibiotics': 'antibiotics',
    'steroids': 'steroids',
    'pain': 'pain_relievers',
    'traditional': 'traditional_medicine',
    'other': 'other_medications',
}

# Duration mappings
DURATION_MAPPING = {
    '1-3': '1-3',
    '3-5': '3-5',
    '5-7': '5-7',
    '7+': '>14',
}

DURATION_REVERSE_MAPPING = {
    '1-3': '1-3',
    '3-5': '3-5',
    '5-7': '5-7',
    '7-14': '7+',
    '>14': '7+',
}

# Food frequency mappings
FOOD_FREQ_MAPPING = {
    '0': 'never',
    '1': '1-3/month',
    '2': '1-2/week',
    '3': '3-5/week',
    '4': '1/day',
    '5': '2+/day',
}

FOOD_FREQ_REVERSE_MAPPING = {v: k for k, v in FOOD_FREQ_MAPPING.items()}

# Food field mapping
FOOD_FIELD_MAPPING = {
    'freq_rice': 'RICE_NOODLES',
    'freq_red_meat': 'RED_MEAT',
    'freq_poultry': 'POULTRY',
    'freq_seafood': 'FISH_SEAFOOD',
    'freq_eggs': 'EGGS',
    'freq_raw_veg': 'RAW_VEGETABLES',
    'freq_cooked_veg': 'COOKED_VEGETABLES',
    'freq_dairy': 'DAIRY',
    'freq_fermented': 'FERMENTED',
    'freq_beer': 'BEER',
    'freq_alcohol': 'ALCOHOL',
}

# Travel frequency mappings
TRAVEL_FREQ_MAPPING = {
    'daily': 'daily',
    '1-2_week': '1-2/week',
    '1-2_month': '1-2/month',
    'less_month': '<1/month',
    'no': 'never',
}

TRAVEL_FREQ_REVERSE_MAPPING = {v: k for k, v in TRAVEL_FREQ_MAPPING.items()}


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
# SAVE FUNCTIONS - EXP 1/3 (Water & Comorbidities)
# ==========================================

def save_water_sources(request, exposure):
    """
    Parse and save water sources from hardcoded template checkboxes
    Template fields: water_{source}_drink, water_{source}_domestic, water_{source}_irrigation, water_{source}_other
    """
    # Clear existing records
    Individual_WaterSource.objects.filter(MEMBERID=exposure).delete()
    
    count = 0
    for source_key, source_choice in WATER_SOURCE_MAPPING.items():
        # Check if any usage is selected
        drink = request.POST.get(f'water_{source_key}_drink') == 'on'
        domestic = request.POST.get(f'water_{source_key}_domestic') == 'on'
        irrigation = request.POST.get(f'water_{source_key}_irrigation') == 'on'
        other_purpose = request.POST.get(f'water_{source_key}_other', '').strip()
        
        if drink or domestic or irrigation or other_purpose:
            # Get other source name if applicable
            other_name = None
            if source_key == 'other':
                other_name = request.POST.get('water_other_src_name', '').strip()
            
            # Create water source record
            ws = Individual_WaterSource(
                MEMBERID=exposure,
                SOURCE_TYPE=source_choice,
                SOURCE_TYPE_OTHER=other_name,
                DRINKING=drink,
                LIVING=domestic,
                IRRIGATION=irrigation,
                FOR_OTHER=bool(other_purpose),
                OTHER_PURPOSE=other_purpose or None
            )
            set_audit_metadata(ws, request.user)
            ws.save()
            count += 1
    
    logger.info(f"Saved {count} water sources")
    return count


def save_water_treatment(request, exposure):
    """
    Parse and save water treatment from hardcoded template
    Template fields: water_treatment (radio), treatment_{type} (checkboxes)
    """
    # Clear existing records
    Individual_WaterTreatment.objects.filter(MEMBERID=exposure).delete()
    
    # Check if water treatment is used
    water_treatment = request.POST.get('water_treatment', '').strip()
    if water_treatment != 'yes':
        return 0
    
    count = 0
    for treatment_key, treatment_choice in WATER_TREATMENT_MAPPING.items():
        if request.POST.get(f'treatment_{treatment_key}') == 'on':
            # Get other treatment text if applicable
            other_text = None
            if treatment_key == 'other':
                other_text = request.POST.get('treatment_other_text', '').strip()
            
            # Create water treatment record
            wt = Individual_WaterTreatment(
                MEMBERID=exposure,
                TREATMENT_TYPE=treatment_choice,
                TREATMENT_TYPE_OTHER=other_text
            )
            set_audit_metadata(wt, request.user)
            wt.save()
            count += 1
    
    logger.info(f"Saved {count} water treatments")
    return count


def save_comorbidities(request, exposure):
    """
    Parse and save comorbidities from hardcoded template
    Template fields: has_conditions (radio), condition_{type} (checkboxes), condition_{type}_treated (radio)
    """
    # Clear existing records
    Individual_Comorbidity.objects.filter(MEMBERID=exposure).delete()
    
    # Check if person has conditions
    has_conditions = request.POST.get('has_conditions', '').strip()
    if has_conditions != 'yes':
        return 0
    
    count = 0
    
    # Process conditions that are in the mapping
    for condition_key, condition_choice in COMORBIDITY_MAPPING.items():
        if request.POST.get(f'condition_{condition_key}') == 'on':
            # Get treatment status from template
            treatment_status_template = request.POST.get(f'condition_{condition_key}_treated', '').strip()
            
            # Map template values to model values
            treatment_status_model = None
            if treatment_status_template == 'treated':
                treatment_status_model = 'treating'
            elif treatment_status_template == 'not_treated':
                treatment_status_model = 'not_treating'
            
            # Create comorbidity record
            comorb = Individual_Comorbidity(
                MEMBERID=exposure,
                COMORBIDITY_TYPE=condition_choice,
                COMORBIDITY_OTHER=None,
                TREATMENT_STATUS=treatment_status_model
            )
            set_audit_metadata(comorb, request.user)
            comorb.save()
            count += 1
            logger.info(f"Saved comorbidity: {condition_choice}, status={treatment_status_model}")
    
    # Handle 'other' condition separately
    if request.POST.get('condition_other') == 'on':
        other_text = request.POST.get('condition_other_text', '').strip()
        treatment_status_template = request.POST.get('condition_other_treated', '').strip()
        
        treatment_status_model = None
        if treatment_status_template == 'treated':
            treatment_status_model = 'treating'
        elif treatment_status_template == 'not_treated':
            treatment_status_model = 'not_treating'
        
        comorb = Individual_Comorbidity(
            MEMBERID=exposure,
            COMORBIDITY_TYPE='OTHER',
            COMORBIDITY_OTHER=other_text if other_text else None,
            TREATMENT_STATUS=treatment_status_model
        )
        set_audit_metadata(comorb, request.user)
        comorb.save()
        count += 1
        logger.info(f"Saved comorbidity: OTHER ({other_text}), status={treatment_status_model}")
    
    # NOTE: condition_cancer is in template but not in model choices
    if request.POST.get('condition_cancer') == 'on':
        logger.warning("Cancer condition selected but not saved (not in model choices)")
    
    logger.info(f"Saved {count} comorbidities")
    return count


# ==========================================
# LOAD FUNCTIONS - EXP 1/3 (Water & Comorbidities)
# ==========================================

def load_water_data(exposure):
    """
    Load water sources data for template display
    Returns dict with water_{source}_{usage} keys
    """
    water_data = {}
    
    water_sources = Individual_WaterSource.objects.filter(MEMBERID=exposure)
    for ws in water_sources:
        source_type_lower = ws.SOURCE_TYPE.lower()
        source_key = 'bottle' if source_type_lower == 'bottled' else source_type_lower
        
        water_data[f'water_{source_key}_drink'] = ws.DRINKING
        water_data[f'water_{source_key}_domestic'] = ws.LIVING
        water_data[f'water_{source_key}_irrigation'] = ws.IRRIGATION
        water_data[f'water_{source_key}_other'] = ws.OTHER_PURPOSE or ''
        
        if source_key == 'other' and ws.SOURCE_TYPE_OTHER:
            water_data['water_other_src_name'] = ws.SOURCE_TYPE_OTHER
    
    return water_data


def load_treatment_data(exposure):
    """
    Load water treatment data for template display
    Returns dict with treatment_{type} and water_treatment keys
    """
    treatment_data = {}
    
    # ✅ FIX: Read water_treatment from model field first
    if exposure.WATER_TREATMENT:
        treatment_data['water_treatment'] = exposure.WATER_TREATMENT.lower()
    
    treatments = Individual_WaterTreatment.objects.filter(MEMBERID=exposure)
    
    type_reverse_map = {v: k for k, v in WATER_TREATMENT_MAPPING.items()}
    
    for treatment in treatments:
        template_key = type_reverse_map.get(treatment.TREATMENT_TYPE, treatment.TREATMENT_TYPE.lower())
        treatment_data[f'treatment_{template_key}'] = True
        
        if treatment.TREATMENT_TYPE == 'OTHER' and treatment.TREATMENT_TYPE_OTHER:
            treatment_data['treatment_other_text'] = treatment.TREATMENT_TYPE_OTHER
    
    return treatment_data


def load_comorbidity_data(exposure):
    """
    Load comorbidity data for template display
    Returns dict with condition_{type} and has_conditions keys
    """
    comorbidity_data = {}
    
    # ✅ FIX: Read has_conditions from model field first
    if exposure.HAS_COMORBIDITY:
        comorbidity_data['has_conditions'] = exposure.HAS_COMORBIDITY.lower()
    
    comorbidities = Individual_Comorbidity.objects.filter(MEMBERID=exposure)
    
    type_reverse_map = {
        'HYPERTENSION': 'hypertension',
        'DIABETES': 'diabetes',
        'CARDIOVASCULAR': 'heart',
        'CHRONIC_KIDNEY': 'kidney',
        'CHRONIC_HEPATITIS': 'liver',
        'COPD': 'asthma',
        'ASTHMA': 'asthma',
        'OTHER': 'other',
    }
    
    for comorb in comorbidities:
        template_key = type_reverse_map.get(comorb.COMORBIDITY_TYPE, 'other')
        
        comorbidity_data[f'condition_{template_key}'] = True
        
        if comorb.TREATMENT_STATUS == 'treating':
            comorbidity_data[f'condition_{template_key}_treated'] = 'treated'
        elif comorb.TREATMENT_STATUS == 'not_treating':
            comorbidity_data[f'condition_{template_key}_treated'] = 'not_treated'
        
        if comorb.COMORBIDITY_TYPE == 'OTHER' and comorb.COMORBIDITY_OTHER:
            comorbidity_data['condition_other_text'] = comorb.COMORBIDITY_OTHER
    
    return comorbidity_data


# ==========================================
# SAVE FUNCTIONS - EXP 2/3 (Vaccination & Hospitalization)
# ==========================================

def save_vaccines(request, exposure):
    """
    Parse and save vaccines from hardcoded template
    Template fields: vaccination_history (radio), vaccine_{type} (checkboxes)
    """
    # Clear existing records
    Individual_Vaccine.objects.filter(MEMBERID=exposure).delete()
    
    # Update vaccination status on exposure
    vaccination_history = request.POST.get('vaccination_history', '').strip()
    if vaccination_history in VACCINATION_STATUS_MAPPING:
        exposure.VACCINATION_STATUS = VACCINATION_STATUS_MAPPING[vaccination_history]
        exposure.save()
    
    # Only save individual vaccines if 'known' selected
    if vaccination_history != 'known':
        return 0
    
    count = 0
    for vaccine_key, vaccine_choice in VACCINE_MAPPING.items():
        if request.POST.get(f'vaccine_{vaccine_key}') == 'on':
            other_text = None
            if vaccine_key == 'other':
                other_text = request.POST.get('vaccine_other_text', '').strip()
            
            vaccine = Individual_Vaccine(
                MEMBERID=exposure,
                VACCINE_TYPE=vaccine_choice,
                VACCINE_OTHER=other_text
            )
            set_audit_metadata(vaccine, request.user)
            vaccine.save()
            count += 1
    
    logger.info(f"Saved {count} vaccines")
    return count


def save_hospitalizations(request, exposure):
    """
    Parse and save hospitalizations from hardcoded template
    Template fields: has_hospitalization (radio), hosp_{type} (checkboxes), hosp_{type}_duration (radio)
    """
    # Clear existing records
    Individual_Hospitalization.objects.filter(MEMBERID=exposure).delete()
    
    # Update hospitalization status on exposure
    has_hospitalization = request.POST.get('has_hospitalization', '').strip()
    if has_hospitalization:
        exposure.HOSPITALIZED_3M = has_hospitalization
        exposure.save()
    
    if has_hospitalization != 'yes':
        return 0
    
    count = 0
    for hosp_key, hosp_choice in HOSPITAL_MAPPING.items():
        if request.POST.get(f'hosp_{hosp_key}') == 'on':
            duration = request.POST.get(f'hosp_{hosp_key}_duration', '').strip()
            mapped_duration = DURATION_MAPPING.get(duration)
            
            other_text = None
            if hosp_key == 'other':
                other_text = request.POST.get('hosp_other_text', '').strip()
                logger.info(f"🔍 Hospitalization OTHER: hosp_other_text = '{other_text}'")
            
            hosp = Individual_Hospitalization(
                MEMBERID=exposure,
                HOSPITAL_TYPE=hosp_choice,
                HOSPITAL_OTHER=other_text,
                DURATION=mapped_duration
            )
            set_audit_metadata(hosp, request.user)
            hosp.save()
            
            logger.info(f"Saved hospitalization: {hosp_choice}, OTHER='{other_text}', DURATION={mapped_duration}")
            count += 1
    
    logger.info(f"Saved {count} hospitalizations")
    return count


def save_medications(request, exposure):
    """
    Parse and save medications from hardcoded template
    Template fields: has_medication (radio), med_{type}_exp2 (checkboxes), 
                     med_{type}_type_exp2 (text), med_{type}_duration (radio)
    """
    # Clear existing records
    Individual_Medication.objects.filter(MEMBERID=exposure).delete()
    
    # Update medication status on exposure
    has_medication = request.POST.get('has_medication', '').strip()
    if has_medication in ['yes', 'no', 'unknown']:
        exposure.MEDICATION_3M = has_medication
        exposure.save()
    
    if has_medication != 'yes':
        return 0
    
    count = 0
    for med_key, med_type in MEDICATION_MAPPING.items():
        if request.POST.get(f'med_{med_key}_exp2') == 'on':
            med_detail = request.POST.get(f'med_{med_key}_type_exp2', '').strip()
            duration = request.POST.get(f'med_{med_key}_duration', '').strip()
            mapped_duration = DURATION_MAPPING.get(duration)
            
            med = Individual_Medication(
                MEMBERID=exposure,
                MEDICATION_TYPE=med_type,
                MEDICATION_DETAIL=med_detail or None,
                DURATION=mapped_duration
            )
            set_audit_metadata(med, request.user)
            med.save()
            count += 1
    
    logger.info(f"Saved {count} medications")
    return count


# ==========================================
# LOAD FUNCTIONS - EXP 2/3 (Vaccination & Hospitalization)
# ==========================================

def load_vaccines(exposure):
    """
    Load vaccine data for template display
    Returns dict with vaccination_history and vaccine_{type} keys
    """
    vaccine_data = {}
    
    if exposure.VACCINATION_STATUS:
        status_reverse = {v: k for k, v in VACCINATION_STATUS_MAPPING.items()}
        vaccine_data['vaccination_history'] = status_reverse.get(exposure.VACCINATION_STATUS, '')
    
    vaccines = Individual_Vaccine.objects.filter(MEMBERID=exposure)
    type_reverse_map = {v: k for k, v in VACCINE_MAPPING.items()}
    
    for vaccine in vaccines:
        template_key = type_reverse_map.get(vaccine.VACCINE_TYPE, 'other')
        vaccine_data[f'vaccine_{template_key}'] = True
        
        if vaccine.VACCINE_TYPE == 'OTHER' and vaccine.VACCINE_OTHER:
            vaccine_data['vaccine_other_text'] = vaccine.VACCINE_OTHER
    
    return vaccine_data


def load_hospitalizations(exposure):
    """
    Load hospitalization data for template display
    Returns dict with has_hospitalization and hosp_{type} keys
    """
    hosp_data = {}
    
    hosp_data['has_hospitalization'] = exposure.HOSPITALIZED_3M if exposure.HOSPITALIZED_3M else ''
    
    hospitalizations = Individual_Hospitalization.objects.filter(MEMBERID=exposure)
    type_reverse_map = {v: k for k, v in HOSPITAL_MAPPING.items()}
    
    logger.info(f"📖 Loading {hospitalizations.count()} hospitalizations")
    
    for hosp in hospitalizations:
        template_key = type_reverse_map.get(hosp.HOSPITAL_TYPE, 'other')
        hosp_data[f'hosp_{template_key}'] = True
        
        if hosp.DURATION:
            hosp_data[f'hosp_{template_key}_duration'] = DURATION_REVERSE_MAPPING.get(hosp.DURATION, '')
        
        if hosp.HOSPITAL_TYPE == 'OTHER' and hosp.HOSPITAL_OTHER:
            hosp_data['hosp_other_text'] = hosp.HOSPITAL_OTHER
            logger.info(f"📖 Loaded OTHER hospitalization: text='{hosp.HOSPITAL_OTHER}'")
    
    logger.info(f"📖 Hospitalization data keys: {list(hosp_data.keys())}")
    return hosp_data


def load_medications(exposure):
    """
    Load medication data for template display
    Returns dict with has_medication and med_{type}_exp2 keys
    """
    med_data = {}
    
    med_data['has_medication'] = exposure.MEDICATION_3M if exposure.MEDICATION_3M else ''
    
    medications = Individual_Medication.objects.filter(MEMBERID=exposure)
    type_reverse_map = {v: k for k, v in MEDICATION_MAPPING.items()}
    
    for med in medications:
        template_key = type_reverse_map.get(med.MEDICATION_TYPE, 'other')
        
        med_data[f'med_{template_key}_exp2'] = True
        
        if med.MEDICATION_DETAIL:
            med_data[f'med_{template_key}_type_exp2'] = med.MEDICATION_DETAIL
        
        if med.DURATION:
            med_data[f'med_{template_key}_duration'] = DURATION_REVERSE_MAPPING.get(med.DURATION, '')
    
    return med_data


# ==========================================
# SAVE FUNCTIONS - EXP 3/3 (Food & Travel)
# ==========================================

def save_food_frequency(request, individual):
    """
    Parse and save food frequency from hardcoded template
    Template fields: freq_rice, freq_red_meat, freq_poultry, freq_seafood, etc (radio buttons)
    """
    # Get or create food frequency record
    food_freq, created = Individual_FoodFrequency.objects.get_or_create(
        MEMBERID=individual
    )
    
    # Update all fields
    updated_count = 0
    for template_field, model_field in FOOD_FIELD_MAPPING.items():
        template_value = request.POST.get(template_field, '').strip()
        
        if template_value in FOOD_FREQ_MAPPING:
            model_value = FOOD_FREQ_MAPPING[template_value]
            setattr(food_freq, model_field, model_value)
            updated_count += 1
    
    # Set audit metadata and save
    set_audit_metadata(food_freq, request.user)
    food_freq.save()
    
    action = "Created" if created else "Updated"
    logger.info(f"{action} food frequency with {updated_count} fields")
    return food_freq


def save_travel_history(request, individual):
    """
    Parse and save travel history from hardcoded template
    Template fields: travel_international, travel_domestic (radio buttons)
    """
    # Clear existing travel records
    Individual_Travel.objects.filter(MEMBERID=individual).delete()
    
    # Travel types mapping: template field -> model choice
    travel_types = {
        'travel_international': 'international',
        'travel_domestic': 'domestic',
    }
    
    count = 0
    for template_field, travel_type in travel_types.items():
        template_value = request.POST.get(template_field, '').strip()
        
        if template_value and template_value in TRAVEL_FREQ_MAPPING:
            model_frequency = TRAVEL_FREQ_MAPPING[template_value]
            
            travel = Individual_Travel(
                MEMBERID=individual,
                TRAVEL_TYPE=travel_type,
                FREQUENCY=model_frequency
            )
            set_audit_metadata(travel, request.user)
            travel.save()
            count += 1
            logger.info(f"Saved travel: {travel_type} - {model_frequency}")
    
    logger.info(f"Saved {count} travel records")
    return count


# ==========================================
# LOAD FUNCTIONS - EXP 3/3 (Food & Travel)
# ==========================================

def load_food_frequency(individual):
    """
    Load food frequency data for template display
    Returns dict with freq_{food_type} keys
    """
    food_data = {}
    
    try:
        food_freq = Individual_FoodFrequency.objects.get(MEMBERID=individual)
    except Individual_FoodFrequency.DoesNotExist:
        return food_data
    
    # Field mapping: model field -> template name
    field_reverse_mapping = {v: k for k, v in FOOD_FIELD_MAPPING.items()}
    
    for model_field, template_field in field_reverse_mapping.items():
        model_value = getattr(food_freq, model_field, None)
        
        if model_value and model_value in FOOD_FREQ_REVERSE_MAPPING:
            template_value = FOOD_FREQ_REVERSE_MAPPING[model_value]
            food_data[template_field] = template_value
    
    return food_data


def load_travel_history(individual):
    """
    Load travel history data for template display
    Returns dict with travel_international and travel_domestic keys
    """
    travel_data = {}
    
    travels = Individual_Travel.objects.filter(MEMBERID=individual)
    
    type_reverse_mapping = {
        'international': 'travel_international',
        'domestic': 'travel_domestic',
    }
    
    for travel in travels:
        if travel.TRAVEL_TYPE in type_reverse_mapping and travel.FREQUENCY:
            template_field = type_reverse_mapping[travel.TRAVEL_TYPE]
            
            if travel.FREQUENCY in TRAVEL_FREQ_REVERSE_MAPPING:
                template_value = TRAVEL_FREQ_REVERSE_MAPPING[travel.FREQUENCY]
                travel_data[template_field] = template_value
    
    return travel_data


# ==========================================
# ✅ NEW: CHANGE DETECTION FOR AUDIT LOG
# ==========================================

def detect_exp1_flat_field_changes(request, exposure):
    """
    ✅ Detect changes in EXP 1/3 flat fields (Water & Comorbidities)
    
    Compares POST data with database data for:
    - Water sources (checkboxes)
    - Water treatment (checkboxes)
    - Comorbidities (checkboxes)
    - Radio buttons (shared_toilet, water_treatment, has_conditions)
    
    ⚠️ IMPORTANT: These radio buttons are hardcoded HTML, NOT in Django form!
    So we must compare POST values directly with database values.
    
    ⚠️ CRITICAL: The exposure object passed in may have been modified by Django form binding.
    We MUST refresh from DB to get the actual stored values.
    
    Returns:
        list: List of change dicts [{field, old_value, new_value, old_display, new_display}]
    """
    changes = []
    
    # ✅ CRITICAL FIX: Refresh exposure from database to get actual stored values
    # The exposure object may have been modified by Django form binding
    exposure.refresh_from_db()
    
    # Load old data from database
    old_water_data = load_water_data(exposure)
    old_treatment_data = load_treatment_data(exposure)
    old_comorbidity_data = load_comorbidity_data(exposure)
    
    # ==========================================
    # 1. Radio buttons on main exposure model
    # ⚠️ These are hardcoded HTML, not in Django form
    # ==========================================
    
    # ✅ DEBUG: Log actual database values
    logger.info("=" * 60)
    logger.info("🔍 DEBUG: Reading radio button values from database:")
    logger.info(f"   exposure.SHARED_TOILET = {repr(getattr(exposure, 'SHARED_TOILET', 'NOT_FOUND'))}")
    logger.info(f"   old_treatment_data = {old_treatment_data}")
    logger.info(f"   old_comorbidity_data = {old_comorbidity_data}")
    logger.info("=" * 60)
    
    # SHARED_TOILET radio - Read from model field
    old_shared_toilet_raw = getattr(exposure, 'SHARED_TOILET', None)
    old_shared_toilet = str(old_shared_toilet_raw or '').strip().lower()
    
    # ✅ FIX: Check if field is in POST (user actually submitted it)
    if 'shared_toilet' in request.POST:
        new_shared_toilet = request.POST.get('shared_toilet', '').strip().lower()
    else:
        new_shared_toilet = old_shared_toilet
    
    logger.info(f"🔍 SHARED_TOILET: old='{old_shared_toilet}', new='{new_shared_toilet}', in_POST={'shared_toilet' in request.POST}")
    
    # Detect change: old vs new (both normalized)
    if old_shared_toilet != new_shared_toilet:
        changes.append({
            'field': 'SHARED_TOILET',
            'old_value': old_shared_toilet or '(trống)',
            'new_value': new_shared_toilet or '(trống)',
            'old_display': old_shared_toilet or '(trống)',
            'new_display': new_shared_toilet or '(trống)',
        })
    
    # ✅ WATER_TREATMENT radio - Read from old_treatment_data (derived from Individual_WaterTreatment table)
    old_water_treatment = str(old_treatment_data.get('water_treatment', '') or '').strip().lower()
    
    if 'water_treatment' in request.POST:
        new_water_treatment = request.POST.get('water_treatment', '').strip().lower()
    else:
        new_water_treatment = old_water_treatment
    
    logger.info(f"🔍 WATER_TREATMENT: old='{old_water_treatment}', new='{new_water_treatment}', in_POST={'water_treatment' in request.POST}")
    
    # Detect change
    if old_water_treatment != new_water_treatment:
        changes.append({
            'field': 'WATER_TREATMENT',
            'old_value': old_water_treatment or '(trống)',
            'new_value': new_water_treatment or '(trống)',
            'old_display': old_water_treatment or '(trống)',
            'new_display': new_water_treatment or '(trống)',
        })
    
    # ✅ HAS_COMORBIDITY radio - Read from old_comorbidity_data (derived from Individual_Comorbidity table)
    old_has_comorbidity = str(old_comorbidity_data.get('has_conditions', '') or '').strip().lower()
    
    if 'has_conditions' in request.POST:
        new_has_comorbidity = request.POST.get('has_conditions', '').strip().lower()
    else:
        new_has_comorbidity = old_has_comorbidity
    
    logger.info(f"🔍 HAS_COMORBIDITY: old='{old_has_comorbidity}', new='{new_has_comorbidity}', in_POST={'has_conditions' in request.POST}")
    
    # Detect change
    if old_has_comorbidity != new_has_comorbidity:
        changes.append({
            'field': 'HAS_COMORBIDITY',
            'old_value': old_has_comorbidity or '(trống)',
            'new_value': new_has_comorbidity or '(trống)',
            'old_display': old_has_comorbidity or '(trống)',
            'new_display': new_has_comorbidity or '(trống)',
        })
    
    # ==========================================
    # 2. Water source checkboxes
    # ==========================================
    for source_key in WATER_SOURCE_MAPPING.keys():
        for usage in ['drink', 'domestic', 'irrigation']:
            field_name = f'water_{source_key}_{usage}'
            old_val = old_water_data.get(field_name, False)
            new_val = request.POST.get(field_name) == 'on'
            
            if old_val != new_val:
                changes.append({
                    'field': field_name,
                    'old_value': old_val,
                    'new_value': new_val,
                    'old_display': 'Có' if old_val else 'Không',
                    'new_display': 'Có' if new_val else 'Không',
                })
        
        # Other purpose text field
        other_field = f'water_{source_key}_other'
        old_other = old_water_data.get(other_field, '')
        new_other = request.POST.get(other_field, '').strip()
        if str(old_other or '').strip() != str(new_other or '').strip():
            changes.append({
                'field': other_field,
                'old_value': old_other,
                'new_value': new_other,
                'old_display': old_other or '(trống)',
                'new_display': new_other or '(trống)',
            })
    
    # Water other source name
    old_water_other_name = old_water_data.get('water_other_src_name', '')
    new_water_other_name = request.POST.get('water_other_src_name', '').strip()
    if str(old_water_other_name or '').strip() != str(new_water_other_name or '').strip():
        changes.append({
            'field': 'water_other_src_name',
            'old_value': old_water_other_name,
            'new_value': new_water_other_name,
            'old_display': old_water_other_name or '(trống)',
            'new_display': new_water_other_name or '(trống)',
        })
    
    # ==========================================
    # 3. Water treatment checkboxes
    # ==========================================
    for treatment_key in WATER_TREATMENT_MAPPING.keys():
        field_name = f'treatment_{treatment_key}'
        old_val = old_treatment_data.get(field_name, False)
        new_val = request.POST.get(field_name) == 'on'
        
        if old_val != new_val:
            changes.append({
                'field': field_name,
                'old_value': old_val,
                'new_value': new_val,
                'old_display': 'Có' if old_val else 'Không',
                'new_display': 'Có' if new_val else 'Không',
            })
    
    # Treatment other text
    old_treatment_other = old_treatment_data.get('treatment_other_text', '')
    new_treatment_other = request.POST.get('treatment_other_text', '').strip()
    if str(old_treatment_other or '').strip() != str(new_treatment_other or '').strip():
        changes.append({
            'field': 'treatment_other_text',
            'old_value': old_treatment_other,
            'new_value': new_treatment_other,
            'old_display': old_treatment_other or '(trống)',
            'new_display': new_treatment_other or '(trống)',
        })
    
    # ==========================================
    # 4. Comorbidity checkboxes
    # ==========================================
    condition_keys = list(COMORBIDITY_MAPPING.keys()) + ['other', 'cancer']
    
    for condition_key in condition_keys:
        # Checkbox
        field_name = f'condition_{condition_key}'
        old_val = old_comorbidity_data.get(field_name, False)
        new_val = request.POST.get(field_name) == 'on'
        
        if old_val != new_val:
            changes.append({
                'field': field_name,
                'old_value': old_val,
                'new_value': new_val,
                'old_display': 'Có' if old_val else 'Không',
                'new_display': 'Có' if new_val else 'Không',
            })
        
        # Treatment status radio
        treated_field = f'condition_{condition_key}_treated'
        old_treated = old_comorbidity_data.get(treated_field, '')
        new_treated = request.POST.get(treated_field, '').strip()
        if str(old_treated or '').strip() != str(new_treated or '').strip():
            changes.append({
                'field': treated_field,
                'old_value': old_treated,
                'new_value': new_treated,
                'old_display': old_treated or '(trống)',
                'new_display': new_treated or '(trống)',
            })
    
    # Condition other text
    old_condition_other_text = old_comorbidity_data.get('condition_other_text', '')
    new_condition_other_text = request.POST.get('condition_other_text', '').strip()
    if str(old_condition_other_text or '').strip() != str(new_condition_other_text or '').strip():
        changes.append({
            'field': 'condition_other_text',
            'old_value': old_condition_other_text,
            'new_value': new_condition_other_text,
            'old_display': old_condition_other_text or '(trống)',
            'new_display': new_condition_other_text or '(trống)',
        })
    
    logger.info(f"🔍 detect_exp1_flat_field_changes: Found {len(changes)} changes")
    return changes


def detect_exp2_flat_field_changes(request, exposure):
    """
    ✅ Detect changes in EXP 2/3 flat fields (Vaccination & Hospitalization)
    
    Compares POST data with database data for:
    - Vaccination history (radio)
    - Vaccine checkboxes
    - Hospitalization status (radio)
    - Hospital type checkboxes + duration
    - Medication status (radio)
    - Medication checkboxes + duration
    
    ⚠️ IMPORTANT: Radio buttons are hardcoded HTML, NOT in Django form!
    Only detect change if POST actually has a value.
    
    ⚠️ CRITICAL: The exposure object passed in may have been modified by Django form binding.
    We MUST refresh from DB to get the actual stored values.
    
    Returns:
        list: List of change dicts [{field, old_value, new_value, old_display, new_display}]
    """
    changes = []
    
    # ✅ CRITICAL FIX: Refresh exposure from database to get actual stored values
    # The exposure object may have been modified by Django form binding
    exposure.refresh_from_db()
    
    # Load old data from database
    old_vaccine_data = load_vaccines(exposure)
    old_hosp_data = load_hospitalizations(exposure)
    old_med_data = load_medications(exposure)
    
    # ==========================================
    # 1. Vaccination history radio - Read from old_vaccine_data
    # ==========================================
    old_vax_history = str(old_vaccine_data.get('vaccination_history', '') or '').strip().lower()
    
    # ✅ FIX: Check if field is in POST
    if 'vaccination_history' in request.POST:
        new_vax_history = request.POST.get('vaccination_history', '').strip().lower()
    else:
        new_vax_history = old_vax_history
    
    logger.info(f"🔍 vaccination_history: old='{old_vax_history}', new='{new_vax_history}', in_POST={'vaccination_history' in request.POST}")
    
    # Detect change
    if old_vax_history != new_vax_history:
        changes.append({
            'field': 'vaccination_history',
            'old_value': old_vax_history or '(trống)',
            'new_value': new_vax_history or '(trống)',
            'old_display': old_vax_history or '(trống)',
            'new_display': new_vax_history or '(trống)',
        })
    
    # ==========================================
    # 2. Vaccine checkboxes
    # ==========================================
    for vaccine_key in VACCINE_MAPPING.keys():
        field_name = f'vaccine_{vaccine_key}'
        old_val = old_vaccine_data.get(field_name, False)
        new_val = request.POST.get(field_name) == 'on'
        
        if old_val != new_val:
            changes.append({
                'field': field_name,
                'old_value': old_val,
                'new_value': new_val,
                'old_display': 'Có' if old_val else 'Không',
                'new_display': 'Có' if new_val else 'Không',
            })
    
    # Vaccine other text
    old_vax_other = old_vaccine_data.get('vaccine_other_text', '')
    new_vax_other = request.POST.get('vaccine_other_text', '').strip()
    if str(old_vax_other or '').strip() != str(new_vax_other or '').strip():
        changes.append({
            'field': 'vaccine_other_text',
            'old_value': old_vax_other,
            'new_value': new_vax_other,
            'old_display': old_vax_other or '(trống)',
            'new_display': new_vax_other or '(trống)',
        })
    
    # ==========================================
    # 3. Hospitalization radio and checkboxes - Read from old_hosp_data
    # ==========================================
    old_has_hosp = str(old_hosp_data.get('has_hospitalization', '') or '').strip().lower()
    
    # ✅ FIX: Check if field is in POST
    if 'has_hospitalization' in request.POST:
        new_has_hosp = request.POST.get('has_hospitalization', '').strip().lower()
    else:
        new_has_hosp = old_has_hosp
    
    logger.info(f"🔍 has_hospitalization: old='{old_has_hosp}', new='{new_has_hosp}', in_POST={'has_hospitalization' in request.POST}")
    
    # Detect change
    if old_has_hosp != new_has_hosp:
        changes.append({
            'field': 'has_hospitalization',
            'old_value': old_has_hosp or '(trống)',
            'new_value': new_has_hosp or '(trống)',
            'old_display': old_has_hosp or '(trống)',
            'new_display': new_has_hosp or '(trống)',
        })
    
    for hosp_key in HOSPITAL_MAPPING.keys():
        # Checkbox
        field_name = f'hosp_{hosp_key}'
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
        duration_field = f'hosp_{hosp_key}_duration'
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
    old_hosp_other = old_hosp_data.get('hosp_other_text', '')
    new_hosp_other = request.POST.get('hosp_other_text', '').strip()
    if str(old_hosp_other or '').strip() != str(new_hosp_other or '').strip():
        changes.append({
            'field': 'hosp_other_text',
            'old_value': old_hosp_other,
            'new_value': new_hosp_other,
            'old_display': old_hosp_other or '(trống)',
            'new_display': new_hosp_other or '(trống)',
        })
    
    # ==========================================
    # 4. Medication radio and checkboxes - Read from old_med_data
    # ==========================================
    old_has_med = str(old_med_data.get('has_medication', '') or '').strip().lower()
    
    # ✅ FIX: Check if field is in POST
    if 'has_medication' in request.POST:
        new_has_med = request.POST.get('has_medication', '').strip().lower()
    else:
        new_has_med = old_has_med
    
    logger.info(f"🔍 has_medication: old='{old_has_med}', new='{new_has_med}', in_POST={'has_medication' in request.POST}")
    
    # Detect change
    if old_has_med != new_has_med:
        changes.append({
            'field': 'has_medication',
            'old_value': old_has_med or '(trống)',
            'new_value': new_has_med or '(trống)',
            'old_display': old_has_med or '(trống)',
            'new_display': new_has_med or '(trống)',
        })
    
    for med_key in MEDICATION_MAPPING.keys():
        # Checkbox (note: uses _exp2 suffix)
        field_name = f'med_{med_key}_exp2'
        old_val = old_med_data.get(field_name, False)
        new_val = request.POST.get(field_name) == 'on'
        
        if old_val != new_val:
            changes.append({
                'field': field_name,
                'old_value': old_val,
                'new_value': new_val,
                'old_display': 'Có' if old_val else 'Không',
                'new_display': 'Có' if new_val else 'Không',
            })
        
        # Detail text
        type_field = f'med_{med_key}_type_exp2'
        old_type = old_med_data.get(type_field, '')
        new_type = request.POST.get(type_field, '').strip()
        if str(old_type or '').strip() != str(new_type or '').strip():
            changes.append({
                'field': type_field,
                'old_value': old_type,
                'new_value': new_type,
                'old_display': old_type or '(trống)',
                'new_display': new_type or '(trống)',
            })
        
        # Duration radio
        duration_field = f'med_{med_key}_duration'
        old_duration = old_med_data.get(duration_field, '')
        new_duration = request.POST.get(duration_field, '').strip()
        if str(old_duration or '').strip() != str(new_duration or '').strip():
            changes.append({
                'field': duration_field,
                'old_value': old_duration,
                'new_value': new_duration,
                'old_display': old_duration or '(trống)',
                'new_display': new_duration or '(trống)',
            })
    
    logger.info(f"🔍 detect_exp2_flat_field_changes: Found {len(changes)} changes")
    return changes


def detect_exp3_flat_field_changes(request, individual):
    """
    ✅ Detect changes in EXP 3/3 flat fields (Food & Travel)
    
    Compares POST data with database data for:
    - Food frequency (radio buttons)
    - Travel history (radio buttons)
    
    Returns:
        list: List of change dicts [{field, old_value, new_value, old_display, new_display}]
    """
    changes = []
    
    # Load old data from database
    old_food_data = load_food_frequency(individual)
    old_travel_data = load_travel_history(individual)
    
    # ==========================================
    # 1. Food frequency radio buttons
    # ==========================================
    for template_field in FOOD_FIELD_MAPPING.keys():
        old_val = old_food_data.get(template_field, '')
        new_val = request.POST.get(template_field, '').strip()
        
        if str(old_val or '').strip() != str(new_val or '').strip():
            # ✅ Convert numeric values to display names
            old_display = FOOD_FREQ_MAPPING.get(str(old_val), old_val) if old_val else '(trống)'
            new_display = FOOD_FREQ_MAPPING.get(str(new_val), new_val) if new_val else '(trống)'
            
            changes.append({
                'field': template_field,
                'old_value': old_val,
                'new_value': new_val,
                'old_display': old_display,
                'new_display': new_display,
            })
    
    # ==========================================
    # 2. Travel history radio buttons
    # ==========================================
    for template_field in ['travel_international', 'travel_domestic']:
        old_val = old_travel_data.get(template_field, '')
        new_val = request.POST.get(template_field, '').strip()
        
        if str(old_val or '').strip() != str(new_val or '').strip():
            changes.append({
                'field': template_field,
                'old_value': old_val,
                'new_value': new_val,
                'old_display': old_val or '(trống)',
                'new_display': new_val or '(trống)',
            })
    
    logger.info(f"🔍 detect_exp3_flat_field_changes: Found {len(changes)} changes")
    return changes


# ==========================================
# EXPORTS
# ==========================================

__all__ = [
    # Utility functions
    'set_audit_metadata',
    'make_form_readonly',
    
    # EXP 1/3 - Water & Comorbidities
    'save_water_sources',
    'save_water_treatment',
    'save_comorbidities',
    'load_water_data',
    'load_treatment_data',
    'load_comorbidity_data',
    
    # EXP 2/3 - Vaccination & Hospitalization
    'save_vaccines',
    'save_hospitalizations',
    'save_medications',
    'load_vaccines',
    'load_hospitalizations',
    'load_medications',
    
    # EXP 3/3 - Food & Travel
    'save_food_frequency',
    'save_travel_history',
    'load_food_frequency',
    'load_travel_history',
    
    # ✅ NEW: Change detection for audit log
    'detect_exp1_flat_field_changes',
    'detect_exp2_flat_field_changes',
    'detect_exp3_flat_field_changes',
]