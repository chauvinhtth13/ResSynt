# backend/tenancy/admin.py - CLEANED VERSION WITHOUT USER STATUS
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

# Import models
from .models.user import User
from .models.study import Study, Site, StudySite
from .models.permission import Role, Permission, RolePermission, StudyMembership
from .models.audit import AuditLog

logger = logging.getLogger(__name__)

# ============================================
# USER ADMIN
# ============================================

class StudyMembershipInline(admin.TabularInline):
    """Inline display of user's study memberships with sorting and filtering"""
    model = StudyMembership
    fk_name = 'user'  # Specify which ForeignKey to use (user, not assigned_by)
    extra = 0
    can_delete = False
    fields = ('study', 'role', 'is_active', 'can_access_all_sites', 'get_sites_display_inline', 'assigned_at')
    readonly_fields = ('study', 'role', 'is_active', 'can_access_all_sites', 'get_sites_display_inline', 'assigned_at')
    ordering = ['study__code']
    
    def get_sites_display_inline(self, obj):
        """Display sites for inline"""
        if obj.can_access_all_sites or not obj.study_sites.exists():
            return "All Sites"
        return ", ".join([site.site.code for site in obj.study_sites.all()])
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

class UserAdminForm(forms.ModelForm):
    """Custom form for User admin"""
    
    class Meta:
        model = User
        fields = '__all__'

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced User Admin with Axes integration - Simplified"""
    
    form = UserAdminForm
    
    # Add the inline for study memberships
    inlines = [StudyMembershipInline]
    
    # List display configuration
    list_display = (
        'username',
        'email',
        'full_name_display',
        'is_active_status',
        'axes_status_display',
        'is_superuser',
        'last_login_display',
        'study_count',
        'created_at',
    )
    
    # FIXED: Removed 'status' from list_filter
    list_filter = (
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
        
        (_('Account Status'), {
            'fields': (
                'is_active',
                'axes_status_combined',
                'last_failed_login_readonly',
                'must_change_password',
                'password_changed_at',
                'notes',
            ),
            'description': 'Account status and security information. Uncheck "Active" to block user.'
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
        
        (_('Last Study Access'), {
            'fields': (
                'last_study_info',
            ),
        }),
        
        (_('Administrative Information'), {
            'fields': (
                'created_by_readonly',
                'last_login',
                'date_joined',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
            'description': 'Shows who created this account and when'
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
    )
    
    # Actions
    actions = [
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
    
    def is_active_status(self, obj):
        """Display user active status"""
        if obj.is_active:
            return "Active"
        else:
            # Check if blocked by axes
            if obj.is_axes_blocked:
                return "Blocked (Axes)"
            else:
                return "Blocked (Manual)"
    
    def axes_status_display(self, obj):
        """Display axes blocking status"""
        from axes.conf import settings as axes_settings
        is_blocked, reason, attempts = obj.get_axes_status()
        
        # Auto-sync if mismatch detected
        if is_blocked and obj.is_active:
            # Axes is blocking but user is active - auto update
            obj.is_active = False
            obj.save(update_fields=['is_active'])
        
        # Get the failure limit
        limit = axes_settings.AXES_FAILURE_LIMIT
        
        if is_blocked:
            return f"BLOCKED ({attempts}/{limit})"
        elif attempts > 0:
            return f"{attempts}/{limit}"
        else:
            return f"0/{limit}"
    
    def axes_status_combined(self, obj):
        """Combined axes status display - detailed view"""
        if not obj.pk:
            return "N/A"
        
        from axes.conf import settings as axes_settings
        is_blocked, reason, attempts = obj.get_axes_status()
        
        # Auto-update failed login attempts in model
        if obj.failed_login_attempts != attempts:
            obj.failed_login_attempts = attempts
            obj.save(update_fields=['failed_login_attempts'])
        
        limit = axes_settings.AXES_FAILURE_LIMIT
        
        if is_blocked:
            status_text = f"BLOCKED ({attempts}/{limit})"
            if reason:
                status_text += f"\n{reason}"
        elif attempts > 0:
            status_text = f"Failed Attempts: {attempts}/{limit}"
        else:
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
        """Display last failed login time"""
        if not obj.pk:
            return "Never"
        
        from axes.models import AccessFailureLog
        
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
        """Display which admin/staff user created this account"""
        if not obj.pk:
            return "System (Auto-created)"
        
        if obj.created_by:
            creator_name = obj.created_by.get_full_name() or obj.created_by.username
            if obj.created_by.is_superuser:
                return f"{creator_name} (Superuser)"
            elif obj.created_by.is_staff:
                return f"{creator_name} (Staff)"
            else:
                return f"{creator_name}"
        
        return "System (Auto-created)"
    
    def last_study_info(self, obj):
        """Display last accessed study with time"""
        if not obj.pk or not obj.last_study_accessed:
            return "No study accessed yet"
        
        study = obj.last_study_accessed
        study_info = f"Study Code: {study.code}"
        
        if obj.last_study_accessed_at:
            delta = timezone.now() - obj.last_study_accessed_at
            
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
    
    # -------------------------
    # Actions
    # -------------------------
    
    def activate_users(self, request, queryset):
        """Activate selected users and reset axes locks"""
        activated = 0
        
        for user in queryset:
            # Reset axes locks
            user.reset_axes_locks()
            
            # Activate user
            if not user.is_active:
                user.is_active = True
                user.failed_login_attempts = 0
                user.last_failed_login = None
                user.save()
                activated += 1
                
                self.log_change(request, user, "Activated user and reset axes locks")
        
        if activated:
            messages.success(
                request,
                f"Successfully activated {activated} user(s) and reset their axes locks."
            )
        else:
            messages.info(request, "Selected users were already active.")
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users (block them)"""
        count = 0
        for user in queryset.exclude(is_superuser=True):
            if user.is_active:
                user.block_user(reason=f"Manually blocked by {request.user.username}")
                count += 1
                self.log_change(request, user, "Deactivated user")
        
        if count:
            messages.success(request, f"Successfully deactivated {count} user(s).")
        else:
            messages.info(request, "No users were deactivated.")
    
    def reset_axes_locks(self, request, queryset):
        """Reset axes locks without changing user active status"""
        reset_count = 0
        
        for user in queryset:
            if user.reset_axes_locks():
                reset_count += 1
                self.log_change(request, user, "Reset axes locks")
        
        messages.success(request, f"Reset axes locks for {reset_count} user(s).")
    
    def sync_with_axes(self, request, queryset):
        """Sync user active status with axes status"""
        synced = 0
        deactivated = 0
        
        for user in queryset:
            is_blocked, reason, attempts = user.get_axes_status()
            
            # If axes is blocking but user is active
            if is_blocked and user.is_active:
                user.is_active = False
                user.save(update_fields=['is_active'])
                deactivated += 1
                synced += 1
                self.log_change(request, user, f"Deactivated due to axes: {reason}")
                
            # If user is blocked but axes is not blocking (manual block - keep it)
            elif not user.is_active and not is_blocked:
                messages.info(request, f"{user.username} is manually blocked (axes is clear)")
        
        if deactivated:
            messages.warning(request, f"Deactivated {deactivated} user(s) based on axes status.")
        if synced:
            messages.info(request, f"Synced {synced} user(s) with axes status.")
        
        if not synced:
            messages.info(request, "All users are already in sync with axes.")
    
    def force_sync_all_axes_status(self, request, queryset):
        """Force sync ALL users status with axes (including reactivating if axes is clear)"""
        synced = 0
        deactivated = 0
        reactivated = 0
        
        for user in queryset:
            is_blocked, reason, attempts = user.get_axes_status()
            changed = False
            
            # If axes is blocking, ensure user is deactivated
            if is_blocked:
                if user.is_active:
                    user.is_active = False
                    changed = True
                    deactivated += 1
                    
            # If axes is NOT blocking, ensure user is active (force clear)
            else:
                if not user.is_active:
                    user.is_active = True
                    changed = True
                    reactivated += 1
                    
            if changed:
                user.save(update_fields=['is_active'])
                synced += 1
                action = "deactivated by axes" if is_blocked else "reactivated (axes clear)"
                self.log_change(request, user, f"Force sync: {action}")
        
        if deactivated:
            messages.warning(request, f"Deactivated {deactivated} user(s) based on axes.")
        if reactivated:
            messages.success(request, f"Reactivated {reactivated} user(s) (axes is clear).")
        if not synced:
            messages.info(request, "All users already in sync with axes.")
        else:
            messages.info(request, f"Total synced: {synced} user(s)")
    
    # -------------------------
    # Save Methods
    # -------------------------
    
    def save_model(self, request, obj, form, change):
        """Override save to handle activation/deactivation properly"""
        
        # Set created_by for new users
        if not change and not obj.pk:
            if not obj.created_by:
                obj.created_by = request.user
        
        # Handle activation/deactivation for existing users
        if obj.pk:
            # Get the original object from database
            original = User.objects.get(pk=obj.pk)
            
            # Check if is_active is being changed from False to True (unblocking)
            if not original.is_active and obj.is_active:
                # User is being activated - need to reset axes locks
                obj.reset_axes_locks()
                obj.failed_login_attempts = 0
                obj.last_failed_login = None
                
                # Add note about manual unblock
                from django.utils import timezone
                timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                current_notes = obj.notes or ""
                obj.notes = f"{current_notes}\n[{timestamp}] Manually unblocked by {request.user.username}".strip()
                
                messages.success(
                    request,
                    f"User {obj.username} has been unblocked and axes locks have been reset."
                )
                logger.info(f"Admin {request.user.username} manually unblocked user {obj.username}")
                
            # Check if is_active is being changed from True to False (blocking)
            elif original.is_active and not obj.is_active:
                # User is being deactivated - add note
                from django.utils import timezone
                timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                current_notes = obj.notes or ""
                obj.notes = f"{current_notes}\n[{timestamp}] Manually blocked by {request.user.username}".strip()
                
                messages.warning(
                    request,
                    f"User {obj.username} has been blocked."
                )
                logger.info(f"Admin {request.user.username} manually blocked user {obj.username}")
            
            # Check axes status and warn if there's a mismatch
            else:
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
                
                # Warn if axes is blocking but user is active
                if is_blocked and obj.is_active:
                    messages.error(
                        request,
                        f"Warning: User {obj.username} is marked as active but axes is still blocking them. "
                        f"Use the 'Activate selected users' action to properly unblock."
                    )
        
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related and auto-sync axes status"""
        qs = super().get_queryset(request)
        qs = qs.select_related('last_study_accessed', 'created_by')
        
        # Auto-sync axes status for all users in list view
        if hasattr(request, 'resolver_match') and request.resolver_match:
            if request.resolver_match.url_name == 'tenancy_user_changelist':
                for user in qs:
                    is_blocked, _, _ = user.get_axes_status()
                    
                    # If axes is blocking but user is active, update it
                    if is_blocked and user.is_active:
                        User.objects.filter(pk=user.pk).update(is_active=False)
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
    """
    from django.utils import timezone
    
    if user and study:
        user.last_study_accessed = study
        user.last_study_accessed_at = timezone.now()
        user.save(update_fields=['last_study_accessed', 'last_study_accessed_at'])

# ============================================
# OTHER ADMIN REGISTRATIONS (unchanged)
# ============================================

class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0
    verbose_name = "Role Permission"
    verbose_name_plural = "Role Permissions"

class StudySiteInline(admin.TabularInline):
    model = StudySite
    extra = 0
    verbose_name = "Study-Site Link"
    verbose_name_plural = "Study-Site Links"
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'created_at', 'updated_at')
    search_fields = ('title', 'code')
    list_filter = ('created_at', 'updated_at')
    inlines = [RolePermissionInline]
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    list_select_related = True

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'created_at', 'updated_at')
    search_fields = ('code', 'name')
    list_filter = ('created_at', 'updated_at')
    inlines = [RolePermissionInline]
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    list_select_related = True

@admin.register(Study)
class StudyAdmin(TranslatableAdmin):
    list_display = ('code', 'name', 'status', 'db_name', 'created_at', 'updated_at', 'created_by')
    search_fields = ('code', 'translations__name', 'db_name')
    list_filter = ('status', 'created_at', 'updated_at')  # This status is Study.status, not User.status
    inlines = [StudySiteInline]
    readonly_fields = ('created_by','created_at', 'updated_at')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by or not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(StudySite)
class StudySiteAdmin(admin.ModelAdmin):
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

class StudySiteCodeChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        # Type assertion for Pylance
        from .models.study import StudySite
        if isinstance(obj, StudySite) and hasattr(obj, 'site') and hasattr(obj.site, 'code'):
            return f"{obj.site.code}"
        return str(obj)

class UserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        # Type assertion for Pylance - obj should be a User instance
        if not isinstance(obj, User):
            return str(obj)
            
        full_name = obj.get_full_name()
        if full_name:
            return f"{obj.username} ({full_name})"
        elif obj.email:
            return f"{obj.username} ({obj.email})"
        return obj.username

class StudyMembershipForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['can_access_all_sites'].initial = True

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
        return super().get_queryset(request).select_related(
            'user', 'study', 'role', 'assigned_by'
        ).prefetch_related('study_sites__site')