# backends/studies/study_43en/services/report_data_service.py
"""
Report Data Service - Improved Version

Fetches data from database for TMG report generation.
Uses same logic as dashboard.py for consistency.
"""

from django.db.models import Count, Q, Case, When, IntegerField
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

# Database alias for study_43en
DB_ALIAS = 'db_study_43en'

# Site name mapping (same as dashboard)
SITE_NAMES = {
    '003': 'HTD',
    '020': 'NHTD', 
    '011': 'Cho Ray',
}


class ReportDataService:
    """
    Service lấy dữ liệu từ database để tạo báo cáo TMG
    
    Sử dụng logic tương tự dashboard.py để đảm bảo consistency
    """
    
    def __init__(self, site_filter: str = None):
        """
        Initialize report data service
        
        Args:
            site_filter: Optional site code ('003', '020', '011', 'all')
        """
        self.site_filter = site_filter if site_filter != 'all' else None
    
    def get_report_data(self, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """
        Lấy toàn bộ dữ liệu cần thiết cho báo cáo
        
        Returns:
            Dict chứa tất cả dữ liệu báo cáo
        """
        return {
            'action_points': [],  # Manual input
            'general_procedures': '',  # Manual input
            'ethics_regulatory': '',  # Manual input
            'study_amendments': '',  # Manual input
            'recruitment': self._get_recruitment_stats(),
            'deviations': [],  # Manual input
            'sample_processing': self._get_sample_processing_stats(),
            'data_management': '',  # Manual input
            'safety_reporting': self._get_safety_stats(),
            'aob': '',  # Manual input
        }
    
    def _get_filtered_queryset(self, model_class, site_field: str = 'SITEID'):
        """Get queryset filtered by site"""
        qs = model_class.objects.using(DB_ALIAS)
        
        if self.site_filter and hasattr(model_class, site_field):
            qs = qs.filter(**{site_field: self.site_filter})
        
        return qs
    
    def _get_recruitment_stats(self) -> Dict:
        """
        Lấy thống kê recruitment từ SCR_CASE và ENR_CASE
        Giống như dashboard cards
        """
        try:
            from backends.studies.study_43en.models.patient import SCR_CASE, ENR_CASE
            from backends.studies.study_43en.models.contact import SCR_CONTACT, ENR_CONTACT
            
            # PATIENT STATS
            # Total screened patients
            scr_patient_qs = self._get_filtered_queryset(SCR_CASE, 'SITEID')
            total_screened_patients = scr_patient_qs.count()
            
            # Total enrolled patients (confirmed screening)
            # ENR_CASE uses USUBJID which links to SCR_CASE
            if self.site_filter:
                enrolled_patients_qs = ENR_CASE.objects.using(DB_ALIAS).filter(
                    USUBJID__SITEID=self.site_filter
                )
            else:
                enrolled_patients_qs = ENR_CASE.objects.using(DB_ALIAS)
            total_enrolled_patients = enrolled_patients_qs.count()
            
            # CONTACT STATS
            scr_contact_qs = self._get_filtered_queryset(SCR_CONTACT, 'SITEID')
            total_screened_contacts = scr_contact_qs.count()
            
            if self.site_filter:
                enrolled_contacts_qs = ENR_CONTACT.objects.using(DB_ALIAS).filter(
                    USUBJID__SITEID=self.site_filter
                )
            else:
                enrolled_contacts_qs = ENR_CONTACT.objects.using(DB_ALIAS)
            total_enrolled_contacts = enrolled_contacts_qs.count()
            
            return {
                'total_screened_patients': total_screened_patients,
                'total_enrolled_patients': total_enrolled_patients,
                'total_screened_contacts': total_screened_contacts,
                'total_enrolled_contacts': total_enrolled_contacts,
            }
            
        except Exception as e:
            logger.error(f"Could not get recruitment stats: {e}")
            return {
                'total_screened_patients': 0,
                'total_enrolled_patients': 0,
                'total_screened_contacts': 0,
                'total_enrolled_contacts': 0,
            }
    
    def _get_sample_processing_stats(self) -> Dict:
        """
        Lấy thống kê sample processing theo format dashboard
        
        Sample types:
        - SAMPLE_TYPE='1': Day 1 (at enrollment)
        - SAMPLE_TYPE='2': Day 10
        - SAMPLE_TYPE='3': Day 28
        - SAMPLE_TYPE='4': Day 90
        
        OPTIMIZED: Uses aggregation to reduce N+1 queries
        """
        try:
            from backends.studies.study_43en.models.patient import SAM_CASE
            from backends.studies.study_43en.models.contact import SAM_CONTACT
            
            # Build base querysets with site filtering
            if self.site_filter:
                patient_samples_qs = SAM_CASE.site_objects.using(DB_ALIAS).filter_by_site(self.site_filter)
                contact_samples_qs = SAM_CONTACT.site_objects.using(DB_ALIAS).filter_by_site(self.site_filter)
            else:
                patient_samples_qs = SAM_CASE.objects.using(DB_ALIAS)
                contact_samples_qs = SAM_CONTACT.objects.using(DB_ALIAS)
            
            def _aggregate_sample_stats(samples_qs):
                """
                OPTIMIZED: Single query with conditional aggregation
                Instead of 4 visits x 5 counts = 20 queries, now just 1 query
                """
                stats = {}
                
                # Use values + annotate for efficient grouped aggregation
                aggregated = samples_qs.filter(SAMPLE=True).values('SAMPLE_TYPE').annotate(
                    total=Count('pk'),
                    blood=Count(Case(When(BLOOD=True, then=1), output_field=IntegerField())),
                    stool=Count(Case(When(STOOL=True, then=1), output_field=IntegerField())),
                    rectswab=Count(Case(When(RECTSWAB=True, then=1), output_field=IntegerField())),
                    throatswab=Count(Case(When(THROATSWAB=True, then=1), output_field=IntegerField())),
                )
                
                # Convert to dict by visit
                for row in aggregated:
                    visit_key = f"visit{row['SAMPLE_TYPE']}"
                    stats[visit_key] = {
                        'total': row['total'],
                        'blood': row['blood'],
                        'stool': row['stool'],
                        'rectswab': row['rectswab'],
                        'throatswab': row['throatswab'],
                    }
                
                # Ensure all visits have entries (even if 0)
                for visit_num in ['1', '2', '3', '4']:
                    visit_key = f"visit{visit_num}"
                    if visit_key not in stats:
                        stats[visit_key] = {
                            'total': 0, 'blood': 0, 'stool': 0,
                            'rectswab': 0, 'throatswab': 0
                        }
                
                return stats
            
            return {
                'patient': _aggregate_sample_stats(patient_samples_qs),
                'contact': _aggregate_sample_stats(contact_samples_qs),
            }
            
        except Exception as e:
            logger.error(f"Could not get sample processing stats: {e}")
            return {'patient': {}, 'contact': {}}
    
    def _get_safety_stats(self) -> Dict:
        """Lấy thống kê safety reporting từ AEHospEvent"""
        try:
            from backends.studies.study_43en.models.patient.CLI_AEHospEvent import AEHospEvent
            
            ae_qs = AEHospEvent.objects.using(DB_ALIAS)
            
            # Filter by site if specified
            if self.site_filter:
                ae_qs = ae_qs.filter(USUBJID__USUBJID__SITEID=self.site_filter)
            
            total_ae = ae_qs.count()
            
            return {
                'total_ae': total_ae,
                'total_sae': 0,  # No SAE flag in current model
                'deaths': 0,
                'ae_discontinuation': 0,
            }
            
        except Exception as e:
            logger.error(f"Could not get safety stats: {e}")
            return {
                'total_ae': 0,
                'total_sae': 0,
                'deaths': 0,
                'ae_discontinuation': 0,
            }
    
    def get_kpneumoniae_stats(self) -> Dict:
        """
        Lấy thống kê K. pneumoniae isolation
        Giống format Table 7 trong PDF report
        
        OPTIMIZED: Reduced from ~40 queries per site to ~4 queries per site
        using aggregation
        """
        try:
            from backends.studies.study_43en.models.patient import SCR_CASE, ENR_CASE, SAM_CASE
            from backends.studies.study_43en.models.contact import ENR_CONTACT, SAM_CONTACT
            
            sites_to_query = [self.site_filter] if self.site_filter else ['003', '020', '011']
            result_data = {}
            
            def _aggregate_kp_stats(samples_qs):
                """
                OPTIMIZED: Single query with conditional aggregation for all visits
                """
                stats = {}
                
                # Group by SAMPLE_TYPE and aggregate all counts in one query
                aggregated = samples_qs.values('SAMPLE_TYPE').annotate(
                    throat_total=Count(Case(When(THROATSWAB=True, then=1), output_field=IntegerField())),
                    throat_kp=Count(Case(When(THROATSWAB=True, KLEBPNEU_3=True, then=1), output_field=IntegerField())),
                    stool_total=Count(Case(
                        When(Q(STOOL=True) | Q(RECTSWAB=True), then=1), 
                        output_field=IntegerField()
                    )),
                    stool_kp=Count(Case(
                        When(
                            (Q(STOOL=True) | Q(RECTSWAB=True)) & (Q(KLEBPNEU_1=True) | Q(KLEBPNEU_2=True)),
                            then=1
                        ),
                        output_field=IntegerField()
                    )),
                )
                
                for row in aggregated:
                    visit_key = f"visit{row['SAMPLE_TYPE']}"
                    stats[visit_key] = {
                        'throat_total': row['throat_total'],
                        'throat_kp': row['throat_kp'],
                        'stool_total': row['stool_total'],
                        'stool_kp': row['stool_kp'],
                    }
                
                # Ensure all visits exist
                for visit_num in ['1', '2', '3', '4']:
                    visit_key = f"visit{visit_num}"
                    if visit_key not in stats:
                        stats[visit_key] = {
                            'throat_total': 0, 'throat_kp': 0,
                            'stool_total': 0, 'stool_kp': 0
                        }
                
                return stats
            
            for site_code in sites_to_query:
                site_name = SITE_NAMES.get(site_code, site_code)
                
                # PATIENT DATA - Use site_objects for consistent filtering
                patient_count = ENR_CASE.site_objects.using(DB_ALIAS).filter_by_site(site_code).count()
                
                # Clinical Kp (at screening)
                clinical_kp = SCR_CASE.site_objects.using(DB_ALIAS).filter_by_site(site_code).filter(
                    ISOLATEDKPNFROMINFECTIONORBLOOD=True
                ).count()
                
                # Patient samples - Use site_objects
                patient_samples = SAM_CASE.site_objects.using(DB_ALIAS).filter_by_site(site_code)
                patient_kp_data = _aggregate_kp_stats(patient_samples)
                
                # CONTACT DATA
                contact_count = ENR_CONTACT.site_objects.using(DB_ALIAS).filter_by_site(site_code).count()
                contact_samples = SAM_CONTACT.site_objects.using(DB_ALIAS).filter_by_site(site_code)
                contact_kp_data = _aggregate_kp_stats(contact_samples)
                
                result_data[site_code] = {
                    'site_name': site_name,
                    'patient': {
                        'count': patient_count,
                        'clinical_kp': clinical_kp,
                        'sampling': patient_kp_data,
                    },
                    'contact': {
                        'count': contact_count,
                        'sampling': contact_kp_data,
                    },
                }
            
            return result_data
            
        except Exception as e:
            logger.error(f"Could not get K. pneumoniae stats: {e}")
            return {}
