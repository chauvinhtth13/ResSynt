# apps/tenancy/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from parler.admin import TranslatableAdmin
from django import forms
from .models import Role, Permission, RolePermission, Study, Site, StudySite, StudyMembership

# Inline for RolePermission in Role and Permission
class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1
    verbose_name = _("Role Permission")
    verbose_name_plural = _("Role Permissions")

# Inline for StudySite in Study and Site
class StudySiteInline(admin.TabularInline):
    model = StudySite
    extra = 1
    verbose_name = _("Study-Site Link")
    verbose_name_plural = _("Study-Site Links")
    readonly_fields = ('created_at', 'updated_at')

# Inline for StudyMembership in Study, StudySite, and Role
class StudyMembershipInline(admin.TabularInline):
    model = StudyMembership
    extra = 1
    verbose_name = _("Study Membership")
    verbose_name_plural = _("Study Memberships")
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
    list_display = ('title', 'abbreviation', 'created_at', 'updated_at')
    search_fields = ('title', 'abbreviation')
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

@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'permission')
    search_fields = ('role__title', 'permission__code')
    list_filter = ('role', 'permission')

@admin.register(Study)
class StudyAdmin(TranslatableAdmin):
    list_display = ('code', 'name', 'status', 'db_name', 'created_at', 'updated_at')
    search_fields = ('code', 'name', 'db_name')
    list_filter = ('status', 'created_at', 'updated_at')
    inlines = [StudySiteInline]
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Site)
class SiteAdmin(TranslatableAdmin):
    list_display = ('code', 'abbreviation', 'name', 'created_at', 'updated_at')
    search_fields = ('code', 'abbreviation', 'name')
    list_filter = ('created_at', 'updated_at')
    inlines = [StudySiteInline]
    readonly_fields = ('created_at', 'updated_at')

@admin.register(StudySite)
class StudySiteAdmin(admin.ModelAdmin):
    list_display = ('study', 'site', 'created_at', 'updated_at')
    search_fields = ('study__code', 'site__code')
    list_filter = ('created_at', 'updated_at')
    inlines = [StudyMembershipInline]
    readonly_fields = ('created_at', 'updated_at')

class StudyMembershipForm(forms.ModelForm):
    class Meta:
        model = StudyMembership
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['study_site'].widget = forms.HiddenInput()  # Hide on add
            self.fields['study_site'].required = False
        else:
            if self.instance.study:
                self.fields['study_site'].queryset = StudySite.objects.filter(study=self.instance.study) # type: ignore
            else:
                self.fields['study_site'].queryset = StudySite.objects.none() # type: ignore

@admin.register(StudyMembership)
class StudyMembershipAdmin(admin.ModelAdmin):
    form = StudyMembershipForm
    list_display = ('user', 'study', 'get_site_code', 'role', 'assigned_at')
    search_fields = ('user__username', 'study__code', 'study_site__site__code', 'role__title')
    list_filter = ('role', 'assigned_at')
    readonly_fields = ('assigned_at',)

    @admin.display(description=_("Site Code"))
    def get_site_code(self, obj):
        return obj.study_site.site.code if obj.study_site else '-'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'study_site':
            study_id = None
            if request is not None and request.resolver_match is not None and 'object_id' in request.resolver_match.kwargs:
                obj = self.get_object(request, request.resolver_match.kwargs['object_id'])  # type: ignore[arg-type]
                if obj and obj.study:
                    study_id = obj.study.id
            if not study_id and request is not None and 'study' in request.POST:
                study_id = request.POST['study']
            if study_id:
                kwargs['queryset'] = StudySite.objects.filter(study_id=study_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)