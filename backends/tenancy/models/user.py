# backend/tenancy/models/user.py - ENHANCED WITH ROLE INTEGRATION
"""
User model with complete role integration
"""
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils import cache
from typing import Optional, Tuple, Set, Dict, List, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from backends.tenancy.models import StudyMembership

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
        
        logger.debug(f"Bulk unblocked {unblocked_count} users")
        return unblocked_count


class User(AbstractUser):
    """
    Extended User model with full role integration
    """
    
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
    
    notes = models.TextField(
        blank=True,
        verbose_name="Admin Notes",
        help_text="Internal notes about user account status or issues"
    )
    
    # Timestamps
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
    
    objects = UserManager()
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = "Authentication Users"
        verbose_name_plural = "Authentication Users"
        indexes = [
            models.Index(fields=['username'], name='idx_user_username'),
            models.Index(fields=['email'], name='idx_user_email'),
            models.Index(fields=['is_active'], name='idx_user_is_active'),
        ]
        
    def __str__(self):
        return self.get_full_name() or self.username
    
    # ==========================================
    # NEW: ROLE MANAGEMENT METHODS
    # ==========================================
    
    def get_study_role(self, study) -> Optional[str]:
        """
        Get user's role key in a study
        
        Args:
            study: Study instance
            
        Returns:
            Role key (e.g., 'data_manager') or None
            
        Example:
            >>> user.get_study_role(study)
            'data_manager'
        """
        if not self.is_active:
            return None
        
        from backends.tenancy.models import StudyMembership
        
        try:
            membership = StudyMembership.objects.select_related('group').get(
                user=self,
                study=study,
                is_active=True
            )
            return membership.get_role_key()
        except StudyMembership.DoesNotExist:
            return None
    
    def get_study_role_display(self, study) -> Optional[str]:
        """
        Get user's role display name in a study
        
        Args:
            study: Study instance
            
        Returns:
            Display name (e.g., 'Data Manager') or None
            
        Example:
            >>> user.get_study_role_display(study)
            'Data Manager'
        """
        if not self.is_active:
            return None
        
        from backends.tenancy.models import StudyMembership
        
        try:
            membership = StudyMembership.objects.select_related('group').get(
                user=self,
                study=study,
                is_active=True
            )
            return membership.get_role_display_name()
        except StudyMembership.DoesNotExist:
            return None
    
    def has_role_in_study(self, study, role_key: str) -> bool:
        """
        Check if user has specific role in a study
        
        Args:
            study: Study instance
            role_key: Role key to check (e.g., 'data_manager')
            
        Returns:
            True if user has this role
            
        Example:
            >>> user.has_role_in_study(study, 'data_manager')
            True
        """
        if not self.is_active:
            return False
        
        current_role = self.get_study_role(study)
        return current_role == role_key
    
    def get_all_study_roles(self) -> Dict[int, Dict[str, str]]:
        """
        Get all roles across all studies
        
        Returns:
            Dict mapping study_id to role info
            
        Example:
            >>> user.get_all_study_roles()
            {
                1: {'study_code': '43EN', 'role_key': 'data_manager', 'role_name': 'Data Manager'},
                2: {'study_code': '44EN', 'role_key': 'research_staff', 'role_name': 'Research Staff'}
            }
        """
        if not self.is_active:
            return {}
        
        from backends.tenancy.models import StudyMembership
        
        memberships = StudyMembership.objects.filter(
            user=self,
            is_active=True
        ).select_related('study', 'group')
        
        result = {}
        for membership in memberships:
            result[membership.study_id] = {
                'study_code': membership.study.code,
                'study_name': membership.study.safe_translation_getter('name', any_language=True),
                'role_key': membership.get_role_key(),
                'role_name': membership.get_role_display_name(),
                'can_access_all_sites': membership.can_access_all_sites,
            }
        
        return result
    
    def is_study_admin(self, study) -> bool:
        """
        Check if user is admin in a study (has privileged role)
        
        Args:
            study: Study instance
            
        Returns:
            True if user has privileged role
        """
        role_key = self.get_study_role(study)
        if not role_key:
            return False
        
        from backends.tenancy.utils.role_manager import RoleTemplate
        
        role_config = RoleTemplate.get_role_config(role_key)
        return role_config.get('is_privileged', False) if role_config else False
    
    def get_study_membership(self, study) -> Optional['StudyMembership']:
        """
        Get active membership for a study
        
        Args:
            study: Study instance
            
        Returns:
            StudyMembership instance or None
        """
        if not self.is_active:
            return None
        
        from backends.tenancy.models import StudyMembership
        
        try:
            return StudyMembership.objects.select_related('group', 'study').prefetch_related(
                'study_sites__site'
            ).get(
                user=self,
                study=study,
                is_active=True
            )
        except StudyMembership.DoesNotExist:
            return None
    
    # ==========================================
    # ENHANCED: PERMISSION METHODS WITH CACHING
    # ==========================================
    
    def get_study_permissions(self, study) -> Set[str]:
        """
        Get all permissions for a specific study (CACHED)
        
        Args:
            study: Study instance
            
        Returns:
            Set of permission codenames
        """
        if not self.is_active:
            return set()
        
        # Use optimized utility with caching
        from backends.tenancy.utils import TenancyUtils
        return TenancyUtils.get_user_permissions(self, study)
    
    def has_study_permission(self, study, permission_codename: str) -> bool:
        """
        Check if user has a specific permission in a study (CACHED)
        
        Args:
            study: Study instance
            permission_codename: Permission codename (e.g., 'add_patient')
        
        Returns:
            True if user has permission
        """
        if not self.is_active:
            return False
        
        from backends.tenancy.utils import TenancyUtils
        return TenancyUtils.user_has_permission(self, study, permission_codename)
    
    def get_permission_summary(self, study) -> Dict[str, List[str]]:
        """
        Get organized permission summary for a study
        
        Args:
            study: Study instance
            
        Returns:
            Dict grouping permissions by model
            
        Example:
            >>> user.get_permission_summary(study)
            {
                'patient': ['add', 'change', 'view'],
                'visit': ['view'],
                'report': ['add', 'view', 'export']
            }
        """
        if not self.is_active:
            return {}
        
        from backends.tenancy.utils import TenancyUtils
        return TenancyUtils.get_permission_display(self, study)
    
    # ==========================================
    # AXES INTEGRATION
    # ==========================================
    
    def get_axes_status(self) -> Tuple[bool, Optional[str], Optional[int]]:
        """Get axes block status"""
        from axes.models import AccessAttempt
        from axes.conf import settings as axes_settings
        
        is_blocked = False
        reason = None
        attempts = 0
        
        try:
            username_attempts = AccessAttempt.objects.filter(
                username=self.username
            ).first()
            
            if username_attempts:
                attempts = username_attempts.failures_since_start
                
                if attempts >= axes_settings.AXES_FAILURE_LIMIT:
                    is_blocked = True
                    reason = f"Too many failed login attempts ({attempts})"
                    
        except Exception as e:
            logger.error(f"Error checking axes status for user {self.username}: {e}")
            attempts = self.failed_login_attempts
            
        return is_blocked, reason, attempts
    
    def reset_axes_locks(self) -> bool:
        """Reset all axes locks"""
        from axes.models import AccessAttempt, AccessFailureLog
        from axes.utils import reset
        
        try:
            reset(username=self.username)
            AccessAttempt.objects.filter(username=self.username).delete()
            AccessFailureLog.objects.filter(username=self.username).delete()
            
            cache.delete_many([
                f"axes:username:{self.username}",
                f"user_blocked_{self.username}",
                f"user_obj_{self.pk}",
            ])
                
            return True
        except Exception as e:
            logger.error(f"Error resetting axes locks: {e}")
            return False
    
    def unblock_user(self) -> bool:
        """Unblock user completely"""
        success = self.reset_axes_locks()
        if success:
            self.is_active = True
            self.failed_login_attempts = 0
            self.last_failed_login = None
            
            super().save(update_fields=[
                'is_active', 'failed_login_attempts', 'last_failed_login'
            ])
            
            logger.debug(f"User {self.username} unblocked successfully")
            
        return success
    
    def block_user(self, reason: Optional[str] = None) -> bool:
        """Block user"""
        self.is_active = False
        
        if reason:
            current_notes = self.notes or ""
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            self.notes = f"{current_notes}\n[{timestamp}] Blocked: {reason}".strip()
        
        self.save(update_fields=['is_active', 'notes'])
        logger.debug(f"User {self.username} blocked: {reason or 'No reason'}")
        return True
    
    @property
    def is_axes_blocked(self) -> bool:
        """Check if blocked by axes"""
        is_blocked, _, _ = self.get_axes_status()
        return is_blocked
    
    @property
    def axes_failure_count(self) -> int:
        """Get axes failure count"""
        _, _, attempts = self.get_axes_status()
        return attempts or 0
    
    @property
    def is_blocked(self) -> bool:
        """Check if blocked"""
        return not self.is_active
    
    # ==========================================
    # STUDY ACCESS METHODS
    # ==========================================
    
    def get_full_name(self):
        """Return full name"""
        parts = [self.first_name, self.last_name]
        return ' '.join(part for part in parts if part).strip()
    
    def has_study_access(self, study) -> bool:
        """Check if user has access to study"""
        if not self.is_active:
            return False
            
        from backends.tenancy.models import StudyMembership
        
        return StudyMembership.objects.filter(
            user=self,
            study=study,
            is_active=True
        ).exists()
    
    def get_accessible_studies(self):
        """Get all accessible studies"""
        from backends.tenancy.models import Study
        
        return Study.objects.filter(
            memberships__user=self,
            memberships__is_active=True,
            status__in=[Study.Status.ACTIVE, Study.Status.PLANNING]
        ).distinct()
    
    def save(self, *args, **kwargs):
        """Override save to handle axes synchronization"""
        if self.pk:
            try:
                original = User.objects.get(pk=self.pk)
                
                if not original.is_active and self.is_active:
                    self.reset_axes_locks()
                    logger.debug(f"User {self.username} activated - axes locks reset")
                    
                elif original.is_active and not self.is_active:
                    logger.debug(f"User {self.username} deactivated")
                    
            except User.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)