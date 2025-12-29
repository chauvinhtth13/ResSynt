# backends/api/studies/study_44en/views/individual/helpers_sample.py

"""
Helper functions for Individual Sample views
Handles sample collection for 4 visit times: baseline, day_14, day_28, day_90
"""

import logging
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
    logger.info("💾 Saving sample collection data...")
    
    # Delete existing samples for this individual
    deleted_count = Individual_Sample.objects.filter(MEMBER=individual).delete()[0]
    logger.info(f"🗑️ Deleted {deleted_count} existing sample records")
    
    samples_created = 0
    
    # Process each visit time
    for form_prefix, model_time in SAMPLE_TIME_MAPPING.items():
        # Get data from POST
        collected = request.POST.get(f'sample_{form_prefix}', '').strip()
        stool_date = request.POST.get(f'stool_date_{form_prefix}', '').strip()
        throat_date = request.POST.get(f'throat_date_{form_prefix}', '').strip()
        reason = request.POST.get(f'reason_{form_prefix}', '').strip()
        
        # Only create record if user selected something
        if collected:
            sample = Individual_Sample(
                MEMBER=individual,
                SAMPLE_TIME=model_time,
                SAMPLE_COLLECTED=collected,
            )
            
            # Add stool date if provided
            if stool_date:
                sample.STOOL_DATE = stool_date
            
            # Add throat swab date if provided
            if throat_date:
                sample.THROAT_SWAB_DATE = throat_date
            
            # Add reason if provided
            if reason:
                sample.NOT_COLLECTED_REASON = reason
            
            set_audit_metadata(sample, request.user)
            sample.save()
            samples_created += 1
            
            logger.info(f"✅ Saved sample {model_time}: collected={collected}, stool={stool_date or 'N/A'}, throat={throat_date or 'N/A'}")
    
    logger.info(f"📊 Total samples created: {samples_created}/4")
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
    samples = Individual_Sample.objects.filter(MEMBER=individual)
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
        
        # Set stool date
        if sample.STOOL_DATE:
            data[f'stool_date_{form_prefix}'] = sample.STOOL_DATE.strftime('%Y-%m-%d')
        
        # Set throat swab date
        if sample.THROAT_SWAB_DATE:
            data[f'throat_date_{form_prefix}'] = sample.THROAT_SWAB_DATE.strftime('%Y-%m-%d')
        
        # Set reason
        if sample.NOT_COLLECTED_REASON:
            data[f'reason_{form_prefix}'] = sample.NOT_COLLECTED_REASON
        
        logger.info(f"📋 Loaded {form_prefix}: collected={sample.SAMPLE_COLLECTED}")
    
    return data


__all__ = [
    'set_audit_metadata',
    'make_form_readonly',
    'save_samples',
    'load_samples',
]
