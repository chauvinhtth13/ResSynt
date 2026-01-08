# backends/audit_log/utils/detector.py
"""
🌐 BASE Change Detection - Shared across all studies

FIXED Change detection - Exclude metadata fields but KEEP date fields
"""
import logging
from typing import Dict, List, Any
from django.forms.models import model_to_dict
from .helpers import normalize_value, format_value_for_display

logger = logging.getLogger(__name__)


class ChangeDetector:
    """Detect changes between old and new data"""
    
    def __init__(self):
        # ✅ FIX: ONLY exclude metadata fields, NOT date fields
        self.excluded_fields = [
            # Primary keys
            'id', 
            
            # History tracking (django-simple-history)
            'history', 
            
            # System metadata (entered by who/when)
            'ENTRY', 
            'ENTEREDTIME',
            
            # Version control
            'version', 
            
            # ✅ CRITICAL: Exclude audit metadata fields
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
            
            # ✅ REMOVED: Count fields no longer used (replaced by formsets)
            'REHOSPCOUNT',
            'ANTIBIOCOUNT',
            
            # ✅ Header fields (auto-populated from enrollment, read-only)
            'EVENT',
            'STUDYID',
            'SITEID',
            'SUBJID',
            
            # ✅ Formset technical fields (not user-editable)
            'DELETE',      # Checkbox for deletion (False = not deleted)
            'SEQUENCE',    # Read-only sequence number
            
        ]
        
    
    def detect_changes(self, old_data: Dict, new_data: Dict) -> List[Dict]:
        """
        Detect changes
        
        ✅ FIX: Only compare fields present in new_data (form fields)
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
        
        # ✅ FIX: If new_data is empty (DummyForm), no changes to detect
        if not new_data:
            logger.debug("⚠️ new_data is empty (DummyForm) - no main changes to detect")
            return changes
        
        # ✅ CRITICAL: Only check fields that are in new_data (submitted via form)
        # Don't check old_data fields that weren't in the form
        for field in new_data.keys():
            # ✅ FIX: Skip excluded fields
            if field in self.excluded_fields:
                logger.debug(f"⏭️ Skipping metadata field: {field}")
                continue
            
            old_value = old_data.get(field)
            new_value = new_data.get(field)
            
            # Normalize for comparison
            old_norm = normalize_value(old_value)
            new_norm = normalize_value(new_value)
            
            logger.info(f"🔍 Comparing {field}: old='{old_value}' (norm: '{old_norm}') vs new='{new_value}' (norm: '{new_norm}')")
            
            if old_norm != new_norm:
                change = {
                    'field': field,
                    'old_value': old_value,
                    'new_value': new_value,
                    'old_display': format_value_for_display(old_value),
                    'new_display': format_value_for_display(new_value),
                }
                changes.append(change)
                
                logger.info(
                    f"✅ Change detected: {field} "
                    f"'{change['old_display']}' → '{change['new_display']}'"
                )
        
        logger.info(f"📝 Total changes detected: {len(changes)} (only form fields)")
        return changes
    
    def extract_old_data(self, instance) -> Dict:
        """Extract old data from model instance"""
        # ✅ FIX: Don't exclude date fields
        excluded = list(self.excluded_fields)
        
        data = model_to_dict(instance, exclude=excluded)
        
        logger.debug(f"📦 Extracted old data: {len(data)} fields")
        if 'SCREENINGFORMDATE' in data:
            logger.debug(f"   SCREENINGFORMDATE: {data['SCREENINGFORMDATE']}") 
        return data
    
    def extract_new_data(self, form) -> Dict:
        """
        Extract new data from form
        
        ✅ FIX: Only extract fields that are DEFINED IN THE FORM
        This prevents detecting changes for read-only/hidden fields
        that appear in cleaned_data but weren't actually in the form
        """
        if not form.is_valid():
            logger.warning("⚠️ Form not valid - cannot extract new data")
            return {}
        
        # ✅ Only get fields that are in the form definition
        new_data = {}
        for field_name in form.fields.keys():
            if field_name in form.cleaned_data:
                new_data[field_name] = form.cleaned_data[field_name]
        
        # Remove excluded fields
        for field in self.excluded_fields:
            new_data.pop(field, None)
        
        logger.debug(f"📦 Extracted new data: {len(new_data)} fields (only form fields)")
        if 'SCREENINGFORMDATE' in new_data:
            logger.debug(f"   SCREENINGFORMDATE: {new_data['SCREENINGFORMDATE']}")
        return new_data
