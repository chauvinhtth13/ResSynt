# backends/studies/study_43en/views/patient/CLI/views_clinical_lab.py
"""
Laboratory Test CRUD Views - REFACTORED with Universal Audit System

Pattern: Formset-only (no main form)
Uses InlineFormSet pattern: ENR_CASE → LaboratoryTest
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

# Import models
from backends.studies.study_43en.models.patient import (
    SCR_CASE,
    ENR_CASE,
    LaboratoryTest,
)

# Import forms
from backends.studies.study_43en.forms.patient.CLI_laboratory import LaboratoryTestFormSet

# Import utilities
from backends.studies.study_43en.utils.audit.decorators import audit_log
from backends.studies.study_43en.utils.audit.processors import process_complex_update
from backends.studies.study_43en.utils.permission_decorators import (
    require_crf_view,
    require_crf_change,
    check_instance_site_access,
)

logger = logging.getLogger(__name__)


# ==========================================
# HELPER FUNCTIONS
# ==========================================


def is_first_data_entry_for_lab_tests(forms_dict):
    """
     CÁCH 2: Detect first data entry using data_entered field
    
    Checks if ALL changed tests have data_entered=False in database.
    This is more performant and explicit than checking PERFORMED+RESULT.
    
    Args:
        forms_dict: Dictionary from processor containing formsets
        
    Returns:
        bool: True = first data entry (skip reason), False = real update (require reason)
    """
    # Get laboratory_tests formset
    formset = forms_dict.get('formsets', {}).get('laboratory_tests')
    
    if not formset:
        logger.warning("⚠️ No laboratory_tests formset found in forms_dict")
        return False
    
    logger.info(f" Checking data_entered flag for {len(formset.forms)} forms...")
    
    any_changes = False
    any_real_updates = False
    
    for form in formset.forms:
        # Skip if no changes
        if not form.has_changed():
            continue
        
        any_changes = True
        
        # Skip new instances (shouldn't happen in lab tests, but just in case)
        if not form.instance.pk:
            logger.info(f"   ℹ️ Found new instance (unexpected), considering as first entry")
            continue
        
        # Check data_entered flag from database
        try:
            # Use .only() for performance - only fetch needed fields
            original = LaboratoryTest.objects.only('id', 'TESTTYPE', 'data_entered').get(
                pk=form.instance.pk
            )
            
            if original.data_entered:
                # Already has data → this is a REAL UPDATE
                logger.info(f"    Real update detected for {original.TESTTYPE}: "
                           f"data_entered=True")
                any_real_updates = True
                break  # Found one real update, that's enough
            else:
                # data_entered=False → first time entering data
                logger.info(f"    First entry for {original.TESTTYPE}: "
                           f"data_entered=False")
                
        except LaboratoryTest.DoesNotExist:
            logger.warning(f"   ⚠️ Instance pk={form.instance.pk} not found in DB")
            # Treat as first entry if can't find original
            continue
    
    if not any_changes:
        logger.info("   ℹ️ No changes detected")
        return False  # No changes = no need to skip
    
    if any_real_updates:
        logger.info("    RESULT: Real update detected → require change reason")
        return False  # Real update = require reason
    else:
        logger.info("    RESULT: First data entry → skip change reason")
        return True  # All changes are first entry = skip reason


def get_enrollment_with_tests(usubjid, lab_type='1'):
    """Get enrollment case with laboratory tests"""
    screening_case = get_object_or_404(SCR_CASE, USUBJID=usubjid)
    enrollment_case = get_object_or_404(ENR_CASE, USUBJID=screening_case)
    
    has_tests = LaboratoryTest.objects.filter(
        USUBJID=enrollment_case,
        LAB_TYPE=lab_type
    ).exists()
    
    return screening_case, enrollment_case, has_tests


def get_tests_by_lab_type(enrollment_case):
    """Get all tests grouped by LAB_TYPE"""
    tests_by_type = {}
    
    for lab_type in ['1', '2', '3']:
        tests = LaboratoryTest.objects.filter(
            USUBJID=enrollment_case,
            LAB_TYPE=lab_type
        ).select_related('USUBJID')
        
        tests_by_type[lab_type] = list(tests)
    
    return tests_by_type


def build_category_test_map():
    """Build mapping of category → test codes"""
    all_test_types = LaboratoryTest.TestTypeChoices.choices
    category_test_map = {}
    
    for test_code, test_label in all_test_types:
        temp_test = LaboratoryTest(TESTTYPE=test_code)
        category = temp_test._get_category_from_test_type()
        
        if category not in category_test_map:
            category_test_map[category] = []
        category_test_map[category].append(test_code)
    
    return category_test_map


# ==========================================
# LABORATORY LIST VIEW
# ==========================================

@login_required
@require_crf_view('laboratorytest', redirect_to='study_43en:patient_list')
def laboratory_test_list(request, usubjid):
    """
    Laboratory tests list/overview - shows all 3 timepoints
    """
    logger.info(f"=== LABORATORY TEST LIST ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    screening_case = get_object_or_404(SCR_CASE, USUBJID=usubjid)
    enrollment_case = get_object_or_404(ENR_CASE, USUBJID=screening_case)
    
    site_check = check_instance_site_access(
        request,
        enrollment_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    tests_by_lab_type = get_tests_by_lab_type(enrollment_case)
    lab_types = LaboratoryTest.LabTypeChoices.choices
    
    context = {
        'usubjid': usubjid,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'tests_by_lab_type': tests_by_lab_type,
        'lab_types': lab_types,
        'selected_site_id': screening_case.SITEID,
    }
    
    return render(request, 'studies/study_43en/CRF/patient/laboratory_test_list.html', context)


# ==========================================
# LABORATORY CREATE VIEW
# ==========================================

@login_required
@require_crf_change('laboratorytest', redirect_to='study_43en:patient_list')
@audit_log(model_name='LABORATORYTEST', get_patient_id_from='usubjid')
def laboratory_test_create(request, usubjid, lab_type):
    """
    Initialize laboratory tests for a specific timepoint (NO AUDIT)
    Auto-creates all standard tests and redirects to bulk update
    """
    logger.info(f"=== LABORATORY CREATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, LAB_TYPE: {lab_type}")
    
    if lab_type not in ['1', '2', '3']:
        messages.error(request, f'Lab type không hợp lệ: {lab_type}')
        return redirect('study_43en:laboratory_test_list', usubjid=usubjid)
    
    screening_case, enrollment_case, has_tests = get_enrollment_with_tests(usubjid, lab_type)
    
    site_check = check_instance_site_access(
        request,
        enrollment_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    if has_tests:
        messages.info(
            request, 
            f'Xét nghiệm lần {lab_type} đã tồn tại. Chuyển sang cập nhật.'
        )
        return redirect('study_43en:laboratory_test_bulk_update', 
                       usubjid=usubjid, lab_type=lab_type)
    
    # Initialize all standard tests
    count = 0
    for test_type_value, test_type_label in LaboratoryTest.TestTypeChoices.choices:
        LaboratoryTest.objects.create(
            USUBJID=enrollment_case,
            LAB_TYPE=lab_type,
            TESTTYPE=test_type_value,
            PERFORMED=False,
        )
        count += 1
    
    messages.success(
        request,
        f' Đã khởi tạo {count} xét nghiệm chuẩn cho lần {lab_type}'
    )
    logger.info(f"Initialized {count} tests for {usubjid} LAB_TYPE={lab_type}")
    
    return redirect('study_43en:laboratory_test_bulk_update', 
                   usubjid=usubjid, lab_type=lab_type)


# ==========================================
# LABORATORY BULK UPDATE VIEW
# ==========================================

@login_required
@require_crf_change('laboratorytest', redirect_to='study_43en:patient_list')
@audit_log(model_name='LABORATORYTEST', get_patient_id_from='usubjid')
def laboratory_test_bulk_update(request, usubjid, lab_type):
    """
    Bulk update laboratory tests WITH DATA_ENTERED TRACKING
    
     Uses data_entered field to distinguish:
    - First entry (data_entered=False): No change reason required
    - Real update (data_entered=True): Change reason required
    """
    logger.info(f"=== LABORATORY BULK UPDATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, LAB_TYPE: {lab_type}, Method: {request.method}")
    
    if lab_type not in ['1', '2', '3']:
        messages.error(request, f'Lab type không hợp lệ: {lab_type}')
        return redirect('study_43en:laboratory_test_list', usubjid=usubjid)
    
    screening_case, enrollment_case, has_tests = get_enrollment_with_tests(usubjid, lab_type)
    
    site_check = check_instance_site_access(
        request,
        enrollment_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    # Auto-initialize missing tests instead of redirecting
    if not has_tests:
        logger.warning(f"No tests found for {usubjid} LAB_TYPE={lab_type}. Initializing...")
        count = 0
        for test_type_value, test_type_label in LaboratoryTest.TestTypeChoices.choices:
            LaboratoryTest.objects.create(
                USUBJID=enrollment_case,
                LAB_TYPE=lab_type,
                TESTTYPE=test_type_value,
                PERFORMED=False,
                data_entered=False,  #  Explicitly set to False
            )
            count += 1
        
        messages.info(
            request,
            f'ℹ️ Đã tự động khởi tạo {count} xét nghiệm cho lần {lab_type}'
        )
        logger.info(f"Auto-initialized {count} tests for {usubjid} LAB_TYPE={lab_type}")
    
    # Ensure ALL test types exist (fill in gaps)
    existing_test_types = set(
        LaboratoryTest.objects.filter(
            USUBJID=enrollment_case,
            LAB_TYPE=lab_type
        ).values_list('TESTTYPE', flat=True)
    )
    
    missing_count = 0
    for test_type_value, test_type_label in LaboratoryTest.TestTypeChoices.choices:
        if test_type_value not in existing_test_types:
            LaboratoryTest.objects.create(
                USUBJID=enrollment_case,
                LAB_TYPE=lab_type,
                TESTTYPE=test_type_value,
                PERFORMED=False,
                data_entered=False,  #  Explicitly set to False
            )
            missing_count += 1
    
    if missing_count > 0:
        logger.info(f"Added {missing_count} missing tests for {usubjid} LAB_TYPE={lab_type}")
    
    # GET - Show form
    if request.method == 'GET':
        formset = LaboratoryTestFormSet(
            queryset=LaboratoryTest.objects.filter(
                USUBJID=enrollment_case,
                LAB_TYPE=lab_type
            ).order_by('CATEGORY', 'TESTTYPE'),
            prefix='labtest'
        )
        
        all_categories = LaboratoryTest.CategoryChoices.choices
        all_test_types = LaboratoryTest.TestTypeChoices.choices
        category_test_map = build_category_test_map()
        lab_type_display = dict(LaboratoryTest.LabTypeChoices.choices).get(
            lab_type, f"Test {lab_type}"
        )
        
        logger.info(f"📋 Formset has {len(formset.forms)} forms")
        logger.info(f"📊 Category map: {category_test_map}")
        
        context = {
            'usubjid': usubjid,
            'screening_case': screening_case,
            'enrollment_case': enrollment_case,
            'formset': formset,
            'lab_type': lab_type,
            'lab_type_display': lab_type_display,
            'all_categories': all_categories,
            'all_test_types': all_test_types,
            'category_test_map': category_test_map,
            'is_update': True,
            'is_readonly': False,
            'selected_site_id': screening_case.SITEID,
        }
        
        return render(
            request, 
            'studies/study_43en/CRF/patient/laboratory_test_bulk_update.html', 
            context
        )
    
    # 📝 POST - USE SMART AUDIT SYSTEM WITH DATA_ENTERED
    logger.info("🧠 Using Smart Audit System with data_entered field tracking")
    
    # Dummy form for formset-only updates
    class DummyForm:
        """Dummy form for formset-only updates - prevents main form change detection"""
        def __init__(self, *args, **kwargs):
            self.instance = enrollment_case
            self.fields = {}
            self.cleaned_data = {}
            self.errors = {}
        
        def is_valid(self):
            return True
        
        def save(self, commit=True):
            return enrollment_case
    
    # Configure forms
    forms_config = {
        'main': {
            'class': DummyForm,
            'instance': enrollment_case,
        },
        'formsets': {
            'laboratory_tests': {
                'class': LaboratoryTestFormSet,
                'queryset': LaboratoryTest.objects.filter(
                    USUBJID=enrollment_case,
                    LAB_TYPE=lab_type
                ).order_by('CATEGORY', 'TESTTYPE'),
                'prefix': 'labtest',
                'related_name': 'laboratorytest_set',
            }
        }
    }
    
    #  ENHANCED SAVE CALLBACK with data_entered tracking
    def save_callback(request, forms_dict):
        """
        Save laboratory tests with data_entered tracking
        
         Auto-sets data_entered=True when test gets real data
        """
        formset = forms_dict['formsets']['laboratory_tests']
        
        try:
            instances = formset.save(commit=False)
            
            first_entry_count = 0
            update_count = 0
            
            for test in instances:
                if not test.USUBJID_id:
                    test.USUBJID = enrollment_case
                
                test.last_modified_by_id = request.user.id
                test.last_modified_by_username = request.user.username
                
                #  Track entry type BEFORE save
                was_first_entry = not test.data_entered
                
                #  Auto-set data_entered if test now has real data
                # Model's save() will also handle this, but we track it here for logging
                if test.PERFORMED and test.RESULT and test.RESULT.strip():
                    if was_first_entry:
                        # First time entering data
                        test.data_entered = True
                        first_entry_count += 1
                        logger.info(f"    First entry: {test.TESTTYPE}")
                    else:
                        # Updating existing data
                        update_count += 1
                        test.version += 1  # Only increment version for real updates
                        logger.info(f"    Update: {test.TESTTYPE}")
                else:
                    # Not performed or no result
                    if test.data_entered:
                        # Had data before, now clearing it (rare case)
                        update_count += 1
                        test.version += 1
                
                # Clear fields if not performed
                if not test.PERFORMED:
                    test.PERFORMEDDATE = None
                    test.RESULT = None
                
                # Auto-set category
                if not test.CATEGORY:
                    test.CATEGORY = test._get_category_from_test_type()
                
                test.save()  # Model's save() will also set data_entered=True if conditions met
            
            # Show appropriate message
            messages_list = []
            if first_entry_count > 0:
                messages_list.append(f' Đã nhập {first_entry_count} xét nghiệm mới')
            if update_count > 0:
                messages_list.append(f' Đã cập nhật {update_count} xét nghiệm')
            
            if messages_list:
                messages.success(request, ' | '.join(messages_list))
            
            logger.info(f"💾 Saved: {first_entry_count} first entries, {update_count} updates")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving laboratory tests: {e}", exc_info=True)
            messages.error(request, f'Lỗi khi lưu: {str(e)}')
            return False
    
    #  Use Universal Audit System with skip_change_reason
    return process_complex_update(
        request=request,
        main_instance=enrollment_case,
        forms_config=forms_config,
        save_callback=save_callback,
        template_name='studies/study_43en/CRF/patient/laboratory_test_bulk_update.html',
        redirect_url=reverse('study_43en:laboratory_test_list', kwargs={'usubjid': usubjid}),
        skip_change_reason=is_first_data_entry_for_lab_tests,  #  KEY: Skip reason for first entry
        extra_context={
            'usubjid': usubjid,
            'screening_case': screening_case,
            'enrollment_case': enrollment_case,
            'lab_type': lab_type,
            'lab_type_display': dict(LaboratoryTest.LabTypeChoices.choices).get(lab_type, lab_type),
            'all_categories': LaboratoryTest.CategoryChoices.choices,
            'all_test_types': LaboratoryTest.TestTypeChoices.choices,
            'category_test_map': build_category_test_map(),
            'selected_site_id': screening_case.SITEID,
        }
    )

# ==========================================
# LABORATORY VIEW (READ-ONLY)
# ==========================================

@login_required
@require_crf_view('laboratorytest', redirect_to='study_43en:patient_list')
@audit_log(model_name='LABORATORYTEST', get_patient_id_from='usubjid')
def laboratory_test_view(request, usubjid, lab_type):
    """
    View laboratory tests (READ-ONLY) - Uses same template as bulk_update
    """
    logger.info(f"=== LABORATORY VIEW (READ-ONLY) ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, LAB_TYPE: {lab_type}")
    
    if lab_type not in ['1', '2', '3']:
        messages.error(request, f'Lab type không hợp lệ: {lab_type}')
        return redirect('study_43en:laboratory_test_list', usubjid=usubjid)
    
    screening_case, enrollment_case, has_tests = get_enrollment_with_tests(usubjid, lab_type)
    
    site_check = check_instance_site_access(
        request,
        enrollment_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    if not has_tests:
        messages.warning(
            request, 
            f'⚠️ Chưa có xét nghiệm nào cho lần {lab_type}'
        )
        return redirect('study_43en:laboratory_test_list', usubjid=usubjid)
    
    # Create formset (will be disabled in template)
    formset = LaboratoryTestFormSet(
        queryset=LaboratoryTest.objects.filter(
            USUBJID=enrollment_case,
            LAB_TYPE=lab_type
        ).order_by('CATEGORY', 'TESTTYPE'),
        prefix='labtest'
    )
    
    all_categories = LaboratoryTest.CategoryChoices.choices
    all_test_types = LaboratoryTest.TestTypeChoices.choices
    category_test_map = build_category_test_map()
    lab_type_display = dict(LaboratoryTest.LabTypeChoices.choices).get(
        lab_type, f"Test {lab_type}"
    )
    
    context = {
        'usubjid': usubjid,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'formset': formset,
        'lab_type': lab_type,
        'lab_type_display': lab_type_display,
        'all_categories': all_categories,
        'all_test_types': all_test_types,
        'category_test_map': category_test_map,
        'is_update': False,  # ← Not update mode
        'is_readonly': True,  # ← KEY FLAG: Make all fields readonly
        'selected_site_id': screening_case.SITEID,
    }
    
    return render(
        request, 
        'studies/study_43en/CRF/patient/laboratory_test_bulk_update.html',  # ← Same template
        context
    )