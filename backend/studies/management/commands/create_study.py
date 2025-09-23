# backend/studies/management/commands/create_study.py
"""
Management command to create a new study with database and app structure
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from backend.tenancy.models import Study, Site
import os
import shutil
from pathlib import Path


class Command(BaseCommand):
    help = 'Create a new study with database and app structure'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'study_code',
            type=str,
            help='Study code (e.g., 45EN)'
        )
        parser.add_argument(
            '--name',
            type=str,
            default='',
            help='Study name'
        )
        parser.add_argument(
            '--copy-from',
            type=str,
            help='Copy structure from existing study (e.g., 43EN)'
        )
    
    def handle(self, *args, **options):
        study_code = options['study_code'].upper()
        study_name = options['name'] or f'Study {study_code}'
        
        self.stdout.write(f'\nCreating new study: {study_code}')
        self.stdout.write(f'Name: {study_name}')
        
        # 1. Create Study record in management database
        db_name = f'db_study_{study_code.lower()}'
        
        if Study.objects.filter(code=study_code).exists():
            raise CommandError(f'Study {study_code} already exists')
        
        study = Study.objects.create(
            code=study_code,
            db_name=db_name,
            status=Study.Status.PLANNING
        )
        study.set_current_language('en')
        study.name = study_name
        study.save()
        
        self.stdout.write(self.style.SUCCESS(f'✓ Study record created'))
        
        # 2. Create app directory structure
        self.create_app_structure(study_code, options.get('copy_from'))
        
        # 3. Create database
        self.stdout.write(f'\nTo create the database, run:')
        self.stdout.write(
            self.style.WARNING(
                f'  python manage.py migrate_study --study={study_code} --create-db'
            )
        )
        
        # 4. Update settings
        self.stdout.write(f'\nDon\'t forget to add the app to settings.py:')
        self.stdout.write(
            self.style.WARNING(
                f'  "backend.studies.study_{study_code.lower()}",'
            )
        )
    
    def create_app_structure(self, study_code, copy_from=None):
        """Create the app directory structure for the study"""
        app_name = f'study_{study_code.lower()}'
        app_path = Path(settings.BASE_DIR) / 'backend' / 'studies' / app_name
        
        if app_path.exists():
            self.stdout.write(
                self.style.WARNING(f'App directory {app_path} already exists')
            )
            return
        
        if copy_from:
            # Copy from existing study
            source_app = f'study_{copy_from.lower()}'
            source_path = Path(settings.BASE_DIR) / 'backend' / 'studies' / source_app
            
            if not source_path.exists():
                raise CommandError(f'Source study app {source_app} does not exist')
            
            # Copy directory
            shutil.copytree(source_path, app_path)
            
            # Update app config
            self.update_app_files(app_path, study_code)
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ App structure copied from {copy_from}')
            )
        else:
            # Create new structure
            app_path.mkdir(parents=True, exist_ok=True)
            
            # Create __init__.py
            init_file = app_path / '__init__.py'
            init_file.write_text(
                f"default_app_config = 'backend.studies.{app_name}.apps.Study{study_code.title()}Config'"
            )
            
            # Create apps.py
            apps_file = app_path / 'apps.py'
            apps_file.write_text(self.get_apps_template(study_code))
            
            # Create models.py
            models_file = app_path / 'models.py'
            models_file.write_text(self.get_models_template(study_code))
            
            # Create admin.py
            admin_file = app_path / 'admin.py'
            admin_file.write_text(self.get_admin_template(study_code))
            
            # Create migrations directory
            migrations_dir = app_path / 'migrations'
            migrations_dir.mkdir(exist_ok=True)
            (migrations_dir / '__init__.py').touch()
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ App structure created at {app_path}')
            )
    
    def update_app_files(self, app_path, study_code):
        """Update app files with new study code"""
        app_name = f'study_{study_code.lower()}'
        
        # Update apps.py
        apps_file = app_path / 'apps.py'
        if apps_file.exists():
            content = apps_file.read_text()
            # Replace class name and app label
            content = self.get_apps_template(study_code)
            apps_file.write_text(content)
        
        # Update models.py - replace app_label
        models_file = app_path / 'models.py'
        if models_file.exists():
            content = models_file.read_text()
            # Replace all occurrences of old app_label
            import re
            content = re.sub(
                r"app_label = 'study_\w+'",
                f"app_label = '{app_name}'",
                content
            )
            models_file.write_text(content)
        
        # Clear migrations except __init__.py
        migrations_dir = app_path / 'migrations'
        if migrations_dir.exists():
            for file in migrations_dir.glob('*.py'):
                if file.name != '__init__.py':
                    file.unlink()
    
    def get_apps_template(self, study_code):
        app_name = f'study_{study_code.lower()}'
        return f'''from django.apps import AppConfig


class Study{study_code.title()}Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.studies.{app_name}'
    label = '{app_name}'
    verbose_name = "Study {study_code}"
    
    def ready(self):
        pass
'''
    
    def get_models_template(self, study_code):
        app_name = f'study_{study_code.lower()}'
        return f'''"""
Models for Study {study_code}
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class BaseStudyModel(models.Model):
    """Base model with common fields"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.IntegerField(verbose_name="Created By User ID")
    updated_by = models.IntegerField(null=True, blank=True)
    
    class Meta:
        abstract = True


class ExampleModel(BaseStudyModel):
    """Example model for Study {study_code}"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'example'
        app_label = '{app_name}'
    
    def __str__(self):
        return self.name
'''
    
    def get_admin_template(self, study_code):
        return f'''"""
Admin configuration for Study {study_code}
"""
from django.contrib import admin
from .models import ExampleModel


@admin.register(ExampleModel)
class ExampleModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user.id
        obj.updated_by = request.user.id
        super().save_model(request, obj, form, change)
'''