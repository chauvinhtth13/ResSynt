# apps/studies/management/commands/create_study_templates.py
from django.core.management.base import BaseCommand
from pathlib import Path

class Command(BaseCommand):
    help = 'Creates template directories for a study'
    
    def add_arguments(self, parser):
        parser.add_argument('study_code', type=str)
    
    def handle(self, *args, **options):
        study_code = options['study_code']
        base_path = Path('apps/web/templates/studies') / study_code
        
        # Create directories
        base_path.mkdir(parents=True, exist_ok=True)
        (base_path / 'crd').mkdir(exist_ok=True)
        
        # Create default templates
        (base_path / 'sidebar.html').write_text('<!-- Sidebar content -->')
        (base_path / 'content.html').write_text('<!-- Main content -->')
        
        self.stdout.write(f'Created templates for {study_code}')