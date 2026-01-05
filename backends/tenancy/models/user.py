# backend/tenancy/models/user.py
"""
User model optimized for django-axes 8.0.0
"""
from django.contrib.auth.models import AbstractUser, UserManager as BaseUserManager
from django.db import models
from django.utils import timezone
from django.core.cache import cache
from typing import Optional, Set, TYPE_CHECKING
import logging

from config import settings

if TYPE_CHECKING:
    from backends.tenancy.models import StudyMembership

logger = logging.getLogger(__name__)


class UserManager(BaseUserManager):
    """Enhanced manager with axes 8.0.0 support"""
    
    def get_by_natural_key(self, username):
        """Override for case-insensitive username"""
        return self.get(username__iexact=username)
    
    def reset_user_axes(self, user):
        """Reset axes locks for specific user - axes 8.0.0 compatible"""
        from axes.utils import reset
        reset(username=user.username)
        return True


class User(AbstractUser):
    """
    User model optimized for axes 8.0.0
    """
    # Security fields
    must_change_password = models.BooleanField(default=True,help_text="User must change password on next login")
    password_changed_at = models.DateTimeField(null=True, blank=True)
    
    last_study_accessed_at= models.DateTimeField(null=True, blank=True)    
    last_study_accessed_id= models.IntegerField(null=True, blank=True) 
    
    #  RSA PUBLIC KEY (for backup signature verification)
    public_key_pem = models.TextField(
        blank=True,
        null=True,
        help_text="User's RSA public key (PEM format) for backup signature verification"
    )
    key_generated_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when RSA key pair was generated"
    )
    key_last_rotated = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp of last key rotation"
    )
    
    # Metadata
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='users_created'
    )
    
    objects = UserManager()
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = "Authentication Users"
        verbose_name_plural = "Authentication Users"
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['is_active']),
        ]

    # ==========================================
    # SIMPLIFIED ROLE METHODS
    # ==========================================
    
    def get_study_membership(self, study) -> Optional['StudyMembership']:
        """Get active membership for a study (cached)"""
        if not self.is_active:
            return None
        
        cache_key = f'membership_{self.pk}_{study.pk}'
        membership = cache.get(cache_key)
        
        if membership is None:
            from backends.tenancy.models import StudyMembership
            
            try:
                membership = StudyMembership.objects.select_related(
                    'group', 'study'
                ).prefetch_related(
                    'study_sites__site'
                ).get(
                    user=self,
                    study=study,
                    is_active=True
                )
                cache.set(cache_key, membership, 300)
            except StudyMembership.DoesNotExist:
                membership = False  # Cache negative result
                cache.set(cache_key, membership, 60)
        
        return membership if membership else None
    
    def get_study_role(self, study) -> Optional[str]:
        """Get role key in study"""
        membership = self.get_study_membership(study)
        return membership.get_role_key() if membership else None
    
    def has_study_permission(self, study, permission: str) -> bool:
        """Check permission in study (uses TenancyUtils for caching)"""
        from backends.tenancy.utils import TenancyUtils
        return TenancyUtils.user_has_permission(self, study, permission)
    
    def get_study_permissions(self, study) -> Set[str]:
        """Get all permissions in study (uses TenancyUtils)"""
        from backends.tenancy.utils import TenancyUtils
        return TenancyUtils.get_user_permissions(self, study)
    
    # ==========================================
    # NEW METHODS - SITES AND PERMISSIONS
    # ==========================================
    
    def get_accessible_sites(self, study=None):
        from backends.tenancy.models import StudyMembership, StudySite
        cache_key = f'user_sites_{self.pk}_{study.pk if study else "all"}'
        sites = cache.get(cache_key)
        
        if sites is None:
            if study:
                # Single query với prefetch
                membership = StudyMembership.objects.filter(
                    user=self, 
                    study=study, 
                    is_active=True
                ).prefetch_related(
                    'study_sites__site'
                ).first()
                
                if not membership:
                    sites = []
                elif membership.can_access_all_sites:
                    sites = list(
                        StudySite.objects.filter(study=study)
                        .values_list('site__code', flat=True)
                    )
                else:
                    sites = [ss.site.code for ss in membership.study_sites.all()]
            else:
                # Bulk query cho all studies
                sites = list(
                    StudySite.objects.filter(
                        memberships__user=self,
                        memberships__is_active=True
                    ).values_list('site__code', flat=True).distinct()
                )
            
            cache.set(cache_key, sites, 300)
        
        return sites
        
    def get_total_permissions_count(self) -> int:
        """Count total permissions across all studies"""
        cache_key = f'user_perms_count_{self.pk}'
        count = cache.get(cache_key)
        
        if count is None:
            count = 0
            for study in self.get_accessible_studies():
                count += len(self.get_study_permissions(study))
            cache.set(cache_key, count, 300)
        
        return count
    
    @property
    def studies_count(self) -> int:
        """Count active studies"""
        from backends.tenancy.models import StudyMembership
        return StudyMembership.objects.filter(user=self, is_active=True).values('study').distinct().count()
    
    def get_memberships_summary(self) -> dict:
        """Get summary of all memberships"""
        from backends.tenancy.models import StudyMembership
        memberships = StudyMembership.objects.filter(user=self, is_active=True).select_related('study', 'group')

        return {
            'total': memberships.count(),
            'by_study': {m.study.code: m.get_role_display_name() for m in memberships},
            'sites_access': sum(1 for m in memberships if m.can_access_all_sites)
        }

    # ==========================================
    # AXES 8.0.0 INTEGRATION
    # ==========================================
    
    def is_axes_locked(self) -> bool:
        """
        Check if user is locked by django-axes
        Direct database check - no cache
        """
        try:
            from axes.models import AccessAttempt
            from axes.conf import settings as axes_settings
            
            # Force fresh query - no cache
            attempt = AccessAttempt.objects.filter(
                username=self.username
            ).first()
            
            if not attempt:
                return False
            
            failure_limit = getattr(axes_settings, 'AXES_FAILURE_LIMIT', 5)
            return attempt.failures_since_start >= failure_limit
            
        except Exception as e:
            logger.error(f"Error checking axes lock: {e}")
            return False


    def can_authenticate(self) -> bool:
        """
        Check if user can authenticate
        Returns False if manually blocked OR axes locked
        """
        # Manually blocked users cannot authenticate
        if not self.is_active:
            return False
        
        # Axes locked users cannot authenticate
        if self.is_axes_locked():
            return False
        
        return True
        
    def get_axes_attempts(self) -> int:
        """
        Get failed attempts - always fresh from DB
        """
        try:
            from axes.models import AccessAttempt
            
            # Force fresh query
            attempt = AccessAttempt.objects.filter(
                username=self.username
            ).first()
            
            return attempt.failures_since_start if attempt else 0
            
        except Exception as e:
            logger.error(f"Error getting attempts: {e}")
            return 0
        
    def reset_axes_locks(self) -> bool:
        """
        Complete axes reset - Fixed version
        """
        try:
            from axes.utils import reset
            reset(username=self.username)
            return True
        except Exception as e:
            logger.error(f"Error resetting axes locks: {e}", exc_info=True)
            return False

    def unblock_user(self) -> bool:
        """Unblock user account manually"""
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])
        
        self.reset_axes_locks()
        
        logger.info(f"User {self.username} unblocked manually")
        return True


    def block_user(self, reason: Optional[str] = None, blocked_by=None) -> bool:
        """Block user account manually"""
        self.is_active = False
        
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        blocker = blocked_by.username if blocked_by else 'System'
        note = f"[{timestamp}] Blocked by {blocker}"
        
        if reason:
            note += f": {reason}"
        
        self.notes = f"{self.notes}\n{note}".strip() if self.notes else note
        self.save(update_fields=['is_active', 'notes', 'updated_at'])
        
        return True
   
    # ==========================================
    # UTILITY METHODS
    # ==========================================
    
    def get_full_name(self):
        """Get full name"""
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    def has_study_access(self, study) -> bool:
        """Check if has access to study"""
        return self.get_study_membership(study) is not None
    
    def get_accessible_studies(self):
        """Get all accessible studies (cached)"""
        from backends.tenancy.utils import TenancyUtils
        return TenancyUtils.get_user_studies(self)
    
    def save(self, *args, **kwargs):
        """Save with axes sync"""
        # If activating user, reset axes locks
        if self.pk:
            try:
                old = User.objects.get(pk=self.pk)
                if not old.is_active and self.is_active:
                    self.reset_axes_locks()
            except User.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)