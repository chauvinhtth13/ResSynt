# backends/api/base/utils.py
"""
Shared utilities for API base module.
"""
from typing import Dict, Any
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
