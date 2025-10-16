// Enrollment Contact Form Audit Logging
// Tích hợp với base.js để ghi lại log cho enrollment contact form

window.EnrollmentContactAudit = {
  // Khởi tạo audit logging cho enrollment contact form
  init: function() {
    console.log("Initializing Enrollment Contact Form Audit Logging");

    // Kiểm tra xem form có tồn tại không
    const form = document.getElementById('enrollmentContactForm');
    if (!form) {
      console.warn("Enrollment contact form not found");
      return;
    }

    // Thiết lập các trường với data-initial-value
    this.setupInitialValues();

    // Thiết lập form submission handler
    this.setupFormSubmission();

    // Thiết lập các event handlers đặc biệt
    this.setupSpecialHandlers();

    console.log("Enrollment Contact Form Audit Logging initialized successfully");
  },

  // Thiết lập giá trị ban đầu cho các trường
  setupInitialValues: function() {
    console.log("Setting up initial values for audit logging");

    // Kiểm tra xem form có tồn tại không
    const form = document.getElementById('enrollmentContactForm');
    if (!form) {
      console.error("Enrollment contact form not found for initial values setup");
      return;
    }

    // Lấy tất cả các trường input, select, textarea
    const fields = document.querySelectorAll('#enrollmentContactForm input:not([name="LISTUNDERLYING"]), #enrollmentContactForm select, #enrollmentContactForm textarea');
    console.log("Found", fields.length, "fields to set initial values for");

    fields.forEach(field => {
      const name = field.name;
      if (!name || name === 'csrfmiddlewaretoken') return;

      let initialValue = '';

      // Xử lý theo loại trường
      if (field.type === 'checkbox') {
          // Đảm bảo luôn là '1' hoặc '0'
          initialValue = field.checked ? '1' : '0';
      } else if (field.type === 'radio') {
          if (field.checked) {
            initialValue = field.value;
          } else {
            return;
          }
      } else if (field.tagName === 'SELECT') {
          initialValue = field.value || '';
      } else {
          initialValue = field.value || '';
      }

      // Lưu giá trị ban đầu
      field.setAttribute('data-initial-value', initialValue);
      console.log(`Field ${name}: initial value = "${initialValue}"`);
    });

    // Handle LISTUNDERLYING separately
    const listUnderlyingInput = document.getElementById('id_LISTUNDERLYING');
    if (listUnderlyingInput) {
      const initialValue = listUnderlyingInput.value || '[]';
      listUnderlyingInput.setAttribute('data-initial-value', initialValue);
      console.log(`LISTUNDERLYING: initial value = "${initialValue}"`);
      
      try {
        // Store the initial state of disease checkboxes based on LISTUNDERLYING
        const diseaseList = JSON.parse(initialValue);
        console.log("Initial disease list:", diseaseList);
      } catch (e) {
        console.error('Error parsing LISTUNDERLYING:', e);
      }
    }

    // Thiết lập initial values cho medication history
    this.setupMedicationInitialValues();
  },

  // Thiết lập initial values cho medication history
  setupMedicationInitialValues: function() {
    // Thiết lập cho các medication rows hiện tại
    const medicationRows = document.querySelectorAll('#medication_table tbody tr');
    medicationRows.forEach((row, index) => {
      const inputs = row.querySelectorAll('input');
      inputs.forEach(input => {
        const name = input.name;
        if (name) {
          const initialValue = input.value || '';
          input.setAttribute('data-initial-value', initialValue);
          console.log(`Medication field ${name}_${index}: initial value = "${initialValue}"`);
        }
      });
    });
  },

  // Thiết lập form submission handler
  setupFormSubmission: function() {
    const form = document.getElementById('enrollmentContactForm');
    console.log("Setting up form submission handler for:", form);

    form.addEventListener('submit', (e) => {
      console.log("Form submit event triggered");
      e.preventDefault();

      // Thu thập dữ liệu ban đầu
      const initialData = this.collectFormData(true);
      console.log("Initial data collected:", initialData);

      // Thu thập dữ liệu hiện tại
      const currentData = this.collectFormData(false);
      console.log("Current data collected:", currentData);

      // So sánh và tìm các trường thay đổi
      const changedFields = this.compareData(initialData, currentData);
      console.log("Changed fields detected:", changedFields);

      // Nếu có thay đổi, hiển thị modal để nhập lý do
      if (Object.keys(changedFields).length > 0) {
        console.log("Changes detected, showing modal");
        this.showChangeModal(changedFields, () => {
          console.log("Modal callback executed, submitting form");
          // Sau khi nhập lý do, submit form
          this.submitForm();
        });
      } else {
        // Không có thay đổi, submit trực tiếp
        console.log("No changes detected, submitting form");
        this.submitForm();
      }
    });
  },

  // Thu thập dữ liệu từ form
  collectFormData: function(useInitialValues = false) {
    const data = {};

    // Thu thập từ input fields (bao gồm cả medication history)
    const inputs = document.querySelectorAll('#enrollmentContactForm input:not([type="hidden"]):not([name="LISTUNDERLYING"])');
    inputs.forEach(input => {
      const name = input.name;
      if (!name || name === 'csrfmiddlewaretoken') return;

      let value = '';
      if (useInitialValues) {
        value = input.getAttribute('data-initial-value') || '';
      } else {
        if (input.type === 'checkbox') {
          value = input.checked ? '1' : '0';
        } else if (input.type === 'radio') {
          if (input.checked) {
            value = input.value;
          } else {
            return; // Bỏ qua radio không được check
          }
        } else {
          value = input.value || '';
        }
      }

      // Xử lý trường hợp radio buttons - chỉ lưu giá trị của radio được check
      if (input.type === 'radio') {
        if ((useInitialValues && value) || (!useInitialValues && input.checked)) {
          data[name] = value;
        }
      } else {
        data[name] = value;
      }
    });

    // Thu thập từ select fields
    const selects = document.querySelectorAll('#enrollmentContactForm select');
    selects.forEach(select => {
      const name = select.name;
      if (!name) return;

      let value = '';
      if (useInitialValues) {
        value = select.getAttribute('data-initial-value') || '';
      } else {
        value = select.value || '';
      }

      data[name] = value;
    });

    // Thu thập từ textarea fields
    const textareas = document.querySelectorAll('#enrollmentContactForm textarea');
    textareas.forEach(textarea => {
      const name = textarea.name;
      if (!name) return;

      let value = '';
      if (useInitialValues) {
        value = textarea.getAttribute('data-initial-value') || '';
      } else {
        value = textarea.value || '';
      }

      data[name] = value;
    });

    // Handle LISTUNDERLYING special case
    const listUnderlyingInput = document.getElementById('id_LISTUNDERLYING');
    if (listUnderlyingInput) {
      let listValue = '';
      if (useInitialValues) {
        listValue = listUnderlyingInput.getAttribute('data-initial-value') || '[]';
      } else {
        listValue = listUnderlyingInput.value || '[]';
      }
      
      try {
        // Add LISTUNDERLYING to data
        data['LISTUNDERLYING'] = listValue;
        
        // Parse the list and set individual disease values
        const diseaseList = JSON.parse(listValue);
        
        // Set all disease fields to 0 (not checked) by default
        document.querySelectorAll('.underlying-disease').forEach(cb => {
          if (cb.name) {
            data[cb.name] = '0';
          }
        });
        
        // Then set those in the list to 1 (checked)
        diseaseList.forEach(disease => {
          data[disease] = '1';
        });
      } catch (e) {
        console.error('Error parsing LISTUNDERLYING:', e);
      }
    }

    // Xử lý medication history data
    this.collectMedicationData(data, useInitialValues);

    return data;
  },

  // Thu thập dữ liệu medication history
  collectMedicationData: function(data, useInitialValues = false) {
    console.log("Collecting medication data, useInitialValues:", useInitialValues);

    // Thu thập dữ liệu từ bảng medication history
    const medicationRows = document.querySelectorAll('#medication_table tbody tr');
    console.log("Found", medicationRows.length, "medication rows");

    // Đảm bảo có medication data
    const medicationData = [];

    medicationRows.forEach((row, index) => {
      const inputs = row.querySelectorAll('input');
      console.log(`Row ${index}: Found ${inputs.length} inputs`);

      const medItem = {};

      inputs.forEach(input => {
        const name = input.name;
        if (name) {
          let value = '';
          if (useInitialValues) {
            value = input.getAttribute('data-initial-value') || '';
          } else {
            value = input.value || '';
          }

          // Lưu vào medication item
          medItem[name] = value;
          
          // Lưu với key bao gồm index để phân biệt
          data[`${name}_${index}`] = value;
          console.log(`Medication field ${name}_${index}: value = "${value}"`);
        }
      });

      // Thêm vào mảng medication data nếu có dữ liệu
      if (Object.keys(medItem).length > 0) {
        medicationData.push(medItem);
      }
    });

    // Đảm bảo tạo data-medication-json hidden input có dữ liệu hiện tại
    if (!useInitialValues) {
      // Cập nhật hidden input MEDICATION_DATA với dữ liệu hiện tại
      const medDataInput = document.getElementById('MEDICATION_DATA');
      if (medDataInput) {
        medDataInput.value = JSON.stringify(medicationData);
        console.log("Updated MEDICATION_DATA:", medDataInput.value);
      }
    }
  },

  // So sánh dữ liệu để tìm thay đổi
  compareData: function(oldData, newData) {
    const changedFields = {};
    const fieldLabels = this.getFieldLabels(oldData, newData);
    const fieldTypes = this.getFieldTypes();
    const fieldOptions = this.getFieldOptions();

    // Debug output của toàn bộ dữ liệu so sánh
    console.log("=== COMPARE DATA DETAILS ===");
    for (const key in newData) {
      const oldValue = oldData[key] !== undefined ? AuditLogBase.normalizeValue(oldData[key]) : '';
      const newValue = AuditLogBase.normalizeValue(newData[key]);
      console.log(`${key}: "${oldValue}" -> "${newValue}" ${oldValue !== newValue ? '(CHANGED)' : ''}`);
    }
    console.log("============================");

    // Special case: handle LISTUNDERLYING - we will ignore this field in comparisons
    // as we're already handling the individual disease fields
    const excludeFromComparison = ['LISTUNDERLYING'];

    for (const key in newData) {
      // Skip excluded fields
      if (excludeFromComparison.includes(key)) {
        continue;
      }
      
      const oldValue = oldData[key] !== undefined ? AuditLogBase.normalizeValue(oldData[key]) : '';
      const newValue = AuditLogBase.normalizeValue(newData[key]);

      if (oldValue !== newValue) {
        changedFields[key] = {
          old: oldData[key] || '',
          new: newData[key],
          label: fieldLabels[key] || key,
          type: fieldTypes[key] || 'text',
          options: fieldOptions[key] || {}
        };
      }
    }

    return changedFields;
  },

  // Lấy nhãn của các trường
  getFieldLabels: function(oldData, newData) {
    const labels = {};

    // Mapping các trường với nhãn tiếng Việt
    const fieldLabelMap = {
      // Thông tin cơ bản
      'SUBJIDENROLLSTUDY': 'Bệnh nhân chính liên quan',
      'ENRDATE': 'Ngày tham gia nghiên cứu',
      'RELATIONSHIP': 'Mối quan hệ với bệnh nhân',
      'DAYOFBIRTH': 'Ngày sinh',
      'MONTHOFBIRTH': 'Tháng sinh', 
      'YEAROFBIRTH': 'Năm sinh',
      'AGEIFDOBUNKNOWN': 'Tuổi (nếu không biết ngày sinh)',
      'SEX': 'Giới tính',
      'ETHNICITY': 'Dân tộc',
      'SPECIFYIFOTHERETHNI': 'Chi tiết dân tộc khác',
      'OCCUPATION': 'Nghề nghiệp',

      // Yếu tố nguy cơ
      'HOSP2D6M': 'Nhập viện ≥2 ngày trong 6 tháng qua',
      'DIAL3M': 'Lọc máu trong 3 tháng qua',
      'CATHETER3M': 'Đặt catheter trong 3 tháng qua',
      'SONDE3M': 'Đặt sonde trong 3 tháng qua',
      'HOMEWOUNDCARE': 'Chăm sóc vết thương tại nhà',
      'LONGTERMCAREFACILITY': 'Ở cơ sở chăm sóc dài hạn',
      'CORTICOIDPPI': 'Dùng corticoid hoặc PPI',

      // Bệnh nền
      'UNDERLYINGCONDS': 'Có bệnh nền',
      'HEARTFAILURE': 'Suy tim',
      'DIABETES': 'Đái tháo đường',
      'COPD': 'COPD',
      'HEPATITIS': 'Viêm gan',
      'CAD': 'Bệnh động mạch vành',
      'KIDNEYDISEASE': 'Bệnh thận',
      'ASTHMA': 'Hen suyễn',
      'CIRRHOSIS': 'Xơ gan',
      'HYPERTENSION': 'Tăng huyết áp',
      'AUTOIMMUNE': 'Bệnh tự miễn',
      'CANCER': 'Ung thư',
      'ALCOHOLISM': 'Nghiện rượu',
      'HIV': 'HIV',
      'ADRENALINSUFFICIENCY': 'Suy thượng thận',
      'BEDRIDDEN': 'Nằm một chỗ',
      'PEPTICULCER': 'Loét dạ dày',
      'COLITIS_IBS': 'Viêm đại tràng/IBS',
      'SENILITY': 'Lão suy',
      'MALNUTRITION_WASTING': 'Suy dinh dưỡng',
      'OTHERDISEASE': 'Bệnh khác',
      'OTHERDISEASESPECIFY': 'Chi tiết bệnh khác',

      // Thông tin hoàn thành
      'COMPLETEDBY': 'Người hoàn thành',
      'COMPLETEDDATE': 'Ngày hoàn thành',

      // Medication history
      'DRUGNAME': 'Tên thuốc',
      'DOSAGE': 'Liều dùng',
      'USAGETIME': 'Thời gian sử dụng',
      'USAGEREASON': 'Lý do sử dụng thuốc'
    };
    
    // Merge with labels from form
    Object.assign(labels, fieldLabelMap);
    
    // Add dynamic medication field labels
    const allKeys = new Set([...Object.keys(oldData || {}), ...Object.keys(newData || {})]);
    allKeys.forEach(key => {
      // Check if this is a medication field using regex
      if (/^MEDICATION_(NAME|DOSAGE|DURATION|REASON)_\d+/.test(key)) {
        // Extract the medication field type (NAME, DOSAGE, etc.)
        const match = key.match(/^MEDICATION_(NAME|DOSAGE|DURATION|REASON)_\d+/);
        if (match && match[1]) {
          const fieldType = match[1];
          
          // Set appropriate label based on field type
          switch (fieldType) {
            case 'NAME':
              labels[key] = 'Tên thuốc';
              break;
            case 'DOSAGE':
              labels[key] = 'Liều dùng';
              break;
            case 'DURATION':
              labels[key] = 'Thời gian sử dụng';
              break;
            case 'REASON':
              labels[key] = 'Lý do sử dụng';
              break;
          }
        }
      }
    });
    
    // Lấy labels từ các thẻ label trong form
    const labelElements = document.querySelectorAll('#enrollmentContactForm label');
    labelElements.forEach(label => {
      const forAttr = label.getAttribute('for');
      if (forAttr) {
        const fieldName = forAttr.replace('id_', '');
        const labelText = label.textContent.trim();
        if (labelText && !labels[fieldName]) {
          labels[fieldName] = labelText;
        }
      }
    });

    // Merge với mapping có sẵn
    return { ...fieldLabelMap, ...labels };
  },

  // Lấy loại của các trường
  getFieldTypes: function() {
    const types = {};

    // Xác định loại từ các trường
    const checkboxes = document.querySelectorAll('#enrollmentContactForm input[type="checkbox"]');
    checkboxes.forEach(cb => {
      if (cb.name) types[cb.name] = 'checkbox';
    });

    const radios = document.querySelectorAll('#enrollmentContactForm input[type="radio"]');
    radios.forEach(radio => {
      if (radio.name) types[radio.name] = 'radio';
    });

    const selects = document.querySelectorAll('#enrollmentContactForm select');
    selects.forEach(select => {
      if (select.name) types[select.name] = 'select';
    });

    const dates = document.querySelectorAll('#enrollmentContactForm input[type="date"], #enrollmentContactForm input.datepicker');
    dates.forEach(date => {
      if (date.name) types[date.name] = 'date';
    });

    return types;
  },

  // Lấy options cho các trường select
  getFieldOptions: function() {
    const options = {};

    const selects = document.querySelectorAll('#enrollmentContactForm select');
    selects.forEach(select => {
      if (select.name) {
        options[select.name] = {};
        const optionElements = select.querySelectorAll('option');
        optionElements.forEach(option => {
          const value = option.value;
          const text = option.textContent.trim();
          if (value) {
            options[select.name][value] = text;
          }
        });
      }
    });

    return options;
  },

  // Hiển thị modal để nhập lý do thay đổi
  showChangeModal: function(changedFields, callback) {
    console.log("EnrollmentContactAudit.showChangeModal called with:", changedFields);
    console.log("Callback function:", callback);

    // Kiểm tra xem modal có tồn tại không
    const modal = document.getElementById('changeReasonModal');
    console.log("Modal element:", modal);

    if (!modal) {
      console.error("Change reason modal not found!");
      return;
    }

    // Kiểm tra xem AuditLogBase có tồn tại không
    if (typeof AuditLogBase === 'undefined') {
      console.error("AuditLogBase is not defined!");
      return;
    }

    // Kiểm tra xem showChangeModal method có tồn tại không
    if (typeof AuditLogBase.showChangeModal !== 'function') {
      console.error("AuditLogBase.showChangeModal is not a function!");
      return;
    }

    // Sử dụng bind để đảm bảo context đúng
    const self = this;
    AuditLogBase.showChangeModal(changedFields, function(reasonsData) {
      console.log("Reasons data received:", reasonsData);
      // Lưu dữ liệu vào hidden fields
      self.saveAuditData(changedFields, reasonsData);
      if (callback) callback();
    });
  },

  // Lưu dữ liệu audit vào hidden fields
  saveAuditData: function(changedFields, reasonsData) {
    // Tạo old data JSON
    const oldData = {};
    Object.keys(changedFields).forEach(key => {
      oldData[key] = changedFields[key].old;
    });

    // Tạo new data JSON
    const newData = {};
    Object.keys(changedFields).forEach(key => {
      newData[key] = changedFields[key].new;
    });

    // Đảm bảo reasons_json chứa cả label động
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

    // Đảm bảo hidden fields tồn tại
    const oldDataJsonInput = document.getElementById('oldDataJson');
    const newDataJsonInput = document.getElementById('newDataJson');
    const reasonsJsonInput = document.getElementById('reasons_json');
    const changeReasonInput = document.getElementById('change_reason');

    if (oldDataJsonInput) oldDataJsonInput.value = JSON.stringify(oldData);
    if (newDataJsonInput) newDataJsonInput.value = JSON.stringify(newData);
    if (reasonsJsonInput) reasonsJsonInput.value = JSON.stringify(reasonsJsonWithLabel);

    // Tạo change_reason summary
    const changeReason = Object.entries(reasonsJsonWithLabel)
      .map(([field, obj]) => {
        const label = obj.label || field;
        return `${label}: ${obj.reason}`;
      })
      .join(' | ');

    if (changeReasonInput) changeReasonInput.value = changeReason;

    console.log("Audit data saved:", { oldData, newData, reasonsJsonWithLabel, changeReason });
  },

  // Submit form
  submitForm: function() {
    const form = document.getElementById('enrollmentContactForm');
    // Đảm bảo sự kiện submit không bị chặn
    $(form).off('submit').submit();
  },

  // Thiết lập các handlers đặc biệt
  setupSpecialHandlers: function() {
    // Xử lý bệnh nền
    this.setupUnderlyingDiseaseHandler();
    
    // Xử lý medication history
    this.setupMedicationHandler();
    
    // Xử lý việc thêm/xóa medication rows
    this.setupMedicationRowHandlers();
  },

  // Xử lý bệnh nền
  setupUnderlyingDiseaseHandler: function() {
    const underlyingCheckbox = document.getElementById('id_UNDERLYINGCONDS');
    if (underlyingCheckbox) {
      underlyingCheckbox.addEventListener('change', () => {
        // Không cần cập nhật data-initial-value khi user thay đổi checkbox
        // vì đây là thay đổi cần được detect trong audit log
      });
    }

    // Xử lý các checkbox bệnh nền
    const diseaseCheckboxes = document.querySelectorAll('.underlying-disease');
    diseaseCheckboxes.forEach(cb => {
      cb.addEventListener('change', () => {
        // Không cần cập nhật data-initial-value khi user thay đổi checkbox
      });
    });
    
    // Ensure we get the initial state of LISTUNDERLYING
    const listUnderlyingInput = document.getElementById('id_LISTUNDERLYING');
    if (listUnderlyingInput) {
      // Store the initial LISTUNDERLYING value for audit comparison
      const initialValue = listUnderlyingInput.value || '[]';
      listUnderlyingInput.setAttribute('data-initial-value', initialValue);
      console.log("Set initial LISTUNDERLYING value:", initialValue);
    }
  },

  // Xử lý medication history
  setupMedicationHandler: function() {
    const corticoidRadios = document.querySelectorAll('input[name="CORTICOIDPPI"]');
    corticoidRadios.forEach(radio => {
      radio.addEventListener('change', () => {
        // Không cần cập nhật data-initial-value khi user thay đổi radio
      });
    });
  },

  // Xử lý việc thêm/xóa medication rows
  setupMedicationRowHandlers: function() {
    // Lắng nghe sự kiện thêm row
    const addButton = document.getElementById('add_medication_row');
    if (addButton) {
      addButton.addEventListener('click', () => {
        // Đợi một chút để row mới được thêm vào DOM
        setTimeout(() => {
          this.setupMedicationInitialValues();
        }, 100);
      });
    }

    // Lắng nghe sự kiện xóa row (sử dụng event delegation)
    const medicationTable = document.getElementById('medication_table');
    if (medicationTable) {
      medicationTable.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-medication-row')) {
          // Đợi một chút để row được xóa khỏi DOM
          setTimeout(() => {
            this.updateInitialValues();
          }, 100);
        }
      });
    }
  },

  // Cập nhật initial values sau khi có thay đổi
  updateInitialValues: function() {
    console.log("Updating initial values after form changes");
    this.setupInitialValues();
  }
};

// Khởi tạo khi DOM ready
document.addEventListener('DOMContentLoaded', function() {
  // Kiểm tra chế độ view-only
  const isViewOnly = document.body.classList.contains('view-only') || 
                    (typeof window.isReadonly !== 'undefined' && window.isReadonly);

  console.log("DOM Content Loaded. isViewOnly:", isViewOnly);
  
  if (!isViewOnly) {
    console.log("Initializing EnrollmentContactAudit");
    EnrollmentContactAudit.init();
  } else {
    console.log("View-only mode detected, not initializing audit logging");
  }
});