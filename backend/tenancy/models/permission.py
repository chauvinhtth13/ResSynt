# backend/tenancy/models/permission.py - FIXED VERSION
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class RoleType:
    """Standard role types"""
    ADMIN = 'ADMIN'
    DATA_MANAGER = 'DM'
    RESEARCH_MANAGER = 'RM'
    MONITOR = 'MON'
    INVESTIGATOR = 'PI'
    VIEWER = 'VIEWER'
    RESEARCH_STAFF = 'RS'

    CHOICES = [
        (ADMIN, _('Administrator')),
        (DATA_MANAGER, _('Data Manager')),
        (RESEARCH_MANAGER, _('Clinical Research Coordinator')),
        (MONITOR, _('Monitor')),
        (INVESTIGATOR, _('Principal Investigator')),
        (VIEWER, _('Viewer')),
        (RESEARCH_STAFF, _('Research Staff')),
    ]


class Role(models.Model):
    """User roles within studies"""

    title = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name=_("Title"),
        validators=[RegexValidator(
            regex=r'^[A-Za-z0-9\s\-_]+$',
            message=_(
                "Title can only contain letters, numbers, spaces, hyphens and underscores")
        )]
    )

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_("Code"),
        validators=[RegexValidator(
            regex=r'^[A-Z_]+$',
            message=_("Code must be uppercase letters and underscores only")
        )]
    )

    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )

    is_system = models.BooleanField(
        default=False,
        verbose_name=_("Is System Role"),
        help_text=_("System roles cannot be modified or deleted")
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )

    class Meta:
        db_table = 'study_roles'  # FIXED: Added management schema
        verbose_name = _("Roles of Study")
        verbose_name_plural = _("Roles of Study")
        ordering = ['title']
        indexes = [
            models.Index(fields=['code'], name='idx_role_code'),
        ]

    def __str__(self):
        return self.title

    @classmethod
    def get_default_roles(cls):
        """Returns default role configurations"""
        return {
            RoleType.ADMIN: {
                'title': _('Administrator'),
                'code': 'ADMIN',
                'description': _('Full access to study management'),
                'permissions': [
                    Permission.DATA_VIEW, Permission.DATA_CREATE, Permission.DATA_UPDATE, Permission.DATA_DELETE, 
                    Permission.ANALYTICS_VIEW, Permission.REPORTS_VIEW, Permission.REPORTS_SCHEDULE, 
                    Permission.AUDIT_VIEW, 
                    Permission.STUDY_VIEW, Permission.STUDY_MANAGE, Permission.STUDY_USERS, Permission.STUDY_SITES,
                ]
            },
            RoleType.DATA_MANAGER: {
                'title': _('Data Manager'),
                'code': 'DM',
                'description': _('Manage study data and exports'),
                'priority': 20,
                'permissions': [
                    Permission.DATA_VIEW, Permission.DATA_CREATE, Permission.DATA_UPDATE, Permission.DATA_DELETE,
                    Permission.ANALYTICS_VIEW, Permission.REPORTS_VIEW,
                    Permission.AUDIT_VIEW,
                    Permission.STUDY_VIEW, Permission.STUDY_MANAGE, Permission.STUDY_USERS, Permission.STUDY_SITES,
                ]
            },
            RoleType.RESEARCH_MANAGER: {
                'title': _('Research Manager'),
                'code': 'RM',
                'description': _('Manage study operations and users'),
                'permissions': [
                    Permission.DATA_VIEW, Permission.DATA_CREATE, Permission.DATA_UPDATE,
                    Permission.REPORTS_VIEW, Permission.REPORTS_SCHEDULE,
                    Permission.STUDY_VIEW, Permission.STUDY_MANAGE, Permission.STUDY_USERS, Permission.STUDY_SITES,
                ]
            },
            RoleType.MONITOR: {
                'title': _('Monitor'),
                'code': 'MON',
                'description': _('View and audit study data'),
                'permissions': [
                    Permission.DATA_VIEW, Permission.ANALYTICS_VIEW,
                    Permission.REPORTS_VIEW, Permission.AUDIT_VIEW,
                ]
            },
            RoleType.INVESTIGATOR: {
                'title': _('Principal Investigator'),
                'code': 'PI',
                'description': _('View study progress and reports'),
                'permissions': [
                    Permission.DATA_VIEW, Permission.ANALYTICS_VIEW, Permission.REPORTS_VIEW,
                    Permission.STUDY_VIEW, Permission.STUDY_MANAGE, Permission.STUDY_USERS, Permission.STUDY_SITES,
                ]
            },
            RoleType.VIEWER: {
                'title': _('Viewer'),
                'code': 'VIEWER',
                'description': _('Read-only access'),
                'permissions': [
                    Permission.DATA_VIEW,
                ]
            },
            RoleType.RESEARCH_STAFF: {
                'title': _('Research Staff'),
                'code': 'RS',
                'description': _('Data entry and report viewing access with report scheduling'),
                'permissions': [
                    Permission.DATA_VIEW, Permission.DATA_CREATE, Permission.DATA_UPDATE,
                    Permission.REPORTS_VIEW, Permission.REPORTS_SCHEDULE
                ]
            },
        }

    @classmethod
    def initialize_roles(cls):
        """Create default roles with permissions"""
        Permission.initialize_permissions()  # Ensure permissions exist
        
        created_count = 0
        for role_type, config in cls.get_default_roles().items():
            role, created = cls.objects.get_or_create(
                code=config['code'],  # FIXED: Changed from role_type to config['code']
                defaults={
                    'title': str(config['title']),
                    'description': str(config['description']),
                    'is_system': True,
                }
            )
            
            if created:
                created_count += 1
                # Add permissions
                for perm_code in config['permissions']:
                    try:
                        permission = Permission.objects.get(code=perm_code)
                        RolePermission.objects.get_or_create(
                            role=role,
                            permission=permission
                        )
                    except Permission.DoesNotExist:
                        pass
        
        return created_count
    
class PermissionCategory:
    """Permission categories for grouping"""
    DATA = 'data'
    ANALYTICS = 'analytics'
    AUDIT = 'audit'
    MANAGEMENT = 'management'
    SYSTEM = 'system'

    CHOICES = [
        (DATA, _('Data Management')),
        (ANALYTICS, _('Analytics & Reports')),
        (AUDIT, _('Audit & Compliance')),
        (MANAGEMENT, _('Study Management')),
        (SYSTEM, _('System Administration')),
    ]


class Permission(models.Model):
    """System permissions with predefined defaults"""

    # Permission codes as constants
    # Data permissions
    DATA_VIEW = 'data.view'
    DATA_CREATE = 'data.create'
    DATA_UPDATE = 'data.update'
    DATA_DELETE = 'data.delete'

    # Analytics permissions
    ANALYTICS_VIEW = 'analytics.view'
    REPORTS_VIEW = 'reports.view'
    REPORTS_SCHEDULE = 'reports.schedule'

    # Audit permissions
    AUDIT_VIEW = 'audit.view'

    # Study management permissions
    STUDY_VIEW = 'study.view'
    STUDY_MANAGE = 'study.manage'
    STUDY_USERS = 'study.users'
    STUDY_SITES = 'study.sites'

    # System permissions
    SYSTEM_ADMIN = 'system.admin'
    SYSTEM_BACKUP = 'system.backup'
    SYSTEM_MONITOR = 'system.monitor'

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_("Code")
    )

    name = models.CharField(
        max_length=100,
        verbose_name=_("Name")
    )

    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )

    category = models.CharField(
        max_length=20,
        choices=PermissionCategory.CHOICES,
        db_index=True,
        verbose_name=_("Category")
    )

    is_dangerous = models.BooleanField(
        default=False,
        verbose_name=_("Is Dangerous"),
        help_text=_(
            "Marks permissions that can cause data loss or security issues")
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )

    class Meta:
        db_table = '"management"."study_permissions"'  # FIXED: Added management schema
        verbose_name = _("Permission of Study")
        verbose_name_plural = _("Permissions of Study")
        ordering = ['category', 'code']
        indexes = [
            models.Index(fields=['category', 'code'],
                         name='idx_perm_cat_code'),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    @classmethod
    def get_default_permissions(cls):
        """Returns default permissions to be created"""
        return [
            # Data permissions
            (cls.DATA_VIEW, _('View Data'), _('View study data'),
             PermissionCategory.DATA, False),
            (cls.DATA_CREATE, _('Create Data'), _(
                'Create new data entries'), PermissionCategory.DATA, False),
            (cls.DATA_UPDATE, _('Update Data'), _(
                'Update existing data'), PermissionCategory.DATA, False),
            (cls.DATA_DELETE, _('Delete Data'), _(
                'Delete data entries'), PermissionCategory.DATA, True),

            # Analytics permissions
            (cls.ANALYTICS_VIEW, _('View Analytics'), _(
                'View analytics dashboard'), PermissionCategory.ANALYTICS, False),
            (cls.REPORTS_VIEW, _('View Reports'), _(
                'View generated reports'), PermissionCategory.ANALYTICS, False),
            (cls.REPORTS_SCHEDULE, _('Schedule Reports'), _(
                'Schedule automatic reports'), PermissionCategory.ANALYTICS, False),

            # Audit permissions
            (cls.AUDIT_VIEW, _('View Audit Logs'), _(
                'View audit trail'), PermissionCategory.AUDIT, False),

            # Study management
            (cls.STUDY_VIEW, _('View Study'), _('View study information'),
             PermissionCategory.MANAGEMENT, False),
            (cls.STUDY_MANAGE, _('Manage Study'), _(
                'Manage study settings'), PermissionCategory.MANAGEMENT, True),
            (cls.STUDY_USERS, _('Manage Users'), _('Manage study users'),
             PermissionCategory.MANAGEMENT, True),
            (cls.STUDY_SITES, _('Manage Sites'), _('Manage study sites'),
             PermissionCategory.MANAGEMENT, True),

            # System permissions
            (cls.SYSTEM_ADMIN, _('System Admin'), _(
                'Full system access'), PermissionCategory.SYSTEM, True),
            (cls.SYSTEM_BACKUP, _('System Backup'), _(
                'Create system backups'), PermissionCategory.SYSTEM, True),
            (cls.SYSTEM_MONITOR, _('System Monitor'), _(
                'Monitor system health'), PermissionCategory.SYSTEM, False),
        ]

    @classmethod
    def initialize_permissions(cls):
        """Create default permissions if they don't exist"""
        created_count = 0
        for code, name, description, category, is_dangerous in cls.get_default_permissions():
            permission, created = cls.objects.get_or_create(
                code=code,
                defaults={
                    'name': str(name),
                    'description': str(description),
                    'category': category,
                    'is_dangerous': is_dangerous,
                }
            )
            if created:
                created_count += 1
        return created_count


class RolePermission(models.Model):
    """Many-to-many relationship between Roles and Permissions"""

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="role_permissions",
        verbose_name=_("Role")
    )

    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="permission_roles",
        verbose_name=_("Permission")
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )

    class Meta:
        db_table = '"management"."study_role_permissions"'  # FIXED: Added management schema
        verbose_name = _("Role Permission")
        verbose_name_plural = _("Role Permissions")
        constraints = [
            models.UniqueConstraint(
                fields=['role', 'permission'],
                name='unique_role_permission'
            )
        ]
        indexes = [
            models.Index(fields=['role'], name='idx_roleperm_role'),
            models.Index(fields=['permission'],
                         name='idx_roleperm_permission'),
        ]

    def __str__(self):
        return f"{self.role.title} - {self.permission.name}"


class StudyMembership(models.Model):
    """User membership and roles in studies"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_memberships",
        verbose_name=_("User")
    )

    study = models.ForeignKey(
        'Study',
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("Study")
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="study_memberships",
        verbose_name=_("Role")
    )

    # Site-specific access (null = all sites in study)
    study_sites = models.ManyToManyField(
        'StudySite',
        blank=True,
        related_name="memberships",
        verbose_name=_("Study Sites"),
        help_text=_(
            "Specific sites within the study. Leave empty for all sites.")
    )

    # Access control
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Is Active")
    )

    can_access_all_sites = models.BooleanField(
        default=False,
        verbose_name=_("Can Access All Sites"),
        help_text=_("If true, user has access to all sites in the study")
    )

    # Dates
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Assigned At")
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Expires At"),
        help_text=_("Access expiration date")
    )

    # Metadata
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="memberships_assigned",
        verbose_name=_("Assigned By")
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )

    class Meta:
        db_table = '"management"."study_memberships"'  # FIXED: Added management schema
        verbose_name = _("Study Membership")
        verbose_name_plural = _("Study Memberships")
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'study', 'role'],
                name='unique_user_study_role'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'study', 'is_active'],
                         name='idx_membership_user_study'),
            models.Index(fields=['study', 'is_active'],
                         name='idx_membership_study'),
            models.Index(fields=['expires_at'],
                         name='idx_membership_expires'),
        ]

    def __str__(self):
        sites_str = "All sites" if self.can_access_all_sites else f"{self.study_sites.count()} sites"
        return f"{self.user.username} - {self.study.code} - {self.role.title} ({sites_str})"

    def clean(self):
        """Validate membership data"""
        # FIXED: Only check study_sites if the instance has been saved (has pk)
        if self.pk:  # Only validate if instance is saved
            if self.can_access_all_sites and self.study_sites.exists():
                raise ValidationError(
                    _("Cannot specify sites when 'can_access_all_sites' is True")
                )

            # Verify sites belong to the study
            if self.study_sites.exists():
                invalid_sites = self.study_sites.exclude(study=self.study)
                if invalid_sites.exists():
                    raise ValidationError(
                        _("Selected sites must belong to the study")
                    )

        super().clean()

    def has_site_access(self, site_id):
        """Check if user has access to specific site"""
        if self.can_access_all_sites:
            return True
        return self.study_sites.filter(site_id=site_id).exists()

    def is_expired(self):
        """Check if membership is expired"""
        from django.utils import timezone
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False