# backend/tenancy/models/permission.py
"""
StudyMembership model - Simplified with better integration
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.contrib.auth.models import Group
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from typing import Optional, Set, Dict, List
import logging

logger = logging.getLogger(__name__)


class StudyMembership(models.Model):
    """
    User membership - OPTIMIZED VERSION
    - Removed duplicate methods (delegated to User model)
    - Simplified group sync logic
    - Better cache management
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_memberships",
        verbose_name="User"
    )

    study = models.ForeignKey(
        'Study',
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="Study"
    )

    group = models.ForeignKey(
        Group,
        on_delete=models.PROTECT,
        related_name="study_memberships",
        verbose_name="Role (Group)",
        help_text="Role group for this study"
    )

    study_sites = models.ManyToManyField(
        'StudySite',
        blank=True,
        related_name="memberships",
        verbose_name="Study Sites"
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True
    )

    can_access_all_sites = models.BooleanField(
        default=False,
        help_text="Access to all sites in study"
    )

    notes = models.TextField(blank=True)
    
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="memberships_assigned"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "study_memberships"
        verbose_name = "Study Membership"
        verbose_name_plural = "Study Memberships"
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'study'],
                name='unique_user_study'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'study', 'is_active']),
            models.Index(fields=['study', 'is_active', 'can_access_all_sites']),
            models.Index(fields=['group', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.study.code} - {self.group.name if self.group else 'No Role'}"

    def save(self, *args, **kwargs):
        """Save with validation and auto group sync"""
        # self.full_clean()
        super().save(*args, **kwargs)
        
        # # Sync user groups after save
        # if self.user:
        #     from backends.tenancy.utils import TenancyUtils
        #     TenancyUtils.sync_user_groups(self.user)
        #     TenancyUtils.clear_user_cache(self.user)

    def clean(self):
        """Validate membership"""
        super().clean()
        
        if self.group and self.study:
            from backends.tenancy.utils.role_manager import StudyRoleManager
            
            study_code, role_key = StudyRoleManager.parse_group_name(self.group.name)
            
            if not role_key:
                raise ValidationError({
                    'group': "Invalid group format"
                })
            
            if study_code != self.study.code.upper():
                raise ValidationError({
                    'group': f"Group must belong to study '{self.study.code}'"
                })

    def get_role_key(self) -> Optional[str]:
        """Get role key from group"""
        if not self.group:
            return None
        
        from backends.tenancy.utils.role_manager import StudyRoleManager
        _, role_key = StudyRoleManager.parse_group_name(self.group.name)
        return role_key
    
    def get_role_display_name(self) -> Optional[str]:
        """Get human-readable role name"""
        role_key = self.get_role_key()
        if not role_key:
            return self.group.name if self.group else None

        from backends.tenancy.utils.role_manager import RoleTemplate

        return RoleTemplate.get_display_name(role_key)

    def get_sites_display(self) -> str:
        """Display string for sites"""
        if self.can_access_all_sites:
            return "All Sites"
        
        if not self.pk or not self.study_sites.exists():
            return "No specific sites"
            
        return ", ".join([s.site.code for s in self.study_sites.all()])

    def get_accessible_sites(self):
        """Lấy danh sách sites có thể truy cập"""
        if self.can_access_all_sites:
            return self.study.study_sites.all()
        return self.study_sites.all()

    def has_site_access(self, study_site) -> bool:
        """Kiểm tra quyền truy cập vào study-site cụ thể"""
        if self.can_access_all_sites:
            return True
        return self.study_sites.filter(pk=study_site.pk).exists()
    
    @property
    def sites_list(self) -> list:
        """Get list of accessible site codes"""
        if self.can_access_all_sites:
            return list(self.study.study_sites.values_list('site__code', flat=True))
        
        return list(self.study_sites.values_list('site__code', flat=True))
    
    def get_summary(self) -> dict:
        """Get membership summary"""
        return {
            'user': self.user.username,
            'study': self.study.code,
            'role': self.get_role_display_name(),
            'sites': self.get_sites_display(),
            'is_active': self.is_active
        }


# Single signal handler for group sync
@receiver(post_save, sender=StudyMembership)
def sync_groups_on_save(sender, instance, created, **kwargs):
    if not kwargs.get('raw', False):  # Tránh trong fixtures
        from backends.tenancy.utils import TenancyUtils
        # Delay để tránh race condition
        from django.db import transaction
        transaction.on_commit(lambda: TenancyUtils.sync_user_groups(instance.user))


@receiver(post_delete, sender=StudyMembership)  
def sync_groups_on_delete(sender, instance, **kwargs):
    """Sync user groups when membership deleted"""
    if instance.user:
        from backends.tenancy.utils import TenancyUtils
        TenancyUtils.sync_user_groups(instance.user)