# backend/tenancy/models/study.py - COMPLETE
"""
Study and Site models
"""
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from parler.models import TranslatableModel, TranslatedFields
import logging

logger = logging.getLogger(__name__)

class Study(TranslatableModel):
    """
    Study/Research Project - Main tenant entity
    Each study has its own database
    """
    
    class Status(models.TextChoices):
        PLANNING = 'planning', 'Planning'
        ACTIVE = 'active', 'Active'
        ARCHIVED = 'archived', 'Archived'

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="Study Code",
        help_text="Unique code for the study (e.g., 43EN, 44EN) - uppercase letters, numbers, underscores only",
        validators=[RegexValidator(
            regex=r'^[A-Z0-9_]+$',
            message="Code must contain only uppercase letters, numbers, and underscores"
        )]
    )
    
    db_name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="Database Name",
        help_text="Auto-generated from study code (e.g., db_study_43en). Leave blank for auto-generation.",
        blank=True,
        validators=[RegexValidator(
            regex=r'^db_study_[a-z0-9_]+$',
            message="Database name must start with 'db_study_' and contain only lowercase letters, numbers, and underscores"
        )]
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNING,
        db_index=True,
        verbose_name="Status",
        help_text="Study status. Archived studies won't be loaded by the system."
    )
    
    # Relationships
    sites = models.ManyToManyField(
        "Site",
        through="StudySite",
        related_name="studies",
        verbose_name="Sites"
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='studies_created',
        verbose_name="Created By"
    )

    # Translatable fields
    translations = TranslatedFields(
        name=models.TextField(
            max_length=255,
            db_index=True,
            verbose_name="Study Name"
        )
    )

    class Meta(TranslatableModel.Meta):
        db_table = 'study_information'
        verbose_name = "Study Information"
        verbose_name_plural = "Study Information"
        ordering = ['-created_at', 'code']
        indexes = [
            models.Index(fields=['status', 'code'], name='idx_study_status_code'),
        ]

    def clean(self):
        """Validate and auto-generate db_name from code"""
        super().clean()
        
        if not self.code:
            raise ValidationError({'code': 'Study code is required.'})
        
        if not self.db_name:
            self.db_name = self.generate_db_name()
        
        expected_db_name = self.generate_db_name()
        if self.db_name != expected_db_name:
            raise ValidationError({
                'db_name': f"Database name must be '{expected_db_name}' for study code '{self.code}'. "
                           f"Leave blank for auto-generation."
            })

    def save(self, *args, **kwargs):
        """Override save to auto-generate db_name"""
        if not self.db_name:
            self.db_name = self.generate_db_name()
        
        self.full_clean()
        
        super().save(*args, **kwargs)

    def generate_db_name(self) -> str:
        """Generate database name from study code"""
        if not self.code:
            raise ValidationError("Study code is required")
        
        # Use settings.STUDY_DB_PREFIX (correct)
        prefix = getattr(settings, 'STUDY_DB_PREFIX', 'db_study_')
        return f"{prefix}{self.code.lower()}"

    def __str__(self):
        name = self.safe_translation_getter('name', any_language=True)
        return f"{self.code} - {name}" if name else self.code


class Site(TranslatableModel):
    """Research Site/Location"""
    
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="Site Code",
        validators=[RegexValidator(
            regex=r'^[A-Z0-9_]+$',
            message="Code must contain only uppercase letters, numbers, and underscores"
        )]
    )
    
    abbreviation = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        verbose_name="Abbreviation"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    translations = TranslatedFields(
        name=models.TextField(
            max_length=255,
            verbose_name="Name"
        ),
    )

    class Meta(TranslatableModel.Meta):
        db_table = 'study_sites'
        verbose_name = "Study Sites"
        verbose_name_plural = "Study Sites"
        ordering = ['code']
        indexes = [
            models.Index(fields=['code'], name='idx_site_code'),
        ]

    def __str__(self):
        name = self.safe_translation_getter('name', any_language=True)
        return f"{self.code} - {name}" if name else self.code


class StudySite(models.Model):
    """Link between Study and Site with specific configuration"""
    
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name="study_sites",
        verbose_name="Study"
    )
    
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name="site_studies",
        verbose_name="Site"
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
        db_table = 'study_site_links'
        verbose_name = "Study-Site Link"
        verbose_name_plural = "Study-Site Links"
        constraints = [
            models.UniqueConstraint(
                fields=['study', 'site'],
                name='unique_study_site'
            )
        ]
        indexes = [
            models.Index(fields=['study'], name='idx_studysite'),
            models.Index(fields=["site"], name="ix_studysite_site"),
        ]

    def __str__(self):
        return f"{self.study.code} - {self.site.code}"
    
# ==========================================
# SIGNALS - AUTO-CREATE DATABASE
# ==========================================

@receiver(post_save, sender=Study)
def auto_create_study_database(sender, instance, created, **kwargs):
    """
    Automatically create database and initialize roles when Study is created/activated
    
    This signal fires after a Study is saved and will:
    1. Create PostgreSQL database if it doesn't exist
    2. Create 'data' schema in the database
    3. Register database in Django's connections
    4. Initialize study roles and permissions
    """
    # Determine if we should create database
    should_create = False
    action = None
    
    if created:
        # New study created
        should_create = True
        action = "created"
    else:
        # Check if status changed from ARCHIVED to ACTIVE/PLANNING
        try:
            old_instance = Study.objects.get(pk=instance.pk)
            if old_instance.status == Study.Status.ARCHIVED and \
               instance.status in [Study.Status.ACTIVE, Study.Status.PLANNING]:
                should_create = True
                action = "reactivated"
        except Study.DoesNotExist:
            pass
    
    if not should_create:
        return
    
    db_name = instance.db_name
    
    logger.debug("=" * 70)
    logger.debug(f"AUTO-CREATING DATABASE FOR STUDY {instance.code}")
    logger.debug("=" * 70)
    logger.debug(f"Action: {action}")
    logger.debug(f"Database: {db_name}")
    
    try:
        from backends.tenancy.utils.db_study_creator import DatabaseStudyCreator
        
        # Check if database already exists
        exists = DatabaseStudyCreator.database_exists(db_name)
        
        if exists:
            logger.debug(f"Database '{db_name}' already exists")
            
            # Ensure schema exists
            from backends.tenancy.db_loader import study_db_manager
            schema_ok = study_db_manager.ensure_schema_exists(db_name)
            
            if schema_ok:
                logger.debug(f"Schema '{settings.STUDY_DB_SCHEMA}' verified")
            
            # Register in Django
            _register_database_dynamically(instance)
            
        else:
            logger.debug(f"📦 Creating database '{db_name}'...")
            
            # Create database
            success, message = DatabaseStudyCreator.create_study_database(db_name)
            
            if success:
                logger.debug(f"{message}")
                
                # Ensure schema
                from backends.tenancy.db_loader import study_db_manager
                study_db_manager.ensure_schema_exists(db_name)
                
                # Register in Django
                _register_database_dynamically(instance)
                
                logger.debug("=" * 70)
                logger.debug(f"STUDY {instance.code} DATABASE READY")
                logger.debug("=" * 70)
                logger.debug(f"Database: {db_name}")
                logger.debug(f"Schema: {settings.STUDY_DB_SCHEMA}")
                logger.debug("")
                logger.debug("Next steps:")
                logger.debug(f"  1. Run: python manage.py migrate --database {db_name}")
                logger.debug(f"  2. Create API: python manage.py create_study_api {instance.code}")
                logger.debug(f"  3. Restart Django server")
                logger.debug("=" * 70)
                
            else:
                logger.error(f"Failed to create database: {message}")
                return
        
        # Auto-initialize roles
        _auto_initialize_roles(instance)
        
    except Exception as e:
        logger.error(f"Error in auto-create database: {e}", exc_info=True)


def _register_database_dynamically(study: Study):
    """
    Dynamically register database in Django's connections
    
    Args:
        study: Study instance
    """
    db_name = study.db_name
    
    try:
        from django.db import connections
        from config.settings import DatabaseConfig
        
        # Check if already registered
        if db_name in connections.databases:
            logger.debug(f"Database {db_name} already registered")
            return
        
        # Get config
        db_config = DatabaseConfig.get_study_db_config(db_name)
        
        # Register in Django
        connections.databases[db_name] = db_config
        
        # Register in study_db_manager
        from backends.tenancy.db_loader import study_db_manager
        study_db_manager.add_study_db(db_name)
        
        logger.debug(f"Registered database: {db_name}")
        
    except Exception as e:
        logger.error(f"Error registering database {db_name}: {e}", exc_info=True)


def _auto_initialize_roles(study: Study):
    """
    Auto-initialize study roles and permissions
    
    Args:
        study: Study instance
    """
    try:
        from backends.tenancy.utils.role_manager import StudyRoleManager
        
        logger.debug(f"Initializing roles for study {study.code}...")
        
        result = StudyRoleManager.initialize_study(
            study.code,
            force=False
        )
        
        if 'error' in result:
            logger.warning(f"Could not initialize roles: {result['error']}")
        else:
            logger.debug(
                f"Roles initialized: "
                f"{result.get('groups_created', 0)} groups, "
                f"{result.get('permissions_assigned', 0)} permissions"
            )
        
    except Exception as e:
        logger.warning(f"Could not initialize roles: {e}")


@receiver(pre_delete, sender=Study)
def warn_before_study_deletion(sender, instance, **kwargs):
    """
    Warn before deleting a study
    Does NOT delete the database (manual cleanup required)
    """
    logger.warning("=" * 70)
    logger.warning(f"STUDY {instance.code} IS BEING DELETED")
    logger.warning("=" * 70)
    logger.warning(f"Database: {instance.db_name}")
    logger.warning("")
    logger.warning("NOTE: The PostgreSQL database is NOT automatically deleted.")
    logger.warning("To manually delete the database, run:")
    logger.warning(f"  python manage.py shell")
    logger.warning(f"  >>> from backends.tenancy.utils.db_study_creator import DatabaseStudyCreator")
    logger.warning(f"  >>> DatabaseStudyCreator.drop_study_database('{instance.db_name}', force=True)")
    logger.warning("=" * 70)