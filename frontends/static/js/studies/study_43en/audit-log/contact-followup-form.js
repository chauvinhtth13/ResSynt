window.ContactFollowUpFormAudit = {
  isProcessing: false,

  init: function() {
    console.log("Initializing Contact Follow Up Form Audit Logging");

    const form = document.getElementById('contactFollowUpForm');
    if (!form) {
      console.warn("Contact follow-up form not found");
      return;
    }

    // Log important form attributes
    console.log("Form attributes:", {
      action: form.action,
      method: form.method,
      isNew: form.getAttribute('data-is-new'),
      followupDay: form.getAttribute('data-followup-day'),
      usubjid: form.getAttribute('data-usubjid')
    });

    // Log the URL structure
    console.log("URL structure:", {
      pathname: window.location.pathname,
      pathSegments: window.location.pathname.split('/').filter(Boolean)
    });

    // Check for formset information
    const formsetPrefix = form.querySelector('input[name$="TOTAL_FORMS"]');
    if (formsetPrefix) {
      console.log("Formset detected with name:", formsetPrefix.name);
    }

    if (this.isViewOnly()) {
      console.log("View-only mode, disabling audit logging");
      return;
    }

    this.setupInitialValues();
    this.setupFormSubmission();
    this.setupSpecialHandlers();
    console.log("Contact Follow Up Form Audit Logging initialized successfully");
  },

  isViewOnly: function() {
    return document.querySelector('.view-only-form') !== null;
  },

  setupInitialValues: function() {
    console.log("Setting up initial values for audit logging");

    const form = document.getElementById('contactFollowUpForm');
    if (!form) {
      console.error("Contact follow-up form not found for initial values setup");
      return;
    }

    const fields = document.querySelectorAll('#contactFollowUpForm input:not([type="hidden"]), #contactFollowUpForm select, #contactFollowUpForm textarea');
    fields.forEach(field => {
      const name = field.name;
      if (!name || name === 'csrfmiddlewaretoken' || name.includes('medications')) return;

      let initialValue = '';
      if (field.type === 'checkbox') {
        initialValue = field.checked ? 'True' : 'False';
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

      field.setAttribute('data-initial-value', initialValue);
      console.log(`Field ${name}: initial value = "${initialValue}"`);
    });

    this.setupMedicationInitialValues();
  },

  setupMedicationInitialValues: function() {
    console.log("Setting up medication initial values");
    const medicationRows = document.querySelectorAll('#medication_history_table tbody tr');
    medicationRows.forEach((row, index) => {
      const inputs = row.querySelectorAll('input:not([name$="-DELETE"]), textarea');
      inputs.forEach(input => {
        const name = input.name;
        if (name) {
          const initialValue = input.value || '';
          input.setAttribute('data-initial-value', initialValue);
          console.log(`Medication field ${name}: initial value = "${initialValue}"`);
        }
      });
    });
  },

  setupFormSubmission: function() {
    const form = document.getElementById('contactFollowUpForm');
    const saveButton = document.getElementById('btnSaveFollowUp');
    if (!saveButton || !form) {
      console.warn("Save button or form not found");
      return;
    }

    $(document).off('click', '#btnSaveFollowUp');
    $(saveButton).off('click');
    saveButton.onclick = null;

    $(saveButton).on('click', (e) => {
      e.preventDefault();
      console.log("Save button clicked");

      if (this.isProcessing) {
        console.log("Form is already processing, preventing duplicate submission");
        return false;
      }

      this.isProcessing = true;

      const isMedicationUsed = $('#id_MEDICATIONUSE').is(':checked');
      if (isMedicationUsed) {
        const hasMedication = Array.from(document.querySelectorAll('#medication_history_table tbody tr')).some(row => {
          const inputs = row.querySelectorAll('input, textarea');
          return Array.from(inputs).some(input => input.value.trim() && !input.name.includes('-DELETE'));
        });
        if (!hasMedication) {
          this.showMessage('Vui lòng nhập ít nhất một loại thuốc khi chọn sử dụng thuốc.', 'warning');
          this.resetProcessingState();
          return;
        }
      }

      const isNew = form.getAttribute('data-is-new') === 'true';
      if (isNew) {
        form.submit();
        return;
      }

      const initialData = this.collectFormData(true);
      const currentData = this.collectFormData(false);
      console.log("Initial data:", initialData);
      console.log("Current data:", currentData);

      const changedFields = this.compareData(initialData, currentData);
      console.log("Changed fields:", changedFields);

      if (Object.keys(changedFields).length === 0) {
        this.showMessage('Không có thay đổi để lưu', 'info');
        $('#btnSaveFollowUp').html('<i class="fas fa-save"></i> Lưu').prop('disabled', false);
        this.resetProcessingState();
        return;
      }

      this.showChangeModal(changedFields, (reasonsData) => {
        this.saveAuditData(changedFields, reasonsData, () => {
          console.log("Audit data saved, now submitting form");
          this.submitForm();
        });
      });
    });
  },

  collectFormData: function(useInitialValues = false) {
    const data = {};
    const form = document.getElementById('contactFollowUpForm');
    if (!form) return data;

    const inputs = document.querySelectorAll('#contactFollowUpForm input:not([type="hidden"]):not([name$="-DELETE"]), #contactFollowUpForm select, #contactFollowUpForm textarea');
    inputs.forEach(input => {
      const name = input.name;
      if (!name || name === 'csrfmiddlewaretoken' || name.includes('-TOTAL_FORMS') || 
          name.includes('-INITIAL_FORMS') || name.includes('-MIN_NUM_FORMS') || 
          name.includes('-MAX_NUM_FORMS')) return;

      let value = '';
      if (useInitialValues) {
        value = input.getAttribute('data-initial-value') || '';
      } else {
        if (input.type === 'checkbox') {
          value = input.checked ? 'True' : 'False';
        } else if (input.type === 'radio') {
          if (input.checked) {
            value = input.value;
          } else {
            return;
          }
        } else {
          value = input.value || '';
        }
      }

      if (input.type === 'radio') {
        if ((useInitialValues && value) || (!useInitialValues && input.checked)) {
          data[name] = value;
        }
      } else {
        data[name] = value;
      }
    });

    this.collectMedicationData(data, useInitialValues);
    return data;
  },

  collectMedicationData: function(data, useInitialValues = false) {
    const medicationRows = document.querySelectorAll('#medication_history_table tbody tr');
    medicationRows.forEach((row, index) => {
      const inputs = row.querySelectorAll('input:not([name$="-DELETE"]), textarea');
      inputs.forEach(input => {
        const name = input.name;
        if (name) {
          let parts = name.split('-');
          let prefix = parts[0]; // Could be medications_28 or medications_90
          let rowIndex = parts[1];
          let fieldName = parts[2];
          
          if (!fieldName || fieldName === 'id') return;

          let value = '';
          if (useInitialValues) {
            value = input.getAttribute('data-initial-value') || '';
          } else {
            value = input.value || '';
          }

          data[name] = value;
          console.log(`Collected medication data: ${name} = ${value}`);
        }
      });
    });
  },

  compareData: function(oldData, newData) {
    const fieldOptions = this.getFieldOptions();
    const fieldLabels = this.getFieldLabels();
    const fieldTypes = this.getFieldTypes();
    
    const allKeys = new Set([...Object.keys(oldData), ...Object.keys(newData)]);
    allKeys.forEach(key => {
      if ((key.includes('medications-') || key.includes('medications_')) && !fieldLabels[key]) {
        const parts = key.split('-');
        if (parts.length === 3) {
          const prefix = parts[0];
          const rowIndex = parseInt(parts[1]);
          const fieldName = parts[2];
          
          let baseLabel = '';
          switch(fieldName) {
            case 'MEDICATIONNAME':
              baseLabel = 'Tên thuốc (Corticoid, PPI, kháng sinh,...)';
              break;
            case 'DOSAGE':
              baseLabel = 'Liều dùng';
              break;
            case 'USAGE_PERIOD':
              baseLabel = 'Thời gian sử dụng';
              break;
            case 'REASON':
              baseLabel = 'Lý do sử dụng';
              break;
            default:
              baseLabel = fieldName;
          }
          
          fieldLabels[key] = `${baseLabel} (hàng ${rowIndex + 1})`;
          fieldTypes[key] = 'text';
          
          console.log(`Added dynamic label for ${key}: ${fieldLabels[key]}`);
        }
      }
    });
    
    const changedFields = window.AuditLogBase.compareFields(
      oldData,
      newData,
      fieldLabels,
      fieldTypes,
      fieldOptions
    );

    Object.keys(changedFields).forEach(key => {
      if (key in fieldOptions) {
        const options = fieldOptions[key];
        changedFields[key].old = options[changedFields[key].old] || changedFields[key].old;
        changedFields[key].new = options[changedFields[key].new] || changedFields[key].new;
      } else if (fieldTypes[key] === 'boolean') {
        changedFields[key].old = changedFields[key].old === 'True' ? 'Có' : 'Không';
        changedFields[key].new = changedFields[key].new === 'True' ? 'Có' : 'Không';
      }
    });

    return changedFields;
  },

  getFieldLabels: function() {
    const labels = {
      'ASSESSED': 'Người tiếp xúc gần được đánh giá',
      'ASSESSDATE': 'Ngày đánh giá',
      'HOSP2D': 'Nằm viện ≥ 2 ngày',
      'DIAL': 'Chạy thận định kỳ',
      'CATHETER': 'Đặt catheter tĩnh mạch',
      'SONDE': 'Đặt sonde tiểu lưu',
      'HOMEWOUNDCARE': 'Chăm sóc vết thương tại nhà',
      'LONGTERMCAREFACILITY': 'Sống ở CSYT chăm sóc dài hạn',
      'MEDICATIONUSE': 'Sử dụng thuốc',
      'COMPLETEDBY': 'Người hoàn thành',
      'COMPLETEDDATE': 'Ngày hoàn thành'
    };

    // Lấy nhãn từ tiêu đề bảng thuốc
    const medicationTableHeaders = document.querySelectorAll('#medication_history_table thead th:not(:last-child)');
    const medicationFields = ['MEDICATIONNAME', 'DOSAGE', 'USAGE_PERIOD', 'REASON'];
    medicationTableHeaders.forEach((header, index) => {
      const fieldName = `medications-${medicationFields[index]}`;
      let baseLabel = header.textContent.trim();
      // Tùy chỉnh nhãn cho MEDICATIONNAME
      if (medicationFields[index] === 'MEDICATIONNAME') {
        baseLabel = 'Tên thuốc (Corticoid, PPI, kháng sinh,...)';
      }
      labels[fieldName] = baseLabel;
    });

    return labels;
  },

  getFieldTypes: function() {
    const fieldTypes = {
      'ASSESSED': 'select',
      'ASSESSDATE': 'date',
      'HOSP2D': 'boolean',
      'DIAL': 'boolean',
      'CATHETER': 'boolean',
      'SONDE': 'boolean',
      'HOMEWOUNDCARE': 'boolean',
      'LONGTERMCAREFACILITY': 'boolean',
      'MEDICATIONUSE': 'boolean',
      'COMPLETEDBY': 'text',
      'COMPLETEDDATE': 'date',
      'medications-MEDICATIONNAME': 'text',
      'medications-DOSAGE': 'text',
      'medications-USAGE_PERIOD': 'text',
      'medications-REASON': 'text'
    };

    return fieldTypes;
  },

  getFieldOptions: function() {
    return {
      'ASSESSED': {
        'Yes': 'Có',
        'No': 'Không',
        'NA': 'Không áp dụng'
      }
    };
  },

  showChangeModal: function(changedFields, callback) {
    console.log("ContactFollowUpFormAudit.showChangeModal called with:", changedFields);
    if (!document.getElementById('changeReasonModal')) {
      console.error("Change reason modal not found!");
      return;
    }

    const self = this;
    const originalShowModalFn = window.AuditLogBase.showChangeModal;

    window.AuditLogBase.showChangeModal = function(fields, cb) {
      self.isProcessing = true;
      const wrappedCallback = function(reasonsData) {
        console.log("Change modal callback executed with reasons:", reasonsData);
        if (cb) cb(reasonsData);
      };
      originalShowModalFn.call(window.AuditLogBase, fields, wrappedCallback);
      window.AuditLogBase.showChangeModal = originalShowModalFn;
    };

    window.AuditLogBase.showChangeModal(changedFields, (reasonsData) => {
      this.saveAuditData(changedFields, reasonsData, () => {
        if (callback) callback(reasonsData);
      });
    });
  },

  saveAuditData: function(changedFields, reasonsData, callback) {
    const oldData = {};
    const newData = {};
    const reasonsJsonWithLabel = {};

    Object.keys(changedFields).forEach(key => {
      oldData[key] = changedFields[key].old;
      newData[key] = changedFields[key].new;
      let reasonKey = key;
      if (!(reasonKey in reasonsData)) {
        if (reasonsData[key.toUpperCase()]) reasonKey = key.toUpperCase();
        else if (reasonsData[key.toLowerCase()]) reasonKey = key.toLowerCase();
      }
      if (typeof reasonsData[reasonKey] === 'string') {
        reasonsJsonWithLabel[key] = {
          label: changedFields[key].label || key,
          reason: reasonsData[reasonKey]
        };
      } else if (typeof reasonsData[reasonKey] === 'object' && reasonsData[reasonKey] !== null) {
        reasonsJsonWithLabel[key] = reasonsData[reasonKey];
      }
    });

    const form = document.getElementById('contactFollowUpForm');
    if (!form) {
      console.error("Form contactFollowUpForm not found!");
      return;
    }

    let oldDataInput = form.querySelector('#oldDataJson');
    let newDataInput = form.querySelector('#newDataJson');
    let reasonsInput = form.querySelector('#reasonsJson');
    let reasonInput = form.querySelector('#change_reason');

    if (!oldDataInput) {
      oldDataInput = document.createElement('input');
      oldDataInput.type = 'hidden';
      oldDataInput.id = 'oldDataJson';
      oldDataInput.name = 'oldDataJson';
      form.appendChild(oldDataInput);
    }
    if (!newDataInput) {
      newDataInput = document.createElement('input');
      newDataInput.type = 'hidden';
      newDataInput.id = 'newDataJson';
      newDataInput.name = 'newDataJson';
      form.appendChild(newDataInput);
    }
    if (!reasonsInput) {
      reasonsInput = document.createElement('input');
      reasonsInput.type = 'hidden';
      reasonsInput.id = 'reasonsJson';
      reasonsInput.name = 'reasonsJson';
      form.appendChild(reasonsInput);
    }
    if (!reasonInput) {
      reasonInput = document.createElement('input');
      reasonInput.type = 'hidden';
      reasonInput.id = 'change_reason';
      reasonInput.name = 'change_reason';
      form.appendChild(reasonInput);
    }

    oldDataInput.value = JSON.stringify(oldData);
    newDataInput.value = JSON.stringify(newData);
    reasonsInput.value = JSON.stringify(reasonsJsonWithLabel);

    const changeReason = Object.entries(reasonsJsonWithLabel)
      .map(([field, obj]) => {
        const label = obj.label || field;
        return `${label}: ${obj.reason}`;
      })
      .join(' | ');

    reasonInput.value = changeReason;

    console.log("Audit data saved for form contactFollowUpForm:", { oldData, newData, reasonsJsonWithLabel, changeReason });

    if (callback) callback();
  },

  submitForm: function() {
    const form = document.getElementById('contactFollowUpForm');
    const $btn = $('#btnSaveFollowUp');
    const originalHtml = $btn.html();
    const followupType = form.getAttribute('data-is-new') === 'true' ? 'create' : 'update';
    
    // Xác định followupDay từ pathname hoặc form attribute
    let followupDay = '';
    if (form.hasAttribute('data-followup-day')) {
      followupDay = form.getAttribute('data-followup-day');
    } else {
      followupDay = window.location.pathname.includes('followup-28') || window.location.pathname.includes('followup/28') ? '28' : '90';
    }
    
    // Phân tích URL để lấy usubjid
    const pathParts = window.location.pathname.split('/').filter(part => part);
    let usubjid = '';
    
    if (form.hasAttribute('data-usubjid')) {
      usubjid = form.getAttribute('data-usubjid');
    } else {
      const contactIndex = pathParts.indexOf('contact');
      if (contactIndex !== -1 && contactIndex + 1 < pathParts.length) {
        usubjid = pathParts[contactIndex + 1];
      } else {
        const usubjidField = form.querySelector('input[name="usubjid"]');
        if (usubjidField) {
          usubjid = usubjidField.value;
        }
      }
    }
    
    if (!usubjid) {
      console.error("Could not determine usubjid from URL or form attributes");
      this.showMessage('Lỗi: Không thể xác định ID bệnh nhân', 'danger');
      this.resetProcessingState();
      return;
    }

    console.log("usubjid:", usubjid, "followupDay:", followupDay, "followupType:", followupType);

    const formData = new FormData(form);
    console.log("Submitting form with data:", Array.from(formData.entries()));

    $btn.html('<i class="fas fa-spinner fa-spin"></i> Đang lưu...').prop('disabled', true);

    $.ajax({
      url: `/43en/contact/${usubjid}/followup/${followupDay}/${followupType}/`,
      method: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      timeout: 30000,
      retryCount: 0,
      retryLimit: 2,
      retryDelay: 1000,
      beforeSend: function(xhr) {
        const csrfToken = form.querySelector('input[name="csrfmiddlewaretoken"]');
        if (csrfToken) {
          xhr.setRequestHeader("X-CSRFToken", csrfToken.value);
        }
      },
      success: (response) => {
        console.log("Update success:", response);
        if (response.success) {
          this.showMessage('Đã cập nhật thông tin theo dõi thành công!', 'success');
          setTimeout(() => {
            console.log("Redirecting to:", `/43en/contact/${usubjid}/`);
            window.location.href = `/43en/contact/${usubjid}/`;
          }, 500);
        } else {
          $btn.html(originalHtml).prop('disabled', false);
          this.resetProcessingState();
          this.showMessage(response.message || 'Có lỗi xảy ra khi cập nhật', 'danger');
        }
      },
      error: (xhr, status, error) => {
        console.error("Update error:", error, "Status:", xhr.status);
        console.log("Raw response:", xhr.responseText);
        $btn.html(originalHtml).prop('disabled', false);
        this.resetProcessingState();
        let errorMsg = 'Có lỗi xảy ra khi cập nhật thông tin theo dõi';
        try {
          const response = JSON.parse(xhr.responseText);
          if (response.message) errorMsg = response.message;
        } catch (e) {
          console.log("Could not parse error response:", e);
        }
        this.showMessage(errorMsg, 'danger');
      }
    });
  },

  showMessage: function(message, type = 'success') {
    clearTimeout(window.saveIndicatorTimeout);
    const $indicator = $('#saveIndicator');
    $indicator.removeClass('alert-success alert-danger alert-warning alert-info')
      .addClass(`alert-${type}`);
    $indicator.find('.message').text(message);
    $indicator.show();

    window.saveIndicatorTimeout = setTimeout(() => {
      $indicator.hide();
    }, 3000);
  },

  resetProcessingState: function() {
    console.log("Resetting processing state");
    this.isProcessing = false;
    const saveButton = document.getElementById('btnSaveFollowUp');
    if (saveButton) {
      saveButton.disabled = false;
      if (saveButton.innerHTML.includes('fa-spinner')) {
        saveButton.innerHTML = '<i class="fas fa-save"></i> Lưu';
      }
    }
  },

  setupSpecialHandlers: function() {
    this.setupMedicationHandler();
    this.setupMedicationRowHandlers();

    const self = this;
    $('#changeReasonModal').on('hidden.bs.modal', function() {
      console.log("Change reason modal hidden, resetting processing state");
      self.resetProcessingState();
    });

    $(document).on('keydown.auditEscape', function(e) {
      if (e.key === 'Escape' && $('#changeReasonModal').is(':visible')) {
        console.log("Escape key detected in change reason modal, resetting processing state");
        self.resetProcessingState();
      }
    });
  },

  setupMedicationHandler: function() {
    const medicationCheckbox = document.getElementById('id_MEDICATIONUSE');
    if (medicationCheckbox) {
      medicationCheckbox.addEventListener('change', () => {});
    }
  },

  setupMedicationRowHandlers: function() {
    const addButton = document.getElementById('add_medication_row');
    if (addButton) {
      addButton.addEventListener('click', () => {
        setTimeout(() => {
          this.setupMedicationInitialValues();
        }, 100);
      });
    }
  }
};

$(document).ready(function() {
  window.ContactFollowUpFormAudit.init();
});