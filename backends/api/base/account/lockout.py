# backends/api/base/account/lockout.py
"""
Custom lockout handlers for django-axes.
"""
import logging
from typing import Dict, Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _

from ..utils import get_client_ip, get_username_from_credentials

logger = logging.getLogger(__name__)


def lockout_response(
    request: HttpRequest,
    credentials: Dict[str, Any],
    *args,
    **kwargs
) -> HttpResponse:
    """
    Production lockout handler - renders login page with error.
    """
    from .forms import AxesLoginForm
    
    username = get_username_from_credentials(credentials, request)
    ip = get_client_ip(request)
    
    logger.warning(f"AXES LOCKOUT: '{username}' from {ip}")
    
    form = AxesLoginForm(initial={'login': username}, request=request)
    form.set_lockout_info({'is_locked': True})
    form.add_lockout_error(_("Account locked. Contact administrator."))
    
    return render(request, 'account/login.html', {
        'form': form,
        'is_locked_out': True,
    }, status=403)


def dev_lockout_response(
    request: HttpRequest,
    credentials: Dict[str, Any],
    *args,
    **kwargs
) -> HttpResponse:
    """
    Development lockout handler - bypasses lockout for superusers.
    """
    from django.contrib.auth import get_user_model
    from django.contrib import messages
    from django.db import models
    
    username = get_username_from_credentials(credentials, request)
    
    User = get_user_model()
    try:
        user = User.objects.filter(
            models.Q(username__iexact=username) | 
            models.Q(email__iexact=username)
        ).first()
        
        if user and user.is_superuser:
            logger.info(f"DEV: Superuser '{username}' lockout bypassed")
            messages.warning(request, "[DEV] Superuser lockout bypassed")
            return redirect('account_login')
    except Exception:
        pass
    
    return lockout_response(request, credentials, *args, **kwargs)


def json_lockout_response(
    request: HttpRequest,
    credentials: Dict[str, Any],
    *args,
    **kwargs
) -> HttpResponse:
    """
    JSON lockout response for API endpoints.
    """
    from django.http import JsonResponse
    
    logger.warning(f"AXES JSON LOCKOUT: '{get_username_from_credentials(credentials, request)}'")
    
    return JsonResponse({
        'error': 'account_locked',
        'message': 'Account locked. Contact administrator.',
    }, status=403)
