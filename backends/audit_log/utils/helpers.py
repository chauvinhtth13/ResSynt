# backends/audit_log/utils/helpers.py
"""
🌐 BASE Common Helper Functions - Shared across all studies
"""
import logging
import re
from typing import Any
from datetime import date, datetime

logger = logging.getLogger(__name__)


def get_client_ip(request) -> str:
    """
    Get client IP address from request
    
    Handles X-Forwarded-For header (for proxies/load balancers)
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def normalize_value(val: Any) -> str:
    """
    Normalize value for comparison
    
    Converts values to consistent format for change detection:
    - None/empty → ''
    - Boolean → '1'/'0'
    - Date → 'YYYY-MM-DD'
    - String → lowercase
    """
    if val is None or val == '':
        return ''
    
    # Handle empty lists (ArrayField)
    if isinstance(val, list) and not val:
        return ''
    
    if isinstance(val, bool):
        return '1' if val else '0'
    
    if isinstance(val, (date, datetime)):
        return val.strftime('%Y-%m-%d')
    
    v = str(val).strip()
    
    # ✅ CRITICAL FIX: Don't normalize 'None' string to empty!
    # Database might have literal string 'None', keep it as is
    # Only normalize if lowercase AND checking for actual null indicators
    # but 'None' in database is DATA, not null!
    if not v:
        return ''
    
    if v.lower() in ['no', 'false']:
        return '0'
    if v.lower() in ['yes', 'true']:
        return '1'
    
    # Normalize dates (DD/MM/YYYY → YYYY-MM-DD)
    if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', v):
        parts = v.split('/')
        return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    
    return v.lower()


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
