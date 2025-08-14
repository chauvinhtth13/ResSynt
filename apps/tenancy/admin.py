# apps/tenancy/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Role, Permission, RolePermission, Study, StudyConfig, StudyTranslation, StudyMembership

# Inline cho RolePermission trong Role và Permission
class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1  # Số form inline mặc định
    verbose_name = _("Role Permission")
    verbose_name_plural = _("Role Permissions")

# Inline cho StudyTranslation trong Study
class StudyTranslationInline(admin.StackedInline):
    model = StudyTranslation
    extra = 1
    verbose_name = _("Study Translation")
    verbose_name_plural = _("Study Translations")

# Inline cho StudyMembership trong Study và Role
class StudyMembershipInline(admin.TabularInline):
    model = StudyMembership
    extra = 1
    verbose_name = _("Study Membership")
    verbose_name_plural = _("Study Memberships")

# Inline cho StudyConfig trong Study (vì OneToOne)
class StudyConfigInline(admin.StackedInline):
    model = StudyConfig
    verbose_name = _("Study Configuration")
    verbose_name_plural = _("Study Configurations")
    can_delete = False  # Không cho xóa config

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
    inlines = [StudyTranslationInline, StudyConfigInline, StudyMembershipInline]
    readonly_fields = ('created_at', 'updated_at')

@admin.register(StudyConfig)
class StudyConfigAdmin(admin.ModelAdmin):
    list_display = ('study',)
    search_fields = ('study__code', 'study__name')

@admin.register(StudyTranslation)
class StudyTranslationAdmin(admin.ModelAdmin):
    list_display = ('study', 'language_code', 'name')
    search_fields = ('study__code', 'language_code', 'name')
    list_filter = ('language_code',)

@admin.register(StudyMembership)
class StudyMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'study', 'role', 'assigned_at')
    search_fields = ('user__username', 'study__code', 'role__title')
    list_filter = ('role', 'assigned_at')
    readonly_fields = ('assigned_at',)