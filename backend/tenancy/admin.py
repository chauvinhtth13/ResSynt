# backend/tenancy/admin.py - FULL VERSION WITH AXES INTEGRATION
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from parler.admin import TranslatableAdmin
from django.contrib.admin import AdminSite
from django import forms
from django.utils.html import format_html
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse

# Import models from correct location
from .models import (
    Role, Permission, RolePermission, Study, Site, 
    StudySite, StudyMembership
)

# Get the User model
User = get_user_model()


# ============================================
# AXES FILTER
# ============================================
class AxesBlockedFilter(admin.SimpleListFilter):
    title = _('Axes Block Status')
    parameter_name = 'axes_blocked'
    
    def lookups(self, request, model_admin):
        return [
            ('blocked', 'Blocked'),
            ('has_attempts','Has Failed Attempts'),
            ('clean', 'No Failed Attempts'),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == 'blocked':
            # Filter users that are blocked
            blocked_users = []
            for user in queryset:
                if user.is_axes_blocked:
                    blocked_users.append(user.pk)
            return queryset.filter(pk__in=blocked_users)
            
        elif self.value() == 'has_attempts':
            # Users with failed attempts but not blocked
            has_attempts = []
            for user in queryset:
                if user.axes_failure_count > 0 and not user.is_axes_blocked:
                    has_attempts.append(user.pk)
            return queryset.filter(pk__in=has_attempts)
            
        elif self.value() == 'clean':
            # Users with no failed attempts
            clean_users = []
            for user in queryset:
                if user.axes_failure_count == 0:
                    clean_users.append(user.pk)
            return queryset.filter(pk__in=clean_users)
        
        return queryset


# ============================================
# USER ADMIN REGISTRATION
# ============================================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced User Admin with Axes Integration"""
    
    list_display = (
        'username', 'email', 'first_name', 'last_name', 
        'is_active', 'status', 'axes_status_display', 'axes_attempts_display',
        'last_login', 'date_joined'
    )
    
    list_filter = list(BaseUserAdmin.list_filter) + [
        'status',
        AxesBlockedFilter,
    ]
    
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    readonly_fields = list(BaseUserAdmin.readonly_fields) + [
        'axes_status_info', 'last_failed_login', 'failed_login_attempts',
        'created_at', 'updated_at', 'last_study_accessed', 'last_study_accessed_at'
    ]
    
    fieldsets = list(BaseUserAdmin.fieldsets) + [
        ('Security Status', {
            'fields': (
                'status', 'axes_status_info',
                'failed_login_attempts', 'last_failed_login',
                'must_change_password', 'password_changed_at'
            ),
            'classes': ('collapse',),
        }),
        ('Study Information', {
            'fields': (
                'last_study_accessed', 'last_study_accessed_at'
            ),
            'classes': ('collapse',),
        }),
        ('Additional Info', {
            'fields': (
                'notes', 'created_at', 'updated_at', 'created_by'
            ),
            'classes': ('collapse',),
        }),
    ]
    
    actions = ['activate_and_unblock', 'unblock_users', 'reset_login_attempts', 
               'force_password_change', 'sync_with_axes']
    
    def axes_status_display(self, obj):
        """Display axes block status with color coding"""
        is_blocked, reason, attempts = obj.get_axes_status()
        
        if is_blocked:
            return format_html(
                '<span style="color: red; font-weight: bold;">BLOCKED</span>'
            )
        elif attempts > 0:
            # Warning if has failed attempts but not blocked yet
            from axes.conf import settings as axes_settings
            limit = axes_settings.AXES_FAILURE_LIMIT
            color = 'orange' if attempts >= limit/2 else 'gray'
            return format_html(
                f'<span style="color: {color};">{attempts}/{limit}</span>'
            )
        else:
            return format_html(
                '<span style="color: green;">✓ OK</span>'
            )
    axes_status_display.short_description = 'Axes Status'  # type: ignore
    axes_status_display.admin_order_field = 'failed_login_attempts' # type: ignore
    
    def axes_attempts_display(self, obj):
        """Display failure attempts count"""
        _, _, attempts = obj.get_axes_status()
        if attempts > 0:
            from axes.conf import settings as axes_settings
            limit = axes_settings.AXES_FAILURE_LIMIT
            percentage = (attempts / limit) * 100
            
            # Color based on severity
            if percentage >= 100:
                color = 'red'
            elif percentage >= 75:
                color = 'orange'
            elif percentage >= 50:
                color = 'yellow'
            else:
                color = 'inherit'
                
            return format_html(
                f'<span style="color: {color}; font-weight: bold;">{attempts}</span>'
            )
        return '0'
    axes_attempts_display.short_description = 'Failed Attempts' # type: ignore
    
    def axes_status_info(self, obj):
        """Detailed axes status information for detail view"""
        if not obj.pk:
            return "Not available for new users"
            
        is_blocked, reason, attempts = obj.get_axes_status()
        
        html_parts = []
        
        # Block status
        if is_blocked:
            html_parts.append(
                f'<div style="padding: 10px; background: #ffebee; border: 1px solid #ef5350; border-radius: 4px;">'
                f'<strong style="color: #c62828;">🔒 Account is BLOCKED</strong><br/>'
                f'Reason: {reason or "Multiple failed login attempts"}<br/>'
                f'<a href="#" onclick="return confirm(\'Unblock this user?\') && '
                f'django.jQuery.post(\'{obj.pk}/unblock/\').done(function(){{location.reload();}});" '
                f'class="button" style="margin-top: 5px;">Unblock User</a>'
                f'</div>'
            )
        else:
            html_parts.append(
                '<div style="padding: 10px; background: #e8f5e9; border: 1px solid #66bb6a; border-radius: 4px;">'
                '<strong style="color: #2e7d32;">✓ Account is not blocked</strong>'
                '</div>'
            )
        
        # Attempts info
        from axes.conf import settings as axes_settings
        limit = axes_settings.AXES_FAILURE_LIMIT
        
        html_parts.append(
            f'<div style="margin-top: 10px;">'
            f'<strong>Failed Login Attempts:</strong> {attempts} / {limit}<br/>'
        )
        
        if attempts > 0:
            percentage = (attempts / limit) * 100
            bar_color = 'red' if percentage >= 80 else 'orange' if percentage >= 50 else 'green'
            html_parts.append(
                f'<div style="width: 200px; height: 20px; background: #e0e0e0; border-radius: 10px; margin-top: 5px;">'
                f'<div style="width: {min(percentage, 100)}%; height: 100%; background: {bar_color}; '
                f'border-radius: 10px;"></div>'
                f'</div>'
            )
        
        html_parts.append('</div>')
        
        # Recent failures
        from axes.models import AccessFailureLog
        recent_failures = AccessFailureLog.objects.filter(
            username=obj.username
        ).order_by('-attempt_time')[:5]
        
        if recent_failures:
            html_parts.append(
                '<div style="margin-top: 10px;">'
                '<strong>Recent Failed Attempts:</strong><br/>'
                '<ul style="margin: 5px 0;">'
            )
            for failure in recent_failures:
                html_parts.append(
                    f'<li>{failure.attempt_time.strftime("%Y-%m-%d %H:%M:%S")} - '
                    f'IP: {failure.ip_address}</li>'
                )
            html_parts.append('</ul></div>')
        
        return format_html(''.join(html_parts))
    axes_status_info.short_description = 'Axes Security Status' # type: ignore
    
    def save_model(self, request, obj, form, change):
        """Override to log status changes"""
        if change:
            old_obj = User.objects.get(pk=obj.pk)
            if old_obj.status != obj.status: # type: ignore
                # Status is changing
                if obj.status == User.Status.ACTIVE and old_obj.status == User.Status.BLOCKED: # type: ignore
                    messages.success(
                        request,
                        f"User {obj.username} has been unblocked (axes locks cleared)."
                    )
                elif obj.status == User.Status.BLOCKED: # type: ignore
                    messages.warning(
                        request,
                        f"User {obj.username} has been blocked."
                    )
        
        super().save_model(request, obj, form, change)
    
    @admin.action(description="Change status to ACTIVE and unblock")
    def activate_and_unblock(self, request, queryset):
        """Admin action to activate and unblock users"""
        count = 0
        for user in queryset:
            user.status = User.Status.ACTIVE # type: ignore
            user.save()  # This will auto-trigger axes unblock
            count += 1
        
        self.message_user(
            request,
            f"Successfully activated and unblocked {count} user(s).",
            messages.SUCCESS
        )
    
    def unblock_users(self, request, queryset):
        """Admin action to unblock selected users"""
        unblocked_count = 0
        failed_count = 0
        
        for user in queryset:
            if user.reset_axes_locks():
                unblocked_count += 1
                self.log_change(request, user, f"Unblocked user via admin action")
            else:
                failed_count += 1
        
        if unblocked_count:
            self.message_user(
                request,
                f"Successfully unblocked {unblocked_count} user(s).",
                messages.SUCCESS
            )
        
        if failed_count:
            self.message_user(
                request,
                f"Failed to unblock {failed_count} user(s). Check logs for details.",
                messages.ERROR
            )
    unblock_users.short_description = "Unblock selected users (Reset Axes locks)" # type: ignore
    
    def reset_login_attempts(self, request, queryset):
        """Reset failed login attempt counters"""
        for user in queryset:
            user.failed_login_attempts = 0
            user.last_failed_login = None
            user.save(update_fields=['failed_login_attempts', 'last_failed_login'])
            
            # Also reset axes
            user.reset_axes_locks()
        
        self.message_user(
            request,
            f"Reset login attempts for {queryset.count()} user(s).",
            messages.SUCCESS
        )
    reset_login_attempts.short_description = "Reset failed login attempts" # type: ignore
    
    def force_password_change(self, request, queryset):
        """Force users to change password on next login"""
        updated = queryset.update(must_change_password=True)
        self.message_user(
            request,
            f"Marked {updated} user(s) to change password on next login.",
            messages.SUCCESS
        )
    force_password_change.short_description = "Force password change on next login" # type: ignore
    
    def sync_with_axes(self, request, queryset):
        """Sync user status with axes status"""
        synced = 0
        for user in queryset:
            if user.sync_with_axes():
                synced += 1
        
        self.message_user(
            request,
            f"Synced {synced} user(s) with axes status.",
            messages.SUCCESS
        )
    sync_with_axes.short_description = "Sync status with axes" # type: ignore
    
    def get_urls(self):
        """Add custom URL for unblock action"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/unblock/',
                self.admin_site.admin_view(self.unblock_user_view),
                name='tenancy_user_unblock'
            ),
        ]
        return custom_urls + urls
    
    def unblock_user_view(self, request, object_id):
        """Handle AJAX unblock request"""
        try:
            user = self.get_object(request, object_id)
            if user and user.reset_axes_locks():
                self.log_change(request, user, "Unblocked user via quick action")
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Failed to unblock'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})


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

# class StudyMembershipInline(admin.TabularInline):
#     model = StudyMembership
#     extra = 0
#     verbose_name = "Study Membership"
#     verbose_name_plural = "Study Memberships"
#     readonly_fields = ('assigned_at',)
#     filter_horizontal = ('study_sites',)
#     autocomplete_fields = ['user', 'assigned_by', 'study_sites']

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