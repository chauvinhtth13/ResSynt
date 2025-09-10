# backend/tenancy/admin.py - FIXED VERSION
from django.contrib import admin
from django.contrib.auth import get_user_model  # FIXED: Use get_user_model() function
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from parler.admin import TranslatableAdmin
from django.contrib.admin import AdminSite
from django import forms

# Import models from correct location
from .models import (
    Role, Permission, RolePermission, Study, Site, 
    StudySite, StudyMembership
)

# Get the User model
User = get_user_model()

# ============================================
# USER ADMIN REGISTRATION
# ============================================
# Ensure User admin is registered with search_fields for autocomplete support
if not admin.site.is_registered(User):
    @admin.register(User)
    class UserAdmin(BaseUserAdmin):
        search_fields = ('username', 'email', 'first_name', 'last_name')

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