"""
Quick Performance Test Script

So sánh performance trước/sau optimization
"""
import os
import django
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.cache import cache
from django.db import connection, reset_queries
from backends.studies.study_43en.models import SCR_CASE, ENR_CASE
from backends.studies.study_43en.utils.site_utils import (
    get_filtered_queryset,
    batch_get_related,
    batch_check_exists,
)
from backends.tenancy.db_router import set_current_db

# CRITICAL: Set database context
DB_ALIAS = 'db_study_43en'
set_current_db(DB_ALIAS)

def test_without_cache():
    """Test WITHOUT cache"""
    print("\n" + "="*80)
    print("TEST 1: WITHOUT CACHE (simulating old behavior)")
    print("="*80)
    
    cache.clear()
    reset_queries()
    start_time = time.time()
    
    # Get cases
    cases = get_filtered_queryset(SCR_CASE, 'all', 'all', use_cache=False).filter(
        is_confirmed=True
    )[:10]
    
    # N+1 pattern - individual queries for each case
    for case in cases:
        try:
            enrollment = get_filtered_queryset(
                ENR_CASE, 'all', 'all', use_cache=False
            ).filter(USUBJID=case).first()
        except:
            pass
    
    end_time = time.time()
    execution_time = (end_time - start_time) * 1000
    num_queries = len(connection.queries)
    
    print(f"\n📊 Results:")
    print(f"   Queries: {num_queries}")
    print(f"   Time:    {execution_time:.2f}ms")
    
    return {'queries': num_queries, 'time': execution_time}


def test_with_cache():
    """Test WITH cache + batch queries"""
    print("\n" + "="*80)
    print("TEST 2: WITH CACHE + BATCH QUERIES (new optimized)")
    print("="*80)
    
    # Warm cache
    print("\n🔥 Warming cache...")
    cache.clear()
    get_filtered_queryset(SCR_CASE, 'all', 'all', use_cache=True)
    get_filtered_queryset(ENR_CASE, 'all', 'all', use_cache=True)
    
    # Now test with cache
    reset_queries()
    start_time = time.time()
    
    # Get cases with cache
    cases = get_filtered_queryset(SCR_CASE, 'all', 'all', use_cache=True).filter(
        is_confirmed=True
    )[:10]
    
    cases_list = list(cases)
    
    # 🚀 Batch query - using batch_get_related helper
    enrollment_map = batch_get_related(
        cases_list,
        ENR_CASE,
        'USUBJID',
        'all',
        'all'
    )
    
    end_time = time.time()
    execution_time = (end_time - start_time) * 1000
    num_queries = len(connection.queries)
    
    print(f"\n📊 Results:")
    print(f"   Queries: {num_queries}")
    print(f"   Time:    {execution_time:.2f}ms")
    print(f"   Cache HITs: Check log for '✅ Cache HIT' messages")
    
    return {'queries': num_queries, 'time': execution_time}


def main():
    print("\n🚀 PERFORMANCE BENCHMARK - Patient List Optimization")
    print("Testing 10 cases with enrollments")
    
    # Test 1: Without cache
    no_cache_stats = test_without_cache()
    
    # Test 2: With cache
    cache_stats = test_with_cache()
    
    # Comparison
    print("\n" + "="*80)
    print("📈 COMPARISON")
    print("="*80)
    
    query_reduction = no_cache_stats['queries'] - cache_stats['queries']
    query_pct = (query_reduction / no_cache_stats['queries'] * 100) if no_cache_stats['queries'] > 0 else 0
    
    time_reduction = no_cache_stats['time'] - cache_stats['time']
    time_pct = (time_reduction / no_cache_stats['time'] * 100) if no_cache_stats['time'] > 0 else 0
    
    print(f"\n📌 WITHOUT CACHE:")
    print(f"   Queries: {no_cache_stats['queries']}")
    print(f"   Time:    {no_cache_stats['time']:.2f}ms")
    
    print(f"\n📌 WITH CACHE:")
    print(f"   Queries: {cache_stats['queries']}")
    print(f"   Time:    {cache_stats['time']:.2f}ms")
    
    print(f"\n✅ IMPROVEMENT:")
    print(f"   Queries: -{query_reduction} ({query_pct:.1f}% reduction)")
    print(f"   Time:    -{time_reduction:.2f}ms ({time_pct:.1f}% faster)")
    
    # Grade
    if query_pct > 80:
        grade = "🏆 EXCELLENT"
    elif query_pct > 50:
        grade = "✅ GOOD"
    elif query_pct > 20:
        grade = "⚠️  FAIR"
    else:
        grade = "❌ NEEDS IMPROVEMENT"
    
    print(f"\n{grade}")
    print("="*80)
    
    # Show cache effectiveness
    print("\n💡 TIP: Check logs for cache performance:")
    print("   - Look for '✅ Cache HIT' messages")
    print("   - Look for '🚀 Batch got X/X' messages")
    print("   - Compare with old logs that had many duplicate queries")


if __name__ == '__main__':
    main()
