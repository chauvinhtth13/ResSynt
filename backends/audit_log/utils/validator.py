# backends/audit_log/utils/validator.py
"""
🌐 BASE Reason Validator - Shared across all studies

Enhanced reason validator with security sanitization
"""
import logging
from typing import Dict, List
from .sanitizer import SecuritySanitizer

logger = logging.getLogger(__name__)


class ReasonValidator:
    """Enhanced validator with security sanitization"""
    
    def __init__(self, min_length: int = 3):
        """
        Args:
            min_length: Minimum character length (default 3)
        """
        self.min_length = min_length
        self.sanitizer = SecuritySanitizer(min_length=min_length)  # ✅ Pass min_length
    
    def validate_reason(self, reason: str, field_name: str = '') -> Dict:
        """
        Validate single reason with sanitization
        
        Returns:
            {
                'valid': bool,
                'message': str,
                'sanitized': str,
                'warnings': List[str]
            }
        """
        # ✅ Sanitize first
        result = self.sanitizer.sanitize(reason, field_name)
        
        if not result['valid']:
            return {
                'valid': False,
                'message': '; '.join(result['errors']),
                'sanitized': result['sanitized'],
                'warnings': result['warnings']
            }
        
        return {
            'valid': True,
            'message': 'Hợp lệ',
            'sanitized': result['sanitized'],
            'warnings': result['warnings']
        }
    
    def validate_reasons(self, reasons: Dict[str, str], 
                        required_fields: List[str]) -> Dict:
        """
        Validate multiple reasons with sanitization
        
        Returns:
            {
                'valid': bool,
                'errors': Dict[str, List[str]],
                'missing': List[str],
                'sanitized_reasons': Dict[str, str],
                'warnings': List[str]
            }
        """
        # ✅ Sanitize all at once
        sanitize_result = self.sanitizer.sanitize_dict(reasons)
        
        if not sanitize_result['valid']:
            return {
                'valid': False,
                'errors': sanitize_result['errors'],
                'missing': [],
                'sanitized_reasons': sanitize_result['sanitized'],
                'warnings': sanitize_result['warnings']
            }
        
        # Check missing fields
        missing = []
        for field in required_fields:
            if field not in sanitize_result['sanitized'] or \
               not sanitize_result['sanitized'][field]:
                missing.append(field)
        
        is_valid = len(missing) == 0
        
        logger.info(
            f"✅ Validated {len(required_fields)} reasons: "
            f"valid={is_valid}, missing={len(missing)}, "
            f"warnings={len(sanitize_result['warnings'])}"
        )
        
        return {
            'valid': is_valid,
            'errors': {},
            'missing': missing,
            'sanitized_reasons': sanitize_result['sanitized'],
            'warnings': sanitize_result['warnings']
        }
    
    def build_change_reason_text(self, changes: List[Dict], 
                                 reasons: Dict[str, str]) -> str:
        """
        Build combined reason text
        
        Format: field1: reason1 | field2: reason2
        """
        parts = []
        for change in changes:
            field = change['field']
            reason = reasons.get(field, '').strip()
            
            if reason:
                parts.append(f"{field}: {reason}")
        
        return ' | '.join(parts)
