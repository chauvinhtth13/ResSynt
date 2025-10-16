// Discharge Form Audit Logging
// Tích hợp với base.js để ghi lại log cho form xuất viện

window.DischargeFormAudit = {
  isProcessing: false,

  init: function() {
    console.log("Initializing Discharge Form Audit Logging");

    const form = document.getElementById('dischargeForm');
    if (!form) {
      console.warn("Discharge form not found");
      return;
    }

    if (this.isViewOnly()) {
      console.log("View-only mode, disabling audit logging");
      return;
    }

    this.setupInitialValues();
    this.setupFormSubmission();
    this.setupModalHandlers();
    this.setupSpecialHandlers();
    console.log("Discharge Form Audit Logging initialized successfully");
  },

  isViewOnly: function() {
    return document.querySelector('.readonly-form') !== null;
  },

  resetProcessingState: function() {
    console.log("Resetting processing state");
    this.isProcessing = false;
    const saveButton = document.getElementById('btnSaveDischarge');
    if (saveButton) {
      saveButton.disabled = false;
      if (saveButton.innerHTML.includes('fa-spinner')) {
        saveButton.innerHTML = '<i class="fas fa-save"></i> Lưu thông tin';
      }
    }
  },

  setupModalHandlers: function() {
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

  setupInitialValues: function() {
    console.log("Setting up initial values for audit logging");

    const form = document.getElementById('dischargeForm');
    if (!form) {
      console.error("Discharge form not found for initial values setup");
      return;
    }

    const fields = document.querySelectorAll('#dischargeForm input:not([type="hidden"]), #dischargeForm select, #dischargeForm textarea');
    console.log("Found", fields.length, "fields to set initial values for");

    fields.forEach(field => {
      const name = field.name;
      if (!name || name === 'csrfmiddlewaretoken' || name === 'oldDataJson' || name === 'newDataJson' || name === 'reasonsJson' || name === 'change_reason') return;

      let initialValue = '';
      if (field.type === 'checkbox') {
        initialValue = field.checked ? 'True' : 'False';
      } else if (field.type === 'radio') {
        const radioGroup = document.querySelectorAll(`input[name="${name}"]:checked`);
        initialValue = radioGroup.length > 0 ? radioGroup[0].value : 'No';
      } else if (field.tagName === 'SELECT') {
        initialValue = field.value || '';
      } else {
        initialValue = field.value || '';
      }

      field.setAttribute('data-initial-value', initialValue);
      console.log(`Field ${name}: initial value = "${initialValue}"`);
    });

    this.setupFormsetInitialValues();
  },

  setupFormsetInitialValues: function() {
    const icdForms = document.querySelectorAll('#icd-formset .icd-form');
    console.log(`Found ${icdForms.length} ICD forms`);
    
    icdForms.forEach((form, index) => {
      const inputs = form.querySelectorAll('input, select, textarea');
      inputs.forEach(input => {
        const name = input.name;
        if (name && !name.includes('-DELETE') && !name.includes('-id') && !name.includes('-discharge_case')) {
          let initialValue = '';
          if (input.type === 'checkbox') {
            initialValue = input.checked ? 'True' : 'False';
          } else if (input.type === 'radio') {
            const radioGroup = document.querySelectorAll(`input[name="${name}"]:checked`);
            initialValue = radioGroup.length > 0 ? radioGroup[0].value : '';
          } else {
            initialValue = input.value || '';
          }
          input.setAttribute('data-initial-value', initialValue);
          console.log(`Set initial value for ICD ${name}: ${initialValue}`);
        }
      });
    });
  },

  setupFormSubmission: function() {
    const saveButton = document.getElementById('btnSaveDischarge');
    if (!saveButton) {
      console.warn("Save button not found");
      return;
    }

    $(document).off('click', '#btnSaveDischarge');
    $(saveButton).off('click');
    saveButton.onclick = null;

    $(saveButton).on('click', (e) => {
      e.preventDefault();
      console.log("Save button clicked");

      if (this.isProcessing) {
        console.log("Form is already processing, preventing duplicate submission");
        return;
      }
      this.isProcessing = true;

      const hasErrors = this.validateForm();
      if (hasErrors) {
        console.log("Validation failed, stopping submission");
        this.resetProcessingState();
        return;
      }

      const form = document.getElementById('dischargeForm');
      const isNew = form.getAttribute('data-is-create') === 'true';
      if (isNew) {
        console.log("Creating new form, submitting to create endpoint");
        this.submitForm(true);
        return;
      }

      const initialData = this.collectFormData(true);
      console.log("Initial data:", initialData);
      const currentData = this.collectFormData(false);
      console.log("Current data:", currentData);

      const changedFields = this.compareData(initialData, currentData);
      console.log("Changed fields:", changedFields);

      if (Object.keys(changedFields).length === 0) {
        console.log("No changes detected, submitting form directly");
        this.submitForm(false);
        return;
      }

      this.showChangeModal(changedFields, (reasonsData) => {
        console.log("Reasons data received:", reasonsData);
        this.saveAuditData(changedFields, reasonsData, () => {
          console.log("Audit data saved, now submitting form");
          this.submitForm(false);
        });
      });
    });
  },

  validateForm: function() {
    let hasErrors = false;
    const errorMessages = [];

    // Validation cho TRANSFERHOSP
    if ($('input[name="TRANSFERHOSP"]:checked').val() === 'Yes') {
      if (!$('textarea[name="TRANSFERREASON"]').val().trim()) {
        hasErrors = true;
        errorMessages.push('Vui lòng nhập lý do chuyển viện.');
      }
      if (!$('input[name="TRANSFERLOCATION"]').val().trim()) {
        hasErrors = true;
        errorMessages.push('Vui lòng nhập nơi chuyển viện.');
      }
    }

    // Validation cho DEATHATDISCH
    if ($('input[name="DEATHATDISCH"]:checked').val() === 'Yes') {
      if (!$('textarea[name="DEATHCAUSE"]').val().trim()) {
        hasErrors = true;
        errorMessages.push('Vui lòng nhập nguyên nhân tử vong.');
      }
    }

    // Validation cho ICD formset
    let hasIcdData = false;
    $('#icd-formset .icd-form').each(function() {
      const hasData = (
        $(this).find('input[name$="-ICDCODE"]').val() ||
        $(this).find('textarea[name$="-ICDDETAIL"]').val()
      );
      const hasId = $(this).find('input[name$="-id"]').val();
      if (hasId || hasData) {
        hasIcdData = true;
        return false;
      }
    });
    if (!hasIcdData) {
      hasErrors = true;
      errorMessages.push('Vui lòng nhập ít nhất một mã ICD.');
    }

    if (hasErrors) {
      this.showMessage('Có lỗi trong form:\n\n' + errorMessages.join('\n'), 'danger');
      return true;
    }
    return false;
  },

  collectFormData: function(useInitialValues = false) {
    const data = {
      main: {},
      icd: []
    };

    const form = document.getElementById('dischargeForm');
    if (!form) {
      console.error("Form dischargeForm not found");
      return data;
    }

    // Thu thập dữ liệu từ form chính
    const mainFields = form.querySelectorAll('input:not([type="hidden"]), select, textarea');
    mainFields.forEach(field => {
      const name = field.name;
      if (name && !name.includes('_set-') && name !== 'csrfmiddlewaretoken' && 
          name !== 'oldDataJson' && name !== 'newDataJson' && 
          name !== 'reasonsJson' && name !== 'change_reason') {
        let value = '';
        if (useInitialValues) {
          value = field.getAttribute('data-initial-value') || '';
        } else {
          if (field.type === 'checkbox') {
            value = field.checked ? 'True' : 'False';
          } else if (field.type === 'radio') {
            const radioGroup = document.querySelectorAll(`input[name="${name}"]:checked`);
            value = radioGroup.length > 0 ? radioGroup[0].value : '';
          } else {
            value = field.value || '';
          }
        }
        data.main[name] = value;
      }
    });

    // Thu thập dữ liệu từ formset ICD
    const icdRows = document.querySelectorAll('.icd-form');
    icdRows.forEach((row, rowIndex) => {
      const rowData = {};
      const inputs = row.querySelectorAll('input, select, textarea');
      
      inputs.forEach(input => {
        const name = input.name;
        if (name && !name.includes('-DELETE') && !name.includes('-id') && !name.includes('-discharge_case')) {
          const fieldMatch = name.match(/icd_set-\d+-(\w+)/);
          if (fieldMatch && fieldMatch[1]) {
            const fieldName = fieldMatch[1];
            let value = '';
            if (useInitialValues) {
              value = input.getAttribute('data-initial-value') || '';
            } else {
              if (input.type === 'checkbox') {
                value = input.checked ? 'True' : 'False';
              } else if (input.type === 'radio') {
                const radioGroup = document.querySelectorAll(`input[name="${name}"]:checked`);
                value = radioGroup.length > 0 ? radioGroup[0].value : '';
              } else {
                value = input.value || '';
              }
            }
            rowData[fieldName] = value;
          }
        }
      });
      
      if (Object.keys(rowData).length > 0) {
        data.icd.push(rowData);
      }
    });

    console.log("Collected data:", data);
    return data;
  },

  compareData: function(initialData, currentData) {
    const changedFields = {};
    const fieldLabels = this.getFieldLabels();
    const fieldTypes = this.getFieldTypes();
    const fieldOptions = this.getFieldOptions();

    // So sánh các trường chính
    for (const key in currentData.main) {
      if (initialData.main[key] !== undefined) {
        const oldValue = AuditLogBase.normalizeValue(initialData.main[key] || '');
        const newValue = AuditLogBase.normalizeValue(currentData.main[key] || '');
        if (oldValue !== newValue) {
          changedFields[key] = {
            old: initialData.main[key] || '',
            new: currentData.main[key] || '',
            label: fieldLabels.main[key] || key,
            type: fieldTypes[key] || 'text',
            options: fieldOptions[key] || {}
          };
        }
      }
    }

    // So sánh formset ICD
    const icdOldRows = initialData.icd || [];
    const icdNewRows = currentData.icd || [];
    const icdMaxLength = Math.max(icdOldRows.length, icdNewRows.length);
    
    for (let i = 0; i < icdMaxLength; i++) {
      const oldRow = icdOldRows[i] || {};
      const newRow = icdNewRows[i] || {};
      Object.keys(fieldLabels.icd || {}).forEach(field => {
        const fieldKey = `icd_${i}_${field}`;
        const oldValue = AuditLogBase.normalizeValue(oldRow[field] || '');
        const newValue = AuditLogBase.normalizeValue(newRow[field] || '');
        if (oldValue !== newValue) {
          changedFields[fieldKey] = {
            old: oldRow[field] || '',
            new: newRow[field] || '',
            label: `${fieldLabels.icd[field] || field} (ICD ${i + 1})`,
            type: fieldTypes[field] || 'text',
            options: fieldOptions[field] || {}
          };
        }
      });
    }

    console.log("Compared fields, result:", changedFields);
    return changedFields;
  },

  getFieldLabels: function() {
    return {
      main: {
        'DISCHDATE': 'Ngày xuất viện',
        'DISCHSTATUS': 'Tình trạng khi xuất viện',
        'DISCHSTATUSDETAIL': 'Chi tiết về tình trạng khi xuất viện',
        'TRANSFERHOSP': 'Bệnh nhân chuyển sang bệnh viện khác?',
        'TRANSFERREASON': 'Lý do chuyển viện',
        'TRANSFERLOCATION': 'Nơi chuyển viện',
        'DEATHATDISCH': 'Bệnh nhân tử vong tại thời điểm ra viện?',
        'DEATHCAUSE': 'Nguyên nhân tử vong',
        'COMPLETEDBY': 'Người hoàn thành',
        'COMPLETEDDATE': 'Ngày hoàn thành'
      },
      icd: {
        'EPISODE': 'Thứ tự',
        'ICDCODE': 'Mã ICD-10',
        'ICDDETAIL': 'Chi tiết chẩn đoán'
      }
    };
  },

  getFieldTypes: function() {
    return {
      'DISCHDATE': 'date',
      'DISCHSTATUS': 'select',
      'DISCHSTATUSDETAIL': 'textarea',
      'TRANSFERHOSP': 'radio',
      'TRANSFERREASON': 'textarea',
      'TRANSFERLOCATION': 'text',
      'DEATHATDISCH': 'radio',
      'DEATHCAUSE': 'textarea',
      'COMPLETEDBY': 'text',
      'COMPLETEDDATE': 'date',
      'EPISODE': 'number',
      'ICDCODE': 'text',
      'ICDDETAIL': 'textarea'
    };
  },

  getFieldOptions: function() {
    return {
      'DISCHSTATUS': {
        'Recovered': 'Xuất viện và hồi phục hoàn toàn',
        'Improved': 'Xuất viện mà chưa hồi phục hoàn toàn',
        'Died': 'Tử vong hoặc hấp hối',
        'TransferredLeft': 'Bộ viện/Xin ra viện khi chưa hoàn thành điều trị'
      },
      'TRANSFERHOSP': { 'Yes': 'Có', 'No': 'Không', 'NA': 'Không áp dụng' },
      'DEATHATDISCH': { 'Yes': 'Có', 'No': 'Không', 'NA': 'Không áp dụng' }
    };
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

  showChangeModal: function(changedFields, callback) {
    console.log("DischargeFormAudit.showChangeModal called with:", changedFields);
    if (!document.getElementById('changeReasonModal')) {
      console.error("Change reason modal not found in DOM! Check base.html inclusion.");
      this.showMessage('Không thể hiển thị modal nhập lý do thay đổi', 'danger');
      this.resetProcessingState();
      return;
    }

    if (typeof AuditLogBase === 'undefined') {
      console.error("AuditLogBase is not defined! Ensure base.js is loaded.");
      this.showMessage('Lỗi: base.js chưa được tải', 'danger');
      this.resetProcessingState();
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

    try {
      console.log("Attempting to show change modal with fields:", changedFields);
      window.AuditLogBase.showChangeModal(changedFields, (reasonsData) => {
        console.log("Reasons data received from modal:", reasonsData);
        if (callback && typeof callback === 'function') {
          callback(reasonsData);
        } else {
          console.error("Callback for showChangeModal is not a function");
          self.resetProcessingState();
        }
      });
    } catch (error) {
      console.error("Error showing change modal:", error);
      this.showMessage('Có lỗi khi hiển thị modal lý do thay đổi: ' + error.message, 'danger');
      this.resetProcessingState();
    }
  },

  saveAuditData: function(changedFields, reasonsData, callback) {
    console.log("Saving audit data with changedFields:", changedFields, "and reasonsData:", reasonsData);
    
    const initialData = this.collectFormData(true);
    const currentData = this.collectFormData(false);
    
    const oldData = {};
    for (const key in initialData.main) {
      oldData[key] = initialData.main[key];
    }
    initialData.icd.forEach((item, idx) => {
      if (item) {
        for (const field in item) {
          oldData[`icd_${idx}_${field}`] = item[field];
        }
      }
    });

    const newData = {};
    for (const key in currentData.main) {
      newData[key] = currentData.main[key];
    }
    currentData.icd.forEach((item, idx) => {
      if (item) {
        for (const field in item) {
          newData[`icd_${idx}_${field}`] = item[field];
        }
      }
    });

    const reasonsJsonWithLabel = {};
    Object.keys(changedFields).forEach(key => {
      let reasonText = "";
      if (key in reasonsData) {
        reasonText = reasonsData[key];
      } else if (key.toUpperCase() in reasonsData) {
        reasonText = reasonsData[key.toUpperCase()];
      } else if (key.toLowerCase() in reasonsData) {
        reasonText = reasonsData[key.toLowerCase()];
      } else if (key.includes('icd_')) {
        const [prefix, index, field] = key.split('_');
        const episode = parseInt(index) + 1;
        const possibleKeys = [
          `icd-${episode}-${field}`,
          `icd_set-${index}-${field}`,
          `icd_${index}_${field}`,
          `${field}`
        ];
        
        for (const altKey of possibleKeys) {
          if (altKey in reasonsData) {
            reasonText = reasonsData[altKey];
            break;
          }
        }
      }
      
      if (!reasonText) {
        reasonText = "Cập nhật thông tin";
      }

      let label = changedFields[key].label || key;
      reasonsJsonWithLabel[key] = {
        label: label,
        reason: reasonText
      };
    });

    const form = document.getElementById('dischargeForm');
    if (!form) {
      console.error("Form dischargeForm not found!");
      this.resetProcessingState();
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

    console.log("Audit data saved for form dischargeForm:", { oldData, newData, reasonsJsonWithLabel, changeReason });

    if (callback) callback();
  },

  submitForm: function(isCreate = false) {
    const form = document.getElementById('dischargeForm');
    const $btn = $('#btnSaveDischarge');
    const originalHtml = $btn.html();
    const usubjid = form.action.match(/\/43en\/([^/]+)\/discharge\/(update|create)\//)?.[1] || window.location.pathname.split('/')[2];

    const formData = new FormData(form);
    console.log("Submitting form with data:", Array.from(formData.entries()));

    const csrftoken = $('input[name="csrfmiddlewaretoken"]').val();
    if (!csrftoken) {
      console.error("CSRF token not found!");
      this.showMessage('Lỗi: Không tìm thấy CSRF token', 'danger');
      this.resetProcessingState();
      return;
    }

    $btn.html('<i class="fas fa-spinner fa-spin"></i> Đang lưu...').prop('disabled', true);

    const url = isCreate ? `/43en/${usubjid}/discharge/create/` : `/43en/${usubjid}/discharge/update/`;
    console.log(`Sending AJAX request to: ${url}`);

    $.ajax({
      url: url,
      method: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      headers: {
        'X-CSRFToken': csrftoken
      },
      success: (response) => {
        console.log("Request success:", response);
        if (response.success) {
          this.showMessage('Đã lưu thông tin xuất viện thành công!', 'success');
          setTimeout(() => {
            window.location.href = response.redirect_url || `/43en/patient/${usubjid}/`;
          }, 500);
        } else {
          $btn.html(originalHtml).prop('disabled', false);
          this.resetProcessingState();
          this.showMessage(response.message || 'Có lỗi xảy ra khi lưu', 'danger');
        }
      },
      error: (xhr, status, error) => {
        console.error("Request error:", error, xhr.status, xhr.responseText);
        $btn.html(originalHtml).prop('disabled', false);
        this.resetProcessingState();
        let errorMsg = 'Có lỗi xảy ra khi lưu. Vui lòng kiểm tra lại.';
        try {
          const response = JSON.parse(xhr.responseText);
          if (response.message) {
            errorMsg = response.message;
            if (response.errors) {
              errorMsg += '\nChi tiết lỗi:\n' + JSON.stringify(response.errors, null, 2);
            }
          }
        } catch (e) {
          console.error("Could not parse error response:", e, "Response text:", xhr.responseText);
          errorMsg += '\nPhản hồi server không phải JSON:\n' + xhr.responseText.substring(0, 200);
        }
        this.showMessage(errorMsg, 'danger');
      }
    });
  },

  setupSpecialHandlers: function() {
    const transferRadios = document.querySelectorAll('input[name="TRANSFERHOSP"]');
    transferRadios.forEach(radio => {
      radio.addEventListener('change', () => {
        const show = radio.value === 'Yes';
        const section = document.getElementById('transfer-details');
        if (section) {
          section.style.display = show ? 'block' : 'none';
          console.log(`TRANSFERHOSP changed to ${radio.value}, transfer-details display: ${section.style.display}`);
        }
      });
    });

    const deathRadios = document.querySelectorAll('input[name="DEATHATDISCH"]');
    deathRadios.forEach(radio => {
      radio.addEventListener('change', () => {
        const show = radio.value === 'Yes';
        const section = document.getElementById('death-details');
        if (section) {
          section.style.display = show ? 'block' : 'none';
          console.log(`DEATHATDISCH changed to ${radio.value}, death-details display: ${section.style.display}`);
        }
      });
    });

    const addButton = document.querySelector('#add-icd');
    if (addButton) {
      addButton.addEventListener('click', () => {
        console.log("Add ICD button clicked");
        setTimeout(() => {
          this.setupFormsetInitialValues();
        }, 100);
      });
    }
  }
};

// Khởi tạo khi DOM ready
$(document).ready(function() {
  const form = document.getElementById('dischargeForm');
  const isViewOnly = form && form.classList.contains('readonly-form');

  if (!isViewOnly) {
    console.log("Initializing DischargeFormAudit");
    window.DischargeFormAudit.init();
  } else {
    console.log("Form is in view-only mode, skipping audit initialization");
  }
});