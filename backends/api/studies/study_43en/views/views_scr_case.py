import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils.translation import gettext as _

# Import models
from backends.studies.study_43en.models.patient import ScreeningCase, EnrollmentCase

# Import forms
from backends.api.studies.study_43en.forms.forms_scr_case import ScreeningCaseForm

# Import utils
from backends.studies.study_43en.utils.audit_log_cross_db import audit_log_decorator

logger = logging.getLogger(__name__)


# ============================================
# SCREENING CASE VIEWS - OPTIMIZED
# ============================================

@login_required
@audit_log_decorator(model_name='SCREENINGCASE')
def screening_case_list(request):
    """
    List all screening cases
    
    Optimizations:
    - Query database instead of converting to list
    - Use is_confirmed field for filtering
    - Sort in database
    - Efficient search using Q objects
    """
    # Get filter parameters
    enrolled = request.GET.get('enrolled', '') == 'true'
    query = request.GET.get('q', '').strip()
    site_id = request.session.get('selected_site_id', 'all')

    # Base queryset with site filter
    if site_id and site_id != 'all':
        cases = ScreeningCase.site_objects.filter_by_site(site_id)
    else:
        cases = ScreeningCase.objects.all()

    # Filter by enrollment status (use is_confirmed field)
    if enrolled:
        cases = cases.filter(is_confirmed=True)

    # Search functionality - query database directly
    if query:
        cases = cases.filter(
            Q(SCRID__icontains=query) |
            Q(USUBJID__icontains=query) |
            Q(SUBJID__icontains=query) |
            Q(INITIAL__icontains=query) |
            Q(SITEID__icontains=query)
        )

    # Sort in database - by SITEID and SCRID
    cases = cases.order_by('SITEID', 'SCRID')

    # Statistics - efficient database queries
    total_cases = cases.count()
    eligible_cases = cases.filter(is_confirmed=True).count()
    screen_failure_rate = (
        ((total_cases - eligible_cases) / total_cases * 100) 
        if total_cases > 0 else 0
    )

    # Pagination
    paginator = Paginator(cases, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_cases': total_cases,
        'eligible_cases': eligible_cases,
        'screen_failure_rate': f'{screen_failure_rate:.1f}',
        'query': query,
        'view_type': 'enrolled' if enrolled else 'screening',
        'selected_site_id': site_id,
    }

    return render(
        request,
        'studies/study_43en/table_list/screening_case_list.html',
        context
    )


@login_required
@audit_log_decorator(model_name='SCREENINGCASE')
def screening_case_create(request):
    """
    Create new ScreeningCase
    
    Changes from old version:
    - No manual SCRID generation (model auto-generates)
    - Pass user to form for auto-fill USER_ENTRY
    - Handle UNRECRUITED_REASON validation
    - Clear success/warning messages based on eligibility
    """
    selected_site_id = request.session.get('selected_site_id', 'all')

    if request.method == 'POST':
        form = ScreeningCaseForm(request.POST, user=request.user)
        
        if form.is_valid():
            # Save with user for auto-fill USER_ENTRY, ENTRY, ENTEREDTIME
            screening = form.save()
            
            # Check eligibility using model method
            if screening.is_eligible():
                # Eligible patient - has USUBJID
                messages.success(
                    request,
                    f'Successfully created patient {screening.USUBJID}. '
                    f'Patient is eligible and has been assigned USUBJID.'
                )
                messages.info(
                    request,
                    'Please enter enrollment details to complete registration.'
                )
                
                # Redirect to enrollment form
                return redirect(
                    'study_43en:enrollment_case_create',
                    usubjid=screening.USUBJID
                )
            else:
                # Not eligible - only has SCRID
                reason_display = (
                    screening.get_UNRECRUITED_REASON_display() 
                    if screening.UNRECRUITED_REASON 
                    else 'not eligible'
                )
                messages.warning(
                    request,
                    f'Screening {screening.SCRID} saved. '
                    f'Patient not recruited: {reason_display}'
                )
                
                return redirect('study_43en:screening_case_list')
        else:
            # Form validation errors
            messages.error(
                request,
                'Please correct the errors below.'
            )
    else:
        # GET request - new form
        initial_data = {'STUDYID': '43EN'}
        
        # Set default SITEID if specific site selected
        if selected_site_id != 'all':
            initial_data['SITEID'] = selected_site_id
        
        form = ScreeningCaseForm(initial=initial_data, user=request.user)

    context = {
        'form': form,
        'is_create': True,
        'selected_site_id': selected_site_id,
        'title': 'Create Screening Case',
    }

    return render(
        request,
        'studies/study_43en/CRF/screening_form.html',
        context
    )


@login_required
@audit_log_decorator(model_name='SCREENINGCASE')
def screening_case_update(request, scrid):
    """
    Update ScreeningCase
    
    Improvements:
    - Fixed edge case in eligibility checking
    - Handle all state transitions:
      * not eligible → eligible
      * eligible → not eligible
      * eligible → still eligible
      * not eligible → still not eligible
    - Pass user to form
    - Clear messages for each scenario
    
    Args:
        scrid: SCRID of the screening case (not USUBJID despite parameter name)
    """
    screening = get_object_or_404(ScreeningCase, SCRID=scrid)
    
    # Store old state for comparison
    was_eligible = screening.is_eligible()
    old_usubjid = screening.USUBJID
    
    if request.method == 'POST':
        form = ScreeningCaseForm(
            request.POST,
            instance=screening,
            user=request.user
        )
        
        if form.is_valid():
            # Save with user for audit trail
            screening = form.save()
            
            # Check new state
            is_now_eligible = screening.is_eligible()
            new_usubjid = screening.USUBJID
            
            # Handle state transitions
            
            # Case 1: Was NOT eligible, NOW eligible
            if not was_eligible and is_now_eligible:
                messages.success(
                    request,
                    f'Successfully updated. Patient {screening.USUBJID} is now '
                    f'eligible and has been assigned USUBJID.'
                )
                
                # Check if enrollment exists
                has_enrollment = EnrollmentCase.objects.filter(
                    USUBJID=screening
                ).exists()
                
                if not has_enrollment:
                    messages.info(
                        request,
                        'Please enter enrollment details to complete registration.'
                    )
                    return redirect(
                        'study_43en:enrollment_case_create',
                        usubjid=screening.USUBJID
                    )
                else:
                    # Already has enrollment, go to detail
                    return redirect(
                        'study_43en:patient_detail',
                        usubjid=screening.USUBJID
                    )
            
            # Case 2: Was eligible, STILL eligible
            elif was_eligible and is_now_eligible:
                messages.success(
                    request,
                    f'Successfully updated patient {screening.USUBJID}.'
                )
                
                # Go to patient detail if USUBJID exists
                if screening.USUBJID:
                    return redirect(
                        'study_43en:patient_detail',
                        usubjid=screening.USUBJID
                    )
                else:
                    return redirect('study_43en:screening_case_list')
            
            # Case 3: Was eligible, NOW NOT eligible
            elif was_eligible and not is_now_eligible:
                reason_display = (
                    screening.get_UNRECRUITED_REASON_display() 
                    if screening.UNRECRUITED_REASON 
                    else 'no longer meets criteria'
                )
                messages.warning(
                    request,
                    f'Updated. Patient no longer eligible: {reason_display}. '
                    f'USUBJID has been removed.'
                )
                return redirect('study_43en:screening_case_list')
            
            # Case 4: Was NOT eligible, STILL NOT eligible
            else:
                reason_display = (
                    screening.get_UNRECRUITED_REASON_display() 
                    if screening.UNRECRUITED_REASON 
                    else 'not eligible'
                )
                messages.info(
                    request,
                    f'Updated screening {screening.SCRID}. '
                    f'Patient remains ineligible: {reason_display}'
                )
                return redirect('study_43en:screening_case_list')
        else:
            # Form validation errors
            messages.error(
                request,
                'Please correct the errors below.'
            )
    else:
        # GET request - populate form
        form = ScreeningCaseForm(instance=screening, user=request.user)
    
    context = {
        'form': form,
        'is_create': False,
        'screening': screening,
        'title': f'Update Screening {screening.SCRID}',
    }

    return render(
        request,
        'studies/study_43en/CRF/screening_form.html',
        context
    )


@login_required
@audit_log_decorator(model_name='SCREENINGCASE')
def screening_case_view(request, scrid):
    """
    View ScreeningCase (read-only)
    
    Args:
        scrid: SCRID of the screening case
    """
    screening = get_object_or_404(ScreeningCase, SCRID=scrid)
    form = ScreeningCaseForm(instance=screening, user=request.user)
    
    # Set all fields to readonly
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True
        
        # Prevent radio button changes
        if hasattr(field.widget, 'choices'):
            field.widget.attrs['onclick'] = 'return false;'
    
    context = {
        'form': form,
        'is_create': False,
        'is_readonly': True,
        'screening': screening,
        'selected_site_id': request.session.get('selected_site_id', 'all'),
        'title': f'View Screening {screening.SCRID}',
    }

    return render(
        request,
        'studies/study_43en/CRF/screening_form.html',
        context
    )


# @login_required
# @audit_log_decorator(model_name='SCREENINGCASE')
# def screening_case_delete(request, scrid):
#     """
#     Delete ScreeningCase
    
#     Args:
#         scrid: SCRID of the screening case
#     """
#     screening = get_object_or_404(ScreeningCase, SCRID=scrid)
    
#     if request.method == 'POST':
#         scrid_display = screening.SCRID
#         usubjid_display = screening.USUBJID
        
#         # Delete the screening
#         screening.delete()
        
#         # Success message
#         if usubjid_display:
#             messages.success(
#                 request,
#                 f'Successfully deleted patient {usubjid_display} (SCRID: {scrid_display}).'
#             )
#         else:
#             messages.success(
#                 request,
#                 f'Successfully deleted screening {scrid_display}.'
#             )
        
#         return redirect('study_43en:screening_case_list')
    
#     # GET request - show confirmation page
#     context = {
#         'screening': screening,
#         'title': f'Delete Screening {screening.SCRID}',
#     }

#     return render(
#         request,
#         'studies/study_43en/CRF/screening_case_confirm_delete.html',
#         context
#     )


# ============================================
# HELPER VIEWS
# ============================================

# @login_required
# def screening_statistics(request):
#     """
#     Display screening statistics dashboard
    
#     Shows:
#     - Total screenings by site
#     - Eligible vs not eligible
#     - Reasons for non-recruitment
#     - Success rate by site
#     """
#     site_id = request.session.get('selected_site_id', 'all')
    
#     # Base queryset
#     if site_id and site_id != 'all':
#         cases = ScreeningCase.site_objects.filter_by_site(site_id)
#     else:
#         cases = ScreeningCase.objects.all()
    
#     # Overall statistics
#     total_screenings = cases.count()
#     eligible = cases.filter(is_confirmed=True).count()
#     not_eligible = total_screenings - eligible
#     success_rate = (eligible / total_screenings * 100) if total_screenings > 0 else 0
    
#     # Statistics by site
#     site_stats = (
#         ScreeningCase.objects
#         .values('SITEID')
#         .annotate(
#             total=Count('SCRID'),
#             eligible=Count('SCRID', filter=Q(is_confirmed=True)),
#             not_eligible=Count('SCRID', filter=Q(is_confirmed=False))
#         )
#         .order_by('SITEID')
#     )
    
#     # Add success rate to each site
#     for site in site_stats:
#         site['success_rate'] = (
#             (site['eligible'] / site['total'] * 100) 
#             if site['total'] > 0 else 0
#         )
    
#     # Reasons for non-recruitment
#     unrecruited_reasons = (
#         cases.filter(is_confirmed=False, UNRECRUITED_REASON__isnull=False)
#         .values('UNRECRUITED_REASON')
#         .annotate(count=Count('SCRID'))
#         .order_by('-count')
#     )
    
#     # Add display text for reasons
#     reason_stats = []
#     for item in unrecruited_reasons:
#         reason_code = item['UNRECRUITED_REASON']
#         reason_text = dict(ScreeningCase.UNRECRUITED_CHOICES).get(
#             reason_code,
#             reason_code
#         )
#         reason_stats.append({
#             'code': reason_code,
#             'reason': reason_text,
#             'count': item['count'],
#             'percentage': (item['count'] / not_eligible * 100) if not_eligible > 0 else 0
#         })
    
#     context = {
#         'total_screenings': total_screenings,
#         'eligible': eligible,
#         'not_eligible': not_eligible,
#         'success_rate': f'{success_rate:.1f}',
#         'site_stats': site_stats,
#         'reason_stats': reason_stats,
#         'selected_site_id': site_id,
#         'title': 'Screening Statistics',
#     }
    
#     return render(
#         request,
#         'studies/study_43en/CRF/screening_statistics.html',
#         context
#     )


# @login_required
# def screening_export_csv(request):
#     """
#     Export screening data to CSV
    
#     Includes:
#     - All screening data
#     - Eligibility status
#     - Unrecruited reasons
#     - Entry metadata
#     """
#     import csv
#     from django.http import HttpResponse
#     from datetime import datetime
    
#     site_id = request.session.get('selected_site_id', 'all')
    
#     # Base queryset
#     if site_id and site_id != 'all':
#         cases = ScreeningCase.site_objects.filter_by_site(site_id)
#     else:
#         cases = ScreeningCase.objects.all()
    
#     cases = cases.order_by('SITEID', 'SCRID')
    
#     # Create response
#     response = HttpResponse(content_type='text/csv')
#     timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#     filename = f'screening_cases_{timestamp}.csv'
#     response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
#     # Write CSV
#     writer = csv.writer(response)
    
#     # Header row
#     writer.writerow([
#         'SCRID',
#         'SITEID',
#         'USUBJID',
#         'SUBJID',
#         'INITIAL',
#         'Screening Date',
#         'Eligible',
#         'Age ≥16',
#         'Infection Timing',
#         'KPN Isolated',
#         'KPN Stable',
#         'Consent',
#         'Unrecruited Reason',
#         'Other Reason',
#         'Entered By',
#         'Entry Time',
#         'Completed By',
#         'Completion Date',
#     ])
    
#     # Data rows
#     for case in cases:
#         reason_text = ''
#         if case.UNRECRUITED_REASON:
#             reason_text = case.get_UNRECRUITED_REASON_display()
        
#         writer.writerow([
#             case.SCRID,
#             case.SITEID,
#             case.USUBJID or '',
#             case.SUBJID or '',
#             case.INITIAL,
#             case.SCREENINGFORMDATE,
#             'Yes' if case.is_confirmed else 'No',
#             'Yes' if case.UPPER16AGE else 'No',
#             'Yes' if case.INFPRIOR2OR48HRSADMIT else 'No',
#             'Yes' if case.ISOLATEDKPNFROMINFECTIONORBLOOD else 'No',
#             'Yes' if case.KPNISOUNTREATEDSTABLE else 'No',
#             'Yes' if case.CONSENTTOSTUDY else 'No',
#             reason_text,
#             case.UNRECRUITED_REASON_OTHER or '',
#             case.USER_ENTRY or '',
#             case.ENTEREDTIME,
#             case.COMPLETEDBY or '',
#             case.COMPLETEDDATE or '',
#         ])
    
#     return response