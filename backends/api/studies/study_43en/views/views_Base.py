import logging
import json
from datetime import date

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.translation import gettext as _
from backends.tenancy.models import Site
from django.db.models import DateTimeField, DateField 

#  Import models từ study app
from backends.studies.study_43en.models.patient import (
    SCR_CASE, ENR_CASE, DISCH_CASE, EndCaseCRF,FU_CASE_28, FU_CASE_90,
    CLI_CASE,SAM_CASE,LaboratoryTest,LAB_Microbiology

)
from backends.studies.study_43en.models.contact import (
    SCR_CONTACT, ENR_CONTACT, 
    FU_CONTACT_28, FU_CONTACT_90,
    ContactEndCaseCRF, SAM_CONTACT
)



from backends.studies.study_43en.models.schedule import ExpectedDates, ContactExpectedDates

#  Import utils từ study app

from backends.studies.study_43en.utils import get_site_filtered_object_or_404

logger = logging.getLogger(__name__)


import pandas as pd
from django.http import HttpResponse
from django.apps import apps
from io import BytesIO
from django.contrib.postgres.fields import JSONField
from django.db.models import DateTimeField
from django.http import HttpResponse


from backends.studies.study_43en.utils.site_utils import (
    get_site_filter_params,
    get_filtered_queryset,
    get_site_filtered_object_or_404
)


# ==========================================
#  PATIENT LIST - REFACTORED
# ==========================================

@login_required
def patient_list(request):
    """Danh sách các bệnh nhân - OPTIMIZED: Batch queries to avoid N+1"""
    query = request.GET.get('q', '')
    
    # Get site filter với 3 strategies
    site_filter, filter_type = get_site_filter_params(request)
    
    logger.info(f"patient_list - User: {request.user.username}, Site: {site_filter}, Type: {filter_type}")
    
    # Get filtered queryset (hỗ trợ all/single/multiple)
    cases = get_filtered_queryset(SCR_CASE, site_filter, filter_type).filter(
        is_confirmed=True
    ).order_by('USUBJID')
    
    # Search
    if query:
        cases = cases.filter(
            Q(USUBJID__icontains=query) | 
            Q(INITIAL__icontains=query)
        )
    
    # Stats
    total_patients = cases.count()
    
    # Pagination
    paginator = Paginator(cases, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # ==========================================
    # OPTIMIZED: Batch fetch all related data
    # ==========================================
    case_list = list(page_obj)
    case_pks = [case.pk for case in case_list]
    
    # Batch fetch enrollments (1 query instead of N)
    enrollments = get_filtered_queryset(ENR_CASE, site_filter, filter_type).filter(
        USUBJID__in=case_pks
    ).select_related('USUBJID')
    enrollment_map = {enr.USUBJID_id: enr for enr in enrollments}
    
    # Get enrollment PKs for further queries
    enrollment_pks = [enr.pk for enr in enrollments]
    
    # Batch fetch EndCaseCRF (1 query)
    endcase_enrollment_ids = set(
        get_filtered_queryset(EndCaseCRF, site_filter, filter_type)
        .filter(USUBJID__in=enrollment_pks)
        .values_list('USUBJID_id', flat=True)
    )
    
    # Batch fetch other CRFs existence (6 queries instead of N*6)
    clinical_ids = set(
        get_filtered_queryset(CLI_CASE, site_filter, filter_type)
        .filter(USUBJID__in=enrollment_pks)
        .values_list('USUBJID_id', flat=True)
    )
    discharge_ids = set(
        get_filtered_queryset(DISCH_CASE, site_filter, filter_type)
        .filter(USUBJID__in=enrollment_pks)
        .values_list('USUBJID_id', flat=True)
    )
    fu28_ids = set(
        get_filtered_queryset(FU_CASE_28, site_filter, filter_type)
        .filter(USUBJID__in=enrollment_pks)
        .values_list('USUBJID_id', flat=True)
    )
    fu90_ids = set(
        get_filtered_queryset(FU_CASE_90, site_filter, filter_type)
        .filter(USUBJID__in=enrollment_pks)
        .values_list('USUBJID_id', flat=True)
    )
    sample_ids = set(
        get_filtered_queryset(SAM_CASE, site_filter, filter_type)
        .filter(USUBJID__in=enrollment_pks)
        .values_list('USUBJID_id', flat=True)
    )
    lab_ids = set(
        get_filtered_queryset(LaboratoryTest, site_filter, filter_type)
        .filter(USUBJID__in=enrollment_pks)
        .values_list('USUBJID_id', flat=True)
    )
    
    # Process status using batched data (no additional queries)
    for case in case_list:
        enrollment = enrollment_map.get(case.pk)
        case.has_enrollment = enrollment is not None
        case.enrollment_date = enrollment.ENRDATE if enrollment else None
        
        if not case.has_enrollment:
            case.process_status = 'not_enrolled'
            case.process_label = 'Not Enrolled'
            case.process_badge = 'secondary'
            continue
        
        enr_pk = enrollment.pk
        
        # Check EndCaseCRF
        if enr_pk in endcase_enrollment_ids:
            case.process_status = 'completed'
            case.process_label = 'Study Completed'
            case.process_badge = 'success'
            continue
        
        # Check all CRFs completion
        has_clinical = enr_pk in clinical_ids
        has_discharge = enr_pk in discharge_ids
        has_fu28 = enr_pk in fu28_ids
        has_fu90 = enr_pk in fu90_ids
        has_sample = enr_pk in sample_ids
        has_lab = enr_pk in lab_ids
        
        all_completed = all([has_clinical, has_discharge, has_fu28, has_fu90, has_sample, has_lab])
        
        if all_completed:
            case.process_status = 'completed'
            case.process_label = 'Study Completed'
            case.process_badge = 'success'
        else:
            case.process_status = 'ongoing'
            case.process_label = 'Ongoing'
            case.process_badge = 'primary'
    
    context = {
        'page_obj': page_obj,
        'total_patients': total_patients,
        'query': query,
        'view_type': 'patients',
        'is_paginated': page_obj.has_other_pages(),
        'site_filter': site_filter,
        'filter_type': filter_type,
    }
    
    return render(request, 'studies/study_43en/CRF/base/patient_list.html', context)


# ==========================================
#  PATIENT DETAIL - REFACTORED
# ==========================================

@login_required
def patient_detail(request, usubjid):
    """View chi tiết bệnh nhân - OPTIMIZED: Batch queries"""
    
    # Get site filter
    site_filter, filter_type = get_site_filter_params(request)
    
    logger.info(f"patient_detail - USUBJID: {usubjid}, Site: {site_filter}, Type: {filter_type}")
    
    # Get screening case với permission check
    screeningcase = get_site_filtered_object_or_404(SCR_CASE, site_filter, filter_type, USUBJID=usubjid)
    
    # ==========================================
    # OPTIMIZED: Batch fetch enrollment and all related data
    # ==========================================
    enrollmentcase = None
    has_enrollment = False
    expecteddates = None
    
    # Try to get enrollment
    enrollment_qs = get_filtered_queryset(ENR_CASE, site_filter, filter_type).filter(
        USUBJID=screeningcase
    )
    enrollmentcase = enrollment_qs.first()
    has_enrollment = enrollmentcase is not None
    
    # Initialize all variables with defaults
    clinicalcase = None
    has_clinical = False
    laboratory_count = microbiology_count = sample_count = 0
    latest_laboratory = latest_microbiology = latest_sample = None
    has_laboratory_tests = has_microbiology_cultures = False
    fu_case_28 = fu_case_90 = None
    has_followup = has_followup90 = False
    disch_case = None
    has_discharge = False
    endcasecrf = None
    has_endcasecrf = False
    
    if enrollmentcase:
        enr_pk = enrollmentcase.pk
        
        # ==========================================
        # BATCH QUERY: Fetch all related CRFs in parallel-style queries
        # ==========================================
        
        # Expected dates
        expecteddates = get_filtered_queryset(
            ExpectedDates, site_filter, filter_type
        ).filter(USUBJID=enrollmentcase).first()
        
        # Clinical case
        clinicalcase = get_filtered_queryset(
            CLI_CASE, site_filter, filter_type
        ).filter(USUBJID=enrollmentcase).first()
        has_clinical = clinicalcase is not None
        
        # Follow-ups
        fu_case_28 = get_filtered_queryset(
            FU_CASE_28, site_filter, filter_type
        ).filter(USUBJID=enrollmentcase).first()
        has_followup = fu_case_28 is not None
        
        fu_case_90 = get_filtered_queryset(
            FU_CASE_90, site_filter, filter_type
        ).filter(USUBJID=enrollmentcase).first()
        has_followup90 = fu_case_90 is not None
        
        # Discharge
        disch_case = get_filtered_queryset(
            DISCH_CASE, site_filter, filter_type
        ).filter(USUBJID=enrollmentcase).first()
        has_discharge = disch_case is not None
        
        # End case
        endcasecrf = get_filtered_queryset(
            EndCaseCRF, site_filter, filter_type
        ).filter(USUBJID=enrollmentcase).first()
        has_endcasecrf = endcasecrf is not None
        
        # ==========================================
        # Laboratory, Microbiology, Sample - Use aggregation
        # ==========================================
        from django.db.models import Count, Max
        
        # Laboratory - count and latest in single query
        lab_qs = get_filtered_queryset(
            LaboratoryTest, site_filter, filter_type
        ).filter(USUBJID=enrollmentcase)
        laboratory_count = lab_qs.count()
        has_laboratory_tests = laboratory_count > 0
        if has_laboratory_tests:
            latest_laboratory = lab_qs.order_by('-last_modified_at').first()
        
        # Microbiology - count and latest in single query
        micro_qs = get_filtered_queryset(
            LAB_Microbiology, site_filter, filter_type
        ).filter(USUBJID=enrollmentcase)
        microbiology_count = micro_qs.count()
        has_microbiology_cultures = microbiology_count > 0
        if has_microbiology_cultures:
            latest_microbiology = micro_qs.order_by('-last_modified_at').first()
        
        # Sample - count and latest in single query
        sample_qs = get_filtered_queryset(
            SAM_CASE, site_filter, filter_type
        ).filter(USUBJID=enrollmentcase)
        sample_count = sample_qs.count()
        if sample_count > 0:
            latest_sample = sample_qs.order_by('-last_modified_at').first()
    
    # ==========================================
    # Death Status (no DB queries needed)
    # ==========================================
    is_deceased = False
    death_form = None
    death_date = None
    
    if disch_case and disch_case.DEATHATDISCH == 'Yes':
        is_deceased = True
        death_form = 'Discharge'
        death_date = disch_case.DISCHDATE
    elif fu_case_28 and fu_case_28.Dead == 'Yes':
        is_deceased = True
        death_form = 'Follow-up Day 28'
        death_date = fu_case_28.DeathDate
    elif fu_case_90 and fu_case_90.Dead == 'Yes':
        is_deceased = True
        death_form = 'Follow-up Day 90'
        death_date = fu_case_90.DeathDate
    
    # ==========================================
    # Calculated Fields (no DB queries needed)
    # ==========================================
    days_since_enrollment = 0
    if has_enrollment and enrollmentcase and enrollmentcase.ENRDATE:
        days_since_enrollment = (date.today() - enrollmentcase.ENRDATE).days
    
    admission_date = clinicalcase.ADMISDATE if clinicalcase and clinicalcase.ADMISDATE else None
    discharge_date = disch_case.DISCHDATE if disch_case and disch_case.DISCHDATE else None
    
    hospital_stay_days = None
    if admission_date and discharge_date:
        delta = discharge_date - admission_date
        hospital_stay_days = max(delta.days + 1, 1)
    
    # ==========================================
    # Context
    # ==========================================
    context = {
        'screeningcase': screeningcase,
        'enrollmentcase': enrollmentcase,
        'has_enrollment': has_enrollment,
        'is_deceased': is_deceased,
        'death_form': death_form,
        'death_date': death_date,
        'clinicalcase': clinicalcase,
        'has_clinical': has_clinical,
        'admission_date': admission_date,
        'laboratory_count': laboratory_count,
        'has_laboratory_tests': has_laboratory_tests,
        'latest_laboratory': latest_laboratory,
        'microbiology_count': microbiology_count,
        'has_microbiology_cultures': has_microbiology_cultures,
        'latest_microbiology': latest_microbiology,
        'sample_count': sample_count,
        'latest_sample': latest_sample,
        'fu_case_28': fu_case_28,
        'has_followup': has_followup,
        'fu_case_90': fu_case_90,
        'has_followup90': has_followup90,
        'disch_case': disch_case,
        'has_discharge': has_discharge,
        'discharge_date': discharge_date,
        'endcasecrf': endcasecrf,
        'has_endcasecrf': has_endcasecrf,
        'days_since_enrollment': days_since_enrollment,
        'hospital_stay_days': hospital_stay_days,
        'expecteddates': expecteddates,
    }
    
    return render(request, 'studies/study_43en/CRF/base/patient_detail.html', context)


# ==========================================
#  CONTACT LIST - REFACTORED
# ==========================================

@login_required
def contact_list(request):
    """Danh sách contacts -  WITH NEW SITE FILTERING"""
    query = request.GET.get('q', '')
    
    #  NEW: Get site filter
    site_filter, filter_type = get_site_filter_params(request)
    
    logger.info(f"contact_list - User: {request.user.username}, Site: {site_filter}, Type: {filter_type}")
    
    #  NEW: Get filtered queryset
    eligible_screening_contacts = get_filtered_queryset(SCR_CONTACT, site_filter, filter_type).filter(
        CONSENTTOSTUDY=True,
        LIVEIN5DAYS3MTHS=True,
        MEALCAREONCEDAY=True
    )
    
    # Search
    if query:
        eligible_screening_contacts = eligible_screening_contacts.filter(
            Q(USUBJID__icontains=query) |
            Q(INITIAL__icontains=query)
        )
    
    # Sort
    eligible_screening_contacts = eligible_screening_contacts.order_by('SCRID')
    
    # Stats
    total_contacts = eligible_screening_contacts.count()
    enrolled_contacts = eligible_screening_contacts.filter(enrollment_contact__isnull=False).count()
    not_enrolled_contacts = total_contacts - enrolled_contacts
    
    # Pagination
    paginator = Paginator(eligible_screening_contacts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Add status info and process status
    for contact in page_obj:
        try:
            #  Use site filtering for enrollment
            enrollment = get_filtered_queryset(ENR_CONTACT, site_filter, filter_type).filter(USUBJID=contact).first()
            contact.has_enrollment = enrollment is not None
            contact.enrollment_date = enrollment.ENRDATE if enrollment else None
        except:
            contact.has_enrollment = False
            enrollment = None
            contact.enrollment_date = None
        
        if not contact.has_enrollment:
            contact.process_status = 'not_enrolled'
            contact.process_label = 'Not Enrolled'
            contact.process_badge = 'secondary'
            continue
        
        # Check EndCaseCRF for contact
        try:
            has_endcase = get_filtered_queryset(ContactEndCaseCRF, site_filter, filter_type).filter(USUBJID=enrollment).exists()
        except:
            has_endcase = False
        
        if has_endcase:
            contact.process_status = 'completed'
            contact.process_label = 'Study Completed'
            contact.process_badge = 'success'
            continue
        
        # Check other CRFs for contact
        try:
            has_sample = get_filtered_queryset(SAM_CONTACT, site_filter, filter_type).filter(USUBJID=enrollment).exists()
            has_fu28 = get_filtered_queryset(FU_CONTACT_28, site_filter, filter_type).filter(USUBJID=enrollment).exists()
            has_fu90 = get_filtered_queryset(FU_CONTACT_90, site_filter, filter_type).filter(USUBJID=enrollment).exists()
            
            all_completed = all([has_sample, has_fu28, has_fu90])
            
            if all_completed:
                contact.process_status = 'completed'
                contact.process_label = 'Study Completed'
                contact.process_badge = 'success'
            else:
                contact.process_status = 'ongoing'
                contact.process_label = 'Ongoing'
                contact.process_badge = 'primary'
        except Exception as e:
            logger.error(f"Error checking status for contact {contact.USUBJID}: {e}")
            contact.process_status = 'ongoing'
            contact.process_label = 'Ongoing'
            contact.process_badge = 'primary'
    
    context = {
        'page_obj': page_obj,
        'total_contacts': total_contacts,
        'enrolled_contacts': enrolled_contacts,
        'not_enrolled_contacts': not_enrolled_contacts,
        'query': query,
        'view_type': 'contacts',
        'site_filter': site_filter,
        'filter_type': filter_type,
    }
    
    return render(request, 'studies/study_43en/CRF/base/contact_list.html', context)


# ==========================================
#  CONTACT DETAIL - REFACTORED
# ==========================================

@login_required
def contact_detail(request, usubjid):
    """View chi tiết contact -  WITH NEW SITE FILTERING"""
    
    #  NEW: Get site filter
    site_filter, filter_type = get_site_filter_params(request)
    
    try:
        #  NEW: Get với permission check
        screening_contact = get_site_filtered_object_or_404(SCR_CONTACT, site_filter, filter_type, USUBJID=usubjid)
        
        # Enrollment contact
        try:
            enrollment_contact = get_filtered_queryset(ENR_CONTACT, site_filter, filter_type).get(USUBJID=screening_contact)
            has_enrollment = True
            
            # Expected dates
            try:
                contactexpecteddates = get_filtered_queryset(ContactExpectedDates, site_filter, filter_type).get(USUBJID=enrollment_contact)
            except ContactExpectedDates.DoesNotExist:
                contactexpecteddates = None
        except ENR_CONTACT.DoesNotExist:
            enrollment_contact = None
            has_enrollment = False
            contactexpecteddates = None
        
        # Sample collection
        has_sample = False
        sample_collection = None
        sample_count = 0
        if has_enrollment:
            sample_count = get_filtered_queryset(SAM_CONTACT, site_filter, filter_type).filter(USUBJID=enrollment_contact).count()
            has_sample = sample_count > 0
            if has_sample:
                sample_collection = get_filtered_queryset(SAM_CONTACT, site_filter, filter_type).filter(USUBJID=enrollment_contact).first()
        
        # Follow-up 28
        followup_28 = None
        if has_enrollment:
            try:
                followup_28 = get_filtered_queryset(FU_CONTACT_28, site_filter, filter_type).get(USUBJID=enrollment_contact)
            except FU_CONTACT_28.DoesNotExist:
                pass
        
        # Follow-up 90
        followup_90 = None
        if has_enrollment:
            try:
                followup_90 = get_filtered_queryset(FU_CONTACT_90, site_filter, filter_type).get(USUBJID=enrollment_contact)
            except FU_CONTACT_90.DoesNotExist:
                pass
        
        # End case
        contactendcasecrf = None
        has_contactendcasecrf = False
        if has_enrollment:
            try:
                contactendcasecrf = get_filtered_queryset(ContactEndCaseCRF, site_filter, filter_type).get(USUBJID=enrollment_contact)
                has_contactendcasecrf = True
            except ContactEndCaseCRF.DoesNotExist:
                pass
        
        context = {
            'screening_contact': screening_contact,
            'enrollment_contact': enrollment_contact,
            'has_enrollment': has_enrollment,
            'sample_collection': sample_collection,
            'has_sample': has_sample,
            'sample_count': sample_count,
            'followup_28': followup_28,
            'followup_90': followup_90,
            'contactendcasecrf': contactendcasecrf,
            'has_contactendcasecrf': has_contactendcasecrf,
            'contactexpecteddates': contactexpecteddates
        }
        
        return render(request, 'studies/study_43en/CRF/base/contact_detail.html', context)
        
    except Exception as e:
        messages.error(request, f'Không tìm thấy contact {usubjid} hoặc không có quyền truy cập')
        return redirect('43en:screening_contact_list')






def export_to_excel(request):
    """Legacy export function -  WITH SITE FILTERING"""
    #  Get site filter with proper strategy
    site_filter, filter_type = get_site_filter_params(request)
    
    logger.info(f"export_to_excel (legacy) - User: {request.user.username}, Site: {site_filter}, Type: {filter_type}")
    
    buffer = BytesIO()
    writer = pd.ExcelWriter(buffer, engine='openpyxl')

    # Get all models
    models = apps.get_models()

    # Sensitive fields to remove
    sensitive_fields = ['FULLNAME', 'PHONE', 'ADDRESS', 'MEDRECORDID']

    for model in models:
        try:
            #  Apply site filtering
            queryset = get_filtered_queryset(model, site_filter, filter_type)
            if not queryset.exists():
                continue
                
            data = list(queryset.values())
            df = pd.DataFrame(data)
            
            # Remove sensitive fields
            for field in sensitive_fields:
                if field in df.columns:
                    df = df.drop(field, axis=1)
            
            # Format datetime fields
            for field in model._meta.get_fields():
                field_name = field.name
                
                if field_name in sensitive_fields:
                    continue
                    
                if field_name in df.columns:
                    if isinstance(field, DateTimeField):
                        df[field_name] = df[field_name].apply(
                            lambda x: x.strftime('%Y-%m-%d %H:%M:%S %z') if pd.notnull(x) else ''
                        )
                    elif isinstance(field, models.DateField):
                        df[field_name] = df[field_name].apply(
                            lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else ''
                        )
            
            # Write to Excel
            sheet_name = model.__name__[:31]
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
        except Exception as e:
            logger.error(f"Error exporting {model.__name__}: {str(e)}")
            continue

    writer.close()
    buffer.seek(0)

    response = HttpResponse(
        content=buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="database_export.xlsx"'
    return response

@login_required
def export_data_page(request):
    """Hiển thị trang export với filters -  WITH SITE FILTERING"""
    
    #  Get site filter with proper strategy
    site_filter, filter_type = get_site_filter_params(request)
    
    #  Try to get Site model, fallback to hardcoded list
    try:
        from backends.tenancy.models import Site
        
        # Show only user's allowed sites in dropdown
        if filter_type == 'single':
            # Single-site user: only show their site
            sites = Site.objects.using('default').filter(code=site_filter).order_by('code')
        elif filter_type == 'multiple':
            # Multi-site user: show their sites
            sites = Site.objects.using('default').filter(code__in=site_filter).order_by('code')
        else:
            # Super admin: show all sites
            sites = Site.objects.using('default').all().order_by('code')
    except ImportError:
        # Fallback: hardcoded sites
        sites = [
            type('Site', (), {'SITEID': 'HCM01', 'SITENAME': 'Site HCM 01'}),
            type('Site', (), {'SITEID': 'HCM02', 'SITENAME': 'Site HCM 02'}),
            type('Site', (), {'SITEID': 'HN01', 'SITENAME': 'Site HN 01'}),
        ]
    
    #  Calculate estimated records for each CRF
    crf_models = {
        'SCR_CASE': SCR_CASE,
        'ENR_CASE': ENR_CASE,
        'CLI_CASE': CLI_CASE,
        'DISCH_CASE': DISCH_CASE,
        'EndCaseCRF': EndCaseCRF,
        'FU_CASE_28': FU_CASE_28,
        'FU_CASE_90': FU_CASE_90,
        'SAM_CASE': SAM_CASE,
        'LaboratoryTest': LaboratoryTest,
        'LAB_Microbiology': LAB_Microbiology,
        'SCR_CONTACT': SCR_CONTACT,
        'ENR_CONTACT': ENR_CONTACT,
        'FU_CONTACT_28': FU_CONTACT_28,
        'FU_CONTACT_90': FU_CONTACT_90,
        'ContactEndCaseCRF': ContactEndCaseCRF,
        'SAM_CONTACT': SAM_CONTACT,
    }
    
    estimated_counts = {}
    try:
        # Try to import child models
        from backends.studies.study_43en.models.patient import (
            UnderlyingCondition, ENR_CASE_MedHisDrug,
            HistorySymptom, Symptom_72H,
            PriorAntibiotic, InitialAntibiotic, MainAntibiotic,
            AEHospEvent, AntibioticSensitivity
        )
        crf_models.update({
            'UnderlyingCondition': UnderlyingCondition,
            'ENR_CASE_MedHisDrug': ENR_CASE_MedHisDrug,
            'HistorySymptom': HistorySymptom,
            'Symptom_72H': Symptom_72H,
            'PriorAntibiotic': PriorAntibiotic,
            'InitialAntibiotic': InitialAntibiotic,
            'MainAntibiotic': MainAntibiotic,
            'AEHospEvent': AEHospEvent,
            'AntibioticSensitivity': AntibioticSensitivity,
        })
    except ImportError:
        pass
    
    for model_name, model in crf_models.items():
        try:
            if hasattr(model, 'site_objects'):
                queryset = get_filtered_queryset(model, site_filter, filter_type)
                estimated_counts[model_name] = queryset.count()
            else:
                estimated_counts[model_name] = 0
        except:
            estimated_counts[model_name] = 0
    
    #  Get recent exports from session (simple implementation)
    recent_exports = request.session.get('recent_exports', [])[:5]  # Last 5 exports
    
    context = {
        'sites': sites,
        'site_filter': site_filter,
        'filter_type': filter_type,
        'recent_exports': recent_exports,
        'estimated_counts': json.dumps(estimated_counts),  #  Convert to JSON string
    }
    
    return render(request, 'studies/study_43en/CRF/base/export_data.html', context)



@login_required
def export_data(request):
    """Handle export with filters -  WITH SITE FILTERING SECURITY"""
    if request.method != 'POST':
        return redirect('study_43en:export_data_page')
    
    from datetime import datetime
    
    #  NEW: Get site filter from user permissions (NOT from form!)
    site_filter, filter_type = get_site_filter_params(request)
    
    logger.info(f"export_data - User: {request.user.username}, Site: {site_filter}, Type: {filter_type}")
    
    # Get filters from form
    selected_crfs = request.POST.getlist('crfs')
    start_date = request.POST.get('start_date')
    end_date = request.POST.get('end_date')
    export_format = request.POST.get('export_format', 'excel')
    include_sensitive = request.POST.get('include_sensitive') == 'on'
    
    # Validate
    if not selected_crfs:
        messages.error(request, 'Please select at least one CRF to export!')
        return redirect('study_43en:export_data_page')
    
    # Create buffer
    buffer = BytesIO()
    
    if export_format == 'excel':
        writer = pd.ExcelWriter(buffer, engine='openpyxl')
    
    # Sensitive fields to remove
    sensitive_fields = [] if include_sensitive else ['FULLNAME', 'PHONE', 'ADDRESS', 'MEDRECORDID']
    
    # Export each selected CRF
    exported_count = 0
    skipped_models = []
    
    for model_name in selected_crfs:
        try:
            # Get model from study_43en app
            model = apps.get_model('study_43en', model_name)
            
            #  NEW: Apply site filtering with proper security
            #  Skip models without site_objects (child/related models)
            if not hasattr(model, 'site_objects'):
                logger.warning(f" Skipping {model_name}: No site_objects manager (likely a related model)")
                skipped_models.append(model_name)
                continue
            
            try:
                queryset = get_filtered_queryset(model, site_filter, filter_type)
            except Exception as e:
                # Handle models with complex relationships that fail site filtering
                if 'OneToOneField' in str(e) or 'startswith' in str(e):
                    logger.warning(f" Skipping {model_name}: Cannot apply site filtering ({str(e)[:100]})")
                    skipped_models.append(model_name)
                    continue
                else:
                    raise  # Re-raise other errors
            
            # Apply date filter - check multiple possible date fields
            date_field = None
            if  hasattr(model, 'SCREENINGFORMDATE'):
                date_field = 'SCREENINGFORMDATE'
            elif hasattr(model, 'ENRDATE'):
                date_field = 'ENRDATE'
            elif hasattr(model, 'ADMISDATE'):
                date_field = 'ADMISDATE'
            elif hasattr(model, 'created_at'):
                date_field = 'created_at'
            elif hasattr(model, 'last_modified_at'):
                date_field = 'last_modified_at'
            
            if date_field:
                if start_date:
                    queryset = queryset.filter(**{f'{date_field}__gte': start_date})
                if end_date:
                    queryset = queryset.filter(**{f'{date_field}__lte': end_date})
            
            # Convert to DataFrame
            if not queryset.exists():
                logger.info(f"No data for {model_name} with current filters")
                continue
            
            data = list(queryset.values())
            df = pd.DataFrame(data)
            
            # Remove sensitive fields
            for field in sensitive_fields:
                if field in df.columns:
                    df = df.drop(field, axis=1)
            
            # Format datetime and date fields
            from django.db.models import DateTimeField, DateField  #  Import locally if not at top
            
            for field in model._meta.get_fields():
                field_name = field.name
                if field_name not in df.columns:
                    continue
                
                #  FIXED: Use DateField instead of models.DateField
                if isinstance(field, DateTimeField):
                    df[field_name] = df[field_name].apply(
                        lambda x: x.strftime('%Y-%m-%d %H:%M:%S %z') if pd.notnull(x) else ''
                    )
                elif isinstance(field, DateField):  #  CHANGED from models.DateField
                    df[field_name] = df[field_name].apply(
                        lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else ''
                    )
            
            # Write to file
            sheet_name = model_name[:31]  # Excel sheet name limit
            
            if export_format == 'excel':
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:  # CSV - append to buffer
                csv_content = df.to_csv(index=False)
                if exported_count > 0:
                    buffer.write(b'\n\n')  # Separator between tables
                buffer.write(f"# {model_name}\n".encode('utf-8'))
                buffer.write(csv_content.encode('utf-8'))
            
            exported_count += 1
            logger.info(f"Successfully exported {model_name}: {len(df)} records")
        
        except Exception as e:
            logger.error(f"Error exporting {model_name}: {str(e)}", exc_info=True)
            continue
    
    # Check if anything was exported
    if exported_count == 0:
        if skipped_models:
            messages.warning(
                request, 
                f'No data exported! {len(skipped_models)} models were skipped (related/child tables): {", ".join(skipped_models[:5])}'
            )
        else:
            messages.warning(request, 'No data found matching your filters!')
        return redirect('study_43en:export_data_page')
    
    # Finalize file
    if export_format == 'excel':
        writer.close()
    
    buffer.seek(0)
    
    # Create response
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    #  Generate filename with site info
    if filter_type == 'single':
        site_suffix = f"_site_{site_filter}"
    elif filter_type == 'multiple':
        site_suffix = f"_sites_{'_'.join(sorted(site_filter))}"
    else:
        site_suffix = "_all_sites"
    
    filename = f'study_43en{site_suffix}_export_{timestamp}'
    
    if export_format == 'excel':
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename += '.xlsx'
    else:
        content_type = 'text/csv'
        filename += '.csv'
    
    response = HttpResponse(content=buffer.getvalue(), content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    #  Save to recent exports history (in session)
    file_size = len(buffer.getvalue())
    file_size_mb = round(file_size / (1024 * 1024), 2)
    
    export_record = {
        'filename': filename,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'file_size': f'{file_size_mb} MB',
        'crf_count': exported_count,
        'site_filter': site_filter if isinstance(site_filter, str) else ', '.join(sorted(site_filter)),
    }
    
    recent_exports = request.session.get('recent_exports', [])
    recent_exports.insert(0, export_record)  # Add to beginning
    request.session['recent_exports'] = recent_exports[:10]  # Keep last 10
    
    # Build success message
    success_msg = f' Export completed! {exported_count} CRFs exported. Downloaded: {filename}'
    
    if skipped_models:
        success_msg += f' |  {len(skipped_models)} related models skipped (no site filtering available)'
        logger.info(f"Skipped models: {', '.join(skipped_models)}")
    
    messages.success(request, success_msg)
    
    return response