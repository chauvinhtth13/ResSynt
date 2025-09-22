# backend/tenancy/backends.py - UPDATED VERSION
from django.contrib.auth.backends import ModelBackend
from axes.utils import reset
from .models.user import User
import logging

logger = logging.getLogger(__name__)


class BlockedUserBackend(ModelBackend):
    """
    Custom authentication backend that:
    1. Blocks users with status=BLOCKED even with correct password
    2. Allows axes reset for non-blocked users who login successfully
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """Override authenticate to check block status first"""
        
        # First check if user exists
        try:
            user = User.objects.get(username=username)
            
            # PRIORITY CHECK: If user.status = BLOCKED, deny immediately
            if user.status == User.Status.BLOCKED:
                logger.warning(f"Blocked user {username} attempted login - denied despite correct password")
                # Don't reset axes for blocked users
                return None
            
            # Check if inactive (different from blocked)
            if not user.is_active and user.status != User.Status.BLOCKED:
                # User is just inactive, not blocked
                logger.info(f"Inactive (but not blocked) user {username} attempted login")
                # Let normal authentication flow handle this
                
        except User.DoesNotExist:
            # User doesn't exist, let normal flow handle
            pass
        
        # Proceed with normal authentication
        user = super().authenticate(request, username=username, password=password, **kwargs)
        
        # If authentication successful and user is NOT blocked, axes will auto-reset
        # (because AXES_RESET_ON_SUCCESS = True)
        if user and user.status != User.Status.BLOCKED:
            logger.info(f"User {username} authenticated successfully, axes will reset attempts")
            
        return user
    
    def user_can_authenticate(self, user):
        """
        Additional check: Reject users with status = BLOCKED
        """
        # First check Django's default (is_active)
        can_authenticate = super().user_can_authenticate(user)
        
        # Then check our custom status
        if can_authenticate and hasattr(user, 'status'):
            if user.status == User.Status.BLOCKED:
                logger.info(f"User {user.username} has status=BLOCKED, denying authentication")
                return False
                
        return can_authenticate