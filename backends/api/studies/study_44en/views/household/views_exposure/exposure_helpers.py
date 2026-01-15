# backends/studies/study_44en/views/household/exposure_helpers.py
"""
Helper utilities for household exposure:
- Save/load water sources, treatment, animals
- Change detection for flat fields
- Display label extraction from model choices

Uses model choices instead of hard-coded labels
"""
import logging
from backends.studies.study_44en.models.household import (
    HH_WaterSource, HH_WaterTreatment, HH_Animal,
    HH_FoodFrequency, HH_FoodSource
)
from backends.api.studies.study_44en.views.household.helpers import set_audit_metadata

logger = logging.getLogger(__name__)


# ==========================================
# SAVE FUNCTIONS (Business Logic)
# ==========================================

def save_water_sources(request, exposure):
    """Parse and save water sources from POST data"""
    HH_WaterSource.objects.filter(HHID=exposure).delete()
    source_types = {
        'tap': HH_WaterSource.SourceTypeChoices.TAP,
        'bottle': HH_WaterSource.SourceTypeChoices.BOTTLED,
        'well': HH_WaterSource.SourceTypeChoices.WELL,
        'rain': HH_WaterSource.SourceTypeChoices.RAIN,
        'river': HH_WaterSource.SourceTypeChoices.RIVER,
        'pond': HH_WaterSource.SourceTypeChoices.POND,
        'other': HH_WaterSource.SourceTypeChoices.OTHER,
    }
    count = 0
    for source_key, source_type in source_types.items():
        drink = request.POST.get(f'water_{source_key}_drink') == 'on'
        use = request.POST.get(f'water_{source_key}_use') == 'on'
        irrigate = request.POST.get(f'water_{source_key}_irrigate') == 'on'
        other_purpose = request.POST.get(f'water_{source_key}_other', '').strip()
        logger.info(f"[save_water_sources] POST: {source_key}: drink={drink}, use={use}, irrigate={irrigate}, other='{other_purpose}'")
        if drink or use or irrigate or other_purpose:
            # Get other source name if applicable
            other_name = None
            if source_key == 'other':
                other_name = request.POST.get('water_other_src_name', '').strip()
                logger.info(f"[save_water_sources] water_other_src_name='{other_name}'")
            
            from backends.api.studies.study_44en.views.household.helpers import set_audit_metadata
            ws = HH_WaterSource(
                HHID=exposure,
                SOURCE_TYPE=source_type,
                SOURCE_TYPE_OTHER=other_name,
                DRINKING=drink,
                LIVING=use,
                IRRIGATION=irrigate,
                OTHER=bool(other_purpose),
                OTHER_PURPOSE=other_purpose if other_purpose else None
            )
            set_audit_metadata(ws, request.user)
            ws.save()
            logger.info(f"[save_water_sources] Saved: {ws.SOURCE_TYPE} name='{ws.SOURCE_TYPE_OTHER}' drink={ws.DRINKING} use={ws.LIVING} irrigate={ws.IRRIGATION} other='{ws.OTHER_PURPOSE}'")
            count += 1
    logger.info(f"Saved {count} water sources")
    return count


def save_water_treatment(request, exposure):
    """Parse and save water treatment from POST data"""
    logger.info(f"💧 Saving water treatment for {exposure.HHID.HHID}")
    
    HH_WaterTreatment.objects.filter(HHID=exposure).delete()
    logger.info("🗑️ Deleted old water treatment records")
    
    treatment_method = request.POST.get('TREATMENT_METHOD', '').strip()
    logger.info(f" TREATMENT_METHOD from POST: '{treatment_method}'")
    
    if treatment_method:
        treatment_other = request.POST.get('TREATMENT_METHOD_OTHER', '').strip()
        logger.info(f" TREATMENT_METHOD_OTHER from POST: '{treatment_other}'")
        
        wt = HH_WaterTreatment(
            HHID=exposure,
            TREATMENT_TYPE=treatment_method,
            TREATMENT_TYPE_OTHER=treatment_other if treatment_other else None
        )
        set_audit_metadata(wt, request.user)
        wt.save()
        logger.info(f"Saved water treatment: {treatment_method}")
        return True
    else:
        logger.warning("⚠️ No TREATMENT_METHOD found in POST data")
    
    return False


def save_animals(request, exposure):
    """Parse and save animals from POST data"""
    logger.info(f"🐾 Saving animals for {exposure.HHID.HHID}")
    
    HH_Animal.objects.filter(HHID=exposure).delete()
    logger.info("🗑️ Deleted old animal records")
    
    animal_types = {
        'dog': HH_Animal.AnimalTypeChoices.DOG,
        'cat': HH_Animal.AnimalTypeChoices.CAT,
        'bird': HH_Animal.AnimalTypeChoices.BIRD,
        'poultry': HH_Animal.AnimalTypeChoices.POULTRY,
        'cow': HH_Animal.AnimalTypeChoices.COW,
        'other': HH_Animal.AnimalTypeChoices.OTHER,
    }
    
    count = 0
    for animal_key, animal_type in animal_types.items():
        field_name = f'animal_{animal_key}'
        field_value = request.POST.get(field_name)
        logger.info(f" Checking {field_name}: '{field_value}'")
        
        if field_value == 'on':
            other_text = None
            if animal_key == 'other':
                other_text = request.POST.get('animal_other_text', '').strip()
                logger.info(f" animal_other_text: '{other_text}'")
            
            animal = HH_Animal(
                HHID=exposure,
                ANIMAL_TYPE=animal_type,
                ANIMAL_TYPE_OTHER=other_text if other_text else None
            )
            set_audit_metadata(animal, request.user)
            animal.save()
            count += 1
            logger.info(f"Saved animal: {animal_type}")
    
    logger.info(f"Saved {count} animals in total")
    return count


# ==========================================
# LOAD FUNCTIONS (Data Retrieval)
# ==========================================

def load_water_data(exposure):
    """Load water sources data for template"""
    water_data = {}
    water_sources = HH_WaterSource.objects.filter(HHID=exposure)
    logger.info(f"[load_water_data] Found {water_sources.count()} water sources in DB for HHID={exposure}")
    for ws in water_sources:
        source_key = ws.SOURCE_TYPE
        if source_key == 'bottled':
            source_key = 'bottle'
        logger.info(f"[load_water_data] DB: {source_key}: drink={ws.DRINKING}, use={ws.LIVING}, irrigate={ws.IRRIGATION}, other='{ws.OTHER_PURPOSE}'")
        water_data[f'water_{source_key}_drink'] = ws.DRINKING
        water_data[f'water_{source_key}_use'] = ws.LIVING
        water_data[f'water_{source_key}_irrigate'] = ws.IRRIGATION
        water_data[f'water_{source_key}_other'] = ws.OTHER_PURPOSE or ''
        
        # Load other source name if applicable
        if source_key == 'other' and ws.SOURCE_TYPE_OTHER:
            water_data['water_other_src_name'] = ws.SOURCE_TYPE_OTHER
            logger.info(f"[load_water_data] Loaded water_other_src_name='{ws.SOURCE_TYPE_OTHER}'")
    return water_data


def load_treatment_data(exposure):
    """Load water treatment data for template"""
    treatment = HH_WaterTreatment.objects.filter(HHID=exposure).first()
    logger.info(f"💧 Loading water treatment for {exposure.HHID}")
    if treatment:
        logger.info(f" Found treatment: {treatment.TREATMENT_TYPE}, other: {treatment.TREATMENT_TYPE_OTHER}")
        return {
            'method': treatment.TREATMENT_TYPE,
            'other': treatment.TREATMENT_TYPE_OTHER or ''
        }
    logger.warning(f"⚠️ No treatment found for {exposure.HHID}")
    return {'method': None, 'other': None}


def load_animal_data(exposure):
    """Load animals data for template"""
    animal_data = {}
    
    animals = HH_Animal.objects.filter(HHID=exposure)
    logger.info(f"🐾 Loading animals for {exposure.HHID}")
    logger.info(f" Found {animals.count()} animal records")
    
    for animal in animals:
        animal_type = animal.ANIMAL_TYPE
        animal_data[animal_type] = True
        logger.info(f" Loaded animal: {animal_type}")
        if animal_type == 'other' and animal.ANIMAL_TYPE_OTHER:
            animal_data['other_text'] = animal.ANIMAL_TYPE_OTHER
            logger.info(f" Other animal text: {animal.ANIMAL_TYPE_OTHER}")
    
    logger.info(f"Loaded animal data: {animal_data}")
    return animal_data


# ==========================================
# CHANGE DETECTION (Flat Fields)
# ==========================================

def detect_flat_field_changes(request, exposure):
    """
    Detect changes in water sources, treatment, animals, and food
    
    Uses model choices for display labels (DRY principle)
    
    Returns:
        list: List of change dictionaries
    """
    changes = []
    
    # ===== 1. Water Sources =====
    old_water_sources = HH_WaterSource.objects.filter(HHID=exposure)
    old_water_dict = {}
    old_other_src_name = ''
    for ws in old_water_sources:
        source_key = 'bottle' if ws.SOURCE_TYPE == 'bottled' else ws.SOURCE_TYPE
        old_water_dict[source_key] = {
            'drink': ws.DRINKING,
            'use': ws.LIVING,
            'irrigate': ws.IRRIGATION,
            'other': ws.OTHER_PURPOSE or '',
        }
        # Save other source name
        if source_key == 'other' and ws.SOURCE_TYPE_OTHER:
            old_other_src_name = ws.SOURCE_TYPE_OTHER
    
    source_types = ['tap', 'bottle', 'well', 'rain', 'river', 'pond', 'other']
    for source_key in source_types:
        # Get new values from POST
        new_drink = request.POST.get(f'water_{source_key}_drink') == 'on'
        new_use = request.POST.get(f'water_{source_key}_use') == 'on'
        new_irrigate = request.POST.get(f'water_{source_key}_irrigate') == 'on'
        new_other = request.POST.get(f'water_{source_key}_other', '').strip()
        
        # Get old values (default to False/empty)
        old_data = old_water_dict.get(source_key, {
            'drink': False, 'use': False, 'irrigate': False, 'other': ''
        })
        
        # Use model choices for source type display
        db_source_key = 'bottled' if source_key == 'bottle' else source_key
        source_display = get_water_source_display(db_source_key)
        
        # Check each purpose
        for field_key, field_label in WATER_SOURCE_LABELS.items():
            if field_key == 'other':
                # Text field comparison
                if old_data['other'] != new_other:
                    changes.append({
                        'field': f'water_{source_key}_other',
                        'field_label': f'{source_display} - {field_label}',
                        'old_value': old_data['other'],
                        'new_value': new_other,
                        'old_display': old_data['other'] or '(Trống)',
                        'new_display': new_other or '(Trống)',
                    })
            else:
                # Boolean field comparison
                new_val = locals()[f'new_{field_key}']  # new_drink, new_use, new_irrigate
                if old_data[field_key] != new_val:
                    changes.append({
                        'field': f'water_{source_key}_{field_key}',
                        'field_label': f'{source_display} - {field_label}',
                        'old_value': 'Yes' if old_data[field_key] else 'No',
                        'new_value': 'Yes' if new_val else 'No',
                        'old_display': 'Có' if old_data[field_key] else 'Không',
                        'new_display': 'Có' if new_val else 'Không',
                    })
    
    # Check water source "Other" name change
    new_other_src_name = request.POST.get('water_other_src_name', '').strip()
    if old_other_src_name != new_other_src_name:
        changes.append({
            'field': 'water_other_src_name',
            'field_label': 'Nguồn nước khác - Tên nguồn',
            'old_value': old_other_src_name,
            'new_value': new_other_src_name,
            'old_display': old_other_src_name or '(Trống)',
            'new_display': new_other_src_name or '(Trống)',
        })
    
    # ===== 2. Water Treatment =====
    old_treatment = HH_WaterTreatment.objects.filter(HHID=exposure).first()
    old_treatment_method = old_treatment.TREATMENT_TYPE if old_treatment else ''
    old_treatment_other = old_treatment.TREATMENT_TYPE_OTHER if old_treatment else ''
    
    new_treatment_method = request.POST.get('TREATMENT_METHOD', '').strip()
    new_treatment_other = request.POST.get('TREATMENT_METHOD_OTHER', '').strip()
    
    # Check treatment method change
    if old_treatment_method != new_treatment_method:
        changes.append({
            'field': 'TREATMENT_METHOD',
            'field_label': 'Phương pháp xử lý nước',
            'old_value': old_treatment_method or 'None',
            'new_value': new_treatment_method or 'None',
            # Use model choices for display
            'old_display': get_treatment_display(old_treatment_method),
            'new_display': get_treatment_display(new_treatment_method),
        })
    
    # Check treatment other specification
    if old_treatment_other != new_treatment_other:
        changes.append({
            'field': 'TREATMENT_METHOD_OTHER',
            'field_label': 'Phương pháp xử lý nước - Khác',
            'old_value': old_treatment_other or '',
            'new_value': new_treatment_other or '',
            'old_display': old_treatment_other or '(Trống)',
            'new_display': new_treatment_other or '(Trống)',
        })
    
    # ===== 3. Animals =====
    old_animals = HH_Animal.objects.filter(HHID=exposure)
    old_animal_dict = {animal.ANIMAL_TYPE: animal for animal in old_animals}
    
    animal_types = ['dog', 'cat', 'bird', 'poultry', 'cow', 'other']
    for animal_key in animal_types:
        new_has_animal = request.POST.get(f'animal_{animal_key}') == 'on'
        old_has_animal = animal_key in old_animal_dict
        
        # Check animal presence change
        if old_has_animal != new_has_animal:
            # Use model choices for display
            animal_display = get_animal_display(animal_key)
            changes.append({
                'field': f'animal_{animal_key}',
                'field_label': f'Nuôi {animal_display}',
                'old_value': 'Yes' if old_has_animal else 'No',
                'new_value': 'Yes' if new_has_animal else 'No',
                'old_display': 'Có' if old_has_animal else 'Không',
                'new_display': 'Có' if new_has_animal else 'Không',
            })
    
    # Check other animal specification
    old_animal_other = old_animal_dict.get('other')
    old_animal_other_text = old_animal_other.ANIMAL_TYPE_OTHER if old_animal_other else ''
    new_animal_other_text = request.POST.get('animal_other_text', '').strip()
    
    if old_animal_other_text != new_animal_other_text:
        changes.append({
            'field': 'animal_other_text',
            'field_label': 'Động vật khác - Ghi rõ',
            'old_value': old_animal_other_text,
            'new_value': new_animal_other_text,
            'old_display': old_animal_other_text or '(Trống)',
            'new_display': new_animal_other_text or '(Trống)',
        })
    
    # ===== 4. Food Frequency =====
    try:
        old_food_freq = HH_FoodFrequency.objects.get(HHID=exposure.HHID)
    except HH_FoodFrequency.DoesNotExist:
        old_food_freq = None
    
    for field_name, field_label in FOOD_FREQ_FIELDS.items():
        old_value = getattr(old_food_freq, field_name, None) if old_food_freq else None
        new_value = request.POST.get(field_name, '').strip() or None
        
        if old_value != new_value:
            changes.append({
                'field': field_name,
                'field_label': f'Tần suất tiêu thụ - {field_label}',
                'old_value': old_value or 'None',
                'new_value': new_value or 'None',
                # Use model choices for display
                'old_display': get_frequency_display(old_value),
                'new_display': get_frequency_display(new_value),
            })
    
    # ===== 5. Food Source =====
    try:
        old_food_source = HH_FoodSource.objects.get(HHID=exposure.HHID)
    except HH_FoodSource.DoesNotExist:
        old_food_source = None
    
    for field_name, field_label in FOOD_SOURCE_FIELDS.items():
        old_value = getattr(old_food_source, field_name, None) if old_food_source else None
        new_value = request.POST.get(field_name, '').strip() or None
        
        if old_value != new_value:
            changes.append({
                'field': field_name,
                'field_label': f'Nguồn gốc thực phẩm - {field_label}',
                'old_value': old_value or 'None',
                'new_value': new_value or 'None',
                # Use model choices for display
                'old_display': get_frequency_display(old_value),
                'new_display': get_frequency_display(new_value),
            })
    
    # Food source OTHER_SPECIFY
    old_other_specify = old_food_source.OTHER_SPECIFY if old_food_source else ''
    new_other_specify = request.POST.get('OTHER_SPECIFY', '').strip()
    # Only detect if at least one is not empty and values differ
    if (old_other_specify or new_other_specify) and old_other_specify != new_other_specify:
        changes.append({
            'field': 'OTHER_SPECIFY',
            'field_label': 'Nguồn gốc thực phẩm - Nguồn khác (ghi rõ)',
            'old_value': old_other_specify,
            'new_value': new_other_specify,
            'old_display': old_other_specify or '(Trống)',
            'new_display': new_other_specify or '(Trống)',
        })
    logger.info(f"🔍 Detected {len(changes)} flat field changes")
    return changes


# ==========================================
# DISPLAY LABEL FUNCTIONS
# ==========================================


def get_choice_display(model_class, field_name, value):
    """
    Get display label for a choice field value
    
    Args:
        model_class: Model class (e.g., HH_WaterTreatment)
        field_name: Field name (e.g., 'TREATMENT_TYPE')
        value: Field value (e.g., 'boiling')
    
    Returns:
        str: Display label (e.g., 'Đun sôi') or value if not found
    """
    if not value:
        return '(Chưa chọn)'
    
    try:
        # Get field's choices
        field = model_class._meta.get_field(field_name)
        if hasattr(field, 'choices') and field.choices:
            # Find matching choice
            for choice_value, choice_label in field.choices:
                if choice_value == value:
                    return str(choice_label)
        return value
    except Exception as e:
        logger.warning(f"Could not get display for {model_class.__name__}.{field_name}={value}: {e}")
        return value


def get_water_source_display(source_type):
    """Get display label for water source type"""
    return get_choice_display(HH_WaterSource, 'SOURCE_TYPE', source_type)


def get_treatment_display(treatment_type):
    """Get display label for treatment type"""
    return get_choice_display(HH_WaterTreatment, 'TREATMENT_TYPE', treatment_type)


def get_animal_display(animal_type):
    """Get display label for animal type"""
    return get_choice_display(HH_Animal, 'ANIMAL_TYPE', animal_type)


def get_frequency_display(frequency):
    """Get display label for food frequency"""
    return get_choice_display(HH_FoodFrequency, 'RICE_NOODLES', frequency)


# ==========================================
# Field Label Mapping (for change detection)
# ==========================================

# Water source field labels
WATER_SOURCE_LABELS = {
    'drink': 'Uống/Ăn',
    'use': 'Sinh hoạt',
    'irrigate': 'Tưới tiêu',
    'other': 'Mục đích khác'
}

# Food frequency fields
FOOD_FREQ_FIELDS = {
    'RICE_NOODLES': 'Cơm/Mì',
    'RED_MEAT': 'Thịt đỏ',
    'POULTRY': 'Gia cầm',
    'FISH_SEAFOOD': 'Cá/Hải sản',
    'EGGS': 'Trứng',
    'RAW_VEGETABLES': 'Rau sống',
    'COOKED_VEGETABLES': 'Rau nấu chín',
    'DAIRY': 'Sữa/Phô mai',
    'FERMENTED': 'Thực phẩm lên men',
    'BEER': 'Bia',
    'ALCOHOL': 'Rượu',
}

# Food source fields
FOOD_SOURCE_FIELDS = {
    'TRADITIONAL_MARKET': 'Chợ truyền thống',
    'SUPERMARKET': 'Siêu thị',
    'CONVENIENCE_STORE': 'Cửa hàng tiện lợi',
    'RESTAURANT': 'Nhà hàng',
    'ONLINE': 'Mua online',
    'SELF_GROWN': 'Tự trồng',
    'GIFTED': 'Được tặng',
    'OTHER': 'Nguồn khác',
}
