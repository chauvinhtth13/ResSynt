# backend/tenancy/models/user.py - FIXED VERSION
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


class User(AbstractUser):
    """Extended User model for ResSync platform"""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        SUSPENDED = 'suspended', 'Suspended'
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        verbose_name="Status"
    )
    
    # Study tracking
    last_study_accessed = models.ForeignKey(
        'Study', 
        null=True, 
        blank=True,
        on_delete=models.SET_NULL,
        related_name='last_accessed_by',
        verbose_name="Last Study Accessed"
    )
    
    last_study_accessed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last Study Access Time"
    )
    
    # Security fields
    must_change_password = models.BooleanField(
        default=False,
        verbose_name="Must Change Password"
    )
    
    password_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Password Changed At"
    )
    
    failed_login_attempts = models.IntegerField(
        default=0,
        verbose_name="Failed Login Attempts"
    )
    
    last_failed_login = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last Failed Login"
    )
    
    # Metadata
    notes = models.TextField(
        blank=True,
        verbose_name="Notes"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )
    
    created_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='users_created',
        verbose_name="Created By"
    )
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = "Authentication User"
        verbose_name_plural = "Authentication Users"
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
        return self.study_memberships.filter( # pyright: ignore[reportAttributeAccessIssue]
            study=study,
            is_active=True
        ).exists()
    
    def get_study_permissions(self, study):
        """Get all permissions for a specific study"""
        from django.db.models import Q
        
        memberships = self.study_memberships.filter( # pyright: ignore[reportAttributeAccessIssue]
            study=study,
            is_active=True
        ).select_related('role').prefetch_related(
            'role__role_permissions__permission'
        )
        
        permissions = set()
        for membership in memberships:
            for role_perm in membership.role.role_permissions.all():
                permissions.add(role_perm.permission.code)
        
        return permissions