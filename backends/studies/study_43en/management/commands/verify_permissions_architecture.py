# backends/studies/study_43en/management/commands/verify_permissions_architecture.py
"""
Verify permissions architecture
Shows where ContentType, Permission, Group are stored

Usage: python manage.py verify_permissions_architecture --study 43EN
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connections
from tabulate import tabulate


class Command(BaseCommand):
    help = 'Verify permissions architecture and database locations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--study',
            type=str,
            default='43EN',
            help='Study code (default: 43EN)'
        )

    def handle(self, *args, **options):
        study_code = options['study']
        app_label = f'study_{study_code.lower()}'
        db_name = f'db_study_{study_code.lower()}'
        
        self.stdout.write("=" * 80)
        self.stdout.write("PERMISSIONS ARCHITECTURE VERIFICATION")
        self.stdout.write("=" * 80)
        
        # Check databases
        self.stdout.write("\n Database Configuration:")
        self.stdout.write("-" * 80)
        
        db_info = []
        for alias in ['default', db_name]:
            if alias in connections.databases:
                db_config = connections.databases[alias]
                db_info.append([
                    alias,
                    db_config.get('NAME', 'N/A'),
                    db_config.get('ENGINE', 'N/A').split('.')[-1],
                    '' if self._test_connection(alias) else ''
                ])
        
        self.stdout.write(
            tabulate(
                db_info,
                headers=['Alias', 'Database Name', 'Engine', 'Connected'],
                tablefmt='grid'
            )
        )
        
        # Check ContentTypes
        self.stdout.write("\n ContentTypes:")
        self.stdout.write("-" * 80)
        
        # Check in default
        ct_default = ContentType.objects.filter(app_label=app_label).count()
        self.stdout.write(f"   Default DB: {ct_default} ContentTypes for {app_label}")
        
        # Check in study db (if exists)
        try:
            ct_study = ContentType.objects.using(db_name).filter(
                app_label=app_label
            ).count()
            self.stdout.write(f"   Study DB:   {ct_study} ContentTypes for {app_label}")
        except Exception as e:
            self.stdout.write(f"   Study DB:    Cannot check ({e})")
        
        # Recommendation
        if ct_default > 0:
            self.stdout.write(self.style.SUCCESS(
                "\n    CORRECT: ContentTypes are in DEFAULT database"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "\n     WARNING: No ContentTypes found in DEFAULT database"
            ))
        
        # Check Permissions
        self.stdout.write("\n Permissions:")
        self.stdout.write("-" * 80)
        
        perms = Permission.objects.filter(
            content_type__app_label=app_label
        ).count()
        
        self.stdout.write(f"   Default DB: {perms} Permissions for {app_label}")
        
        if perms > 0:
            # Show breakdown by action
            actions = ['view', 'add', 'change', 'delete']
            action_counts = []
            
            for action in actions:
                count = Permission.objects.filter(
                    content_type__app_label=app_label,
                    codename__startswith=action
                ).count()
                action_counts.append([action.upper(), count])
            
            self.stdout.write("\n   Breakdown by action:")
            self.stdout.write(
                tabulate(
                    action_counts,
                    headers=['Action', 'Count'],
                    tablefmt='simple'
                )
            )
        
        # Check Groups
        self.stdout.write("\n👥 Groups:")
        self.stdout.write("-" * 80)
        
        groups = Group.objects.filter(name__istartswith=f"Study {study_code}")
        
        if groups.exists():
            group_info = []
            for group in groups:
                perm_count = group.permissions.filter(
                    content_type__app_label=app_label
                ).count()
                
                group_info.append([
                    group.name,
                    group.user_set.count(),
                    perm_count
                ])
            
            self.stdout.write(
                tabulate(
                    group_info,
                    headers=['Group Name', 'Users', 'Permissions'],
                    tablefmt='grid'
                )
            )
        else:
            self.stdout.write("     No groups found for this study")
        
        # Architecture Summary
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("ARCHITECTURE SUMMARY")
        self.stdout.write("=" * 80)
        
        summary = []
        summary.append(['ContentType', 'default database', '' if ct_default > 0 else ''])
        summary.append(['Permission', 'default database', '' if perms > 0 else ''])
        summary.append(['Group', 'default database', '' if groups.exists() else ''])
        summary.append(['CRF Data', f'{db_name} (data schema)', ''])
        
        self.stdout.write(
            tabulate(
                summary,
                headers=['Component', 'Location', 'Status'],
                tablefmt='grid'
            )
        )
        
        # Recommendations
        self.stdout.write("\n💡 RECOMMENDATIONS:")
        self.stdout.write("-" * 80)
        
        if ct_default == 0:
            self.stdout.write(self.style.WARNING(
                "     Run: python manage.py setup_crf_permissions_v3 --study " + study_code
            ))
        
        if perms == 0:
            self.stdout.write(self.style.WARNING(
                "     Run: python manage.py setup_crf_permissions_v3 --study " + study_code
            ))
        
        if not groups.exists():
            self.stdout.write(self.style.WARNING(
                "     Run: python manage.py sync_user_groups (or create groups manually)"
            ))
        
        if ct_default > 0 and perms > 0 and groups.exists():
            self.stdout.write(self.style.SUCCESS(
                "    Architecture looks good! You can now assign users to groups."
            ))
        
        self.stdout.write("\n" + "=" * 80 + "\n")
    
    def _test_connection(self, db_alias: str) -> bool:
        """Test if database connection works"""
        try:
            connection = connections[db_alias]
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception:
            return False