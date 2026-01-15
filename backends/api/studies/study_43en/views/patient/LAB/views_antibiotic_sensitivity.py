# backends/studies/study_43en/views/patient/LAB/views_antibiotic_sensitivity.py
"""
Antibiotic Sensitivity Test Views - WITH SEMANTIC IDs
Features:
- Auto-generation of WHONET_CODE and AST_ID
- Only testable on KPN+ cultures
- Inline formset support
- Resistance profile analysis
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse

# Import models
from backends.studies.study_43en.models.patient import (
    SCR_CASE,
    ENR_CASE,
    LAB_Microbiology,
    AntibioticSensitivity,
)
from backends.studies.study_43en.models import AuditLog, AuditLogDetail

# Import forms
from backends.studies.study_43en.forms.patient.LAB_antibiotic_sensitivity import (
    AntibioticSensitivityForm,
    AntibioticSensitivityInlineFormSet,
    AntibioticSensitivityFilterForm,
    get_antibiotic_resistance_profile,
    get_resistance_statistics,
)

# Import utilities
from backends.audit_logs.utils.permission_decorators import (
    require_crf_view,
    require_crf_add,
    require_crf_change,
    check_instance_site_access,
)
from backends.audit_logs.utils.decorators import audit_log
from backends.audit_logs.utils.processors import process_crf_update

logger = logging.getLogger(__name__)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_culture_with_tests(request, usubjid, culture_id):
    """
    Get culture with antibiotic sensitivity tests (WITH SITE FILTERING)
    
    Args:
        request: HttpRequest (for site filtering)
        usubjid: Patient USUBJID
        culture_id: Culture ID
        
    Returns:
        tuple: (screening_case, enrollment_case, culture, tests)
        
    Raises:
        Http404: If not found OR user lacks site access
    """
    from backends.studies.study_43en.utils.site_utils import (
        get_site_filter_params,
        get_site_filtered_object_or_404
    )
    
    # Use study database
    db_alias = 'db_study_43en'
    
    # Get site filtering params
    site_filter, filter_type = get_site_filter_params(request)
    
    # Get objects with site filtering
    screening_case = get_site_filtered_object_or_404(
        SCR_CASE, site_filter, filter_type, USUBJID=usubjid
    )
    enrollment_case = get_site_filtered_object_or_404(
        ENR_CASE, site_filter, filter_type, USUBJID=screening_case
    )
    
    culture = get_object_or_404(
        LAB_Microbiology.objects.using(db_alias),
        id=culture_id,
        USUBJID=enrollment_case
    )
    
    tests = AntibioticSensitivity.objects.using(db_alias).filter(
        LAB_CULTURE_ID=culture
    ).select_related('LAB_CULTURE_ID').order_by('TIER', 'WHONET_CODE')
    
    return screening_case, enrollment_case, culture, tests


# ==========================================
# LIST VIEW (for specific culture)
# ==========================================

# backends/studies/study_43en/views/patient/LAB/views_antibiotic_sensitivity.py

@login_required
@require_crf_view('antibioticsensitivity', redirect_to='study_43en:patient_list')
@audit_log(
    model_name='ANTIBIOTIC_SENSITIVITY',
    get_patient_id_from='usubjid',
    patient_model=SCR_CASE,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def antibiotic_list(request, usubjid, culture_id):
    """
    Display antibiotic sensitivity tests for a specific culture
    WITH UNIVERSAL AUDIT SYSTEM (Custom bulk edit pattern)
    
     FIX: Skip audit for first-time data entry (similar to Laboratory)
    """
    logger.info(f"=== ANTIBIOTIC SENSITIVITY LIST ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Culture: {culture_id}")
    
    # Get culture and tests (WITH SITE FILTERING)
    screening_case, enrollment_case, culture, tests = get_culture_with_tests(
        request, usubjid, culture_id
    )
    
    logger.info(f" Tests found: {tests.count()}")
    logger.info(f" Culture ID: {culture.id}, LAB_CULTURE_ID: {culture.LAB_CULTURE_ID}")
    logger.info(f" Is testable: {culture.is_testable_for_antibiotics}")
    
    # Check if culture is testable
    if not culture.is_testable_for_antibiotics:
        messages.warning(
            request,
            f'⚠ Culture {culture.LAB_CULTURE_ID} is not eligible for antibiotic testing.'
        )
        return redirect('study_43en:microbiology_list', usubjid=usubjid)
    
    #  If no tests exist, trigger auto-creation
    if not tests.exists():
        logger.info(f"No tests found, triggering auto-creation for {culture.LAB_CULTURE_ID}")
        from backends.studies.study_43en.models.patient.LAB_Case import auto_create_antibiotic_tests
        db_alias = 'db_study_43en'
        
        auto_create_antibiotic_tests(sender=LAB_Microbiology, instance=culture, created=False, using=db_alias)
        
        # Refresh tests with correct database
        tests = AntibioticSensitivity.objects.using(db_alias).filter(
            LAB_CULTURE_ID=culture
        ).select_related('LAB_CULTURE_ID').order_by('TIER', 'WHONET_CODE')
    
    #  HANDLE BULK UPDATE WITH AUDIT SYSTEM
    if request.method == 'POST':
        logger.info("🔵 Processing bulk antibiotic test update WITH AUDIT")
        
        from backends.audit_logs.utils.detector import ChangeDetector
        from backends.audit_logs.utils.validator import ReasonValidator
        
        detector = ChangeDetector()
        validator = ReasonValidator()
        
        db_alias = 'db_study_43en'
        
        # STEP 1: Capture old data AND detect changes
        all_changes = []
        changes_by_test = {}  # {test_id: [changes]}

        logger.info(f"🔍 Processing POST data...")
        logger.info(f"🔍 Total POST keys: {len(request.POST.keys())}")

        # DEBUG: Log first 20 keys
        post_keys = [k for k in request.POST.keys() if k.startswith('sensitivity_')]
        logger.info(f"🔍 Sensitivity keys found: {len(post_keys)}")
        logger.info(f"🔍 First 10 keys: {post_keys[:10]}")

        for key in request.POST:
            if key.startswith('sensitivity_'):
                identifier = key.replace('sensitivity_', '')
                
                logger.info(f"━━━ Processing: {key} (identifier: {identifier}) ━━━")
                
                # Get sensitivity value
                sensitivity = request.POST.get(f'sensitivity_{identifier}')
                
                logger.info(f"  → Sensitivity value: '{sensitivity}' (type: {type(sensitivity).__name__})")
                
                # FIX 1: Only skip if form field doesn't exist at all (None)
                # Don't skip empty string or 'ND' - these are valid values
                if sensitivity is None:
                    logger.info(f"  ⏭️  SKIP: Form field doesn't exist (None)")
                    continue
                
                # FIX 2: Allow empty string but log it
                if sensitivity == '':
                    logger.info(f"  ⚠️  WARNING: Empty string value (will be treated as no change)")
                    # Don't skip - let detector handle it
                
                # Process existing tests (numeric IDs)
                if identifier.isdigit():
                    test_id = int(identifier)
                    
                    try:
                        test = AntibioticSensitivity.objects.using(db_alias).get(
                            id=test_id,
                            LAB_CULTURE_ID=culture
                        )
                        
                        logger.info(f"  Found test ID {test_id}: {test.AST_ID}")
                        logger.info(f"     Old sensitivity: '{test.SENSITIVITY_LEVEL}'")
                        logger.info(f"     Old MIC: '{test.MIC}'")
                        logger.info(f"     Old IZDIAM: '{test.IZDIAM}'")
                        logger.info(f"     Old NOTES: '{test.NOTES}'")
                        
                        # FIX 3: Check first-time fill (but DON'T skip if changing TO ND)
                        is_first_time_fill = (
                            test.SENSITIVITY_LEVEL == 'ND' and
                            not test.MIC and
                            not test.IZDIAM and
                            not test.NOTES
                        )
                        
                        # IMPORTANT: If changing FROM filled value TO ND, NOT first-fill
                        is_reverting_to_nd = (
                            test.SENSITIVITY_LEVEL != 'ND' and  # Was filled
                            sensitivity == 'ND'  # Now reverting to ND
                        )
                        
                        if is_reverting_to_nd:
                            is_first_time_fill = False  # Force to detect as change
                        
                        if is_first_time_fill and sensitivity != 'ND':
                            logger.info(f"  FIRST-TIME FILL: {test.AST_ID} - Skip audit, just UPDATE")
                            
                            # Build new data from POST
                            mic_raw = request.POST.get(f'mic_{identifier}', '')
                            mic_value = mic_raw.strip() or None
                            
                            new_data = {
                                'SENSITIVITY_LEVEL': sensitivity,
                                'MIC': mic_value,
                                'IZDIAM': request.POST.get(f'izdiam_{identifier}') or None,
                                'NOTES': request.POST.get(f'notes_{identifier}', '').strip() or None,
                            }
                            
                            # Convert IZDIAM to float
                            if new_data['IZDIAM']:
                                try:
                                    new_data['IZDIAM'] = float(new_data['IZDIAM'])
                                except ValueError:
                                    new_data['IZDIAM'] = None
                            
                            # Store for DIRECT UPDATE (no audit)
                            changes_by_test[test_id] = {
                                'test': test,
                                'new_data': new_data,
                                'changes': [],  # Empty = no audit needed
                                'is_first_fill': True,
                            }
                            
                            logger.info(f"     → Queued for FIRST-FILL (no audit)")
                            continue  # Skip change detection
                        
                        # Normal update OR revert to ND → detect changes
                        logger.info(f"  🔄 NORMAL UPDATE/REVERT: {test.AST_ID} - Detect changes + audit")
                        logger.info(f"  NORMAL UPDATE/REVERT: {test.AST_ID} - Detect changes + audit")
                        
                        # Capture old data
                        old_data = detector.extract_old_data(test)
                        
                        logger.info(f"     Old data extracted: {old_data}")
                        
                        # Build new data from POST
                        mic_raw = request.POST.get(f'mic_{identifier}', '')
                        mic_value = mic_raw.strip() or None
                        
                        # FIX 4: Get IZDIAM and NOTES properly
                        izdiam_raw = request.POST.get(f'izdiam_{identifier}', '')
                        izdiam_value = izdiam_raw.strip() if izdiam_raw else None
                        
                        notes_raw = request.POST.get(f'notes_{identifier}', '')
                        notes_value = notes_raw.strip() if notes_raw else None
                        
                        new_data = {
                            'SENSITIVITY_LEVEL': sensitivity,  # Can be 'ND'
                            'MIC': mic_value,
                            'IZDIAM': izdiam_value,
                            'NOTES': notes_value,
                        }
                        
                        logger.info(f"     New data built: {new_data}")
                        logger.info(f"     MIC raw from POST: '{mic_raw}' → processed: {mic_value}")
                        logger.info(f"     IZDIAM raw: '{izdiam_raw}' → processed: {izdiam_value}")
                        logger.info(f"     NOTES raw: '{notes_raw}' → processed: {notes_value}")
                        
                        # Convert IZDIAM to float
                        if new_data['IZDIAM']:
                            try:
                                new_data['IZDIAM'] = float(new_data['IZDIAM'])
                                logger.info(f"     IZDIAM converted to float: {new_data['IZDIAM']}")
                            except ValueError:
                                logger.warning(f"     ⚠️  IZDIAM conversion failed: '{new_data['IZDIAM']}'")
                                new_data['IZDIAM'] = None
                        
                        # Detect changes for this test
                        test_changes = detector.detect_changes(old_data, new_data)
                        
                        logger.info(f"     🔍 Changes detected: {len(test_changes)}")
                        
                        if test_changes:
                            # Log each change
                            for idx, change in enumerate(test_changes, 1):
                                logger.info(f"       Change {idx}: {change['field']} | {change['old_value']} → {change['new_value']}")
                            
                            # Enhanced display with AST_ID
                            antibiotic_name = test.get_antibiotic_display_name()
                            ast_id = test.AST_ID  # e.g., "003-A-001-C1-AMP"
                            
                            # Field display mapping
                            field_display = {
                                'SENSITIVITY_LEVEL': 'Sensitivity',
                                'MIC': 'MIC',
                                'IZDIAM': 'Zone Diameter',
                                'NOTES': 'Notes'
                            }
                            
                            # FIX 5: Process EACH change separately
                            for change in test_changes:
                                # Technical field for POST (keep as is for hidden form)
                                change['field'] = f"test_{test_id}_{change['field']}"
                                
                                # Display label: AST_ID - Field Name
                                original_field = change['field'].split('_')[-1]  # Get last part (e.g., "MIC")
                                field_label = field_display.get(original_field, original_field)
                                change['field_label'] = f"{ast_id} - {field_label}"
                                
                                # Additional metadata for audit log
                                change['antibiotic'] = antibiotic_name
                                change['ast_id'] = ast_id
                            
                            # Store changes for this test
                            changes_by_test[test_id] = {
                                'test': test,
                                'new_data': new_data,
                                'changes': test_changes,
                                'is_first_fill': False,
                            }
                            
                            # FIX 6: Add ALL changes from this test
                            all_changes.extend(test_changes)
                            
                            logger.info(f"     Test {test.AST_ID} ({antibiotic_name}): {len(test_changes)} changes added")
                            logger.info(f"     Total changes so far: {len(all_changes)}")
                        else:
                            logger.info(f"     ⏭️  No changes detected for {test.AST_ID}")
                    
                    except AntibioticSensitivity.DoesNotExist:
                        logger.warning(f"   Test {test_id} not found")
                        continue
                    except Exception as e:
                        logger.error(f"   Error processing test {test_id}: {e}", exc_info=True)
                        continue
                
                # Process NEW tests (identifier format: new_AntibioticName_Tier)
                elif identifier.startswith('new_'):
                    # FIX 7: Only skip NEW tests if ND (not filled)
                    if sensitivity == 'ND':
                        logger.info(f"  ⏭️  SKIP new test {identifier}: sensitivity is ND (not filled)")
                        continue
                    
                    # Parse antibiotic name and tier from identifier
                    # Format: new_Ampicillin_Tier1 → antibiotic=Ampicillin, tier=Tier1
                    parts = identifier.replace('new_', '').rsplit('_', 1)
                    if len(parts) != 2:
                        logger.warning(f"   Invalid new test identifier: {identifier}")
                        continue
                    
                    antibiotic_name = parts[0]  # e.g., "Ampicillin"
                    tier = parts[1]  # e.g., "Tier1"
                    
                    # Get MIC, IZDIAM, NOTES from POST
                    mic_value = request.POST.get(f'mic_{identifier}', '').strip() or None
                    izdiam_value = request.POST.get(f'izdiam_{identifier}', '').strip() or None
                    notes_value = request.POST.get(f'notes_{identifier}', '').strip() or None
                    
                    logger.info(f"  Creating new test: {antibiotic_name} ({tier})")
                    logger.info(f"     Sensitivity: {sensitivity}, MIC: {mic_value}")
                    
                    # Store for creation in STEP 5/6
                    new_test_key = f"new_{antibiotic_name}_{tier}"
                    changes_by_test[new_test_key] = {
                        'test': None,  # No existing test
                        'new_data': {
                            'ANTIBIOTIC_NAME': antibiotic_name,
                            'TIER': tier,
                            'SENSITIVITY_LEVEL': sensitivity,
                            'MIC': mic_value,
                            'IZDIAM': float(izdiam_value) if izdiam_value else None,
                            'NOTES': notes_value,
                        },
                        'changes': [],  # Empty = no audit needed (new test creation)
                        'is_new': True,
                    }
                    logger.info(f"     → Queued for creation (no audit for new)")

        # FINAL SUMMARY LOG
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"📊 PROCESSING SUMMARY:")
        logger.info(f"   Total POST sensitivity keys: {len(post_keys)}")
        logger.info(f"   Tests processed: {len(changes_by_test)}")
        logger.info(f"   Total changes detected: {len(all_changes)}")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # DEBUG: Log all changes
        if all_changes:
            logger.info(f"📋 ALL CHANGES DETAIL:")
            for idx, change in enumerate(all_changes, 1):
                logger.info(
                    f"   {idx}. {change.get('field_label', change['field'])}: "
                    f"{change['old_display']} → {change['new_display']}"
                )
        else:
            logger.info(f"  No changes detected")

        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # STEP 2: No changes → redirect
        if not changes_by_test:
            messages.info(request, ' No changes were made.')
            return redirect('study_43en:antibiotic_list', usubjid=usubjid, culture_id=culture_id)
        
        #  Check if ALL changes are first-time fills or new tests
        has_real_changes = any(
            data.get('changes') and len(data['changes']) > 0
            for data in changes_by_test.values()
        )
        
        if not has_real_changes:
            logger.info(" ALL CHANGES ARE FIRST-TIME FILLS - Save without audit")
            
            # STEP 6: Save all changes WITHOUT audit
            updated_count = 0
            created_count = 0
            errors = []
            
            with transaction.atomic(using=db_alias):
                # Process all tests (both updates and new creations)
                for test_key, data in changes_by_test.items():
                    try:
                        test = data['test']
                        new_data = data['new_data']
                        is_new = data.get('is_new', False)
                        is_first_fill = data.get('is_first_fill', False)
                        
                        if is_new:
                            # Create new test
                            test = AntibioticSensitivity.objects.using(db_alias).create(
                                LAB_CULTURE_ID=culture,
                                ANTIBIOTIC_NAME=new_data['ANTIBIOTIC_NAME'],
                                TIER=new_data['TIER'],
                                SENSITIVITY_LEVEL=new_data['SENSITIVITY_LEVEL'],
                                MIC=new_data.get('MIC'),
                                IZDIAM=new_data.get('IZDIAM'),
                                NOTES=new_data.get('NOTES'),
                                INTERPRETATION_STANDARD='CLSI',
                                last_modified_by_id=request.user.id,
                                last_modified_by_username=request.user.username,
                            )
                            created_count += 1
                            logger.info(f" Created {test.AST_ID}")
                        else:
                            # Update existing test (first-time fill)
                            for field, value in new_data.items():
                                setattr(test, field, value)
                            
                            test.last_modified_by_id = request.user.id
                            test.last_modified_by_username = request.user.username
                            test.save(using=db_alias)
                            
                            updated_count += 1
                            logger.info(f" Updated (first-fill) {test.AST_ID}")
                    
                    except Exception as e:
                        logger.error(f" Error processing test {test_key}: {e}", exc_info=True)
                        errors.append(f"Test {test_key}: {str(e)}")
                
                # Check for errors
                if errors:
                    messages.warning(request, f"⚠ Some tests had errors: {'; '.join(errors)}")
            
            # Success message
            messages.success(
                request,
                f' Saved {updated_count} first-time fills, created {created_count} new tests!'
            )
            
            return redirect('study_43en:antibiotic_list', usubjid=usubjid, culture_id=culture_id)
        
        # STEP 3: Has real changes → Collect and validate reasons
        reasons_data = {}
        for change in all_changes:
            field_name = change['field']
            reason_key = f'reason_{field_name}'
            reason = request.POST.get(reason_key, '').strip()
            if reason:
                reasons_data[field_name] = reason
        
        required_fields = [c['field'] for c in all_changes]
        validation_result = validator.validate_reasons(reasons_data, required_fields)
        
        # STEP 4: If reasons missing → show modal
        if not validation_result['valid']:
            messages.warning(request, '⚠ Vui lòng nhập lý do thay đổi cho tất cả các trường.')
            
            # Get resistance profile for re-render
            profile = get_antibiotic_resistance_profile(culture)
            has_change_permission = request.user.has_perm('study_43en.change_antibioticsensitivity')
            
            context = {
                'usubjid': usubjid,
                'screening_case': screening_case,
                'enrollment_case': enrollment_case,
                'culture': culture,
                'tests': tests,
                'profile': profile,
                'has_tests': tests.exists(),
                'has_change_permission': has_change_permission,
                'selected_site_id': screening_case.SITEID,
                #  Add audit modal data
                'detected_changes': all_changes,
                'show_reason_form': True,
                'submitted_reasons': reasons_data,
                'edit_post_data': dict(request.POST.items()),  # Pass POST data for re-submit
            }
            
            return render(request, 'studies/study_43en/patient/form/antibiotic_sensitivity_list.html', context)
        
        # STEP 5: Reasons valid → save with audit
        sanitized_reasons = validation_result.get('sanitized_reasons', reasons_data)
        
        # Show security warnings
        if validation_result.get('warnings'):
            for warning in validation_result['warnings']:
                messages.warning(request, warning)
        
        # Set audit_data for decorator
        #  Use field_label for readable audit log
        combined_reason = "\n".join([
            f"{change.get('field_label', change['field'])}: {sanitized_reasons.get(change['field'], 'N/A')}"
            for change in all_changes
        ])
        
        request.audit_data = {
            'patient_id': enrollment_case.USUBJID.USUBJID,
            'site_id': enrollment_case.SITEID,
            'reason': combined_reason,
            'changes': all_changes,
            'reasons_json': sanitized_reasons,
        }
        
        # STEP 6: Save all changes (mix of first-fills and real updates)
        updated_count = 0
        created_count = 0
        first_fill_count = 0
        errors = []
        
        with transaction.atomic(using=db_alias):
            # Process all tests
            for test_key, data in changes_by_test.items():
                try:
                    test = data['test']
                    new_data = data['new_data']
                    is_new = data.get('is_new', False)
                    is_first_fill = data.get('is_first_fill', False)
                    
                    if is_new:
                        # Create new test
                        test = AntibioticSensitivity.objects.using(db_alias).create(
                            LAB_CULTURE_ID=culture,
                            ANTIBIOTIC_NAME=new_data['ANTIBIOTIC_NAME'],
                            TIER=new_data['TIER'],
                            SENSITIVITY_LEVEL=new_data['SENSITIVITY_LEVEL'],
                            MIC=new_data.get('MIC'),
                            IZDIAM=new_data.get('IZDIAM'),
                            NOTES=new_data.get('NOTES'),
                            INTERPRETATION_STANDARD='CLSI',
                            last_modified_by_id=request.user.id,
                            last_modified_by_username=request.user.username,
                        )
                        created_count += 1
                        logger.info(f" Created {test.AST_ID}")
                    elif is_first_fill:
                        # First-time fill (no audit)
                        for field, value in new_data.items():
                            setattr(test, field, value)
                        
                        test.last_modified_by_id = request.user.id
                        test.last_modified_by_username = request.user.username
                        test.save(using=db_alias)
                        
                        first_fill_count += 1
                        logger.info(f" First-fill {test.AST_ID}")
                    else:
                        # Normal update (with audit)
                        for field, value in new_data.items():
                            setattr(test, field, value)
                        
                        test.last_modified_by_id = request.user.id
                        test.last_modified_by_username = request.user.username
                        test.save(using=db_alias)
                        
                        updated_count += 1
                        logger.info(f" Updated (audit) {test.AST_ID}")
                
                except Exception as e:
                    logger.error(f" Error processing test {test_key}: {e}", exc_info=True)
                    errors.append(f"Test {test_key}: {str(e)}")
            
            # Check for errors
            if errors:
                messages.warning(request, f"⚠ Some tests had errors: {'; '.join(errors)}")
        
        # Success message
        if updated_count > 0:
            messages.success(
                request,
                f' Updated {updated_count} tests with audit trail, '
                f'{first_fill_count} first-time fills, {created_count} new tests!'
            )
        else:
            messages.success(
                request,
                f' Saved {first_fill_count} first-time fills, {created_count} new tests!'
            )
        
        return redirect('study_43en:antibiotic_list', usubjid=usubjid, culture_id=culture_id)
    
    # GET - Display list
    profile = get_antibiotic_resistance_profile(culture)
    
    #  DEBUG: Log profile details
    logger.info(f" Profile: {profile}")
    if profile:
        logger.info(f" Profile keys: {profile.keys()}")
        logger.info(f" tests_by_tier: {profile.get('tests_by_tier', {})}")
    
    # Check permissions
    has_change_permission = request.user.has_perm('study_43en.change_antibioticsensitivity')
    
    context = {
        'usubjid': usubjid,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'culture': culture,
        'tests': tests,
        'profile': profile,
        'has_tests': tests.exists(),
        'has_change_permission': has_change_permission,
        'selected_site_id': screening_case.SITEID,
    }
    
    logger.info(f" Loaded {tests.count()} antibiotic tests for {culture.LAB_CULTURE_ID}")
    return render(request, 'studies/study_43en/patient/form/antibiotic_sensitivity_list.html', context)

#  NEW: Add "Other" Antibiotic (AJAX)
@login_required
@require_crf_add('antibioticsensitivity', redirect_to='study_43en:patient_list')
def antibiotic_create_other(request, usubjid, culture_id):
    """
    Add a custom "Other" antibiotic not in the standard list
    Handles AJAX POST request from modal
    """
    logger.info(f"=== ADD OTHER ANTIBIOTIC (AJAX) ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Culture: {culture_id}")
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST only'}, status=405)
    
    try:
        # Get culture (WITH SITE FILTERING)
        screening_case, enrollment_case, culture, _ = get_culture_with_tests(request, usubjid, culture_id)
        
        # Check if culture is testable
        if not culture.is_testable_for_antibiotics:
            return JsonResponse({
                'success': False,
                'message': 'Culture is not eligible for antibiotic testing'
            }, status=400)
        
        # Get form data
        antibiotic_name = request.POST.get('other_antibiotic_name', '').strip()
        tier = request.POST.get('tier')
        sensitivity = request.POST.get('sensitivity_level')
        mic = request.POST.get('mic', '').strip()
        izdiam = request.POST.get('izdiam', '').strip()
        method = request.POST.get('method', '').strip()
        notes = request.POST.get('notes', '').strip()
        
        # Validate required fields
        if not antibiotic_name:
            return JsonResponse({
                'success': False,
                'message': 'Antibiotic name is required'
            }, status=400)
        
        if not tier:
            return JsonResponse({
                'success': False,
                'message': 'Tier is required'
            }, status=400)
        
        if not sensitivity:
            return JsonResponse({
                'success': False,
                'message': 'Sensitivity level is required'
            }, status=400)
        
        # Create the test
        with transaction.atomic():
            test = AntibioticSensitivity.objects.create(
                LAB_CULTURE_ID=culture,
                ANTIBIOTIC_NAME='Other',
                OTHER_ANTIBIOTIC_NAME=antibiotic_name,
                TIER=tier,
                SENSITIVITY_LEVEL=sensitivity,
                MIC=mic if mic else None,
                IZDIAM=float(izdiam) if izdiam else None,
                NOTES=notes if notes else None,
                INTERPRETATION_STANDARD='CLSI',
                last_modified_by_id=request.user.id,
                last_modified_by_username=request.user.username,
            )
            
            logger.info(f" Created other antibiotic: {test.AST_ID} - {antibiotic_name}")
            
            return JsonResponse({
                'success': True,
                'message': f'Added {antibiotic_name} successfully',
                'test': {
                    'id': test.id,
                    'AST_ID': test.AST_ID,
                    'WHONET_CODE': test.WHONET_CODE,
                    'antibiotic_name': antibiotic_name,
                    'tier': tier,
                    'sensitivity': sensitivity,
                }
            })
    
    except Exception as e:
        logger.error(f" Error creating other antibiotic: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


# ==========================================
# CREATE VIEW (Inline Formset)
# ==========================================

@login_required
@require_crf_add('antibioticsensitivity', redirect_to='study_43en:patient_list')
@audit_log(
    model_name='ANTIBIOTIC_SENSITIVITY',
    get_patient_id_from='usubjid',
    patient_model=SCR_CASE,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def antibiotic_create(request, usubjid, culture_id):
    """
    Add antibiotic sensitivity tests using inline formset
    
    Permission: add_antibiotic_sensitivity
    Features:
    - Add multiple antibiotics at once
    - Auto-generates WHONET_CODE and AST_ID
    - Validates culture eligibility
    """
    logger.info(f"=== ANTIBIOTIC SENSITIVITY CREATE ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}, Culture: {culture_id}")
    
    # Get culture
    screening_case, enrollment_case, culture, _ = get_culture_with_tests(
        request, usubjid, culture_id
    )
    
    #  Site access already verified by helper function
    
    # Check if culture is testable
    if not culture.is_testable_for_antibiotics:
        messages.error(
            request,
            f' Cannot add tests: Culture {culture.LAB_CULTURE_ID} is not positive for Klebsiella.'
        )
        return redirect('study_43en:microbiology_list', usubjid=usubjid)
    
    # POST - Process creation
    if request.method == 'POST':
        formset = AntibioticSensitivityInlineFormSet(
            request.POST,
            instance=culture,
            form_kwargs={'culture': culture}
        )
        
        if formset.is_valid():
            try:
                with transaction.atomic():
                    instances = formset.save(commit=False)
                    
                    # Set audit fields and save
                    for test in instances:
                        test.last_modified_by_id = request.user.id
                        test.last_modified_by_username = request.user.username
                        test.save()  # Triggers WHONET_CODE and AST_ID generation
                    
                    # Handle deletions
                    for test in formset.deleted_objects:
                        test.delete()
                    
                    logger.info(f" Added {len(instances)} antibiotic tests to {culture.LAB_CULTURE_ID}")
                    
                    messages.success(
                        request,
                        f' Đã thêm {len(instances)} kháng sinh đồ cho culture {culture.LAB_CULTURE_ID}!'
                    )
                    return redirect('study_43en:antibiotic_list', usubjid=usubjid, culture_id=culture_id)
            
            except Exception as e:
                logger.error(f" Error creating tests: {e}", exc_info=True)
                messages.error(request, f'Lỗi khi thêm kháng sinh đồ: {str(e)}')
        else:
            logger.warning(f"Formset validation errors: {formset.errors}")
            messages.error(request, 'Vui lòng kiểm tra lại các trường bị lỗi.')
    
    # GET - Show blank formset
    else:
        formset = AntibioticSensitivityInlineFormSet(
            instance=culture,
            form_kwargs={'culture': culture}
        )
    
    context = {
        'formset': formset,
        'usubjid': usubjid,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'culture': culture,
        'is_create': True,
        'selected_site_id': screening_case.SITEID,
    }
    
    return render(request, 'studies/study_43en/patient/form/LAB/antibiotic_sensitivity_form.html', context)


# ==========================================
# UPDATE VIEW WITH UNIVERSAL AUDIT
# ==========================================

@login_required
@require_crf_change('antibioticsensitivity', redirect_to='study_43en:patient_list')
@audit_log(
    model_name='ANTIBIOTIC_SENSITIVITY',
    get_patient_id_from='usubjid',
    patient_model=SCR_CASE,
    audit_log_model=AuditLog,
    audit_log_detail_model=AuditLogDetail
)
def antibiotic_update(request, usubjid, culture_id, test_id):
    """
    Update antibiotic sensitivity test WITH UNIVERSAL AUDIT SYSTEM
    
    Permission: change_antibiotic_sensitivity
    Features:
    - Tracks changes to sensitivity level, MIC
    - Re-parses MIC_NUMERIC
    - Updates WHONET_CODE if antibiotic changed
    """
    logger.info(f"=== ANTIBIOTIC SENSITIVITY UPDATE ===")
    logger.info(
        f"User: {request.user.username}, USUBJID: {usubjid}, "
        f"Culture: {culture_id}, Test ID: {test_id}"
    )
    
    # Get culture and test
    screening_case, enrollment_case, culture, _ = get_culture_with_tests(
        request, usubjid, culture_id
    )
    
    test = get_object_or_404(
        AntibioticSensitivity,
        id=test_id,
        LAB_CULTURE_ID=culture
    )
    
    logger.info(f"Editing test: {test.AST_ID}")
    
    #  Site access already verified by helper function
    
    # GET - Redirect to list
    if request.method == 'GET':
        messages.info(request, 'Please use the edit button to modify tests.')
        return redirect('study_43en:antibiotic_list', usubjid=usubjid, culture_id=culture_id)
    
    # POST - USE UNIVERSAL AUDIT SYSTEM
    logger.info(" Using Universal Audit System (Tier 1)")
    
    # Use Universal Audit System
    return process_crf_update(
        request=request,
        instance=test,
        form_class=AntibioticSensitivityForm,
        template_name='studies/study_43en/patient/form/antibiotic_sensitivity_list.html',
        redirect_url=reverse('study_43en:antibiotic_list', kwargs={
            'usubjid': usubjid,
            'culture_id': culture_id
        }),
        extra_context={
            'usubjid': usubjid,
            'screening_case': screening_case,
            'enrollment_case': enrollment_case,
            'culture': culture,
            'tests': AntibioticSensitivity.objects.filter(
                LAB_CULTURE_ID=culture
            ).order_by('TIER', 'WHONET_CODE'),
            'profile': get_antibiotic_resistance_profile(culture),
            'selected_site_id': screening_case.SITEID,
            'edit_test_id': test_id,
        },
    )


# ==========================================
# GET TEST DATA (AJAX)
# ==========================================

@login_required
@require_crf_view('antibioticsensitivity', redirect_to='study_43en:patient_list')
def antibiotic_get(request, usubjid, culture_id, test_id):
    """
    Get antibiotic test data as JSON for edit modal
    
    Permission: view_antibiotic_sensitivity
    Returns: JSON with test data including AST_ID and WHONET_CODE
    """
    logger.info(f"=== ANTIBIOTIC SENSITIVITY GET ===")
    logger.info(
        f"User: {request.user.username}, USUBJID: {usubjid}, "
        f"Culture: {culture_id}, Test: {test_id}"
    )
    
    try:
        # Get culture and test
        screening_case, enrollment_case, culture, _ = get_culture_with_tests(
            request, usubjid, culture_id
        )
        
        test = get_object_or_404(
            AntibioticSensitivity,
            id=test_id,
            LAB_CULTURE_ID=culture
        )
        
        #  Site access already verified by helper function
        
        # Format date
        test_date = test.TESTDATE.isoformat() if test.TESTDATE else ''
        
        data = {
            'success': True,
            'data': {
                'id': test.id,
                'AST_ID': test.AST_ID,  #  Semantic ID
                'WHONET_CODE': test.WHONET_CODE,  #  Standard code
                'ANTIBIOTIC_NAME': test.ANTIBIOTIC_NAME,
                'OTHER_ANTIBIOTIC_NAME': test.OTHER_ANTIBIOTIC_NAME or '',
                'TIER': test.TIER,
                'SENSITIVITY_LEVEL': test.SENSITIVITY_LEVEL,
                'MIC': test.MIC or '',
                'MIC_NUMERIC': test.MIC_NUMERIC,
                'IZDIAM': test.IZDIAM,
                'TESTDATE': test_date,
                'INTERPRETATION_STANDARD': test.INTERPRETATION_STANDARD,
                'NOTES': test.NOTES or '',
                'version': test.version,
                # For display
                'antibiotic_display': test.get_antibiotic_display_name(),
                'tier_display': test.get_TIER_display(),
                'sensitivity_display': test.get_SENSITIVITY_LEVEL_display(),
                'is_resistant': test.is_resistant,
            }
        }
        
        logger.info(f" Retrieved test data for {test.AST_ID}")
        return JsonResponse(data)
    
    except Exception as e:
        logger.error(f" Error getting test: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# ==========================================
# RESISTANCE STATISTICS VIEW
# ==========================================

@login_required
@require_crf_view('antibioticsensitivity', redirect_to='study_43en:patient_list')
def antibiotic_statistics(request, usubjid):
    """
    Display comprehensive resistance statistics for a patient
    
    Permission: view_antibiotic_sensitivity
    Features:
    - Resistance rates by tier
    - Top resistant antibiotics
    - Carbapenem resistance detection
    """
    logger.info(f"=== ANTIBIOTIC STATISTICS ===")
    logger.info(f"User: {request.user.username}, USUBJID: {usubjid}")
    
    # Get enrollment
    screening_case = get_object_or_404(SCR_CASE, USUBJID=usubjid)
    enrollment_case = get_object_or_404(ENR_CASE, USUBJID=screening_case)
    
    # Check site access
    site_check = check_instance_site_access(
        request,
        enrollment_case,
        redirect_to='study_43en:patient_list'
    )
    if site_check is not True:
        return site_check
    
    # Get statistics
    stats = get_resistance_statistics(enrollment_case)
    
    context = {
        'usubjid': usubjid,
        'screening_case': screening_case,
        'enrollment_case': enrollment_case,
        'stats': stats,
        'selected_site_id': screening_case.SITEID,
    }
    
    logger.info(f" Generated statistics: {stats['total_tests']} tests analyzed")
    return render(request, 'studies/study_43en/patient/list/antibiotic_statistics.html', context)
