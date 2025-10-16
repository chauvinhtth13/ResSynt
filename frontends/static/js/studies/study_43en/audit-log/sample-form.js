// Sample Collection Form Audit Logging
// Tích hợp với base.js để ghi lại log cho form thu thập mẫu

window.SampleCollectionFormAudit = {
  isProcessing: false, // Thêm trạng thái để tránh submit kép
  
  // Phương thức reset trạng thái xử lý
  resetProcessingState: function() {
    console.log("Resetting processing state");
    this.isProcessing = false;
    
    // Đảm bảo nút không bị disabled
    const saveButton = document.getElementById('btnSaveSample');
    if (saveButton) {
      saveButton.disabled = false;
      if (saveButton.innerHTML.includes('fa-spinner')) {
        saveButton.innerHTML = '<i class="fas fa-save"></i> Cập Nhật';
      }
    }
  },
  
  init: function() {
    console.log("Initializing Sample Collection Form Audit Logging");

    if (this.isViewOnly()) {
      console.log("View-only mode, disabling audit logging");
      return;
    }

    this.setupInitialValues();
    this.setupFormSubmission();
    this.setupModalHandlers();
    console.log("Sample Collection Form Audit Logging initialized successfully");
  },
  
  // Thiết lập handlers cho modals để tránh trạng thái bị kẹt
  setupModalHandlers: function() {
    const self = this;
    
    // Reset trạng thái khi đóng modal change reason
    $('#changeReasonModal').on('hidden.bs.modal', function() {
      console.log("Change reason modal hidden, resetting processing state");
      self.resetProcessingState();
    });
    
    // Reset trạng thái khi người dùng nhấn ESC
    $(document).on('keydown.auditEscape', function(e) {
      if (e.key === 'Escape' && $('#changeReasonModal').is(':visible')) {
        console.log("Escape key detected in change reason modal, resetting processing state");
        self.resetProcessingState();
      }
    });
  },

  isViewOnly: function() {
    return document.querySelector('.readonly-form') !== null;
  },

  setupInitialValues: function() {
    console.log("Setting up initial values for audit logging");

    const form = document.getElementById('sampleCollectionForm');
    if (form) {
      const fields = form.querySelectorAll('input, select, textarea');
      fields.forEach(field => {
        if (field.name && field.name !== 'csrfmiddlewaretoken' && field.name !== 'form_submitted' && field.name !== 'force_save' && field.name !== 'debug_info' && field.name !== 'sample_type') {
          let value = '';
          if (field.type === 'checkbox' || field.type === 'radio') {
            value = field.checked ? 'True' : 'False';
          } else {
            value = field.value || '';
          }
          field.setAttribute('data-initial-value', value);
          console.log(`Set initial value for ${field.name}: ${value}`);
        }
      });
    }
  },

  setupFormSubmission: function() {
    const saveButton = document.getElementById('btnSaveSample');
    if (!saveButton) {
      console.warn("Save button not found");
      return;
    }

    $(document).off('click', '#btnSaveSample');
    $(saveButton).off('click');
    saveButton.onclick = null;

    $(saveButton).on('click', (e) => {
      e.preventDefault();
      console.log("Save button clicked");

      // Prevent multiple submissions
      if (this.isProcessing) {
        console.log("Form is already processing, preventing duplicate submission");
        return false;
      }
      
      this.isProcessing = true;

      // Validate
      const isSampleYes = $('input[name="SAMPLE"][value="True"]').is(':checked');
      if (!isSampleYes) {
        const reason = $('#id_REASONIFNO').val().trim();
        if (reason === '') {
          this.showMessage('Vui lòng nhập lý do không thu thập được mẫu', 'warning');
          $('#id_REASONIFNO').focus();
          this.resetProcessingState();
          return;
        }
      } else {
        const hasAnyChecked = $('#id_BLOOD').is(':checked') ||
                              $('#id_STOOL').is(':checked') ||
                              $('#id_THROATSWAB').is(':checked') ||
                              $('#id_RECTSWAB').is(':checked');
        if (!hasAnyChecked) {
          this.showMessage('Vui lòng chọn ít nhất một loại mẫu', 'warning');
          this.resetProcessingState();
          return;
        }
      }

      const form = document.getElementById('sampleCollectionForm');
      // Kiểm tra xem form có phải là form tạo mới không
      const isNew = form.getAttribute('data-is-new') === 'true';
      if (isNew) {
        // Submit truyền thống cho tạo mới
        form.submit();
        return;
      }

      // Thu thập dữ liệu cho cập nhật
      const currentData = this.collectFormData(false);
      const initialData = this.collectFormData(true);
      console.log("Initial data:", initialData);
      console.log("Current data:", currentData);

      const changedFields = this.compareData(initialData, currentData);
      console.log("Changed fields:", changedFields);

      if (Object.keys(changedFields).length === 0) {
        this.showMessage('Không có thay đổi để lưu', 'info');
        $('#btnSaveSample').html('<i class="fas fa-save"></i> Cập Nhật').prop('disabled', false);
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
    const form = document.getElementById('sampleCollectionForm');
    if (!form) return data;

    const inputs = form.querySelectorAll('input:not([type="hidden"]), select, textarea');
    inputs.forEach(input => {
      if (input.name && input.name !== 'csrfmiddlewaretoken' && input.name !== 'form_submitted' && input.name !== 'force_save' && input.name !== 'debug_info' && input.name !== 'sample_type') {
        if (useInitialValues) {
          const initialValue = input.getAttribute('data-initial-value') || '';
          data[input.name] = initialValue;
        } else {
          if (input.type === 'checkbox' || input.type === 'radio') {
            data[input.name] = input.checked ? 'True' : 'False';
          } else {
            data[input.name] = input.value || '';
          }
        }
      }
    });

    return data;
  },

  compareData: function(oldData, newData) {
    const fieldOptions = this.getFieldOptions();
    const changedFields = window.AuditLogBase.compareFields(
      oldData,
      newData,
      this.getFieldLabels(),
      this.getFieldTypes(),
      this.getFieldOptions()
    );

    // Ánh xạ giá trị hiển thị cho các trường select và boolean
    Object.keys(changedFields).forEach(key => {
      if (key in fieldOptions) {
        const options = fieldOptions[key];
        changedFields[key].old = options[changedFields[key].old] || changedFields[key].old;
        changedFields[key].new = options[changedFields[key].new] || changedFields[key].new;
      } else if (this.getFieldTypes()[key] === 'boolean') {
        changedFields[key].old = changedFields[key].old === 'True' ? 'Có' : 'Không';
        changedFields[key].new = changedFields[key].new === 'True' ? 'Có' : 'Không';
      }
    });

    return changedFields;
  },

  getFieldLabels: function() {
    return {
      'SAMPLE': 'Mẫu lần thu nhận',
      'STOOL': 'Phân',
      'STOOLDATE': 'Ngày lấy mẫu phân',
      'RECTSWAB': 'Phết trực tràng',
      'RECTSWABDATE': 'Ngày lấy mẫu phết trực tràng',
      'THROATSWAB': 'Phết họng',
      'THROATSWABDATE': 'Ngày lấy mẫu phết họng',
      'BLOOD': 'Mẫu máu',
      'BLOODDATE': 'Ngày lấy mẫu máu',
      'REASONIFNO': 'Lý do không thu nhận được mẫu',
      'CULTRES_1': 'Kết quả nuôi cấy mẫu phân',
      'KLEBPNEU_1': 'Klebsiella pneumoniae (Phân)',
      'OTHERRES_1': 'Khác (Phân)',
      'OTHERRESSPECIFY_1': 'Ghi rõ (Phân)',
      'CULTRES_2': 'Kết quả nuôi cấy mẫu phết trực tràng',
      'KLEBPNEU_2': 'Klebsiella pneumoniae (Phết trực tràng)',
      'OTHERRES_2': 'Khác (Phết trực tràng)',
      'OTHERRESSPECIFY_2': 'Ghi rõ (Phết trực tràng)',
      'CULTRES_3': 'Kết quả nuôi cấy mẫu phết họng',
      'KLEBPNEU_3': 'Klebsiella pneumoniae (Phết họng)',
      'OTHERRES_3': 'Khác (Phết họng)',
      'OTHERRESSPECIFY_3': 'Ghi rõ (Phết họng)',
      'COMPLETEDBY': 'Người hoàn thành',
      'COMPLETEDDATE': 'Ngày hoàn thành'
    };
  },

  getFieldTypes: function() {
    return {
      'SAMPLE': 'boolean',
      'STOOL': 'boolean',
      'STOOLDATE': 'date',
      'RECTSWAB': 'boolean',
      'RECTSWABDATE': 'date',
      'THROATSWAB': 'boolean',
      'THROATSWABDATE': 'date',
      'BLOOD': 'boolean',
      'BLOODDATE': 'date',
      'REASONIFNO': 'text',
      'CULTRES_1': 'select',
      'KLEBPNEU_1': 'boolean',
      'OTHERRES_1': 'boolean',
      'OTHERRESSPECIFY_1': 'text',
      'CULTRES_2': 'select',
      'KLEBPNEU_2': 'boolean',
      'OTHERRES_2': 'boolean',
      'OTHERRESSPECIFY_2': 'text',
      'CULTRES_3': 'select',
      'KLEBPNEU_3': 'boolean',
      'OTHERRES_3': 'boolean',
      'OTHERRESSPECIFY_3': 'text',
      'COMPLETEDBY': 'text',
      'COMPLETEDDATE': 'date'
    };
  },

  getFieldOptions: function() {
    return {
      'CULTRES_1': {
        'Pos': 'Dương tính',
        'Neg': 'Âm tính',
        'NoApply': 'Không áp dụng',
        'NotPerformed': 'Không thực hiện'
      },
      'CULTRES_2': {
        'Pos': 'Dương tính',
        'Neg': 'Âm tính',
        'NoApply': 'Không áp dụng',
        'NotPerformed': 'Không thực hiện'
      },
      'CULTRES_3': {
        'Pos': 'Dương tính',
        'Neg': 'Âm tính',
        'NoApply': 'Không áp dụng',
        'NotPerformed': 'Không thực hiện'
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
    console.log("SampleCollectionFormAudit.showChangeModal called with:", changedFields);
    if (!document.getElementById('changeReasonModal')) {
      console.error("Change reason modal not found!");
      return;
    }
    
    // Prevent automatic submission when modal is shown
    const self = this;
    const originalShowModalFn = window.AuditLogBase.showChangeModal;
    
    window.AuditLogBase.showChangeModal = function(fields, cb) {
      // Set processing state to prevent double submission
      self.isProcessing = true;
      
      // Replace the callback to include our reset logic
      const wrappedCallback = function(reasonsData) {
        console.log("Change modal callback executed with reasons:", reasonsData);
        if (cb) cb(reasonsData);
      };
      
      // Show the modal with our wrapped callback
      originalShowModalFn.call(window.AuditLogBase, fields, wrappedCallback);
      
      // Restore the original function
      window.AuditLogBase.showChangeModal = originalShowModalFn;
    };
    
    // Call the function with our changes applied
    window.AuditLogBase.showChangeModal(changedFields, callback);
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

    const form = document.getElementById('sampleCollectionForm');
    if (!form) {
      console.error("Form sampleCollectionForm not found!");
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

    console.log("Audit data saved for form sampleCollectionForm:", { oldData, newData, reasonsJsonWithLabel, changeReason });

    if (callback) callback();
  },

  submitForm: function() {
    const form = document.getElementById('sampleCollectionForm');
    const $btn = $('#btnSaveSample');
    const originalHtml = $btn.html();
    const usubjid = window.location.pathname.split('/')[2];
    const sampleType = form.querySelector('[name="sample_type"]').value;

    const formData = new FormData(form);
    console.log("Submitting form with data:", Array.from(formData.entries()));

    $btn.html('<i class="fas fa-spinner fa-spin"></i> Đang lưu...').prop('disabled', true);

    $.ajax({
      url: `/43en/${usubjid}/samples/${sampleType}/update/`,
      method: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: (response) => {
        console.log("Update success:", response);
        if (response.success) {
          this.showMessage('Đã cập nhật thông tin mẫu thu thập thành công!', 'success');
          setTimeout(() => {
            window.location.href = `/43en/${usubjid}/samples/`;
          }, 500);
        } else {
          $btn.html(originalHtml).prop('disabled', false);
          this.resetProcessingState(); // Reset processing state on error
          this.showMessage(response.message || 'Có lỗi xảy ra khi cập nhật', 'danger');
        }
      },
      error: (xhr, status, error) => {
        console.error("Update error:", error);
        $btn.html(originalHtml).prop('disabled', false);
        this.resetProcessingState(); // Reset processing state on error
        let errorMsg = 'Có lỗi xảy ra khi cập nhật mẫu';
        try {
          const response = JSON.parse(xhr.responseText);
          if (response.message) errorMsg = response.message;
        } catch (e) {
          console.log("Could not parse error response");
        }
        this.showMessage(errorMsg, 'danger');
      }
    });
  }
};

// Khởi tạo khi DOM ready
$(document).ready(function() {
  window.SampleCollectionFormAudit.init();
});