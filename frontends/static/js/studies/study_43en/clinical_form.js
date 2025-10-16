$(document).ready(function() {
    // Tắt hệ thống audit log cũ trong clinical_form.js
    // Sử dụng hệ thống audit log mới trong clinical-log.js
    
    // Hàm chuẩn bị dữ liệu trước khi submit (không gọi saveAuditData nữa)
    $('#clinicalForm').on('prepare-submit', function() {
        console.log('Preparing form data before submission');
        prepareAllFormValues();
        // Không gọi saveAuditData() nữa - để clinical-log.js xử lý audit
    });

    // Hàm saveAuditData đã được chuyển sang clinical-log.js
    // Để tránh xung đột, hàm này đã được loại bỏ khỏi clinical_form.js

    function toggleSupportTypeDurations() {
        function updateVisibility() {
            // Oxy mũi/mask
            if ($('input[name="SUPPORTTYPE"][value="Oxy mũi/mask"]').is(':checked')) {
                $('#id_OXYMASKDURATION').closest('.form-group').show();
            } else {
                $('#id_OXYMASKDURATION').closest('.form-group').hide();
            }
            // HFNC/NIV
            if ($('input[name="SUPPORTTYPE"][value="HFNC/NIV"]').is(':checked')) {
                $('#id_HFNCNIVDURATION').closest('.form-group').show();
            } else {
                $('#id_HFNCNIVDURATION').closest('.form-group').hide();
            }
            // Thở máy
            if ($('input[name="SUPPORTTYPE"][value="Thở máy"]').is(':checked')) {
                $('#id_VENTILATORDURATION').closest('.form-group').show();
            } else {
                $('#id_VENTILATORDURATION').closest('.form-group').hide();
            }
        }
        $('input[name="SUPPORTTYPE"]').on('change', updateVisibility);
        updateVisibility(); // Khởi tạo trạng thái ban đầu
    }

    function prepareAllFormValues() {
        // Đồng bộ RESUSFLUID
        var resusfluidRadioVal = $('input[name="resusfluid_radio"]:checked').val();
        if (resusfluidRadioVal === 'true') {
            if ($('input[name="RESUSFLUID_hidden"]').length) {
                $('input[name="RESUSFLUID_hidden"]').val('true');
            } else {
                $('<input>').attr({
                    type: 'hidden',
                    name: 'RESUSFLUID',
                    value: 'true'
                }).appendTo('#clinicalForm');
            }
            $('#id_RESUSFLUID').prop('checked', true);
        } else {
            $('#id_RESUSFLUID').prop('checked', false);
            if ($('input[name="RESUSFLUID_hidden"]').length) {
                $('input[name="RESUSFLUID_hidden"]').val('false');
            } else {
                $('<input>').attr({
                    type: 'hidden',
                    name: 'RESUSFLUID',
                    value: 'false'
                }).appendTo('#clinicalForm');
            }
        }

        // Đồng bộ các trường khác nếu cần
        updateAllHiddenFields();
    }


    // Hàm xử lý tab navigation
    function handleTabNavigation() {
        $('.nav-tabs a').click(function(e) {
            e.preventDefault();
            $(this).tab('show');
        });

        $('.prev-page').click(function() {
            var targetTab = $(this).data('target');
            $('#' + targetTab).tab('show');
        });
    }


    function toggleOtherDetails() {
        $('#id_OTHERSYMPTOM').on('change', function() {
            if ($(this).is(':checked')) {
                $('#othersymptom_detail').show();
            } else {
                $('#othersymptom_detail').hide();
            }
        });

        $('#id_OTHERSYMPTOM_2').on('change', function() {
            if ($(this).is(':checked')) {
                $('#othersymptom_2_detail').show();
            } else {
                $('#othersymptom_2_detail').hide();
            }
        });

        $('#id_RESPPATTERN_OTHER').on('change', function() {
            if ($(this).is(':checked')) {
                $('#resppattern_other_detail').show();
            } else {
                $('#resppattern_other_detail').hide();
            }
        });

        $('input[name="RESPPATTERN"]').not('#id_RESPPATTERN_OTHER').on('change', function() {
            $('#resppattern_other_detail').hide();
        });
    }

    function toggleSections() {
        $('#id_VASODRUG').on('change', function() {
            if ($(this).is(':checked')) {
                $('#vasodrug-section').show();
            } else {
                $('#vasodrug-section').hide();
            }
        });
        if ($('#id_VASODRUG').is(':checked')) {
            $('#vasodrug-section').show();
        }

        $('#id_PRIORANTIBIOTIC').on('change', function() {
            if ($(this).is(':checked')) {
                $('#prior-antibiotic-section').show();
            } else {
                $('#prior-antibiotic-section').hide();
            }
        });
        if ($('#id_PRIORANTIBIOTIC').is(':checked')) {
            $('#prior-antibiotic-section').show();
        }

        $('#id_INITIALANTIBIOTIC').on('change', function() {
            if ($(this).is(':checked')) {
                $('#initial-antibiotic-section').show();
            } else {
                $('#initial-antibiotic-section').hide();
            }
        });
        if ($('#id_INITIALANTIBIOTIC').is(':checked')) {
            $('#initial-antibiotic-section').show();
        }
    }

    function handleRespiSupportRadio() {
        $('input[name="RESPISUPPORT"]').on('change', function() {
            var value = $(this).val();
            if (value === 'true') {
                $('#respi-support-section').show();
                $('#id_RESPISUPPORT').prop('checked', true);
            } else {
                $('#respi-support-section').hide();
                $('#id_RESPISUPPORT').prop('checked', false);
            }
        });
        // Khởi tạo trạng thái ban đầu
        if ($('input[name="RESPISUPPORT"]:checked').val() === 'true') {
            $('#respi-support-section').show();
        } else {
            $('#respi-support-section').hide();
        }
    }

    function syncRespiSupportField() {
        var isChecked = $('#id_RESPISUPPORT').prop('checked');
        if (isChecked) {
            $('input[name="RESPISUPPORT"][value="true"]').prop('checked', true);
            $('#respi-support-options').show();
        } else {
            $('input[name="RESPISUPPORT"][value="false"]').prop('checked', true);
            $('#respi-support-options').hide();
        }
    }

    function handleResusFluidRadio() {
        $('input[name="resusfluid_radio"]').on('change', function() {
            var value = $(this).val();
            console.log('RESUSFLUID changed to:', value);

            if (value === 'true') {
                $('#id_RESUSFLUID').prop('checked', true);
                $('#resus-fluid-section').show();
            } else {
                $('#id_RESUSFLUID').prop('checked', false);
                $('#resus-fluid-section').hide();
            }
        });
    }

    function syncResusFluidField() {
        var isChecked = $('#id_RESUSFLUID').prop('checked');
        console.log('RESUSFLUID initial checked state:', isChecked);

        if (isChecked) {
            $('#resusfluid_yes').prop('checked', true);
            $('#resus-fluid-section').show();
        } else {
            $('#resusfluid_no').prop('checked', true);
            $('#resus-fluid-section').hide();
        }
    }

    function handleDialysisRadio() {
        $('input[name="dialysis_radio"]').on('change', function() {
            var value = $(this).val();
            if (value === 'yes') {
                $('#id_DIALYSIS').prop('checked', true);
            } else {
                $('#id_DIALYSIS').prop('checked', false);
            }
        });
    }

    function syncDialysisField() {
        var isChecked = $('#id_DIALYSIS').prop('checked');

        if (isChecked) {
            $('#dialysis_yes').prop('checked', true);
        } else {
            $('#dialysis_no').prop('checked', true);
        }
    }

    function handleDrainageRadio() {
        $('input[name="drainage_radio"]').on('change', function() {
            var value = $(this).val();
            if (value === 'yes') {
                $('#id_DRAINAGE').prop('checked', true);
                $('#drainage_type_section').show();
            } else {
                $('#id_DRAINAGE').prop('checked', false);
                $('#drainage_type_section').hide();
            }
        });
    }

    function handleDrainageTypeRadio() {
        $('input[name="drainage_type_radio"]').on('change', function() {
            var value = $(this).val();
            $('#id_DRAINAGETYPE').val(value);

            if (value === 'Other') {
                $('#drainage_type_other').show();
            } else {
                $('#drainage_type_other').hide();
            }
        });
    }

    function syncDrainageField() {
        var isChecked = $('#id_DRAINAGE').prop('checked');

        if (isChecked) {
            $('#drainage_yes').prop('checked', true);
            $('#drainage_type_section').show();

            var drainageType = $('#id_DRAINAGETYPE').val();
            if (drainageType) {
                $(`input[name="drainage_type_radio"][value="${drainageType}"]`).prop('checked', true);

                if (drainageType === 'Other') {
                    $('#drainage_type_other').show();
                }
            }
        } else {
            $('#drainage_no').prop('checked', true);
            $('#drainage_type_section').hide();
        }
    }

    function handleInfectionRadio() {
        $('input[name="BLOODINFECT"]').on('change', function() {
            $('#id_BLOODINFECT').val($(this).val());
        });

        $('input[name="SEPTICSHOCK"]').on('change', function() {
            $('#id_SEPTICSHOCK').val($(this).val());
        });
    }

    function handleInfectSrcRadio() {
        $('input[name="infectsrc"]').on('change', function() {
            var value = $(this).val();
            $('#id_INFECTSRC').val(value);
        });
    }

    function syncInfectionFields() {
        var bloodinfectVal = $('#id_BLOODINFECT').val();
        if (bloodinfectVal === 'yes') {
            $('#sepsis_yes').prop('checked', true);
        } else if (bloodinfectVal === 'no') {
            $('#sepsis_no').prop('checked', true);
        } else if (bloodinfectVal === 'unknown') {
            $('#sepsis_unknown').prop('checked', true);
        }

        var septicshockVal = $('#id_SEPTICSHOCK').val();
        if (septicshockVal === 'yes') {
            $('#septic_shock_yes').prop('checked', true);
        } else if (septicshockVal === 'no') {
            $('#septic_shock_no').prop('checked', true);
        } else if (septicshockVal === 'unknown') {
            $('#septic_shock_unknown').prop('checked', true);
        }

        var infectSrc = $('#id_INFECTSRC').val();
        if (infectSrc) {
            $(`input[name="infectsrc"][value="${infectSrc}"]`).prop('checked', true);
        }
    }

    function handleAbxAppropriateRadio() {
        $('input[name="abx_appropriate"]').on('change', function() {
            var value = $(this).val();
            if (value === 'yes') {
                $('#id_INITIALABXAPPROP').prop('checked', true);
            } else if (value === 'no') {
                $('#id_INITIALABXAPPROP').prop('checked', false);
            } else {
                $('#id_INITIALABXAPPROP').prop('checked', false);
                $('#id_INITIALABXAPPROP').data('unknown', true);
            }
        });
    }

    function syncAbxAppropField() {
        var isChecked = $('#id_INITIALABXAPPROP').prop('checked');

        if (isChecked) {
            $('#abx_approp_yes').prop('checked', true);
        } else {
            var val = $('#id_INITIALABXAPPROP').val();
            if (val === '') {
                $('#abx_approp_unknown').prop('checked', true);
            } else {
                $('#abx_approp_no').prop('checked', true);
            }
        }
    }

    function handleInfectFocusCheckboxes() {
        $('input[name="infectfocus[]"]').on('change', function() {
            updateInfectFocus();
        });
    }

    function updateInfectFocus() {
        var selected = [];
        $('input[name="infectfocus[]"]:checked').each(function() {
            selected.push($(this).val());
        });

        if (selected.includes('none')) {
            $('input[name="infectfocus[]"]').not('#infectfocus_none').prop('checked', false);
            selected = ['none'];
        }

        $('#id_INFECTFOCUS48H').val(selected.join(','));

        if (selected.includes('other')) {
            $('#infectfocus-other-section').show();
        } else {
            $('#infectfocus-other-section').hide();
        }
    }

    function handleInfectFocusOther() {
        $('#id_INFECTFOCUS48H').on('change', function() {
            if ($(this).val() === 'Other') {
                $('#infectfocus-other-section').show();
            } else {
                $('#infectfocus-other-section').hide();
            }
        });

        if ($('#id_INFECTFOCUS48H').val() === 'Other') {
            $('#infectfocus-other-section').show();
        } else {
            $('#infectfocus-other-section').hide();
        }
    }

    function syncInfectFocusField() {
        var infectFocus = $('#id_INFECTFOCUS48H').val();
        if (infectFocus) {
            var focuses = infectFocus.split(',');
            focuses.forEach(function(focus) {
                $(`input[name="infectfocus[]"][value="${focus}"]`).prop('checked', true);
            });

            if (focuses.includes('other')) {
                $('#infectfocus-other-section').show();
            }
        }
    }

    function handleRespiSupportTypes() {
        $('input[name="support_type[]"]').on('change', function() {
            updateSupportTypes();
        });

        $('input[name="oxygen_days"]').on('change', function() {
            var value = $(this).val();
            if (value) {
                $('#id_OXYMASKDURATION').val(value);
            }
        });

        $('input[name="hfnc_days"]').on('change', function() {
            var value = $(this).val();
            if (value) {
                $('#id_HFNCNIVDURATION').val(value);
            }
        });

        $('input[name="ventilator_days"]').on('change', function() {
            var value = $(this).val();
            if (value) {
                $('#id_VENTILATORDURATION').val(value);
            }
        });
    }

    function updateSupportTypes() {
        var selected = [];
        $('input[name="support_type[]"]:checked').each(function() {
            selected.push($(this).val());
        });

        $('#id_SUPPORTTYPE').val(selected.join(','));
    }

    function syncRespiSupportFields() {
        var supportType = $('#id_SUPPORTTYPE').val();
        if (supportType) {
            var types = supportType.split(',');
            types.forEach(function(type) {
                $(`input[name="support_type[]"][value="${type}"]`).prop('checked', true);
            });

            var oxyDays = $('#id_OXYMASKDURATION').val();
            if (oxyDays) {
                $('input[name="oxygen_days"]').val(oxyDays);
            }

            var hfncDays = $('#id_HFNCNIVDURATION').val();
            if (hfncDays) {
                $('input[name="hfnc_days"]').val(hfncDays);
            }

            var ventilatorDays = $('#id_VENTILATORDURATION').val();
            if (ventilatorDays) {
                $('input[name="ventilator_days"]').val(ventilatorDays);
            }
        }
    }

    function handleVasoinotropesRadio() {
        $('input[name="vasoinotropes_radio"]').on('change', function() {
            var value = $(this).val();
            if (value === 'true') {
                $('#id_VASOINOTROPES').prop('checked', true);
                $('#vasodrug-section').show();
            } else {
                $('#id_VASOINOTROPES').prop('checked', false);
                $('#vasodrug-section').hide();
            }
        });
    }

    function syncVasoinotropesField() {
        var isChecked = $('#id_VASOINOTROPES').prop('checked');
        if (isChecked) {
            $('#vasoinotropes_yes').prop('checked', true);
            $('#vasodrug-section').show();
        } else {
            $('#vasoinotropes_no').prop('checked', true);
            $('#vasodrug-section').hide();
        }
    }

    function setupFormsetHandlers(formsetPrefix, addButtonSelector) {
        var formsetName = formsetPrefix;
        if (formsetPrefix === 'hospiprocess-formset') {
            formsetName = 'hospiprocess_formset';
        } else if (formsetPrefix === 'prior-antibiotic-formset') {
            formsetName = 'priorantibiotic_set';
        } else if (formsetPrefix === 'initial-antibiotic-formset') {
            formsetName = 'initialantibiotic_set';
        } else if (formsetPrefix === 'main-antibiotic-formset') {
            formsetName = 'mainantibiotic_set';
        } else if (formsetPrefix === 'vasoidrug-formset') {
            formsetName = 'vasoidrug_set';
        } else if (formsetPrefix === 'aehospevent-formset') {
            formsetName = 'aehospevent_set';
        } else if (formsetPrefix === 'improvesympt-formset') {
            formsetName = 'improvesympt_set';
        }

        var totalForms = $(`#id_${formsetName}-TOTAL_FORMS`);
        console.log(`Khởi tạo formset ${formsetPrefix}, Total forms: ${totalForms.val()}`);

        $(addButtonSelector).click(function() {
            var formCount = parseInt(totalForms.val());
            console.log(`Thêm form mới cho ${formsetPrefix}, index: ${formCount}`);

            var emptyRow = $(`#${formsetPrefix} .empty-row`);
            if (emptyRow.length) {
                emptyRow.remove();
            }

            var newRow;
            if (formsetPrefix.includes('hospiprocess')) {
                newRow = $(`
                    <tr class="hospiprocess-form-row">
                        <td>
                            <input type="hidden" name="${formsetName}-${formCount}-id" id="id_${formsetName}-${formCount}-id">
                            <input type="text" name="${formsetName}-${formCount}-DEPTNAME" class="form-control" placeholder="Tên khoa" data-initial-value="">
                        </td>
                        <td>
                            <input type="text" name="${formsetName}-${formCount}-STARTDTC" class="form-control datepicker" placeholder="YYYY-MM-DD" data-initial-value="">
                        </td>
                        <td>
                            <input type="text" name="${formsetName}-${formCount}-ENDDTC" class="form-control datepicker" placeholder="YYYY-MM-DD" data-initial-value="">
                        </td>
                        <td>
                            <textarea name="${formsetName}-${formCount}-TRANSFER_REASON" class="form-control" rows="2" placeholder="Lý do chuyển" data-initial-value=""></textarea>
                        </td>
                        <td>
                            <input type="checkbox" class="delete-checkbox" data-formset="${formsetPrefix}" data-index="${formCount}">
                            <input type="hidden" name="${formsetName}-${formCount}-DELETE" id="id_${formsetName}-${formCount}-DELETE">
                        </td>
                    </tr>
                `);
            } else if (formsetPrefix.includes('vasoidrug')) {
                newRow = $(`
                    <tr class="vasoidrug-form">
                        <td>
                            <input type="hidden" name="${formsetName}-${formCount}-id" id="id_${formsetName}-${formCount}-id">
                            <input type="text" name="${formsetName}-${formCount}-VASOIDRUGNAME" class="form-control" placeholder="Tên thuốc" data-initial-value="">
                        </td>
                        <td>
                            <input type="text" name="${formsetName}-${formCount}-VASOIDRUGDOSAGE" class="form-control" placeholder="Liều lượng" data-initial-value="">
                        </td>
                        <td>
                            <input type="text" name="${formsetName}-${formCount}-VASOIDRUGSTARTDTC" class="form-control datepicker" placeholder="Ngày bắt đầu" data-initial-value="">
                        </td>
                        <td>
                            <input type="text" name="${formsetName}-${formCount}-VASOIDRUGENDDTC" class="form-control datepicker" placeholder="Ngày kết thúc" data-initial-value="">
                        </td>
                        <td>
                            <input type="checkbox" class="delete-checkbox" data-formset="${formsetPrefix}" data-index="${formCount}">
                            <input type="hidden" name="${formsetName}-${formCount}-DELETE" id="id_${formsetName}-${formCount}-DELETE">
                        </td>
                    </tr>
                `);
            } else if (formsetPrefix.includes('prior')) {
                newRow = $(`
                    <tr class="antibiotic-form prior-antibiotic-form-row">
                        <td>
                            <input type="hidden" name="${formsetName}-${formCount}-id" id="id_${formsetName}-${formCount}-id">
                            <input type="text" name="${formsetName}-${formCount}-PRIORANTIBIONAME" class="form-control" placeholder="Tên kháng sinh" data-initial-value="">
                        </td>
                        <td>
                            <input type="text" name="${formsetName}-${formCount}-PRIORANTIBIODOSAGE" class="form-control" placeholder="Liều lượng" data-initial-value="">
                        </td>
                        <td>
                            <input type="text" name="${formsetName}-${formCount}-PRIORANTIBIOSTARTDTC" class="form-control datepicker" placeholder="Ngày bắt đầu" data-initial-value="">
                        </td>
                        <td>
                            <input type="text" name="${formsetName}-${formCount}-PRIORANTIBIOENDDTC" class="form-control datepicker" placeholder="Ngày kết thúc" data-initial-value="">
                        </td>
                        <td>
                            <input type="checkbox" class="delete-checkbox" data-formset="${formsetPrefix}" data-index="${formCount}">
                            <input type="hidden" name="${formsetName}-${formCount}-DELETE" id="id_${formsetName}-${formCount}-DELETE">
                        </td>
                    </tr>
                `);
            } else if (formsetPrefix.includes('initial')) {
                newRow = $(`
                    <tr class="antibiotic-form initial-antibiotic-form-row">
                        <td>
                            <input type="hidden" name="${formsetName}-${formCount}-id" id="id_${formsetName}-${formCount}-id">
                            <input type="text" name="${formsetName}-${formCount}-INITIALANTIBIONAME" class="form-control" placeholder="Tên kháng sinh" data-initial-value="">
                        </td>
                        <td>
                            <input type="text" name="${formsetName}-${formCount}-INITIALANTIBIODOSAGE" class="form-control" placeholder="Liều lượng" data-initial-value="">
                        </td>
                        <td>
                            <input type="text" name="${formsetName}-${formCount}-INITIALANTIBIOSTARTDTC" class="form-control datepicker" placeholder="Ngày bắt đầu" data-initial-value="">
                        </td>
                        <td>
                            <input type="text" name="${formsetName}-${formCount}-INITIALANTIBIOENDDTC" class="form-control datepicker" placeholder="Ngày kết thúc" data-initial-value="">
                        </td>
                        <td>
                            <input type="checkbox" class="delete-checkbox" data-formset="${formsetPrefix}" data-index="${formCount}">
                            <input type="hidden" name="${formsetName}-${formCount}-DELETE" id="id_${formsetName}-${formCount}-DELETE">
                        </td>
                    </tr>
                `);
            } else if (formsetPrefix.includes('main')) {
                newRow = $(`
                    <tr class="antibiotic-form main-antibiotic-form-row">
                        <td>
                            <input type="hidden" name="${formsetName}-${formCount}-id" id="id_${formsetName}-${formCount}-id">
                            <input type="text" name="${formsetName}-${formCount}-MAINANTIBIONAME" class="form-control" placeholder="Tên kháng sinh" data-initial-value="">
                        </td>
                        <td>
                            <input type="text" name="${formsetName}-${formCount}-MAINANTIBIODOSAGE" class="form-control" placeholder="Liều lượng" data-initial-value="">
                        </td>
                        <td>
                            <input type="text" name="${formsetName}-${formCount}-MAINANTIBIOSTARTDTC" class="form-control datepicker" placeholder="Ngày bắt đầu" data-initial-value="">
                        </td>
                        <td>
                            <input type="text" name="${formsetName}-${formCount}-MAINANTIBIOENDDTC" class="form-control datepicker" placeholder="Ngày kết thúc" data-initial-value="">
                        </td>
                        <td>
                            <input type="checkbox" class="delete-checkbox" data-formset="${formsetPrefix}" data-index="${formCount}">
                            <input type="hidden" name="${formsetName}-${formCount}-DELETE" id="id_${formsetName}-${formCount}-DELETE">
                        </td>
                    </tr>
                `);
            } else if (formsetPrefix.includes('aehospevent')) {
                newRow = $(`
                    <tr class="aehospevent-form-row">
                        <td>
                            <input type="hidden" name="${formsetName}-${formCount}-id" id="id_${formsetName}-${formCount}-id">
                            <input type="text" name="${formsetName}-${formCount}-AENAME" class="form-control" placeholder="Tên biến cố" data-initial-value="">
                        </td>
                        <td>
                            <textarea name="${formsetName}-${formCount}-AEDETAILS" class="form-control" rows="2" placeholder="Chi tiết biến cố" data-initial-value=""></textarea>
                        </td>
                        <td>
                            <input type="text" name="${formsetName}-${formCount}-AEDTC" class="form-control datepicker" placeholder="YYYY-MM-DD" data-initial-value="">
                        </td>
                        <td>
                            <input type="checkbox" class="delete-checkbox" data-formset="${formsetPrefix}" data-index="${formCount}">
                            <input type="hidden" name="${formsetName}-${formCount}-DELETE" id="id_${formsetName}-${formCount}-DELETE">
                        </td>
                    </tr>
                `);
            } else if (formsetPrefix.includes('improvesympt')) {
                newRow = $(`
                    <tr class="improvesympt-form-row">
                        <td>
                            <input type="hidden" name="${formsetName}-${formCount}-id" id="id_${formsetName}-${formCount}-id">
                            <select name="${formsetName}-${formCount}-IMPROVE_SYMPTS" class="form-control" data-initial-value="">
                                <option value="yes">Có</option>
                                <option value="no">Không</option>
                            </select>
                        </td>
                        <td>
                            <textarea name="${formsetName}-${formCount}-SYMPTS" class="form-control" rows="2" placeholder="Triệu chứng" data-initial-value=""></textarea>
                        </td>
                        <td>
                            <textarea name="${formsetName}-${formCount}-IMPROVE_CONDITIONS" class="form-control" rows="2" placeholder="Tình trạng cải thiện" data-initial-value=""></textarea>
                        </td>
                        <td>
                            <input type="text" name="${formsetName}-${formCount}-SYMPTSDTC" class="form-control datepicker" placeholder="YYYY-MM-DD" data-initial-value="">
                        </td>
                        <td>
                            <input type="checkbox" class="delete-checkbox" data-formset="${formsetPrefix}" data-index="${formCount}">
                            <input type="hidden" name="${formsetName}-${formCount}-DELETE" id="id_${formsetName}-${formCount}-DELETE">
                        </td>
                    </tr>
                `);
            }

            if (newRow) {
                $(`#${formsetPrefix} tbody`).append(newRow);

                $(`#${formsetPrefix} .datepicker`).datepicker({
                    format: 'yyyy-mm-dd',
                    autoclose: true
                });

                totalForms.val(formCount + 1);

                $(`#${formsetPrefix} .delete-checkbox`).on('change', function() {
                    var formset = $(this).data('formset');
                    var index = $(this).data('index');

                    if ($(this).is(':checked')) {
                        $(`#id_${formset}-${index}-DELETE`).val('on');
                        $(this).closest('tr').addClass('bg-light text-muted');
                    } else {
                        $(`#id_${formset}-${index}-DELETE`).val('');
                        $(this).closest('tr').removeClass('bg-light text-muted');
                    }
                });
            } else {
                console.error(`Không thể tạo hàng mới cho formset ${formsetPrefix}`);
            }
        });

        $(`#${formsetPrefix} .delete-checkbox`).on('change', function() {
            var formset = $(this).data('formset');
            var index = $(this).data('index');

            if ($(this).is(':checked')) {
                $(`#id_${formset}-${index}-DELETE`).val('on');
                $(this).closest('tr').addClass('bg-light text-muted');
            } else {
                $(`#id_${formset}-${index}-DELETE`).val('');
                $(this).closest('tr').removeClass('bg-light text-muted');
            }
        });
    }

    // Xử lý submit biểu mẫu với modal lý do thay đổi
    $('#clinicalForm').on('submit', function(e) {
        // Prepare all form values - make sure GCS field has a default value if empty
        prepareAllFormValues();
        
        // Ensure the GCS field is valid and focusable
        const gcsField = $('#id_GCS');
        if (gcsField.length && gcsField.prop('required')) {
            // If field is empty but required, provide a default value
            if (!gcsField.val()) {
                gcsField.val('7'); // Default value - can be changed by user
                gcsField.data('auto-filled', true);
            }
        }
        
        // Kiểm tra nếu có thay đổi thì hiển thị modal
        saveAuditData(); // Gọi lại để đảm bảo dữ liệu mới nhất
        const changedFields = JSON.parse($('#reasons_json').val() || '{}');
        if (Object.keys(changedFields).length > 0) {
            e.preventDefault();
            $('#changeReasonModal').modal('show');
        }
    });

    $('#saveWithReason').on('click', function() {
        let reason = $('#changeReason').val();
        $('#change_reason').val(reason);
        $('#clinicalForm').off('submit').submit(); // Gửi biểu mẫu mà không lặp lại modal
    });

    // Khởi tạo formset handlers
    setupFormsetHandlers('hospiprocess-formset', '[data-formset="#hospiprocess-formset"]');
    setupFormsetHandlers('prior-antibiotic-formset', '[data-formset="#prior-antibiotic-formset"]');
    setupFormsetHandlers('initial-antibiotic-formset', '[data-formset="#initial-antibiotic-formset"]');
    setupFormsetHandlers('main-antibiotic-formset', '[data-formset="#main-antibiotic-formset"]');
    setupFormsetHandlers('vasoidrug-formset', '[data-formset="#vasoidrug-formset"]');
    setupFormsetHandlers('aehospevent-formset', '[data-formset="#aehospevent-formset"]');
    setupFormsetHandlers('improvesympt-formset', '[data-formset="#improvesympt-formset"]');

    // Xử lý radio button cho aehospevent-formset
    $('input[name="has_aehospevent"]').change(function() {
        if ($(this).val() === 'yes') {
            $('#aehospevent-formset').show();
        } else {
            $('#aehospevent-formset').hide();
        }
    });

    // Xử lý radio button cho improvesympt-formset
    $('input[name="has_improvesympt"]').change(function() {
        if ($(this).val() === 'yes') {
            $('#improvesympt-formset').show();
        } else {
            $('#improvesympt-formset').hide();
        }
    });

    // Kiểm tra trạng thái ban đầu
    if ($('#aehospevent-formset tbody tr').length > 1 || $('#aehospevent-formset .empty-row').length === 0) {
        $('#has_aehospevent_yes').prop('checked', true);
        $('#aehospevent-formset').show();
    } else {
        $('#has_aehospevent_no').prop('checked', true);
        $('#aehospevent-formset').hide();
    }
    if ($('#improvesympt-formset tbody tr').length > 1 || $('#improvesympt-formset .empty-row').length === 0) {
        $('#has_improvesympt_yes').prop('checked', true);
        $('#improvesympt-formset').show();
    } else {
        $('#has_improvesympt_no').prop('checked', true);
        $('#improvesympt-formset').hide();
    }

    // Gọi tất cả các hàm khởi tạo
    handleTabNavigation();
    // Không cần dùng hàm tính toán tự động cho GCS, BMI vì người dùng nhập thủ công
    toggleOtherDetails();
    toggleSections();
    toggleSupportTypeDurations();
    handleRespiSupportRadio();
    syncRespiSupportField();
    handleResusFluidRadio();
    syncResusFluidField();
    handleDialysisRadio();
    syncDialysisField();
    handleDrainageRadio();
    handleDrainageTypeRadio();
    syncDrainageField();
    handleInfectionRadio();
    handleInfectSrcRadio();
    syncInfectionFields();
    handleAbxAppropriateRadio();
    syncAbxAppropField();
    handleInfectFocusCheckboxes();
    handleInfectFocusOther();
    syncInfectFocusField();
    handleRespiSupportTypes();
    syncRespiSupportFields();
    handleVasoinotropesRadio();
    syncVasoinotropesField();
    handleReadOnlyMode();
});