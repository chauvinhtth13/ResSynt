# backends/audit_logs/utils/helpers.py
"""
BASE Common Helper Functions - Shared across all studies

PERFORMANCE: Pre-compiled regex patterns
"""
import logging
import re
from typing import Any
from datetime import date, datetime

logger = logging.getLogger(__name__)

# Pre-compile date pattern for better performance
_DATE_PATTERN = re.compile(r'^\d{1,2}/\d{1,2}/\d{4}$')


def get_client_ip(request) -> str:
    """
    Get client IP address from request
    
    Handles X-Forwarded-For header (for proxies/load balancers)
    
    SECURITY: Validates IP format to prevent injection attacks
    """
    import ipaddress
    
    def validate_ip(ip_str: str) -> str:
        """Validate and sanitize IP address"""
        if not ip_str or ip_str == 'unknown':
            return 'unknown'
        
        # Remove whitespace
        ip_str = ip_str.strip()
        
        # Validate IPv4 or IPv6 format
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            return str(ip_obj)
        except ValueError:
            # Invalid IP format - log and return sanitized version
            logger.warning(f"Invalid IP format detected: {ip_str[:50]}")
            return 'invalid'
    
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Get first IP (client), validate it
        first_ip = x_forwarded_for.split(',')[0].strip()
        return validate_ip(first_ip)
    
    remote_addr = request.META.get('REMOTE_ADDR', 'unknown')
    return validate_ip(remote_addr)


def normalize_value(val: Any) -> str:
    """
    Normalize value for comparison
    
    Converts values to consistent format for change detection:
    - None/empty → ''
    - Boolean → '1'/'0'
    - Date → 'YYYY-MM-DD'
    - String → lowercase
    
    OPTIMIZED: Early returns for common cases
    """
    # Fast path for None/empty (most common)
    if val is None or val == '':
        return ''
    
    # Type-based handling with early returns
    val_type = type(val)
    
    if val_type is bool:
        return '1' if val else '0'
    
    if val_type in (date, datetime):
        return val.strftime('%Y-%m-%d')
    
    if val_type is list:
        return '' if not val else str(val)
    
    # String handling
    v = str(val).strip()
    if not v:
        return ''
    
    # Use lowercase for comparison (cache the result)
    v_lower = v.lower()
    
    # Boolean string normalization (O(1) set lookup)
    if v_lower in {'no', 'false'}:
        return '0'
    if v_lower in {'yes', 'true'}:
        return '1'
    
    # Normalize dates (DD/MM/YYYY → YYYY-MM-DD) using pre-compiled pattern
    if _DATE_PATTERN.match(v):
        parts = v.split('/')
        return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    
    return v_lower


def format_value_for_display(val: Any) -> str:
    """
    Format value for display in templates
    
    Converts values to user-friendly format:
    - None/empty → '(trống)'
    - Boolean → 'Có'/'Không'
    - Date → 'DD/MM/YYYY'
    """
    if val is None or val == '':
        return '(trống)'
    
    if isinstance(val, bool):
        return 'Có' if val else 'Không'
    
    if isinstance(val, (date, datetime)):
        return val.strftime('%d/%m/%Y')
    
    return str(val)
