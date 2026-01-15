# backends/audit_logs/utils/detector.py
"""
BASE Change Detection - Shared across all studies

FIXED Change detection - Exclude metadata fields but KEEP date fields
"""
import logging
from typing import Dict, List, Any
from django.forms.models import model_to_dict
from .helpers import normalize_value, format_value_for_display

logger = logging.getLogger(__name__)

# ==========================================
# SHARED CONSTANTS - Use in both detector and processors
# ==========================================
EXCLUDED_METADATA_FIELDS = [
    # Primary keys
    'id', 
    
    # History tracking (django-simple-history)
    'history', 
    
    # System metadata (entered by who/when)
    'ENTRY', 
    'ENTEREDTIME',
    
    # Version control
    'version', 
    
    # CRITICAL: Exclude audit metadata fields
    'last_modified_by',
    'last_modified_by_id',
    'last_modified_by_username',
    'last_modified_at',
    'created_by',
    'created_by_id',
    'created_at',
    'updated_at',
    
    # Status flags
    'CONFIRMED', 
    'is_confirmed', 
    
    # Auto-generated IDs
    'USUBJID',
    
    # Count fields (replaced by formsets)
    'REHOSPCOUNT',
    'ANTIBIOCOUNT',
    
    # Header fields (auto-populated from enrollment, read-only)
    'EVENT',
    'STUDYID',
    'SITEID',
    'SUBJID',
    
    # Formset technical fields (not user-editable)
    'DELETE',
    'SEQUENCE',
]


# Use frozenset for O(1) lookup instead of list
EXCLUDED_METADATA_FIELDS_SET = frozenset(EXCLUDED_METADATA_FIELDS)


class ChangeDetector:
    """Detect changes between old and new data"""
    
    # Class-level cache for excluded fields (faster lookup)
    _excluded_fields = EXCLUDED_METADATA_FIELDS_SET
    
    def __init__(self):
        # Use class-level frozenset for O(1) lookup
        self.excluded_fields = self._excluded_fields
        
    
    def detect_changes(self, old_data: Dict, new_data: Dict) -> List[Dict]:
        """
        Detect changes
        
        FIX: Only compare fields present in new_data (form fields)
        This prevents detecting "deletions" for fields not in the form
        
        Returns:
            List of changes: [
                {
                    'field': str,          # Technical field name
                    'old_value': Any,
                    'new_value': Any,
                    'old_display': str,    # For display
                    'new_display': str
                }
            ]
        """
        changes = []
        
        # If new_data is empty (DummyForm), no changes to detect
        if not new_data:
            logger.debug("new_data is empty - no changes to detect")
            return changes
        
        # CRITICAL: Only check fields that are in new_data (submitted via form)
        # Don't check old_data fields that weren't in the form
        for field in new_data.keys():
            # Skip excluded fields (O(1) lookup with frozenset)
            if field in self.excluded_fields:
                continue
            
            old_value = old_data.get(field)
            new_value = new_data.get(field)
            
            # Normalize for comparison
            old_norm = normalize_value(old_value)
            new_norm = normalize_value(new_value)
            
            if old_norm != new_norm:
                change = {
                    'field': field,
                    'old_value': old_value,
                    'new_value': new_value,
                    'old_display': format_value_for_display(old_value),
                    'new_display': format_value_for_display(new_value),
                }
                changes.append(change)
                
                # Reduced logging - only log individual changes at TRACE level
                if logger.isEnabledFor(5):  # TRACE level
                    logger.log(
                        5,
                        "Change detected: %s '%s' → '%s'",
                        field, change['old_display'], change['new_display']
                    )
        
        # Only log summary at TRACE level to reduce overhead
        if logger.isEnabledFor(5) and len(changes) > 0:
            logger.log(5, "Total changes detected: %d", len(changes))
        return changes
    
    def extract_old_data(self, instance) -> Dict:
        """Extract old data from model instance"""
        data = model_to_dict(instance, exclude=list(self.excluded_fields))
        # Reduced logging - only log at TRACE level or when explicitly debugging
        if logger.isEnabledFor(5):  # TRACE level (below DEBUG)
            logger.log(5, "Extracted old data: %d fields", len(data))
        return data
    
    def extract_new_data(self, form) -> Dict:
        """
        Extract new data from form
        
        Only extract fields that are DEFINED IN THE FORM
        This prevents detecting changes for read-only/hidden fields
        that appear in cleaned_data but weren't actually in the form
        """
        if not form.is_valid():
            logger.warning("Form not valid - cannot extract new data")
            return {}
        
        # Only get fields that are in the form definition
        # Use dict comprehension for efficiency
        new_data = {
            field_name: form.cleaned_data[field_name]
            for field_name in form.fields.keys()
            if field_name in form.cleaned_data and field_name not in self.excluded_fields
        }
        
        # Reduced logging - only log at TRACE level to avoid 81+ log entries per request
        if logger.isEnabledFor(5):  # TRACE level (below DEBUG)
            logger.log(5, "Extracted new data: %d fields", len(new_data))
        return new_data
