"""
Celery Tasks for Tenancy Module
Handles async email sending and database backups
"""
from celery import shared_task
from django.core.mail import mail_admins, send_mail
from django.conf import settings
from django.contrib.sessions.models import Session
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


# ==========================================
# EMAIL TASKS
# ==========================================

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # Retry after 1 minute
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 minutes
)
def send_admin_alert_email(self, subject, message):
    """
    Send alert email to admins asynchronously
    
    Args:
        subject: Email subject
        message: Email message body
    
    Returns:
        dict: Status and info
    """
    try:
        logger.info(f"📧 Sending admin alert: {subject}")
        
        mail_admins(
            subject=subject,
            message=message,
            fail_silently=False
        )
        
        logger.info(f"✓ Admin alert sent successfully: {subject}")
        return {
            'status': 'success',
            'subject': subject,
            'retry_count': self.request.retries
        }
        
    except Exception as exc:
        logger.error(f"❌ Failed to send admin alert: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_user_email(self, subject, message, recipient_list, from_email=None):
    """
    Send email to users asynchronously
    
    Args:
        subject: Email subject
        message: Email message body
        recipient_list: List of recipient email addresses
        from_email: From email address (optional)
    
    Returns:
        dict: Status and info
    """
    try:
        logger.info(f"📧 Sending email to {len(recipient_list)} recipient(s): {subject}")
        
        if from_email is None:
            from_email = settings.DEFAULT_FROM_EMAIL
        
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False
        )
        
        logger.info(f"✓ Email sent successfully: {subject}")
        return {
            'status': 'success',
            'subject': subject,
            'recipients': len(recipient_list),
            'retry_count': self.request.retries
        }
        
    except Exception as exc:
        logger.error(f"❌ Failed to send email: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2)
def send_security_alert(self, alert_type, details):
    """
    Send security alert with standardized format
    
    Args:
        alert_type: Type of alert (lockout, brute_force, etc.)
        details: Dictionary with alert details
    
    Returns:
        dict: Status
    """
    try:
        alert_templates = {
            'user_lockout': {
                'subject': '🚨 SECURITY ALERT: User Locked Out',
                'template': (
                    "A user has been locked out after multiple failed login attempts.\n"
                    "\n"
                    "Details:\n"
                    "  User:       {username}\n"
                    "  IP Address: {ip_address}\n"
                    "  Time:       {timestamp}\n"
                    "  Server:     {server_name}\n"
                    "\n"
                    "Action Required:\n"
                    "  1. Review the lockout reason\n"
                    "  2. Check if this is a legitimate user\n"
                    "  3. Unlock user if needed: python manage.py axes_reset {username}\n"
                )
            },
            'invalid_user_attempt': {
                'subject': '🚨 SECURITY ALERT: Invalid User Login Attempts',
                'template': (
                    "Multiple login attempts for NON-EXISTENT user.\n"
                    "This may indicate a brute-force attack or user enumeration attempt.\n"
                    "\n"
                    "Details:\n"
                    "  Username:   {username} (DOES NOT EXIST)\n"
                    "  IP Address: {ip_address}\n"
                    "  Time:       {timestamp}\n"
                    "  Server:     {server_name}\n"
                    "\n"
                    "Recommended Actions:\n"
                    "  1. Consider blocking IP: {ip_address}\n"
                    "  2. Review firewall rules\n"
                    "  3. Check for similar attempts from this IP\n"
                )
            },
            'rate_limit_exceeded': {
                'subject': '🚨 SECURITY ALERT: Rate Limit Exceeded',
                'template': (
                    "Rate limit has been exceeded for a user/IP.\n"
                    "\n"
                    "Details:\n"
                    "  User:       {username}\n"
                    "  IP Address: {ip_address}\n"
                    "  Endpoint:   {endpoint}\n"
                    "  Count:      {count}\n"
                    "  Time:       {timestamp}\n"
                    "  Server:     {server_name}\n"
                    "\n"
                    "Action Required:\n"
                    "  1. Review the activity pattern\n"
                    "  2. Verify this is not a DoS attempt\n"
                )
            }
        }
        
        template_data = alert_templates.get(alert_type)
        if not template_data:
            raise ValueError(f"Unknown alert type: {alert_type}")
        
        # Add server name if not provided
        if 'server_name' not in details:
            details['server_name'] = getattr(settings, 'SERVER_NAME', 'ReSYNC')
        
        subject = template_data['subject']
        message = template_data['template'].format(**details)
        
        mail_admins(subject=subject, message=message, fail_silently=False)
        
        logger.info(f"✓ Security alert sent: {alert_type}")
        return {'status': 'success', 'alert_type': alert_type}
        
    except Exception as exc:
        logger.error(f"❌ Failed to send security alert: {exc}")
        raise self.retry(exc=exc)


# ==========================================
# BACKUP TASKS
# ==========================================

@shared_task(
    bind=True,
    time_limit=3600,  # 1 hour limit
    soft_time_limit=3300,  # 55 minutes soft limit
)
def backup_database(self, database='default', compress=True):
    """
    Create database backup asynchronously
    
    Args:
        database: Database alias to backup
        compress: Use compression
    
    Returns:
        dict: Backup result
    """
    try:
        logger.info(f"📦 Starting backup for database: {database}")
        
        from backends.tenancy.utils.backup_manager import get_backup_manager
        backup_manager = get_backup_manager()
        
        result = backup_manager.create_backup(database=database, compress=compress)
        
        if result['status'] == 'success':
            logger.info(
                f"✓ Backup completed: {database}\n"
                f"  Path: {result['path']}\n"
                f"  Size: {backup_manager._format_size(result['size'])}"
            )
            
            # Send success notification to admins
            send_admin_alert_email.delay(
                subject=f"✓ Database Backup Successful: {database}",
                message=(
                    f"Database backup completed successfully.\n"
                    f"\n"
                    f"Details:\n"
                    f"  Database: {database}\n"
                    f"  Path: {result['path']}\n"
                    f"  Size: {backup_manager._format_size(result['size'])}\n"
                    f"  Checksum: {result['checksum'][:32]}...\n"
                    f"  Timestamp: {result['timestamp']}\n"
                )
            )
        else:
            # Send failure notification
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"❌ Backup failed: {error_msg}")
            
            send_admin_alert_email.delay(
                subject=f"❌ Database Backup FAILED: {database}",
                message=(
                    f"Database backup failed!\n"
                    f"\n"
                    f"Database: {database}\n"
                    f"Error: {error_msg}\n"
                    f"\n"
                    f"Action Required: Check backup configuration and logs."
                )
            )
        
        return result
        
    except Exception as exc:
        logger.error(f"❌ Backup task failed: {exc}", exc_info=True)
        
        # Send failure notification
        send_admin_alert_email.delay(
            subject=f"❌ Database Backup EXCEPTION: {database}",
            message=(
                f"Database backup encountered an exception!\n"
                f"\n"
                f"Database: {database}\n"
                f"Exception: {str(exc)}\n"
                f"\n"
                f"Action Required: Check logs and backup configuration."
            )
        )
        
        raise


@shared_task(
    bind=True,
    time_limit=7200,  # 2 hours for multiple databases
)
def scheduled_backup_all_databases(self):
    """
    Scheduled task to backup all databases from PostgreSQL server
    Runs daily at 2:00 AM (configured in celery.py)
    
    Backs up ALL databases in PostgreSQL (not just settings.DATABASES)
    Excludes: postgres, template0, template1, test
    
    Returns:
        dict: Summary of all backups
    """
    try:
        logger.info("📦 Starting scheduled backup for all databases")
        
        from backends.tenancy.utils.backup_manager import get_backup_manager
        from django.db import connection
        import psycopg
        
        backup_manager = get_backup_manager()
        
        # Get ALL databases from PostgreSQL server
        db_settings = connection.settings_dict
        conninfo = (
            f"host={db_settings['HOST']} "
            f"port={db_settings['PORT']} "
            f"user={db_settings['USER']} "
            f"password={db_settings['PASSWORD']} "
            f"dbname=postgres"
        )
        
        # Databases to exclude (system dbs + databases without permissions)
        excluded = ['postgres', 'template0', 'template1', 'test', 'admin_system']
        
        with psycopg.connect(conninfo) as conn:
            with conn.cursor() as cursor:
                placeholders = ','.join(['%s'] * len(excluded))
                cursor.execute(f"""
                    SELECT datname 
                    FROM pg_database 
                    WHERE datistemplate = false
                      AND datname NOT IN ({placeholders})
                    ORDER BY datname
                """, excluded)
                databases = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"Found {len(databases)} databases to backup: {', '.join(databases)}")
        
        results = []
        success_count = 0
        failed_count = 0
        
        for database in databases:
            try:
                logger.info(f"Backing up database: {database}")
                
                # Create backup with compression
                result = backup_manager.create_backup(database=database, compress=True)
                
                if result['status'] != 'success':
                    failed_count += 1
                    results.append({
                        'database': database,
                        'status': 'failed',
                        'error': result.get('error', 'Unknown error')
                    })
                    logger.warning(f"⚠️  Backup failed: {database} - {result.get('error', '')}")
                    continue
                
                # Encrypt backup if password is configured
                encryption_password = getattr(settings, 'BACKUP_ENCRYPTION_PASSWORD', None)
                if encryption_password:
                    logger.info(f"Encrypting backup: {database}")
                    encrypt_result = backup_manager.encrypt_backup(
                        backup_path=result['path'],
                        password=encryption_password,
                        remove_original=True  # Keep only encrypted version
                    )
                    
                    if encrypt_result['status'] == 'success':
                        logger.info(f"✓ Backup encrypted: {database}")
                        results.append({
                            'database': database,
                            'status': 'success',
                            'path': encrypt_result['encrypted_path'],
                            'size': encrypt_result['size'],
                            'encrypted': True,
                            'error': ''
                        })
                        success_count += 1
                    else:
                        # Encryption failed, but unencrypted backup exists
                        logger.warning(f"⚠️  Encryption failed for {database}: {encrypt_result.get('error', '')}")
                        results.append({
                            'database': database,
                            'status': 'success',
                            'path': result['path'],
                            'size': result['size'],
                            'encrypted': False,
                            'error': f"Not encrypted: {encrypt_result.get('error', '')}"
                        })
                        success_count += 1
                else:
                    # No encryption password configured
                    logger.warning(f"⚠️  BACKUP_ENCRYPTION_PASSWORD not set - backup NOT encrypted!")
                    results.append({
                        'database': database,
                        'status': 'success',
                        'path': result['path'],
                        'size': result['size'],
                        'encrypted': False,
                        'error': ''
                    })
                    success_count += 1
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Failed to backup {database}: {error_msg}")
                
                # Check if permission denied
                if 'permission denied' in error_msg.lower():
                    logger.warning(f"Skipping {database}: insufficient permissions")
                
                results.append({
                    'database': database,
                    'status': 'failed',
                    'error': error_msg,
                    'encrypted': False
                })
                failed_count += 1
        
        # Send summary email
        summary_message = (
            f"Scheduled database backup completed.\n"
            f"\n"
            f"Summary:\n"
            f"  Total databases: {len(databases)}\n"
            f"  Successful: {success_count}\n"
            f"  Failed: {failed_count}\n"
            f"\n"
            f"Details:\n"
        )
        
        for result in results:
            if result['status'] == 'success':
                encrypted_badge = "🔒" if result.get('encrypted', False) else "⚠️ "
                summary_message += (
                    f"  {encrypted_badge} {result['database']}: "
                    f"{backup_manager._format_size(result['size'])}\n"
                )
            else:
                error = result.get('error', 'Unknown error')
                # Truncate long error messages
                if len(error) > 100:
                    error = error[:100] + '...'
                summary_message += f"  ❌ {result['database']}: {error}\n"
        
        subject = (
            f"📦 Daily Backup Report: {success_count} successful, {failed_count} failed"
        )
        
        send_admin_alert_email.delay(subject=subject, message=summary_message)
        
        logger.info(f"✓ Scheduled backup completed: {success_count}/{len(databases)} successful")
        
        return {
            'status': 'completed',
            'total': len(databases),
            'success': success_count,
            'failed': failed_count,
            'results': results
        }
        
    except Exception as exc:
        logger.error(f"❌ Scheduled backup task failed: {exc}", exc_info=True)
        raise


@shared_task(bind=True)
def cleanup_old_backups(self):
    """
    Clean up old backup files based on retention policy
    Runs weekly on Sunday at 3:00 AM
    
    Returns:
        dict: Cleanup summary
    """
    try:
        logger.info("🧹 Starting backup cleanup")
        
        from backends.tenancy.utils.backup_manager import get_backup_manager
        backup_manager = get_backup_manager()
        
        databases = list(settings.DATABASES.keys())
        total_removed = 0
        
        for database in databases:
            removed = backup_manager._cleanup_old_backups(database)
            if removed > 0:
                total_removed += removed
                logger.info(f"  Removed {removed} old backup(s) for {database}")
        
        logger.info(f"✓ Backup cleanup completed: {total_removed} file(s) removed")
        
        # Send notification if files were removed
        if total_removed > 0:
            send_admin_alert_email.delay(
                subject=f"🧹 Backup Cleanup: {total_removed} old file(s) removed",
                message=(
                    f"Old backup files have been cleaned up.\n"
                    f"\n"
                    f"Files removed: {total_removed}\n"
                    f"Retention policy: {backup_manager.retention_days} days\n"
                )
            )
        
        return {
            'status': 'success',
            'removed': total_removed,
            'retention_days': backup_manager.retention_days
        }
        
    except Exception as exc:
        logger.error(f"❌ Backup cleanup failed: {exc}", exc_info=True)
        raise


@shared_task(bind=True)
def cleanup_expired_sessions(self):
    """
    Clean up expired Django sessions
    Runs daily at 4:00 AM
    
    Returns:
        dict: Cleanup summary
    """
    try:
        logger.info("🧹 Starting session cleanup")
        
        expired_count = Session.objects.filter(
            expire_date__lt=timezone.now()
        ).count()
        
        if expired_count > 0:
            Session.objects.filter(expire_date__lt=timezone.now()).delete()
            logger.info(f"✓ Removed {expired_count} expired session(s)")
        else:
            logger.info("✓ No expired sessions to remove")
        
        return {
            'status': 'success',
            'removed': expired_count
        }
        
    except Exception as exc:
        logger.error(f"❌ Session cleanup failed: {exc}", exc_info=True)
        raise
