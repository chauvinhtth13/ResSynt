# backend/tenancy/backends.py - SECURE VERSION
from django.contrib.auth.backends import ModelBackend
from axes.utils import reset
from .models.user import User
import logging

logger = logging.getLogger(__name__)


class BlockedUserBackend(ModelBackend):
    """
    Custom authentication backend that:
    1. Blocks users with is_active=False even with correct password
    2. Allows axes reset for active users who login successfully
    3. NEVER resets attempts for blocked users
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """Override authenticate to check active status first"""
        
        # First check if user exists and is blocked
        try:
            user = User.objects.get(username=username)
            
            # CRITICAL: If user is blocked, deny immediately and DON'T reset axes
            if not user.is_active:
                logger.warning(f"Blocked user {username} attempted login - denied without reset")
                # Don't reset axes for blocked users
                return None
                
        except User.DoesNotExist:
            # User doesn't exist, let normal flow handle
            pass
        
        # Proceed with normal authentication
        user = super().authenticate(request, username=username, password=password, **kwargs)
        
        # If authentication successful and user is active, axes will auto-reset
        # This happens ONLY because:
        # 1. User authenticated successfully (correct password)
        # 2. User is active (not blocked)
        # 3. AXES_RESET_ON_SUCCESS = True in settings
        if user and user.is_active:
            logger.info(f"Active user {username} authenticated successfully, axes will reset attempts")
            # The reset happens automatically via axes middleware
            
        return user
    
    def user_can_authenticate(self, user):
        """
        Check if user can authenticate - must be active
        This is a double-check to ensure blocked users can't login
        """
        # Only active users can authenticate
        can_authenticate = super().user_can_authenticate(user)
        
        if not can_authenticate:
            if user is not None:
                username = getattr(user, 'username', 'unknown')
                is_active = getattr(user, 'is_active', False)
                logger.info(f"User {username} cannot authenticate (is_active={is_active})")
            else:
                logger.info("User cannot authenticate (user object is None)")
                
        return can_authenticate