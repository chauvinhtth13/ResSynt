# backends/tenancy/tasks.py
"""
Celery tasks for tenancy module.
Handles async operations like security alerts, cleanup, etc.
"""
import logging
from typing import Dict, Any, Optional

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


# ==========================================
# SECURITY ALERT TASKS
# ==========================================

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def send_security_alert(
    self, 
    alert_type: str, 
    details: Dict[str, Any]
) -> bool:
    """
    Send security alert email asynchronously.
    
    Args:
        alert_type: Type of alert (user_lockout, invalid_user_attempt, etc.)
        details: Dictionary with alert details
        
    Returns:
        bool: True if email sent successfully
    """
    try:
        timestamp = details.get('timestamp', timezone.now().strftime('%Y-%m-%d %H:%M:%S'))
        username = details.get('username', 'unknown')
        ip_address = details.get('ip_address', 'unknown')
        
        # Build subject based on alert type
        subjects = {
            'user_lockout': f'[Security] User Lockout: {username}',
            'invalid_user_attempt': f'[Security] Invalid User Attempt: {username}',
            'suspicious_activity': f'[Security] Suspicious Activity Detected',
            'password_reset': f'[Security] Password Reset Request: {username}',
        }
        subject = subjects.get(alert_type, f'[Security] Alert: {alert_type}')
        
        # Build message
        message = _build_alert_message(alert_type, details, timestamp)
        
        # Get admin emails
        admin_emails = _get_admin_emails()
        
        if not admin_emails:
            logger.warning("No admin emails configured for security alerts")
            return False
        
        # Send email
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
            recipient_list=admin_emails,
            fail_silently=False,
        )
        
        logger.info(f"Security alert sent: {alert_type} for {username}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send security alert [{alert_type}]: {e}")
        raise


def _build_alert_message(
    alert_type: str, 
    details: Dict[str, Any], 
    timestamp: str
) -> str:
    """Build formatted alert message."""
    
    base_info = f"""
Security Alert Report
=====================

Alert Type: {alert_type}
Timestamp: {timestamp}
Username: {details.get('username', 'N/A')}
IP Address: {details.get('ip_address', 'N/A')}
"""
    
    if alert_type == 'user_lockout':
        return base_info + f"""
Action Required: User account has been locked due to multiple failed login attempts.

Recommendation:
- Verify if this is a legitimate user
- Check for potential brute force attack from IP {details.get('ip_address')}
- Consider blocking IP if suspicious
- Contact user if legitimate

To unlock user via command line:
    python manage.py axes_reset_user {details.get('username')}
"""
    
    elif alert_type == 'invalid_user_attempt':
        return base_info + f"""
Warning: Multiple login attempts for non-existent username.

This could indicate:
- Typo by legitimate user
- Reconnaissance attack
- Credential stuffing attempt

Recommendation:
- Monitor IP {details.get('ip_address')} for further attempts
- Consider IP blocking if pattern continues
"""
    
    elif alert_type == 'suspicious_activity':
        return base_info + f"""
Suspicious Activity Detected

Additional Details:
{details.get('additional_info', 'No additional information')}

Please investigate immediately.
"""
    
    else:
        # Generic message
        additional = '\n'.join(f"  {k}: {v}" for k, v in details.items())
        return base_info + f"""
Additional Details:
{additional}
"""


def _get_admin_emails() -> list:
    """Get list of admin emails for alerts."""
    # Try various settings
    admin_email = getattr(settings, 'ADMIN_EMAIL', None)
    if admin_email:
        return [admin_email] if isinstance(admin_email, str) else list(admin_email)
    
    # Fall back to ADMINS setting
    admins = getattr(settings, 'ADMINS', [])
    if admins:
        return [email for name, email in admins]
    
    # Fall back to SECURITY_ALERT_EMAILS
    security_emails = getattr(settings, 'SECURITY_ALERT_EMAILS', [])
    if security_emails:
        return list(security_emails)
    
    return []


# ==========================================
# CLEANUP TASKS
# ==========================================

@shared_task
def cleanup_expired_sessions() -> Dict[str, int]:
    """
    Clean up expired sessions and related data.
    Should be run periodically (e.g., daily via celery beat).
    """
    from django.contrib.sessions.models import Session
    
    results = {'sessions_deleted': 0, 'connections_cleaned': 0}
    
    try:
        # Delete expired sessions
        expired = Session.objects.filter(expire_date__lt=timezone.now())
        results['sessions_deleted'] = expired.count()
        expired.delete()
        
        if results['sessions_deleted'] > 0:
            logger.info(f"Cleaned {results['sessions_deleted']} expired sessions")
        
    except Exception as e:
        logger.error(f"Error cleaning sessions: {e}")
    
    return results


@shared_task
def cleanup_old_access_logs(days: int = 30) -> Dict[str, int]:
    """
    Clean up old axes access logs.
    Should be run periodically to prevent table bloat.
    
    Args:
        days: Number of days to keep logs
    """
    from datetime import timedelta
    
    results = {'access_logs_deleted': 0, 'access_attempts_cleaned': 0}
    
    try:
        from axes.models import AccessLog, AccessAttempt
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Clean access logs
        old_logs = AccessLog.objects.filter(attempt_time__lt=cutoff_date)
        results['access_logs_deleted'] = old_logs.count()
        old_logs.delete()
        
        # Clean old successful attempts (keep failed ones longer)
        old_attempts = AccessAttempt.objects.filter(
            attempt_time__lt=cutoff_date,
            failures_since_start=0
        )
        results['access_attempts_cleaned'] = old_attempts.count()
        old_attempts.delete()
        
        total = results['access_logs_deleted'] + results['access_attempts_cleaned']
        if total > 0:
            logger.info(f"Cleaned {total} old access records")
        
    except Exception as e:
        logger.error(f"Error cleaning access logs: {e}")
    
    return results


@shared_task
def reset_user_axes_lock(username: str) -> bool:
    """
    Reset axes lock for a specific user.
    Can be triggered manually or by admin action.
    """
    try:
        from axes.utils import reset
        reset(username=username)
        logger.info(f"Reset axes lock for user: {username}")
        return True
    except Exception as e:
        logger.error(f"Failed to reset axes for {username}: {e}")
        return False


# ==========================================
# MONITORING TASKS
# ==========================================

@shared_task
def check_suspicious_activity() -> Optional[Dict[str, Any]]:
    """
    Check for suspicious login patterns.
    Run periodically to detect potential attacks.
    """
    from datetime import timedelta
    from django.db.models import Count
    
    try:
        from axes.models import AccessLog
        
        # Check last hour
        one_hour_ago = timezone.now() - timedelta(hours=1)
        
        # Find IPs with many failed attempts
        suspicious_ips = AccessLog.objects.filter(
            attempt_time__gte=one_hour_ago,
        ).values('ip_address').annotate(
            attempt_count=Count('id')
        ).filter(attempt_count__gte=20)  # 20+ attempts/hour is suspicious
        
        if suspicious_ips:
            for entry in suspicious_ips:
                send_security_alert.delay(
                    alert_type='suspicious_activity',
                    details={
                        'ip_address': entry['ip_address'],
                        'attempt_count': entry['attempt_count'],
                        'period': 'last hour',
                        'additional_info': f"IP made {entry['attempt_count']} login attempts in 1 hour"
                    }
                )
            
            return {
                'suspicious_ips_found': len(suspicious_ips),
                'details': list(suspicious_ips)
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error checking suspicious activity: {e}")
        return None
