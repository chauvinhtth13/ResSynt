# backends/studies/study_43en/services/report_data_service.py
"""
Report Data Service - Improved Version

Fetches data from database for TMG report generation.
Uses same logic as dashboard.py for consistency.
"""

from django.db.models import Count, Q
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
        """
        try:
            from backends.studies.study_43en.models.patient import SAM_CASE, ENR_CASE
            from backends.studies.study_43en.models.contact import SAM_CONTACT, ENR_CONTACT
            
            # Get enrolled patients/contacts for site filtering
            if self.site_filter:
                enrolled_patients = ENR_CASE.objects.using(DB_ALIAS).filter(
                    USUBJID__SITEID=self.site_filter
                ).values('USUBJID')
                patient_samples_qs = SAM_CASE.objects.using(DB_ALIAS).filter(
                    USUBJID__in=enrolled_patients
                )
                
                enrolled_contacts = ENR_CONTACT.objects.using(DB_ALIAS).filter(
                    USUBJID__SITEID=self.site_filter
                ).values('USUBJID')
                contact_samples_qs = SAM_CONTACT.objects.using(DB_ALIAS).filter(
                    USUBJID__in=enrolled_contacts
                )
            else:
                patient_samples_qs = SAM_CASE.objects.using(DB_ALIAS)
                contact_samples_qs = SAM_CONTACT.objects.using(DB_ALIAS)
            
            # PATIENT SAMPLING - by visit
            patient_stats = {}
            for visit_num in ['1', '2', '3', '4']:
                visit_samples = patient_samples_qs.filter(SAMPLE_TYPE=visit_num, SAMPLE=True)
                patient_stats[f'visit{visit_num}'] = {
                    'total': visit_samples.count(),
                    'blood': visit_samples.filter(BLOOD=True).count(),
                    'stool': visit_samples.filter(STOOL=True).count(),
                    'rectswab': visit_samples.filter(RECTSWAB=True).count(),
                    'throatswab': visit_samples.filter(THROATSWAB=True).count(),
                }
            
            # CONTACT SAMPLING - by visit  
            contact_stats = {}
            for visit_num in ['1', '2', '3', '4']:
                visit_samples = contact_samples_qs.filter(SAMPLE_TYPE=visit_num, SAMPLE=True)
                contact_stats[f'visit{visit_num}'] = {
                    'total': visit_samples.count(),
                    'blood': visit_samples.filter(BLOOD=True).count(),
                    'stool': visit_samples.filter(STOOL=True).count(),
                    'rectswab': visit_samples.filter(RECTSWAB=True).count(),
                    'throatswab': visit_samples.filter(THROATSWAB=True).count(),
                }
            
            return {
                'patient': patient_stats,
                'contact': contact_stats,
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
        """
        try:
            from backends.studies.study_43en.models.patient import SCR_CASE, ENR_CASE, SAM_CASE
            from backends.studies.study_43en.models.contact import ENR_CONTACT, SAM_CONTACT
            
            sites_to_query = [self.site_filter] if self.site_filter else ['003', '020', '011']
            result_data = {}
            
            for site_code in sites_to_query:
                site_name = SITE_NAMES.get(site_code, site_code)
                
                # PATIENT DATA
                patients = ENR_CASE.objects.using(DB_ALIAS).filter(USUBJID__SITEID=site_code)
                patient_count = patients.count()
                
                # Clinical Kp (at screening)
                clinical_kp = SCR_CASE.objects.using(DB_ALIAS).filter(
                    SITEID=site_code,
                    ISOLATEDKPNFROMINFECTIONORBLOOD=True
                ).count()
                
                # Patient samples
                patient_samples = SAM_CASE.objects.using(DB_ALIAS).filter(
                    USUBJID__in=patients.values('USUBJID')
                )
                
                patient_kp_data = {}
                for visit_num in ['1', '2', '3', '4']:
                    visit_samples = patient_samples.filter(SAMPLE_TYPE=visit_num)
                    
                    # Throat swab: KLEBPNEU_3
                    throat_total = visit_samples.filter(THROATSWAB=True).count()
                    throat_kp = visit_samples.filter(THROATSWAB=True, KLEBPNEU_3=True).count()
                    
                    # Stool/Rectal: KLEBPNEU_1 or KLEBPNEU_2
                    stool_total = visit_samples.filter(Q(STOOL=True) | Q(RECTSWAB=True)).count()
                    stool_kp = visit_samples.filter(
                        Q(STOOL=True) | Q(RECTSWAB=True)
                    ).filter(
                        Q(KLEBPNEU_1=True) | Q(KLEBPNEU_2=True)
                    ).count()
                    
                    patient_kp_data[f'visit{visit_num}'] = {
                        'throat_total': throat_total,
                        'throat_kp': throat_kp,
                        'stool_total': stool_total,
                        'stool_kp': stool_kp,
                    }
                
                # CONTACT DATA
                contacts = ENR_CONTACT.objects.using(DB_ALIAS).filter(USUBJID__SITEID=site_code)
                contact_count = contacts.count()
                
                contact_samples = SAM_CONTACT.objects.using(DB_ALIAS).filter(
                    USUBJID__in=contacts.values('USUBJID')
                )
                
                contact_kp_data = {}
                for visit_num in ['1', '2', '3', '4']:
                    visit_samples = contact_samples.filter(SAMPLE_TYPE=visit_num)
                    
                    throat_total = visit_samples.filter(THROATSWAB=True).count()
                    throat_kp = visit_samples.filter(THROATSWAB=True, KLEBPNEU_3=True).count()
                    
                    stool_total = visit_samples.filter(Q(STOOL=True) | Q(RECTSWAB=True)).count()
                    stool_kp = visit_samples.filter(
                        Q(STOOL=True) | Q(RECTSWAB=True)
                    ).filter(
                        Q(KLEBPNEU_1=True) | Q(KLEBPNEU_2=True)
                    ).count()
                    
                    contact_kp_data[f'visit{visit_num}'] = {
                        'throat_total': throat_total,
                        'throat_kp': throat_kp,
                        'stool_total': stool_total,
                        'stool_kp': stool_kp,
                    }
                
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
