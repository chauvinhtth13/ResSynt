# backend/tenancy/admin.py - FULL VERSION WITH AXES INTEGRATION
import logging
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from parler.admin import TranslatableAdmin
from django import forms
from django.utils.html import format_html
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError

# Import the actual User model from your models
from .models.user import User
from .models.study import Study, Site, StudySite
from .models.permission import Role, Permission, RolePermission, StudyMembership
from .models.audit import AuditLog

logger = logging.getLogger(__name__)
# Don't override your custom User model that has the Status attribute


# ============================================
# USER ADMIN
# ============================================

class UserAdminForm(forms.ModelForm):
    """Custom form for User admin with validation"""
    
    class Meta:
        model = User
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        is_active = cleaned_data.get('is_active')
        
        # Ensure consistency between status and is_active
        if status == User.Status.BLOCKED and is_active:
            raise ValidationError("Blocked users cannot be active")
        
        return cleaned_data

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced User Admin with Axes integration"""
    
    form = UserAdminForm
    
    # List display configuration
    list_display = (
        'username',
        'email',
        'full_name_display',
        'status_display',
        'axes_status_display',
        'is_active',
        'is_superuser',
        'last_login_display',
        'study_count',
        'created_at',
    )
    
    list_filter = (
        'status',
        'is_active',
        'is_superuser',
        'is_staff',
        ('last_login', admin.DateFieldListFilter),
        ('created_at', admin.DateFieldListFilter),
        'groups',
    )
    
    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
    )
    
    ordering = ('-created_at',)
    
    # Fieldsets for detail view
    fieldsets = (
        # Basic Information
        (_('Authentication'), {
            'fields': ('username', 'password', 'email')
        }),
        
        (_('Personal Information'), {
            'fields': ('first_name', 'last_name')
        }),
        
        (_('Status & Security'), {
            'fields': (
                'status',
                'is_active',
                'axes_status_combined',
                'last_failed_login_readonly',
                'must_change_password',
                'password_changed_at',
            ),
            'description': 'Security status and axes integration information'
        }),
        
        (_('Permissions'), {
            'fields': (
                'is_superuser',
                'is_staff',
                'groups',
                'user_permissions',
            ),
            'classes': ('collapse',),
        }),
        
        (_('Study Access'), {
            'fields': (
                'last_study_info',
                'study_access_history',
            ),
        }),
        
        (_('Important Dates'), {
            'fields': (
                'last_login',
                'date_joined',
                'created_at',
                'updated_at',
                'created_by_readonly',
            ),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = (
        'axes_status_combined',
        'last_failed_login_readonly',
        'last_login',
        'date_joined',
        'created_at',
        'updated_at',
        'created_by_readonly',
        'password_changed_at',
        'last_study_info',
        'study_access_history',
    )
    
    # Actions
    actions = [
        'unblock_users',
        'block_users',
        'activate_users',
        'deactivate_users',
        'reset_axes_locks',
        'sync_with_axes',
        'force_sync_all_axes_status',
    ]
    
    # -------------------------
    # Display Methods
    # -------------------------
    
    def full_name_display(self, obj):
        """Display full name or username"""
        full_name = obj.get_full_name()
        return full_name if full_name else f"({obj.username})"
    
    def status_display(self, obj):
        """Display user status with axes sync"""
        # Auto-sync with axes if needed
        is_blocked, reason, attempts = obj.get_axes_status()
        
        # If axes is blocking but status is not BLOCKED, update it
        if is_blocked and obj.status != User.Status.BLOCKED:
            obj.status = User.Status.BLOCKED
            obj.is_active = False
            obj.save(update_fields=['status', 'is_active'])
            
        status_text = obj.get_status_display()
        
        # Add sync indicator if there's mismatch
        if obj.status == User.Status.BLOCKED and not is_blocked:
            status_text += " (manual)"
        elif is_blocked and obj.status == User.Status.BLOCKED:
            status_text += " (axes)"
            
        return status_text
    
    def axes_status_display(self, obj):
        """Display axes blocking status with auto-sync"""
        from axes.conf import settings as axes_settings
        is_blocked, reason, attempts = obj.get_axes_status()
        
        # Auto-sync if mismatch detected
        if is_blocked and obj.status != User.Status.BLOCKED:
            # Axes is blocking but status is not BLOCKED - auto update
            obj.status = User.Status.BLOCKED  
            obj.is_active = False
            obj.save(update_fields=['status', 'is_active'])
        
        # Get the failure limit
        limit = axes_settings.AXES_FAILURE_LIMIT
        
        if is_blocked:
            return f"BLOCKED ({attempts}/{limit})"
        elif attempts > 0:
            return f"{attempts}/{limit}"
        else:
            return f"0/{limit}"
    
    def axes_status_combined(self, obj):
        """Combined axes status display - all info in one field"""
        if not obj.pk:
            return "N/A"
        
        from axes.conf import settings as axes_settings
        is_blocked, reason, attempts = obj.get_axes_status()
        
        # Auto-update failed login attempts in model
        if obj.failed_login_attempts != attempts:
            obj.failed_login_attempts = attempts
            obj.save(update_fields=['failed_login_attempts'])
        
        # Get the failure limit from axes settings
        limit = axes_settings.AXES_FAILURE_LIMIT
        
        # Format the display
        if is_blocked:
            # BLOCKED status with attempts
            status_text = f"BLOCKED ({attempts}/{limit})"
            if reason:
                status_text += f"\n{reason}"
        elif attempts > 0:
            # Has attempts but not blocked yet
            status_text = f"Failed Attempts: {attempts}/{limit}"
        else:
            # Clear - no attempts
            status_text = f"Clear (0/{limit})"
        
        return status_text
    
    def last_login_display(self, obj):
        """Display last login with relative time"""
        if not obj.last_login:
            return "Never"
        
        delta = timezone.now() - obj.last_login
        if delta.days == 0:
            return "Today"
        elif delta.days == 1:
            return "Yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        else:
            return obj.last_login.strftime('%Y-%m-%d')
    
    def study_count(self, obj):
        """Count of active study memberships"""
        return obj.study_memberships.filter(is_active=True).count()
    
    def last_failed_login_readonly(self, obj):
        """Display last failed login time - auto-updated from axes"""
        if not obj.pk:
            return "Never"
        
        from axes.models import AccessFailureLog
        from django.utils import timezone
        
        # Get latest failure from axes
        latest_failure = AccessFailureLog.objects.filter(
            username=obj.username
        ).order_by('-attempt_time').first()
        
        if latest_failure:
            # Auto-update if different
            if obj.last_failed_login != latest_failure.attempt_time:
                obj.last_failed_login = latest_failure.attempt_time
                obj.save(update_fields=['last_failed_login'])
            
            # Format display
            delta = timezone.now() - latest_failure.attempt_time
            if delta.days == 0:
                if delta.seconds < 3600:
                    minutes = delta.seconds // 60
                    return f"{minutes} minutes ago" if minutes > 1 else "Just now"
                else:
                    hours = delta.seconds // 3600
                    return f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif delta.days == 1:
                return "Yesterday"
            elif delta.days < 7:
                return f"{delta.days} days ago"
            else:
                return latest_failure.attempt_time.strftime('%Y-%m-%d %H:%M')
        
        return "Never"
    
    def created_by_readonly(self, obj):
        """Display who created this user"""
        if not obj.pk:
            return "System"
        
        if obj.created_by:
            return f"{obj.created_by.get_full_name() or obj.created_by.username}"
        
        return "System"
    
    def last_study_info(self, obj):
        """Display last accessed study with time"""
        if not obj.pk or not obj.last_study_accessed:
            return "No study accessed yet"
        
        study = obj.last_study_accessed
        study_info = f"Study Code: {study.code}"
        
        if obj.last_study_accessed_at:
            from django.utils import timezone
            delta = timezone.now() - obj.last_study_accessed_at
            
            # Format time
            if delta.days == 0:
                if delta.seconds < 3600:
                    minutes = delta.seconds // 60
                    time_str = f"{minutes} minutes ago" if minutes > 1 else "Just now"
                else:
                    hours = delta.seconds // 3600
                    time_str = f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif delta.days == 1:
                time_str = "Yesterday"
            elif delta.days < 7:
                time_str = f"{delta.days} days ago"
            else:
                time_str = obj.last_study_accessed_at.strftime('%Y-%m-%d %H:%M')
            
            study_info += f"\nLast Access: {time_str}"
        
        return study_info
    
    def study_access_history(self, obj):
        """Display study access history and active memberships"""
        if not obj.pk:
            return "N/A"
        
        # Get all active study memberships
        memberships = obj.study_memberships.filter(
            is_active=True
        ).select_related('study', 'role').order_by('-assigned_at')
        
        if not memberships:
            return "No active study memberships"
        
        history = []
        for membership in memberships[:5]:  # Show last 5 active studies
            study_line = f"• {membership.study.code} - {membership.role.title}"
            
            # Add access time if this is the last accessed study
            if obj.last_study_accessed and membership.study.id == obj.last_study_accessed.id:
                study_line += " (Current)"
            
            # Add assignment date
            study_line += f" - Assigned: {membership.assigned_at.strftime('%Y-%m-%d')}"
            
            history.append(study_line)
        
        # Add count if more than 5
        total = memberships.count()
        if total > 5:
            history.append(f"... and {total - 5} more studies")
        
        return "\n".join(history)
    
    # -------------------------
    # Actions
    # -------------------------
    
    def unblock_users(self, request, queryset):
        """Unblock selected users (both status and axes)"""
        unblocked = 0
        failed = 0
        
        for user in queryset:
            try:
                # Unblock in axes
                user.reset_axes_locks()
                
                # Update status if blocked
                if user.status == User.Status.BLOCKED:
                    user.status = User.Status.ACTIVE
                
                # Ensure is_active
                user.is_active = True
                
                # Reset failed attempts
                user.failed_login_attempts = 0
                user.last_failed_login = None
                
                user.save()
                unblocked += 1
                
                # Log the action
                self.log_change(request, user, f"Unblocked user and reset axes locks")
                
            except Exception as e:
                failed += 1
                messages.error(request, f"Failed to unblock {user.username}: {str(e)}")
        
        if unblocked:
            messages.success(
                request,
                f"Successfully unblocked {unblocked} user(s) and reset their axes locks."
            )
        if failed:
            messages.error(request, f"Failed to unblock {failed} user(s).")
    
    def block_users(self, request, queryset):
        """Block selected users"""
        blocked = 0
        
        for user in queryset.exclude(is_superuser=True):
            user.block_user(reason=f"Manually blocked by {request.user.username}")
            blocked += 1
            self.log_change(request, user, "Blocked user")
        
        messages.success(request, f"Successfully blocked {blocked} user(s).")
    
    def activate_users(self, request, queryset):
        """Activate selected users"""
        count = queryset.update(
            status=User.Status.ACTIVE,
            is_active=True
        )
        messages.success(request, f"Successfully activated {count} user(s).")
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        count = queryset.exclude(is_superuser=True).update(
            status=User.Status.INACTIVE,
            is_active=False
        )
        messages.success(request, f"Successfully deactivated {count} user(s).")
        
    def reset_axes_locks(self, request, queryset):
        """Reset axes locks without changing user status"""
        reset_count = 0
        
        for user in queryset:
            if user.reset_axes_locks():
                reset_count += 1
                self.log_change(request, user, "Reset axes locks")
        
        messages.success(request, f"Reset axes locks for {reset_count} user(s).")
    
    def sync_with_axes(self, request, queryset):
        """Sync user status with axes status"""
        synced = 0
        blocked = 0
        cleared = 0
        
        for user in queryset:
            is_blocked, reason, attempts = user.get_axes_status()
            
            # If axes is blocking but user status is not BLOCKED
            if is_blocked and user.status != User.Status.BLOCKED:
                user.status = User.Status.BLOCKED
                user.is_active = False
                user.save(update_fields=['status', 'is_active'])
                blocked += 1
                synced += 1
                self.log_change(request, user, f"Status synced to BLOCKED (axes: {reason})")
                
            # If user is BLOCKED but axes is not blocking (manual block - keep it)
            elif user.status == User.Status.BLOCKED and not is_blocked:
                # Don't change manually blocked users
                messages.info(request, f"{user.username} is manually blocked (axes is clear)")
                
            # If both are clear
            elif not is_blocked and user.status == User.Status.ACTIVE:
                cleared += 1
        
        if blocked:
            messages.warning(request, f"Blocked {blocked} user(s) based on axes status.")
        if cleared:
            messages.success(request, f"{cleared} user(s) are clear and active.")
        if synced:
            messages.info(request, f"Synced {synced} user(s) with axes status.")
        
        if not synced and not cleared:
            messages.info(request, "All users are already in sync with axes.")
    
    def force_sync_all_axes_status(self, request, queryset):
        """Force sync ALL users status with axes (including clearing BLOCKED if axes is clear)"""
        synced = 0
        blocked = 0
        unblocked = 0
        
        for user in queryset:
            is_blocked, reason, attempts = user.get_axes_status()
            changed = False
            
            # If axes is blocking, ensure user is BLOCKED
            if is_blocked:
                if user.status != User.Status.BLOCKED:
                    user.status = User.Status.BLOCKED
                    user.is_active = False
                    changed = True
                    blocked += 1
                    
            # If axes is NOT blocking, ensure user is NOT BLOCKED (force clear)
            else:
                if user.status == User.Status.BLOCKED:
                    user.status = User.Status.ACTIVE
                    user.is_active = True
                    changed = True
                    unblocked += 1
                    
            if changed:
                user.save(update_fields=['status', 'is_active'])
                synced += 1
                action = "blocked by axes" if is_blocked else "unblocked (axes clear)"
                self.log_change(request, user, f"Force sync: {action}")
        
        if blocked:
            messages.warning(request, f"Blocked {blocked} user(s) based on axes.")
        if unblocked:
            messages.success(request, f"Unblocked {unblocked} user(s) (axes is clear).")
        if not synced:
            messages.info(request, "All users already in sync with axes.")
        else:
            messages.info(request, f"Total synced: {synced} user(s)")
        
    # -------------------------
    # Save Methods
    # -------------------------
    
    def save_model(self, request, obj, form, change):
        """Override save to auto-set created_by and handle axes sync"""
        
        # Set created_by for new users
        if not change and not obj.pk:  # Creating new user
            if not obj.created_by:
                obj.created_by = request.user
        
        # Check and sync with axes before saving
        if obj.pk:
            is_blocked, reason, attempts = obj.get_axes_status()
            
            # Update failed login attempts
            obj.failed_login_attempts = attempts
            
            # Get last failed login from axes
            from axes.models import AccessFailureLog
            latest_failure = AccessFailureLog.objects.filter(
                username=obj.username
            ).order_by('-attempt_time').first()
            
            if latest_failure:
                obj.last_failed_login = latest_failure.attempt_time
            
            # Sync status with axes if needed
            if is_blocked and obj.status != User.Status.BLOCKED:
                obj.status = User.Status.BLOCKED
                obj.is_active = False
                messages.warning(
                    request, 
                    f"User {obj.username} status set to BLOCKED due to axes lock"
                )
        
        super().save_model(request, obj, form, change)
    
    def save_formset(self, request, form, formset, change):
        """Set assigned_by for StudyMembership inline"""
        instances = formset.save(commit=False)
        
        for instance in instances:
            if not instance.pk:  # New membership
                instance.assigned_by = request.user
            instance.save()
        
        formset.save_m2m()
    
    def get_queryset(self, request):
        """Optimize queryset with select_related and auto-sync axes status"""
        qs = super().get_queryset(request)
        qs = qs.select_related('last_study_accessed', 'created_by')
        
        # Auto-sync axes status for all users in list view
        # This ensures status is always current with axes
        if hasattr(request, 'resolver_match') and request.resolver_match:
            if request.resolver_match.url_name == 'tenancy_user_changelist':
                for user in qs:
                    is_blocked, _, _ = user.get_axes_status()
                    
                    # If axes is blocking but status is not BLOCKED, update it
                    if is_blocked and user.status != User.Status.BLOCKED:
                        User.objects.filter(pk=user.pk).update(
                            status=User.Status.BLOCKED,
                            is_active=False
                        )
                        user.status = User.Status.BLOCKED
                        user.is_active = False
                        
        return qs
    
    # -------------------------
    # Permissions
    # -------------------------
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of superusers by non-superusers"""
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)
    
    def get_readonly_fields(self, request, obj=None):
        """Make username readonly for existing users"""
        readonly = list(self.readonly_fields)
        
        if obj:  # Editing existing user
            readonly.append('username')
            
            # Non-superusers cannot edit superuser status
            if not request.user.is_superuser:
                readonly.extend(['is_superuser', 'is_staff', 'user_permissions'])
        
        return tuple(readonly)

# ============================================
# MIDDLEWARE HOOK FOR AUTO-UPDATE
# ============================================

def update_user_study_access(user, study):
    """
    Helper function to update user's last study access.
    Call this from your middleware when user accesses a study.
    
    Usage in middleware:
        from backend.tenancy.admin import update_user_study_access
        update_user_study_access(request.user, study)
    """
    from django.utils import timezone
    
    if user and study:
        # Update last study access
        user.last_study_accessed = study
        user.last_study_accessed_at = timezone.now()
        user.save(update_fields=['last_study_accessed', 'last_study_accessed_at'])

# ============================================
# OTHER ADMIN REGISTRATIONS (không thay đổi)
# ============================================

# Inline for RolePermission in Role and Permission
class RolePermissionInline(admin.TabularInline):
    """Inline admin for RolePermission."""
    model = RolePermission
    extra = 0
    verbose_name = "Role Permission"
    verbose_name_plural = "Role Permissions"


# Inline for StudySite in Study and Site
class StudySiteInline(admin.TabularInline):
    """Inline admin for StudySite in Study and Site admin."""
    model = StudySite
    extra = 0
    verbose_name = "Study-Site Link"
    verbose_name_plural = "Study-Site Links"
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin for Role model."""
    list_display = ('title', 'code', 'created_at', 'updated_at')
    search_fields = ('title', 'code')
    list_filter = ('created_at', 'updated_at')
    inlines = [RolePermissionInline]
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    list_select_related = True

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Admin for Permission model."""
    list_display = ('code', 'name', 'created_at', 'updated_at')
    search_fields = ('code', 'name')
    list_filter = ('created_at', 'updated_at')
    inlines = [RolePermissionInline]
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    list_select_related = True

@admin.register(Study)
class StudyAdmin(TranslatableAdmin):
    """Admin for Study model."""
    list_display = ('code', 'name', 'status', 'db_name', 'created_at', 'updated_at', 'created_by')
    search_fields = ('code', 'translations__name', 'db_name')
    list_filter = ('status', 'created_at', 'updated_at')
    inlines = [StudySiteInline]
    readonly_fields = ('created_by','created_at', 'updated_at')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    def save_model(self, request, obj, form, change):
        # Robustly assign created_by only if not set or on creation
        if not obj.created_by or not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

# Register StudySite admin for autocomplete support
@admin.register(StudySite)
class StudySiteAdmin(admin.ModelAdmin):
    """Admin for StudySite model."""
    search_fields = ('site__code', 'site__name')
    list_display = ('site', 'study', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    autocomplete_fields = ['site', 'study']
    list_select_related = ('site', 'study')

@admin.register(Site)
class SiteAdmin(TranslatableAdmin):
    list_display = ('code', 'abbreviation', 'name', 'created_at', 'updated_at')
    search_fields = ('code', 'abbreviation', 'translations__name')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

# Custom ModelChoiceField to display study code
class StudyCodeChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.code # type: ignore[name-defined]

class StudySiteCodeChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.site.code}" # type: ignore[name-defined]

class UserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        full_name = obj.get_full_name() # type: ignore[name-defined]
        if full_name:
            return f"{obj.username} ({full_name})" # type: ignore[name-defined]
        elif obj.email: # type: ignore[name-defined]
            return f"{obj.username} ({obj.email})" # type: ignore[name-defined]
        return obj.username # type: ignore[name-defined]

class StudyMembershipForm(forms.ModelForm):
    """Custom form for StudyMembership to filter study_sites by selected study."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default: can_access_all_sites = True if creating new
        if not self.instance.pk:
            self.fields['can_access_all_sites'].initial = True

        # Filter study_sites by selected study
        study = None
        if self.instance and self.instance.pk and self.instance.study:
            study = self.instance.study
        elif 'study' in self.data:
            try:
                study_id = self.data.get('study')
                if study_id:
                    study = Study.objects.get(pk=study_id)
            except Exception:
                pass
        from django.forms.models import ModelMultipleChoiceField
        if isinstance(self.fields['study_sites'], ModelMultipleChoiceField):
            if study:
                self.fields['study_sites'].queryset = StudySite.objects.filter(study=study)
            else:
                self.fields['study_sites'].queryset = StudySite.objects.none()
    class Meta:
        model = StudyMembership
        fields = '__all__'
        widgets = {
            'study_sites': forms.CheckboxSelectMultiple,
        }

@admin.register(StudyMembership)
class StudyMembershipAdmin(admin.ModelAdmin):
    """Admin for StudyMembership with optimized UX and performance."""
    form = StudyMembershipForm
    list_display = ('get_user_display', 'get_study_code', 'get_sites_display', 'role', 'assigned_at', 'is_active', 'can_access_all_sites')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'study__code', 'role__title')
    list_filter = ('role', 'assigned_at', 'study', 'is_active', 'can_access_all_sites')
    readonly_fields = ('assigned_by','assigned_at')
    filter_horizontal = ('study_sites',)
    autocomplete_fields = ['user', 'assigned_by', 'role', 'study']
    ordering = ('-assigned_at',)
    date_hierarchy = 'assigned_at'

    def save_model(self, request, obj, form, change):
        # Robustly assign assigned_by only if not set or changed
        if not obj.assigned_by or not change:
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="User")
    def get_user_display(self, obj):
        user = obj.user
        full_name = user.get_full_name()
        if full_name:
            return f"{user.username} ({full_name})"
        return user.username

    @admin.display(description="Study Code")
    def get_study_code(self, obj):
        return obj.study.code

    @admin.display(description="Sites")
    def get_sites_display(self, obj):
        if obj.can_access_all_sites or not obj.study_sites.exists():
            return "All Sites"
        return ", ".join([site.site.code for site in obj.study_sites.all()])

    def get_queryset(self, request):
        # Optimize queryset for list display
        return super().get_queryset(request).select_related(
            'user', 'study', 'role', 'assigned_by'
        ).prefetch_related('study_sites__site')