# backends/api/studies/study_43en/views/shared/queries.py
"""
Query optimization utilities shared across all views.

Provides standardized methods for retrieving case chains with proper
site filtering and eager loading.
"""
import logging
from django.shortcuts import get_object_or_404

from backends.studies.study_43en.utils.site_utils import (
    get_site_filter_params,
    get_site_filtered_object_or_404,
)

logger = logging.getLogger(__name__)


def get_case_with_enrollment(request, model_class, enrollment_model, usubjid, 
                              select_related=None, prefetch_related=None):
    """
    Generic function to get a case with its enrollment.
    
    Args:
        request: HTTP request (for site filtering)
        model_class: The case model class (e.g., FU_CASE_28)
        enrollment_model: The enrollment model (e.g., ENR_CASE)
        usubjid: Patient/Contact USUBJID
        select_related: List of related fields to eager load
        prefetch_related: List of related sets to prefetch
    
    Returns:
        tuple: (enrollment, case or None)
    """
    site_filter, filter_type = get_site_filter_params(request)
    
    enrollment = get_site_filtered_object_or_404(
        enrollment_model,
        site_filter,
        filter_type,
        USUBJID=usubjid
    )
    
    try:
        queryset = model_class.objects.all()
        
        if select_related:
            queryset = queryset.select_related(*select_related)
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)
        
        case = queryset.get(USUBJID=enrollment)
        return enrollment, case
        
    except model_class.DoesNotExist:
        return enrollment, None


def get_patient_case_chain(request, usubjid, case_model=None, 
                           select_related=None, prefetch_related=None):
    """
    Get patient case chain: SCR -> ENR -> [target case].
    
    Args:
        request: HTTP request
        usubjid: Patient USUBJID
        case_model: Target case model (optional, e.g., FU_CASE_28)
        select_related: Fields to eager load
        prefetch_related: Related sets to prefetch
    
    Returns:
        tuple: (screening, enrollment, case or None)
    """
    from backends.studies.study_43en.models.patient import SCR_CASE, ENR_CASE
    
    site_filter, filter_type = get_site_filter_params(request)
    
    # Get screening
    screening = get_site_filtered_object_or_404(
        SCR_CASE, site_filter, filter_type, USUBJID=usubjid
    )
    
    # Get enrollment
    enrollment = get_site_filtered_object_or_404(
        ENR_CASE, site_filter, filter_type, USUBJID=screening
    )
    
    # Get target case if model provided
    if case_model is None:
        return screening, enrollment, None
    
    try:
        queryset = case_model.objects.all()
        
        if select_related:
            queryset = queryset.select_related(*select_related)
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)
        
        case = queryset.get(USUBJID=enrollment)
        return screening, enrollment, case
        
    except case_model.DoesNotExist:
        return screening, enrollment, None


def get_contact_case_chain(request, usubjid, case_model=None,
                           select_related=None, prefetch_related=None):
    """
    Get contact case chain: SCR_CONTACT -> ENR_CONTACT -> [target case].
    
    Args:
        request: HTTP request
        usubjid: Contact USUBJID
        case_model: Target case model (optional, e.g., FU_CONTACT_28)
        select_related: Fields to eager load
        prefetch_related: Related sets to prefetch
    
    Returns:
        tuple: (screening, enrollment) or (screening, enrollment, case or None)
    """
    from backends.studies.study_43en.models.contact import SCR_CONTACT, ENR_CONTACT
    
    site_filter, filter_type = get_site_filter_params(request)
    
    # Get screening
    screening = get_site_filtered_object_or_404(
        SCR_CONTACT, site_filter, filter_type, USUBJID=usubjid
    )
    
    # Get enrollment
    enrollment = get_site_filtered_object_or_404(
        ENR_CONTACT, site_filter, filter_type, USUBJID=screening
    )
    
    # Return just screening and enrollment if no case model
    if case_model is None:
        return screening, enrollment
    
    try:
        queryset = case_model.objects.all()
        
        if select_related:
            queryset = queryset.select_related(*select_related)
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)
        
        case = queryset.get(USUBJID=enrollment)
        return screening, enrollment, case
        
    except case_model.DoesNotExist:
        return screening, enrollment, None
