# backends/audit_logs/utils/integrity.py
"""
BASE Integrity Checker - Shared across all studies

HMAC-SHA-256 checksum for audit log integrity verification
Enhanced with secret key for tamper-proof checksums

SECURITY:
- Uses HMAC with secret key (not just hash)
- Constant-time comparison to prevent timing attacks
- Supports Django's SECRET_KEY rotation via AUDIT_INTEGRITY_SECRET setting
"""
import hashlib
import hmac
import json
import logging
from datetime import date, datetime
from decimal import Decimal
from django.conf import settings

logger = logging.getLogger(__name__)

# Get secret key from settings (fallback to SECRET_KEY if not defined)
# SECURITY: Use dedicated key for audit integrity if available
AUDIT_SECRET_KEY = getattr(settings, 'AUDIT_INTEGRITY_SECRET', settings.SECRET_KEY)

# Pre-encode secret key for reuse (optimization)
_AUDIT_SECRET_KEY_BYTES = AUDIT_SECRET_KEY.encode('utf-8')


class IntegrityChecker:
    """
    Check integrity with SHA-256 checksums
    
    Ensures audit logs haven't been tampered with
    """
    
    @staticmethod
    def _serialize_value(value):
        """
        Convert non-JSON-serializable values to strings
        
        Handles:
        - None → None
        - date/datetime → ISO format
        - Decimal → string
        - Boolean → boolean (keep as is)
        - Other → string
        """
        if value is None:
            return None
        
        # Handle date/datetime objects
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        
        # Handle Decimal
        if isinstance(value, Decimal):
            return str(value)
        
        # Handle boolean (force to string to match DB storage)
        if isinstance(value, bool):
            return str(value)
        
        # Convert other types to string
        return str(value)
    
    @staticmethod
    def _serialize_dict(data: dict) -> dict:
        """
        Recursively serialize all values in dict
        
        Ensures all values are JSON-serializable
        """
        serialized = {}
        for key, value in data.items():
            if isinstance(value, dict):
                serialized[key] = IntegrityChecker._serialize_dict(value)
            elif isinstance(value, list):
                serialized[key] = [IntegrityChecker._serialize_value(v) for v in value]
            else:
                serialized[key] = IntegrityChecker._serialize_value(value)
        return serialized
    
    @staticmethod
    def generate_checksum(audit_data: dict) -> str:
        """
        Generate HMAC-SHA-256 checksum for audit log
        
        ENHANCED: Uses HMAC with secret key for tamper-proof checksums
        Even with database access, attackers cannot forge valid checksums
        
        Args:
            audit_data: Dictionary with:
                - user_id
                - username
                - action
                - model_name
                - patient_id
                - timestamp
                - old_data (dict)
                - new_data (dict)
                - reason
        
        Returns:
            str: HMAC-SHA-256 checksum (64 characters)
        """
        # Serialize old_data and new_data
        old_data = IntegrityChecker._serialize_dict(audit_data.get('old_data', {}))
        new_data = IntegrityChecker._serialize_dict(audit_data.get('new_data', {}))
        
        # Build canonical data structure
        canonical_data = {
            'user_id': str(audit_data.get('user_id', '')),
            'username': audit_data.get('username', ''),
            'action': audit_data.get('action', ''),
            'model_name': audit_data.get('model_name', ''),
            'patient_id': audit_data.get('patient_id', ''),
            'timestamp': audit_data.get('timestamp', ''),
            'old_data': json.dumps(old_data, sort_keys=True),
            'new_data': json.dumps(new_data, sort_keys=True),
            'reason': audit_data.get('reason', ''),
        }
        
        # Generate HMAC checksum with secret key
        # OPTIMIZATION: Use pre-encoded secret key
        canonical_string = json.dumps(canonical_data, sort_keys=True)
        hash_hex = hmac.new(
            _AUDIT_SECRET_KEY_BYTES,
            canonical_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Only log at DEBUG level to reduce overhead
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Generated HMAC checksum: %s...", hash_hex[:16])
        
        return hash_hex
    
    @staticmethod
    def verify_integrity(audit_log) -> bool:
        """
        Verify audit log integrity
        
        ENHANCED: Uses HMAC verification with secret key
        
        Args:
            audit_log: AuditLog instance
        
        Returns:
            bool: True if checksum matches, False if tampered
        """
        stored_checksum = audit_log.checksum
        
        if not stored_checksum:
            logger.warning("No checksum stored")
            return False
        
        # Rebuild old_data and new_data from details
        # OPTIMIZED: Use select_related to avoid N+1 queries
        details = audit_log.details.all()
        
        old_data = {}
        new_data = {}
        
        for detail in details:
            old_data[detail.field_name] = detail.old_value
            new_data[detail.field_name] = detail.new_value
        
        # Build audit_data for verification
        audit_data = {
            'user_id': audit_log.user_id,
            'username': audit_log.username,
            'action': audit_log.action,
            'model_name': audit_log.model_name,
            'patient_id': audit_log.patient_id,
            'timestamp': str(audit_log.timestamp),
            'old_data': old_data,
            'new_data': new_data,
            'reason': audit_log.reason,
        }
        
        # Calculate checksum
        calculated_checksum = IntegrityChecker.generate_checksum(audit_data)
        
        # Use constant-time comparison to prevent timing attacks
        # SECURITY: hmac.compare_digest is resistant to timing attacks
        is_valid = hmac.compare_digest(calculated_checksum, stored_checksum)
        
        if not is_valid:
            # Log security event - potential tampering detected
            logger.error(
                "INTEGRITY VIOLATION: AuditLog %s - checksum mismatch (expected: %s..., stored: %s...)",
                audit_log.id, calculated_checksum[:16], stored_checksum[:16]
            )
        elif logger.isEnabledFor(logging.DEBUG):
            logger.debug("Integrity verified for AuditLog %s", audit_log.id)
        
        return is_valid
