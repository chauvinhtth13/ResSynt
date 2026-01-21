# backends/tenancy/tasks.py
"""
Celery tasks for tenancy app.

Handles async operations like:
- Database creation for new studies
- Security alert emails
- Permission syncing
"""
import logging
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def create_study_database_task(self, study_pk: int):
    """
    Async task to create study database and initialize roles.
    
    This prevents blocking the request when creating a new study.
    """
    try:
        from backends.tenancy.models import Study
        from backends.tenancy.utils.db_study_creator import DatabaseStudyCreator
        from backends.tenancy.utils.role_manager import StudyRoleManager
        
        study = Study.objects.get(pk=study_pk)
        
        # Create database if not exists
        if not DatabaseStudyCreator.database_exists(study.db_name):
            success, message = DatabaseStudyCreator.create_study_database(study.db_name)
            if not success:
                logger.error(f"Failed to create database for study {study.code}: {message}")
                raise Exception(f"Database creation failed: {message}")
            logger.info(f"Created database: {study.db_name}")
        
        # Initialize roles and permissions
        result = StudyRoleManager.initialize_study(study.code)
        
        if 'error' in result:
            logger.warning(f"Role initialization warning for {study.code}: {result['error']}")
        else:
            logger.info(
                f"Initialized study {study.code}: "
                f"{result.get('groups_created', 0)} groups, "
                f"{result.get('permissions_assigned', 0)} permissions"
            )
        
        return {
            'status': 'success',
            'study_code': study.code,
            'db_name': study.db_name,
            'groups_created': result.get('groups_created', 0),
            'permissions_assigned': result.get('permissions_assigned', 0),
        }
        
    except Study.DoesNotExist:
        logger.error(f"Study with pk={study_pk} not found")
        return {'status': 'error', 'message': 'Study not found'}
    except Exception as e:
        logger.error(f"Error in create_study_database_task: {e}", exc_info=True)
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_security_alert(self, alert_type: str, details: dict):
    """
    Send security alert email asynchronously.
    
    Args:
        alert_type: Type of alert (user_lockout, rate_limit_exceeded, etc.)
        details: Alert details dict
    """
    try:
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        
        # Get admin emails
        admin_emails = [email for name, email in getattr(settings, 'ADMINS', [])]
        if not admin_emails:
            logger.warning("No admin emails configured for security alerts")
            return {'status': 'skipped', 'reason': 'No admin emails'}
        
        # Build subject and message
        subject_map = {
            'user_lockout': 'User Account Locked Out',
            'rate_limit_exceeded': 'Rate Limit Exceeded',
            'invalid_user_attempt': 'Invalid User Login Attempt',
            'suspicious_activity': 'Suspicious Activity Detected',
        }
        
        subject = f"[{settings.ORGANIZATION_NAME}] {subject_map.get(alert_type, 'Security Alert')}"
        
        # Build message
        message_lines = [
            f"Security Alert: {alert_type}",
            f"Server: {getattr(settings, 'SERVER_NAME', 'Unknown')}",
            "",
            "Details:",
        ]
        for key, value in details.items():
            message_lines.append(f"  {key}: {value}")
        
        message = "\n".join(message_lines)
        
        # Send email
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_emails,
            fail_silently=False,
        )
        
        logger.info(f"Security alert sent: {alert_type}")
        return {'status': 'sent', 'alert_type': alert_type, 'recipients': len(admin_emails)}
        
    except Exception as e:
        logger.error(f"Failed to send security alert: {e}", exc_info=True)
        raise self.retry(exc=e)


@shared_task
def sync_study_permissions_task(study_code: str, force: bool = False):
    """
    Async task to sync permissions for a study.
    
    Useful after migrations or bulk updates.
    """
    try:
        from backends.tenancy.utils.role_manager import StudyRoleManager
        
        result = StudyRoleManager.assign_permissions(study_code, force=force)
        
        logger.info(
            f"Synced permissions for study {study_code}: "
            f"assigned={result.get('permissions_assigned', 0)}, "
            f"removed={result.get('permissions_removed', 0)}"
        )
        
        return {
            'status': 'success',
            'study_code': study_code,
            **result
        }
        
    except Exception as e:
        logger.error(f"Error syncing permissions for {study_code}: {e}", exc_info=True)
        return {'status': 'error', 'message': str(e)}


@shared_task
def cleanup_expired_sessions_task():
    """
    Periodic task to clean up expired sessions and related data.
    """
    try:
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        
        # Delete expired sessions
        expired_count = Session.objects.filter(
            expire_date__lt=timezone.now()
        ).delete()[0]
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired sessions")
        
        return {'status': 'success', 'sessions_deleted': expired_count}
        
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}", exc_info=True)
        return {'status': 'error', 'message': str(e)}
