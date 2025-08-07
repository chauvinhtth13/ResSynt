# apps/tenancy/admin.py

from django.contrib import admin
from .models import Study, StudyMembership, AuditLog, SystemSetting

@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'status', 'db_name', 'created_at', 'created_by')
    search_fields = ('code', 'name', 'db_name')

@admin.register(StudyMembership)
class StudyMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'study', 'role', 'date_joined')
    list_filter = ('role', 'study')
    search_fields = ('user__username', 'study__code')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'study', 'action')
    search_fields = ('user__username', 'study__code', 'action')

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')
    search_fields = ('key',)