"""
Run Development Server with Auto Backup

Starts Django development server AND backup scheduler in parallel
Perfect for localhost development
"""
import subprocess
import sys
import time
import signal
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run development server with auto backup scheduler'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=int,
            default=8000,
            help='Port for development server (default: 8000)'
        )
        parser.add_argument(
            '--backup-interval',
            type=int,
            default=5,
            help='Backup interval in minutes (default: 5)'
        )
        parser.add_argument(
            '--backup-user',
            type=str,
            default='system_backup',
            help='Backup user (default: system_backup)'
        )
    
    def handle(self, *args, **options):
        port = options['port']
        interval = options['backup_interval']
        backup_user = options['backup_user']
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('🚀 STARTING DEVELOPMENT ENVIRONMENT'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'\n📡 Django server: http://127.0.0.1:{port}/')
        self.stdout.write(f'🔄 Auto backup: Every {interval} minute(s)')
        self.stdout.write(f'👤 Backup user: {backup_user}')
        self.stdout.write(f'\n⚠️  Press CTRL+C to stop both services\n')
        
        # Start Django server
        server_process = subprocess.Popen(
            [sys.executable, 'manage.py', 'runserver', str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Wait a bit for server to start
        time.sleep(2)
        
        # Start backup scheduler
        scheduler_process = subprocess.Popen(
            [
                sys.executable, 'manage.py', 'start_backup_scheduler',
                '--user', backup_user,
                '--interval', str(interval)
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        self.stdout.write(self.style.SUCCESS('✅ Both services started!\n'))
        
        try:
            # Stream output from both processes
            import select
            
            while True:
                # Check if processes are still running
                if server_process.poll() is not None:
                    self.stdout.write(self.style.ERROR('\n❌ Server stopped unexpectedly'))
                    break
                
                if scheduler_process.poll() is not None:
                    self.stdout.write(self.style.ERROR('\n❌ Scheduler stopped unexpectedly'))
                    break
                
                # Read output
                if server_process.stdout.readable():
                    line = server_process.stdout.readline()
                    if line:
                        self.stdout.write(f'[SERVER] {line.strip()}')
                
                if scheduler_process.stdout.readable():
                    line = scheduler_process.stdout.readline()
                    if line:
                        self.stdout.write(f'[BACKUP] {line.strip()}')
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n\n⏸️  Shutting down...'))
            
            # Gracefully shutdown both processes
            server_process.send_signal(signal.SIGTERM)
            scheduler_process.send_signal(signal.SIGTERM)
            
            # Wait for shutdown
            server_process.wait(timeout=5)
            scheduler_process.wait(timeout=5)
            
            self.stdout.write(self.style.SUCCESS('✓ Shutdown complete'))
