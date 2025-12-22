# backend/tenancy/models/study.py
"""
Study and Site models - Optimized version
"""
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)


class Study(models.Model):
    """Study/Research Project"""
    
    class Status(models.TextChoices):
        PLANNING = 'planning', 'Planning'
        ACTIVE = 'active', 'Active'
        ARCHIVED = 'archived', 'Archived'

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        validators=[RegexValidator(
            regex=r'^[A-z0-9_]+$',
            message="Only uppercase letters, numbers, underscores"
        )]
    )

    name_vi = models.TextField(max_length=255, verbose_name='Name (Vietnamese)')
    name_en = models.TextField(max_length=255, verbose_name='Name (English)')
    
    db_name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        blank=True,
        verbose_name="Database Name"
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNING,
        db_index=True
    )
    
    sites = models.ManyToManyField(
        "Site",
        through="StudySite",
        related_name="studies",
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='studies_created'
    )

    class Meta:
        db_table = 'study_information'
        verbose_name = "Studies Information"
        verbose_name_plural = "Studies Information"
        ordering = ['code']  # Simple consistent ordering

    def clean(self):
        """Validate and generate db_name"""
        super().clean()
        
        if not self.db_name:
            self.db_name = self.generate_db_name()

    def save(self, *args, **kwargs):
        """Save with auto db_name"""
        if not self.db_name:
            self.db_name = self.generate_db_name()
        
        self.full_clean()
        super().save(*args, **kwargs)

    def generate_db_name(self) -> str:
        """Generate database name"""
        prefix = getattr(settings, 'STUDY_DB_PREFIX', 'db_study_')
        return f"{prefix}{self.code.lower()}"
    
    @property
    def name(self):
        from django.utils import translation
        lang = translation.get_language()
        if lang == 'en':
            return self.name_en or self.name_vi
        return self.name_vi or self.name_en

    def __str__(self):
        return f"Study {self.code}"
    
    # ==========================================
    # NEW METHODS - STATISTICS AND HEALTH
    # ==========================================
    
    def get_active_users_count(self) -> int:
        """Count active users in this study"""
        from backends.tenancy.models import StudyMembership
        return StudyMembership.objects.filter(
            is_active=True, 
            user__is_active=True,
            study=self
        ).values('user').distinct().count()
    
    def get_sites_list(self) -> list:
        """Get list of site codes"""
        from backends.tenancy.models import StudySite
        return list(StudySite.objects.filter(study=self).values_list('site__code', flat=True))
    
    def get_role_distribution(self) -> dict:
        """Get distribution of roles in this study"""
        from django.db.models import Count
        from backends.tenancy.models import StudyMembership
        return dict(
            StudyMembership.objects.filter(study=self, is_active=True)
            .values('group__name')
            .annotate(count=Count('id'))
            .values_list('group__name', 'count')
        )


class Site(models.Model):
    """Research Site"""
    
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        validators=[RegexValidator(
            regex=r'^[A-Z0-9_]+$',
            message="Only uppercase letters, numbers, underscores"
        )]
    )
    
    abbreviation = models.CharField(
        max_length=10,
        unique=True,
        db_index=True
    )

    
    name_vi = models.TextField(max_length=255, verbose_name='Name (Vietnamese)')
    name_en = models.TextField(max_length=255, verbose_name='Name (English)')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sites_created'
    )

    class Meta:
        db_table = 'study_sites'
        verbose_name = "Study Sites"
        verbose_name_plural = "Study Sites"
        ordering = ['id','code']

    @property
    def name(self):
        from django.utils import translation
        lang = translation.get_language()
        if lang == 'en':
            return self.name_en or self.name_vi
        return self.name_vi or self.name_en

    def __str__(self):
        abbreviation= self.abbreviation if self.abbreviation else ''
        return f"{self.code} - {abbreviation}" if abbreviation else self.code


# In study.py
class StudySite(models.Model):
    """Link between Study and Site"""
    
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name="study_sites"
    )
    
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name="site_studies"
    )
    
    # Add this field if you want to track who created the link
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='study_sites_created'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

    def __str__(self):
        return f"{self.study.code} - {self.site.code}"
    




# Single signal for database creation
@receiver(post_save, sender=Study)
def handle_study_database(sender, instance, created, **kwargs):
    if not created:
        return
    
    from django.db import transaction
    
    def _create_database():
        try:
            from backends.tenancy.utils.db_study_creator import DatabaseStudyCreator
            from backends.tenancy.utils.role_manager import StudyRoleManager
            
            if not DatabaseStudyCreator.database_exists(instance.db_name):
                success, message = DatabaseStudyCreator.create_study_database(instance.db_name)
                if not success:
                    logger.error(f"Failed to create database: {message}")
                    return
            
            StudyRoleManager.initialize_study(instance.code)
            
        except Exception as e:
            logger.error(f"Error in database creation: {e}")
    
    # Delay until transaction commits
    transaction.on_commit(_create_database)