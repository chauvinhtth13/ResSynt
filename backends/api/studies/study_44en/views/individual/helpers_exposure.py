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
7. Save functions (EXP 3/3) - Food & Travel (TODO)
8. Load functions (EXP 3/3) (TODO)
"""

import logging
from backends.studies.study_44en.models.individual import (
    Individual_WaterSource,
    Individual_WaterTreatment,
    Individual_Comorbidity,
    Individual_Vaccine,
    Individual_Hospitalization,
    Individual_Medication,
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
# Template fields: condition_hypertension, condition_diabetes, condition_heart, 
#                  condition_kidney, condition_liver, condition_asthma, condition_cancer, condition_other
COMORBIDITY_MAPPING = {
    'hypertension': 'HYPERTENSION',
    'diabetes': 'DIABETES',
    'heart': 'CARDIOVASCULAR',
    'kidney': 'CHRONIC_KIDNEY',
    'liver': 'CHRONIC_HEPATITIS',
    'asthma': 'COPD',  # Template uses 'asthma' for Asthma/COPD
    # 'cancer' is not in model choices - will be skipped or use OTHER
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
    Individual_WaterSource.objects.filter(MEMBER=exposure).delete()
    
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
                MEMBER=exposure,
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
    Individual_WaterTreatment.objects.filter(MEMBER=exposure).delete()
    
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
                MEMBER=exposure,
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
    
    Template has these conditions:
    - condition_hypertension -> HYPERTENSION
    - condition_diabetes -> DIABETES
    - condition_heart -> CARDIOVASCULAR
    - condition_kidney -> CHRONIC_KIDNEY
    - condition_liver -> CHRONIC_HEPATITIS
    - condition_asthma -> COPD (template says "Asthma/COPD")
    - condition_cancer -> Not in model, will skip
    - condition_other -> OTHER
    
    Treatment status mapping:
    - Template: 'treated' -> Model: 'treating'
    - Template: 'not_treated' -> Model: 'not_treating'
    """
    # Clear existing records
    Individual_Comorbidity.objects.filter(MEMBER=exposure).delete()
    
    # Check if person has conditions
    has_conditions = request.POST.get('has_conditions', '').strip()
    if has_conditions != 'yes':
        return 0
    
    count = 0
    
    # Process conditions that are in the mapping
    for condition_key, condition_choice in COMORBIDITY_MAPPING.items():
        if request.POST.get(f'condition_{condition_key}') == 'on':
            # Get treatment status from template (values: 'treated' or 'not_treated')
            treatment_status_template = request.POST.get(f'condition_{condition_key}_treated', '').strip()
            
            # Map template values to model values
            treatment_status_model = None
            if treatment_status_template == 'treated':
                treatment_status_model = 'treating'  # Model uses 'treating'
            elif treatment_status_template == 'not_treated':
                treatment_status_model = 'not_treating'  # Model uses 'not_treating'
            
            # Create comorbidity record
            comorb = Individual_Comorbidity(
                MEMBER=exposure,
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
        
        # Map template values to model values
        treatment_status_model = None
        if treatment_status_template == 'treated':
            treatment_status_model = 'treating'
        elif treatment_status_template == 'not_treated':
            treatment_status_model = 'not_treating'
        
        comorb = Individual_Comorbidity(
            MEMBER=exposure,
            COMORBIDITY_TYPE='OTHER',
            COMORBIDITY_OTHER=other_text if other_text else None,
            TREATMENT_STATUS=treatment_status_model
        )
        set_audit_metadata(comorb, request.user)
        comorb.save()
        count += 1
        logger.info(f"Saved comorbidity: OTHER ({other_text}), status={treatment_status_model}")
    
    # NOTE: condition_cancer is in template but not in model choices
    # We skip it or could map to OTHER if needed
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
    
    water_sources = Individual_WaterSource.objects.filter(MEMBER=exposure)
    for ws in water_sources:
        # Map model SOURCE_TYPE to template key (handle uppercase/lowercase)
        # Model: 'BOTTLED' or 'bottled' -> Template: 'bottle'
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
    
    treatments = Individual_WaterTreatment.objects.filter(MEMBER=exposure)
    
    # Create reverse mapping (model choice -> template key)
    type_reverse_map = {v: k for k, v in WATER_TREATMENT_MAPPING.items()}
    
    for treatment in treatments:
        template_key = type_reverse_map.get(treatment.TREATMENT_TYPE, treatment.TREATMENT_TYPE.lower())
        treatment_data[f'treatment_{template_key}'] = True
        
        if treatment.TREATMENT_TYPE == 'OTHER' and treatment.TREATMENT_TYPE_OTHER:
            treatment_data['treatment_other_text'] = treatment.TREATMENT_TYPE_OTHER
    
    # Set water_treatment radio to 'yes' if any treatments exist
    if treatments.exists():
        treatment_data['water_treatment'] = 'yes'
    
    return treatment_data


def load_comorbidity_data(exposure):
    """
    Load comorbidity data for template display
    Returns dict with condition_{type} and has_conditions keys
    
    Maps model data back to template field names:
    - HYPERTENSION -> condition_hypertension
    - DIABETES -> condition_diabetes
    - CARDIOVASCULAR -> condition_heart
    - CHRONIC_KIDNEY -> condition_kidney
    - CHRONIC_HEPATITIS -> condition_liver
    - COPD -> condition_asthma (template says "Asthma/COPD")
    - ASTHMA -> condition_asthma
    - OTHER -> condition_other
    
    Treatment status mapping:
    - Model: 'treating' -> Template: 'treated'
    - Model: 'not_treating' -> Template: 'not_treated'
    """
    comorbidity_data = {}
    
    comorbidities = Individual_Comorbidity.objects.filter(MEMBER=exposure)
    
    # Create reverse mapping (model choice -> template key)
    # Need to handle both COPD and ASTHMA mapping to same template field
    type_reverse_map = {
        'HYPERTENSION': 'hypertension',
        'DIABETES': 'diabetes',
        'CARDIOVASCULAR': 'heart',
        'CHRONIC_KIDNEY': 'kidney',
        'CHRONIC_HEPATITIS': 'liver',
        'COPD': 'asthma',  # Template uses 'asthma' for COPD
        'ASTHMA': 'asthma',  # Both ASTHMA and COPD map to same checkbox
        'OTHER': 'other',
    }
    
    for comorb in comorbidities:
        template_key = type_reverse_map.get(comorb.COMORBIDITY_TYPE, 'other')
        
        # Set checkbox
        comorbidity_data[f'condition_{template_key}'] = True
        
        # Set treatment status - map model values to template values
        if comorb.TREATMENT_STATUS == 'treating':
            comorbidity_data[f'condition_{template_key}_treated'] = 'treated'  # Model 'treating' -> Template 'treated'
        elif comorb.TREATMENT_STATUS == 'not_treating':
            comorbidity_data[f'condition_{template_key}_treated'] = 'not_treated'  # Model 'not_treating' -> Template 'not_treated'
        
        # Set other text if applicable
        if comorb.COMORBIDITY_TYPE == 'OTHER' and comorb.COMORBIDITY_OTHER:
            comorbidity_data['condition_other_text'] = comorb.COMORBIDITY_OTHER
    
    # Set has_conditions radio to 'yes' if any comorbidities exist
    if comorbidities.exists():
        comorbidity_data['has_conditions'] = 'yes'
    
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
    Individual_Vaccine.objects.filter(MEMBER=exposure).delete()
    
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
            # Get other vaccine text if applicable
            other_text = None
            if vaccine_key == 'other':
                other_text = request.POST.get('vaccine_other_text', '').strip()
            
            # Create vaccine record
            vaccine = Individual_Vaccine(
                MEMBER=exposure,
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
    Individual_Hospitalization.objects.filter(MEMBER=exposure).delete()
    
    # Update hospitalization status on exposure
    has_hospitalization = request.POST.get('has_hospitalization', '').strip()
    if has_hospitalization:
        exposure.HOSPITALIZED_3M = has_hospitalization
        exposure.save()
    
    # Only save details if 'yes' selected
    if has_hospitalization != 'yes':
        return 0
    
    count = 0
    for hosp_key, hosp_choice in HOSPITAL_MAPPING.items():
        if request.POST.get(f'hosp_{hosp_key}') == 'on':
            # Get duration
            duration = request.POST.get(f'hosp_{hosp_key}_duration', '').strip()
            mapped_duration = DURATION_MAPPING.get(duration)
            
            # Get other hospital text if applicable
            other_text = None
            if hosp_key == 'other':
                other_text = request.POST.get('hosp_other_text', '').strip()
                logger.info(f"🔍 Hospitalization OTHER: hosp_other_text = '{other_text}'")
            
            # Create hospitalization record
            hosp = Individual_Hospitalization(
                MEMBER=exposure,
                HOSPITAL_TYPE=hosp_choice,
                HOSPITAL_OTHER=other_text,
                DURATION=mapped_duration
            )
            set_audit_metadata(hosp, request.user)
            hosp.save()
            
            logger.info(f"✅ Saved hospitalization: {hosp_choice}, OTHER='{other_text}', DURATION={mapped_duration}")
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
    Individual_Medication.objects.filter(MEMBER=exposure).delete()
    
    # Update medication status on exposure
    has_medication = request.POST.get('has_medication', '').strip()
    if has_medication in ['yes', 'no', 'unknown']:
        exposure.MEDICATION_3M = has_medication
        exposure.save()
    
    # Only save details if 'yes' selected
    if has_medication != 'yes':
        return 0
    
    count = 0
    for med_key, med_type in MEDICATION_MAPPING.items():
        # Note: template uses _exp2 suffix for checkboxes
        if request.POST.get(f'med_{med_key}_exp2') == 'on':
            # Get medication detail/type text
            med_detail = request.POST.get(f'med_{med_key}_type_exp2', '').strip()
            
            # Get duration
            duration = request.POST.get(f'med_{med_key}_duration', '').strip()
            mapped_duration = DURATION_MAPPING.get(duration)
            
            # Create medication record
            med = Individual_Medication(
                MEMBER=exposure,
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
    
    # Load vaccination status
    if exposure.VACCINATION_STATUS:
        status_reverse = {v: k for k, v in VACCINATION_STATUS_MAPPING.items()}
        vaccine_data['vaccination_history'] = status_reverse.get(exposure.VACCINATION_STATUS, '')
    
    # Load individual vaccines
    vaccines = Individual_Vaccine.objects.filter(MEMBER=exposure)
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
    
    # Load hospitalization status - always set, even if None
    hosp_data['has_hospitalization'] = exposure.HOSPITALIZED_3M if exposure.HOSPITALIZED_3M else ''
    
    # Load individual hospitalizations
    hospitalizations = Individual_Hospitalization.objects.filter(MEMBER=exposure)
    type_reverse_map = {v: k for k, v in HOSPITAL_MAPPING.items()}
    
    logger.info(f"📖 Loading {hospitalizations.count()} hospitalizations")
    
    for hosp in hospitalizations:
        template_key = type_reverse_map.get(hosp.HOSPITAL_TYPE, 'other')
        hosp_data[f'hosp_{template_key}'] = True
        
        # Map duration back to template values
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
    
    # Load medication status - always set, even if None
    med_data['has_medication'] = exposure.MEDICATION_3M if exposure.MEDICATION_3M else ''
    
    # Load individual medications
    medications = Individual_Medication.objects.filter(MEMBER=exposure)
    type_reverse_map = {v: k for k, v in MEDICATION_MAPPING.items()}
    
    for med in medications:
        template_key = type_reverse_map.get(med.MEDICATION_TYPE, 'other')
        
        # Note: template uses _exp2 suffix
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
    
    Values mapping:
    - Template: '0', '1', '2', '3', '4', '5' (numeric strings)
    - Model: 'never', '1-3/month', '1-2/week', '3-5/week', '1/day', '2+/day'
    """
    from backends.studies.study_44en.models.individual import Individual_FoodFrequency
    
    # Value mapping: template numeric -> model choice
    freq_mapping = {
        '0': 'never',
        '1': '1-3/month',
        '2': '1-2/week',
        '3': '3-5/week',
        '4': '1/day',
        '5': '2+/day',
    }
    
    # Field mapping: template name -> model field
    field_mapping = {
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
    
    # Get or create food frequency record
    food_freq, created = Individual_FoodFrequency.objects.get_or_create(
        MEMBER=individual
    )
    
    # Update all fields
    updated_count = 0
    for template_field, model_field in field_mapping.items():
        template_value = request.POST.get(template_field, '').strip()
        
        if template_value in freq_mapping:
            model_value = freq_mapping[template_value]
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
    
    Values mapping:
    - Template: 'daily', '1-2_week', '1-2_month', 'less_month', 'no'
    - Model: 'daily', '1-2/week', '1-2/month', '<1/month', 'never'
    """
    from backends.studies.study_44en.models.individual import Individual_Travel
    
    # Clear existing travel records
    Individual_Travel.objects.filter(MEMBER=individual).delete()
    
    # Value mapping: template -> model
    freq_mapping = {
        'daily': 'daily',
        '1-2_week': '1-2/week',
        '1-2_month': '1-2/month',
        'less_month': '<1/month',
        'no': 'never',
    }
    
    # Travel types mapping: template field -> model choice
    travel_types = {
        'travel_international': 'international',
        'travel_domestic': 'domestic',
    }
    
    count = 0
    for template_field, travel_type in travel_types.items():
        template_value = request.POST.get(template_field, '').strip()
        
        if template_value and template_value in freq_mapping:
            model_frequency = freq_mapping[template_value]
            
            # Only create record if not 'never'
            # Or always create to track the answer
            travel = Individual_Travel(
                MEMBER=individual,
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
    
    Maps model data back to template values:
    - Model: 'never', '1-3/month', etc → Template: '0', '1', '2', etc
    """
    from backends.studies.study_44en.models.individual import Individual_FoodFrequency
    
    food_data = {}
    
    try:
        food_freq = Individual_FoodFrequency.objects.get(MEMBER=individual)
    except Individual_FoodFrequency.DoesNotExist:
        return food_data
    
    # Reverse mapping: model choice -> template value
    freq_reverse_mapping = {
        'never': '0',
        '1-3/month': '1',
        '1-2/week': '2',
        '3-5/week': '3',
        '1/day': '4',
        '2+/day': '5',
    }
    
    # Field mapping: model field -> template name
    field_reverse_mapping = {
        'RICE_NOODLES': 'freq_rice',
        'RED_MEAT': 'freq_red_meat',
        'POULTRY': 'freq_poultry',
        'FISH_SEAFOOD': 'freq_seafood',
        'EGGS': 'freq_eggs',
        'RAW_VEGETABLES': 'freq_raw_veg',
        'COOKED_VEGETABLES': 'freq_cooked_veg',
        'DAIRY': 'freq_dairy',
        'FERMENTED': 'freq_fermented',
        'BEER': 'freq_beer',
        'ALCOHOL': 'freq_alcohol',
    }
    
    for model_field, template_field in field_reverse_mapping.items():
        model_value = getattr(food_freq, model_field, None)
        
        if model_value and model_value in freq_reverse_mapping:
            template_value = freq_reverse_mapping[model_value]
            food_data[template_field] = template_value
    
    return food_data


def load_travel_history(individual):
    """
    Load travel history data for template display
    Returns dict with travel_international and travel_domestic keys
    
    Maps model data back to template values:
    - Model: 'daily', '1-2/week', etc → Template: 'daily', '1-2_week', etc
    """
    from backends.studies.study_44en.models.individual import Individual_Travel
    
    travel_data = {}
    
    travels = Individual_Travel.objects.filter(MEMBER=individual)
    
    # Reverse mapping: model frequency -> template value
    freq_reverse_mapping = {
        'daily': 'daily',
        '1-2/week': '1-2_week',
        '1-2/month': '1-2_month',
        '<1/month': 'less_month',
        'never': 'no',
    }
    
    # Travel type mapping: model type -> template field
    type_reverse_mapping = {
        'international': 'travel_international',
        'domestic': 'travel_domestic',
    }
    
    for travel in travels:
        if travel.TRAVEL_TYPE in type_reverse_mapping and travel.FREQUENCY:
            template_field = type_reverse_mapping[travel.TRAVEL_TYPE]
            
            if travel.FREQUENCY in freq_reverse_mapping:
                template_value = freq_reverse_mapping[travel.FREQUENCY]
                travel_data[template_field] = template_value
    
    return travel_data


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
]