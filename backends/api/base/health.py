"""
Health Check API Views and Utilities.

Provides comprehensive health check endpoints for monitoring
system status, database connectivity, cache availability,
disk usage, and memory.
"""

import os
import time
import shutil
from datetime import datetime, timezone
from functools import wraps

from django.conf import settings
from django.db import connection, connections
from django.core.cache import cache
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator


def rate_limit_health_check(key_prefix: str, max_requests: int = 10, window_seconds: int = 60):
    """
    Rate limiting decorator for health check endpoints.
    
    Prevents abuse of detailed health endpoints that query databases.
    Uses Django cache for tracking request counts.
    
    Args:
        key_prefix: Unique prefix for cache key
        max_requests: Maximum requests allowed per window
        window_seconds: Time window in seconds
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # Get client IP for rate limiting
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR', 'unknown')
            
            cache_key = f"health_ratelimit:{key_prefix}:{ip}"
            
            # Get current count
            current_count = cache.get(cache_key, 0)
            
            if current_count >= max_requests:
                return JsonResponse({
                    "status": "rate_limited",
                    "message": f"Too many requests. Max {max_requests} per {window_seconds}s",
                    "retry_after": window_seconds,
                }, status=429)
            
            # Increment counter
            cache.set(cache_key, current_count + 1, window_seconds)
            
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator


class HealthCheckMixin:
    """
    Mixin providing health check utilities.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.health_settings = getattr(settings, "HEALTH_CHECK_SETTINGS", {})
    
    def get_db_timeout(self):
        return self.health_settings.get("db_timeout", 5)
    
    def get_cache_key(self):
        return self.health_settings.get("cache_key", "health_check_test")
    
    def get_disk_path(self):
        return self.health_settings.get("disk_path", "/")
    
    def get_disk_max_percent(self):
        return self.health_settings.get("disk_usage_max", 90)
    
    def get_memory_min_mb(self):
        return self.health_settings.get("memory_min_mb", 100)
    
    def get_response_time_warning(self):
        return self.health_settings.get("response_time_warning", 500)
    
    def get_response_time_critical(self):
        return self.health_settings.get("response_time_critical", 2000)


class HealthCheckView(HealthCheckMixin, View):
    """
    Basic health check endpoint.
    
    Returns a simple OK response for load balancer health checks.
    Lightweight and fast - minimal processing.
    
    Usage:
        GET /health/
        
    Response:
        200 OK: {"status": "healthy", "timestamp": "..."}
        503 Service Unavailable: {"status": "unhealthy", ...}
    """
    
    def get(self, request):
        return JsonResponse({
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "ressynt-api",
        })


class DetailedHealthCheckView(HealthCheckMixin, View):
    """
    Detailed health check endpoint.
    
    Performs comprehensive checks on all system components:
    - Database connectivity (all configured databases)
    - Cache availability
    - Disk usage
    - Memory availability
    
    Rate limited to 10 requests per minute per IP.
    
    Usage:
        GET /health/detailed/
        
    Response:
        200 OK: All checks passed
        503 Service Unavailable: One or more checks failed
        429 Too Many Requests: Rate limit exceeded
    """
    
    @rate_limit_health_check('detailed', max_requests=10, window_seconds=60)
    def get(self, request):
        start_time = time.time()
        
        checks = {
            "database": self._check_databases(),
            "cache": self._check_cache(),
            "disk": self._check_disk(),
            "memory": self._check_memory(),
        }
        
        # Calculate overall status
        all_healthy = all(
            check.get("status") == "healthy" 
            for check in checks.values()
        )
        
        response_time_ms = (time.time() - start_time) * 1000
        
        response_data = {
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "ressynt-api",
            "version": getattr(settings, "APP_VERSION", "unknown"),
            "environment": os.environ.get("DJANGO_ENV", "unknown"),
            "response_time_ms": round(response_time_ms, 2),
            "checks": checks,
        }
        
        # Add warnings for slow response
        if response_time_ms > self.get_response_time_critical():
            response_data["warning"] = "Response time critical"
        elif response_time_ms > self.get_response_time_warning():
            response_data["warning"] = "Response time elevated"
        
        status_code = 200 if all_healthy else 503
        return JsonResponse(response_data, status=status_code)
    
    def _check_databases(self):
        """Check connectivity for all configured databases."""
        results = {}
        overall_healthy = True
        
        for db_alias in connections:
            try:
                start = time.time()
                conn = connections[db_alias]
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                latency_ms = (time.time() - start) * 1000
                
                results[db_alias] = {
                    "status": "healthy",
                    "latency_ms": round(latency_ms, 2),
                }
            except Exception as e:
                overall_healthy = False
                results[db_alias] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "databases": results,
        }
    
    def _check_cache(self):
        """Check cache availability."""
        cache_key = self.get_cache_key()
        test_value = f"health_check_{time.time()}"
        
        try:
            start = time.time()
            
            # Test set
            cache.set(cache_key, test_value, timeout=10)
            
            # Test get
            retrieved = cache.get(cache_key)
            
            # Cleanup
            cache.delete(cache_key)
            
            latency_ms = (time.time() - start) * 1000
            
            if retrieved == test_value:
                return {
                    "status": "healthy",
                    "latency_ms": round(latency_ms, 2),
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "Cache value mismatch",
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }
    
    def _check_disk(self):
        """Check disk usage."""
        try:
            disk_path = self.get_disk_path()
            
            # Windows compatibility
            if os.name == "nt" and disk_path == "/":
                disk_path = "C:\\"
            
            usage = shutil.disk_usage(disk_path)
            percent_used = (usage.used / usage.total) * 100
            max_percent = self.get_disk_max_percent()
            
            return {
                "status": "healthy" if percent_used < max_percent else "unhealthy",
                "path": disk_path,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent_used": round(percent_used, 2),
                "threshold_percent": max_percent,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }
    
    def _check_memory(self):
        """Check memory availability."""
        try:
            # Try to use psutil if available
            try:
                import psutil
                mem = psutil.virtual_memory()
                min_mb = self.get_memory_min_mb()
                available_mb = mem.available / (1024**2)
                
                return {
                    "status": "healthy" if available_mb > min_mb else "unhealthy",
                    "total_mb": round(mem.total / (1024**2), 2),
                    "available_mb": round(available_mb, 2),
                    "percent_used": round(mem.percent, 2),
                    "threshold_mb": min_mb,
                }
            except ImportError:
                # Fallback: basic check without psutil
                return {
                    "status": "healthy",
                    "message": "psutil not installed - detailed memory check unavailable",
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }


class ReadinessCheckView(HealthCheckMixin, View):
    """
    Kubernetes readiness probe endpoint.
    
    Checks if the application is ready to accept traffic.
    Verifies database and cache are accessible.
    
    Usage:
        GET /health/ready/
        
    Response:
        200 OK: Ready to accept traffic
        503 Service Unavailable: Not ready
    """
    
    def get(self, request):
        checks = {}
        
        # Check primary database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            checks["database"] = "ok"
        except Exception as e:
            checks["database"] = f"error: {e}"
        
        # Check cache
        try:
            cache.set("readiness_check", "ok", timeout=5)
            cache.get("readiness_check")
            cache.delete("readiness_check")
            checks["cache"] = "ok"
        except Exception as e:
            checks["cache"] = f"error: {e}"
        
        is_ready = all(v == "ok" for v in checks.values())
        
        return JsonResponse({
            "ready": is_ready,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
        }, status=200 if is_ready else 503)


class LivenessCheckView(HealthCheckMixin, View):
    """
    Kubernetes liveness probe endpoint.
    
    Simple check to verify the application process is alive.
    Should be lightweight - no external dependencies checked.
    
    Usage:
        GET /health/live/
        
    Response:
        200 OK: Application is alive
    """
    
    def get(self, request):
        return JsonResponse({
            "alive": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
