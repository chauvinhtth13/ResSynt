# backend/tenancy/models/permission.py - FIXED VERSION
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError


class RoleType:
    """Standard role types"""
    ADMIN = 'ADMIN'
    DATA_MANAGER = 'DM'
    RESEARCH_MANAGER = 'RM'
    RESEARCH_MONITOR = 'MON'
    INVESTIGATOR = 'PI'
    RESEARCH_STAFF = 'RS'

    CHOICES = [
        (ADMIN, 'Administrator'),
        (DATA_MANAGER, 'Data Manager'),
        (RESEARCH_MANAGER, 'Research Manager'),
        (RESEARCH_MONITOR, 'Research Monitor'),
        (INVESTIGATOR, 'Principal Investigator'),
        (RESEARCH_STAFF, 'Research Staff'),
    ]


class Role(models.Model):
    """User roles within studies"""

    title = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="Title",
        validators=[RegexValidator(
            regex=r'^[A-Za-z0-9\s\-_]+$',
            message="Title can only contain letters, numbers, spaces, hyphens and underscores"
        )]
    )

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="Code",
        validators=[RegexValidator(
            regex=r'^[A-Z_]+$',
            message="Code must be uppercase letters and underscores only"
        )]
    )

    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )

    is_system = models.BooleanField(
        default=False,
        verbose_name="Is System Role",
        help_text="System roles cannot be modified or deleted"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    class Meta:
        db_table = 'study_roles'
        verbose_name = "Roles of Study"
        verbose_name_plural = "Roles of Study"
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
                'title': 'Administrator',
                'code': 'ADMIN',
                'description': 'Full access to study management',
                'permissions': [
                    Permission.DATA_VIEW, Permission.DATA_CREATE, Permission.DATA_UPDATE, Permission.DATA_DELETE, 
                    Permission.ANALYTICS_VIEW, Permission.REPORTS_VIEW, Permission.REPORTS_SCHEDULE, 
                    Permission.AUDIT_VIEW, 
                    Permission.STUDY_VIEW, Permission.STUDY_MANAGE, Permission.STUDY_USERS, Permission.STUDY_SITES,
                ]
            },
            RoleType.DATA_MANAGER: {
                'title': 'Data Manager',
                'code': 'DM',
                'description': 'Manage study data and exports',
                'priority': 20,
                'permissions': [
                    Permission.DATA_VIEW, Permission.DATA_CREATE, Permission.DATA_UPDATE, Permission.DATA_DELETE,
                    Permission.ANALYTICS_VIEW, Permission.REPORTS_VIEW,
                    Permission.AUDIT_VIEW,
                    Permission.STUDY_VIEW, Permission.STUDY_MANAGE, Permission.STUDY_USERS, Permission.STUDY_SITES,
                ]
            },
            RoleType.RESEARCH_MANAGER: {
                'title': 'Research Manager',
                'code': 'RM',
                'description': 'Manage study operations and users',
                'permissions': [
                    Permission.DATA_VIEW, Permission.DATA_CREATE, Permission.DATA_UPDATE,
                    Permission.REPORTS_VIEW, Permission.REPORTS_SCHEDULE,
                    Permission.STUDY_VIEW, Permission.STUDY_MANAGE, Permission.STUDY_USERS, Permission.STUDY_SITES,
                ]
            },
            RoleType.RESEARCH_MONITOR: {
                'title': 'Research Monitor',
                'code': 'MON',
                'description': 'View and audit study data',
                'permissions': [
                    Permission.DATA_VIEW, Permission.ANALYTICS_VIEW,
                    Permission.REPORTS_VIEW, Permission.AUDIT_VIEW,
                ]
            },
            RoleType.INVESTIGATOR: {
                'title': 'Principal Investigator',
                'code': 'PI',
                'description': 'View study progress and reports',
                'permissions': [
                    Permission.DATA_VIEW, Permission.ANALYTICS_VIEW, Permission.REPORTS_VIEW,
                    Permission.STUDY_VIEW, Permission.STUDY_MANAGE, Permission.STUDY_USERS, Permission.STUDY_SITES,
                ]
            },
            RoleType.RESEARCH_STAFF: {
                'title': 'Research Staff',
                'code': 'RS',
                'description': 'Data entry and report viewing access with report scheduling',
                'permissions': [
                    Permission.DATA_VIEW, Permission.DATA_CREATE, Permission.DATA_UPDATE,
                    Permission.REPORTS_VIEW, Permission.REPORTS_SCHEDULE
                ]
            },
        }

    @classmethod
    def initialize_roles(cls):
        """Create default roles with permissions"""
        Permission.initialize_permissions()
        
        created_count = 0
        for role_type, config in cls.get_default_roles().items():
            role, created = cls.objects.get_or_create(
                code=config['code'],
                defaults={
                    'title': str(config['title']),
                    'description': str(config['description']),
                    'is_system': True,
                }
            )
            
            if created:
                created_count += 1
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
        (DATA, 'Data Management'),
        (ANALYTICS, 'Analytics & Reports'),
        (AUDIT, 'Audit & Compliance'),
        (MANAGEMENT, 'Study Management'),
        (SYSTEM, 'System Administration'),
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
        verbose_name="Code"
    )

    name = models.CharField(
        max_length=100,
        verbose_name="Name"
    )

    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )

    category = models.CharField(
        max_length=20,
        choices=PermissionCategory.CHOICES,
        db_index=True,
        verbose_name="Category"
    )

    is_dangerous = models.BooleanField(
        default=False,
        verbose_name="Is Dangerous",
        help_text="Marks permissions that can cause data loss or security issues"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    class Meta:
        db_table = '"management"."study_permissions"'
        verbose_name = "Permission of Study"
        verbose_name_plural = "Permissions of Study"
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
            (cls.DATA_VIEW, 'View Data', 'View study data',
             PermissionCategory.DATA, False),
            (cls.DATA_CREATE, 'Create Data',
             'Create new data entries', PermissionCategory.DATA, False),
            (cls.DATA_UPDATE, 'Update Data',
             'Update existing data', PermissionCategory.DATA, False),
            (cls.DATA_DELETE, 'Delete Data',
             'Delete data entries', PermissionCategory.DATA, True),

            # Analytics permissions
            (cls.ANALYTICS_VIEW, 'View Analytics',
             'View analytics dashboard', PermissionCategory.ANALYTICS, False),
            (cls.REPORTS_VIEW, 'View Reports',
             'View generated reports', PermissionCategory.ANALYTICS, False),
            (cls.REPORTS_SCHEDULE, 'Schedule Reports',
             'Schedule automatic reports', PermissionCategory.ANALYTICS, False),

            # Audit permissions
            (cls.AUDIT_VIEW, 'View Audit Logs',
             'View audit trail', PermissionCategory.AUDIT, False),

            # Study management
            (cls.STUDY_VIEW, 'View Study', 'View study information',
             PermissionCategory.MANAGEMENT, False),
            (cls.STUDY_MANAGE, 'Manage Study',
             'Manage study settings', PermissionCategory.MANAGEMENT, True),
            (cls.STUDY_USERS, 'Manage Users', 'Manage study users',
             PermissionCategory.MANAGEMENT, True),
            (cls.STUDY_SITES, 'Manage Sites', 'Manage study sites',
             PermissionCategory.MANAGEMENT, True),

            # System permissions
            (cls.SYSTEM_ADMIN, 'System Admin',
             'Full system access', PermissionCategory.SYSTEM, True),
            (cls.SYSTEM_BACKUP, 'System Backup',
             'Create system backups', PermissionCategory.SYSTEM, True),
            (cls.SYSTEM_MONITOR, 'System Monitor',
             'Monitor system health', PermissionCategory.SYSTEM, False),
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
        verbose_name="Role"
    )

    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="permission_roles",
        verbose_name="Permission"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )

    class Meta:
        db_table = '"management"."study_role_permissions"'
        verbose_name = "Role Permission"
        verbose_name_plural = "Role Permissions"
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
        verbose_name="User"
    )

    study = models.ForeignKey(
        'Study',
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="Study"
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="study_memberships",
        verbose_name="Role"
    )

    study_sites = models.ManyToManyField(
        'StudySite',
        blank=True,
        related_name="memberships",
        verbose_name="Study Sites",
        help_text="Specific sites within the study. Leave empty for all sites."
    )

    # Access control
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Is Active"
    )

    can_access_all_sites = models.BooleanField(
        default=False,
        verbose_name="Can Access All Sites",
        help_text="If true, user has access to all sites in the study"
    )

    # Dates
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Assigned At"
    )

    # Metadata
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="memberships_assigned",
        verbose_name="Assigned By"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    class Meta:
        db_table = '"management"."study_memberships"'
        verbose_name = "Study Membership"
        verbose_name_plural = "Study Memberships"
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'study', 'role'],
                name='unique_user_study_role'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'study', 'is_active'], name='idx_membership_user_study'),
            models.Index(fields=['study', 'is_active'], name='idx_membership_study'),
        ]

    def __str__(self):
        if self.can_access_all_sites or not self.study_sites.exists():
            sites_str = "All sites"
        else:
            sites_str = ", ".join([s.site.code for s in self.study_sites.all()])
        return f"{self.user.username} - {self.study.code} - {self.role.title} ({sites_str})"

    def clean(self):
        """Validate membership data"""
        if self.pk:
            if self.can_access_all_sites and self.study_sites.exists():
                raise ValidationError("Cannot specify sites when 'can_access_all_sites' is True")
            if self.study_sites.exists():
                invalid_sites = self.study_sites.exclude(study=self.study)
                if invalid_sites.exists():
                    raise ValidationError("Selected sites must belong to the study")
        super().clean()

    def has_site_access(self, site_id):
        """Check if user has access to specific site"""
        if self.can_access_all_sites or not self.study_sites.exists():
            return True
        return self.study_sites.filter(site_id=site_id).exists()