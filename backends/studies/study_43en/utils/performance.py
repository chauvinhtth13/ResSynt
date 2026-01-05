"""
Performance Monitoring & Profiling Utilities

Công cụ đo lường performance để verify optimization effectiveness
"""
import time
import logging
from functools import wraps
from django.db import connection, reset_queries
from django.conf import settings

logger = logging.getLogger(__name__)


def profile_view(view_name=None):
    """
    Decorator để profile view performance
    
    Logs:
    - Execution time (ms)
    - Number of queries
    - Query time (ms)
    - Cache hits (if available)
    
    Usage:
        @profile_view("patient_list")
        def patient_list(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get view name
            name = view_name or view_func.__name__
            
            # Enable query logging
            reset_queries()
            
            # Start timing
            start_time = time.time()
            
            # Execute view
            response = view_func(request, *args, **kwargs)
            
            # End timing
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000  # Convert to ms
            
            # Get query stats
            queries = connection.queries
            num_queries = len(queries)
            
            # Calculate total query time
            query_time = sum(float(q.get('time', 0)) for q in queries) * 1000  # Convert to ms
            
            # Log performance metrics
            logger.info(
                f"⚡ PERFORMANCE [{name}] | "
                f"Time: {execution_time:.2f}ms | "
                f"Queries: {num_queries} | "
                f"DB Time: {query_time:.2f}ms | "
                f"User: {request.user.username if request.user.is_authenticated else 'Anonymous'}"
            )
            
            # Log detailed query breakdown if too many queries
            if num_queries > 20:
                logger.warning(
                    f"⚠️  HIGH QUERY COUNT [{name}]: {num_queries} queries detected!"
                )
                
                # Group similar queries
                query_patterns = {}
                for q in queries:
                    sql = q['sql']
                    # Extract table name
                    if 'FROM' in sql:
                        table = sql.split('FROM')[1].split()[0].strip('"')
                    else:
                        table = 'unknown'
                    
                    query_patterns[table] = query_patterns.get(table, 0) + 1
                
                logger.debug(f"Query breakdown: {query_patterns}")
            
            return response
        
        return wrapper
    return decorator


def get_query_stats():
    """
    Get current query statistics
    
    Returns:
        dict: {
            'count': int,
            'time': float (ms),
            'queries': list
        }
    """
    queries = connection.queries
    return {
        'count': len(queries),
        'time': sum(float(q.get('time', 0)) for q in queries) * 1000,
        'queries': queries
    }


def print_performance_report(before_stats, after_stats, operation_name="Operation"):
    """
    Print performance comparison report
    
    Args:
        before_stats: Stats before optimization
        after_stats: Stats after optimization
        operation_name: Name of the operation
    """
    query_reduction = before_stats['count'] - after_stats['count']
    query_reduction_pct = (query_reduction / before_stats['count'] * 100) if before_stats['count'] > 0 else 0
    
    time_reduction = before_stats['time'] - after_stats['time']
    time_reduction_pct = (time_reduction / before_stats['time'] * 100) if before_stats['time'] > 0 else 0
    
    logger.info(f"""
    ╔══════════════════════════════════════════════════════════════
    ║  PERFORMANCE REPORT: {operation_name}
    ╠══════════════════════════════════════════════════════════════
    ║  BEFORE OPTIMIZATION:
    ║    Queries: {before_stats['count']}
    ║    DB Time: {before_stats['time']:.2f}ms
    ║
    ║  AFTER OPTIMIZATION:
    ║    Queries: {after_stats['count']}
    ║    DB Time: {after_stats['time']:.2f}ms
    ║
    ║  IMPROVEMENT:
    ║    ✅ Queries: -{query_reduction} ({query_reduction_pct:.1f}% reduction)
    ║    ✅ DB Time: -{time_reduction:.2f}ms ({time_reduction_pct:.1f}% faster)
    ╚══════════════════════════════════════════════════════════════
    """)


class PerformanceMonitor:
    """
    Context manager for monitoring performance
    
    Usage:
        with PerformanceMonitor("My Operation") as pm:
            # ... do work ...
            pass
        
        # Stats automatically logged
    """
    def __init__(self, operation_name):
        self.operation_name = operation_name
        self.start_time = None
        self.start_queries = None
    
    def __enter__(self):
        reset_queries()
        self.start_time = time.time()
        self.start_queries = len(connection.queries)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        execution_time = (end_time - self.start_time) * 1000
        
        queries = connection.queries[self.start_queries:]
        num_queries = len(queries)
        query_time = sum(float(q.get('time', 0)) for q in queries) * 1000
        
        logger.info(
            f"⚡ [{self.operation_name}] "
            f"Time: {execution_time:.2f}ms | "
            f"Queries: {num_queries} | "
            f"DB Time: {query_time:.2f}ms"
        )
