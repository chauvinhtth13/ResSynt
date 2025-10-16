# backends/tenancy/management/commands/create_study_structure.py
"""
Create study app folder structure (folder + apps.py only)
FIXED: Handle both QuerySet and list
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from pathlib import Path
from backends.tenancy.models import Study
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create study folder structure and apps.py from Study in database'

    def add_arguments(self, parser):
        parser.add_argument(
            'study_code',
            type=str,
            nargs='?',
            help='Study code (e.g., 43EN). Leave empty to create for all active studies.'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite apps.py if folder already exists'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Create for ALL studies (including archived)'
        )

    def handle(self, *args, **options):
        study_code = options.get('study_code')
        force = options.get('force', False)
        create_all = options.get('all', False)

        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('CREATE STUDY STRUCTURE'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))

        # Get studies to process
        if study_code:
            studies = self._get_specific_study(study_code)
            study_count = len(studies)  # Use len() for list
        elif create_all:
            studies = Study.objects.all()
            study_count = studies.count()  # Use count() for QuerySet
        else:
            studies = Study.objects.exclude(status=Study.Status.ARCHIVED)
            study_count = studies.count()  # Use count() for QuerySet

        if not studies:
            raise CommandError("No studies found")

        self.stdout.write(f"Processing {study_count} study/studies...\n")

        # Process each study
        created = 0
        skipped = 0
        errors = 0

        for study in studies:
            try:
                result = self._create_study_structure(study, force)
                
                if result == 'created':
                    created += 1
                elif result == 'skipped':
                    skipped += 1

            except Exception as e:
                errors += 1
                logger.error(f"Error for {study.code}: {e}", exc_info=True)
                self.stdout.write(
                    self.style.ERROR(f"ERROR {study.code}: {e}")
                )

        # Summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write('SUMMARY')
        self.stdout.write('='*70)
        
        if created > 0:
            self.stdout.write(self.style.SUCCESS(f"Created: {created}"))
        
        if skipped > 0:
            self.stdout.write(self.style.WARNING(f"Skipped: {skipped}"))
        
        if errors > 0:
            self.stdout.write(self.style.ERROR(f"Errors: {errors}"))

        if created > 0:
            self.stdout.write('\n' + self.style.WARNING(
                'RESTART DJANGO SERVER to load new apps!'
            ))
        
        self.stdout.write('')

    def _get_specific_study(self, study_code: str) -> list:
        """
        Get specific study by code
        FIXED: Returns list instead of queryset for consistent handling
        """
        try:
            study = Study.objects.get(code__iexact=study_code)
            return [study]  # Return as list
        except Study.DoesNotExist:
            raise CommandError(f"Study '{study_code}' not found in database")

    def _create_study_structure(self, study: Study, force: bool = False) -> str:
        """
        Create folders and apps.py for study
        
        Returns:
            'created' or 'skipped'
        """
        study_code = study.code
        study_code_lower = study_code.lower()
        study_name = study.safe_translation_getter('name', any_language=True) or study_code

        # Base directory
        base_dir = Path(settings.BASE_DIR)

        # Define all folders to create
        folders = [
            base_dir / 'backends' / 'studies' / f'study_{study_code_lower}',
            base_dir / 'backends' / 'api' / 'studies' / f'study_{study_code_lower}',
            base_dir / 'frontends' / 'static' / 'css' / 'studies' / f'study_{study_code_lower}',
            base_dir / 'frontends' / 'static' / 'images' / 'studies' / f'study_{study_code_lower}',
            base_dir / 'frontends' / 'static' / 'js' / 'studies' / f'study_{study_code_lower}',
            base_dir / 'frontends' / 'templates' / 'studies' / f'study_{study_code_lower}',
        ]

        # Main folder for apps.py
        main_folder = folders[0]
        apps_file = main_folder / 'apps.py'

        self.stdout.write(f"\n{study_code}: {study_name}")
        self.stdout.write('-'*70)

        # Check if main folder exists
        if main_folder.exists():
            if not force:
                self.stdout.write(
                    self.style.WARNING(
                        "Folder already exists, skipping (use --force to overwrite apps.py)"
                    )
                )
                return 'skipped'
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "Folder exists, will overwrite apps.py"
                    )
                )

        # Create all folders
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)
            self.stdout.write(f"  Created: {folder.relative_to(base_dir)}")

        # Create apps.py
        apps_content = self._generate_apps_py(study_code, study_code_lower, study_name)
        apps_file.write_text(apps_content, encoding='utf-8')
        self.stdout.write(f"  Created: {apps_file.relative_to(base_dir)}")

        return 'created'

    def _generate_apps_py(self, study_code: str, study_code_lower: str, study_name: str) -> str:
        """Generate apps.py content"""
        # Sanitize study code for class name
        class_name_base = study_code.upper().replace('-', '').replace('_', '')
        class_name = f"Study{class_name_base}Config"
        
        return f'''# backends/studies/study_{study_code_lower}/apps.py
"""
Django App Configuration for Study {study_code}
"""
from django.apps import AppConfig


class {class_name}(AppConfig):
    """App configuration for Study {study_code}"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backends.studies.study_{study_code_lower}'
    label = 'study_{study_code_lower}'
    verbose_name = "Study {study_code}: {study_name}"
    
    def ready(self):
        """App initialization"""
        pass
'''