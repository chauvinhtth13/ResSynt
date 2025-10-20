# backends/tenancy/admin.py - CLEAN MINIMAL VERSION

import logging
from io import StringIO
from pathlib import Path

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import (
    AdminPasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import connections
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from parler.admin import TranslatableAdmin

from backends.tenancy.models import StudyMembership, Study, Site, StudySite
from backends.tenancy.models.user import User
from backends.tenancy.utils import DatabaseStudyCreator
from backends.tenancy.utils.role_manager import RoleTemplate, StudyRoleManager

logger = logging.getLogger(__name__)


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_time_display(dt):
    """Convert datetime to human-readable string"""
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
    """Get Axes status display for user"""
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
# CUSTOM USER FORMS
# ============================================

class CustomUserCreationForm(UserCreationForm):
    """Form for creating new users in admin"""

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["password1"].help_text = _(
            "Enter a strong password with at least 8 characters"
        )
        self.fields["username"].help_text = _(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.password_changed_at = timezone.now()
        user.must_change_password = True

        if commit:
            user.save()

        return user


class CustomUserChangeForm(UserChangeForm):
    """Form for changing existing users in admin"""

    class Meta:
        model = User
        fields = "__all__"


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
        if db_field.name == "site":
            kwargs["queryset"] = Site.objects.all().order_by("code")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ============================================
# USER ADMIN
# ============================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced User Admin with proper password management"""

    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    change_password_form = AdminPasswordChangeForm

    inlines = [StudyMembershipInline]

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
            "Personal Information",
            {
                "fields": ("first_name", "last_name"),
            },
        ),
        (
            "Status",
            {
                "fields": ("is_active", "is_staff", "is_superuser"),
            },
        ),
    )

    fieldsets = (
        (
            None,
            {
                "fields": ("username", "password"),
            },
        ),
        (
            "Personal Information",
            {
                "fields": ("first_name", "last_name", "email"),
            },
        ),
        (
            "Status",
            {
                "fields": ("is_active", "must_change_password"),
            },
        ),
        (
            "Security",
            {
                "fields": (
                    "axes_status_detail",
                    "last_failed_login_display",
                    "password_changed_at_display",
                ),
                "description": "Use the actions below to reset Axes locks.",
            },
        ),
        (
            "Permissions",
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
            "Study Access",
            {
                "fields": ("last_study_display",),
                "classes": ("collapse",),
            },
        ),
        (
            "Administrative",
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

    readonly_fields = (
        "axes_status_detail",
        "last_failed_login_display",
        "password_changed_at_display",
        "last_login_display_detail",
        "date_joined_display",
        "created_at_display",
        "updated_at_display",
        "created_by_display",
        "last_study_display",
    )

    actions = [
        "activate_users",
        "deactivate_users",
        #"reset_axes_locks",
        "sync_user_groups_action",
    ]

    # Display Methods
    
    @admin.display(description="Full Name")
    def full_name_display(self, obj):
        full_name = obj.get_full_name()
        return full_name if full_name else f"({obj.username})"

    @admin.display(description="Status")
    def status_display(self, obj):
        if obj.is_active:
            return "Active"
        elif obj.is_axes_blocked:
            return "Blocked (Axes)"
        else:
            return "Inactive"

    @admin.display(description="Axes Status")
    def axes_status_display(self, obj):
        return get_axes_status_display(obj)

    @admin.display(description="Last Login")
    def last_login_display(self, obj):
        return get_time_display(obj.last_login)

    @admin.display(description="Studies")
    def study_count_display(self, obj):
        count = obj.study_memberships.filter(is_active=True).count()
        return f"{count} active"

    @admin.display(description="Axes Status")
    def axes_status_detail(self, obj):
        if not obj or not obj.pk:
            return "N/A"
        return get_axes_status_display(obj)

    @admin.display(description="Last Failed Login")
    def last_failed_login_display(self, obj):
        return get_time_display(obj.last_failed_login_at)

    @admin.display(description="Password Last Changed")
    def password_changed_at_display(self, obj):
        return get_time_display(obj.password_changed_at)

    @admin.display(description="Last Login Detail")
    def last_login_display_detail(self, obj):
        if obj.last_login:
            return obj.last_login.strftime("%Y-%m-%d %H:%M:%S")
        return "Never"

    @admin.display(description="Date Joined")
    def date_joined_display(self, obj):
        return obj.date_joined.strftime("%Y-%m-%d %H:%M:%S")

    @admin.display(description="Created At")
    def created_at_display(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")

    @admin.display(description="Updated At")
    def updated_at_display(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d %H:%M:%S")

    @admin.display(description="Created By")
    def created_by_display(self, obj):
        return obj.created_by.username if obj.created_by else "System"

    @admin.display(description="Last Study")
    def last_study_display(self, obj):
        if obj.last_study:
            return f"{obj.last_study.code}"
        return "None"

    # Actions
    
    @admin.action(description="Activate users & reset Axes locks")
    def activate_users(self, request, queryset):
        """
        Activate users và reset Axes locks - IMPROVED VERSION
        
        Features:
        - Activate inactive users + reset axes
        - Reset axes cho active users có warning/blocked
        - Smart detection: chỉ xử lý users cần thiết
        """
        activated = 0
        axes_reset_only = 0
        skipped = 0
        failed = 0
        
        for user in queryset:
            # Case 1: User INACTIVE → Activate + Reset Axes
            if not user.is_active:
                if user.unblock_user():  # activate + reset_axes_locks + reset counters
                    activated += 1
                    logger.info(
                        f"Admin {request.user.username} activated user: {user.username}"
                    )
                else:
                    failed += 1
                    logger.error(
                        f"Failed to activate user: {user.username}"
                    )
            
            # Case 2: User ACTIVE nhưng có Axes attempts → Chỉ Reset Axes
            elif user.axes_failure_count > 0:
                if user.reset_axes_locks():
                    axes_reset_only += 1
                    logger.info(
                        f"Admin {request.user.username} reset Axes locks for active user: {user.username}"
                    )
                else:
                    failed += 1
                    logger.error(
                        f"Failed to reset Axes locks for user: {user.username}"
                    )
            
            # Case 3: User ACTIVE và CLEAN → Skip
            else:
                skipped += 1
        
        # Thông báo kết quả chi tiết
        messages_list = []
        
        if activated:
            messages_list.append(f"Activated {activated} user(s)")
        
        if axes_reset_only:
            messages_list.append(f"Reset Axes locks for {axes_reset_only} active user(s)")
        
        if messages_list:
            self.message_user(
                request,
                " and ".join(messages_list),
                messages.SUCCESS
            )
        
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} user(s) (already active and clean)",
                messages.INFO
            )
        
        if failed:
            self.message_user(
                request,
                f"Failed to process {failed} user(s)",
                messages.ERROR
            )

    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        """Deactivate users"""
        deactivated = 0
        failed = 0
        
        for user in queryset.filter(is_active=True):
            if user.block_user(reason="Deactivated by admin"):
                deactivated += 1
            else:
                failed += 1
        
        if deactivated:
            self.message_user(
                request, 
                f"Deactivated {deactivated} user(s)",
                messages.WARNING
            )
        
        if failed:
            self.message_user(
                request,
                f"Failed to deactivate {failed} user(s)",
                messages.ERROR
            )

    @admin.action(description="Reset Axes locks")
    def reset_axes_locks(self, request, queryset):
        """
        Reset Axes locks - FIXED VERSION
        Reset cho TẤT CẢ users được chọn, bất kể Warning hay Blocked
        """
        reset_count = 0
        failed = 0
        
        for user in queryset:
            # Reset VÔ ĐIỀU KIỆN - không cần check is_axes_blocked
            if user.reset_axes_locks():
                reset_count += 1
                logger.info(
                    f"Admin {request.user.username} reset Axes locks for user: {user.username}"
                )
            else:
                failed += 1
                logger.error(
                    f"Failed to reset Axes locks for user: {user.username}"
                )
        
        # Thông báo kết quả
        if reset_count:
            self.message_user(
                request, 
                f"Successfully reset Axes locks for {reset_count} user(s)",
                messages.SUCCESS
            )
        
        if failed:
            self.message_user(
                request,
                f"Failed to reset Axes locks for {failed} user(s)",
                messages.ERROR
            )
        
        if reset_count == 0 and failed == 0:
            self.message_user(
                request,
                "No users selected",
                messages.WARNING
            )

    @admin.action(description="Sync users to Django groups")
    def sync_user_groups_action(self, request, queryset):
        synced = 0
        errors = 0

        for user in queryset:
            try:
                memberships = user.study_memberships.filter(is_active=True)
                for membership in memberships:
                    membership.sync_user_to_groups()
                synced += 1
            except Exception as e:
                logger.error(f"Error syncing user {user.username}: {e}")
                errors += 1

        if synced > 0:
            self.message_user(
                request, 
                f"Synced {synced} user(s) to groups", 
                messages.SUCCESS
            )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("created_by", "last_study_accessed")
            .prefetch_related("study_memberships__study")
        )


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

    # Display Methods
    
    @admin.display(description="Database Name")
    def db_name_readonly(self, obj):
        if obj and obj.pk:
            return obj.db_name
        elif obj and obj.code:
            return obj.generate_db_name()
        return "Auto-generated from code"

    @admin.display(description="Database")
    def database_status_display(self, obj):
        if not obj or not obj.db_name:
            return "Not created"

        exists = DatabaseStudyCreator.database_exists(obj.db_name)

        if exists:
            if obj.db_name in connections.databases:
                return "Active"
            else:
                return "Not loaded"
        else:
            return "Not created"

    @admin.display(description="Folder")
    def folder_status_display(self, obj):
        if not obj or not obj.code:
            return "N/A"

        from django.conf import settings

        study_folder = (
            Path(settings.BASE_DIR)
            / "backends"
            / "studies"
            / f"study_{obj.code.lower()}"
        )

        if not study_folder.exists():
            return "Missing"

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

    # Actions
    
    @admin.action(description="Create folder structures")
    def create_study_structures(self, request, queryset):
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
                    request, 
                    f"Error for {study.code}: {str(e)}", 
                    messages.ERROR
                )

        if created > 0:
            self.message_user(
                request,
                f"Created {created} structure(s). Restart server to load.",
                messages.SUCCESS,
            )

    @admin.action(description="Activate studies")
    def activate_studies(self, request, queryset):
        count = queryset.filter(status=Study.Status.ARCHIVED).update(
            status=Study.Status.ACTIVE
        )
        if count:
            self.message_user(
                request, 
                f"Activated {count} study/studies", 
                messages.SUCCESS
            )

    @admin.action(description="Archive studies")
    def archive_studies(self, request, queryset):
        count = queryset.exclude(status=Study.Status.ARCHIVED).update(
            status=Study.Status.ARCHIVED
        )
        if count:
            self.message_user(
                request, 
                f"Archived {count} study/studies", 
                messages.SUCCESS
            )


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
# STUDY MEMBERSHIP FORM
# ============================================

class StudyMembershipForm(forms.ModelForm):
    """Form for StudyMembership with proper field handling"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            if "can_access_all_sites" in self.fields:
                self.fields["can_access_all_sites"].initial = True

        # Initialize group as ModelChoiceField
        if "group" in self.fields:
            self.fields["group"] = forms.ModelChoiceField(
                queryset=Group.objects.none(),
                required=False
            )

        self._configure_group_field()
        self._configure_sites_field()

    def _configure_group_field(self):
        """Configure group field based on instance state"""
        
        if "group" not in self.fields:
            logger.debug("Group field not in form, skipping configuration")
            return

        if self.instance.pk and self.instance.study:
            study = self.instance.study
            study_groups = StudyRoleManager.get_study_groups(study.code)

            if not study_groups:
                try:
                    created = StudyRoleManager.create_study_groups(study.code)
                    study_groups = list(created.values())

                    if created:
                        self.fields["group"].help_text = (
                            f"Auto-created {len(created)} groups for study {study.code}"
                        )
                except Exception as e:
                    logger.error(f"Failed to create groups for {study.code}: {e}")
                    self.fields["group"].help_text = (
                        f"Error creating groups: {str(e)}\n"
                        f"Run: python manage.py sync_study_roles {study.code}"
                    )
                    study_groups = []

            if study_groups:
                group_ids = [g.pk for g in study_groups]
                qs = Group.objects.filter(pk__in=group_ids).order_by("name")
                
                role_descriptions = []
                for role_key in RoleTemplate.get_all_role_keys():
                    config = RoleTemplate.get_role_config(role_key)
                    if config:
                        role_descriptions.append(
                            f"{config['display_name']}: {config['description']}"
                        )

                help_text = ""
                if role_descriptions:
                    help_text = (
                        f"Available roles for study {study.code}:\n\n"
                        + "\n".join(role_descriptions)
                    )

                # Recreate the ModelChoiceField (instead of mutating .queryset)
                field = forms.ModelChoiceField(queryset=qs, required=False)
                if help_text:
                    field.help_text = help_text
                self.fields["group"] = field
            else:
                field = forms.ModelChoiceField(queryset=Group.objects.none(), required=False)
                field.help_text = (
                    f"No groups found for study {study.code}.\n"
                    f"Run: python manage.py sync_study_roles {study.code}"
                )
                self.fields["group"] = field

        else:
            self.fields["group"].required = False
            field = forms.ModelChoiceField(queryset=Group.objects.none(), required=False)
            field.help_text = (
                "Role will be available after you save.\n"
                "Select user and study first, then 'Save and continue editing'."
            )
            self.fields["group"] = field

    def _configure_sites_field(self):
        """Configure sites field based on study"""
        
        if "study_sites" not in self.fields:
            logger.debug("study_sites field not in form, skipping configuration")
            return

        study = None

        if self.instance.pk and self.instance.study:
            study = self.instance.study
        elif "study" in self.data:
            try:
                study_id = self.data.get("study")
                if study_id:
                    study = Study.objects.get(pk=study_id)
            except (ValueError, Study.DoesNotExist):
                pass

        # Use a ModelMultipleChoiceField instead of mutating .queryset on a generic Field
        if study:
            qs = StudySite.objects.filter(study=study).select_related("site")
            site_count = qs.count()
            field = forms.ModelMultipleChoiceField(
                queryset=qs,
                required=False,
                widget=forms.CheckboxSelectMultiple,
            )
            field.help_text = (
                f"Select specific sites for this user in study {study.code}. "
                f"({site_count} site(s) available)\n"
                f"Leave empty if 'Can Access All Sites' is checked."
            )
            self.fields["study_sites"] = field
        else:
            field = forms.ModelMultipleChoiceField(
                queryset=StudySite.objects.none(),
                required=False,
                widget=forms.CheckboxSelectMultiple,
            )
            field.help_text = "Save the membership first to select sites."
            self.fields["study_sites"] = field

    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()

        study = cleaned_data.get("study")
        group = cleaned_data.get("group")
        user = cleaned_data.get("user")

        if not self.instance.pk:
            return cleaned_data

        if user and study:
            duplicate = StudyMembership.objects.filter(
                user=user,
                study=study
            ).exclude(pk=self.instance.pk)
            
            if duplicate.exists():
                self.add_error(
                    'user',
                    f"User '{user.username}' already has a membership in study '{study.code}'."
                )

        if study and group:
            study_code, role_key = StudyRoleManager.parse_group_name(group.name)

            if not study_code or study_code.upper() != study.code.upper():
                self.add_error(
                    "group",
                    f"Selected role does not belong to study '{study.code}'. "
                    f"Please select a valid role for this study."
                )

        can_access_all = cleaned_data.get("can_access_all_sites", False)
        study_sites = cleaned_data.get("study_sites", [])
        
        if not can_access_all and not study_sites:
            self.add_error(
                "study_sites",
                "Please either select specific sites OR check 'Can Access All Sites'."
            )

        return cleaned_data

    class Meta:
        model = StudyMembership
        fields = "__all__"
        widgets = {
            "study_sites": forms.CheckboxSelectMultiple,
            "notes": forms.Textarea(attrs={"rows": 3, "cols": 80}),
        }


# ============================================
# STUDY MEMBERSHIP ADMIN
# ============================================

@admin.register(StudyMembership)
class StudyMembershipAdmin(admin.ModelAdmin):
    """StudyMembership Admin with clean workflow"""

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
        ("assigned_at", admin.DateFieldListFilter),
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
    autocomplete_fields = ["user", "study"]
    ordering = ("-assigned_at",)
    date_hierarchy = "assigned_at"

    actions = [
        "activate_memberships",
        "deactivate_memberships",
        "sync_permissions",
        "sync_to_groups",
    ]

    def get_fieldsets(self, request, obj=None):
        """Dynamic fieldsets based on add vs edit"""
        
        if not obj:
            return (
                (
                    "Step 1: Select User and Study",
                    {
                        "fields": ("user", "study"),
                        "description": (
                            "First, select the user and study. "
                            "After saving, you'll be able to assign a role in Step 2."
                        ),
                    },
                ),
                (
                    "Site Access",
                    {
                        "fields": ("can_access_all_sites", "study_sites"),
                        "description": (
                            "Choose either 'All Sites' or select specific sites."
                        ),
                    },
                ),
                (
                    "Status and Notes",
                    {
                        "fields": ("is_active", "notes"),
                    },
                ),
            )
        else:
            return (
                (
                    "User, Study, and Role",
                    {
                        "fields": ("user", "study", "group"),
                        "description": "Assign or change the user's role in this study.",
                    },
                ),
                (
                    "Role Permissions",
                    {
                        "fields": ("permissions_display",),
                        "description": "Permissions granted by the selected role.",
                        "classes": ("collapse",),
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

    # Display Methods
    
    @admin.display(description="User", ordering="user__username")
    def get_user_display(self, obj):
        if not obj or not obj.user:
            return "-"
        
        user = obj.user
        full_name = user.get_full_name()

        if full_name:
            return f"{user.username} ({full_name})"
        return user.username

    @admin.display(description="Study", ordering="study__code")
    def get_study_display(self, obj):
        if not obj or not obj.study:
            return "-"
        return obj.study.code

    @admin.display(description="Role", ordering="group__name")
    def get_role_display(self, obj):
        if not obj or not obj.group:
            return "No role assigned"

        _, role_key = StudyRoleManager.parse_group_name(obj.group.name)

        if role_key:
            config = RoleTemplate.get_role_config(role_key)
            if config:
                return config["display_name"]

        return obj.group.name

    @admin.display(description="Sites")
    def get_sites_display(self, obj):
        if not obj:
            return "-"
        return obj.get_sites_display()

    @admin.display(description="Permissions")
    def permissions_display(self, obj):
        """Display permissions in plain text"""
        
        if not obj or not obj.pk or not obj.group:
            return "Save to see permissions"

        try:
            from backends.tenancy.utils import TenancyUtils
            perm_summary = TenancyUtils.get_permission_display(obj.user, obj.study)

            if not perm_summary:
                return "No permissions found"

            # Format as plain text list
            lines = []
            for model_name, actions in sorted(perm_summary.items()):
                actions_str = ', '.join(sorted(actions))
                lines.append(f"{model_name}: {actions_str}")
            
            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Error displaying permissions: {e}")
            return "Error loading permissions"

    # Actions
    
    @admin.action(description="Activate selected memberships")
    def activate_memberships(self, request, queryset):
        updated = queryset.filter(is_active=False).update(is_active=True)
        
        if updated:
            self.message_user(
                request,
                f"Activated {updated} membership(s)",
                messages.SUCCESS
            )

    @admin.action(description="Deactivate selected memberships")
    def deactivate_memberships(self, request, queryset):
        updated = queryset.filter(is_active=True).update(is_active=False)
        
        if updated:
            self.message_user(
                request,
                f"Deactivated {updated} membership(s)",
                messages.WARNING
            )

    @admin.action(description="Sync permissions for selected studies")
    def sync_permissions(self, request, queryset):
        studies = queryset.values_list('study__code', flat=True).distinct()
        
        synced = 0
        errors = 0
        
        for study_code in studies:
            try:
                result = StudyRoleManager.initialize_study(study_code, force=True)
                if 'error' not in result:
                    synced += 1
                else:
                    errors += 1
            except Exception as e:
                logger.error(f"Error syncing {study_code}: {e}")
                errors += 1
        
        if synced > 0:
            self.message_user(
                request,
                f"Synced permissions for {synced} study/studies",
                messages.SUCCESS
            )
        
        if errors > 0:
            self.message_user(
                request,
                f"Failed to sync {errors} study/studies. Check logs.",
                messages.ERROR
            )

    @admin.action(description="Sync users to Django groups")
    def sync_to_groups(self, request, queryset):
        synced = 0
        errors = 0
        
        for membership in queryset:
            try:
                membership.sync_user_to_groups()
                synced += 1
            except Exception as e:
                logger.error(f"Error syncing membership {membership.pk}: {e}")
                errors += 1
        
        if synced > 0:
            self.message_user(
                request,
                f"Synced {synced} user(s) to groups",
                messages.SUCCESS
            )

    def save_model(self, request, obj, form, change):
        """Handle save with automatic setup"""
        
        if not change and not obj.assigned_by:
            obj.assigned_by = request.user

        if not change and obj.study and not obj.group_id:
            groups = StudyRoleManager.get_study_groups(obj.study.code)

            if not groups:
                try:
                    created = StudyRoleManager.create_study_groups(obj.study.code)
                    groups = list(created.values()) if created else []
                    
                    if groups:
                        self.message_user(
                            request,
                            f"Auto-created {len(groups)} groups for study {obj.study.code}",
                            messages.INFO
                        )
                except Exception as e:
                    logger.error(f"Failed to create groups: {e}")
                    self.message_user(
                        request,
                        f"Could not create groups: {str(e)}",
                        messages.ERROR
                    )

            if groups:
                obj.group = groups[0]
                obj.notes = (obj.notes or "") + (
                    "\n[Auto-assigned temporary role. Please update after saving.]"
                )

        super().save_model(request, obj, form, change)

        if not change:
            try:
                StudyRoleManager.assign_permissions(obj.study.code, force=False)
            except Exception as e:
                logger.error(f"Failed to sync permissions: {e}")
                self.message_user(
                    request,
                    f"Membership saved but permissions sync failed: {str(e)}",
                    messages.WARNING
                )

    def response_add(self, request, obj, post_url_continue=None):
        """Customize response after adding"""
        
        if "_addanother" in request.POST:
            return super().response_add(request, obj, post_url_continue)

        self.message_user(
            request,
            f"Membership created for {obj.user.username}. Now assign a role in Step 2.",
            messages.SUCCESS
        )

        return HttpResponseRedirect(
            reverse("admin:tenancy_studymembership_change", args=[obj.pk])
        )

    def get_queryset(self, request):
        """Optimize queryset with proper joins"""
        return (
            super()
            .get_queryset(request)
            .select_related("user", "study", "group", "assigned_by")
            .prefetch_related("study_sites__site")
        )