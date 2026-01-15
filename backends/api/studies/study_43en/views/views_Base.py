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

from backends.audit_logs.utils import get_site_filtered_object_or_404

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
    get_site_filtered_object_or_404,
    batch_get_related,
    batch_check_exists,
    invalidate_cache,
)


# ==========================================
#  PATIENT LIST - 🚀 OPTIMIZED WITH REDIS
# ==========================================

@login_required
def patient_list(request):
    """
    Danh sách các bệnh nhân - OPTIMIZED VERSION
    
     Improvements:
    - Redis caching for queries
    - Batch queries thay vì N+1
    - Giảm từ ~100 queries xuống ~10 queries
    """
    query = request.GET.get('q', '')
    
    # Get site filter
    site_filter, filter_type = get_site_filter_params(request)
    
    logger.info(f"patient_list - User: {request.user.username}, Site: {site_filter}, Type: {filter_type}")
    
    # 🚀 Get filtered queryset (with Redis caching)
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
    
    # 🚀 BATCH: Get all enrollments trong 1 query
    enrollment_map = batch_get_related(
        list(page_obj.object_list),
        ENR_CASE,
        'USUBJID',
        site_filter,
        filter_type
    )
    
    # 🚀 BATCH: Check all CRFs existence
    enrollments = [e for e in enrollment_map.values() if e is not None]
    
    if enrollments:
        crf_status_map = batch_check_exists(
            enrollments,
            [CLI_CASE, DISCH_CASE, EndCaseCRF, FU_CASE_28, FU_CASE_90, SAM_CASE, LaboratoryTest],
            'USUBJID',
            site_filter,
            filter_type
        )
    else:
        crf_status_map = {}
    
    # 🚀 BATCH: Get all discharge cases to check death status
    discharge_map = {}
    if enrollments:
        enrollment_ids = [e.pk for e in enrollments]
        discharges = DISCH_CASE.objects.using('db_study_43en').filter(
            USUBJID__in=enrollment_ids
        ).select_related('USUBJID')
        discharge_map = {d.USUBJID_id: d for d in discharges}
    
    # Process status (giờ chỉ là lookup, không query DB!)
    for case in page_obj:
        enrollment = enrollment_map.get(case.pk)
        
        case.has_enrollment = enrollment is not None
        case.enrollment_date = enrollment.ENRDATE if enrollment else None
        
        if not case.has_enrollment:
            case.process_status = 'not_enrolled'
            case.process_label = 'Not Enrolled'
            case.process_badge = 'secondary'
            continue
        
        # Get CRF status từ batch results
        crf_status = crf_status_map.get(enrollment.pk, {})
        
        # 🔥 Check death status from discharge
        discharge_case = discharge_map.get(enrollment.pk)
        is_deceased = discharge_case and discharge_case.DEATHATDISCH == 'Yes'
        
        # If patient died, study ends early (no need for all CRFs)
        if is_deceased:
            case.process_status = 'completed'
            case.process_label = 'Study Completed (Died)'
            case.process_badge = 'dark'
            continue
        
        # Check EndCaseCRF
        if crf_status.get('EndCaseCRF', False):
            case.process_status = 'completed'
            case.process_label = 'Study Completed'
            case.process_badge = 'success'
            continue
        
        # Check other CRFs
        all_completed = all([
            crf_status.get('CLI_CASE', False),
            crf_status.get('DISCH_CASE', False),
            crf_status.get('FU_CASE_28', False),
            crf_status.get('FU_CASE_90', False),
            crf_status.get('SAM_CASE', False),
            crf_status.get('LaboratoryTest', False),
        ])
        
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
    
    return render(request, 'studies/study_43en/patient/list/patient_list.html', context)


# ==========================================
#  PATIENT DETAIL - REFACTORED
# ==========================================

@login_required
def patient_detail(request, usubjid):
    """View chi tiết bệnh nhân -  WITH NEW SITE FILTERING"""
    
    #  NEW: Get site filter
    site_filter, filter_type = get_site_filter_params(request)
    
    logger.info(f"patient_detail - USUBJID: {usubjid}, Site: {site_filter}, Type: {filter_type}")
    
    #  NEW: Get screening case với permission check
    screeningcase = get_site_filtered_object_or_404(SCR_CASE, site_filter, filter_type, USUBJID=usubjid)
    
    # ==========================================
    # ENR_CASE - Enrollment
    # ==========================================
    try:
        enrollmentcase = get_filtered_queryset(ENR_CASE, site_filter, filter_type).get(USUBJID=screeningcase)
        has_enrollment = True
        
        # Expected dates
        try:
            expecteddates = get_filtered_queryset(ExpectedDates, site_filter, filter_type).get(USUBJID=enrollmentcase)
        except ExpectedDates.DoesNotExist:
            expecteddates = None
    except ENR_CASE.DoesNotExist:
        enrollmentcase = None
        has_enrollment = False
        expecteddates = None
    
    # ==========================================
    # CLI_CASE - Clinical
    # ==========================================
    clinicalcase = None
    has_clinical = False
    if enrollmentcase:
        try:
            clinicalcase = get_filtered_queryset(CLI_CASE, site_filter, filter_type).get(USUBJID=enrollmentcase)
            has_clinical = True
        except CLI_CASE.DoesNotExist:
            pass
    
    # ==========================================
    # Laboratory, Microbiology, Sample
    # 🚀 OPTIMIZED: Use direct queries with aggregation
    # ==========================================
    if enrollmentcase:
        # Direct query to avoid loading all 2420 objects from cache
        from django.db.models import Count, Max
        
        # Laboratory - single query for count + latest
        lab_qs = LaboratoryTest.objects.using('db_study_43en').filter(USUBJID=enrollmentcase)
        lab_stats = lab_qs.aggregate(
            total=Count('id'),
            latest_date=Max('last_modified_at')
        )
        laboratory_count = lab_stats['total']
        latest_laboratory = lab_qs.order_by('-last_modified_at').first() if laboratory_count > 0 else None
        
        # Microbiology - single query
        micro_qs = LAB_Microbiology.objects.using('db_study_43en').filter(USUBJID=enrollmentcase)
        micro_stats = micro_qs.aggregate(
            total=Count('id'),
            latest_date=Max('last_modified_at')
        )
        microbiology_count = micro_stats['total']
        latest_microbiology = micro_qs.order_by('-last_modified_at').first() if microbiology_count > 0 else None
        
        # Sample - single query
        sample_qs = SAM_CASE.objects.using('db_study_43en').filter(USUBJID=enrollmentcase)
        sample_stats = sample_qs.aggregate(
            total=Count('id'),
            latest_date=Max('last_modified_at')
        )
        sample_count = sample_stats['total']
        latest_sample = sample_qs.order_by('-last_modified_at').first() if sample_count > 0 else None
    else:
        laboratory_count = microbiology_count = sample_count = 0
        latest_laboratory = latest_microbiology = latest_sample = None
    
    has_laboratory_tests = laboratory_count > 0
    has_microbiology_cultures = microbiology_count > 0
    
    # ==========================================
    # Follow-ups, Discharge, End Case
    # 🚀 OPTIMIZED: Direct queries for single objects
    # ==========================================
    fu_case_28 = None
    fu_case_90 = None
    disch_case = None
    endcasecrf = None
    has_followup = has_followup90 = has_discharge = has_endcasecrf = False
    
    if enrollmentcase:
        # Follow-up Day 28
        fu_case_28 = FU_CASE_28.objects.using('db_study_43en').filter(USUBJID=enrollmentcase).first()
        has_followup = fu_case_28 is not None
        
        # Follow-up Day 90
        fu_case_90 = FU_CASE_90.objects.using('db_study_43en').filter(USUBJID=enrollmentcase).first()
        has_followup90 = fu_case_90 is not None
        
        # Discharge
        disch_case = DISCH_CASE.objects.using('db_study_43en').filter(USUBJID=enrollmentcase).first()
        has_discharge = disch_case is not None
        
        # End Case
        endcasecrf = EndCaseCRF.objects.using('db_study_43en').filter(USUBJID=enrollmentcase).first()
        has_endcasecrf = endcasecrf is not None
    
    # ==========================================
    # Death Status
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
    # Calculated Fields
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
    
    return render(request, 'studies/study_43en/patient/list/patient_detail.html', context)


# ==========================================
#  CONTACT LIST - 🚀 OPTIMIZED WITH REDIS
# ==========================================

@login_required
def contact_list(request):
    """
    Danh sách contacts - OPTIMIZED VERSION
    
     Improvements:
    - Redis caching for queries
    - Batch queries thay vì N+1
    - Giảm từ ~50+ queries xuống ~10 queries
    """
    query = request.GET.get('q', '')
    
    # Get site filter
    site_filter, filter_type = get_site_filter_params(request)
    
    logger.info(f"contact_list - User: {request.user.username}, Site: {site_filter}, Type: {filter_type}")
    
    # 🚀 Get filtered queryset (with Redis caching)
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
    
    # 🚀 BATCH: Get all enrollments trong 1 query
    enrollment_map = batch_get_related(
        list(page_obj.object_list),
        ENR_CONTACT,
        'USUBJID',
        site_filter,
        filter_type
    )
    
    # 🚀 BATCH: Check all CRFs existence
    enrollments = [e for e in enrollment_map.values() if e is not None]
    
    if enrollments:
        crf_status_map = batch_check_exists(
            enrollments,
            [ContactEndCaseCRF, SAM_CONTACT, FU_CONTACT_28, FU_CONTACT_90],
            'USUBJID',
            site_filter,
            filter_type
        )
    else:
        crf_status_map = {}
    
    # Process status (giờ chỉ là lookup, không query DB!)
    for contact in page_obj:
        enrollment = enrollment_map.get(contact.pk)
        
        contact.has_enrollment = enrollment is not None
        contact.enrollment_date = enrollment.ENRDATE if enrollment else None
        
        if not contact.has_enrollment:
            contact.process_status = 'not_enrolled'
            contact.process_label = 'Not Enrolled'
            contact.process_badge = 'secondary'
            continue
        
        # Get CRF status từ batch results
        crf_status = crf_status_map.get(enrollment.pk, {})
        
        # Check EndCaseCRF
        if crf_status.get('ContactEndCaseCRF', False):
            contact.process_status = 'completed'
            contact.process_label = 'Study Completed'
            contact.process_badge = 'success'
            continue
        
        # Check other CRFs
        all_completed = all([
            crf_status.get('SAM_CONTACT', False),
            crf_status.get('FU_CONTACT_28', False),
            crf_status.get('FU_CONTACT_90', False),
        ])
        
        if all_completed:
            contact.process_status = 'completed'
            contact.process_label = 'Study Completed'
            contact.process_badge = 'success'
        else:
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
    
    return render(request, 'studies/study_43en/contact/list/contact_list.html', context)


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
        
        return render(request, 'studies/study_43en/contact/list/contact_detail.html', context)
        
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
    
    return render(request, 'studies/study_43en/base/export_data.html', context)



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
