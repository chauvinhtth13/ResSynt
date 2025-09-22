# backend/studies/utils.py
"""
Utility functions for working with study models and databases
"""
from django.apps import apps
from django.db import connections, transaction
from backend.tenancy.db_loader import add_study_db
from backend.tenancy.db_router import set_current_db, get_current_db
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class StudyModelLoader:
    """Dynamically load and work with study models"""
    
    @staticmethod
    def get_study_models(study_code):
        """
        Get all models for a specific study
        
        Args:
            study_code: The study code (e.g., '43EN')
            
        Returns:
            Dict of model_name: model_class
        """
        app_label = f'study_{study_code.lower()}'
        
        try:
            # Get the app config
            app_config = apps.get_app_config(app_label)
            
            # Get all models for this app
            models = {}
            for model in app_config.get_models():
                models[model.__name__] = model
            
            return models
            
        except LookupError:
            logger.error(f"App {app_label} not found")
            return {}
    
    @staticmethod
    def get_model(study_code, model_name):
        """
        Get a specific model for a study
        
        Args:
            study_code: The study code (e.g., '43EN')
            model_name: Name of the model (e.g., 'Patient')
            
        Returns:
            Model class or None
        """
        app_label = f'study_{study_code.lower()}'
        
        try:
            return apps.get_model(app_label, model_name)
        except LookupError:
            logger.error(f"Model {model_name} not found in {app_label}")
            return None


@contextmanager
def study_database_context(study):
    """
    Context manager to temporarily switch to a study database
    
    Usage:
        with study_database_context(study):
            # All queries here will use the study database
            patients = Patient.objects.all()
    """
    # Save current database
    original_db = get_current_db()
    
    try:
        # Add and switch to study database
        add_study_db(study.db_name)
        set_current_db(study.db_name)
        
        yield study.db_name
        
    finally:
        # Restore original database
        set_current_db(original_db)


def execute_study_query(study, model_name, query_method='all', **filters):
    """
    Execute a query on a study model
    
    Args:
        study: Study object
        model_name: Name of the model
        query_method: QuerySet method ('all', 'filter', 'get', etc.)
        **filters: Query filters
        
    Returns:
        QuerySet or Model instance
        
    Example:
        patients = execute_study_query(study, 'Patient', 'filter', site__site_code='SITE01')
    """
    model = StudyModelLoader.get_model(study.code, model_name)
    if not model:
        return None
    
    with study_database_context(study):
        queryset = model.objects.using(study.db_name)
        
        # Apply query method
        if query_method == 'all':
            return list(queryset.all())
        elif query_method == 'filter':
            return list(queryset.filter(**filters))
        elif query_method == 'get':
            return queryset.get(**filters)
        elif query_method == 'count':
            return queryset.filter(**filters).count()
        elif query_method == 'exists':
            return queryset.filter(**filters).exists()
        else:
            raise ValueError(f"Unsupported query method: {query_method}")


def bulk_create_study_data(study, model_name, data_list):
    """
    Bulk create records in a study model
    
    Args:
        study: Study object
        model_name: Name of the model
        data_list: List of dictionaries with model data
        
    Returns:
        List of created objects
        
    Example:
        patients = bulk_create_study_data(study, 'Patient', [
            {'patient_id': 'P000001', 'site_id': 1, ...},
            {'patient_id': 'P000002', 'site_id': 1, ...},
        ])
    """
    model = StudyModelLoader.get_model(study.code, model_name)
    if not model:
        return []
    
    with study_database_context(study):
        with transaction.atomic(using=study.db_name):
            objects = [model(**data) for data in data_list]
            return model.objects.using(study.db_name).bulk_create(objects)


def copy_study_structure(source_study_code, target_study_code):
    """
    Copy table structure from one study to another (schema only, no data)
    
    Args:
        source_study_code: Source study code
        target_study_code: Target study code
    """
    from django.core.management import call_command
    
    # Get models from source study
    source_models = StudyModelLoader.get_study_models(source_study_code)
    
    if not source_models:
        raise ValueError(f"No models found for study {source_study_code}")
    
    # Create migrations for target study
    target_app = f'study_{target_study_code.lower()}'
    
    # Make migrations
    call_command('makemigrations', target_app)
    
    # Apply migrations to target database
    target_db = f'db_study_{target_study_code.lower()}'
    call_command('migrate', target_app, database=target_db)
    
    logger.info(f"Structure copied from {source_study_code} to {target_study_code}")


def get_study_statistics(study):
    """
    Get statistics for a study
    
    Args:
        study: Study object
        
    Returns:
        Dictionary with statistics
    """
    stats = {}
    
    with study_database_context(study):
        # Get all models for this study
        models = StudyModelLoader.get_study_models(study.code)
        
        for model_name, model_class in models.items():
            if hasattr(model_class._meta, 'abstract') and model_class._meta.abstract:
                continue  # Skip abstract models
                
            try:
                count = model_class.objects.using(study.db_name).count()
                stats[model_name] = count
            except Exception as e:
                logger.error(f"Error counting {model_name}: {e}")
                stats[model_name] = 0
    
    return stats