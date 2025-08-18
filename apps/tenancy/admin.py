# apps/tenancy/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Role, Permission, RolePermission, Study, StudyTranslation, StudySite, StudyMembership

# Inline for RolePermission in Role and Permission
class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1  # Number of default inline forms
    verbose_name = _("Role Permission")
    verbose_name_plural = _("Role Permissions")

# Inline for StudyTranslation in Study
class StudyTranslationInline(admin.StackedInline):
    model = StudyTranslation
    extra = 1
    verbose_name = _("Study Translation")
    verbose_name_plural = _("Study Translations")

# Inline for StudySite in Study
class StudySiteInline(admin.TabularInline):
    model = StudySite
    extra = 1
    verbose_name = _("Study Site")
    verbose_name_plural = _("Study Sites")

# Inline for StudyMembership in Study, Role, and StudySite
class StudyMembershipInline(admin.TabularInline):
    model = StudyMembership
    extra = 1
    verbose_name = _("Study Membership")
    verbose_name_plural = _("Study Memberships")

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('title', 'abbreviation', 'created_at', 'updated_at')
    search_fields = ('title', 'abbreviation')
    list_filter = ('created_at', 'updated_at')
    inlines = [RolePermissionInline, StudyMembershipInline]
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
class StudyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'status', 'db_name', 'created_at', 'updated_at')
    search_fields = ('code', 'name', 'db_name')
    list_filter = ('status', 'created_at', 'updated_at')
    inlines = [StudyTranslationInline, StudySiteInline, StudyMembershipInline]
    readonly_fields = ('created_at', 'updated_at')

@admin.register(StudyTranslation)
class StudyTranslationAdmin(admin.ModelAdmin):
    list_display = ('study', 'language_code', 'name')
    search_fields = ('study__code', 'language_code', 'name')
    list_filter = ('language_code',)

@admin.register(StudySite)
class StudySiteAdmin(admin.ModelAdmin):
    list_display = ('study', 'code', 'name_en', 'name_vi', 'created_at', 'updated_at')
    search_fields = ('study__code', 'code', 'name_en', 'name_vi')
    list_filter = ('created_at', 'updated_at')
    inlines = [StudyMembershipInline]
    readonly_fields = ('created_at', 'updated_at')

@admin.register(StudyMembership)
class StudyMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'study', 'site', 'role', 'assigned_at')
    search_fields = ('user__username', 'study__code', 'site__code', 'role__title')
    list_filter = ('role', 'assigned_at')
    readonly_fields = ('assigned_at',)