# backend/tenancy/contrib/auth.py
"""
Core authentication and exception classes
"""
from django.contrib.auth.backends import ModelBackend
from django.core.cache import cache
from ..models.user import User
import logging

logger = logging.getLogger(__name__)


# ==========================================
# AUTHENTICATION BACKEND
# ==========================================

class BlockedUserBackend(ModelBackend):
    """
    Enhanced authentication backend with caching and security
    """
    
    CACHE_TTL = 60  # 1 minute cache for user status
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """Override authenticate with caching"""
        if not username:
            return None
        
        # Check cache for blocked status
        cache_key = f'user_blocked_{username}'
        is_blocked = cache.get(cache_key)
        
        if is_blocked is None:
            # Check database
            try:
                user = User.objects.only('username', 'is_active').get(username=username)
                is_blocked = not user.is_active
                cache.set(cache_key, is_blocked, self.CACHE_TTL)
            except User.DoesNotExist:
                return None
        
        # If blocked, deny immediately
        if is_blocked:
            logger.warning(f"Blocked user {username} attempted login")
            return None
        
        # Proceed with authentication
        user = super().authenticate(request, username=username, password=password, **kwargs)
        
        if user and user.is_active:
            # Clear block cache on successful login
            cache.delete(cache_key)
            logger.debug(f"User {username} authenticated successfully")
        
        return user
    
    def get_user(self, user_id):
        """Get user with caching"""
        cache_key = f'user_obj_{user_id}'
        user = cache.get(cache_key)
        
        if user is None:
            try:
                user = User.objects.select_related('last_study_accessed').get(pk=user_id)
                cache.set(cache_key, user, self.CACHE_TTL)
            except User.DoesNotExist:
                return None
        
        return user if self.user_can_authenticate(user) else None

# ==========================================