$(document).ready(function() {
  // Tab handling
  $('.nav-tabs a').click(function(e) {
    e.preventDefault();
    $(this).tab('show');
  });
  
  // DatePicker initialization
  $('.datepicker').datepicker({
    format: 'dd/mm/yyyy',
    autoclose: true,
    todayHighlight: true,
    language: 'vi'
  });
  
  // Tự động tính BMI
  $('#id_WEIGHT, #id_HEIGHT').on('change keyup', function() {
    var weight = parseFloat($('#id_WEIGHT').val());
    var height = parseFloat($('#id_HEIGHT').val());
    
    if (weight && height) {
      // Chuyển height từ cm sang m
      var heightInMeters = height / 100;
      var bmi = weight / (heightInMeters * heightInMeters);
      $('#id_BMI').val(bmi.toFixed(2));
    } else {
      $('#id_BMI').val('');
    }
  });
  
  // Toggle các trường nhập chi tiết khi chọn "Khác"
  $('#id_OTHERSYMPTOM').on('change', function() {
    if ($(this).is(':checked')) {
      $('#othersymptom_detail').show();
    } else {
      $('#othersymptom_detail').hide();
      $('#id_SPECIFYOTHERSYMPTOM').val('');
    }
  });
  
  $('#id_OTHERSYMPTOM_2').on('change', function() {
    if ($(this).is(':checked')) {
      $('#othersymptom_2_detail').show();
    } else {
      $('#othersymptom_2_detail').hide();
      $('#id_SPECIFYOTHERSYMPTOM_2').val('');
    }
  });
  
  $('#id_RESPPATTERN_OTHER').on('change', function() {
    if ($(this).is(':checked')) {
      $('#resppattern_other_detail').show();
    } else {
      $('#resppattern_other_detail').hide();
      $('#id_RESPPATTERNOTHERSPEC').val('');
    }
  });
  
  // Nếu chọn một radio khác thì ẩn trường nhập chi tiết
  $('input[name="RESPPATTERN"]').not('#id_RESPPATTERN_OTHER').on('change', function() {
    $('#resppattern_other_detail').hide();
    $('#id_RESPPATTERNOTHERSPEC').val('');
  });
  
  // Tự động tính GCS tổng
  $('#id_EYES, #id_MOTOR, #id_VERBAL').on('change keyup', function() {
    var eyes = parseInt($('#id_EYES').val()) || 0;
    var motor = parseInt($('#id_MOTOR').val()) || 0;
    var verbal = parseInt($('#id_VERBAL').val()) || 0;
    
    if (eyes > 0 || motor > 0 || verbal > 0) {
      var total = eyes + motor + verbal;
      $('#id_GCS').val(total);
    }
  });
  
  // Xử lý toggle sections khi chọn "Có/Không"
  $('#id_VASODRUG').on('change', function() {
    if ($(this).is(':checked')) {
      $('#vasodrug-section').show();
    } else {
      $('#vasodrug-section').hide();
    }
  });
  
  // Hiển thị section nếu đã check
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
  
  // Hiển thị section nếu đã check
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
  
  // Hiển thị section nếu đã check
  if ($('#id_INITIALANTIBIOTIC').is(':checked')) {
    $('#initial-antibiotic-section').show();
  }
  
  // Xử lý radio buttons cho trạng thái hỗ trợ hô hấp
  $('input[name="respisupport_radio"]').on('change', function() {
    var value = $(this).val();
    if (value === 'yes') {
      $('#respi-support-options').show();
      $('#id_RESPISUPPORT').val(true);
    } else {
      $('#respi-support-options').hide();
      $('#id_RESPISUPPORT').val(false);
    }
  });
  
  // Xử lý radio buttons cho dịch truyền hồi sức
  $('input[name="resusfluid_radio"]').on('change', function() {
    var value = $(this).val();
    if (value === 'yes') {
      $('#resus-fluid-section').show();
      $('#id_RESUSFLUID').val(true);
    } else {
      $('#resus-fluid-section').hide();
      $('#id_RESUSFLUID').val(false);
    }
  });
  
  // Xử lý radio buttons cho lọc máu
  $('input[name="dialysis_radio"]').on('change', function() {
    var value = $(this).val();
    $('#id_DIALYSIS').val(value === 'yes');
  });
  
  // Xử lý radio buttons cho dẫn lưu
  $('input[name="drainage_radio"]').on('change', function() {
    var value = $(this).val();
    if (value === 'yes') {
      $('#drainage_type_section').show();
      $('#id_DRAINAGE').val(true);
    } else {
      $('#drainage_type_section').hide();
      $('#id_DRAINAGE').val(false);
    }
  });
  
  // Xử lý radio buttons cho loại dẫn lưu
  $('input[name="drainage_type_radio"]').on('change', function() {
    var value = $(this).val();
    $('#id_DRAINAGETYPE').val(value);
    
    if (value === 'Other') {
      $('#drainage_type_other').show();
    } else {
      $('#drainage_type_other').hide();
      $('#id_SPECIFYOTHERDRAINAGE').val('');
    }
  });
  
  // Xử lý radio buttons cho nhiễm trùng huyết
  $('input[name="sepsis"]').on('change', function() {
    var value = $(this).val();
    if (value === 'yes') {
      $('#id_BLOODINFECT').val(true);
    } else if (value === 'no') {
      $('#id_BLOODINFECT').val(false);
    } else {
      $('#id_BLOODINFECT').val(null);
    }
  });
  
  // Xử lý radio buttons cho sốc nhiễm trùng
  $('input[name="septic_shock"]').on('change', function() {
    var value = $(this).val();
    if (value === 'yes') {
      $('#id_SEPTICSHOCK').val(true);
    } else if (value === 'no') {
      $('#id_SEPTICSHOCK').val(false);
    } else {
      $('#id_SEPTICSHOCK').val(null);
    }
  });
  
  // Xử lý radio buttons cho nguồn gốc nhiễm trùng
  $('input[name="infectsrc"]').on('change', function() {
    var value = $(this).val();
    $('#id_INFECTSRC').val(value);
  });
  
  // Xử lý radio buttons cho điều trị kháng sinh ban đầu phù hợp
  $('input[name="abx_appropriate"]').on('change', function() {
    var value = $(this).val();
    if (value === 'yes') {
      $('#id_INITIALABXAPPROP').val(true);
    } else if (value === 'no') {
      $('#id_INITIALABXAPPROP').val(false);
    } else {
      $('#id_INITIALABXAPPROP').val(null);
    }
  });
  
  // Xử lý các checkbox nhiễm trùng 48h
  $('input[name="infectfocus[]"]').on('change', function() {
    updateInfectFocus();
  });
  
  function updateInfectFocus() {
    var selected = [];
    $('input[name="infectfocus[]"]:checked').each(function() {
      selected.push($(this).val());
    });
    
    // Kiểm tra nếu có "none" thì bỏ chọn các mục khác
    if (selected.includes('none')) {
      $('input[name="infectfocus[]"]').not('#infectfocus_none').prop('checked', false);
      selected = ['none'];
    }
    
    // Cập nhật hidden field
    $('#id_INFECTFOCUS48H').val(selected.join(','));
    
    // Hiển thị trường nhập "khác" nếu đã chọn
    if (selected.includes('other')) {
      $('#infectfocus-other-section').show();
    } else {
      $('#infectfocus-other-section').hide();
      $('#id_SPECIFYOTHERINFECT48H').val('');
    }
  }
  
  // Quá trình nằm viện - thêm/xóa hàng
  $('#add-hospital-row').click(function() {
    var newRow = `
      <tr>
        <td><input type="text" class="form-control" name="hospital_department[]"></td>
        <td><input type="text" class="form-control datepicker" name="hospital_from[]"></td>
        <td><input type="text" class="form-control datepicker" name="hospital_to[]"></td>
        <td><button type="button" class="btn btn-sm btn-outline-danger remove-row"><i class="fas fa-trash"></i></button></td>
      </tr>
    `;
    $('#hospital-stay-table tbody').append(newRow);
    
    // Khởi tạo datepicker cho các trường mới
    $('#hospital-stay-table .datepicker').datepicker({
      format: 'dd/mm/yyyy',
      autoclose: true,
      todayHighlight: true,
      language: 'vi'
    });
  });
  
  // Xóa hàng trong bảng quá trình nằm viện
  $('#hospital-stay-table').on('click', '.remove-row', function() {
    $(this).closest('tr').remove();
  });
  
  // Lưu dữ liệu quá trình nằm viện vào JSON trước khi submit
  $('#clinicalForm').on('submit', function() {
    var hospitalStays = [];
    $('#hospital-stay-table tbody tr').each(function() {
      var department = $(this).find('input[name="hospital_department[]"]').val();
      var from = $(this).find('input[name="hospital_from[]"]').val();
      var to = $(this).find('input[name="hospital_to[]"]').val();
      
      if (department || from || to) {
        hospitalStays.push({
          department: department,
          from: from,
          to: to
        });
      }
    });
    
    $('#hospital-stays-json').val(JSON.stringify(hospitalStays));
  });
  
  // Hỗ trợ hô hấp - checkbox và nhập số ngày
  $('input[name="support_type[]"]').on('change', function() {
    updateSupportTypes();
  });
  
  function updateSupportTypes() {
    var selected = [];
    $('input[name="support_type[]"]:checked').each(function() {
      selected.push($(this).val());
    });
    
    // Cập nhật hidden field
    $('#id_SUPPORTTYPE').val(selected.join(','));
  }
  
  $('input[name="oxygen_days"]').on('change', function() {
    $('#id_OXYMASKDURATION').val($(this).val());
  });
  
  $('input[name="hfnc_days"]').on('change', function() {
    $('#id_HFNCNIVDURATION').val($(this).val());
  });
  
  $('input[name="ventilator_days"]').on('change', function() {
    $('#id_VENTILATORDURATION').val($(this).val());
  });
  
  // Xử lý các dynamic formsets
  function setupFormsetHandlers(formsetPrefix, addButtonSelector) {
    var totalForms = $(`#id_${formsetPrefix}-TOTAL_FORMS`);
    
    // Add new form
    $(addButtonSelector).click(function() {
      var formCount = parseInt(totalForms.val());
      var emptyRow = $(`#${formsetPrefix} .empty-row`);
      
      if (emptyRow.length) {
        // Xóa hàng "empty" nếu có
        emptyRow.remove();
      }
      
      // Clone hàng đầu tiên hoặc tạo mới nếu không có
      var templateRow = $(`#${formsetPrefix} tr:first`);
      var newRow;
      
      if (templateRow.length) {
        newRow = templateRow.clone(true);
        
        // Cập nhật ID và name cho các trường
        newRow.find(':input').each(function() {
          var name = $(this).attr('name');
          if (name) {
            name = name.replace(new RegExp(`${formsetPrefix}-[0-9]+`), `${formsetPrefix}-${formCount}`);
            $(this).attr('name', name);
          }
          
          var id = $(this).attr('id');
          if (id) {
            id = id.replace(new RegExp(`${formsetPrefix}-[0-9]+`), `${formsetPrefix}-${formCount}`);
            $(this).attr('id', id);
          }
          
          // Reset giá trị
          if ($(this).attr('type') !== 'hidden') {
            $(this).val('');
          }
          
          // Đánh dấu DELETE là false
          if (name && name.endsWith('-DELETE')) {
            $(this).val('');
          }
        });
      } else {
        // Tạo hàng mới nếu không có hàng nào
        if (formsetPrefix.includes('vaso')) {
          newRow = `
            <tr class="vasoidrug-form">
              <td>
                <input type="hidden" name="${formsetPrefix}-${formCount}-id" id="id_${formsetPrefix}-${formCount}-id">
                <input type="text" name="${formsetPrefix}-${formCount}-VASOIDRUGNAME" class="form-control">
              </td>
              <td>
                <input type="text" name="${formsetPrefix}-${formCount}-VASOIDRUGDOSAGE" class="form-control">
              </td>
              <td>
                <input type="text" name="${formsetPrefix}-${formCount}-VASOIDRUGSTARTDTC" class="form-control datepicker">
              </td>
              <td>
                <input type="text" name="${formsetPrefix}-${formCount}-VASOIDRUGENDDTC" class="form-control datepicker">
              </td>
              <td>
                <input type="checkbox" class="delete-checkbox" data-formset="${formsetPrefix}" data-index="${formCount}">
                <input type="hidden" name="${formsetPrefix}-${formCount}-DELETE" id="id_${formsetPrefix}-${formCount}-DELETE">
              </td>
            </tr>
          `;
        } else if (formsetPrefix.includes('prior')) {
          newRow = `
            <tr class="antibiotic-form prior-antibiotic-form-row">
              <td>
                <input type="hidden" name="${formsetPrefix}-${formCount}-id" id="id_${formsetPrefix}-${formCount}-id">
                <input type="text" name="${formsetPrefix}-${formCount}-PRIORANTIBIONAME" class="form-control">
              </td>
              <td>
                <input type="text" name="${formsetPrefix}-${formCount}-PRIORANTIBIODOSAGE" class="form-control">
              </td>
              <td>
                <input type="text" name="${formsetPrefix}-${formCount}-PRIORANTIBIOSTARTDTC" class="form-control datepicker">
              </td>
              <td>
                <input type="text" name="${formsetPrefix}-${formCount}-PRIORANTIBIOENDDTC" class="form-control datepicker">
              </td>
              <td>
                <input type="checkbox" class="delete-checkbox" data-formset="${formsetPrefix}" data-index="${formCount}">
                <input type="hidden" name="${formsetPrefix}-${formCount}-DELETE" id="id_${formsetPrefix}-${formCount}-DELETE">
              </td>
            </tr>
          `;
        } else if (formsetPrefix.includes('initial')) {
          newRow = `
            <tr class="antibiotic-form initial-antibiotic-form-row">
              <td>
                <input type="hidden" name="${formsetPrefix}-${formCount}-id" id="id_${formsetPrefix}-${formCount}-id">
                <input type="text" name="${formsetPrefix}-${formCount}-INITIALANTIBIONAME" class="form-control">
              </td>
              <td>
                <input type="text" name="${formsetPrefix}-${formCount}-INITIALANTIBIODOSAGE" class="form-control">
              </td>
              <td>
                <input type="text" name="${formsetPrefix}-${formCount}-INITIALANTIBIOSTARTDTC" class="form-control datepicker">
              </td>
              <td>
                <input type="text" name="${formsetPrefix}-${formCount}-INITIALANTIBIOENDDTC" class="form-control datepicker">
              </td>
              <td>
                <input type="checkbox" class="delete-checkbox" data-formset="${formsetPrefix}" data-index="${formCount}">
                <input type="hidden" name="${formsetPrefix}-${formCount}-DELETE" id="id_${formsetPrefix}-${formCount}-DELETE">
              </td>
            </tr>
          `;
        } else if (formsetPrefix.includes('main')) {
          newRow = `
            <tr class="antibiotic-form main-antibiotic-form-row">
              <td>
                <input type="hidden" name="${formsetPrefix}-${formCount}-id" id="id_${formsetPrefix}-${formCount}-id">
                <input type="text" name="${formsetPrefix}-${formCount}-MAINANTIBIONAME" class="form-control">
              </td>
              <td>
                <input type="text" name="${formsetPrefix}-${formCount}-MAINANTIBIODOSAGE" class="form-control">
              </td>
              <td>
                <input type="text" name="${formsetPrefix}-${formCount}-MAINANTIBIOSTARTDTC" class="form-control datepicker">
              </td>
              <td>
                <input type="text" name="${formsetPrefix}-${formCount}-MAINANTIBIOENDDTC" class="form-control datepicker">
              </td>
              <td>
                <input type="checkbox" class="delete-checkbox" data-formset="${formsetPrefix}" data-index="${formCount}">
                <input type="hidden" name="${formsetPrefix}-${formCount}-DELETE" id="id_${formsetPrefix}-${formCount}-DELETE">
              </td>
            </tr>
          `;
        }
      }
      
      // Thêm hàng mới vào bảng
      $(`#${formsetPrefix} tbody`).append(newRow);
      
      // Cập nhật số lượng form
      totalForms.val(formCount + 1);
      
      // Khởi tạo datepicker cho các trường mới
      $(`#${formsetPrefix} .datepicker`).datepicker({
        format: 'dd/mm/yyyy',
        autoclose: true,
        todayHighlight: true,
        language: 'vi'
      });
      
      // Xử lý checkbox xóa
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
    });
    
    // Xử lý các checkbox xóa đã có sẵn
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
  
  // Khởi tạo các formset handlers
  setupFormsetHandlers('prior-antibiotic-formset', '[data-formset="#prior-antibiotic-formset"]');
  setupFormsetHandlers('initial-antibiotic-formset', '[data-formset="#initial-antibiotic-formset"]');
  setupFormsetHandlers('main-antibiotic-formset', '[data-formset="#main-antibiotic-formset"]');
  setupFormsetHandlers('vasoidrug-formset', '[data-formset="#vasoidrug-formset"]');
  
  // Tab navigation với nút prev-page
  $('.prev-page').click(function() {
    var targetTab = $(this).data('target');
    $('#' + targetTab).tab('show');
  });
  
  // Khởi tạo trạng thái ban đầu dựa trên dữ liệu đã có
  // Hỗ trợ hô hấp
  if ($('#id_RESPISUPPORT').val() === 'true') {
    $('#respisupport_yes').prop('checked', true);
    $('#respi-support-options').show();
  } else if ($('#id_RESPISUPPORT').val() === 'false') {
    $('#respisupport_no').prop('checked', true);
  }
  
  // Dịch truyền hồi sức
  if ($('#id_RESUSFLUID').val() === 'true') {
    $('#resusfluid_yes').prop('checked', true);
    $('#resus-fluid-section').show();
  } else if ($('#id_RESUSFLUID').val() === 'false') {
    $('#resusfluid_no').prop('checked', true);
  }
  
  // Lọc máu
  if ($('#id_DIALYSIS').val() === 'true') {
    $('#dialysis_yes').prop('checked', true);
  } else if ($('#id_DIALYSIS').val() === 'false') {
    $('#dialysis_no').prop('checked', true);
  }
  
  // Dẫn lưu
  if ($('#id_DRAINAGE').val() === 'true') {
    $('#drainage_yes').prop('checked', true);
    $('#drainage_type_section').show();
    
    // Loại dẫn lưu
    var drainageType = $('#id_DRAINAGETYPE').val();
    if (drainageType) {
      $(`input[name="drainage_type_radio"][value="${drainageType}"]`).prop('checked', true);
      
      if (drainageType === 'Other') {
        $('#drainage_type_other').show();
      }
    }
  } else if ($('#id_DRAINAGE').val() === 'false') {
    $('#drainage_no').prop('checked', true);
  }
  
  // Nhiễm trùng huyết
  if ($('#id_BLOODINFECT').val() === 'true') {
    $('#sepsis_yes').prop('checked', true);
  } else if ($('#id_BLOODINFECT').val() === 'false') {
    $('#sepsis_no').prop('checked', true);
  } else {
    $('#sepsis_unknown').prop('checked', true);
  }
  
  // Sốc nhiễm trùng
  if ($('#id_SEPTICSHOCK').val() === 'true') {
    $('#septic_shock_yes').prop('checked', true);
  } else if ($('#id_SEPTICSHOCK').val() === 'false') {
    $('#septic_shock_no').prop('checked', true);
  } else {
    $('#septic_shock_unknown').prop('checked', true);
  }
  
  // Nguồn gốc nhiễm trùng
  var infectSrc = $('#id_INFECTSRC').val();
  if (infectSrc) {
    $(`input[name="infectsrc"][value="${infectSrc}"]`).prop('checked', true);
  }
  
  // Điều trị kháng sinh ban đầu phù hợp
  if ($('#id_INITIALABXAPPROP').val() === 'true') {
    $('#abx_approp_yes').prop('checked', true);
  } else if ($('#id_INITIALABXAPPROP').val() === 'false') {
    $('#abx_approp_no').prop('checked', true);
  } else {
    $('#abx_approp_unknown').prop('checked', true);
  }
  
  // Ổ nhiễm trùng 48h
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
  
  // Hỗ trợ hô hấp
  var supportType = $('#id_SUPPORTTYPE').val();
  if (supportType) {
    var types = supportType.split(',');
    types.forEach(function(type) {
      $(`input[name="support_type[]"][value="${type}"]`).prop('checked', true);
    });
    
    // Thời gian hỗ trợ
    $('input[name="oxygen_days"]').val($('#id_OXYMASKDURATION').val());
    $('input[name="hfnc_days"]').val($('#id_HFNCNIVDURATION').val());
    $('input[name="ventilator_days"]').val($('#id_VENTILATORDURATION').val());
  }

  if (document.querySelector('form[data-read-only="true"]')) {
  // Vô hiệu hóa tương tác
  document.querySelectorAll('input, select, textarea').forEach(element => {
    element.setAttribute('readonly', true);
    element.setAttribute('disabled', true);
  });
  
  // Vô hiệu hóa tương tác với radio buttons và checkboxes
  document.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(element => {
    element.setAttribute('onclick', 'return false;');
  });
  
  // Ẩn các nút thêm/xóa
  document.querySelectorAll('.add-row, .remove-row').forEach(button => {
    button.style.display = 'none';
  });
}
// Xử lý chế độ read-only
if (isReadOnly || document.querySelector('form[data-read-only="true"]')) {
  // Vô hiệu hóa tất cả input, select, textarea
  document.querySelectorAll('input, select, textarea').forEach(element => {
    element.setAttribute('readonly', true);
    element.setAttribute('disabled', true);
  });
  
  // Vô hiệu hóa radio và checkbox
  document.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(element => {
    element.setAttribute('onclick', 'return false;');
  });
  
  // Ẩn các nút thêm/xóa
  document.querySelectorAll('.add-row, .remove-row').forEach(button => {
    button.style.display = 'none';
  });
  
  // Ẩn nút submit
  document.querySelectorAll('button[type="submit"]').forEach(button => {
    button.style.display = 'none';
  });
}
});
