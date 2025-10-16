// EndCaseCRF Form Audit Logging
// Tích hợp với base.js để ghi lại log cho form kết thúc nghiên cứu

window.EndCaseCRFAudit = {
  isProcessing: false,

  init: function() {
    console.log("Initializing EndCaseCRF Form Audit Logging");

    const form = document.getElementById('endcaseForm');
    if (!form) {
      console.warn("EndCaseCRF form not found");
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
    console.log("EndCaseCRF Form Audit Logging initialized successfully");
  },

  isViewOnly: function() {
    return document.querySelector('.view-only-form') !== null;
  },

  resetProcessingState: function() {
    console.log("Resetting processing state");
    this.isProcessing = false;
    const saveButton = document.getElementById('btnSaveEndcase');
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

    const form = document.getElementById('endcaseForm');
    if (!form) {
      console.error("EndCaseCRF form not found for initial values setup");
      return;
    }

    const fields = document.querySelectorAll('#endcaseForm input:not([type="hidden"]), #endcaseForm select, #endcaseForm textarea');
    console.log("Found", fields.length, "fields to set initial values for");

    fields.forEach(field => {
      const name = field.name;
      if (!name || name === 'csrfmiddlewaretoken' || name === 'oldDataJson' || name === 'newDataJson' || name === 'reasonsJson' || name === 'change_reason') return;

      let initialValue = '';
      if (field.type === 'checkbox') {
        initialValue = field.checked ? 'True' : 'False';
      } else if (field.type === 'radio') {
        const radioGroup = document.querySelectorAll(`input[name="${name}"]:checked`);
        initialValue = radioGroup.length > 0 ? radioGroup[0].value : 'na';
      } else {
        initialValue = field.value || '';
      }

      field.setAttribute('data-initial-value', initialValue);
      console.log(`Field ${name}: initial value = "${initialValue}"`);
    });
  },

  setupFormSubmission: function() {
    const saveButton = document.getElementById('btnSaveLabTests');
    if (!saveButton) {
      console.error("Save button 'btnSaveLabTests' not found");
      return;
    }

    console.log("Attaching click event to btnSaveLabTests");
    $(document).off('click', '#btnSaveLabTests');
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

      const form = document.getElementById('lab-form');
      // Thu thập dữ liệu ban đầu (từ data-initial-value)
      const initialData = this.collectFormData(true);
      console.log("Initial data:", initialData);
      // Thu thập dữ liệu hiện tại
      const currentData = this.collectFormData(false);
      console.log("Current data:", currentData);

      const changedFields = this.findChanges(initialData, currentData);
      console.log("Changed fields:", changedFields);

      if (changedFields.length === 0) {
        console.log("No changes detected, submitting form directly");
        this.submitForm();
        return;
      }

      this.showChangeReasonModal(changedFields, (reasonsData) => {
        console.log("Reasons data received:", reasonsData);
        this.saveAuditData(changedFields, reasonsData, () => {
          console.log("Audit data saved, now submitting form");
          this.submitForm();
        });
      });
    });
  },

  validateForm: function() {
    let hasErrors = false;
    const errorMessages = [];

    // Validation cho INCOMPLETE
    if ($('input[name="INCOMPLETE"]:checked').val() === 'yes') {
      const deathChecked = $('#id_INCOMPLETEDEATH').is(':checked');
      const movedChecked = $('#id_INCOMPLETEMOVED').is(':checked');
      const otherValue = $('#id_INCOMPLETEOTHER').val().trim();
      if (!deathChecked && !movedChecked && !otherValue) {
        hasErrors = true;
        errorMessages.push('Vui lòng chọn ít nhất một lý do không hoàn tất nghiên cứu.');
      }
    }

    if (hasErrors) {
      this.showMessage('Có lỗi trong form:\n\n' + errorMessages.join('\n'), 'danger');
      return true;
    }
    return false;
  },

  collectFormData: function(useInitialValues = false) {
    const data = { main: {} };

    const form = document.getElementById('endcaseForm');
    if (!form) {
      console.error("Form endcaseForm not found");
      return data;
    }

    const fields = form.querySelectorAll('input:not([type="hidden"]), select, textarea');
    fields.forEach(field => {
      const name = field.name;
      if (name && name !== 'csrfmiddlewaretoken' && 
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

    console.log("Collected data:", data);
    return data;
  },

  compareData: function(initialData, currentData) {
    const changedFields = {};
    const fieldLabels = this.getFieldLabels();
    const fieldTypes = this.getFieldTypes();
    const fieldOptions = this.getFieldOptions();

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

    console.log("Compared fields, result:", changedFields);
    return changedFields;
  },

  getFieldLabels: function() {
    return {
      main: {
        'ENDDATE': 'Ngày ghi nhận',
        'ENDFORMDATE': 'Ngày kết thúc nghiên cứu',
        'VICOMPLETED': 'V1 (Tham gia nghiên cứu)',
        'V2COMPLETED': 'V2 (Ngày 10±3)',
        'V3COMPLETED': 'V3 (Ngày 28±3)',
        'V4COMPLETED': 'V4 (Ngày 90±3)',
        'WITHDRAWREASON': 'Lý do rút khỏi nghiên cứu',
        'INCOMPLETE': 'Không thể hoàn tất nghiên cứu',
        'INCOMPLETEDEATH': 'Người tham gia tử vong',
        'INCOMPLETEMOVED': 'Người tham gia không thể đến địa điểm nghiên cứu',
        'INCOMPLETEOTHER': 'Khác, ghi rõ',
        'LOSTTOFOLLOWUP': 'Người tham gia bị mất liên lạc'
      }
    };
  },

  getFieldTypes: function() {
    return {
      'ENDDATE': 'date',
      'ENDFORMDATE': 'date',
      'VICOMPLETED': 'checkbox',
      'V2COMPLETED': 'checkbox',
      'V3COMPLETED': 'checkbox',
      'V4COMPLETED': 'checkbox',
      'WITHDRAWREASON': 'radio',
      'INCOMPLETE': 'radio',
      'INCOMPLETEDEATH': 'checkbox',
      'INCOMPLETEMOVED': 'checkbox',
      'INCOMPLETEOTHER': 'text',
      'LOSTTOFOLLOWUP': 'radio'
    };
  },

  getFieldOptions: function() {
    return {
      'WITHDRAWREASON': {
        'withdraw': 'Rút khỏi nghiên cứu',
        'forced': 'Bị rút khỏi',
        'na': 'Không áp dụng'
      },
      'INCOMPLETE': {
        'yes': 'Có',
        'no': 'Không',
        'na': 'Không áp dụng'
      },
      'LOSTTOFOLLOWUP': {
        'yes': 'Có',
        'no': 'Không',
        'na': 'Không áp dụng'
      }
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
    console.log("EndCaseCRFAudit.showChangeModal called with:", changedFields);
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

    const newData = {};
    for (const key in currentData.main) {
      newData[key] = currentData.main[key];
    }

    const reasonsJsonWithLabel = {};
    Object.keys(changedFields).forEach(key => {
      let reasonText = "";
      if (key in reasonsData) {
        reasonText = reasonsData[key];
      } else if (key.toUpperCase() in reasonsData) {
        reasonText = reasonsData[key.toUpperCase()];
      } else if (key.toLowerCase() in reasonsData) {
        reasonText = reasonsData[key.toLowerCase()];
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

    const form = document.getElementById('endcaseForm');
    if (!form) {
      console.error("Form endcaseForm not found!");
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

    console.log("Audit data saved for form endcaseForm:", { oldData, newData, reasonsJsonWithLabel, changeReason });

    if (callback) callback();
  },

  submitForm: function(isCreate = false) {
    const form = document.getElementById('endcaseForm');
    const $btn = $('#btnSaveEndcase');
    const originalHtml = $btn.html();
    const usubjid = form.action.match(/\/43en\/patient\/([^/]+)\/endcasecrf\/(update|create)\//)?.[1] || window.location.pathname.split('/')[3];

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

    const url = isCreate ? `/43en/patient/${usubjid}/endcasecrf/create/` : `/43en/patient/${usubjid}/endcasecrf/update/`;
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
          this.showMessage('Đã lưu phiếu kết thúc nghiên cứu thành công!', 'success');
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
    const incompleteRadios = document.querySelectorAll('input[name="INCOMPLETE"]');
    incompleteRadios.forEach(radio => {
      radio.addEventListener('change', () => {
        const show = radio.value === 'yes';
        const section = document.getElementById('incomplete_reasons');
        if (section) {
          section.style.display = show ? 'block' : 'none';
          console.log(`INCOMPLETE changed to ${radio.value}, incomplete_reasons display: ${section.style.display}`);
        }
      });
    });
  }
};

// Khởi tạo khi DOM ready
$(document).ready(function() {
  const form = document.getElementById('endcaseForm');
  const isViewOnly = form && form.classList.contains('view-only-form');

  if (!isViewOnly) {
    console.log("Initializing EndCaseCRFAudit");
    window.EndCaseCRFAudit.init();
  } else {
    console.log("Form is in view-only mode, skipping audit initialization");
  }
});