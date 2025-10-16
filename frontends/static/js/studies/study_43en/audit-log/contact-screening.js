$(document).ready(function() {
  console.log("contact-screening.js loaded");
  console.log("Form exists:", $('#contactScreeningForm').length > 0);
  console.log("window.isReadonly:", window.isReadonly);
  
  // Chỉ xử lý nếu không phải readonly
  if ($('#contactScreeningForm').length && !window.isReadonly) {
    console.log("Initializing form handling for contact screening");
    const $form = $('#contactScreeningForm');
    
    // Ensure all form fields have data-initial-value attribute set properly
    function captureInitialValues() {
      console.log("Capturing initial values for all form fields");
      
      // Regular inputs, selects, and textareas
      $form.find('input[type="text"], input[type="date"], select, textarea').each(function() {
        const name = $(this).attr('name');
        if (name && name !== 'csrfmiddlewaretoken') {
          if (!$(this).attr('data-initial-value')) {
            const value = $(this).val() || '';
            $(this).attr('data-initial-value', value);
            console.log(`Set initial value for ${name}: "${value}"`);
          }
        }
      });
      
      // Checkboxes
      $form.find('input[type="checkbox"]').each(function() {
        const name = $(this).attr('name');
        if (name && !$(this).attr('data-initial-value')) {
          const value = $(this).prop('checked') ? '1' : '0';
          $(this).attr('data-initial-value', value);
          console.log(`Set initial value for checkbox ${name}: "${value}"`);
        }
      });
      
      // Radio buttons
      const radioFields = ['LIVEIN5DAYS3MTHS', 'MEALCAREONCEDAY', 'CONSENTTOSTUDY'];
      radioFields.forEach(fieldName => {
        const checkedRadio = $(`input[name="${fieldName}"]:checked`);
        if (checkedRadio.length && !checkedRadio.attr('data-initial-value')) {
          const value = checkedRadio.val();
          $(`input[name="${fieldName}"]`).attr('data-initial-value', ''); // Reset all in group
          checkedRadio.attr('data-initial-value', value);
          console.log(`Set initial value for radio ${fieldName}: "${value}"`);
        } else if (!checkedRadio.length) {
          // If no radio is checked, set default to '0'
          $(`input[name="${fieldName}"]`).attr('data-initial-value', '');
          console.log(`No radio checked for ${fieldName}, all set to empty initial value`);
        }
      });
    }
    
    // Run the initial value capture when page loads
    captureInitialValues();
    
    // Check if this is a new record
    const isNewRecord = !$form.find('input[name="SCRID"]').val() || 
                        $form.find('input[name="SCRID"]').val().trim() === '';
    
    console.log("Checking if new record:", isNewRecord);
    console.log("SCRID value:", $form.find('input[name="SCRID"]').val());

    // Định nghĩa các labels cho các trường
    const fieldLabels = {
      SCRID: "Mã sàng lọc",
      USUBJID: "USUBJID",
      SITEID: "Mã cơ sở",
      INITIAL: "Viết tắt",
      SUBJIDENROLLSTUDY: "Bệnh nhân liên quan",
      LIVEIN5DAYS3MTHS: "Sống chung ít nhất 5 ngày trong 3 tháng",
      MEALCAREONCEDAY: "Ăn cùng/chăm sóc ít nhất 1 lần/ngày",
      CONSENTTOSTUDY: "Đồng ý tham gia nghiên cứu",
      SCREENINGFORMDATE: "Ngày sàng lọc",
      COMPLETEDBY: "Người hoàn thành",
      COMPLETEDDATE: "Ngày hoàn thành",
      is_confirmed: "Đã xác nhận"
    };
    const fieldTypes = {}; // Nếu cần, bổ sung sau
    const fieldOptions = {}; // Nếu cần, bổ sung sau

    // Lấy initial data
    const initialData = {};
    
    if (isNewRecord) {
      console.log("This is a new record - setting all initial values to empty");
      // For new records, all initial values should be empty
      $form.find('input[type="text"], input[type="date"], select, textarea').each(function() {
        const name = $(this).attr('name');
        if (name && name !== 'csrfmiddlewaretoken') {
          initialData[name] = '';
          // Update the data-initial-value attribute to empty for consistency
          $(this).attr('data-initial-value', '');
        }
      });
    } else {
      console.log("This is an existing record - extracting initial values");
      // For existing records, use data-initial-value attributes or value
      $form.find('input[type="text"], input[type="date"], select, textarea').each(function() {
        const name = $(this).attr('name');
        if (name && name !== 'csrfmiddlewaretoken') {
          // For bootstrap_field generated inputs, we need to capture values differently
          // First try data-initial-value, if not set, try value as fallback
          let initialValue = '';
          
          if ($(this).attr('data-initial-value')) {
            initialValue = $(this).attr('data-initial-value').trim();
            console.log(`Found data-initial-value for ${name}: "${initialValue}"`);
          } else {
            initialValue = ($(this).val() || '').trim();
            console.log(`Using value for ${name}: "${initialValue}"`);
            // Store it as data-initial-value for consistency
            $(this).attr('data-initial-value', initialValue);
          }
          
          // Special handling for select fields
          if ($(this).is('select')) {
            console.log(`${name} is a select field with value: ${initialValue}`);
            if (name === 'SUBJIDENROLLSTUDY') {
              // Make sure to properly capture the SUBJIDENROLLSTUDY value
              const selectedText = $(this).find('option:selected').text();
              console.log(`SUBJIDENROLLSTUDY selected text: ${selectedText}`);
            }
          }
          
          initialData[name] = initialValue;
        }
      });
    }

    // Xử lý checkbox
    $form.find('input[type="checkbox"]').each(function() {
      const name = $(this).attr('name');
      if (name) {
        if (isNewRecord) {
          initialData[name] = '0'; // Default to unchecked for new records
          $(this).attr('data-initial-value', '0');
        } else {
          let initialValue;
          if ($(this).attr('data-initial-value')) {
            initialValue = $(this).attr('data-initial-value').trim();
          } else {
            initialValue = $(this).prop('checked') ? '1' : '0';
            $(this).attr('data-initial-value', initialValue);
          }
          initialData[name] = initialValue;
          console.log(`Checkbox ${name} initial value: ${initialValue}`);
        }
      }
    });

    // Xử lý radio buttons
    const radioFields = ['LIVEIN5DAYS3MTHS', 'MEALCAREONCEDAY', 'CONSENTTOSTUDY'];
    radioFields.forEach(fieldName => {
      if (isNewRecord) {
        initialData[fieldName] = ''; // Empty initial value for new records
        $(`input[name="${fieldName}"]`).attr('data-initial-value', '');
      } else {
        const checkedRadio = $(`input[name="${fieldName}"]:checked`);
        if (checkedRadio.length) {
          let initialValue;
          if (checkedRadio.attr('data-initial-value')) {
            initialValue = checkedRadio.attr('data-initial-value').trim();
          } else {
            initialValue = checkedRadio.val();
            checkedRadio.attr('data-initial-value', initialValue);
          }
          initialData[fieldName] = initialValue;
          console.log(`Radio ${fieldName} initial value: ${initialValue}`);
        } else {
          // Nếu không có tùy chọn nào được chọn, đặt giá trị mặc định là '0'
          initialData[fieldName] = '0';
          console.log(`Radio ${fieldName} has no checked option, setting default value: 0`);
        }
      }
    });

    $form.on('submit', function(e) {
      console.log("Form submission detected");
      const formData = {};
      
      // First get all standard form values
      $form.serializeArray().forEach(function(item) {
        if (item.name !== 'csrfmiddlewaretoken') {
          formData[item.name] = item.value.trim();
        }
      });
      
      // Handle checkboxes - they don't appear in serializeArray() when unchecked
      $form.find('input[type="checkbox"]').each(function() {
        const name = $(this).attr('name');
        if (name) {
          formData[name] = $(this).prop('checked') ? '1' : '0';
        }
      });
      
      // Handle radio buttons - make sure they always have a value even if none selected
      radioFields.forEach(fieldName => {
        const checkedRadio = $(`input[name="${fieldName}"]:checked`);
        if (checkedRadio.length) {
          formData[fieldName] = checkedRadio.val();
        } else if (!formData[fieldName]) {
          // Default to "0" if no option selected
          formData[fieldName] = '0';
        }
      });

      // Special handling for select fields
      $form.find('select').each(function() {
        const name = $(this).attr('name');
        if (name) {
          const value = $(this).val();
          formData[name] = value || '';
          
          // Debug logging for select fields
          console.log(`Select field ${name} value: ${value}`);
          if ($(this).find('option:selected').length) {
            console.log(`${name} selected text: ${$(this).find('option:selected').text()}`);
          }
        }
      });

      // Special handling for SUBJIDENROLLSTUDY select field
      const subjidField = $form.find('select[name="SUBJIDENROLLSTUDY"]');
      if (subjidField.length && !isNewRecord) {
        // For select fields with bootstrap_field, we need to ensure we have the correct initial value
        const subjidFieldValue = subjidField.val();
        if (subjidFieldValue) {
          console.log(`SUBJIDENROLLSTUDY current value: ${subjidFieldValue}`);
          const subjidFieldText = subjidField.find('option:selected').text();
          console.log(`SUBJIDENROLLSTUDY selected text: ${subjidFieldText}`);
          
          if (!subjidField.attr('data-initial-value')) {
            subjidField.attr('data-initial-value', subjidFieldValue);
            console.log(`Set data-initial-value for SUBJIDENROLLSTUDY to: ${subjidFieldValue}`);
          }
          
          // Make sure it's in the initialData
          initialData['SUBJIDENROLLSTUDY'] = subjidField.attr('data-initial-value');
        }
      }
    
    console.log("Initial data collected:", initialData);
      console.log("Form data:", formData);
      console.log("Is new record:", isNewRecord);
      
      // Extra check for debugging purposes - show all form fields with their old/new values
      console.log("=== FULL FIELD COMPARISON ===");
      const allFields = new Set([...Object.keys(initialData), ...Object.keys(formData)]);
      allFields.forEach(field => {
        if (field !== 'csrfmiddlewaretoken' && field !== 'oldDataJson' && 
            field !== 'newDataJson' && field !== 'change_reason' && field !== 'reasons_json') {
          const oldVal = initialData[field] || '';
          const newVal = formData[field] || '';
          console.log(`${field}: "${oldVal}" -> "${newVal}" ${oldVal !== newVal ? '(CHANGED)' : ''}`);
        }
      });
      console.log("============================");

      // So sánh dữ liệu để tìm các trường thay đổi
      const changedFields = {};
      
      // If this is a new record and there's data in the form, consider all non-empty fields as changed
      if (isNewRecord) {
        console.log("Processing as new record - all non-empty fields will be considered as changed");
        for (const key in formData) {
          const newValue = (formData[key] === undefined || formData[key] === null) ? '' : formData[key].toString().trim();
          if (newValue !== '' && key !== 'csrfmiddlewaretoken') {
            changedFields[key] = {
              old: '',
              new: formData[key],
              label: fieldLabels[key] || key,
              type: fieldTypes[key] || 'text',
              options: fieldOptions[key] || {}
            };
          }
        }
      } else {
        // Normal change detection for existing records
        console.log("Processing as existing record - comparing old and new values");
        for (const key in formData) {
          if (key !== 'csrfmiddlewaretoken' && key !== 'oldDataJson' && key !== 'newDataJson' && 
              key !== 'change_reason' && key !== 'reasons_json') {
            
            const oldValue = initialData.hasOwnProperty(key) ? 
                             (initialData[key] === undefined || initialData[key] === null) ? '' : initialData[key].toString().trim() : '';
            const newValue = (formData[key] === undefined || formData[key] === null) ? '' : formData[key].toString().trim();
            
            console.log(`Comparing ${key}: Old="${oldValue}" -> New="${newValue}"`);
            
            if (oldValue !== newValue) {
              changedFields[key] = {
                old: initialData[key] || '',
                new: formData[key],
                label: fieldLabels[key] || key,
                type: fieldTypes[key] || 'text',
                options: fieldOptions[key] || {}
              };
              console.log(`Field ${key} changed: "${oldValue}" -> "${newValue}"`);
            }
          }
        }
      }

      console.log("Changed fields:", changedFields);
      console.log("Number of changed fields:", Object.keys(changedFields).length);

      // Debug output of changed fields for better visibility
      if (Object.keys(changedFields).length > 0) {
        console.log("=== CHANGED FIELDS SUMMARY ===");
        Object.entries(changedFields).forEach(([field, data]) => {
          console.log(`${fieldLabels[field] || field}: "${data.old}" -> "${data.new}"`);
        });
        console.log("=============================");
      }

      if (Object.keys(changedFields).length > 0) {
        console.log("Changes detected, showing modal");
        e.preventDefault();
        $('#oldDataJson').val(JSON.stringify(Object.fromEntries(
          Object.entries(changedFields).map(([k, v]) => [k, v.old])
        )));
        $('#newDataJson').val(JSON.stringify(Object.fromEntries(
          Object.entries(changedFields).map(([k, v]) => [k, v.new])
        )));

        // Hiển thị modal nhập lý do thay đổi
        AuditLogBase.showChangeModal(changedFields, function(reasonsData) {
          console.log("Modal callback received", reasonsData);
          const reasonsJsonWithLabel = {};
          Object.keys(changedFields).forEach(key => {
            if (typeof reasonsData[key] === 'string') {
              reasonsJsonWithLabel[key] = {
                label: changedFields[key].label || key,
                reason: reasonsData[key]
              };
            } else if (typeof reasonsData[key] === 'object' && reasonsData[key] !== null) {
              reasonsJsonWithLabel[key] = reasonsData[key];
            }
          });

          $('#reasons_json').val(JSON.stringify(reasonsJsonWithLabel));
          const changeReason = Object.entries(reasonsJsonWithLabel)
            .map(([field, obj]) => {
              const label = obj.label || field;
              return `${label}: ${obj.reason}`;
            })
            .join(' | ');
          $('#change_reason').val(changeReason);
          
          console.log("Preparing to submit form");
          
          // Show saving feedback to the user
          $('#submitButton').prop('disabled', true).html('<i class="fas fa-spinner fa-spin mr-1"></i> Đang lưu...');
          
          // Flag to track submission success
          let submitted = false;
          
          // Try first method - jQuery off + submit
          try {
            $form.off('submit').submit();
            console.log("Form submitted via jQuery off+submit");
            submitted = true;
          } catch(e) {
            console.error("jQuery off+submit failed:", e);
          }
          
          // If first method failed, try vanilla JS submit
          if (!submitted) {
            try {
              document.getElementById('contactScreeningForm').submit();
              console.log("Form submitted via vanilla JS");
              submitted = true;
            } catch(e2) {
              console.error("Vanilla JS submit failed:", e2);
            }
          }
          
          // Last resort - click the submit button
          if (!submitted) {
            try {
              setTimeout(function() {
                console.log("Attempting button click submission");
                $('#submitButton').trigger('click');
                console.log("Form submitted via button click");
              }, 100);
            } catch(e3) {
              console.error("Button click submit failed:", e3);
              // Ultra last resort - force form native submit
              try {
                console.log("Attempting native form submission");
                $form[0].submit();
              } catch(e4) {
                console.error("All submission methods failed:", e4);
                alert("Đã xảy ra lỗi khi lưu. Vui lòng thử lại hoặc liên hệ hỗ trợ.");
              }
            }
          }
        });
      } else {
        console.log("No changes detected, submitting form directly");
        // Allow the form to submit normally
        return true;
      }
    });
    
    // Add a fallback submission for any form that fails
    // This is added at the document level so it's never removed
    $(document).on('submit-fallback', '#contactScreeningForm', function(e) {
      console.log("Fallback submission triggered");
      
      // Directly submit the form using its native submit() method
      try {
        e.preventDefault();
        this.submit();
        console.log("Fallback submission successful");
      } catch(err) {
        console.error("Fallback submission failed:", err);
        alert("Could not submit form. Please try again or contact support.");
        $('#submitButton').prop('disabled', false).html('<i class="fas fa-save mr-1"></i> Lưu');
      }
    });
    
    // Handle the submit button click directly
    $('#submitButton').on('click', function(e) {
      console.log("Submit button clicked");
      // If the form doesn't submit within 5 seconds, trigger fallback
      setTimeout(function() {
        const form = document.getElementById('contactScreeningForm');
        if (form) {
          $(form).trigger('submit-fallback');
        }
      }, 5000);
    });
  }
});