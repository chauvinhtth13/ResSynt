# backend/tenancy/admin.py - COMPLETE WITHOUT CUSTOM PERMISSIONS
"""
Django Admin configuration for Tenancy app
Uses Django's built-in Groups instead of custom roles
"""
import logging
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from parler.admin import TranslatableAdmin
from django import forms
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Prefetch, Q, Count
from django.db import connections
from pathlib import Path

from django.core.management import call_command
from io import StringIO

from backends.tenancy.utils import DatabaseStudyCreator
from backends.tenancy.utils.role_manager import RoleTemplate

# Import models
from .models.user import User
from .models.study import Study, Site, StudySite
from .models.permission import StudyMembership

logger = logging.getLogger(__name__)


# ============================================
# INLINE ADMINS
# ============================================

class StudyMembershipInline(admin.TabularInline):
    """Inline display of user's study memberships"""
    model = StudyMembership
    fk_name = 'user'
    extra = 0
    can_delete = False
    fields = ('study', 'group', 'is_active', 'can_access_all_sites',
              'get_sites_display_inline', 'assigned_at')
    readonly_fields = ('study', 'group', 'is_active',
                       'can_access_all_sites', 'get_sites_display_inline', 'assigned_at')
    ordering = ['study__code']

    def get_sites_display_inline(self, obj):
        """Display sites for inline"""
        if not obj or not obj.pk:
            return "-"
        if obj.can_access_all_sites or not obj.study_sites.exists():
            return "All Sites"
        return ", ".join([site.site.code for site in obj.study_sites.all()])

    get_sites_display_inline.short_description = "Sites"

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class StudySiteInline(admin.TabularInline):
    model = StudySite
    extra = 0
    verbose_name = "Study-Site Link"
    verbose_name_plural = "Study-Site Links"
    readonly_fields = ('created_at', 'updated_at')
    
    class Media:
        js = ('js/admin/study_site_inline.js',)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Show all sites - JavaScript will handle duplicate prevention"""
        if db_field.name == "site":
            kwargs["queryset"] = Site.objects.all().order_by('code')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# ============================================
# USER ADMIN
# ============================================

class UserAdminForm(forms.ModelForm):
    """Custom form for User admin"""

    class Meta:
        model = User
        fields = '__all__'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced User Admin with Axes integration - Using Django Groups"""

    form = UserAdminForm
    inlines = [StudyMembershipInline]

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

    list_filter = (
        'is_active',
        'is_superuser',
        'is_staff',
        'groups',  # Django Groups
        ('last_login', admin.DateFieldListFilter),
        ('created_at', admin.DateFieldListFilter),
    )

    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
    )

    ordering = ('-created_at',)

    fieldsets = (
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
                'groups',  # Django Groups
                'user_permissions',  # Django Permissions
            ),
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

    actions = [
        'activate_users',
        'deactivate_users',
        'reset_axes_locks',
        'sync_user_groups_action'
    ]

    # -------------------------
    # Display Methods
    # -------------------------

    @admin.display(description="Full Name")
    def full_name_display(self, obj):
        """Display full name or username"""
        full_name = obj.get_full_name()
        return full_name if full_name else f"({obj.username})"

    @admin.display(description="Status")
    def is_active_status(self, obj):
        """Return user active status as a string."""
        return "Active" if obj.is_active else "Blocked (Axes)" if obj.is_axes_blocked else "Blocked (Manual)"

    @admin.display(description="Axes Status")
    def axes_status_display(self, obj):
        """Return axes blocking status as a string."""
        from axes.conf import settings as axes_settings
        is_blocked, _, attempts = obj.get_axes_status()
        limit = axes_settings.AXES_FAILURE_LIMIT

        status = "BLOCKED" if is_blocked else "Warning" if attempts > 0 else "Clear"
        return f"{status}: {attempts}/{limit}"

    @admin.display(description="Axes Status Detail")
    def axes_status_combined(self, obj):
        """Return combined axes status display as a string."""
        if not obj.pk:
            return "N/A"

        from axes.conf import settings as axes_settings
        is_blocked, reason, attempts = obj.get_axes_status()
        limit = axes_settings.AXES_FAILURE_LIMIT

        status = ("BLOCKED" if is_blocked else
                  "Failed Attempts" if attempts > 0 else
                  "Clear")
        result = f"{status} ({attempts}/{limit})"
        return result + (f"\nReason: {reason}" if is_blocked and reason else "")

    @admin.display(description="Last Login")
    def last_login_display(self, obj):
        """Return last login time as a relative string or date."""
        if not obj.last_login:
            return "Never"

        delta = timezone.now() - obj.last_login
        days = delta.days

        if days == 0:
            return "Today"
        if days == 1:
            return "Yesterday"
        if days < 7:
            return f"{days} days ago"
        if days < 30:
            return f"{days // 7} week{'s' if days // 7 > 1 else ''} ago"
        return obj.last_login.strftime("%Y-%m-%d")

    @admin.display(description="Studies")
    def study_count(self, obj):
        """Count of active study memberships"""
        return obj.study_memberships.filter(is_active=True).count()

    @admin.display(description="Last Failed Login")
    def last_failed_login_readonly(self, obj):
        """Display last failed login time"""
        if not obj.pk:
            return "Never"

        from axes.models import AccessFailureLog

        latest_failure = AccessFailureLog.objects.filter(
            username=obj.username
        ).order_by('-attempt_time').first()

        if latest_failure:
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

    @admin.display(description="Created By")
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

    @admin.display(description="Last Study Access")
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
                time_str = obj.last_study_accessed_at.strftime(
                    '%Y-%m-%d %H:%M')

            study_info += f"\nLast Access: {time_str}"

        return study_info

    # -------------------------
    # Actions
    # -------------------------

    @admin.action(description="Activate selected users")
    def activate_users(self, request, queryset):
        """Activate selected users and reset axes locks"""
        activated = 0

        for user in queryset:
            user.reset_axes_locks()

            if not user.is_active:
                user.is_active = True
                user.failed_login_attempts = 0
                user.last_failed_login = None
                user.save()
                activated += 1

                self.log_change(
                    request, user, "Activated user and reset axes locks")

        if activated:
            self.message_user(
                request,
                f"Successfully activated {activated} user(s) and reset their axes locks.",
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                "Selected users were already active.",
                messages.INFO
            )

    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        """Deactivate selected users (block them)"""
        count = 0
        for user in queryset.exclude(is_superuser=True):
            if user.is_active:
                user.block_user(
                    reason=f"Manually blocked by {request.user.username}")
                count += 1
                self.log_change(request, user, "Deactivated user")

        if count:
            self.message_user(
                request,
                f"Successfully deactivated {count} user(s).",
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                "No users were deactivated.",
                messages.INFO
            )

    @admin.action(description="Reset axes locks")
    def reset_axes_locks(self, request, queryset):
        """Reset axes locks without changing user active status"""
        reset_count = 0

        for user in queryset:
            if user.reset_axes_locks():
                reset_count += 1
                self.log_change(request, user, "Reset axes locks")

        self.message_user(
            request,
            f"Reset axes locks for {reset_count} user(s).",
            messages.SUCCESS
        )

    @admin.action(description="Sync Django Groups with Study Memberships")
    def sync_user_groups_action(self, request, queryset):
        """
        Sync selected users' Django Groups based on their active StudyMemberships

        This ensures that:
        - User.groups contains all groups from active StudyMemberships
        - User.groups doesn't contain groups from inactive/deleted memberships
        - Django's permission system reflects study role assignments
        """
        from backends.tenancy.utils.role_manager import StudyRoleManager

        total_stats = {
            'users_processed': 0,
            'users_changed': 0,
            'groups_added': 0,
            'groups_removed': 0,
        }

        for user in queryset:
            try:
                # Get active memberships
                active_memberships = user.study_memberships.filter(
                    is_active=True
                ).select_related('group')

                # Groups user should have
                should_have = set(
                    m.group for m in active_memberships if m.group)

                # Current study groups
                current_study = set()
                for group in user.groups.all():
                    if StudyRoleManager.is_study_group(group.name):
                        current_study.add(group)

                # Calculate changes
                to_add = should_have - current_study
                to_remove = current_study - should_have

                # Apply changes
                if to_add or to_remove:
                    for group in to_add:
                        user.groups.add(group)
                        total_stats['groups_added'] += 1

                    for group in to_remove:
                        user.groups.remove(group)
                        total_stats['groups_removed'] += 1

                    total_stats['users_changed'] += 1

                total_stats['users_processed'] += 1

            except Exception as e:
                self.message_user(
                    request,
                    f"Error syncing {user.username}: {str(e)}",
                    messages.ERROR
                )

        # Show summary
        if total_stats['users_changed'] > 0:
            self.message_user(
                request,
                f"Synced {total_stats['users_processed']} user(s): "
                f"Added {total_stats['groups_added']} groups, "
                f"Removed {total_stats['groups_removed']} groups",
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                f"All {total_stats['users_processed']} user(s) already in sync",
                messages.INFO
            )

    # -------------------------
    # Save Methods
    # -------------------------

    def save_model(self, request, obj, form, change):
        """Override save to handle activation/deactivation properly"""

        if not change and not obj.pk:
            if not obj.created_by:
                obj.created_by = request.user

        if obj.pk:
            original = User.objects.get(pk=obj.pk)

            if not original.is_active and obj.is_active:
                obj.reset_axes_locks()
                obj.failed_login_attempts = 0
                obj.last_failed_login = None

                timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                current_notes = obj.notes or ""
                obj.notes = f"{current_notes}\n[{timestamp}] Manually unblocked by {request.user.username}".strip(
                )

                self.message_user(
                    request,
                    f"User {obj.username} has been unblocked and axes locks have been reset.",
                    messages.SUCCESS
                )
                logger.debug(
                    f"Admin {request.user.username} manually unblocked user {obj.username}")

            elif original.is_active and not obj.is_active:
                timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                current_notes = obj.notes or ""
                obj.notes = f"{current_notes}\n[{timestamp}] Manually blocked by {request.user.username}".strip(
                )

                self.message_user(
                    request,
                    f"User {obj.username} has been blocked.",
                    messages.WARNING
                )
                logger.debug(
                    f"Admin {request.user.username} manually blocked user {obj.username}")

        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        """Optimized queryset"""
        qs = super().get_queryset(request)

        qs = qs.select_related('last_study_accessed', 'created_by')

        qs = qs.prefetch_related(
            Prefetch(
                'study_memberships',
                queryset=StudyMembership.objects.select_related(
                    'study', 'group').filter(is_active=True)
            )
        )

        qs = qs.annotate(
            _study_count=Count('study_memberships', filter=Q(
                study_memberships__is_active=True))
        )

        return qs

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of superusers by non-superusers"""
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        """Make username readonly for existing users"""
        readonly = list(self.readonly_fields)

        if obj:
            readonly.append('username')

            if not request.user.is_superuser:
                readonly.extend(
                    ['is_superuser', 'is_staff', 'user_permissions'])

        return tuple(readonly)


# ============================================
# STUDY ADMIN
# ============================================

@admin.register(Study)
class StudyAdmin(TranslatableAdmin):
    """Study Admin with auto database creation"""

    list_display = (
        'code',
        'name',
        'status',
        'db_name',
        'database_status',
        'folder_status',
        'created_at',
        'updated_at',
        'created_by'
    )

    search_fields = ('code', 'translations__name', 'db_name')
    list_filter = ('status', 'created_at', 'updated_at')
    inlines = [StudySiteInline]
    readonly_fields = ('created_by', 'created_at', 'updated_at',
                       'database_status_detail', 'db_name_display')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    actions = ['create_study_structures',
               'activate_studies', 'archive_studies']

    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'status'),
            'description': 'Study code will auto-generate the database name'
        }),
        ('Database Configuration', {
            'fields': ('db_name_display', 'database_status_detail'),
            'description': 'Database is automatically created when you save the study'
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """Make code readonly for existing objects"""
        readonly = list(self.readonly_fields)
        if obj:
            readonly.append('code')
        return tuple(readonly)

    @admin.display(description="Database Name")
    def db_name_display(self, obj):
        """Display the database name (auto-generated or existing)"""
        if obj and obj.pk:
            return obj.db_name
        elif obj and obj.code:
            return obj.generate_db_name()
        return "Will be auto-generated from study code"

    @admin.display(description="Database")
    def database_status(self, obj):
        """Quick database status for list view"""
        if not obj or not obj.db_name:
            return "Not created"

        exists = DatabaseStudyCreator.database_exists(obj.db_name)

        if exists:
        # Check if registered in Django
            from django.db import connections
            if obj.db_name in connections.databases:
                return "Active"
            else:
                return "Not Loaded (restart server)"
        else:
            return "Not Created"

    @admin.display(description="Folder")
    def folder_status(self, obj):
        """Check if folder structure exists"""
        if not obj or not obj.code:
            return "N/A"

        from django.conf import settings

        study_code_lower = obj.code.lower()
        study_folder = Path(settings.BASE_DIR) / 'backend' / \
            'studies' / f'study_{study_code_lower}'

        if study_folder.exists():
            required_files = [
                study_folder / 'apps.py',
                study_folder / 'models' / '__init__.py',
            ]

            if all(f.exists() for f in required_files):
                return "Complete"
            else:
                return "Incomplete"
        else:
            return "Missing"

    @admin.display(description="Database Status")
    def database_status_detail(self, obj):
        """Detailed database status for detail view"""
        if not obj or not obj.pk:
            return "Database will be created automatically when you save this study"

        exists = DatabaseStudyCreator.database_exists(obj.db_name)

        if exists:
            registered = obj.db_name in connections.databases
            
            status = f"Database '{obj.db_name}' exists\n"
            
            if registered:
                status += "Registered in Django\n"
                status += f"Ready to use!"
            else:
                status += "Not registered yet\n"
                status += "→ Reload: python manage.py reload_databases\n"
                status += "→ Or: Restart Django server"
            
            return status
        else:
            return (
                f"Database '{obj.db_name}' does not exist yet\n"
                f"→ Will be auto-created when you save this study"
            )

    @admin.action(description="Create folder structures")
    def create_study_structures(self, request, queryset):
        """Create folder structures for selected studies"""
        created = 0
        errors = 0
        
        for study in queryset:
            try:
                # Capture command output
                out = StringIO()
                
                # Call the management command
                call_command(
                    'create_study_structure',
                    study.code,
                    force=False,
                    stdout=out,
                    stderr=out
                )
                
                created += 1
                
                self.message_user(
                    request,
                    f"Created structure for {study.code}",
                    messages.SUCCESS
                )
                
            except Exception as e:
                errors += 1
                self.message_user(
                    request,
                    f"Error creating structure for {study.code}: {str(e)}",
                    messages.ERROR
                )
        
        # Summary message
        if created > 0:
            self.message_user(
                request,
                f"Created structures for {created} study/studies. Restart Django server to load them.",
                messages.WARNING
            )
        
        if errors > 0:
            self.message_user(
                request,
                f"Failed to create {errors} structure(s). Check logs for details.",
                messages.ERROR
            )

    @admin.action(description="Activate selected studies")
    def activate_studies(self, request, queryset):
        """Activate selected studies"""
        count = queryset.filter(status=Study.Status.ARCHIVED).update(
            status=Study.Status.ACTIVE)

        if count:
            self.message_user(
                request,
                f"Activated {count} study/studies. Restart server to load them.",
                messages.SUCCESS
            )
        else:
            self.message_user(
                request, "No studies were activated.", messages.INFO)

    @admin.action(description="Archive selected studies")
    def archive_studies(self, request, queryset):
        """Archive selected studies"""
        count = queryset.exclude(status=Study.Status.ARCHIVED).update(
            status=Study.Status.ARCHIVED)

        if count:
            self.message_user(
                request,
                f"Archived {count} study/studies. Restart server to unload them.",
                messages.WARNING
            )
        else:
            self.message_user(
                request, "No studies were archived.", messages.INFO)

    def save_model(self, request, obj, form, change):
        """Override save to auto-create database"""

        if not change and not obj.pk:
            if not obj.created_by:
                obj.created_by = request.user

        if not obj.db_name:
            obj.db_name = obj.generate_db_name()

        super().save_model(request, obj, form, change)

        db_exists = DatabaseStudyCreator.database_exists(obj.db_name)
        
        if not db_exists:
            self.message_user(
                request, f"Creating database '{obj.db_name}'...", messages.INFO)
            success, error = DatabaseStudyCreator.create_study_database(
                obj.db_name)

            if success:
                self.message_user(
                    request,
                    f"Database '{obj.db_name}' created successfully with 'data' schema!",
                    messages.SUCCESS
                )
            else:
                self.message_user(
                    request,
                    f"Failed to create database '{obj.db_name}': {error}",
                    messages.ERROR
                )
        else:
            self.message_user(
                request,
                f"Database '{obj.db_name}' already exists. No action taken.",
                messages.INFO
            )
            
    def save_formset(self, request, form, formset, change):
        """
        Validate no duplicate sites before saving
        This is the backend safety check
        """
        if formset.model == StudySite:
            instances = formset.save(commit=False)
            
            # Collect all site IDs from the formset
            site_ids = []
            for instance in instances:
                if instance.site_id:
                    if instance.site_id in site_ids:
                        # Duplicate found!
                        from django.contrib import messages
                        messages.error(
                            request,
                            f"Duplicate site detected: {instance.site.code}. "
                            f"Each site can only be added once per study."
                        )
                        return  # Don't save
                    site_ids.append(instance.site_id)
            
            # Check against existing saved sites
            if change and form.instance.pk:
                existing_site_ids = set(
                    StudySite.objects.filter(
                        study=form.instance
                    ).exclude(
                        id__in=[i.id for i in instances if i.id]
                    ).values_list('site_id', flat=True)
                )
                
                duplicates = set(site_ids) & existing_site_ids
                if duplicates:
                    duplicate_sites = Site.objects.filter(id__in=duplicates)
                    from django.contrib import messages
                    messages.error(
                        request,
                        f"Site(s) already exist in this study: "
                        f"{', '.join([s.code for s in duplicate_sites])}"
                    )
                    return  # Don't save
        
        # No duplicates, proceed with save
        super().save_formset(request, form, formset, change)


# ============================================
# SITE ADMIN
# ============================================

@admin.register(Site)
class SiteAdmin(TranslatableAdmin):
    """Site Admin"""

    list_display = ('code', 'abbreviation', 'name', 'created_at', 'updated_at')
    search_fields = ('code', 'abbreviation', 'translations__name')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('code',)


@admin.register(StudySite)
class StudySiteAdmin(admin.ModelAdmin):
    """StudySite Admin"""

    list_display = ('site', 'study', 'created_at', 'updated_at')
    search_fields = ('site__code', 'site__translations__name', 'study__code')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    autocomplete_fields = ['site', 'study']
    list_select_related = ('site', 'study')


# ============================================
# STUDY MEMBERSHIP ADMIN - UPDATED FOR ROLE SYSTEM
# ============================================

# backend/tenancy/admin.py

class StudyMembershipForm(forms.ModelForm):
    """
    Improved form with automatic group filtering and creation
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set default
        if not self.instance.pk:
            self.fields['can_access_all_sites'].initial = True

        # DEFENSIVE CHECK: Ensure group field exists before accessing
        if 'group' not in self.fields:
            # Group field not in form, skip group logic
            logger.warning("Group field not found in StudyMembershipForm")
        
        # Only handle group when editing existing instance
        elif self.instance.pk and self.instance.study:
            study = self.instance.study
            
            # Get study groups
            from backends.tenancy.utils.role_manager import StudyRoleManager, RoleTemplate
            study_groups = StudyRoleManager.get_study_groups(study.code)

            if not study_groups:
                # Auto-create groups if missing
                try:
                    created_groups = StudyRoleManager.create_study_groups(study.code)
                    study_groups = list(created_groups.values())

                    self.fields['group'].help_text = (
                        f"Created {len(created_groups)} default groups for study {study.code}."
                    )
                except Exception as e:
                    self.fields['group'].help_text = (
                        f"Error creating groups: {str(e)}. "
                        f"Please run 'python manage.py sync_study_roles --study {study.code}'"
                    )
                    study_groups = []

            # Filter to show only this study's groups
            group_ids = [g.id for g in study_groups]
            self.fields['group'].queryset = Group.objects.filter(
                id__in=group_ids
            ).order_by('name')

            # Help text with role descriptions
            role_descriptions = []
            for role_key in RoleTemplate.get_all_role_keys():
                info = RoleTemplate.get_role_config(role_key)
                role_descriptions.append(f"{info['display_name']}: {info['description']}")

            self.fields['group'].help_text = (
                f"Select a role for study {study.code}. " +
                " | ".join(role_descriptions)
            )
            
        elif self.instance.pk and not self.instance.study:
            # Edge case: has PK but no study
            self.fields['group'].queryset = Group.objects.none()
            self.fields['group'].help_text = "Please select a study first"
            
        elif 'group' in self.fields:  # DEFENSIVE CHECK
            # When creating new - disable group field
            self.fields['group'].queryset = Group.objects.none()
            self.fields['group'].required = False
            self.fields['group'].help_text = (
                "Role selection will be available after you save this membership. "
                "Please select user and study first, then click 'Save and continue editing'."
            )
        
        # Get study for site filtering
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

        # Filter sites by study
        if 'study_sites' in self.fields:  # DEFENSIVE CHECK
            if study:
                self.fields['study_sites'].queryset = StudySite.objects.filter(study=study)
            else:
                self.fields['study_sites'].queryset = StudySite.objects.none()

    def clean(self):
        """Enhanced validation"""
        cleaned_data = super().clean()
        study = cleaned_data.get('study')
        group = cleaned_data.get('group')

        # Skip group validation when creating new
        if not self.instance.pk:
            return cleaned_data

        # Validate group belongs to study (only when editing)
        if study and group:
            from backends.tenancy.utils.role_manager import StudyRoleManager

            study_code, role_name = StudyRoleManager.parse_group_name(group.name)

            if not study_code or study_code.upper() != study.code.upper():
                self.add_error('group',
                    f"Please select a role for study '{study.code}'. "
                    f"Current group '{group.name}' does not belong to this study."
                )

        return cleaned_data

    class Meta:
        model = StudyMembership
        fields = '__all__'
        widgets = {
            'study_sites': forms.CheckboxSelectMultiple,
        }


@admin.register(StudyMembership)
class StudyMembershipAdmin(admin.ModelAdmin):
    """
    Improved StudyMembership Admin with role system integration
    """

    form = StudyMembershipForm

    list_display = (
        'get_user_display',
        'get_study_code',
        'get_role_with_description',
        'get_sites_display',
        'assigned_at',
        'is_active',
        'can_access_all_sites'
    )

    list_filter = (
        'study',
        'is_active',
        'can_access_all_sites',
        'assigned_at',
    )

    search_fields = (
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'study__code',
        'group__name'
    )

    readonly_fields = ('assigned_by', 'assigned_at', 'updated_at', 'permission_preview')
    filter_horizontal = ('study_sites',)
    autocomplete_fields = ['user', 'assigned_by', 'study']
    ordering = ('-assigned_at',)
    date_hierarchy = 'assigned_at'

    def get_fieldsets(self, request, obj=None):
        """
        Dynamic fieldsets based on whether adding new or editing existing
        """
        if not obj:  # Adding new
            return (
                ('Step 1: Select User and Study', {
                    'fields': ('user', 'study'),
                    'description': (
                        'Note: Role selection will be available after you save. '
                        'Please click "Save and continue editing" after selecting user and study.'
                    )
                }),
                ('Site Access (Optional)', {
                    'fields': ('can_access_all_sites', 'study_sites'),
                    'classes': ('collapse',),
                }),
                ('Status and Notes (Optional)', {
                    'fields': ('is_active', 'notes'),
                    'classes': ('collapse',),
                }),
            )
        else:  # Editing existing
            return (
                ('User and Study', {
                    'fields': ('user', 'study', 'group'),
                    'description': 'Select user, study, and their role.'
                }),
                ('Permissions Preview', {
                    'fields': ('permission_preview',),
                    'description': 'Preview of permissions granted by this role'
                }),
                ('Site Access', {
                    'fields': ('can_access_all_sites', 'study_sites')
                }),
                ('Status and Notes', {
                    'fields': ('is_active', 'notes')
                }),
                ('Metadata', {
                    'fields': ('assigned_by', 'assigned_at', 'updated_at'),
                }),
            )

    def get_readonly_fields(self, request, obj=None):
        """Dynamic readonly fields"""
        if not obj:  # Adding new
            return ('assigned_by', 'assigned_at', 'updated_at')
        else:  # Editing existing
            return ('assigned_by', 'assigned_at', 'updated_at', 'permission_preview')
    
    def get_exclude(self, request, obj=None):
        """
        IMPORTANT: Exclude 'group' field when adding new
        This prevents KeyError in form __init__
        """
        if not obj:  # Adding new
            return ('group',)
        return None

    actions = ['sync_permissions_for_selected', 'activate_memberships',
               'deactivate_memberships', 'sync_users_to_groups']

    # ==========================================
    # Display Methods
    # ==========================================

    @admin.display(description="User")
    def get_user_display(self, obj):
        """Display user with full name"""
        user = obj.user
        full_name = user.get_full_name()
        if full_name:
            return f"{user.username} ({full_name})"
        return user.username

    @admin.display(description="Study")
    def get_study_code(self, obj):
        """Display study code"""
        return obj.study.code

    @admin.display(description="Role")
    def get_role_with_description(self, obj):
        """Display role with description"""
        if obj.group:
            from backends.tenancy.utils.role_manager import StudyRoleManager, RoleTemplate

            _, role_key = StudyRoleManager.parse_group_name(obj.group.name)
            if role_key:
                info = RoleTemplate.get_role_config(role_key)
                if info:
                    desc = info['description'][:30]
                    display_name = info['display_name']
                    return f"{display_name} ({desc}...)"
                return role_key
            return obj.group.name
        return "-"

    @admin.display(description="Sites")
    def get_sites_display(self, obj):
        """Display accessible sites"""
        return obj.get_sites_display()

    @admin.display(description="Permissions")
    def permission_preview(self, obj):
        """Show preview of permissions"""
        if not obj.pk or not obj.group:
            return "Save to see permissions"

        from backends.tenancy.utils.role_manager import StudyRoleManager

        perms = StudyRoleManager.get_group_permissions(obj.group)

        if not perms:
            return "No permissions assigned yet. Run: python manage.py sync_study_roles"

        # Group by model
        from collections import defaultdict
        grouped = defaultdict(list)

        for perm in sorted(perms):
            parts = perm.split('_', 1)
            if len(parts) == 2:
                action, model = parts
                grouped[model].append(action)

        # Format display
        lines = []
        for model, actions in sorted(grouped.items()):
            lines.append(f"{model.upper()}: {', '.join(sorted(actions))}")

        return "\n".join(lines) if lines else "No permissions"

    # ==========================================
    # Actions
    # ==========================================

    @admin.action(description="Sync permissions for selected memberships")
    def sync_permissions_for_selected(self, request, queryset):
        """Sync permissions for selected study memberships"""
        from backends.tenancy.utils.role_manager import StudyRoleManager

        study_codes = set(queryset.values_list('study__code', flat=True))

        synced = 0
        for study_code in study_codes:
            try:
                result = StudyRoleManager.assign_permissions(study_code, force=True)
                synced += result['groups_updated']
            except Exception as e:
                self.message_user(
                    request,
                    f"Error syncing {study_code}: {str(e)}",
                    messages.ERROR
                )

        if synced > 0:
            self.message_user(
                request,
                f"Successfully synced permissions for {synced} groups across {len(study_codes)} studies",
                messages.SUCCESS
            )

    @admin.action(description="Activate selected memberships")
    def activate_memberships(self, request, queryset):
        """Activate selected memberships"""
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            f"Activated {count} membership(s)",
            messages.SUCCESS
        )

    @admin.action(description="Deactivate selected memberships")
    def deactivate_memberships(self, request, queryset):
        """Deactivate selected memberships"""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            f"Deactivated {count} membership(s)",
            messages.SUCCESS
        )

    @admin.action(description="Sync Users to Groups")
    def sync_users_to_groups(self, request, queryset):
        """Sync selected memberships' users to their assigned groups"""
        synced = 0
        errors = 0

        for membership in queryset:
            try:
                if membership.sync_user_to_group():
                    synced += 1
            except Exception as e:
                errors += 1
                self.message_user(
                    request,
                    f"Error syncing {membership.user.username}: {str(e)}",
                    messages.ERROR
                )

        if synced > 0:
            self.message_user(
                request,
                f"Synced {synced} user(s) to their groups",
                messages.SUCCESS
            )

        if errors > 0:
            self.message_user(
                request,
                f"{errors} error(s) occurred during sync",
                messages.WARNING
            )

        if synced == 0 and errors == 0:
            self.message_user(
                request,
                "All users already synced to groups",
                messages.INFO
            )

    # ==========================================
    # Save Methods
    # ==========================================

    def save_model(self, request, obj, form, change):
        """Set assigned_by and ensure permissions are synced"""
        if not obj.assigned_by or not change:
            obj.assigned_by = request.user

        # BEST FIX: Check group_id instead of group (direct field access, no relation lookup)
        if not change and obj.study and not obj.group_id:
            from backends.tenancy.utils.role_manager import StudyRoleManager
            
            # Get first available group for this study as placeholder
            study_groups = StudyRoleManager.get_study_groups(obj.study.code)
            if study_groups:
                obj.group = study_groups[0]
                
                # Add note
                obj.notes = (obj.notes or "") + (
                    "\n[Auto-assigned temporary role. Please update role after saving.]"
                )
            else:
                # No groups available - create them
                try:
                    created_groups = StudyRoleManager.create_study_groups(obj.study.code)
                    if created_groups:
                        obj.group = list(created_groups.values())[0]
                        obj.notes = (obj.notes or "") + (
                            "\n[Auto-assigned temporary role. Please update role after saving.]"
                        )
                except Exception as e:
                    logger.error(f"Could not create groups for study {obj.study.code}: {e}")
                    self.message_user(
                        request,
                        f"Warning: Could not assign role. Please assign manually after saving.",
                        messages.WARNING
                    )

        super().save_model(request, obj, form, change)

        # Auto-sync permissions if this is a new membership
        if not change:
            from backends.tenancy.utils.role_manager import StudyRoleManager

            try:
                StudyRoleManager.assign_permissions(obj.study.code, force=False)
            except Exception as e:
                self.message_user(
                    request,
                    f"Membership saved but could not sync permissions: {str(e)}",
                    messages.WARNING
                )

    def response_add(self, request, obj, post_url_continue=None):
        """
        Override to redirect to change page after add
        """
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        # Check if user clicked "Save and continue editing"
        if "_continue" in request.POST:
            return super().response_add(request, obj, post_url_continue)
        
        # Check if user clicked "Save and add another"
        if "_addanother" in request.POST:
            return super().response_add(request, obj, post_url_continue)
        
        # Default "Save" button - redirect to change page
        self.message_user(
            request,
            f"Membership created. Please select a role for {obj.user.username} in study {obj.study.code}.",
            messages.SUCCESS
        )
        
        return HttpResponseRedirect(
            reverse('admin:tenancy_studymembership_change', args=[obj.pk])
        )

    def get_form(self, request, obj=None, **kwargs):
        """Override to ensure group is required only when editing"""
        form = super().get_form(request, obj, **kwargs)

        # Group handling is now done via get_exclude()
        # This ensures field doesn't exist when adding new
        if obj and 'group' in form.base_fields:
            # Editing - make group required
            form.base_fields['group'].required = True
            form.base_fields['group'].empty_label = None

        return form

    def get_queryset(self, request):
        """Optimized queryset"""
        return super().get_queryset(request).select_related(
            'user', 'study', 'group', 'assigned_by'
        ).prefetch_related('study_sites__site')