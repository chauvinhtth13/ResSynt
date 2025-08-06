/**
 * enrollment-form.js
 * Xử lý tất cả chức năng và logic cho form nhập thông tin bệnh nhân 43EN
 */

// Template HTML cho medication row - thêm template này để tách khỏi HTML
const medicationRowTemplate = `
  <tr data-row-index="\${rowIndex}">
    <td>
      <input type="text" name="MEDICATION_NAME_\${rowIndex}" class="form-control form-control-sm" placeholder="Tên thuốc">
    </td>
    <td>
      <input type="text" name="MEDICATION_DOSAGE_\${rowIndex}" class="form-control form-control-sm" placeholder="Liều dùng">
    </td>
    <td>
      <input type="text" name="MEDICATION_DURATION_\${rowIndex}" class="form-control form-control-sm" placeholder="Thời gian">
    </td>
    <td>
      <div class="d-flex">
        <input type="text" name="MEDICATION_REASON_\${rowIndex}" class="form-control form-control-sm mr-2" placeholder="Lý do">
        <button type="button" class="btn btn-sm btn-danger remove-medication-row">
          <i class="fas fa-trash"></i>
        </button>
      </div>
    </td>
  </tr>
`;

// Khởi tạo các biến và sự kiện cho form khi DOM đã sẵn sàng
$(document).ready(function() {
  // Khởi tạo DatePicker cho tất cả các trường ngày (bao gồm trường ngày tuyển bệnh)
  $('.date input').each(function() {
    var $input = $(this);
    var dateValue = $input.val();
    var initialDate = null;
    
    // Pre-process the date value to ensure it's either empty or a valid date string
    if (dateValue && dateValue !== '' && dateValue !== 'Invalid date') {
      if (dateValue.indexOf('/') > -1) {
        // Already in DD/MM/YYYY format
        var dateParts = dateValue.split('/');
        if (dateParts.length === 3) {
          var day = parseInt(dateParts[0], 10);
          var month = parseInt(dateParts[1], 10) - 1; // JS months are 0-based
          var year = parseInt(dateParts[2], 10);
          initialDate = new Date(year, month, day);
        }
      } else {
        // Try to parse as a JavaScript date
        var parsedDate = new Date(dateValue);
        if (!isNaN(parsedDate.getTime())) {
          initialDate = parsedDate;
        }
      }
    }
    
    // Initialize daterangepicker with the properly parsed date
    $input.daterangepicker({
      singleDatePicker: true,
      locale: {
        format: 'DD/MM/YYYY'
      },
      autoUpdateInput: true,
      showDropdowns: true,
      minYear: 1900,
      maxYear: (new Date()).getFullYear(),
      startDate: initialDate || moment()
    });
    
    // Format the value correctly right after initialization
    if (initialDate) {
      var day = String(initialDate.getDate()).padStart(2, '0');
      var month = String(initialDate.getMonth() + 1).padStart(2, '0');
      var year = initialDate.getFullYear();
      $input.val(day + '/' + month + '/' + year);
    } else if (dateValue === 'Invalid date' || dateValue === '') {
      $input.val(''); // Clear invalid values
    }
  });
    // Handle date of birth picker riêng biệt - chỉ khởi tạo nếu chưa được xử lý bởi birth-date-handler.js
  console.log("enrollment-form.js: Checking dateOfBirth initialization conditions");
  console.log("dateOfBirth has daterangepicker:", $('#dateOfBirth').data('daterangepicker'));
  console.log("birthDateHandlerLoaded:", window.birthDateHandlerLoaded);
  console.log("Should initialize dateOfBirth:", !$('#dateOfBirth').data('daterangepicker') && !window.birthDateHandlerLoaded);
  
  if (!$('#dateOfBirth').data('daterangepicker') && !window.birthDateHandlerLoaded) {
    console.log("enrollment-form.js: Initializing dateOfBirth picker");
    console.log("Initializing dateOfBirth picker from enrollment-form.js");
    $('#dateOfBirth').daterangepicker({
      singleDatePicker: true,
      locale: {
        format: 'DD/MM/YYYY'
      },
      autoUpdateInput: true,
      showDropdowns: true,
      minYear: 1900,
      maxYear: (new Date()).getFullYear()
    });
    
    // Set initial value for date of birth if values exist
    var day = $('#id_DAYOFBIRTH').val();
    var month = $('#id_MONTHOFBIRTH').val();
    var year = $('#id_YEAROFBIRTH').val();
    
    // Check if values exist and are valid numbers
    if (day && month && year && 
        !isNaN(parseInt(day)) && !isNaN(parseInt(month)) && !isNaN(parseInt(year))) {
      // Convert to integers first to ensure valid values
      const dayValue = parseInt(day, 10);
      const monthValue = parseInt(month, 10);
      const yearValue = parseInt(year, 10);
      
      // Validate ranges
      if (dayValue >= 1 && dayValue <= 31 && 
          monthValue >= 1 && monthValue <= 12 && 
          yearValue >= 1900 && yearValue <= new Date().getFullYear()) {
        // Format with leading zeros for display
        const formattedDay = String(dayValue).padStart(2, '0');
        const formattedMonth = String(monthValue).padStart(2, '0');
        $('#dateOfBirth').val(`${formattedDay}/${formattedMonth}/${yearValue}`);
        
        // Update hidden fields with integer values
        $('#id_DAYOFBIRTH').val(dayValue);
        $('#id_MONTHOFBIRTH').val(monthValue);
        $('#id_YEAROFBIRTH').val(yearValue);
      } else {
        // Clear the field if values are out of range
        $('#dateOfBirth').val('');
        $('#id_DAYOFBIRTH').val('');
        $('#id_MONTHOFBIRTH').val('');
        $('#id_YEAROFBIRTH').val('');
      }
    } else {
      // Clear the field if we have invalid values
      $('#dateOfBirth').val('');
    }
  }
    // Update hidden fields when date is selected - chỉ xử lý nếu chưa có event handler từ birth-date-handler.js
  console.log("enrollment-form.js: Checking dateOfBirth event handler conditions");
  var events = $._data($('#dateOfBirth')[0], 'events');
  console.log("dateOfBirth events:", events);
  console.log("Has apply.daterangepicker events:", events && events['apply.daterangepicker']);
  console.log("birthDateHandlerLoaded for events:", window.birthDateHandlerLoaded);
  console.log("Should add event handlers:", (!events || !events['apply.daterangepicker']) && !window.birthDateHandlerLoaded);
  
  if ((!$._data($('#dateOfBirth')[0], 'events') || !$._data($('#dateOfBirth')[0], 'events')['apply.daterangepicker']) && !window.birthDateHandlerLoaded) {
    console.log("enrollment-form.js: Adding dateOfBirth event handlers");
    $('#dateOfBirth').on('apply.daterangepicker', function(ev, picker) {
      // Update display format with leading zeros
      $(this).val(picker.startDate.format('DD/MM/YYYY'));
      
      // Update hidden fields with integer values (no leading zeros)
      const day = parseInt(picker.startDate.format('D'), 10);
      const month = parseInt(picker.startDate.format('M'), 10);
      const year = parseInt(picker.startDate.format('YYYY'), 10);
      
      $('#id_DAYOFBIRTH').val(day);
      $('#id_MONTHOFBIRTH').val(month);
      $('#id_YEAROFBIRTH').val(year);
      
      console.log("Date of birth updated from enrollment-form.js:", day, month, year);
    });
  }
  
  // Xử lý các trường ngày tháng khác để đảm bảo hiển thị đúng
  $('.date input').on('apply.daterangepicker', function(ev, picker) {
    $(this).val(picker.startDate.format('DD/MM/YYYY'));
  }).on('cancel.daterangepicker', function(e, picker) {
    $(this).val('');
  }).on('error.daterangepicker', function(e, picker) {
    $(this).val('');
  });
  
  // Đảm bảo hiển thị ban đầu của tất cả các trường ngày tháng
  $('.date input').each(function() {
    var $input = $(this);
    var dateValue = $input.val();
    
    // Xử lý trường hợp "Invalid date"
    if (dateValue === 'Invalid date') {
      $input.val('');
      return;
    }
    
    if (dateValue && dateValue.trim() !== '') {
      // Nếu giá trị đã tồn tại nhưng không đúng định dạng, định dạng lại
      if (dateValue.indexOf('/') === -1) {
        var date = new Date(dateValue);
        if (!isNaN(date.getTime())) {
          var day = String(date.getDate()).padStart(2, '0');
          var month = String(date.getMonth() + 1).padStart(2, '0');
          var year = date.getFullYear();
          $input.val(day + '/' + month + '/' + year);
        } else {
          // Nếu không parse được thành công, xóa giá trị không hợp lệ
          $input.val('');
        }
      }
    }
  });
  
  // ====== Toggle cho các phần thông tin ======
  
  // 1. Chuyển từ bệnh viện khác
  function togglePreviousHospital() {
    if($('#id_FROMOTHERHOSPITAL').is(':checked')) {
      $('#previous_hospital_info').slideDown(300);
    } else {
      $('#previous_hospital_info').slideUp(300);
      // Reset các giá trị
      $('#previous_hospital_info input').val('');
    }
  }
  
  $('#id_FROMOTHERHOSPITAL').on('change', togglePreviousHospital);
  
  // Kích hoạt kiểm tra ban đầu
  togglePreviousHospital();
  
  // 2. Dân tộc khác
  function toggleOtherEthnicity() {
    if($('#id_ETHNICITY').val() === 'Other') {
      $('#other_ethnicity_row').slideDown(300);
    } else {
      $('#other_ethnicity_row').slideUp(300);
      $('#id_SPECIFYIFOTHERETHNI').val('');
    }
  }
  
  $('#id_ETHNICITY').on('change', toggleOtherEthnicity);
  
  // Kích hoạt kiểm tra ban đầu
  toggleOtherEthnicity();
  
  // 3. Bệnh nền
  function toggleUnderlyingConditions() {
    if($('#id_UNDERLYINGCONDS').is(':checked')) {
      $('#conditions_container').removeClass('hidden').slideDown(300);
    } else {
      $('#conditions_container').slideUp(300, function() {
        // Reset tất cả các checkbox của bệnh nền
        $('#conditions_container input[type="checkbox"]').prop('checked', false);
        $('#other_disease_detail').hide();
        $('#id_OTHERDISEASESPECIFY').val('');
      });
    }
  }
  
  $('#id_UNDERLYINGCONDS').on('change', toggleUnderlyingConditions);
  
  // Initialize tooltips for checkboxes
  $('.form-check-label, .risk-factor-label').tooltip({
    placement: 'top',
    trigger: 'hover'
  });
  
  // Handle custom checkboxes
  $('.custom-checkbox input[type="checkbox"]').on('change', function() {
    if ($(this).is(':checked')) {
      $(this).closest('.risk-factor-item').addClass('active');
    } else {
      $(this).closest('.risk-factor-item').removeClass('active');
    }
  });
  
  // Initialize active state for checked checkboxes
  $('.custom-checkbox input[type="checkbox"]:checked').each(function() {
    $(this).closest('.risk-factor-item').addClass('active');
  });
  
  // Kích hoạt kiểm tra ban đầu
  toggleUnderlyingConditions();
  
  // 4. Bệnh khác
  function toggleOtherDisease() {
    if($('#id_OTHERDISEASE').is(':checked')) {
      $('#other_disease_detail').slideDown(300);
    } else {
      $('#other_disease_detail').slideUp(300);
      $('#id_OTHERDISEASESPECIFY').val('');
    }
  }
  
  $('#id_OTHERDISEASE').on('change', toggleOtherDisease);
  
  // Kích hoạt kiểm tra ban đầu
  toggleOtherDisease();
  
  // Toggle Medication History table when CORTICOIDPPI checkbox is changed
  function toggleMedicationHistory() {
    if ($('#id_CORTICOIDPPI').is(':checked')) {
      $('#medication_history_container').slideDown(300);
      
      // Initialize with data if the table is empty
      if ($('#medication_history_table tbody tr').length === 0) {
        // Add an initial empty row
        addMedicationRow();
      }
    } else {
      $('#medication_history_container').slideUp(300);
    }
  }
  
  $('#id_CORTICOIDPPI').on('change', toggleMedicationHistory);
  
  // Activate the check initially
  toggleMedicationHistory();
  
  // Function to add a new medication row
  $('#add_medication_row').on('click', function() {
    addMedicationRow();
  });
  // Function to create a new medication row
  function addMedicationRow() {
    var rowIndex = $('#medication_history_table tbody tr').length;
    
    // Sử dụng template từ HTML template nếu có, ngược lại sử dụng template JS
    var newRow;
    if ($('#medication_row_template').length > 0) {
      newRow = $('#medication_row_template').html().replace(/\${rowIndex}/g, rowIndex);
    } else {
      // Fallback to the JS template nếu không tìm thấy template trong HTML
      newRow = medicationRowTemplate.replace(/\${rowIndex}/g, rowIndex);
    }
    
    $('#medication_history_table tbody').append(newRow);
    
    // Update the hidden field with the total number of medication rows
    updateMedicationCount();
  }
  
  // Remove a medication row
  $(document).on('click', '.remove-medication-row', function() {
    $(this).closest('tr').remove();
    updateMedicationCount();
    
    // Reindex the rows
    $('#medication_history_table tbody tr').each(function(index) {
      $(this).attr('data-row-index', index);
      $(this).find('input').each(function() {
        var name = $(this).attr('name');
        var newName = name.replace(/\d+$/, index);
        $(this).attr('name', newName);
      });
    });
  });
  
  // Update the count of medication entries
  function updateMedicationCount() {
    var count = $('#medication_history_table tbody tr').length;
    
    // If we're tracking count in a hidden field
    if ($('#id_MEDICATION_COUNT').length === 0) {
      $('<input>').attr({
        type: 'hidden',
        id: 'id_MEDICATION_COUNT',
        name: 'MEDICATION_COUNT',
        value: count
      }).appendTo('#enrollmentForm');
    } else {
      $('#id_MEDICATION_COUNT').val(count);
    }
  }
  
  // ====== Các hành vi tương tác khác ======
  
  // Highlight trường bắt buộc
  $('input[required], select[required], textarea[required]').closest('.form-group').addClass('required-field');
  
  // Hiệu ứng focus
  $('.form-control, .form-select').focus(function() {
    $(this).closest('.form-group').addClass('border-primary').css('padding', '5px');
  }).blur(function() {
    $(this).closest('.form-group').removeClass('border-primary').css('padding', '0');
  });
  
  // Xử lý button group cho radio button
  $('.btn-group-toggle .btn').click(function() {
    var btnGroup = $(this).closest('.btn-group-toggle');
    btnGroup.find('.btn').removeClass('active');
    $(this).addClass('active');
    
    // Đảm bảo radio button được chọn
    var radioInput = $(this).find('input[type="radio"]');
    radioInput.prop('checked', true).trigger('change');
  });
  
  // Tooltip cho các trường dữ liệu
  $('[data-toggle="tooltip"]').tooltip();
  
  // Animation khi hiển thị/ẩn card
  $('.card-header .btn-tool').click(function() {
    var icon = $(this).find('i');
    
    if(icon.hasClass('fa-minus')) {
      icon.removeClass('fa-minus').addClass('fa-plus');
    } else {
      icon.removeClass('fa-plus').addClass('fa-minus');
    }
  });
  
  // Đảm bảo tất cả các phần đều được mở khi tải trang
  $('.card-body').show();
  $('.card-header .btn-tool i').removeClass('fa-plus').addClass('fa-minus');
  
  // Nút reset form với xác nhận
  $('button[type="reset"]').click(function(e) {
    e.preventDefault();
    
    if(confirm('Bạn có chắc muốn xóa tất cả thông tin đã nhập?')) {
      $('#enrollmentForm')[0].reset();
      
      // Trigger các sự kiện change để cập nhật UI
      $('#id_FROMOTHERHOSPITAL, #id_UNDERLYINGCONDS, #id_OTHERDISEASE').trigger('change');
      $('#id_ETHNICITY').trigger('change');
      
      // Reset các button radio
      $('.btn-group-toggle .btn').removeClass('active');
      $('.btn-group-toggle .btn:first-child').addClass('active');
    }
  });
  
      // Thêm trình xử lý riêng cho trường ngày tuyển bệnh để đảm bảo không hiển thị 'Invalid date'
    // Chỉ khởi tạo nếu chưa được khởi tạo bởi template và chưa được xử lý bởi birth-date-handler
    console.log("enrollment-form.js: Checking ENRDATE initialization conditions");
    console.log("ENRDATE has daterangepicker:", $('#id_ENRDATE').data('daterangepicker'));
    console.log("birthDateHandlerLoaded for ENRDATE:", window.birthDateHandlerLoaded);
    console.log("Should initialize ENRDATE:", !$('#id_ENRDATE').data('daterangepicker') && !window.birthDateHandlerLoaded);
    
    if (!$('#id_ENRDATE').data('daterangepicker') && !window.birthDateHandlerLoaded) {
      console.log("enrollment-form.js: Initializing ENRDATE picker");
    var enrDateValue = $('#id_ENRDATE').val();
    var initialDate = null;
    
    // Xử lý giá trị ban đầu
    if (enrDateValue && enrDateValue !== '' && enrDateValue !== 'Invalid date') {
      if (enrDateValue.indexOf('/') > -1) {
        // Đã ở định dạng DD/MM/YYYY
        var dateParts = enrDateValue.split('/');
        if (dateParts.length === 3) {
          var day = parseInt(dateParts[0], 10);
          var month = parseInt(dateParts[1], 10) - 1; // JS months are 0-based
          var year = parseInt(dateParts[2], 10);
          initialDate = new Date(year, month, day);
        }
      } else {
        // Thử parse như JavaScript date
        var parsedDate = new Date(enrDateValue);
        if (!isNaN(parsedDate.getTime())) {
          initialDate = parsedDate;
        }
      }
    }
    
    $('#id_ENRDATE').daterangepicker({
      singleDatePicker: true,
      locale: {
        format: 'DD/MM/YYYY'
      },
      autoUpdateInput: true,
      showDropdowns: true,
      minYear: 1900,
      maxYear: (new Date()).getFullYear(),
      startDate: initialDate || moment()
    }).on('apply.daterangepicker', function(e, picker) {
      $(this).val(picker.startDate.format('DD/MM/YYYY'));
    }).on('cancel.daterangepicker', function(e, picker) {
      $(this).val('');
    }).on('error', function(e) {
      $(this).val('');
    });
  }
  
  // Đảm bảo rằng trường ngày tuyển bệnh được hiển thị đúng khi tải trang
  var enrDateValue = $('#id_ENRDATE').val();
  if (enrDateValue === 'Invalid date') {
    $('#id_ENRDATE').val('');
  } else if (enrDateValue && enrDateValue.indexOf('/') === -1) {
    try {
      var date = new Date(enrDateValue);
      if (!isNaN(date.getTime())) {
        $('#id_ENRDATE').val(date.getDate().toString().padStart(2, '0') + '/' + 
                            (date.getMonth() + 1).toString().padStart(2, '0') + '/' + 
                            date.getFullYear());
      } else {
        $('#id_ENRDATE').val('');
      }
    } catch(e) {
      $('#id_ENRDATE').val('');
    }
  }
  
  // Khởi tạo hiển thị điều kiện trong DOM ready (tránh nested ready)
  initializeConditionalDisplays();
});

// Khởi tạo hiển thị điều kiện (tách ra để tránh lồng $(document).ready)
function initializeConditionalDisplays() {
  // Kích hoạt tất cả các kiểm tra ban đầu cho các phần điều kiện
  if ($('#id_UNDERLYINGCONDS').is(':checked')) {
    $('#conditions_container').removeClass('hidden').show();
  }
  
  if ($('#id_OTHERDISEASE').is(':checked')) {
    $('#other_disease_detail').show();
  }
  
  if ($('#id_FROMOTHERHOSPITAL').is(':checked')) {
    $('#previous_hospital_info').show();
  }
  
  if ($('#id_CORTICOIDPPI').is(':checked')) {
    $('#medication_history_container').show();
  }
  
  if ($('#id_ETHNICITY').val() === 'Other') {
    $('#other_ethnicity_row').show();
  }
}

// Gán giá trị screeningCaseId vào biến toàn cục window
function setScreeningCaseId(id) {
  // Sử dụng biến toàn cục window để tránh khai báo trùng lặp
  if (typeof window.screeningCaseId === 'undefined') {
    window.screeningCaseId = id;
  }
  console.log("Initialized screeningCaseId:", window.screeningCaseId);
}
