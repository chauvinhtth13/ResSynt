# backends/audit_log/utils/integrity.py
"""
🌐 BASE Integrity Checker - Shared across all studies

SHA-256 checksum for audit log integrity verification
"""
import hashlib
import json
import logging
from datetime import date, datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


class IntegrityChecker:
    """
    Check integrity with SHA-256 checksums
    
    Ensures audit logs haven't been tampered with
    """
    
    @staticmethod
    def _serialize_value(value):
        """
        ✅ Convert non-JSON-serializable values to strings
        
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
        
        # Handle boolean (keep as is)
        if isinstance(value, bool):
            return value
        
        # Convert other types to string
        return str(value)
    
    @staticmethod
    def _serialize_dict(data: dict) -> dict:
        """
        ✅ Recursively serialize all values in dict
        
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
        Generate SHA-256 checksum for audit log
        
        ✅ FIXED: Serialize date/datetime objects before JSON encoding
        
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
            str: SHA-256 checksum (64 characters)
        """
        # ✅ Serialize old_data and new_data
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
        
        # Generate checksum
        canonical_string = json.dumps(canonical_data, sort_keys=True)
        hash_hex = hashlib.sha256(canonical_string.encode()).hexdigest()
        
        logger.debug(f"✅ Generated checksum: {hash_hex[:16]}...")
        
        return hash_hex
    
    @staticmethod
    def verify_integrity(audit_log) -> bool:
        """
        Verify audit log integrity
        
        ✅ FIXED: Handle date serialization during verification
        
        Args:
            audit_log: AuditLog instance
        
        Returns:
            bool: True if checksum matches, False if tampered
        """
        stored_checksum = audit_log.checksum
        
        if not stored_checksum:
            logger.warning("⚠️ No checksum stored")
            return False
        
        # Rebuild old_data and new_data from details
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
        
        # Compare
        is_valid = (calculated_checksum == stored_checksum)
        
        if not is_valid:
            logger.error(
                f"🚨 INTEGRITY VIOLATION: AuditLog {audit_log.id}\n"
                f"   Expected: {calculated_checksum[:16]}...\n"
                f"   Stored:   {stored_checksum[:16]}..."
            )
        else:
            logger.debug(f"✅ Integrity verified for AuditLog {audit_log.id}")
        
        return is_valid
