# backend/tenancy/models/user.py - UPDATED VERSION WITHOUT STATUS
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as BaseUserManager
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class UserManager(BaseUserManager):
    """Custom manager with axes integration"""
    
    def get_blocked_users(self):
        """Get all blocked users (is_active=False)"""
        return self.filter(is_active=False)
    
    def get_active_users(self):
        """Get all active users"""
        return self.filter(is_active=True)
    
    def unblock_users(self, queryset=None):
        """Bulk unblock users"""
        if queryset is None:
            queryset = self.filter(is_active=False)
        
        unblocked_count = 0
        for user in queryset:
            if user.unblock_user():
                unblocked_count += 1
        
        logger.info(f"Bulk unblocked {unblocked_count} users")
        return unblocked_count
    
    def sync_all_with_axes(self):
        """Sync all users with their axes status"""
        synced_count = 0
        for user in self.all():
            if user.sync_with_axes():
                synced_count += 1
        
        logger.info(f"Synced {synced_count} users with axes status")
        return synced_count


class User(AbstractUser):
    """Extended User model for ResSync platform"""
    
    # Study tracking
    last_study_accessed = models.ForeignKey(
        'Study', 
        null=True, 
        blank=True,
        on_delete=models.SET_NULL,
        related_name='last_accessed_by',
        verbose_name="Last Study Accessed"
    )
    
    # Add related_name for StudyMembership relationship
    # This creates the study_memberships attribute
    # StudyMembership model should have a ForeignKey to User
    
    last_study_accessed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last Study Access Time"
    )
    
    # Security fields
    must_change_password = models.BooleanField(
        default=False,
        verbose_name="Must Change Password"
    )
    
    password_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Password Changed At"
    )
    
    failed_login_attempts = models.IntegerField(
        default=0,
        verbose_name="Failed Login Attempts"
    )
    
    last_failed_login = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last Failed Login"
    )
    
    # Additional notes field for tracking block reasons
    notes = models.TextField(
        blank=True,
        verbose_name="Admin Notes",
        help_text="Internal notes about user account status or issues"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )
    
    created_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='users_created',
        verbose_name="Created By (Admin User)",
        help_text="The admin/staff user who created this account"
    )
    
    # Use custom manager
    objects = UserManager()
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = "Authentication User"
        verbose_name_plural = "Authentication Users"
        indexes = [
            models.Index(fields=['username'], name='idx_user_username'),
            models.Index(fields=['email'], name='idx_user_email'),
            models.Index(fields=['is_active'], name='idx_user_is_active'),
        ]
        
    def __str__(self):
        return self.get_full_name() or self.username
    
    def save(self, *args, **kwargs):
        """Override save to handle axes synchronization when activating/deactivating"""
        # Track if is_active is changing
        if self.pk:
            try:
                original = User.objects.get(pk=self.pk)
                
                # If activating a blocked user, reset axes locks
                if not original.is_active and self.is_active:
                    # Reset axes locks when activating
                    self.reset_axes_locks()
                    logger.info(f"User {self.username} activated - axes locks reset")
                    
                # If deactivating an active user, just log it
                elif original.is_active and not self.is_active:
                    logger.info(f"User {self.username} deactivated")
                    
            except User.DoesNotExist:
                pass
        
        # Check axes status only if user is supposedly active
        if self.pk and self.is_active:
            is_blocked, reason, _ = self.get_axes_status()
            if is_blocked:
                # Axes is still blocking - warn but don't override
                logger.warning(f"User {self.username} is active but axes is still blocking: {reason}")
        
        super().save(*args, **kwargs)
    
    def get_axes_status(self) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Get axes block status for this user
        Returns: (is_blocked, reason, attempts_count)
        """
        from axes.models import AccessAttempt
        from axes.conf import settings as axes_settings
        
        is_blocked = False
        reason = None
        attempts = 0
        
        try:
            # Simple check by username only (no request needed)
            username_attempts = AccessAttempt.objects.filter(
                username=self.username
            ).first()
            
            if username_attempts:
                attempts = username_attempts.failures_since_start
                
                # Check if attempts exceed limit
                if attempts >= axes_settings.AXES_FAILURE_LIMIT:
                    is_blocked = True
                    reason = f"Too many failed login attempts ({attempts})"
                    
        except Exception as e:
            logger.error(f"Error checking axes status for user {self.username}: {e}")
            # Fallback to simple check
            attempts = self.failed_login_attempts
            
        return is_blocked, reason, attempts
    
    def reset_axes_locks(self) -> bool:
        """Reset all axes locks for this user"""
        from axes.models import AccessAttempt, AccessFailureLog
        from axes.utils import reset
        
        try:
            # Reset using axes utility
            reset(username=self.username)
            
            # Also clear any remaining records
            AccessAttempt.objects.filter(username=self.username).delete()
            AccessFailureLog.objects.filter(username=self.username).delete()
            
            # Clear cache
            from django.core.cache import cache
            cache_keys = [
                f"axes:username:{self.username}",
                f"axes:ip:*",
            ]
            for key in cache_keys:
                cache.delete(key)
                
            return True
        except Exception as e:
            logger.error(f"Error resetting axes locks for user {self.username}: {e}")
            return False
    
    def unblock_user(self) -> bool:
        """Unblock user completely - both is_active and axes"""
        success = self.reset_axes_locks()
        if success:
            # Activate the user
            self.is_active = True
            # Reset security counters
            self.failed_login_attempts = 0
            self.last_failed_login = None
            
            # Save without triggering another unblock
            super().save(update_fields=[
                'is_active', 'failed_login_attempts', 'last_failed_login'
            ])
            
            logger.info(f"User {self.username} unblocked successfully")
            
        return success
    
    def block_user(self, reason: Optional[str] = None) -> bool:
        """Block user - set is_active to False"""
        self.is_active = False
        
        if reason:
            current_notes = self.notes or ""
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            self.notes = f"{current_notes}\n[{timestamp}] Blocked: {reason}".strip()
        
        self.save(update_fields=['is_active', 'notes'])
        logger.info(f"User {self.username} blocked: {reason or 'No reason specified'}")
        return True
    
    def sync_with_axes(self) -> bool:
        """Sync user is_active with axes block status"""
        is_blocked, reason, attempts = self.get_axes_status()
        
        if is_blocked and self.is_active:
            # Axes is blocking but user is active - sync to blocked
            self.is_active = False
            self.save(update_fields=['is_active'])
            logger.info(f"User {self.username} deactivated (axes: {reason})")
            return True
            
        elif not is_blocked and not self.is_active:
            # User is blocked but axes is not blocking - might need review
            logger.warning(
                f"User {self.username} is blocked but axes is not blocking. "
                f"Consider reviewing account status."
            )
            return False
            
        return True
    
    @property
    def is_axes_blocked(self) -> bool:
        """Check if user is currently blocked by axes"""
        is_blocked, _, _ = self.get_axes_status()
        return is_blocked
    
    @property
    def axes_failure_count(self) -> int:
        """Get current failure count from axes"""
        _, _, attempts = self.get_axes_status()
        return attempts or 0
    
    @property
    def is_blocked(self) -> bool:
        """Check if user is blocked (for compatibility)"""
        return not self.is_active
    
    @property
    def study_memberships(self):
        """Return study memberships for this user"""
        # This property ensures backward compatibility if the related_name isn't set correctly
        from tenancy.models import StudyMembership
        return StudyMembership.objects.filter(user=self)
    
    def get_full_name(self):
        """Return full name"""
        parts = [self.first_name, self.last_name]
        return ' '.join(part for part in parts if part).strip()
    
    def has_study_access(self, study):
        """Check if user has access to a specific study"""
        # Must be active to have any access
        if not self.is_active:
            return False
            
        return self.study_memberships.filter(
            study=study,
            is_active=True
        ).exists()
    
    def get_study_permissions(self, study):
        """Get all permissions for a specific study"""
        # Blocked users have no permissions
        if not self.is_active:
            return set()
            
        from django.db.models import Q
        
        memberships = self.study_memberships.filter(
            study=study,
            is_active=True
        ).select_related('role').prefetch_related(
            'role__role_permissions__permission'
        )
        
        permissions = set()
        for membership in memberships:
            # Import here to avoid circular imports
            from tenancy.models import RolePermission
            
            for role_perm in RolePermission.objects.filter(role=membership.role):
                permissions.add(role_perm.permission.code)
        
        return permissions