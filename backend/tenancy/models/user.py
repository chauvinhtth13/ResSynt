# backend/tenancy/models/user.py - FIXED VERSION
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Extended User model for ResSync platform"""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        SUSPENDED = 'suspended', _('Suspended')
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        verbose_name=_("Status")
    )
    
    # Study tracking
    last_study_accessed = models.ForeignKey(
        'Study', 
        null=True, 
        blank=True,
        on_delete=models.SET_NULL,
        related_name='last_accessed_by',
        verbose_name=_("Last Study Accessed")
    )
    
    last_study_accessed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Study Access Time")
    )
    
    # Security fields
    must_change_password = models.BooleanField(
        default=False,
        verbose_name=_("Must Change Password")
    )
    
    password_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Password Changed At")
    )
    
    failed_login_attempts = models.IntegerField(
        default=0,
        verbose_name=_("Failed Login Attempts")
    )
    
    last_failed_login = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Failed Login")
    )
    
    # Metadata
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes")
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )
    
    created_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='users_created',
        verbose_name=_("Created By")
    )
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = _("Authentication User")
        verbose_name_plural = _("Authentication Users")
        indexes = [
            models.Index(fields=['username'], name='idx_user_username'),
            models.Index(fields=['email'], name='idx_user_email'),
            models.Index(fields=['status'], name='idx_user_status'),
        ]
        
    def __str__(self):
        return self.get_full_name() or self.username
    
    def get_full_name(self):
        """Return full name"""
        parts = [self.first_name, self.last_name]
        return ' '.join(part for part in parts if part).strip()
    
    def has_study_access(self, study):
        """Check if user has access to a specific study"""
        return self.study_memberships.filter( # type: ignore
            study=study,
            is_active=True  # FIXED: Added is_active check
        ).exists()
    
    def get_study_permissions(self, study):
        """Get all permissions for a specific study"""
        from django.db.models import Q
        
        memberships = self.study_memberships.filter( # type: ignore
            study=study,
            is_active=True  # FIXED: Added is_active check
        ).select_related('role').prefetch_related(
            'role__role_permissions__permission'
        )
        
        permissions = set()
        for membership in memberships:
            for role_perm in membership.role.role_permissions.all():
                permissions.add(role_perm.permission.code)
        
        return permissions