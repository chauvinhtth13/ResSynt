# backends/api/studies/study_44en/views/individual/helpers_sample.py

"""
Helper functions for Individual Sample views
Handles sample collection for 4 visit times: baseline, day_14, day_28, day_90

ORGANIZATION:
1. Constants - Sample Time Mapping
2. Utility functions
3. Save functions
4. Load functions
5. NEW: Change Detection Functions for Audit Log
"""

import logging
from datetime import datetime
from backends.studies.study_44en.models.individual import Individual_Sample

logger = logging.getLogger(__name__)


# ==========================================
# CONSTANTS - Sample Time Mapping
# ==========================================

SAMPLE_TIME_MAPPING = {
    'enrollment': 'baseline',
    'day14': 'day_14',
    'day28': 'day_28',
    'day90': 'day_90',
}


# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def set_audit_metadata(instance, user):
    """Set audit fields for tracking"""
    if hasattr(instance, 'last_modified_by_id'):
        instance.last_modified_by_id = user.id
    if hasattr(instance, 'last_modified_by_username'):
        instance.last_modified_by_username = user.username


def make_form_readonly(form):
    """Make all form fields readonly"""
    for field in form.fields.values():
        field.disabled = True


def parse_date_string(date_str):
    """
    Parse date string from dd/mm/yyyy or yyyy-mm-dd format to date object.
    Returns None if parsing fails or input is empty.
    """
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    # Try dd/mm/yyyy format first (datepicker format)
    for fmt in ['%d/%m/%Y', '%Y-%m-%d']:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    logger.warning(f"Could not parse date: {date_str}")
    return None


# ==========================================
# SAVE FUNCTIONS
# ==========================================

def save_samples(request, individual):
    """
    Save sample collection data from hardcoded HTML table
    Creates/updates 4 Individual_Sample records (one per visit time)
    
    Args:
        request: HTTP request with POST data
        individual: Individual instance
    """
    logger.info(" Saving sample collection data...")
    
    # Delete existing samples for this individual
    deleted_count = Individual_Sample.objects.filter(MEMBERID=individual).delete()[0]
    logger.info(f"Deleted {deleted_count} existing sample records")
    
    samples_created = 0
    
    # Process each visit time
    for form_prefix, model_time in SAMPLE_TIME_MAPPING.items():
        # Get data from POST
        collected = request.POST.get(f'sample_{form_prefix}', '').strip()
        stool_date_str = request.POST.get(f'stool_date_{form_prefix}', '').strip()
        throat_date_str = request.POST.get(f'throat_date_{form_prefix}', '').strip()
        reason = request.POST.get(f'reason_{form_prefix}', '').strip()
        
        # Only create record if user selected something
        if collected:
            sample = Individual_Sample(
                MEMBERID=individual,
                SAMPLE_TIME=model_time,
                SAMPLE_COLLECTED=collected,
            )
            
            # Add stool date if provided (parse string to date object)
            if stool_date_str:
                stool_date = parse_date_string(stool_date_str)
                if stool_date:
                    sample.STOOL_DATE = stool_date
                else:
                    logger.warning(f"Could not parse stool date: {stool_date_str}")
            
            # Add throat swab date if provided (parse string to date object)
            if throat_date_str:
                throat_date = parse_date_string(throat_date_str)
                if throat_date:
                    sample.THROAT_SWAB_DATE = throat_date
                else:
                    logger.warning(f"Could not parse throat date: {throat_date_str}")
            
            # Add reason if provided
            if reason:
                sample.NOT_COLLECTED_REASON = reason
            
            set_audit_metadata(sample, request.user)
            sample.save()
            samples_created += 1
            
            logger.info(f"Saved sample {model_time}: collected={collected}, stool={stool_date_str or 'N/A'}, throat={throat_date_str or 'N/A'}")
    
    logger.info(f" Total samples created: {samples_created}/4")
    return samples_created


# ==========================================
# LOAD FUNCTIONS
# ==========================================

def load_samples(individual):
    """
    Load sample collection data and build dict for template
    
    Args:
        individual: Individual instance
        
    Returns:
        dict: Data for template with keys like sample_enrollment, stool_date_enrollment, etc.
    """
    logger.info("📖 Loading sample collection data...")
    
    data = {}
    
    # Query all samples for this individual
    samples = Individual_Sample.objects.filter(MEMBERID=individual)
    logger.info(f"Found {samples.count()} sample records")
    
    # Build reverse mapping: model_time -> form_prefix
    reverse_mapping = {v: k for k, v in SAMPLE_TIME_MAPPING.items()}
    
    # Process each sample record
    for sample in samples:
        form_prefix = reverse_mapping.get(sample.SAMPLE_TIME)
        if not form_prefix:
            logger.warning(f"⚠️ Unknown SAMPLE_TIME: {sample.SAMPLE_TIME}")
            continue
        
        # Set collected value (yes/no/na)
        data[f'sample_{form_prefix}'] = sample.SAMPLE_COLLECTED
        
        # Set stool date (format dd/mm/yyyy for datepicker)
        if sample.STOOL_DATE:
            data[f'stool_date_{form_prefix}'] = sample.STOOL_DATE.strftime('%d/%m/%Y')
        
        # Set throat swab date (format dd/mm/yyyy for datepicker)
        if sample.THROAT_SWAB_DATE:
            data[f'throat_date_{form_prefix}'] = sample.THROAT_SWAB_DATE.strftime('%d/%m/%Y')
        
        # Set reason
        if sample.NOT_COLLECTED_REASON:
            data[f'reason_{form_prefix}'] = sample.NOT_COLLECTED_REASON
        
        logger.info(f"📋 Loaded {form_prefix}: collected={sample.SAMPLE_COLLECTED}")
    
    return data


# ==========================================
# NEW: CHANGE DETECTION FOR AUDIT LOG
# ==========================================

def detect_sample_flat_field_changes(request, individual):
    """
    Detect changes in sample flat fields (4 visit times x 4 fields each)
    
    Compares POST data with database data for:
    - sample_{time} (radio: yes/no/na)
    - stool_date_{time} (date)
    - throat_date_{time} (date)
    - reason_{time} (text)
    
    For each of 4 visit times: enrollment, day14, day28, day90
    
    Returns:
        list: List of change dicts [{field, old_value, new_value, old_display, new_display}]
    """
    changes = []
    
    # Load old data from database
    old_sample_data = load_samples(individual)
    
    logger.info("=" * 60)
    logger.info("🔍 DEBUG: Detecting sample changes...")
    logger.info(f"   old_sample_data = {old_sample_data}")
    logger.info("=" * 60)
    
    # Process each visit time
    for form_prefix in SAMPLE_TIME_MAPPING.keys():
        # ==========================================
        # 1. sample_{time} radio (yes/no/na)
        # ==========================================
        field_name = f'sample_{form_prefix}'
        old_val = str(old_sample_data.get(field_name, '') or '').strip().lower()
        
        if field_name in request.POST:
            new_val = request.POST.get(field_name, '').strip().lower()
        else:
            new_val = old_val
        
        logger.info(f"🔍 {field_name}: old='{old_val}', new='{new_val}', in_POST={field_name in request.POST}")
        
        if old_val != new_val:
            changes.append({
                'field': field_name,
                'old_value': old_val or '(trống)',
                'new_value': new_val or '(trống)',
                'old_display': old_val or '(trống)',
                'new_display': new_val or '(trống)',
            })
        
        # ==========================================
        # 2. stool_date_{time} (date)
        # ==========================================
        date_field = f'stool_date_{form_prefix}'
        old_date = old_sample_data.get(date_field, '')
        
        if date_field in request.POST:
            new_date = request.POST.get(date_field, '').strip()
        else:
            new_date = old_date
        
        if str(old_date or '').strip() != str(new_date or '').strip():
            changes.append({
                'field': date_field,
                'old_value': old_date or '(trống)',
                'new_value': new_date or '(trống)',
                'old_display': old_date or '(trống)',
                'new_display': new_date or '(trống)',
            })
        
        # ==========================================
        # 3. throat_date_{time} (date)
        # ==========================================
        throat_field = f'throat_date_{form_prefix}'
        old_throat = old_sample_data.get(throat_field, '')
        
        if throat_field in request.POST:
            new_throat = request.POST.get(throat_field, '').strip()
        else:
            new_throat = old_throat
        
        if str(old_throat or '').strip() != str(new_throat or '').strip():
            changes.append({
                'field': throat_field,
                'old_value': old_throat or '(trống)',
                'new_value': new_throat or '(trống)',
                'old_display': old_throat or '(trống)',
                'new_display': new_throat or '(trống)',
            })
        
        # ==========================================
        # 4. reason_{time} (text)
        # ==========================================
        reason_field = f'reason_{form_prefix}'
        old_reason = old_sample_data.get(reason_field, '')
        
        if reason_field in request.POST:
            new_reason = request.POST.get(reason_field, '').strip()
        else:
            new_reason = old_reason
        
        if str(old_reason or '').strip() != str(new_reason or '').strip():
            changes.append({
                'field': reason_field,
                'old_value': old_reason or '(trống)',
                'new_value': new_reason or '(trống)',
                'old_display': old_reason or '(trống)',
                'new_display': new_reason or '(trống)',
            })
    
    logger.info(f"🔍 detect_sample_flat_field_changes: Found {len(changes)} changes")
    return changes


def detect_food_frequency_form_changes(old_data, new_data):
    """
    Detect changes in FoodFrequency form fields
    
    Args:
        old_data: Dict of old values from detector.extract_old_data()
        new_data: Dict of new values from detector.extract_new_data()
    
    Returns:
        list: List of change dicts
    """
    changes = []
    
    # Get all fields from both old and new data
    all_fields = set(old_data.keys()) | set(new_data.keys())
    
    for field in all_fields:
        old_val = old_data.get(field)
        new_val = new_data.get(field)
        
        # Normalize for comparison
        old_norm = str(old_val or '').strip().lower() if old_val is not None else ''
        new_norm = str(new_val or '').strip().lower() if new_val is not None else ''
        
        if old_norm != new_norm:
            changes.append({
                'field': field,
                'old_value': old_val if old_val is not None else '(trống)',
                'new_value': new_val if new_val is not None else '(trống)',
                'old_display': str(old_val) if old_val is not None else '(trống)',
                'new_display': str(new_val) if new_val is not None else '(trống)',
            })
    
    logger.info(f"🔍 detect_food_frequency_form_changes: Found {len(changes)} changes")
    return changes


# ==========================================
# EXPORTS
# ==========================================

__all__ = [
    'set_audit_metadata',
    'make_form_readonly',
    'parse_date_string',
    'save_samples',
    'load_samples',
    # NEW: Change detection for audit log
    'detect_sample_flat_field_changes',
    'detect_food_frequency_form_changes',
]
