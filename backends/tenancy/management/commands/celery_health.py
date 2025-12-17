"""
Quick Celery Health Check
Tests if Celery is configured and can execute tasks
"""

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Check Celery configuration and connectivity'

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.SUCCESS("CELERY HEALTH CHECK"))
        self.stdout.write("="*70 + "\n")

        # 1. Check Celery configuration
        self.stdout.write("1️⃣ Checking Celery Configuration...")
        self.stdout.write("-"*70)
        
        try:
            from config.celery import app
            
            self.stdout.write(self.style.SUCCESS("  ✓ Celery app initialized"))
            
            # Check broker URL
            broker_url = getattr(settings, 'CELERY_BROKER_URL', None)
            if broker_url:
                self.stdout.write(f"  ✓ Broker URL: {broker_url}")
            else:
                if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
                    self.stdout.write(self.style.WARNING("  ⚠️ Running in EAGER mode (dev mode - no broker needed)"))
                else:
                    self.stdout.write(self.style.ERROR("  ❌ No broker URL configured!"))
                    
            # Check result backend
            result_backend = getattr(settings, 'CELERY_RESULT_BACKEND', None)
            if result_backend:
                self.stdout.write(f"  ✓ Result backend: {result_backend}")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Failed to load Celery: {e}"))
            return

        self.stdout.write()

        # 2. Check if tasks are discoverable
        self.stdout.write("2️⃣ Checking Task Discovery...")
        self.stdout.write("-"*70)
        
        try:
            from backends.tenancy import tasks
            
            task_list = [
                'send_admin_alert_email',
                'send_user_email', 
                'send_security_alert',
                'backup_database',
                'scheduled_backup_all_databases',
                'cleanup_old_backups',
                'cleanup_expired_sessions',
            ]
            
            for task_name in task_list:
                if hasattr(tasks, task_name):
                    self.stdout.write(self.style.SUCCESS(f"  ✓ {task_name}"))
                else:
                    self.stdout.write(self.style.ERROR(f"  ❌ {task_name} not found"))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Failed to import tasks: {e}"))

        self.stdout.write()

        # 3. Test task execution
        self.stdout.write("3️⃣ Testing Task Execution...")
        self.stdout.write("-"*70)
        
        try:
            from config.celery import debug_task
            
            if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
                # In eager mode, task runs synchronously
                result = debug_task.delay()
                self.stdout.write(self.style.SUCCESS("  ✓ Debug task executed (eager mode)"))
            else:
                # In production mode, task is queued
                result = debug_task.delay()
                self.stdout.write(self.style.SUCCESS(f"  ✓ Debug task queued (ID: {result.id})"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Failed to execute task: {e}"))

        self.stdout.write()

        # 4. Check Redis connectivity (if not eager mode)
        if not getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
            self.stdout.write("4️⃣ Checking Redis Connectivity...")
            self.stdout.write("-"*70)
            
            try:
                import redis
                broker_url = getattr(settings, 'CELERY_BROKER_URL', '')
                
                if broker_url.startswith('redis://'):
                    # Parse Redis URL
                    parts = broker_url.replace('redis://', '').split('/')
                    host_port = parts[0].split(':')
                    host = host_port[0] if host_port else 'localhost'
                    port = int(host_port[1]) if len(host_port) > 1 else 6379
                    
                    r = redis.Redis(host=host, port=port, socket_connect_timeout=5)
                    r.ping()
                    
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Redis connected ({host}:{port})"))
                else:
                    self.stdout.write(self.style.WARNING("  ⚠️ Not using Redis broker"))
                    
            except ImportError:
                self.stdout.write(self.style.ERROR("  ❌ Redis library not installed"))
                self.stdout.write("     Install: pip install redis")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Redis connection failed: {e}"))
                self.stdout.write("     Make sure Redis is running:")
                self.stdout.write("       Windows: Start redis-server.exe")
                self.stdout.write("       Linux: sudo systemctl start redis")
                self.stdout.write("       Docker: docker run -d -p 6379:6379 redis:latest")

            self.stdout.write()

        # 5. Check if worker is running
        if not getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
            self.stdout.write("5️⃣ Checking Worker Status...")
            self.stdout.write("-"*70)
            
            try:
                from config.celery import app
                
                inspect = app.control.inspect()
                stats = inspect.stats()
                
                if stats:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ {len(stats)} worker(s) online"))
                    for worker_name in stats.keys():
                        self.stdout.write(f"    - {worker_name}")
                else:
                    self.stdout.write(self.style.WARNING("  ⚠️ No workers found"))
                    self.stdout.write("     Start worker: celery -A config worker --loglevel=info --pool=solo")
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Failed to check workers: {e}"))

            self.stdout.write()

        # Summary
        self.stdout.write("="*70)
        self.stdout.write(self.style.SUCCESS("HEALTH CHECK COMPLETED"))
        self.stdout.write("="*70)
        
        if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
            self.stdout.write()
            self.stdout.write(self.style.WARNING("⚠️  DEVELOPMENT MODE (EAGER)"))
            self.stdout.write("   Tasks run synchronously without broker")
            self.stdout.write("   To enable production mode:")
            self.stdout.write("     1. Set CELERY_TASK_ALWAYS_EAGER=False in .env")
            self.stdout.write("     2. Start Redis")
            self.stdout.write("     3. Start Celery worker")
        else:
            self.stdout.write()
            self.stdout.write(self.style.SUCCESS("✓ PRODUCTION MODE"))
            self.stdout.write("  To start Celery:")
            self.stdout.write("    Windows: start_celery.bat")
            self.stdout.write("    Linux:   ./start_celery.sh")
            
        self.stdout.write()
