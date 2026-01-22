from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from datetime import datetime, timedelta
import logging

# Import models
from backends.studies.study_44en.models.household import (
    HH_CASE,
    HH_Member,
)
from backends.studies.study_44en.models.individual import Individual
from backends.studies.study_44en.models.per_data import HH_PERSONAL_DATA

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

DB_ALIAS = 'db_study_44en'


# ============================================================================
# MAIN DASHBOARD VIEW
# ============================================================================

@login_required
def home_dashboard(request):
    """
    Main dashboard for Study 44EN
    
    Displays:
    - Summary statistics
    - Ward distribution table
    - Recent households
    - Recent individuals
    
    Backend-first: All data prepared here, minimal JS in template
    """
    try:
        # ===== BASIC STATISTICS =====
        
        # Total households
        total_households = HH_CASE.objects.count()
        
        # Total members (from HH_Member table)
        total_members = HH_Member.objects.count()
        
        # Total individuals (from Individual table - those with detailed data)
        total_individuals = Individual.objects.count()
        
        # Recent households (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_households_count = HH_CASE.objects.filter(
            last_modified_at__gte=thirty_days_ago
        ).count()
        
        # Recent individuals (last 30 days)
        recent_individuals_count = Individual.objects.filter(
            last_modified_at__gte=thirty_days_ago
        ).count()
        
        # Follow-ups statistics (placeholder - implement when needed)
        total_followups = 0
        pending_followups = 0
        
        # ===== RECENT LISTS =====
        
        # Recent households (top 10)
        recent_household_list = HH_CASE.objects.select_related(
            'personal_data'
        ).order_by('-last_modified_at')[:10]
        
        # Recent individuals (top 10)
        recent_individual_list = Individual.objects.select_related(
            'MEMBERID',
            'MEMBERID__HHID'
        ).order_by('-last_modified_at')[:10]
        
        # ===== WARD DISTRIBUTION DATA =====
        
        # Get ward distribution (WARD is encrypted in HH_PERSONAL_DATA)
        # We need to decrypt each record to count by ward
        ward_distribution = get_ward_distribution()
        
        # ===== CONTEXT =====
        
        context = {
            'study_code': '44EN',
            'study_name': 'Study 44EN - Household Survey',
            
            # Statistics
            'total_households': total_households,
            'total_members': total_members,
            'total_individuals': total_individuals,
            'recent_households_count': recent_households_count,
            'recent_individuals_count': recent_individuals_count,
            'total_followups': total_followups,
            'pending_followups': pending_followups,
            
            # Recent lists
            'recent_household_list': recent_household_list,
            'recent_individual_list': recent_individual_list,
            
            # Ward distribution
            'ward_distribution': ward_distribution,
        }
        
        return render(request, 'studies/study_44en/home_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}", exc_info=True)
        # Return minimal context on error
        return render(request, 'studies/study_44en/home_dashboard.html', {
            'study_code': '44EN',
            'study_name': 'Study 44EN',
            'error': str(e),
        })


# ============================================================================
# WARD DISTRIBUTION HELPER
# ============================================================================

def get_ward_distribution():
    """
    Calculate household and participant distribution by ward
    
    Returns:
        list: [{
            'ward': 'Phường X',
            'total_households': N,
            'total_participants': M
        }, ...]
    
    Note: WARD is encrypted, so we need to decrypt each record
    """
    try:
        # Get all personal data with related household and members
        personal_data_records = HH_PERSONAL_DATA.objects.select_related(
            'HHID'
        ).prefetch_related(
            'HHID__members'
        ).all()
        
        # Aggregate by ward (after decryption)
        ward_stats = {}
        
        for pd in personal_data_records:
            # Decrypt ward (EncryptedCharField auto-decrypts on access)
            ward = pd.WARD
            
            if not ward:
                ward = 'Không xác định'
            
            # Initialize ward entry if not exists
            if ward not in ward_stats:
                ward_stats[ward] = {
                    'ward': ward,
                    'total_households': 0,
                    'total_participants': 0,
                }
            
            # Count household
            ward_stats[ward]['total_households'] += 1
            
            # Count participants (members of this household)
            member_count = pd.HHID.members.count()
            ward_stats[ward]['total_participants'] += member_count
        
        # Convert to list and sort by ward name
        ward_list = list(ward_stats.values())
        ward_list.sort(key=lambda x: x['ward'])
        
        # Calculate totals
        total_row = {
            'ward': 'TỔNG CỘNG',
            'total_households': sum(w['total_households'] for w in ward_list),
            'total_participants': sum(w['total_participants'] for w in ward_list),
            'is_total': True,
        }
        
        # Add total row at the end
        ward_list.append(total_row)
        
        return ward_list
        
    except Exception as e:
        logger.error(f"Ward distribution error: {str(e)}", exc_info=True)
        return []


# ============================================================================
# API ENDPOINTS (Optional - for dynamic refresh)
# ============================================================================

@require_GET
@login_required
def get_ward_distribution_api(request):
    """
    API endpoint for ward distribution data
    
    Returns:
        JSON with ward distribution data
    
    Usage:
        GET /api/ward-distribution/
    """
    try:
        ward_distribution = get_ward_distribution()
        
        return JsonResponse({
            'success': True,
            'data': ward_distribution,
            'timestamp': datetime.now().isoformat(),
        })
        
    except Exception as e:
        logger.error(f"Ward distribution API error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)


@require_GET
@login_required
def get_dashboard_stats_api(request):
    """
    API endpoint for dashboard statistics (for refresh)
    
    Returns:
        JSON with all dashboard stats
    
    Usage:
        GET /api/dashboard-stats/
    """
    try:
        # Calculate statistics
        total_households = HH_CASE.objects.count()
        total_members = HH_Member.objects.count()
        total_individuals = Individual.objects.count()
        
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_households_count = HH_CASE.objects.filter(
            last_modified_at__gte=thirty_days_ago
        ).count()
        recent_individuals_count = Individual.objects.filter(
            last_modified_at__gte=thirty_days_ago
        ).count()
        
        return JsonResponse({
            'success': True,
            'data': {
                'total_households': total_households,
                'total_members': total_members,
                'total_individuals': total_individuals,
                'recent_households_count': recent_households_count,
                'recent_individuals_count': recent_individuals_count,
                'total_followups': 0,  # Placeholder
                'pending_followups': 0,  # Placeholder
            },
            'timestamp': datetime.now().isoformat(),
        })
        
    except Exception as e:
        logger.error(f"Dashboard stats API error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)


