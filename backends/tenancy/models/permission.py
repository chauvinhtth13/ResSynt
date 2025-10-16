# backend/tenancy/models/permission.py - ENHANCED WITH AUTO GROUP SYNC
"""
StudyMembership model with automatic User-Group synchronization
When you assign a role via StudyMembership, the user is automatically added to that Group
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
    User membership with AUTOMATIC user-group synchronization
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
        help_text="Select a role for this study. User will be automatically added to this group."
    )

    study_sites = models.ManyToManyField(
        'StudySite',
        blank=True,
        related_name="memberships",
        verbose_name="Study Sites",
        help_text="Specific sites within the study. Leave empty for all sites."
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Is Active"
    )

    can_access_all_sites = models.BooleanField(
        default=False,
        verbose_name="Can Access All Sites",
        help_text="If true, user has access to all sites in the study"
    )

    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="Additional notes about this membership"
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Assigned At"
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="memberships_assigned",
        verbose_name="Assigned By"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    class Meta:
        db_table = '"management"."study_memberships"'
        verbose_name = "Study Membership"
        verbose_name_plural = "Study Memberships"
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'study'],
                name='unique_user_study'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'study', 'is_active'], name='idx_membership_user_study'),
            models.Index(fields=['study', 'is_active'], name='idx_membership_study'),
            models.Index(fields=['group'], name='idx_membership_group'),
        ]

    def __str__(self):
        """String representation"""
        if not self.user or not self.study:
            return "Incomplete StudyMembership"
        
        group_name = self.group.name if self.group else "No Role"
        sites_str = self.get_sites_display() if self.pk else "N/A"
        
        return f"{self.user.username} - {self.study.code} - {group_name} ({sites_str})"

    # ==========================================
    #  NEW: USER-GROUP SYNCHRONIZATION
    # ==========================================
    
    def sync_user_to_group(self) -> bool:
        """
        Add user to the Django Group
        This makes the group appear in User's permissions panel
        
        Returns:
            True if user was added, False if already in group
        """
        if not self.user or not self.group:
            return False
        
        if not self.is_active:
            # If inactive, remove from group
            return self.remove_user_from_group()
        
        # Add user to group
        if not self.user.groups.filter(pk=self.group.pk).exists():
            self.user.groups.add(self.group)
            logger.debug(
                f"Added user {self.user.username} to group {self.group.name}"
            )
            
            # Clear user permissions cache
            cache.delete(f'user_perms_{self.user.pk}')
            cache.delete(f'user_obj_{self.user.pk}')
            
            return True
        
        return False
    
    def remove_user_from_group(self) -> bool:
        """
        Remove user from the Django Group
        
        Returns:
            True if user was removed, False if not in group
        """
        if not self.user or not self.group:
            return False
        
        if self.user.groups.filter(pk=self.group.pk).exists():
            self.user.groups.remove(self.group)
            logger.debug(
                f"Removed user {self.user.username} from group {self.group.name}"
            )
            
            # Clear cache
            cache.delete(f'user_perms_{self.user.pk}')
            cache.delete(f'user_obj_{self.user.pk}')
            
            return True
        
        return False
    
    def sync_all_user_groups(self) -> Dict[str, int]:
        """
        Sync ALL user's groups based on active memberships
        This ensures user only has groups from active memberships
        
        Returns:
            Dict with sync statistics
        """
        if not self.user:
            return {'added': 0, 'removed': 0}
        
        # Get all active study memberships for this user
        active_memberships = StudyMembership.objects.filter(
            user=self.user,
            is_active=True
        ).select_related('group')
        
        # Get groups user should have
        should_have_groups = set(m.group for m in active_memberships if m.group)
        
        # Get groups user currently has (study groups only)
        from backends.tenancy.utils.role_manager import StudyRoleManager
        
        current_study_groups = set()
        for group in self.user.groups.all():
            if StudyRoleManager.is_study_group(group.name):
                current_study_groups.add(group)
        
        # Calculate changes
        to_add = should_have_groups - current_study_groups
        to_remove = current_study_groups - should_have_groups
        
        # Apply changes
        added = 0
        removed = 0
        
        for group in to_add:
            self.user.groups.add(group)
            added += 1
            logger.debug(f"Added {self.user.username} to {group.name}")
        
        for group in to_remove:
            self.user.groups.remove(group)
            removed += 1
            logger.debug(f"Removed {self.user.username} from {group.name}")
        
        if added > 0 or removed > 0:
            # Clear cache
            cache.delete(f'user_perms_{self.user.pk}')
            cache.delete(f'user_obj_{self.user.pk}')
        
        return {
            'added': added,
            'removed': removed,
            'total_groups': len(should_have_groups),
        }
    
    # ==========================================
    # ROLE MANAGEMENT METHODS (keep existing)
    # ==========================================
    
    def get_role_key(self) -> Optional[str]:
        """Extract role key from group name"""
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
    
    def get_role_description(self) -> Optional[str]:
        """Get role description"""
        role_key = self.get_role_key()
        if not role_key:
            return None
        
        from backends.tenancy.utils.role_manager import RoleTemplate
        return RoleTemplate.get_description(role_key)
    
    def get_role_info(self) -> Dict[str, any]:
        """Get complete role information"""
        role_key = self.get_role_key()
        if not role_key:
            return {
                'role_key': None,
                'display_name': self.group.name if self.group else None,
                'group_id': self.group_id,
            }
        
        from backends.tenancy.utils.role_manager import RoleTemplate
        
        config = RoleTemplate.get_role_config(role_key)
        if not config:
            return {'role_key': role_key}
        
        return {
            'role_key': role_key,
            'display_name': config.get('display_name'),
            'description': config.get('description'),
            'permissions': config.get('permissions', []),
            'is_privileged': config.get('is_privileged', False),
            'priority': config.get('priority', 0),
            'group_id': self.group_id,
            'group_name': self.group.name if self.group else None,
        }
    
    def is_privileged_role(self) -> bool:
        """Check if this is a privileged role"""
        role_key = self.get_role_key()
        if not role_key:
            return False
        
        from backends.tenancy.utils.role_manager import RoleTemplate
        
        config = RoleTemplate.get_role_config(role_key)
        return config.get('is_privileged', False) if config else False
    
    def get_permissions(self, use_cache: bool = True) -> Set[str]:
        """Get all permission codenames"""
        if not self.group:
            return set()
        
        if use_cache:
            cache_key = f'membership_perms_{self.pk}'
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        study_code_lower = self.study.code.lower()
        app_label = f'study_{study_code_lower}'
        
        permissions = set()
        for perm in self.group.permissions.filter(
            content_type__app_label=app_label
        ).select_related('content_type'):
            permissions.add(perm.codename)
        
        if use_cache:
            cache.set(cache_key, permissions, 300)
        
        return permissions
    
    def has_permission(self, permission_codename: str) -> bool:
        """Check if membership grants specific permission"""
        if not self.is_active:
            return False
        
        permissions = self.get_permissions()
        return permission_codename in permissions
    
    def get_permission_summary(self) -> Dict[str, List[str]]:
        """Get permissions grouped by model"""
        permissions = self.get_permissions()
        
        grouped = {}
        for perm in permissions:
            parts = perm.split('_', 1)
            if len(parts) == 2:
                action, model = parts
                if model not in grouped:
                    grouped[model] = []
                grouped[model].append(action)
        
        for model in grouped:
            grouped[model].sort()
        
        return grouped
    
    def can_perform_action(self, model_name: str, action: str) -> bool:
        """Check if can perform specific action on model"""
        permission_code = f"{action}_{model_name}"
        return self.has_permission(permission_code)
    
    # ==========================================
    # SITE ACCESS METHODS
    # ==========================================
    
    def get_sites_display(self) -> str:
        """Get display string for sites"""
        if self.can_access_all_sites or not self.study_sites.exists():
            return "All Sites"
        return ", ".join([s.site.code for s in self.study_sites.all()])
    
    def has_site_access(self, site_id: int) -> bool:
        """Check if user has access to specific site"""
        if self.can_access_all_sites:
            return True
        if not self.study_sites.exists():
            return True
        return self.study_sites.filter(site_id=site_id).exists()
    
    def get_accessible_sites(self) -> List[str]:
        """Get list of accessible site codes"""
        if self.can_access_all_sites:
            from backends.tenancy.models import StudySite
            return list(
                StudySite.objects.filter(study=self.study)
                .values_list('site__code', flat=True)
            )
        
        return list(
            self.study_sites.values_list('site__code', flat=True)
        )
    
    # ==========================================
    # VALIDATION
    # ==========================================

    def clean(self):
        """Validate membership data"""
        super().clean()
        
        if self.group_id and self.study_id:
            try:
                from backends.tenancy.utils.role_manager import StudyRoleManager
                
                group = Group.objects.get(pk=self.group_id)
                study = self.study if hasattr(self, 'study') else None
                
                if not study:
                    from backends.tenancy.models import Study
                    study = Study.objects.get(pk=self.study_id)
                
                study_code, role_key = StudyRoleManager.parse_group_name(group.name)
                
                if not role_key:
                    raise ValidationError({
                        'group': f"Invalid group format. Group must be a study role group."
                    })
                
                expected_prefix = f"Study {study.code.upper()}."
                if not group.name.startswith(expected_prefix):
                    raise ValidationError({
                        'group': f"Group must belong to study '{study.code}'. "
                                f"Expected format: '{expected_prefix}[Role Name]'"
                    })
                    
            except (Group.DoesNotExist, Exception) as e:
                logger.error(f"Error validating group: {e}")
        
        if self.pk and self.study_id:
            if self.can_access_all_sites and self.study_sites.exists():
                raise ValidationError(
                    "Cannot specify sites when 'can_access_all_sites' is True"
                )
            
            if self.study_sites.exists():
                invalid_sites = self.study_sites.exclude(study_id=self.study_id)
                if invalid_sites.exists():
                    raise ValidationError(
                        "Selected sites must belong to the study"
                    )

    def save(self, *args, **kwargs):
        """
        Override save to:
        1. Run validation
        2. Save the object
        3. Sync user to group automatically
        """
        self.full_clean()
        
        # Track if this is new or group changed
        is_new = not self.pk
        group_changed = False
        
        if not is_new:
            try:
                old = StudyMembership.objects.get(pk=self.pk)
                group_changed = old.group_id != self.group_id
            except StudyMembership.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # AUTO-SYNC: Add user to group after save
        if is_new or group_changed:
            self.sync_user_to_group()
            logger.debug(
                f"Auto-synced user {self.user.username} to group {self.group.name}"
            )
        
        # If active status changed, sync again
        if not is_new:
            try:
                old = StudyMembership.objects.get(pk=self.pk)
                if old.is_active != self.is_active:
                    self.sync_user_to_group()
            except StudyMembership.DoesNotExist:
                pass
        
        # Clear cache
        if self.pk:
            cache.delete(f'membership_perms_{self.pk}')

    def refresh_permissions(self) -> int:
        """Refresh permissions for this membership's role"""
        from backends.tenancy.utils.role_manager import StudyRoleManager
        
        if not self.study:
            return 0
        
        try:
            result = StudyRoleManager.assign_permissions(
                self.study.code, 
                force=True
            )
            
            cache.delete(f'membership_perms_{self.pk}')
            
            return result.get('permissions_assigned', 0)
            
        except Exception as e:
            logger.error(f"Error refreshing permissions: {e}")
            return 0
    
    def get_comparison_with_role(self, role_key: str) -> Dict[str, any]:
        """Compare current permissions with another role"""
        from backends.tenancy.utils.role_manager import RoleTemplate
        
        current_role = self.get_role_key()
        current_config = RoleTemplate.get_role_config(current_role) if current_role else {}
        target_config = RoleTemplate.get_role_config(role_key)
        
        if not target_config:
            return {'error': f'Invalid role key: {role_key}'}
        
        current_perms = set(current_config.get('permissions', []))
        target_perms = set(target_config.get('permissions', []))
        
        return {
            'current_role': current_role,
            'current_display': current_config.get('display_name'),
            'target_role': role_key,
            'target_display': target_config.get('display_name'),
            'added_permissions': list(target_perms - current_perms),
            'removed_permissions': list(current_perms - target_perms),
            'same_permissions': list(current_perms & target_perms),
            'would_upgrade': target_config.get('priority', 0) > current_config.get('priority', 0),
        }
    
    @staticmethod
    def get_study_group_name(study_code: str, role_name: str) -> str:
        """DEPRECATED: Use StudyRoleManager.get_group_name()"""
        from backends.tenancy.utils.role_manager import StudyRoleManager
        return StudyRoleManager.get_group_name(study_code, role_name)

    @staticmethod
    def parse_group_name(group_name: str) -> tuple:
        """DEPRECATED: Use StudyRoleManager.parse_group_name()"""
        from backends.tenancy.utils.role_manager import StudyRoleManager
        return StudyRoleManager.parse_group_name(group_name)


# ==========================================
#  NEW: SIGNALS FOR AUTO GROUP SYNC
# ==========================================

@receiver(post_save, sender=StudyMembership)
def auto_sync_user_group_on_save(sender, instance, created, **kwargs):
    """
    Automatically sync user to group when StudyMembership is saved
    This ensures Django's User.groups reflects StudyMembership assignments
    """
    if instance.user and instance.group:
        instance.sync_user_to_group()


@receiver(post_delete, sender=StudyMembership)
def auto_remove_user_from_group_on_delete(sender, instance, **kwargs):
    """
    When StudyMembership is deleted, check if user should be removed from group
    Only remove if user has no other active memberships with this group
    """
    if not instance.user or not instance.group:
        return
    
    # Check if user has other active memberships with same group
    other_memberships = StudyMembership.objects.filter(
        user=instance.user,
        group=instance.group,
        is_active=True
    ).exclude(pk=instance.pk).exists()
    
    if not other_memberships:
        # No other memberships with this group, remove user from group
        instance.remove_user_from_group()
        logger.debug(
            f"Removed {instance.user.username} from {instance.group.name} "
            f"(no other active memberships)"
        )
    else:
        logger.debug(
            f"Kept {instance.user.username} in {instance.group.name} "
            f"(has other active memberships)"
        )


@receiver(pre_save, sender=StudyMembership)
def handle_group_change(sender, instance, **kwargs):
    """
    Handle when group is changed on existing membership
    Remove from old group, add to new group
    """
    if not instance.pk:
        return
    
    try:
        old = StudyMembership.objects.get(pk=instance.pk)
        
        # If group changed
        if old.group_id != instance.group_id:
            # Remove from old group (if no other memberships)
            if old.group:
                other_with_old = StudyMembership.objects.filter(
                    user=instance.user,
                    group=old.group,
                    is_active=True
                ).exclude(pk=instance.pk).exists()
                
                if not other_with_old:
                    instance.user.groups.remove(old.group)
                    logger.debug(
                        f"Removed {instance.user.username} from old group {old.group.name}"
                    )
            
            # New group will be added in post_save signal
            
    except StudyMembership.DoesNotExist:
        pass