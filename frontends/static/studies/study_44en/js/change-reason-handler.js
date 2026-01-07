/**
 * Change Reason Modal Handler - FIXED
 * Ensure formset management forms are included in submit
 */

$(document).ready(function () {
    const $modal = $('#changeReasonModal');

    if ($modal.length === 0) {
        console.log(' No modal - no changes detected');
        return;
    }

    console.log('✅ Modal found - changes detected by backend');

    // 🎯 AUTO-DETECT form (support all forms)
    let $form = $('#householdCaseForm');  // Household Case form
    if ($form.length === 0) {
        $form = $('#householdExposureForm');  // Household Exposure form
    }
    if ($form.length === 0) {
        $form = $('#individualExposureForm');  // Individual Exposure form (NEW)
    }
    if ($form.length === 0) {
        $form = $('#individualFollowUpForm');  // Individual Follow-up form (NEW)
    }
    if ($form.length === 0) {
        $form = $('#individualForm');  // Individual form
    }
    if ($form.length === 0) {
        $form = $('#hiddenEditIndividualForm');  // Individual edit form
    }
    if ($form.length === 0) {
        $form = $('#hiddenEditCultureForm');  // Culture form
    }
    if ($form.length === 0) {
        $form = $('#hiddenAntibioticForm');  // Antibiotic form
    }
    if ($form.length === 0) {
        $form = $('form').filter(function () {
            return $(this).attr('id') &&
                ($(this).attr('id').includes('Form') ||
                    $(this).attr('id').includes('form'));
        }).first();
    }

    if ($form.length === 0) {
        console.error('❌ No form found!');
        return;
    }

    const formId = $form.attr('id');
    console.log('🎯 Detected form:', formId);

    //  CREATE hidden fields if they don't exist
    $('.reason-input').each(function () {
        const field = $(this).data('field');
        const $hidden = $('#reason_' + field);

        if ($hidden.length === 0) {
            console.log(' Creating missing hidden field for:', field);
            const $newHidden = $('<input>')
                .attr('type', 'hidden')
                .attr('name', 'reason_' + field)
                .attr('id', 'reason_' + field)
                .val('');
            $form.append($newHidden);
        }
    });

    // Auto-show modal
    $modal.modal('show');
    setTimeout(() => $('.reason-input').first().focus(), 500);

    //  Confirm button - FIX SUBMIT
    $('#confirmReason').on('click', function () {
        console.log('🔘 Confirm button clicked');

        let valid = true;

        //  Validate all reasons
        $('.reason-input').each(function () {
            const reason = $(this).val().trim();
            if (reason.length < 3) {
                $(this).addClass('is-invalid');
                valid = false;
            } else {
                $(this).removeClass('is-invalid');
            }
        });

        if (valid) {
            // Copy reasons to hidden fields
            $('.reason-input').each(function () {
                const field = $(this).data('field');
                const reason = $(this).val().trim();

                // Create or update hidden field
                let $hidden = $form.find('input[name="reason_' + field + '"]');
                if ($hidden.length === 0) {
                    $hidden = $('<input>')
                        .attr('type', 'hidden')
                        .attr('name', 'reason_' + field);
                    $form.append($hidden);
                }
                $hidden.val(reason);

                console.log(' Set reason_' + field + ':', reason.substring(0, 30));
            });

            console.log(' All reasons valid - submitting form');

            //  CRITICAL: Submit form directly WITHOUT closing modal first
            // This ensures all form fields (including management forms) are included
            $form.submit();
        } else {
            alert('Vui lòng nhập lý do (tối thiểu 3 ký tự) cho tất cả các thay đổi');
        }
    });

    // Cancel button
    $('#cancelReason').on('click', function () {
        console.log('🚫 Cancel button clicked');

        if (confirm('Bạn có chắc muốn hủy? Các thay đổi sẽ không được lưu.')) {
            const cancelUrl = $modal.data('cancel-url');
            if (cancelUrl) {
                console.log('↩️ Redirecting to:', cancelUrl);
                window.location.href = cancelUrl;
            } else {
                console.log('↩️ Going back');
                window.history.back();
            }
        }
    });

    // Remove invalid class on input
    $(document).on('input', '.reason-input', function () {
        if ($(this).val().trim().length >= 3) {
            $(this).removeClass('is-invalid');
        }
    });

    console.log(' Change Reason Modal Handler initialized');
});