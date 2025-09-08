# backend/tenancy/admin.py - FIXED VERSION
from django.contrib import admin
from django.contrib.auth import get_user_model  # FIXED: Use get_user_model() function
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from parler.admin import TranslatableAdmin
from django import forms
from django.utils.translation import gettext_lazy as _

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
    model = RolePermission
    extra = 1
    verbose_name = "Role Permission"
    verbose_name_plural = "Role Permissions"


# Inline for StudySite in Study and Site
class StudySiteInline(admin.TabularInline):
    model = StudySite
    extra = 1
    verbose_name ="Study-Site Link"
    verbose_name_plural ="Study-Site Links"
    readonly_fields = ('created_at', 'updated_at')

# Inline for StudyMembership in Study, StudySite, and Role
class StudyMembershipInline(admin.TabularInline):
    model = StudyMembership
    extra = 1
    verbose_name ="Study Membership"
    verbose_name_plural ="Study Memberships"
    readonly_fields = ('assigned_at',)

    def get_parent_object_from_request(self, request):
        """
        Returns the parent object from the request or `None`.
        """
        resolved = request.resolver_match
        if resolved and 'object_id' in resolved.kwargs:
            object_id = resolved.kwargs['object_id']
            parent_model = self.parent_model
            try:
                return parent_model.objects.get(pk=object_id)
            except parent_model.DoesNotExist:
                return None
        return None

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'study_site':
            parent_obj = self.get_parent_object_from_request(request)
            if isinstance(parent_obj, Study):
                kwargs['queryset'] = StudySite.objects.filter(study=parent_obj)
            elif isinstance(parent_obj, StudySite):
                kwargs['queryset'] = StudySite.objects.filter(pk=parent_obj.pk)
            else:
                kwargs['queryset'] = StudySite.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'created_at', 'updated_at')  # FIXED: Added code
    search_fields = ('title', 'code')  # FIXED: Changed from abbreviation to code
    list_filter = ('created_at', 'updated_at')
    inlines = [RolePermissionInline]
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'created_at', 'updated_at')
    search_fields = ('code', 'name')
    list_filter = ('created_at', 'updated_at')
    inlines = [RolePermissionInline]
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Study)
class StudyAdmin(TranslatableAdmin):
    list_display = ('code', 'name', 'status', 'db_name', 'created_at', 'updated_at')
    search_fields = ('code', 'translations__name', 'db_name')
    list_filter = ('status', 'created_at', 'updated_at')
    inlines = [StudySiteInline, StudyMembershipInline]
    readonly_fields = ('created_at', 'updated_at')

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
    # Override fields with custom choice fields
    study = StudyCodeChoiceField(
        queryset=Study.objects.all().order_by('code'),
        label="Study"
    )
    study_site = StudySiteCodeChoiceField(
        queryset=StudySite.objects.none(),
        label="Study Site",
        required=False
    )
    user = UserChoiceField(
        queryset=User.objects.all().order_by('username'),
        label="User"
    )
    
    class Meta:
        model = StudyMembership
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Handle study_site queryset based on selected study
        if self.instance.pk and self.instance.study:
            self.fields['study_site'].queryset = StudySite.objects.filter(  # type: ignore[name-defined]
                study=self.instance.study
            ).select_related('site')
        
        # If form is submitted with a study value
        if 'study' in self.data:
            try:
                study_id = int(self.data.get('study'))  # type: ignore[name-defined]
                self.fields['study_site'].queryset = StudySite.objects.filter(  # type: ignore[name-defined]
                    study_id=study_id
                ).select_related('site')
            except (ValueError, TypeError):
                pass

@admin.register(StudyMembership)
class StudyMembershipAdmin(admin.ModelAdmin):
    form = StudyMembershipForm
    list_display = ('get_user_display', 'get_study_code', 'get_site_code', 'role', 'assigned_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'study__code', 'role__title')
    list_filter = ('role', 'assigned_at', 'study')
    readonly_fields = ('assigned_at',)
    
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

    @admin.display(description="Site Code")
    def get_site_code(self, obj):
        # FIXED: Updated to use many-to-many relationship
        sites = obj.study_sites.all()
        if obj.can_access_all_sites:
            return "All Sites"
        elif sites:
            return ", ".join([site.site.code for site in sites])
        return '-'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'study', 'role'
        ).prefetch_related('study_sites__site')