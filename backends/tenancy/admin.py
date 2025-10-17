# backend/tenancy/admin.py - COMPLETE OPTIMIZED VERSION
"""
Django Admin configuration for Tenancy app

FEATURES:
- Proper password management with Django's built-in forms
- Complete readonly fields review
- Optimized queries with select_related/prefetch_related
- Clean workflows for all models
- No emojis (Django default style)

FIXES:
- Password hashing for admin-created/changed users
- Readonly fields for all auto-managed timestamps
- Better UX for StudyMembership workflow
"""
import logging
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import (
    UserCreationForm,
    UserChangeForm,
    AdminPasswordChangeForm,
)
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from parler.admin import TranslatableAdmin
from django import forms
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Prefetch, Q, Count
from django.db import connections, transaction
from django.urls import reverse, path
from django.template.response import TemplateResponse
from pathlib import Path
from django.core.management import call_command
from io import StringIO

from backends.tenancy.utils import DatabaseStudyCreator
from backends.tenancy.utils.role_manager import RoleTemplate, StudyRoleManager

# Import models
from .models.user import User
from .models.study import Study, Site, StudySite
from .models.permission import StudyMembership

logger = logging.getLogger(__name__)


# ============================================
# HELPER FUNCTIONS
# ============================================


def get_time_display(dt):
    """
    Convert datetime to human-readable string

    Args:
        dt: datetime object or None

    Returns:
        Human-readable time string
    """
    if not dt:
        return "Never"

    delta = timezone.now() - dt
    days = delta.days
    seconds = delta.seconds

    if days == 0:
        if seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute(s) ago" if minutes > 1 else "Just now"
        else:
            hours = seconds // 3600
            return f"{hours} hour(s) ago"
    elif days == 1:
        return "Yesterday"
    elif days < 7:
        return f"{days} days ago"
    elif days < 30:
        weeks = days // 7
        return f"{weeks} week(s) ago"
    else:
        return dt.strftime("%Y-%m-%d")


def get_axes_status_display(user):
    """
    Get Axes status display for user

    Args:
        user: User instance

    Returns:
        Status string with format "Status (attempts/limit)"
    """
    from axes.conf import settings as axes_settings

    is_blocked, reason, attempts = user.get_axes_status()
    limit = axes_settings.AXES_FAILURE_LIMIT

    if is_blocked:
        return f"BLOCKED ({attempts}/{limit})"
    elif attempts > 0:
        return f"Warning ({attempts}/{limit})"
    else:
        return f"Clear (0/{limit})"


# ============================================
# CUSTOM FORMS FOR USER ADMIN
# ============================================


class CustomUserCreationForm(UserCreationForm):
    """
    Form for creating new users in admin
    Properly handles password hashing and required fields
    """

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make email required
        self.fields["email"].required = True

        # Customize help text
        self.fields["password1"].help_text = _(
            "Enter a strong password with at least 8 characters"
        )
        self.fields["username"].help_text = _(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        )

    def save(self, commit=True):
        """Save user with hashed password and timestamp"""
        user = super().save(commit=False)

        # Set password_changed_at to now
        user.password_changed_at = timezone.now()

        # Admin-created users don't need to change password
        user.must_change_password = True

        if commit:
            user.save()

        return user


class CustomUserChangeForm(UserChangeForm):
    """
    Form for changing existing users in admin
    Uses Django's password widget (shows hash, links to change form)
    """

    class Meta:
        model = User
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


# ============================================
# INLINE ADMINS
# ============================================


class StudyMembershipInline(admin.TabularInline):
    """Inline display of user's study memberships"""

    model = StudyMembership
    fk_name = "user"
    extra = 0
    can_delete = False

    fields = (
        "study",
        "group",
        "is_active",
        "can_access_all_sites",
        "get_sites_display_inline",
        "assigned_at",
    )

    readonly_fields = (
        "study",
        "group",
        "is_active",
        "can_access_all_sites",
        "get_sites_display_inline",
        "assigned_at",
    )

    ordering = ["study__code"]

    @admin.display(description="Sites")
    def get_sites_display_inline(self, obj):
        """Display sites for inline"""
        if not obj or not obj.pk:
            return "-"
        return obj.get_sites_display()

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class StudySiteInline(admin.TabularInline):
    """Inline for Study-Site links"""

    model = StudySite
    extra = 1
    verbose_name = "Study-Site Link"
    verbose_name_plural = "Study-Site Links"
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ["site"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Optimize site queryset"""
        if db_field.name == "site":
            kwargs["queryset"] = Site.objects.all().order_by("code")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ============================================
# USER ADMIN - WITH PROPER PASSWORD MANAGEMENT
# ============================================


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Enhanced User Admin with proper password management

    FEATURES:
    - Proper password hashing using Django's built-in forms
    - Axes integration for security
    - Study membership tracking
    - Optimized queries
    """

    # Use custom forms that handle passwords correctly
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    change_password_form = AdminPasswordChangeForm

    inlines = [StudyMembershipInline]

    # -------------------------
    # List Display
    # -------------------------

    list_display = (
        "username",
        "email",
        "full_name_display",
        "status_display",
        "axes_status_display",
        "is_superuser",
        "last_login_display",
        "study_count_display",
        "created_at",
    )

    list_filter = (
        "is_active",
        "is_superuser",
        "is_staff",
        "groups",
        ("last_login", admin.DateFieldListFilter),
        ("created_at", admin.DateFieldListFilter),
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
    )

    ordering = ("-created_at",)

    # -------------------------
    # Fieldsets
    # -------------------------

    # Fieldset for ADDING new user
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                ),
                "description": "Create a new user account. Password will be hashed automatically.",
            },
        ),
        (
            _("Personal Information"),
            {
                "fields": ("first_name", "last_name"),
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
    )

    # Fieldset for EDITING existing user
    fieldsets = (
        (
            _("Authentication"),
            {
                "fields": ("username", "password", "email"),
                "description": _(
                    'Password is stored as a hash. Click the "Change password" link below to update it.'
                ),
            },
        ),
        (_("Personal Information"), {"fields": ("first_name", "last_name")}),
        (
            _("Account Status"),
            {
                "fields": (
                    "is_active",
                    "axes_status_detail",
                    "last_failed_login_display",
                    "must_change_password",
                    "password_changed_at_display",
                    "notes",
                ),
                "description": _(
                    'Uncheck "Active" to block the user. '
                    "Use the actions below to reset Axes locks."
                ),
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_superuser",
                    "is_staff",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Study Access"),
            {
                "fields": ("last_study_display",),
                "classes": ("collapse",),
            },
        ),
        (
            _("Administrative"),
            {
                "fields": (
                    "created_by_display",
                    "last_login_display_detail",
                    "date_joined_display",
                    "created_at_display",
                    "updated_at_display",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    # Complete readonly fields
    readonly_fields = (
        # Axes and security
        "axes_status_detail",
        "last_failed_login_display",
        # Password tracking
        "password_changed_at_display",
        # Django managed fields
        "last_login_display_detail",
        "date_joined_display",
        # Auto timestamps
        "created_at_display",
        "updated_at_display",
        # Administrative
        "created_by_display",
        "last_study_display",
    )

    actions = [
        "activate_users",
        "deactivate_users",
        "reset_axes_locks",
        "sync_user_groups_action",
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
    def status_display(self, obj):
        """Display user status"""
        if obj.is_active:
            return "Active"
        elif obj.is_axes_blocked:
            return "Blocked (Axes)"
        else:
            return "Blocked (Manual)"

    @admin.display(description="Axes Status")
    def axes_status_display(self, obj):
        """Display Axes status"""
        return get_axes_status_display(obj)

    @admin.display(description="Axes Status Detail")
    def axes_status_detail(self, obj):
        """Display detailed Axes status"""
        if not obj.pk:
            return "N/A"

        from axes.conf import settings as axes_settings

        is_blocked, reason, attempts = obj.get_axes_status()
        limit = axes_settings.AXES_FAILURE_LIMIT

        lines = [f"Status: {'BLOCKED' if is_blocked else 'Clear'}"]
        lines.append(f"Failed Attempts: {attempts}/{limit}")

        if is_blocked and reason:
            lines.append(f"Reason: {reason}")

        return "\n".join(lines)

    @admin.display(description="Last Login")
    def last_login_display(self, obj):
        """Display last login time (for list view)"""
        return get_time_display(obj.last_login)

    @admin.display(description="Last Login")
    def last_login_display_detail(self, obj):
        """Display last login time (for detail view)"""
        if not obj.last_login:
            return "Never logged in"

        return f"{obj.last_login.strftime('%Y-%m-%d %H:%M:%S')} ({get_time_display(obj.last_login)})"

    @admin.display(description="Date Joined")
    def date_joined_display(self, obj):
        """Display date joined"""
        if not obj.date_joined:
            return "N/A"
        return f"{obj.date_joined.strftime('%Y-%m-%d %H:%M:%S')} ({get_time_display(obj.date_joined)})"

    @admin.display(description="Created At")
    def created_at_display(self, obj):
        """Display created at"""
        if not obj.created_at:
            return "N/A"
        return f"{obj.created_at.strftime('%Y-%m-%d %H:%M:%S')} ({get_time_display(obj.created_at)})"

    @admin.display(description="Updated At")
    def updated_at_display(self, obj):
        """Display updated at"""
        if not obj.updated_at:
            return "N/A"
        return f"{obj.updated_at.strftime('%Y-%m-%d %H:%M:%S')} ({get_time_display(obj.updated_at)})"

    @admin.display(description="Password Changed At")
    def password_changed_at_display(self, obj):
        """Display when password was last changed"""
        if not obj.password_changed_at:
            return "Never changed (using initial password)"

        return f"{obj.password_changed_at.strftime('%Y-%m-%d %H:%M:%S')} ({get_time_display(obj.password_changed_at)})"

    @admin.display(description="Last Failed Login")
    def last_failed_login_display(self, obj):
        """Display last failed login time"""
        if not obj.pk:
            return "Never"

        from axes.models import AccessFailureLog

        latest = (
            AccessFailureLog.objects.filter(username=obj.username)
            .order_by("-attempt_time")
            .first()
        )

        if latest:
            return get_time_display(latest.attempt_time)

        return "Never"

    @admin.display(description="Studies")
    def study_count_display(self, obj):
        """Display study count"""
        if hasattr(obj, "_study_count"):
            return obj._study_count
        return obj.study_memberships.filter(is_active=True).count()

    @admin.display(description="Created By")
    def created_by_display(self, obj):
        """Display creator"""
        if not obj.pk:
            return "System"

        if obj.created_by:
            creator = obj.created_by
            name = creator.get_full_name() or creator.username

            if creator.is_superuser:
                return f"{name} (Superuser)"
            elif creator.is_staff:
                return f"{name} (Staff)"
            else:
                return name

        return "System"

    @admin.display(description="Last Study Access")
    def last_study_display(self, obj):
        """Display last study access"""
        if not obj.pk or not obj.last_study_accessed:
            return "No study accessed"

        study = obj.last_study_accessed
        lines = [f"Study: {study.code}"]

        if obj.last_study_accessed_at:
            time_str = get_time_display(obj.last_study_accessed_at)
            lines.append(f"Accessed: {time_str}")

        return "\n".join(lines)

    # -------------------------
    # Actions
    # -------------------------

    @admin.action(description="Activate selected users")
    def activate_users(self, request, queryset):
        """Activate selected users and reset Axes locks"""
        activated = 0

        for user in queryset:
            if not user.is_active:
                user.reset_axes_locks()

                user.is_active = True
                user.failed_login_attempts = 0
                user.last_failed_login = None
                user.save(
                    update_fields=[
                        "is_active",
                        "failed_login_attempts",
                        "last_failed_login",
                    ]
                )

                activated += 1

                self.log_change(request, user, "Activated user and reset Axes locks")

        if activated:
            self.message_user(
                request, f"Successfully activated {activated} user(s)", messages.SUCCESS
            )
        else:
            self.message_user(
                request, "Selected users were already active", messages.INFO
            )

    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        users = queryset.exclude(is_superuser=True)
        count = 0

        for user in users:
            if user.is_active:
                reason = f"Manually blocked by {request.user.username}"
                user.block_user(reason=reason)
                count += 1

                self.log_change(request, user, "Deactivated user")

        if count:
            self.message_user(
                request, f"Successfully deactivated {count} user(s)", messages.SUCCESS
            )
        else:
            self.message_user(request, "No users were deactivated", messages.INFO)

    @admin.action(description="Reset Axes locks")
    def reset_axes_locks(self, request, queryset):
        """Reset Axes locks without changing active status"""
        reset_count = 0

        for user in queryset:
            if user.reset_axes_locks():
                reset_count += 1
                self.log_change(request, user, "Reset Axes locks")

        self.message_user(
            request, f"Reset Axes locks for {reset_count} user(s)", messages.SUCCESS
        )

    @admin.action(description="Sync Django Groups")
    def sync_user_groups_action(self, request, queryset):
        """Sync Django Groups based on StudyMemberships"""
        total_added = 0
        total_removed = 0
        users_changed = 0

        for user in queryset:
            try:
                memberships = user.study_memberships.filter(
                    is_active=True
                ).select_related("group")

                if memberships.exists():
                    result = memberships.first().sync_all_user_groups()

                    if result["added"] > 0 or result["removed"] > 0:
                        users_changed += 1
                        total_added += result["added"]
                        total_removed += result["removed"]

            except Exception as e:
                self.message_user(
                    request, f"Error syncing {user.username}: {str(e)}", messages.ERROR
                )

        if users_changed > 0:
            self.message_user(
                request,
                f"Synced {users_changed} user(s): "
                f"Added {total_added} groups, Removed {total_removed} groups",
                messages.SUCCESS,
            )
        else:
            self.message_user(request, "All users already in sync", messages.INFO)

    # -------------------------
    # Custom URLs for password change
    # -------------------------

    def get_urls(self):
        """Add password change URL"""
        urls = super().get_urls()
        custom_urls = [
            path(
                "<id>/password/",
                self.admin_site.admin_view(self.user_change_password),
                name="auth_user_password_change",
            ),
        ]
        return custom_urls + urls

    def user_change_password(self, request, id, form_url=""):
        """Handle password change for a user"""
        user = self.get_object(request, id)

        if not self.has_change_permission(request, user):
            raise PermissionDenied

        if user is None:
            raise Http404

        if request.method == "POST":
            form = self.change_password_form(user, request.POST)

            if form.is_valid():
                form.save()

                # Update password_changed_at
                User.objects.filter(pk=user.pk).update(
                    password_changed_at=timezone.now()
                )

                change_message = self.construct_change_message(request, form, None)
                self.log_change(request, user, change_message)

                msg = _("Password changed successfully.")
                messages.success(request, msg)

                return HttpResponseRedirect(
                    reverse(
                        f"{self.admin_site.name}:tenancy_user_change",
                        args=(user.pk,),
                    )
                )
        else:
            form = self.change_password_form(user)

        fieldsets = [(None, {"fields": list(form.base_fields)})]
        adminForm = admin.helpers.AdminForm(form, fieldsets, {})

        context = {
            "title": _("Change password: %s") % user.username,
            "adminForm": adminForm,
            "form_url": form_url,
            "form": form,
            "is_popup": False,
            "add": False,
            "change": False,
            "has_delete_permission": False,
            "has_change_permission": True,
            "has_absolute_url": False,
            "opts": self.model._meta,
            "original": user,
            "save_as": False,
            "show_save": True,
        }

        return TemplateResponse(
            request,
            "admin/auth/user/change_password.html",
            context,
        )

    # -------------------------
    # Save/Query Optimization
    # -------------------------

    def save_model(self, request, obj, form, change):
        """Handle activation/deactivation and set creator"""

        # Set creator for new users
        if not change:
            if not obj.created_by:
                obj.created_by = request.user

            # For new users, password_changed_at is set in form.save()

        # Handle activation/deactivation
        if change and obj.pk:
            try:
                original = User.objects.only("is_active").get(pk=obj.pk)

                # Activating user
                if not original.is_active and obj.is_active:
                    obj.reset_axes_locks()
                    obj.failed_login_attempts = 0
                    obj.last_failed_login = None

                    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                    note = f"\n[{timestamp}] Unblocked by {request.user.username}"
                    obj.notes = (obj.notes or "") + note

                    self.message_user(
                        request,
                        f"User {obj.username} has been activated",
                        messages.SUCCESS,
                    )

                # Deactivating user
                elif original.is_active and not obj.is_active:
                    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                    note = f"\n[{timestamp}] Blocked by {request.user.username}"
                    obj.notes = (obj.notes or "") + note

                    self.message_user(
                        request,
                        f"User {obj.username} has been deactivated",
                        messages.WARNING,
                    )

            except User.DoesNotExist:
                pass

        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        """Optimize queryset with proper prefetching"""
        qs = super().get_queryset(request)

        qs = qs.select_related("last_study_accessed", "created_by")

        qs = qs.prefetch_related(
            Prefetch(
                "study_memberships",
                queryset=StudyMembership.objects.select_related(
                    "study", "group"
                ).filter(is_active=True),
            )
        )

        qs = qs.annotate(
            _study_count=Count(
                "study_memberships", filter=Q(study_memberships__is_active=True)
            )
        )

        return qs

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of superusers"""
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        """Make username readonly for existing users"""
        readonly = list(self.readonly_fields)

        if obj:
            readonly.append("username")

            if not request.user.is_superuser:
                readonly.extend(["is_superuser", "is_staff", "user_permissions"])

        return tuple(readonly)


# ============================================
# STUDY ADMIN
# ============================================


@admin.register(Study)
class StudyAdmin(TranslatableAdmin):
    """Study Admin with database management"""

    list_display = (
        "code",
        "name",
        "status",
        "db_name",
        "database_status_display",
        "folder_status_display",
        "created_at",
    )

    search_fields = ("code", "translations__name", "db_name")
    list_filter = ("status", "created_at")
    inlines = [StudySiteInline]

    readonly_fields = (
        "created_by",
        "created_at",
        "updated_at",
        "database_status_detail",
        "db_name_readonly",
    )

    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    actions = ["create_study_structures", "activate_studies", "archive_studies"]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("code", "name", "status"),
                "description": "Study code auto-generates database name",
            },
        ),
        (
            "Database",
            {
                "fields": ("db_name_readonly", "database_status_detail"),
                "description": "Database is auto-created when study is saved",
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    # -------------------------
    # Display Methods
    # -------------------------

    @admin.display(description="Database Name")
    def db_name_readonly(self, obj):
        """Display database name"""
        if obj and obj.pk:
            return obj.db_name
        elif obj and obj.code:
            return obj.generate_db_name()
        return "Auto-generated from code"

    @admin.display(description="Database")
    def database_status_display(self, obj):
        """Database status for list view"""
        if not obj or not obj.db_name:
            return "Not created"

        exists = DatabaseStudyCreator.database_exists(obj.db_name)

        if exists:
            if obj.db_name in connections.databases:
                return "Active"
            else:
                return "Not loaded (restart server)"
        else:
            return "Not created"

    @admin.display(description="Folder")
    def folder_status_display(self, obj):
        """Folder status for list view"""
        if not obj or not obj.code:
            return "N/A"

        from django.conf import settings

        study_folder = (
            Path(settings.BASE_DIR)
            / "backend"
            / "studies"
            / f"study_{obj.code.lower()}"
        )

        if not study_folder.exists():
            return "Missing"

        # Check required files
        required = [
            study_folder / "apps.py",
            study_folder / "models" / "__init__.py",
        ]

        if all(f.exists() for f in required):
            return "Complete"
        else:
            return "Incomplete"

    @admin.display(description="Database Status")
    def database_status_detail(self, obj):
        """Detailed database status"""
        if not obj or not obj.pk:
            return "Database will be auto-created when you save"

        exists = DatabaseStudyCreator.database_exists(obj.db_name)

        if exists:
            registered = obj.db_name in connections.databases

            lines = [f"Database: {obj.db_name} (exists)"]

            if registered:
                lines.append("Status: Registered and ready")
            else:
                lines.append("Status: Not registered")
                lines.append("Action: Restart Django server")

            return "\n".join(lines)
        else:
            return f"Database '{obj.db_name}' will be created on save"

    # -------------------------
    # Actions
    # -------------------------

    @admin.action(description="Create folder structures")
    def create_study_structures(self, request, queryset):
        """Create folder structures for studies"""
        created = 0
        errors = 0

        for study in queryset:
            try:
                out = StringIO()

                call_command(
                    "create_study_structure",
                    study.code,
                    force=False,
                    stdout=out,
                    stderr=out,
                )

                created += 1

            except Exception as e:
                errors += 1
                self.message_user(
                    request, f"Error for {study.code}: {str(e)}", messages.ERROR
                )

        if created > 0:
            self.message_user(
                request,
                f"Created {created} structure(s). Restart server to load.",
                messages.SUCCESS,
            )

        if errors > 0:
            self.message_user(request, f"Failed {errors} structure(s)", messages.ERROR)

    @admin.action(description="Activate studies")
    def activate_studies(self, request, queryset):
        """Activate studies"""
        count = queryset.filter(status=Study.Status.ARCHIVED).update(
            status=Study.Status.ACTIVE
        )

        if count:
            self.message_user(
                request, f"Activated {count} study/studies", messages.SUCCESS
            )
        else:
            self.message_user(request, "No studies activated", messages.INFO)

    @admin.action(description="Archive studies")
    def archive_studies(self, request, queryset):
        """Archive studies"""
        count = queryset.exclude(status=Study.Status.ARCHIVED).update(
            status=Study.Status.ARCHIVED
        )

        if count:
            self.message_user(
                request, f"Archived {count} study/studies", messages.SUCCESS
            )
        else:
            self.message_user(request, "No studies archived", messages.INFO)

    # -------------------------
    # Save Methods
    # -------------------------

    def save_model(self, request, obj, form, change):
        """Handle database creation"""

        # Set creator
        if not change:
            if not obj.created_by:
                obj.created_by = request.user

        # Generate db_name
        if not obj.db_name:
            obj.db_name = obj.generate_db_name()

        super().save_model(request, obj, form, change)

        # Check/create database
        exists = DatabaseStudyCreator.database_exists(obj.db_name)

        if not exists:
            self.message_user(
                request, f"Creating database '{obj.db_name}'...", messages.INFO
            )

            success, error = DatabaseStudyCreator.create_study_database(obj.db_name)

            if success:
                self.message_user(
                    request,
                    f"Database '{obj.db_name}' created successfully",
                    messages.SUCCESS,
                )
            else:
                self.message_user(
                    request, f"Failed to create database: {error}", messages.ERROR
                )
        else:
            self.message_user(
                request, f"Database '{obj.db_name}' already exists", messages.INFO
            )

    def get_readonly_fields(self, request, obj=None):
        """Make code readonly for existing studies"""
        readonly = list(self.readonly_fields)
        if obj:
            readonly.append("code")
        return tuple(readonly)

    def save_formset(self, request, form, formset, change):
        """Validate no duplicate sites"""
        if formset.model == StudySite:
            instances = formset.save(commit=False)

            # Check for duplicates
            site_ids = [i.site_id for i in instances if i.site_id]

            if len(site_ids) != len(set(site_ids)):
                self.message_user(
                    request,
                    "Duplicate sites detected. Each site can only be added once.",
                    messages.ERROR,
                )
                return

            # Check against existing
            if change and form.instance.pk:
                existing = set(
                    StudySite.objects.filter(study=form.instance)
                    .exclude(id__in=[i.id for i in instances if i.id])
                    .values_list("site_id", flat=True)
                )

                duplicates = set(site_ids) & existing

                if duplicates:
                    dup_sites = Site.objects.filter(id__in=duplicates)
                    self.message_user(
                        request,
                        f"Sites already exist: {', '.join([s.code for s in dup_sites])}",
                        messages.ERROR,
                    )
                    return

        super().save_formset(request, form, formset, change)


# ============================================
# SITE ADMIN
# ============================================


@admin.register(Site)
class SiteAdmin(TranslatableAdmin):
    """Site Admin"""

    list_display = ("code", "abbreviation", "name", "created_at")
    search_fields = ("code", "abbreviation", "translations__name")
    list_filter = ("created_at",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("code",)


@admin.register(StudySite)
class StudySiteAdmin(admin.ModelAdmin):
    """StudySite Admin"""

    list_display = ("site", "study", "created_at")
    search_fields = ("site__code", "study__code")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
    autocomplete_fields = ["site", "study"]
    list_select_related = ("site", "study")


# ============================================
# STUDY MEMBERSHIP ADMIN
# ============================================


class StudyMembershipForm(forms.ModelForm):
    """
    Simplified form for StudyMembership

    FEATURES:
    - Auto-filters groups by study
    - Clear validation messages
    - Proper field handling
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set default
        if not self.instance.pk:
            self.fields["can_access_all_sites"].initial = True

        # Handle group field based on context
        self._configure_group_field()

        # Handle sites field
        self._configure_sites_field()

    def _configure_group_field(self):
        """Configure group field based on instance state"""

        # When editing existing membership
        if self.instance.pk and self.instance.study:
            study = self.instance.study

            # Get groups for this study
            study_groups = StudyRoleManager.get_study_groups(study.code)

            if not study_groups:
                # Create groups if missing
                try:
                    created = StudyRoleManager.create_study_groups(study.code)
                    study_groups = list(created.values())

                    self.fields["group"].help_text = (
                        f"Auto-created {len(created)} groups for study {study.code}"
                    )
                except Exception as e:
                    self.fields["group"].help_text = (
                        f"Error: {str(e)}. Run: "
                        f"python manage.py sync_study_roles --study {study.code}"
                    )
                    study_groups = []

            # Set queryset
            if study_groups:
                group_ids = [g.pk for g in study_groups]
                self.fields["group"].queryset = Group.objects.filter( # type: ignore
                    pk__in=group_ids
                ).order_by("name")
            else:
                self.fields["group"].queryset = Group.objects.none() # type: ignore

            # Add help text with role descriptions
            role_descriptions = []
            for role_key in RoleTemplate.get_all_role_keys():
                config = RoleTemplate.get_role_config(role_key)
                if config:
                    role_descriptions.append(
                        f"{config['display_name']}: {config['description']}"
                    )

            self.fields["group"].help_text = (
                f"Available roles for study {study.code}:\n"
                + "\n".join(role_descriptions)
            )

        # When adding new
        else:
            self.fields["group"].required = False
            self.fields["group"].queryset = Group.objects.none() # type: ignore
            self.fields["group"].help_text = (
                "Role will be assigned after you save. "
                "Select user and study first, then 'Save and continue editing'."
            )

    def _configure_sites_field(self):
        """Configure sites field"""
        study = None

        # Get study from instance or form data
        if self.instance.pk and self.instance.study:
            study = self.instance.study
        elif "study" in self.data:
            try:
                study_id = self.data.get("study")
                if study_id:
                    study = Study.objects.get(pk=study_id)
            except (ValueError, Study.DoesNotExist):
                pass

        # Filter sites
        if study:
            self.fields["study_sites"].queryset = StudySite.objects.filter( # type: ignore
                study=study
            ).select_related("site")
        else:
            self.fields["study_sites"].queryset = StudySite.objects.none() # type: ignore

    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()

        study = cleaned_data.get("study")
        group = cleaned_data.get("group")

        # Skip group validation for new instances
        if not self.instance.pk:
            return cleaned_data

        # Validate group belongs to study
        if study and group:
            study_code, role_key = StudyRoleManager.parse_group_name(group.name)

            if not study_code or study_code.upper() != study.code.upper():
                self.add_error(
                    "group",
                    f"Selected role does not belong to study '{study.code}'. "
                    f"Please select a valid role for this study.",
                )

        return cleaned_data

    class Meta:
        model = StudyMembership
        fields = "__all__"
        widgets = {
            "study_sites": forms.CheckboxSelectMultiple,
            "notes": forms.Textarea(attrs={"rows": 3, "cols": 80}),
        }


@admin.register(StudyMembership)
class StudyMembershipAdmin(admin.ModelAdmin):
    """
    StudyMembership Admin

    FEATURES:
    - Clean workflow for adding/editing
    - Role-based permissions preview
    - Optimized queries
    """

    form = StudyMembershipForm

    list_display = (
        "get_user_display",
        "get_study_display",
        "get_role_display",
        "get_sites_display",
        "is_active",
        "assigned_at",
    )

    list_filter = (
        "study",
        "is_active",
        "can_access_all_sites",
        "assigned_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "study__code",
        "group__name",
    )

    readonly_fields = (
        "assigned_by",
        "assigned_at",
        "updated_at",
        "permissions_display",
    )

    filter_horizontal = ("study_sites",)
    autocomplete_fields = ["user", "assigned_by", "study"]
    ordering = ("-assigned_at",)
    date_hierarchy = "assigned_at"

    actions = [
        "activate_memberships",
        "deactivate_memberships",
        "sync_permissions",
        "sync_to_groups",
    ]

    # -------------------------
    # Fieldsets
    # -------------------------

    def get_fieldsets(self, request, obj=None):
        """Dynamic fieldsets"""

        if not obj:
            # Adding new
            return (
                (
                    "User and Study",
                    {
                        "fields": ("user", "study"),
                        "description": (
                            "Select user and study first. "
                            "After saving, you can assign a role."
                        ),
                    },
                ),
                (
                    "Site Access",
                    {
                        "fields": ("can_access_all_sites", "study_sites"),
                    },
                ),
                (
                    "Status",
                    {
                        "fields": ("is_active", "notes"),
                    },
                ),
            )
        else:
            # Editing existing
            return (
                (
                    "User and Study",
                    {
                        "fields": ("user", "study", "group"),
                    },
                ),
                (
                    "Permissions",
                    {
                        "fields": ("permissions_display",),
                        "description": "Permissions granted by selected role",
                    },
                ),
                (
                    "Site Access",
                    {
                        "fields": ("can_access_all_sites", "study_sites"),
                    },
                ),
                (
                    "Status and Notes",
                    {
                        "fields": ("is_active", "notes"),
                    },
                ),
                (
                    "Metadata",
                    {
                        "fields": ("assigned_by", "assigned_at", "updated_at"),
                        "classes": ("collapse",),
                    },
                ),
            )

    # -------------------------
    # Display Methods
    # -------------------------

    @admin.display(description="User")
    def get_user_display(self, obj):
        """Display user"""
        user = obj.user
        full_name = user.get_full_name()

        if full_name:
            return f"{user.username} ({full_name})"
        return user.username

    @admin.display(description="Study")
    def get_study_display(self, obj):
        """Display study"""
        return obj.study.code

    @admin.display(description="Role")
    def get_role_display(self, obj):
        """Display role"""
        if not obj.group:
            return "-"

        _, role_key = StudyRoleManager.parse_group_name(obj.group.name)

        if role_key:
            config = RoleTemplate.get_role_config(role_key)
            if config:
                return config["display_name"]

        return obj.group.name

    @admin.display(description="Sites")
    def get_sites_display(self, obj):
        """Display sites"""
        return obj.get_sites_display()

    @admin.display(description="Permissions")
    def permissions_display(self, obj):
        """Display permissions"""
        if not obj.pk or not obj.group:
            return "Save to see permissions"

        perms = StudyRoleManager.get_group_permissions(obj.group)

        if not perms:
            return "No permissions. Run: python manage.py sync_study_roles"

        # Group by model
        from collections import defaultdict

        grouped = defaultdict(list)

        for perm in sorted(perms):
            parts = perm.split("_", 1)
            if len(parts) == 2:
                action, model = parts
                grouped[model].append(action)

        # Format
        lines = []
        for model in sorted(grouped.keys()):
            actions = ", ".join(sorted(grouped[model]))
            lines.append(f"{model.upper()}: {actions}")

        return "\n".join(lines) if lines else "No permissions"

    # -------------------------
    # Actions
    # -------------------------

    @admin.action(description="Activate memberships")
    def activate_memberships(self, request, queryset):
        """Activate memberships"""
        count = queryset.update(is_active=True)

        self.message_user(request, f"Activated {count} membership(s)", messages.SUCCESS)

    @admin.action(description="Deactivate memberships")
    def deactivate_memberships(self, request, queryset):
        """Deactivate memberships"""
        count = queryset.update(is_active=False)

        self.message_user(
            request, f"Deactivated {count} membership(s)", messages.SUCCESS
        )

    @admin.action(description="Sync permissions")
    def sync_permissions(self, request, queryset):
        """Sync permissions for studies"""
        study_codes = set(queryset.values_list("study__code", flat=True))

        synced = 0
        for code in study_codes:
            try:
                result = StudyRoleManager.assign_permissions(code, force=True)
                synced += result["groups_updated"]
            except Exception as e:
                self.message_user(
                    request, f"Error syncing {code}: {str(e)}", messages.ERROR
                )

        if synced > 0:
            self.message_user(
                request,
                f"Synced {synced} groups across {len(study_codes)} studies",
                messages.SUCCESS,
            )

    @admin.action(description="Sync to groups")
    def sync_to_groups(self, request, queryset):
        """Sync users to groups"""
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
                    f"Error: {membership.user.username} - {str(e)}",
                    messages.ERROR,
                )

        if synced > 0:
            self.message_user(
                request, f"Synced {synced} user(s) to groups", messages.SUCCESS
            )

        if errors == 0 and synced == 0:
            self.message_user(request, "All users already synced", messages.INFO)

    # -------------------------
    # Save Methods
    # -------------------------

    def save_model(self, request, obj, form, change):
        """Handle save with proper group assignment"""

        # Set assigned_by
        if not obj.assigned_by:
            obj.assigned_by = request.user

        # For new memberships without group
        if not change and obj.study and not obj.group_id:
            # Get first group as temporary placeholder
            groups = StudyRoleManager.get_study_groups(obj.study.code)

            if not groups:
                # Create groups if missing
                try:
                    created = StudyRoleManager.create_study_groups(obj.study.code)
                    groups = list(created.values())
                except Exception as e:
                    logger.error(f"Could not create groups: {e}")

            if groups:
                obj.group = groups[0]
                obj.notes = (obj.notes or "") + (
                    "\nTemporary role assigned. Please update after saving."
                )

        super().save_model(request, obj, form, change)

        # Sync permissions for new memberships
        if not change:
            try:
                StudyRoleManager.assign_permissions(obj.study.code, force=False)
            except Exception as e:
                self.message_user(
                    request,
                    f"Membership saved but permissions sync failed: {str(e)}",
                    messages.WARNING,
                )

    def response_add(self, request, obj, post_url_continue=None):
        """Redirect to change page after add"""

        # Handle different save buttons
        if "_continue" in request.POST or "_addanother" in request.POST:
            return super().response_add(request, obj, post_url_continue)

        # Default: redirect to change page
        self.message_user(
            request,
            f"Membership created. Please assign a role for {obj.user.username}.",
            messages.SUCCESS,
        )

        return HttpResponseRedirect(
            reverse("admin:tenancy_studymembership_change", args=[obj.pk])
        )

    def get_queryset(self, request):
        """Optimize queryset"""
        return (
            super()
            .get_queryset(request)
            .select_related("user", "study", "group", "assigned_by")
            .prefetch_related("study_sites__site")
        )
