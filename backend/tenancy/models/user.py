# backend/tenancy/models/user.py - FIXED VERSION
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
    
    def unblock_users(self, queryset=None):
        """Bulk unblock users"""
        if queryset is None:
            queryset = self.filter(status=User.Status.BLOCKED)
        
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
    
    def get_blocked_users(self):
        """Get all blocked users (either by status or axes)"""
        blocked_by_status = self.filter(status=User.Status.BLOCKED)
        blocked_by_axes = []
        
        for user in self.filter(status=User.Status.ACTIVE):
            if user.is_axes_blocked:
                blocked_by_axes.append(user.pk)
        
        # Combine both querysets
        from django.db.models import Q
        return self.filter(
            Q(status=User.Status.BLOCKED) | Q(pk__in=blocked_by_axes)
        )


class User(AbstractUser):
    """Extended User model for ResSync platform"""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'  
        SUSPENDED = 'suspended', 'Suspended'
        BLOCKED = 'blocked', 'Blocked by Security'
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        verbose_name="Status"
    )
    
    # Study tracking
    last_study_accessed = models.ForeignKey(
        'Study', 
        null=True, 
        blank=True,
        on_delete=models.SET_NULL,
        related_name='last_accessed_by',
        verbose_name="Last Study Accessed"
    )
    
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
        verbose_name="Created By"
    )

        # Track status changes
    _original_status = None
    
    # Use custom manager
    objects = UserManager()
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = "Authentication User"
        verbose_name_plural = "Authentication Users"
        indexes = [
            models.Index(fields=['username'], name='idx_user_username'),
            models.Index(fields=['email'], name='idx_user_email'),
            models.Index(fields=['status'], name='idx_user_status'),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_status = self.status
        
    def __str__(self):
        return self.get_full_name() or self.username
    
    def save(self, *args, **kwargs):
        """Override save to handle status changes"""
        # Check if status is changing from BLOCKED to ACTIVE
        if self.pk and self._original_status == self.Status.BLOCKED and self.status == self.Status.ACTIVE:
            # Automatically unblock in axes
            self.unblock_user()
            logger.info(f"User {self.username} unblocked via status change to ACTIVE")
        
        # Check if user is being activated from any non-active status
        elif self.pk and self._original_status != self.Status.ACTIVE and self.status == self.Status.ACTIVE:
            # Reset axes locks when activating user
            self.reset_axes_locks()
            logger.info(f"User {self.username} axes reset due to activation")
        
        # Auto-sync axes block status to user status
        elif self.pk and self.is_axes_blocked and self.status == self.Status.ACTIVE:
            # If axes is blocking but status is active, update status
            self.status = self.Status.BLOCKED
            logger.warning(f"User {self.username} status synced to BLOCKED due to axes lock")
        
        super().save(*args, **kwargs)
        self._original_status = self.status
    
    def get_axes_status(self) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Get axes block status for this user
        Returns: (is_blocked, reason, attempts_count)
        """
        from axes.models import AccessAttempt, AccessFailureLog
        from axes.helpers import get_client_username, get_client_cache_keys
        from django.core.cache import cache
        
        # Check if user is blocked
        is_blocked = False
        reason = None
        attempts = 0
        
        try:
            # Check by username
            username_attempts = AccessAttempt.objects.filter(
                username=self.username
            ).first()
            
            if username_attempts:
                attempts = username_attempts.failures_since_start
                
                # Check cache for block status
                from axes.conf import settings as axes_settings
                if attempts >= axes_settings.AXES_FAILURE_LIMIT:
                    is_blocked = True
                    reason = f"Too many failed login attempts ({attempts})"
            
            # Also check AccessFailureLog for recent failures
            recent_failures = AccessFailureLog.objects.filter(
                username=self.username,
                attempt_time__gte=timezone.now() - timezone.timedelta(hours=24)
            ).count()
            
            if recent_failures > 0 and not is_blocked:
                # Check if there's an active lock
                from axes.handlers.database import AxesDatabaseHandler
                handler = AxesDatabaseHandler()
                if handler.is_locked(request=None, credentials={'username': self.username}):
                    is_blocked = True
                    reason = f"Account locked due to {recent_failures} recent failures"
                    
        except Exception as e:
            # Log error but don't break
            logger.error(f"Error checking axes status for user {self.username}: {e}")
            
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
                f"axes:ip:*",  # This would need proper IP tracking
            ]
            for key in cache_keys:
                cache.delete(key)
                
            return True
        except Exception as e:
            logger.error(f"Error resetting axes locks for user {self.username}: {e}")
            return False
    
    def unblock_user(self) -> bool:
        """Unblock user completely - both status and axes"""
        success = self.reset_axes_locks()
        if success:
            # Also ensure is_active is True
            self.is_active = True
            # Reset security counters
            self.failed_login_attempts = 0
            self.last_failed_login = None
            
            if self.status == self.Status.BLOCKED:
                self.status = self.Status.ACTIVE
                
            # Save without triggering another unblock
            super().save(update_fields=[
                'is_active', 'status', 'failed_login_attempts', 'last_failed_login'
            ])
            
        return success
    
    def block_user(self, reason: Optional[str] = None) -> bool:
        """Block user - set status to BLOCKED"""
        self.status = self.Status.BLOCKED
        self.is_active = False
        
        if reason:
            current_notes = self.notes or ""
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            self.notes = f"{current_notes}\n[{timestamp}] Blocked: {reason}".strip()
        
        self.save(update_fields=['status', 'is_active', 'notes'])
        logger.info(f"User {self.username} blocked: {reason or 'No reason specified'}")
        return True
    
    def sync_with_axes(self) -> bool:
        """Sync user status with axes block status"""
        is_blocked, reason, attempts = self.get_axes_status()
        
        if is_blocked and self.status == self.Status.ACTIVE:
            # Axes is blocking but user is active - sync to blocked
            self.status = self.Status.BLOCKED
            self.save(update_fields=['status'])
            logger.info(f"User {self.username} status synced to BLOCKED (axes: {reason})")
            return True
            
        elif not is_blocked and self.status == self.Status.BLOCKED:
            # User is blocked but axes is not blocking - might need review
            logger.warning(
                f"User {self.username} is BLOCKED but axes is not blocking. "
                f"Consider reviewing status."
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
    
    
    def get_full_name(self):
        """Return full name"""
        parts = [self.first_name, self.last_name]
        return ' '.join(part for part in parts if part).strip()
    
    def has_study_access(self, study):
        """Check if user has access to a specific study"""
        return self.study_memberships.filter( # pyright: ignore[reportAttributeAccessIssue]
            study=study,
            is_active=True
        ).exists()
    
    def get_study_permissions(self, study):
        """Get all permissions for a specific study"""
        from django.db.models import Q
        
        memberships = self.study_memberships.filter( # pyright: ignore[reportAttributeAccessIssue]
            study=study,
            is_active=True
        ).select_related('role').prefetch_related(
            'role__role_permissions__permission'
        )
        
        permissions = set()
        for membership in memberships:
            for role_perm in membership.role.role_permissions.all():
                permissions.add(role_perm.permission.code)
        
        return permissions