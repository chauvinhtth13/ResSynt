# backend/tenancy/admin.py
"""
Django Admin configuration for tenancy models
Optimized for administrator management and axes monitoring
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count, Q

from .models import User, Study, Site, StudySite, StudyMembership


# ==========================================
# USER ADMIN WITH AXES INTEGRATION
# ==========================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced User Admin with axes monitoring"""

    list_display = (
        'username',
        'is_active',
        'studies_count',
        'axes_status',
        'axes_attempts',
        'last_login',
    )

    list_filter = (
        'is_active',
        'is_staff',
        'is_superuser',
        'must_change_password',
        'groups',
        ('last_login', admin.DateFieldListFilter),
    )

    search_fields = ('username', 'email', 'first_name', 'last_name')

    fieldsets = (
        ('Basic Information', {
            'fields': ('username', 'email', 'first_name', 'last_name')
        }),
        ('Status', {
            'fields': ('is_active', 'must_change_password', 'is_staff', 'is_superuser')
        }),
        ('Security Information', {
            'fields': ('password', 'password_changed_at', 'last_login', 'date_joined'),
        }),
        ('Groups & Permissions', {
            'fields': ('groups', 'user_permissions'),
        }),
        ('Notes', {
            'fields': ('notes',),
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
        }),
    )

    readonly_fields = (
        'password_changed_at',
        'last_login',
        'date_joined',
        'created_at',
        'updated_at',
        'created_by'
    )

    actions = [
        'unblock_users',
        'block_users',
        'reset_axes_attempts',
        'force_password_change',
        'clear_user_cache',
    ]

    def get_queryset(self, request):
        """Force fresh data - no select_related cache"""
        qs = super().get_queryset(request)
        # Remove select_related to avoid stale cache
        return qs.annotate(
            active_memberships_count=Count(
                'study_memberships',
                filter=Q(study_memberships__is_active=True)
            )
        )

    def full_name(self, obj):
        """Display full name"""
        return obj.get_full_name()
    full_name.short_description = 'Full Name'

    def axes_status(self, obj):
        """Show axes lock status"""
        if not obj.is_active:
            return "INACTIVE"
        elif obj.is_axes_locked():
            return "BLOCKED"
        return "OK"
    axes_status.short_description = 'Status'

    def axes_attempts(self, obj):
        """Show failed attempts count"""
        from django.conf import settings
        
        try:
            attempts = obj.get_axes_attempts()
            limit = getattr(settings, 'AXES_FAILURE_LIMIT', 7)
            return f"{attempts}/{limit}"
        except Exception:
            return "-"
    axes_attempts.short_description = 'Attempts'

    @admin.action(description='Unblock and reset axes locks')
    def unblock_users(self, request, queryset):
        """Unblock users and reset their axes locks"""
        success = []
        
        for user in queryset:
            user.unblock_user()
            success.append(user.username)
        
        if success:
            self.message_user(
                request,
                f'Unblocked: {", ".join(success)}',
                level='SUCCESS'
            )

    @admin.action(description='Reset failed login attempts (axes)')
    def reset_axes_attempts(self, request, queryset):
        """Reset axes failed login attempts without changing user status"""
        success = []
        failed = []
        
        for user in queryset:
            if user.reset_axes_locks():
                success.append(user.username)
            else:
                failed.append(user.username)
        
        if success:
            self.message_user(
                request,
                f'Reset login attempts for: {", ".join(success)}',
                level='SUCCESS'
            )
        if failed:
            self.message_user(
                request,
                f'Failed to reset for: {", ".join(failed)}',
                level='ERROR'
            )

    @admin.action(description='Block users')  
    def block_users(self, request, queryset):
        """Block selected users"""
        success = []
        
        for user in queryset:
            user.block_user(
                reason="Blocked via admin action",
                blocked_by=request.user
            )
            success.append(user.username)
        
        if success:
            self.message_user(
                request,
                f'Blocked: {", ".join(success)}',
                level='WARNING'
            )

    def studies_count(self, obj):
        return obj.active_memberships_count
    studies_count.short_description = 'Studies'
    studies_count.admin_order_field = 'active_memberships_count'

    def clear_user_cache(self, request, queryset):
        """Clear cache for selected users"""
        from backends.tenancy.utils import TenancyUtils

        count = 0
        for user in queryset:
            TenancyUtils.clear_user_cache(user)
            count += 1

        self.message_user(request, f'Cleared cache for {count} users')
    clear_user_cache.short_description = 'Clear user cache'


# ==========================================
# STUDY SITE INLINE
# ==========================================

class StudySiteInline(admin.TabularInline):
    model = StudySite
    extra = 1
    fields = ('site', 'created_at')
    readonly_fields = ('created_at',)
    autocomplete_fields = ['site']
    verbose_name = 'Site'
    verbose_name_plural = 'Sites in this study'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('site')
    
# ==========================================
# STUDY ADMIN
# ==========================================

@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    """Study administration"""

    list_display = (
        'code',
        'name_display',
        'status',
        'users_count_display',
        'sites_count_display',
        'database_status',
        'created_at',
    )
    
    list_filter = (
        'status',
        ('created_at', admin.DateFieldListFilter),
    )
    
    search_fields = ('code', 'name_vi', 'name_en', 'db_name')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'status')
        }),
        ('Names', {
            'fields': ('name_vi', 'name_en')
        }),
        ('Database Information', {
            'fields': ('db_name', 'database_info'),
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = (
        'db_name',
        'database_info',
        'created_at',
        'updated_at',
        'created_by',
    )
    
    inlines = [StudySiteInline]
    
    actions = [
        'activate_studies',
        'archive_studies',
        'initialize_roles',
    ]
    
    ordering = ['code']  # Fix pagination warning
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('created_by').annotate(
            users_count=Count(
                'memberships', 
                filter=Q(memberships__is_active=True),
                distinct=True
            ),
            sites_count=Count('study_sites', distinct=True)
        )
    
    def name_display(self, obj):
        return obj.name
    name_display.short_description = 'Name'

    def users_count_display(self, obj):
        """Display users count"""
        return getattr(obj, 'users_count', 0)
    users_count_display.short_description = 'Users'
    users_count_display.admin_order_field = '_users_count'
    
    def sites_count_display(self, obj):
        """Display sites count"""
        return getattr(obj, 'sites_count', 0)
    sites_count_display.short_description = 'Sites'
    sites_count_display.admin_order_field = '_sites_count'

    def database_status(self, obj):
        """Check database status"""
        from backends.tenancy.utils.db_study_creator import DatabaseStudyCreator
        
        if DatabaseStudyCreator.database_exists(obj.db_name):
            return 'Study Database Exists'
        return 'Study Database Does Not Exist'
    database_status.short_description = 'DB Status'
    
    @admin.display(description="Database Information")
    def database_info(self, obj):
        """Show database information (plain text)."""
        from backends.tenancy.utils.db_study_creator import DatabaseStudyCreator

        info = DatabaseStudyCreator.get_database_info(obj.db_name)
        if not info:
            return "Database does not exist"

        size_human = info.get("size_human", "N/A")
        size_bytes = info.get("size_bytes")
        size_bytes_str = f"{size_bytes:,} B" if isinstance(size_bytes, int) else "N/A"

        connections = info.get("connections", "N/A")
        encoding = info.get("encoding", "N/A")
        collation = info.get("collation", "N/A")
        owner = info.get("owner", "N/A")
        schemas = len(info.get("schemas", []))

        return (
            f"Size: {size_human} ({size_bytes_str})\n"
            f"Connections: {connections}\n"
            f"Encoding: {encoding}\n"
            f"Collation: {collation}\n"
            f"Owner: {owner}\n"
            f"Schemas: {schemas}"
        )
    database_info.short_description = "Database Information"
    

    def activate_studies(self, request, queryset):
        count = queryset.update(status=Study.Status.ACTIVE)
        self.message_user(request, f'Activated {count} studies')
    activate_studies.short_description = 'Activate selected studies'
    
    def archive_studies(self, request, queryset):
        count = queryset.update(status=Study.Status.ARCHIVED)
        self.message_user(request, f'Archived {count} studies')
    archive_studies.short_description = 'Archive selected studies'

    def initialize_roles(self, request, queryset):
        """Initialize roles for selected studies"""
        from backends.tenancy.utils.role_manager import StudyRoleManager
        
        success_count = 0
        total_groups = 0
        total_perms = 0
        errors = []
        
        for study in queryset:
            result = StudyRoleManager.initialize_study(study.code, force=True)
            if 'error' in result:
                errors.append(f"{study.code}: {result['error']}")
            else:
                success_count += 1
                total_groups += result.get('groups_created', 0)
                total_perms += result.get('permissions_assigned', 0)
        
        if success_count > 0:
            self.message_user(
                request, 
                f'Initialized {success_count} studies: {total_groups} groups, {total_perms} permissions assigned'
            )
        
        if errors:
            self.message_user(
                request,
                f'Errors: {"; ".join(errors)}',
                level='error'
            )
    initialize_roles.short_description = 'Initialize roles and permissions'


# ==========================================
# SITE ADMIN
# ==========================================

@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    """Site administration"""
    
    list_display = (
        'code',
        'abbreviation',
        'name_display',
        'studies_count_display',
        'created_at',
    )
    
    list_filter = (
        ('created_at', admin.DateFieldListFilter),
    )
    
    search_fields = ('code', 'abbreviation', 'name_vi', 'name_en')

    fields = (
        'code',
        'abbreviation',
        'name_vi',
        'name_en',
        'created_by',
        'created_at',
        'updated_at',
    )
    
    readonly_fields = ('created_at', 'updated_at','created_by')
    
    def get_queryset(self, request):
        """Optimize queryset with ordering"""
        qs = super().get_queryset(request)
        return qs.annotate(
            study_count=Count('site_studies', distinct=True)
        ).order_by('code')  # Fix UnorderedObjectListWarning
    
    def studies_count_display(self, obj):
        """Show number of studies"""
        return obj.study_count or 0
    studies_count_display.short_description = 'Studies'

    def name_display(self, obj):
        return obj.name
    name_display.short_description = 'Name'

@admin.register(StudySite)
class StudySiteAdmin(admin.ModelAdmin):
    """Study-Site relationship management"""
    
    list_display = (
        'id',
        'study_code',
        'site_code',
        'site_abbreviation',
        'memberships_count',
        'created_at',
    )
    
    list_filter = ('study', 'site', 'created_at')
    
    search_fields = (
        'study__code',
        'site__code',
        'site__abbreviation',
    )
    
    autocomplete_fields = ['study', 'site']
    
    fields = (
        'study',
        'site',
        'created_by',
        'created_at',
        'updated_at',
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('study', 'site').annotate(
            memberships_count=Count('memberships')
        )
    
    def study_code(self, obj):
        return obj.study.code
    study_code.short_description = 'Study'
    study_code.admin_order_field = 'study__code'
    
    def site_code(self, obj):
        return obj.site.code
    site_code.short_description = 'Site'
    site_code.admin_order_field = 'site__code'
    
    def site_abbreviation(self, obj):
        return obj.site.abbreviation
    site_abbreviation.short_description = 'Abbr.'
    
    def memberships_count(self, obj):
        return getattr(obj, 'memberships_count', 0)
    memberships_count.short_description = 'Members'
    memberships_count.admin_order_field = 'memberships_count'

# ==========================================
# STUDY MEMBERSHIP ADMIN
# ==========================================

@admin.register(StudyMembership)
class StudyMembershipAdmin(admin.ModelAdmin):
    """Study membership administration"""
    
    list_display = (
        'user',
        'study',
        'role',
        'is_active',
        'sites_access',
        'assigned_at',
        'assigned_by',
    )
    
    list_filter = (
        'is_active',
        'study',
        'group',
        'can_access_all_sites',
        ('assigned_at', admin.DateFieldListFilter),
    )
    
    search_fields = (
        'user__username',
        'user__email',
        'study__code',
        'group__name',
    )
    
    fieldsets = (
        ('Basic Assignment', {
            'fields': ('user', 'study', 'group', 'is_active')
        }),
        ('Sites Access', {
            'fields': ('can_access_all_sites', 'study_sites')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('assigned_by', 'assigned_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('assigned_at', 'updated_at')
    
    autocomplete_fields = ['user', 'study', 'group', 'assigned_by']
    
    filter_horizontal = ('study_sites',)
    
    actions = [
        'activate_memberships',
        'deactivate_memberships',
        'grant_all_sites_access',
        'revoke_all_sites_access',
        'sync_user_groups',
    ]
    
    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related(
            'user',
            'study',
            'group',
            'assigned_by'
        ).prefetch_related('study_sites__site')
    
    def role(self, obj):
        """Show role name"""
        return obj.get_role_display_name() or '-'
    role.short_description = 'Role'
    
    def sites_access(self, obj):
        """Show sites access"""
        return obj.get_sites_display()
    sites_access.short_description = 'Sites'
    
    def activate_memberships(self, request, queryset):
        """Activate selected memberships"""
        count = queryset.update(is_active=True)
        
        # Sync groups
        users = set(m.user for m in queryset)
        from backends.tenancy.utils import TenancyUtils
        for user in users:
            TenancyUtils.sync_user_groups(user)
        
        self.message_user(request, f'Activated {count} memberships')
    activate_memberships.short_description = 'Activate selected'
    
    def deactivate_memberships(self, request, queryset):
        """Deactivate selected memberships"""
        count = queryset.update(is_active=False)
        
        # Sync groups
        users = set(m.user for m in queryset)
        from backends.tenancy.utils import TenancyUtils
        for user in users:
            TenancyUtils.sync_user_groups(user)
        
        self.message_user(request, f'Deactivated {count} memberships')
    deactivate_memberships.short_description = 'Deactivate selected'
    
    def grant_all_sites_access(self, request, queryset):
        count = queryset.update(can_access_all_sites=True)
        self.message_user(request, f'Granted all sites access to {count} memberships')
    grant_all_sites_access.short_description = 'Grant all sites access'
    
    def revoke_all_sites_access(self, request, queryset):
        count = queryset.update(can_access_all_sites=False)
        self.message_user(request, f'Revoked all sites access from {count} memberships')
    revoke_all_sites_access.short_description = 'Revoke all sites access'
    
    def sync_user_groups(self, request, queryset):
        users = set(m.user for m in queryset)
        from backends.tenancy.utils import TenancyUtils
        
        count = 0
        for user in users:
            result = TenancyUtils.sync_user_groups(user)
            if result.get('added', 0) > 0 or result.get('removed', 0) > 0:
                count += 1
        
        self.message_user(request, f'Synced groups for {count} users')
    sync_user_groups.short_description = 'Sync user groups'
