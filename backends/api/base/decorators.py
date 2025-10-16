# backend/api/base/decorators.py
"""
Custom decorators for views
"""
from functools import wraps
from django.http import HttpResponse
from django.conf import settings
from django.utils import translation
from .constants import AppConstants


def ensure_language(view_func):
    """
    Decorator to ensure language is set to default if not already set.
    
    Usage:
        @ensure_language
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not translation.get_language():
            translation.activate(AppConstants.DEFAULT_LANGUAGE)
            request.session[settings.LANGUAGE_SESSION_KEY] = AppConstants.DEFAULT_LANGUAGE
        return view_func(request, *args, **kwargs)
    return wrapper


def set_language_on_response(view_func):
    """
    Decorator to automatically set language cookie on response.
    
    Usage:
        @set_language_on_response
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        
        if isinstance(response, HttpResponse):
            lang_code = translation.get_language() or AppConstants.DEFAULT_LANGUAGE
            
            # Set language cookie
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                lang_code,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
                samesite=settings.LANGUAGE_COOKIE_SAMESITE,
            )
        
        return response
    return wrapper


def combined_language_decorator(view_func):
    """
    Combined decorator that ensures language and sets cookie.
    Convenience decorator that combines both ensure_language and set_language_on_response.
    
    Usage:
        @combined_language_decorator
        def my_view(request):
            ...
    """
    return set_language_on_response(ensure_language(view_func))