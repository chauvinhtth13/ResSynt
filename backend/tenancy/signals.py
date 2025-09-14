# backend/tenancy/signals.py - FIXED VERSION
from django.core.signals import request_finished
from django.db import connections
from django.conf import settings
from django.core.cache import cache
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from axes.signals import user_locked_out
import logging
from typing import Set

logger = logging.getLogger('backend.tenancy')  # FIXED: Changed from 'apps.tenancy'

User = get_user_model()


# ============================================
# AXES SIGNAL HANDLERS
# ============================================

@receiver(user_locked_out)
def handle_axes_lockout(sender, request, username, ip_address, **kwargs):
    """When axes locks out a user, update their status"""
    try:
        user = User.objects.get(username=username)
        if user.status == User.Status.ACTIVE: # type: ignore
            user.status = User.Status.BLOCKED # type: ignore
            user.is_active = False
            
            # Add note about the lockout
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            note = f"\n[{timestamp}] Auto-blocked by axes from IP {ip_address}"
            user.notes = (user.notes or "") + note # type: ignore
            
            user.save(update_fields=['status', 'is_active', 'notes'])
            logger.info(f"User {username} auto-blocked due to axes lockout from IP {ip_address}")
            
            # Send notification if configured
            from django.core.mail import mail_admins
            if getattr(settings, 'AXES_NOTIFY_ADMINS_ON_LOCKOUT', False):
                mail_admins(
                    f"User {username} blocked by axes",
                    f"User {username} has been automatically blocked due to too many failed login attempts from IP {ip_address}.",
                    fail_silently=True
                )
                
    except User.DoesNotExist:
        logger.warning(f"Axes lockout for non-existent user: {username}")
    except Exception as e:
        logger.error(f"Error handling axes lockout for {username}: {e}")


@receiver(pre_save, sender=User)
def sync_status_with_axes(sender, instance, **kwargs):
    """Before saving, check if we need to sync with axes"""
    if instance.pk:  # Only for existing users
        try:
            # Get the old instance
            old_user = User.objects.filter(pk=instance.pk).first()
            
            if old_user:
                # If changing to ACTIVE from BLOCKED, ensure axes is unblocked
                if instance.status == User.Status.ACTIVE and old_user.status == User.Status.BLOCKED: # type: ignore
                    instance.reset_axes_locks()
                    instance.is_active = True
                    logger.info(f"Auto-unblocking axes for user {instance.username} due to ACTIVE status")
                
                # If changing from any inactive status to ACTIVE
                elif instance.status == User.Status.ACTIVE and old_user.status != User.Status.ACTIVE: # type: ignore
                    instance.reset_axes_locks()
                    instance.is_active = True
                    logger.info(f"Resetting axes locks for user {instance.username} due to activation")
                
                # Log status changes
                if old_user.status != instance.status: # type: ignore
                    logger.info(f"User {instance.username} status changed from {old_user.status} to {instance.status}") # type: ignore
                    
        except Exception as e:
            logger.error(f"Error in pre_save signal for user {instance.username}: {e}")

# ============================================
# DATABASE CONNECTION MANAGEMENT
# ============================================

class DBConnectionManager:
    """Manage DB connections efficiently."""
    
    USAGE_CACHE_KEY_PREFIX = 'study_db_usage_'
    BATCH_SIZE = 10  # Process in batches
    
    @classmethod
    def release_unused_dbs(cls, sender, **kwargs):
        """Release unused study DBs."""
        # Close unusable connections first
        for conn in connections.all():
            conn.close_if_unusable_or_obsolete()
        
        # Batch process DB aliases
        study_aliases = [
            alias for alias in connections.databases.keys()
            if alias != 'default' and alias.startswith(settings.STUDY_DB_PREFIX)
        ]
        
        to_remove: Set[str] = set()
        for alias in study_aliases[:cls.BATCH_SIZE]:  # Process limited batch
            usage_key = f"{cls.USAGE_CACHE_KEY_PREFIX}{alias}"
            if not cache.get(usage_key):
                to_remove.add(alias)
            else:
                cache.delete(usage_key)  # Reset for next cycle
        
        # Batch remove
        for alias in to_remove:
            try:
                if alias in connections:
                    connections[alias].close()
                del connections.databases[alias]
                logger.debug(f"Released: {alias}")
            except Exception as e:
                logger.error(f"Error releasing {alias}: {e}")

# Connect optimized handler
request_finished.connect(DBConnectionManager.release_unused_dbs)