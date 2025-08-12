from django.contrib import admin
from .models import Study, StudyMembership, Role

@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "database_name", "status", "created_at")
    search_fields = ("code", "name", "database_name")
    list_filter = ("status",)

@admin.register(StudyMembership)
class StudyMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "study", "role", "created_at")
    search_fields = ("user__username", "study__code")
    list_filter = ("role",)
    readonly_fields = ("created_at",)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("key", "label", "priority")
    search_fields = ("key", "label")