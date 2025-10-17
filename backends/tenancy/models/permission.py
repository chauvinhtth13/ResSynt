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
from typing import Optional, Set, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class StudyMembershipManager(models.Manager):
    """Custom manager for StudyMembership"""
    
    def get_queryset(self):
        """Optimize default queryset"""
        return super().get_queryset().select_related('user', 'study', 'group')
    
    def active(self):
        """Get active memberships"""
        return self.filter(is_active=True)
    
    def for_user(self, user):
        """Get all memberships for a user"""
        return self.filter(user=user).prefetch_related('study_sites__site')
    
    def for_study(self, study):
        """Get all memberships for a study"""
        return self.filter(study=study)
    
    def bulk_sync_users(self, user_ids: List[int]) -> Dict[str, int]:
        """
        Bulk sync groups for multiple users
        More efficient than calling sync one by one
        """
        from django.db import transaction
        
        total_added = 0
        total_removed = 0
        
        with transaction.atomic():
            memberships = self.filter(
                user_id__in=user_ids,
                is_active=True
            ).select_related('user', 'group')
            
            # Group by user
            user_memberships = {}
            for m in memberships:
                if m.user_id not in user_memberships:
                    user_memberships[m.user_id] = []
                user_memberships[m.user_id].append(m)
            
            # Sync each user
            for user_id, user_mems in user_memberships.items():
                if user_mems:
                    result = user_mems[0].sync_all_user_groups()
                    total_added += result['added']
                    total_removed += result['removed']
        
        return {
            'users_synced': len(user_memberships),
            'total_added': total_added,
            'total_removed': total_removed,
        }
    
    def bulk_assign_role(
        self, 
        user_ids: List[int], 
        study_id: int, 
        group_id: int,
        assigned_by=None
    ) -> int:
        """
        Bulk assign role to multiple users
        Much faster than one-by-one
        """
        from django.db import transaction
        
        with transaction.atomic():
            # Create memberships in bulk
            memberships = [
                StudyMembership(
                    user_id=user_id,
                    study_id=study_id,
                    group_id=group_id,
                    assigned_by=assigned_by,
                    is_active=True
                )
                for user_id in user_ids
            ]
            
            created = self.bulk_create(
                memberships,
                ignore_conflicts=True  # Skip duplicates
            )
            
            # Sync groups for all created users
            if created:
                self.bulk_sync_users([m.user_id for m in created])
            
            return len(created)
    
    def bulk_deactivate(self, user_ids: List[int], study_id: int) -> int:
        """Bulk deactivate memberships"""
        from django.db import transaction
        
        with transaction.atomic():
            updated = self.filter(
                user_id__in=user_ids,
                study_id=study_id,
                is_active=True
            ).update(is_active=False)
            
            # Sync to remove from groups
            if updated:
                self.bulk_sync_users(user_ids)
            
            return updated

class StudyMembership(models.Model):
    """
    User membership with AUTOMATIC user-group synchronization
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_memberships",
        verbose_name="User",
    )

    study = models.ForeignKey(
        "Study",
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="Study",
    )

    group = models.ForeignKey(
        Group,
        on_delete=models.PROTECT,
        related_name="study_memberships",
        verbose_name="Role (Group)",
        help_text="Select a role for this study. User will be automatically added to this group.",
    )

    study_sites = models.ManyToManyField(
        "StudySite",
        blank=True,
        related_name="memberships",
        verbose_name="Study Sites",
        help_text="Specific sites within the study. Leave empty for all sites.",
    )

    is_active = models.BooleanField(
        default=True, db_index=True, verbose_name="Is Active"
    )

    can_access_all_sites = models.BooleanField(
        default=False,
        verbose_name="Can Access All Sites",
        help_text="If true, user has access to all sites in the study",
    )

    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="Additional notes about this membership",
    )

    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name="Assigned At")

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="memberships_assigned",
        verbose_name="Assigned By",
    )

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    
    objects = StudyMembershipManager()

    class Meta:
        db_table = '"management"."study_memberships"'
        verbose_name = "Study Membership"
        verbose_name_plural = "Study Memberships"
        constraints = [
            models.UniqueConstraint(fields=["user", "study"], name="unique_user_study")
        ]
        indexes = [
            models.Index(
                fields=["user", "study", "is_active"], name="idx_membership_user_study"
            ),
            models.Index(fields=["study", "is_active"], name="idx_membership_study"),
            models.Index(fields=["group"], name="idx_membership_group"),
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
            logger.debug(f"Added user {self.user.username} to group {self.group.name}")

            # Clear user permissions cache
            cache.delete(f"user_perms_{self.user.pk}")
            cache.delete(f"user_obj_{self.user.pk}")

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
            cache.delete(f"user_perms_{self.user.pk}")
            cache.delete(f"user_obj_{self.user.pk}")

            return True

        return False

    def sync_all_user_groups(self) -> Dict[str, int]:
        """
        Sync ALL user's groups based on active memberships
        OPTIMIZED: Uses bulk operations
        """
        if not self.user:
            return {"added": 0, "removed": 0}

        from django.db import transaction
        from backends.tenancy.utils.role_manager import StudyRoleManager

        with transaction.atomic():
            # Get all active study memberships for this user
            active_memberships = (
                StudyMembership.objects
                .filter(user=self.user, is_active=True)
                .select_related("group")
            )

            # Get groups user should have
            should_have_group_ids = {
                m.group.pk for m in active_memberships if m.group
            }

            # Get groups user currently has (study groups only)
            current_study_groups = self.user.groups.filter(
                name__startswith='Study '
            ).values_list('pk', flat=True)
            
            current_group_ids = set(current_study_groups)

            # Calculate changes
            to_add_ids = should_have_group_ids - current_group_ids
            to_remove_ids = current_group_ids - should_have_group_ids

            # 🔥 BULK OPERATIONS - Much faster!
            if to_add_ids:
                self.user.groups.add(*to_add_ids)
                
            if to_remove_ids:
                self.user.groups.remove(*to_remove_ids)

            # Clear cache once
            if to_add_ids or to_remove_ids:
                cache.delete_many([
                    f"user_perms_{self.user.pk}",
                    f"user_obj_{self.user.pk}",
                    f"user_groups_{self.user.pk}",
                ])

            return {
                "added": len(to_add_ids),
                "removed": len(to_remove_ids),
                "total_groups": len(should_have_group_ids),
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

    def get_role_info(self) -> Dict[str, Any]:
        """Get complete role information"""
        role_key = self.get_role_key()
        if not role_key:
            return {
                "role_key": None,
                "display_name": self.group.name if self.group else None,
                "group_id": self.group.pk if self.group else None,
            }

        from backends.tenancy.utils.role_manager import RoleTemplate

        config = RoleTemplate.get_role_config(role_key)
        if not config:
            return {"role_key": role_key}

        return {
            "role_key": role_key,
            "display_name": config.get("display_name"),
            "description": config.get("description"),
            "permissions": config.get("permissions", []),
            "is_privileged": config.get("is_privileged", False),
            "priority": config.get("priority", 0),
            "group_id": self.group.pk if self.group else None,
            "group_name": self.group.name if self.group else None,
        }

    def is_privileged_role(self) -> bool:
        """Check if this is a privileged role"""
        role_key = self.get_role_key()
        if not role_key:
            return False

        from backends.tenancy.utils.role_manager import RoleTemplate

        config = RoleTemplate.get_role_config(role_key)
        return config.get("is_privileged", False) if config else False

    def get_permissions(self, use_cache: bool = True) -> Set[str]:
        """Get all permission codenames"""
        if not self.group:
            return set()

        if use_cache:
            cache_key = f"membership_perms_{self.pk}"
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        study_code_lower = self.study.code.lower()
        app_label = f"study_{study_code_lower}"

        permissions = set()
        for perm in self.group.permissions.filter(
            content_type__app_label=app_label
        ).select_related("content_type"):
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
            parts = perm.split("_", 1)
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
                StudySite.objects.filter(study=self.study).values_list(
                    "site__code", flat=True
                )
            )

        return list(self.study_sites.values_list("site__code", flat=True))

    # ==========================================
    # VALIDATION
    # ==========================================

    def clean(self):
        """Validate membership data - OPTIMIZED"""
        super().clean()
        
        # Basic validation without queries
        if not self.user:
            raise ValidationError({'user': 'User is required'})
        
        if not self.study:
            raise ValidationError({'study': 'Study is required'})
        
        if not self.group:
            raise ValidationError({'group': 'Role group is required'})
        
        # Validate group format
        if self.group:
            from backends.tenancy.utils.role_manager import StudyRoleManager
            
            group_name = self.group.name
            study_code, role_key = StudyRoleManager.parse_group_name(group_name)
            
            if not role_key:
                raise ValidationError({
                    'group': 'Invalid group format. Must be a study role group.'
                })
            
            # ✅ Only validate if study is set and group doesn't match
            if self.study:
                expected_study_code = self.study.code
                
                if study_code != expected_study_code:
                    raise ValidationError({
                        'group': f"Group must belong to study '{expected_study_code}'. "
                                f"Expected format: 'Study {expected_study_code} - [Role Name]'"
                    })
        
        # Site validation - only check if object exists in DB
        if self.pk and self.can_access_all_sites:
            # ✅ Use exists() instead of fetching all
            if self.study_sites.exists():
                raise ValidationError(
                    "Cannot specify sites when 'can_access_all_sites' is True"
                )
                

    def save(self, *args, **kwargs):
        """Enhanced save with proper transaction handling"""
        from django.db import transaction
        
        self.full_clean()
        
        # Track changes BEFORE save (more efficient)
        is_new = self.pk is None
        group_changed = False
        was_active = None
        
        if not is_new:
            # Use __class__ to avoid extra query
            try:
                # Get only needed fields
                old_data = self.__class__.objects.filter(pk=self.pk).values(
                    'group_id', 'is_active'
                ).first()
                
                if old_data:
                    current_group_id = self.group.pk if self.group else None
                    group_changed = old_data['group_id'] != current_group_id
                    was_active = old_data['is_active']
            except Exception:
                pass
        
        # Wrap everything in transaction
        with transaction.atomic():
            # Save first
            super().save(*args, **kwargs)
            
            # Then sync (within same transaction)
            should_sync = (
                is_new or 
                group_changed or 
                (was_active is not None and was_active != self.is_active)
            )
            
            if should_sync:
                self.sync_user_to_group()
                
                # Clear relevant caches
                cache.delete_many([
                    f"membership_perms_{self.pk}",
                    f"perms_{self.user.pk}_{self.study.pk}",
                    f"sites_{self.user.pk}_{self.study.pk}",
                ])

    def refresh_permissions(self) -> int:
        """Refresh permissions for this membership's role"""
        from backends.tenancy.utils.role_manager import StudyRoleManager

        if not self.study:
            return 0

        try:
            result = StudyRoleManager.assign_permissions(self.study.code, force=True)

            cache.delete(f"membership_perms_{self.pk}")

            return result.get("permissions_assigned", 0)

        except Exception as e:
            logger.error(f"Error refreshing permissions: {e}")
            return 0

    def get_comparison_with_role(self, role_key: str) -> Dict[str, Any]:
        """Compare current permissions with another role"""
        from backends.tenancy.utils.role_manager import RoleTemplate

        current_role = self.get_role_key()
        current_config = (
            RoleTemplate.get_role_config(current_role) if current_role else None
        )
        if current_config is None:
            current_config = {}
        target_config = RoleTemplate.get_role_config(role_key)

        if not target_config:
            return {"error": f"Invalid role key: {role_key}"}

        current_perms = set(current_config.get("permissions", []))
        target_perms = set(target_config.get("permissions", []))

        return {
            "current_role": current_role,
            "current_display": current_config.get("display_name"),
            "target_role": role_key,
            "target_display": target_config.get("display_name"),
            "added_permissions": list(target_perms - current_perms),
            "removed_permissions": list(current_perms - target_perms),
            "same_permissions": list(current_perms & target_perms),
            "would_upgrade": target_config.get("priority", 0)
            > current_config.get("priority", 0),
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
