// Enrollment Form Audit Logging
// Tích hợp với base.js để ghi lại log cho enrollment form

window.EnrollmentFormAudit = {
  // Khởi tạo audit logging cho enrollment form
  init: function() {
    console.log("Initializing Enrollment Form Audit Logging");

    // Kiểm tra xem form có tồn tại không
    const form = document.getElementById('enrollmentForm');
    if (!form) {
      console.warn("Enrollment form not found");
      return;
    }

    // Thiết lập các trường với data-initial-value
    this.setupInitialValues();

    // Thiết lập form submission handler
    this.setupFormSubmission();

    // Thiết lập các event handlers đặc biệt
    this.setupSpecialHandlers();

    console.log("Enrollment Form Audit Logging initialized successfully");
  },

  // Thiết lập giá trị ban đầu cho các trường
  setupInitialValues: function() {
    console.log("Setting up initial values for audit logging");

    // Kiểm tra xem form có tồn tại không
    const form = document.getElementById('enrollmentForm');
    if (!form) {
      console.error("Enrollment form not found for initial values setup");
      return;
    }

    // Lấy tất cả các trường input, select, textarea
    const fields = document.querySelectorAll('#enrollmentForm input, #enrollmentForm select, #enrollmentForm textarea');
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

    // Thiết lập initial values cho medication history
    this.setupMedicationInitialValues();
  },

  // Thiết lập initial values cho medication history
  setupMedicationInitialValues: function() {
    // Thiết lập cho medication count
    const medCountInput = document.getElementById('id_MEDICATION_COUNT');
    if (medCountInput) {
      const initialValue = medCountInput.value || '0';
      medCountInput.setAttribute('data-initial-value', initialValue);
    }

    // Thiết lập cho các medication rows hiện tại
    const medicationRows = document.querySelectorAll('#medication_history_table tbody tr');
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
    const form = document.getElementById('enrollmentForm');
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
    const inputs = document.querySelectorAll('#enrollmentForm input:not([type="hidden"])');
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
    const selects = document.querySelectorAll('#enrollmentForm select');
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
    const textareas = document.querySelectorAll('#enrollmentForm textarea');
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

    // Xử lý medication history data
    this.collectMedicationData(data, useInitialValues);

    return data;
  },

  // Thu thập dữ liệu medication history
  collectMedicationData: function(data, useInitialValues = false) {
    console.log("Collecting medication data, useInitialValues:", useInitialValues);

    // Thu thập dữ liệu từ bảng medication history
    const medicationRows = document.querySelectorAll('#medication_history_table tbody tr');
    console.log("Found", medicationRows.length, "medication rows");

    medicationRows.forEach((row, index) => {
      const inputs = row.querySelectorAll('input');
      console.log(`Row ${index}: Found ${inputs.length} inputs`);

      inputs.forEach(input => {
        const name = input.name;
        if (name) {
          let value = '';
          if (useInitialValues) {
            value = input.getAttribute('data-initial-value') || '';
          } else {
            value = input.value || '';
          }

          // Lưu với key bao gồm index để phân biệt
          data[`${name}_${index}`] = value;
          console.log(`Medication field ${name}_${index}: value = "${value}"`);
        }
      });
    });

    // Thu thập medication count
    const medCountInput = document.getElementById('id_MEDICATION_COUNT');
    if (medCountInput) {
      const name = medCountInput.name;
      if (name) {
        let value = '';
        if (useInitialValues) {
          value = medCountInput.getAttribute('data-initial-value') || '';
        } else {
          value = medCountInput.value || '';
        }
        data[name] = value;
        console.log(`Medication count ${name}: value = "${value}"`);
      }
    }
  },

  // So sánh dữ liệu để tìm thay đổi
  compareData: function(oldData, newData) {
    const changedFields = {};
    const fieldLabels = this.getFieldLabels();
    const fieldTypes = this.getFieldTypes();
    const fieldOptions = this.getFieldOptions();

    for (const key in newData) {
      if (oldData[key] !== undefined) {
        const oldValue = AuditLogBase.normalizeValue(oldData[key]);
        const newValue = AuditLogBase.normalizeValue(newData[key]);

        if (oldValue !== newValue) {
          changedFields[key] = {
            old: oldData[key],
            new: newData[key],
            label: fieldLabels[key] || key,
            type: fieldTypes[key] || 'text',
            options: fieldOptions[key] || {}
          };
        }
      }
    }

    return changedFields;
  },

  // Lấy nhãn của các trường
  getFieldLabels: function() {
    const labels = {};

    // Mapping các trường với nhãn tiếng Việt
    const fieldLabelMap = {
      // Thông tin cơ bản
      'ENRDATE': 'Ngày tham gia nghiên cứu',
      'RECRUITDEPT': 'Khoa tuyển bệnh',
      'DAYOFBIRTH': 'Ngày sinh',
      'MONTHOFBIRTH': 'Tháng sinh',
      'YEAROFBIRTH': 'Năm sinh',
      'AGEIFDOBUNKNOWN': 'Tuổi (nếu không biết ngày sinh)',
      'SEX': 'Giới tính',
      'ETHNICITY': 'Dân tộc',
      'MEDRECORDID': 'Mã hồ sơ bệnh án',
      'OCCUPATION': 'Nghề nghiệp',

      // Thông tin chuyển viện
      'FROMOTHERHOSPITAL': 'Chuyển viện từ cơ sở y tế khác',
      'PRIORHOSPIADMISDATE': 'Ngày nhập viện ở CSYT trước đó',
      'HEALFACILITYNAME': 'Tên cơ sở y tế',
      'REASONFORADM': 'Lý do nhập viện ở CSYT trước đó',

      // Địa chỉ
      'WARD': 'Phường/Xã',
      'DISTRICT': 'Quận/Huyện',
      'PROVINCECITY': 'Tỉnh/Thành phố',
      'TOILETNUM': 'Số lượng nhà vệ sinh',
      'SHAREDTOILET': 'Sử dụng chung nhà vệ sinh',
      'RESIDENCETYPE': 'Đặc điểm nơi ở',
      'WORKPLACETYPE': 'Đặc điểm nơi làm việc',

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

      // Thông tin chuyên viên
      'COMPLETEDBY': 'Người hoàn thành',
      'COMPLETEDDATE': 'Ngày hoàn thành',

      // Medication history
      'MEDICATION_COUNT': 'Số lượng thuốc',
      'DRUGNAME': 'Tên thuốc',
      'DOSAGE': 'Liều dùng',
      'USAGETIME': 'Thời gian sử dụng',
      'USAGEREASON': 'Lý do sử dụng thuốc'
    };

    // Lấy labels từ các thẻ label trong form
    const labelElements = document.querySelectorAll('#enrollmentForm label');
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
    const checkboxes = document.querySelectorAll('#enrollmentForm input[type="checkbox"]');
    checkboxes.forEach(cb => {
      if (cb.name) types[cb.name] = 'checkbox';
    });

    const radios = document.querySelectorAll('#enrollmentForm input[type="radio"]');
    radios.forEach(radio => {
      if (radio.name) types[radio.name] = 'radio';
    });

    const selects = document.querySelectorAll('#enrollmentForm select');
    selects.forEach(select => {
      if (select.name) types[select.name] = 'select';
    });

    const dates = document.querySelectorAll('#enrollmentForm input[type="date"], #enrollmentForm input.datepicker');
    dates.forEach(date => {
      if (date.name) types[date.name] = 'date';
    });

    return types;
  },

  // Lấy options cho các trường select
  getFieldOptions: function() {
    const options = {};

    const selects = document.querySelectorAll('#enrollmentForm select');
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
    console.log("EnrollmentFormAudit.showChangeModal called with:", changedFields);
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

    document.getElementById('oldDataJson').value = JSON.stringify(oldData);
    document.getElementById('newDataJson').value = JSON.stringify(newData);
    document.getElementById('reasons_json').value = JSON.stringify(reasonsJsonWithLabel);

    // Tạo change_reason summary
    const changeReason = Object.entries(reasonsJsonWithLabel)
        .map(([field, obj]) => {
        const label = obj.label || field;
        return `${label}: ${obj.reason}`;
        })
        .join(' | ');

    document.getElementById('change_reason').value = changeReason;

    console.log("Audit data saved:", { oldData, newData, reasonsJsonWithLabel, changeReason });
    },

  // Submit form
  submitForm: function() {
    const form = document.getElementById('enrollmentForm');
    form.submit();
  },

  // Xử lý bệnh nền
  setupUnderlyingDiseaseHandler: function() {
    const underlyingCheckbox = document.getElementById('id_UNDERLYINGCONDS');
    if (underlyingCheckbox) {
      underlyingCheckbox.addEventListener('change', () => {
        // Không cần cập nhật data-initial-value khi user thay đổi checkbox
        // vì đây là thay đổi cần được detect trong audit log
        // Chỉ cập nhật khi có thay đổi cấu trúc DOM (như add/remove rows)
      });
    }

    // Xử lý các checkbox bệnh nền
    const diseaseCheckboxes = document.querySelectorAll('.underlying-disease');
    diseaseCheckboxes.forEach(cb => {
      cb.addEventListener('change', () => {
        // Không cần cập nhật data-initial-value khi user thay đổi checkbox
        // vì đây là thay đổi cần được detect trong audit log
      });
    });
  },

  // Xử lý medication history
  setupMedicationHandler: function() {
    const corticoidRadios = document.querySelectorAll('input[name*="CORTICOIDPPI"]');
    corticoidRadios.forEach(radio => {
      radio.addEventListener('change', () => {
        // Không cần cập nhật data-initial-value khi user thay đổi radio
        // vì đây là thay đổi cần được detect trong audit log
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
    const medicationTable = document.getElementById('medication_history_table');
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
  // Kiểm tra chế độ view-only từ class của form
  const form = document.getElementById('enrollmentForm');
  const isViewOnly = form && form.classList.contains('view-only-form');

  if (!isViewOnly) {
    EnrollmentFormAudit.init();
  }
});