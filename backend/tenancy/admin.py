# backend/tenancy/admin.py - FULL VERSION WITH AXES INTEGRATION
import logging
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import path, reverse
from parler.admin import TranslatableAdmin
from django.contrib.admin import AdminSite
from django import forms
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.http import JsonResponse, HttpResponseRedirect

# Import models
from .models import (
    Role, Permission, RolePermission, Study, Site, 
    StudySite, StudyMembership
)

logger = logging.getLogger(__name__)
User = get_user_model()


# ============================================
# AXES BLOCKED FILTER
# ============================================
class AxesBlockedFilter(admin.SimpleListFilter):
    """Filter users by Axes block status"""
    
    title = 'Security Status'
    parameter_name = 'axes_status'
    
    def lookups(self, request, model_admin):
        """Return filter options"""
        return [
            ('blocked', 'Blocked'),
            ('has_attempts', 'Has Failed Attempts'),
            ('clean', 'Clean'),
        ]
    
    def queryset(self, request, queryset):
        """Filter queryset based on axes status"""
        value = self.value()
        
        if not value:
            return queryset
        
        filtered_ids = []
        
        for user in queryset:
            try:
                if hasattr(user, 'get_axes_status'):
                    is_blocked, _, attempts = user.get_axes_status()
                    
                    if value == 'blocked' and is_blocked:
                        filtered_ids.append(user.pk)
                    elif value == 'has_attempts' and attempts > 0 and not is_blocked:
                        filtered_ids.append(user.pk)
                    elif value == 'clean' and attempts == 0:
                        filtered_ids.append(user.pk)
                else:
                    if value == 'clean':
                        filtered_ids.append(user.pk)
                        
            except Exception as e:
                logger.debug(f"Error checking axes status for user {user.pk}: {e}")
                if value == 'clean':
                    filtered_ids.append(user.pk)
        
        return queryset.filter(pk__in=filtered_ids) if filtered_ids else queryset.none()


# ============================================
# USER ADMIN 
# ============================================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced User Admin with Axes Integration"""
    
    # List display configuration
    list_display = (
        'username', 'email', 'full_name_display', 
        'is_active', 'status', 'axes_status_text', 
        'last_login_display', 'date_joined'
    )
    
    # Filters
    list_filter = (
        'is_active', 'is_staff', 'is_superuser',
        'status', AxesBlockedFilter,
        'groups', 'date_joined', 'last_login'
    )
    
    # Search configuration
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    # Read-only fields
    readonly_fields = (
        'axes_status_display', 
        'axes_attempts_count',
        'last_failed_attempt',
        'axes_security_info',
        'created_at', 'updated_at', 'date_joined',
        'last_login', 'last_study_accessed', 'last_study_accessed_at'
    )
    
    # Fieldsets
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        (_('Personal info'), {
            'fields': ('first_name', 'last_name', 'email')
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Security Status'), {
            'fields': (
                'status', 
                'axes_status_display',
                'axes_attempts_count',
                'last_failed_attempt',
                'axes_security_info',
                'must_change_password', 
                'password_changed_at'
            ),
            'classes': ('collapse',),
        }),
        (_('Important dates'), {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')
        }),
        (_('Study Information'), {
            'fields': ('last_study_accessed', 'last_study_accessed_at'),
            'classes': ('collapse',),
        }),
        (_('Additional Info'), {
            'fields': ('notes', 'created_by'),
            'classes': ('collapse',),
        }),
    )
    
    # Admin actions
    actions = [
        'activate_and_unblock', 
        'unblock_users', 
        'reset_axes_attempts',
        'force_password_change',
        'export_security_report'
    ]
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('created_by', 'last_study_accessed')
    
    # ============================================
    # SIMPLE DISPLAY METHODS (NO COLORS/HTML)
    # ============================================
    
    @admin.display(description='Full Name')
    def full_name_display(self, obj):
        """Display full name or username"""
        return obj.get_full_name() or obj.username
    
    @admin.display(description='Security')
    def axes_status_text(self, obj):
        """Simple text for axes status in list view"""
        try:
            is_blocked, _, attempts = obj.get_axes_status()
            
            if is_blocked:
                return "BLOCKED"
            elif attempts > 0:
                from axes.conf import settings as axes_settings
                limit = axes_settings.AXES_FAILURE_LIMIT
                return f"{attempts}/{limit}"
            else:
                return "OK"
        except:
            return "-"
    
    @admin.display(description='Last Login')
    def last_login_display(self, obj):
        """Display last login in readable format"""
        if obj.last_login:
            delta = timezone.now() - obj.last_login
            if delta.days == 0:
                return "Today"
            elif delta.days == 1:
                return "Yesterday"
            elif delta.days < 30:
                return f"{delta.days} days ago"
            else:
                return obj.last_login.strftime("%Y-%m-%d")
        return "Never"
    
    # ============================================
    # DETAIL VIEW FIELDS (SIMPLE TEXT)
    # ============================================
    
    @admin.display(description='Axes Status')
    def axes_status_display(self, obj):
        """Current axes block status - simple text"""
        if not obj.pk:
            return "-"
        
        try:
            is_blocked, reason, _ = obj.get_axes_status()
            
            if is_blocked:
                return f"BLOCKED - {reason or 'Too many failed attempts'}"
            else:
                return "Not blocked"
        except Exception as e:
            logger.error(f"Error getting axes status: {e}")
            return "-"
    
    @admin.display(description='Failed Login Attempts')
    def axes_attempts_count(self, obj):
        """Current failed attempts from axes - simple text"""
        if not obj.pk:
            return "-"
        
        try:
            from axes.conf import settings as axes_settings
            _, _, attempts = obj.get_axes_status()
            limit = axes_settings.AXES_FAILURE_LIMIT
            
            return f"{attempts} / {limit}"
            
        except Exception as e:
            logger.error(f"Error getting attempts count: {e}")
            return "-"
    
    @admin.display(description='Last Failed Login')
    def last_failed_attempt(self, obj):
        """Get last failed login from axes logs - simple text"""
        if not obj.pk:
            return "-"
        
        try:
            from axes.models import AccessFailureLog
            
            last_failure = AccessFailureLog.objects.filter(
                username=obj.username
            ).order_by('-attempt_time').first()
            
            if last_failure:
                return f"{last_failure.attempt_time.strftime('%Y-%m-%d %H:%M')} (IP: {last_failure.ip_address})"
            
            return "No failed attempts"
            
        except Exception as e:
            logger.error(f"Error getting last failed attempt: {e}")
            return "-"
    
    @admin.display(description='Security Information')
    def axes_security_info(self, obj):
        """Security summary - simple text with unblock link"""
        if not obj.pk:
            return "-"
        
        try:
            from axes.conf import settings as axes_settings
            from axes.models import AccessFailureLog
            
            is_blocked, _, attempts = obj.get_axes_status()
            limit = axes_settings.AXES_FAILURE_LIMIT
            
            # Build simple info
            lines = []
            
            # Status with unblock link if needed
            if is_blocked:
                unblock_url = reverse('admin:tenancy_user_unblock', args=[obj.pk])
                lines.append(f'Status: BLOCKED - <a href="{unblock_url}">Unblock</a>')
            else:
                lines.append('Status: Active')
            
            # Attempts
            lines.append(f'Attempts: {attempts}/{limit}')
            
            # Recent failures
            recent_failures = AccessFailureLog.objects.filter(
                username=obj.username
            ).order_by('-attempt_time')[:3]
            
            if recent_failures:
                lines.append('Recent failures:')
                for failure in recent_failures:
                    lines.append(
                        f'- {failure.attempt_time.strftime("%Y-%m-%d %H:%M")} '
                        f'(IP: {failure.ip_address})'
                    )
            
            return mark_safe('<br>'.join(lines))
            
        except Exception as e:
            logger.error(f"Error getting security info: {e}")
            return "-"
    
    # ============================================
    # ADMIN ACTIONS
    # ============================================
    
    @admin.action(description="Activate and unblock selected users")
    def activate_and_unblock(self, request, queryset):
        """Activate users and clear axes blocks"""
        count = 0
        from backend.tenancy.models.user import User as UserModel
        
        for user in queryset:
            user.status = UserModel.Status.ACTIVE
            user.is_active = True
            user.save()
            if user.reset_axes_locks():
                count += 1
        
        self.message_user(
            request,
            f"Successfully activated and unblocked {count} user(s).",
            messages.SUCCESS
        )
    
    @admin.action(description="Unblock selected users")
    def unblock_users(self, request, queryset):
        """Clear axes blocks for selected users"""
        success_count = 0
        
        for user in queryset:
            if user.reset_axes_locks():
                success_count += 1
                self.log_change(request, user, "Unblocked via admin action")
        
        if success_count:
            self.message_user(
                request,
                f"Successfully unblocked {success_count} user(s).",
                messages.SUCCESS
            )
    
    @admin.action(description="Reset axes attempts")
    def reset_axes_attempts(self, request, queryset):
        """Reset axes attempts only"""
        count = 0
        from axes.utils import reset
        
        for user in queryset:
            try:
                reset(username=user.username)
                count += 1
            except Exception as e:
                logger.error(f"Error resetting axes for {user.username}: {e}")
        
        self.message_user(
            request,
            f"Reset axes attempts for {count} user(s).",
            messages.SUCCESS
        )
    
    @admin.action(description="Force password change")
    def force_password_change(self, request, queryset):
        """Mark users to change password"""
        updated = queryset.update(must_change_password=True)
        self.message_user(
            request,
            f"Marked {updated} user(s) for password change.",
            messages.SUCCESS
        )
    
    @admin.action(description="Export security report")
    def export_security_report(self, request, queryset):
        """Export security status as CSV"""
        import csv
        from django.http import HttpResponse
        from axes.models import AccessFailureLog
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="security_report_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Username', 'Email', 'Full Name', 'Status', 
            'Is Blocked', 'Failed Attempts', 'Last Failed Login', 
            'Last Successful Login', 'Date Joined'
        ])
        
        for user in queryset:
            is_blocked, _, attempts = user.get_axes_status()
            
            last_failure = AccessFailureLog.objects.filter(
                username=user.username
            ).order_by('-attempt_time').first()
            
            writer.writerow([
                user.username,
                user.email,
                user.get_full_name(),
                getattr(user, 'status', 'active'),
                'Yes' if is_blocked else 'No',
                attempts,
                last_failure.attempt_time.strftime("%Y-%m-%d %H:%M") if last_failure else 'Never',
                user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else 'Never',
                user.date_joined.strftime("%Y-%m-%d")
            ])
        
        return response
    
    # ============================================
    # CUSTOM VIEWS
    # ============================================
    
    def get_urls(self):
        """Add custom URL for unblock action"""
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
        """Handle unblock user request"""
        from backend.tenancy.models.user import User as UserModel
        
        try:
            user = self.get_object(request, object_id)
            if user:
                if user.reset_axes_locks():
                    if getattr(user, 'status', None) == UserModel.Status.BLOCKED:
                        user.status = UserModel.Status.ACTIVE
                        user.is_active = True
                        user.save()
                    
                    self.log_change(request, user, "Unblocked user")
                    messages.success(request, f"Successfully unblocked {user.username}")
                else:
                    messages.info(request, f"User {user.username} was not blocked")
            else:
                messages.error(request, "User not found")
                
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            logger.error(f"Error unblocking user {object_id}: {e}")
        
        return HttpResponseRedirect(f"../../{object_id}/change/")
    
    def save_model(self, request, obj, form, change):
        """Handle model save with axes sync"""
        from backend.tenancy.models.user import User as UserModel
        
        if change:
            try:
                old_obj = UserModel.objects.get(pk=obj.pk)
                
                if getattr(old_obj, 'status', None) != getattr(obj, 'status', None):
                    if getattr(obj, 'status', None) == UserModel.Status.ACTIVE and getattr(old_obj, 'status', None) == UserModel.Status.BLOCKED:
                        obj.reset_axes_locks()
                        messages.success(request, f"User {obj.username} activated and axes locks cleared.")
                    elif getattr(obj, 'status', None) == UserModel.Status.BLOCKED:
                        messages.warning(request, f"User {obj.username} has been blocked.")
                    
                    self.log_change(
                        request, obj, 
                        f"Status changed: {getattr(old_obj, 'status', 'unknown')} → {getattr(obj, 'status', 'unknown')}"
                    )
                    
            except UserModel.DoesNotExist:
                pass
        
        super().save_model(request, obj, form, change)

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