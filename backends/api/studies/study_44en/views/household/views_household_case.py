# backends/api/studies/study_44en/views/household/views_household_case.py

"""
Household Case Views for Study 44EN
Handles HH_CASE CRUD operations with members management
"""

import logging
from datetime import date
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

from backends.studies.study_44en.models.household import HH_CASE, HH_Member
from backends.studies.study_44en.forms.household import (
    HH_CASEForm, HH_MemberForm, HH_MemberFormSet
)
from backends.api.studies.study_44en.views.views_base import (
    get_filtered_households, get_household_with_related
)

logger = logging.getLogger(__name__)


def set_audit_metadata(instance, user):
    """Set audit fields for tracking"""
    if hasattr(instance, 'last_modified_by_id'):
        instance.last_modified_by_id = user.id
    if hasattr(instance, 'last_modified_by_username'):
        instance.last_modified_by_username = user.username


@login_required
def household_list(request):
    """
    List all households with search, filter, and pagination
    """
    from backends.api.studies.study_44en.views.views_base import household_list
    return household_list(request)


@login_required
def household_detail(request, hhid):
    """
    View household details with all members and exposure data
    """
    queryset = get_filtered_households(request.user)
    household = get_object_or_404(queryset, HHID=hhid)
    
    # Get all members
    members = HH_Member.objects.filter(HHID=household).order_by('MEMBER_NUM')
    
    # Get respondent info (based on RESPONDENT_MEMBER_NUM)
    respondent = None
    if household.RESPONDENT_MEMBER_NUM:
        respondent = members.filter(MEMBER_NUM=household.RESPONDENT_MEMBER_NUM).first()
    
    # Get exposure data
    try:
        from backends.studies.study_44en.models.household import (
            HH_Exposure, HH_WaterSource, HH_WaterTreatment, HH_Animal
        )
        exposure = HH_Exposure.objects.get(HHID=household)
        water_sources = HH_WaterSource.objects.filter(HHID=exposure)
        water_treatments = HH_WaterTreatment.objects.filter(HHID=exposure)
        animals = HH_Animal.objects.filter(HHID=exposure)
    except HH_Exposure.DoesNotExist:
        exposure = None
        water_sources = []
        water_treatments = []
        animals = []
    
    context = {
        'household': household,
        'members': members,
        'respondent': respondent,
        'total_members': members.count(),
        'exposure': exposure,
        'water_sources': water_sources,
        'water_treatments': water_treatments,
        'animals': animals,
    }
    
    return render(request, 'studies/study_44en/CRF/household/household_detail.html', context)


@login_required
def household_create(request):
    """
    Create or edit household with members (supports ?hhid= for editing)
    """
    # Check if editing existing household via ?hhid= parameter
    hhid_param = request.GET.get('hhid')
    household = None
    is_create = True
    
    if hhid_param:
        try:
            queryset = get_filtered_households(request.user)
            household = get_object_or_404(queryset, HHID=hhid_param)
            is_create = False
        except:
            household = None
            is_create = True
    
    if request.method == 'POST':
        # Debug: Log POST data
        logger.debug(f"POST data keys: {list(request.POST.keys())}")
        logger.debug(f"POST data: {dict(request.POST)}")
        
        household_form = HH_CASEForm(request.POST, instance=household)
        member_formset = HH_MemberFormSet(request.POST, prefix='members', instance=household)
        
        # Debug: Log form validation status
        logger.debug(f"Household form valid: {household_form.is_valid()}")
        logger.debug(f"Member formset valid: {member_formset.is_valid()}")
        
        if household_form.is_valid() and member_formset.is_valid():
            try:
                with transaction.atomic():
                    # Save household
                    household = household_form.save(commit=False)
                    set_audit_metadata(household, request.user)
                    household.save()
                    
                    action = "Updated" if not is_create else "Created"
                    logger.info(f"{action} household: {household.HHID}")
                    
                    # Save members
                    members = member_formset.save(commit=False)
                    for member in members:
                        member.HHID = household
                        set_audit_metadata(member, request.user)
                        member.save()
                    
                    # Handle deleted members
                    for obj in member_formset.deleted_objects:
                        obj.delete()
                    
                    logger.info(f"Saved {len(members)} members")
                    
                    messages.success(
                        request,
                        f'Household {household.HHID} {action.lower()} successfully.'
                    )
                    return redirect('study_44en:household:detail', hhid=household.HHID)
                    
            except Exception as e:
                logger.error(f"Error saving household: {e}", exc_info=True)
                messages.error(request, f'Error saving household: {str(e)}')
        else:
            # Log validation errors
            if household_form.errors:
                logger.warning(f"Household form errors: {household_form.errors}")
                for field, errors in household_form.errors.items():
                    logger.warning(f"  Field '{field}': {errors}")
            else:
                logger.debug("Household form has no field errors")
                
            if member_formset.errors:
                logger.warning(f"Member formset errors: {member_formset.errors}")
                for i, form_errors in enumerate(member_formset.errors):
                    if form_errors:
                        logger.warning(f"  Member form {i}: {form_errors}")
            else:
                logger.debug("Member formset has no errors")
            
            if member_formset.non_form_errors():
                logger.warning(f"Member formset non-form errors: {member_formset.non_form_errors()}")
            
            messages.error(request, 'Please check the form for errors.')
    
    else:
        # GET - Load form
        if household:
            household_form = HH_CASEForm(instance=household)
            member_formset = HH_MemberFormSet(prefix='members', instance=household)
        else:
            household_form = HH_CASEForm()
            member_formset = HH_MemberFormSet(prefix='members', instance=None, queryset=HH_Member.objects.none())
    
    context = {
        'household': household,
        'household_form': household_form,
        'member_formset': member_formset,
        'is_create': is_create,
    }
    
    return render(request, 'studies/study_44en/CRF/household/household_form.html', context)


@login_required
def household_edit(request, hhid):
    """
    Edit existing household and members
    """
    queryset = get_filtered_households(request.user)
    household = get_object_or_404(queryset, HHID=hhid)
    
    if request.method == 'POST':
        household_form = HH_CASEForm(request.POST, instance=household)
        member_formset = HH_MemberFormSet(
            request.POST, 
            instance=household, 
            prefix='members'
        )
        
        if household_form.is_valid() and member_formset.is_valid():
            try:
                with transaction.atomic():
                    # Update household
                    household = household_form.save(commit=False)
                    set_audit_metadata(household, request.user)
                    household.save()
                    
                    logger.info(f"Updated household: {household.HHID}")
                    
                    # Save members
                    members = member_formset.save(commit=False)
                    for member in members:
                        member.HHID = household
                        set_audit_metadata(member, request.user)
                        member.save()
                    
                    # Handle deleted members
                    for obj in member_formset.deleted_objects:
                        logger.info(f"Deleting member: {obj.MEMBERID}")
                        obj.delete()
                    
                    logger.info(f"Saved {len(members)} members")
                    
                    messages.success(
                        request,
                        f'Household {household.HHID} updated successfully.'
                    )
                    return redirect('study_44en:household:detail', hhid=household.HHID)
                    
            except Exception as e:
                logger.error(f"Error updating household: {e}", exc_info=True)
                messages.error(request, f'Error updating household: {str(e)}')
        else:
            # Log validation errors
            if household_form.errors:
                logger.warning(f"Household form errors: {household_form.errors}")
            if member_formset.errors:
                logger.warning(f"Member formset errors: {member_formset.errors}")
            
            messages.error(request, 'Please check the form for errors.')
    
    else:
        # GET - Show form with data
        household_form = HH_CASEForm(instance=household)
        member_formset = HH_MemberFormSet(instance=household, prefix='members')
    
    context = {
        'household_form': household_form,
        'member_formset': member_formset,
        'household': household,
        'is_create': False,
    }
    
    return render(request, 'studies/study_44en/CRF/household/household_form.html', context)


__all__ = [
    'household_list',
    'household_detail',
    'household_create',
    'household_edit',
]
