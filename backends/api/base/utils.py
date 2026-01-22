# backends/api/base/utils.py
"""
Shared utilities for API base module.
"""
import re
from typing import Dict, Any, Optional
from django.http import HttpRequest


def get_client_ip(request: HttpRequest) -> str:
    """
    Get client IP address from request.
    
    Checks in order:
    1. request.axes_ip_address (set by axes middleware)
    2. HTTP_X_FORWARDED_FOR header (first IP)
    3. REMOTE_ADDR
    """
    if not request:
        return 'unknown'
    
    # Axes sets this attribute
    if hasattr(request, 'axes_ip_address'):
        return request.axes_ip_address
    
    # Check X-Forwarded-For header
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    
    return request.META.get('REMOTE_ADDR', 'unknown')


def get_username_from_credentials(
    credentials: Dict[str, Any], 
    request: HttpRequest = None
) -> str:
    """
    Extract username from credentials dict or request POST data.
    
    Args:
        credentials: Dict containing username/login/email keys
        request: Optional request to check POST data
        
    Returns:
        Username string or 'unknown'
    """
    if credentials:
        for key in ['username', 'login', 'email']:
            if credentials.get(key):
                return str(credentials[key])
    
    if request and hasattr(request, 'POST'):
        for key in ['login', 'username', 'email']:
            if request.POST.get(key):
                return request.POST[key]
    
    return 'unknown'


# ============================================================================
# SECURITY UTILITIES
# ============================================================================

# Dangerous characters that could indicate XSS/injection attempts
DANGEROUS_CHARS_PATTERN = re.compile(r'[<>"\'\x00\x0a\x0d\x1a]')

# Maximum length for search queries
MAX_SEARCH_LENGTH = 200

# Maximum length for order_by params
MAX_ORDER_BY_LENGTH = 50


def sanitize_search_query(query: Optional[str], max_length: int = MAX_SEARCH_LENGTH) -> str:
    """
    Sanitize search query input to prevent XSS and injection attacks.
    
    Args:
        query: Raw search query from user input
        max_length: Maximum allowed length
        
    Returns:
        Sanitized search query string
    """
    if not query:
        return ''
    
    # Strip whitespace
    query = str(query).strip()
    
    # Truncate to max length
    if len(query) > max_length:
        query = query[:max_length]
    
    # Remove dangerous characters
    query = DANGEROUS_CHARS_PATTERN.sub('', query)
    
    return query


def validate_order_by(order_by: Optional[str], allowed_fields: list = None) -> Optional[str]:
    """
    Validate order_by parameter to prevent SQL injection.
    
    Args:
        order_by: Raw order_by parameter
        allowed_fields: List of allowed field names
        
    Returns:
        Validated order_by string or None if invalid
    """
    if not order_by:
        return None
    
    order_by = str(order_by).strip()
    
    # Check length
    if len(order_by) > MAX_ORDER_BY_LENGTH:
        return None
    
    # Remove leading - for descending
    field_name = order_by.lstrip('-')
    
    # Only allow alphanumeric and underscore
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', field_name):
        return None
    
    # Check against allowed fields if provided
    if allowed_fields and field_name not in allowed_fields:
        return None
    
    return order_by


def sanitize_page_number(page: Optional[str]) -> int:
    """
    Sanitize page number parameter.
    
    Args:
        page: Raw page number from user input
        
    Returns:
        Valid page number (1 or higher)
    """
    if not page:
        return 1
    
    try:
        page_num = int(page)
        return max(1, page_num)
    except (ValueError, TypeError):
        return 1
