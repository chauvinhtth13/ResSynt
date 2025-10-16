
// Laboratory Form Audit Logging
// Đảm bảo logic giống các CRF khác, thu thập tất cả input và hiển thị modal khi có thay đổi

const LaboratoryFormAudit = {
  // Định nghĩa TEST_TYPE_CHOICES từ models
  TEST_TYPE_CHOICES: {
    'INR': 'INR',
    'DIC': 'DIC',
    'WBC': 'Bạch cầu máu',
    'NEU': 'Neu',
    'LYM': 'Lym',
    'EOS': 'Eos',
    'RBC': 'Hồng cầu',
    'HEMOGLOBIN': 'Hemoglobin',
    'PLATELETS': 'Tiểu cầu',
    'NATRI': 'Natri máu',
    'KALI': 'Kali máu',
    'CLO': 'Clo máu',
    'MAGNE': 'Magne máu',
    'URE': 'Ure máu',
    'CREATININE': 'Creatinine máu',
    'AST': 'AST',
    'ALT': 'ALT',
    'GLUCOSEBLOOD': 'Glucose máu',
    'BEDSIDE_GLUCOSE': 'Đường huyết tại giường',
    'BILIRUBIN_TP': 'Bilirubin TP',
    'BILIRUBIN_TT': 'Bilirubin TT',
    'PROTEIN': 'Protein máu',
    'ALBUMIN': 'Albumin máu',
    'CRP_QUALITATIVE': 'Ceton máu định tính',
    'CRP_QUANTITATIVE': 'Ceton máu định lượng',
    'CRP': 'CRP',
    'PROCALCITONIN': 'Procalcitonin',
    'HBA1C': 'HbA1c',
    'CORTISOL': 'Cortisol máu',
    'HIV': 'HIV',
    'CD4': 'CD4',
    'PH': 'pH',
    'PCO2': 'pCO2',
    'PO2': 'pO2',
    'HCO3': 'HCO3',
    'BE': 'BE',
    'AADO2': 'AaDO2',
    'LACTATE_ARTERIAL': 'Lactate động mạch',
    'URINE_PH': 'pH',
    'NITRIT': 'Nitrit',
    'URINE_PROTEIN': 'Protein',
    'LEU': 'LEU',
    'URINE_RBC': 'Hồng cầu',
    'SEDIMENT': 'Cặn lắng',
    'PERITONEAL_WBC': 'Bạch cầu',
    'PERITONEAL_NEU': 'Bạch cầu đa nhân',
    'PERITONEAL_MONO': 'Bạch cầu đơn nhân',
    'PERITONEAL_RBC': 'Hồng cầu',
    'PERITONEAL_PROTEIN': 'Protein',
    'PERITONEAL_PROTEIN_BLOOD': 'Protein máu',
    'PERITONEAL_ALBUMIN': 'Albumin',
    'PERITONEAL_ALBUMIN_BLOOD': 'Albumin máu',
    'PERITONEAL_ADA': 'ADA',
    'PERITONEAL_CELLBLOCK': 'Cell block',
    'PLEURAL_WBC': 'Bạch cầu',
    'PLEURAL_NEU': 'Bạch cầu đa nhân',
    'PLEURAL_MONO': 'Bạch cầu đơn nhân',
    'PLEURAL_EOS': 'Eos',
    'PLEURAL_RBC': 'Hồng cầu',
    'PLEURAL_PROTEIN': 'Protein',
    'PLEURAL_LDH': 'LDH',
    'PLEURAL_LDH_BLOOD': 'LDH máu',
    'PLEURAL_ADA': 'ADA',
    'PLEURAL_CELLBLOCK': 'Cell block',
    'CSF_WBC': 'Bạch cầu',
    'CSF_NEU': 'Bạch cầu đa nhân',
    'CSF_MONO': 'Bạch cầu đơn nhân',
    'CSF_EOS': 'Eos',
    'CSF_RBC': 'Hồng cầu',
    'CSF_PROTEIN': 'Protein',
    'CSF_GLUCOSE': 'Glucose',
    'CSF_LACTATE': 'Lactate',
    'CSF_GRAM_STAIN': 'Nhuộm Gram',
    'CHEST_XRAY': 'X-quang ngực thẳng',
    'ABDOMINAL_ULTRASOUND': 'Siêu âm bụng',
    'BRAIN_CT_MRI': 'CT scan sọ não/MRI não',
    'CHEST_ABDOMEN_CT': 'CT ngực bụng',
    'ECHOCARDIOGRAPHY': 'Siêu âm tim',
    'SOFT_TISSUE_ULTRASOUND': 'Siêu âm mô mềm'
  },

  isProcessing: false,

  init: function() {
    console.log("Initializing Laboratory Form Audit Logging");

    const form = document.getElementById('lab-form');
    if (!form) {
      console.error("Laboratory form not found");
      return;
    }

    if (this.isViewOnly()) {
      console.log("View-only mode, disabling audit logging");
      return;
    }

    console.log("Setting up initial values and event handlers");
    this.setupInitialValues();
    this.setupFormSubmission();
    this.setupSpecialHandlers();
    console.log("Laboratory Form Audit Logging initialized successfully");
  },

  isViewOnly: function() {
    return document.querySelector('.view-only-form') !== null;
  },

  resetProcessingState: function() {
    console.log("Resetting processing state");
    this.isProcessing = false;
    const saveButtons = document.querySelectorAll('#btnSaveLabTests, #btnSaveLabTestsBottom');
    saveButtons.forEach(button => {
      button.disabled = false;
      if (button.innerHTML.includes('fa-spinner')) {
        button.innerHTML = '<i class="fas fa-save"></i> ' + 
                          (button.id === 'btnSaveLabTests' ? 'Lưu thông tin' : 'Tạo mới xét nghiệm');
      }
    });
  },

  setupInitialValues: function() {
    console.log("Setting up initial values for audit logging");

    const form = document.getElementById('lab-form');
    if (!form) {
      console.error("Laboratory form not found for initial values setup");
      return;
    }

    const allInputs = form.querySelectorAll('input, select, textarea');
    console.log(`Found ${allInputs.length} inputs to set initial values`);

    allInputs.forEach(input => {
      const name = input.name;
      if (!name || name === 'csrfmiddlewaretoken' || name.includes('-DELETE') || 
          name === 'oldDataJson' || name === 'newDataJson' || 
          name === 'reasonsJson' || name === 'change_reason') {
        return;
      }

      let initialValue = '';
      if (input.type === 'checkbox') {
        initialValue = input.checked ? 'True' : 'False';
      } else if (input.type === 'radio') {
        if (input.checked) {
          initialValue = input.value || '';
        } else {
          return;
        }
      } else {
        initialValue = input.value || '';
      }

      input.setAttribute('data-initial-value', initialValue);
      console.log(`Field ${name}: initial value = "${initialValue}"`);
    });

    // Ensure hidden inputs exist
    const requiredInputs = ['oldDataJson', 'newDataJson', 'reasonsJson', 'change_reason'];
    requiredInputs.forEach(inputId => {
      if (!document.getElementById(inputId)) {
        console.log(`Creating ${inputId} input element`);
        const input = document.createElement('input');
        input.type = 'hidden';
        input.id = inputId;
        input.name = inputId;
        form.appendChild(input);
      }
    });

    // Thu thập dữ liệu ban đầu
    const initialData = this.collectFormData();
    document.getElementById('oldDataJson').value = JSON.stringify(initialData);
    console.log("Initial data collected:", initialData);
  },

  setupFormSubmission: function() {
    // Chọn tất cả các nút có ID btnSaveLabTests hoặc btnSaveLabTestsBottom
    const saveButtons = document.querySelectorAll('#btnSaveLabTests, #btnSaveLabTestsBottom');
    if (saveButtons.length === 0) {
      console.error("Save buttons not found");
      return;
    }

    console.log(`Found ${saveButtons.length} save buttons, attaching events`);
    
    // Xóa các event handlers cũ
    $(document).off('click', '#btnSaveLabTests, #btnSaveLabTestsBottom');
    $('#lab-form').off('submit');
    
    // Ngăn chặn form submit mặc định
    $('#lab-form').on('submit', function(e) {
      e.preventDefault();
      console.log("Form submit intercepted");
      return false;
    });
    
    // Gắn sự kiện cho tất cả các nút
    saveButtons.forEach(button => {
      $(button).off('click').on('click', (e) => {
        e.preventDefault();
        console.log("Save button clicked:", button.id);

        if (this.isProcessing) {
          console.log("Form is already processing, preventing duplicate submission");
          return;
        }
        this.isProcessing = true;

        // Kiểm tra xem có phải là nút tạo mới không
        const isCreateButton = button.innerText.includes('Tạo Mới Xét Nghiệm');
        if (isCreateButton) {
          console.log("Đây là nút tạo mới xét nghiệm, bỏ qua kiểm tra validation và thay đổi");
          this.submitForm();
          return;
        }

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
    });
  },

  validateForm: function() {
    let hasErrors = false;
    const errorMessages = [];

    const form = document.getElementById('lab-form');
    const performedInputs = form.querySelectorAll('input[name$="-PERFORMED"]:checked, input[name^="new_performed_"]:checked');
    performedInputs.forEach(input => {
      const prefix = input.name.includes('new_performed_') ? input.name.replace('new_performed_', '') : input.name.replace('-PERFORMED', '');
      const dateInput = form.querySelector(`input[name="${prefix}-PERFORMEDDATE"], input[name="new_date_${prefix}"]`);
      const resultInput = form.querySelector(`textarea[name="${prefix}-RESULT"], textarea[name="new_result_${prefix}"]`);

      if (dateInput && !dateInput.value.trim()) {
        hasErrors = true;
        errorMessages.push(`Vui lòng nhập ngày thực hiện cho xét nghiệm ${prefix}.`);
      }
      if (resultInput && !resultInput.value.trim()) {
        hasErrors = true;
        errorMessages.push(`Vui lòng nhập kết quả cho xét nghiệm ${prefix}.`);
      }
    });

    if (hasErrors) {
      this.showMessage('Có lỗi trong form:\n\n' + errorMessages.join('\n'), 'danger');
      return true;
    }
    return false;
  },

  collectFormData: function(useInitialValues = false) {
    const formData = {};
    const form = document.getElementById('lab-form');
    if (!form) {
      console.error("Form lab-form not found");
      return formData;
    }

    const inputs = form.querySelectorAll('input, select, textarea');
    console.log(`Collecting ${useInitialValues ? 'initial' : 'current'} data from ${inputs.length} inputs`);

    inputs.forEach(input => {
      const name = input.name;
      if (!name || name.includes('csrfmiddlewaretoken') || name.includes('-DELETE')) return;

      let value;
      if (useInitialValues) {
        value = input.getAttribute('data-initial-value') || '';
      } else {
        if (input.type === 'checkbox') {
          value = input.checked ? 'True' : 'False';
        } else {
          value = input.value || '';
        }
      }
      formData[name] = value;
      console.log(`Field ${name}: ${useInitialValues ? 'initial' : 'current'} value = "${value}"`);
    });

    return formData;
  },

  findChanges: function(oldData, newData) {
    const changes = [];
    const ignoredFields = ['oldDataJson', 'newDataJson', 'reasonsJson', 'change_reason', 'csrfmiddlewaretoken'];

    // Kiểm tra nếu nút có chứa "Tạo Mới Xét Nghiệm", cho phép submit mà không cần thay đổi
    const isBtnCreateNew = $('#btnSaveLabTestsBottom').text().trim().includes('Tạo Mới Xét Nghiệm');
    const isEmptyForm = Object.keys(newData).length <= 5; // Chỉ có các trường ẩn và csrf token
    
    if (isBtnCreateNew && isEmptyForm) {
      console.log("Đây là form tạo mới xét nghiệm, bỏ qua kiểm tra thay đổi");
      return [{
        field: 'dummy_change',
        old: '',
        new: 'new',
        testType: '',
        label: 'Tạo mới xét nghiệm'
      }];
    }

    Object.keys(newData).forEach(key => {
      // Bỏ qua các trường đặc biệt
      if (ignoredFields.includes(key)) {
        return;
      }

      const oldValue = oldData[key] || '';
      const newValue = newData[key] || '';

      const normalizedOldValue = this.normalizeValue(oldValue);
      const normalizedNewValue = this.normalizeValue(newValue);

      if (normalizedOldValue !== normalizedNewValue) {
        let testType = '';
        if (key.includes('-')) {
          const parts = key.split('-');
          if (parts.length >= 3) {
            const prefix = parts.slice(0, 2).join('-');
            const testTypeKey = `${prefix}-TESTTYPE`;
            testType = newData[testTypeKey] || '';
          } else if (key.includes('new_')) {
            testType = key.split('_').slice(-1)[0];
          }
        }

        changes.push({
          field: key,
          old: oldValue,
          new: newValue,
          testType: testType,
          label: this.getFieldLabel(key, testType)
        });
      }
    });

    console.log("Changed fields:", changes);
    return changes;
  },

  getFieldLabel: function(fieldName, testType) {
    const baseLabels = {
      'RESULT': 'Kết quả',
      'PERFORMED': 'Đã thực hiện',
      'PERFORMEDDATE': 'Ngày thực hiện',
      'new_performed_': 'Đã thực hiện',
      'new_date_': 'Ngày thực hiện',
      'new_result_': 'Kết quả'
    };

    let fieldType = '';
    if (fieldName.includes('-')) {
      fieldType = fieldName.split('-').pop();
    } else if (fieldName.includes('new_')) {
      fieldType = fieldName.split('_')[1];
    }

    let label = baseLabels[fieldType] || fieldName;
    if (testType && this.TEST_TYPE_CHOICES[testType]) {
      label += ` (${this.TEST_TYPE_CHOICES[testType]})`;
    }
    return label;
  },

  normalizeValue: function(val) {
    if (val === null || val === undefined) return '';

    const str = String(val).trim();
    if (!str || ['null', 'none', 'na', 'n/a', 'undefined'].includes(str.toLowerCase())) {
      return '';
    }

    if (['no', 'false', '0'].includes(str.toLowerCase())) {
      return 'False';
    }
    if (['yes', 'true', '1', 'on'].includes(str.toLowerCase())) {
      return 'True';
    }

    return str;
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

  showChangeReasonModal: function(changedFields, callback) {
    console.log("showChangeReasonModal called with:", changedFields);

    let modalElement = document.getElementById('changeReasonModal');
    if (!modalElement) {
      console.error("Modal #changeReasonModal not found in DOM! Check change_reason_modal.html inclusion.");
      this.showMessage('Không thể hiển thị modal nhập lý do thay đổi', 'danger');
      this.resetProcessingState();
      callback({});
      return;
    }

    const tableBody = modalElement.querySelector('#changeTableBody');
    if (!tableBody) {
      console.error("Table body with id 'changeTableBody' not found in modal!");
      this.showMessage('Lỗi: Cấu trúc modal không đúng', 'danger');
      this.resetProcessingState();
      callback({});
      return;
    }

    tableBody.innerHTML = '';

    changedFields.forEach((change, index) => {
      const row = document.createElement('tr');

      const fieldCell = document.createElement('td');
      fieldCell.textContent = change.field;
      row.appendChild(fieldCell);

      const labelCell = document.createElement('td');
      labelCell.textContent = change.label || change.field;
      row.appendChild(labelCell);

      const oldValueCell = document.createElement('td');
      oldValueCell.textContent = change.old || '';
      row.appendChild(oldValueCell);

      const newValueCell = document.createElement('td');
      newValueCell.textContent = change.new || '';
      row.appendChild(newValueCell);

      const reasonCell = document.createElement('td');
      const reasonInput = document.createElement('input');
      reasonInput.type = 'text';
      reasonInput.className = 'form-control reason-input';
      reasonInput.name = `reason-${change.field}`;
      reasonInput.id = `reason-${change.field}`;
      reasonInput.placeholder = 'Nhập lý do thay đổi';
      reasonCell.appendChild(reasonInput);
      row.appendChild(reasonCell);

      tableBody.appendChild(row);
    });

    const modal = new bootstrap.Modal(modalElement);
    modal.show();

    const confirmButton = modalElement.querySelector('#saveWithReason');
    if (!confirmButton) {
      console.error("Confirm button with id 'saveWithReason' not found in modal!");
      this.showMessage('Lỗi: Không tìm thấy nút xác nhận trong modal', 'danger');
      this.resetProcessingState();
      callback({});
      return;
    }

    confirmButton.onclick = () => {
      // Sử dụng cấu trúc phẳng cho reasonsData, giống như các CRF khác
      const reasonsData = {};

      changedFields.forEach(change => {
        const reasonInput = document.getElementById(`reason-${change.field}`);
        const reasonText = reasonInput ? reasonInput.value.trim() : '';
        reasonsData[change.field] = reasonText || 'Cập nhật thông tin';  // Đảm bảo string
      });

      // Join change_reason với string lý do
      const allReasons = changedFields.map(change => {
        const reasonText = reasonsData[change.field] || 'Cập nhật thông tin';
        return `${change.label || change.field}: ${reasonText}`;
      }).join('; ');

      document.getElementById('change_reason').value = allReasons;
      document.getElementById('reasonsJson').value = JSON.stringify(reasonsData);  // Chỉ phẳng

      console.log("Reasons data prepared (flat):", reasonsData);
      console.log("Change reason:", allReasons);

      modal.hide();
      callback(reasonsData);
    };

    const fillAllButton = modalElement.querySelector('#fillAllReasons');
    if (fillAllButton) {
      fillAllButton.onclick = () => {
        const fillAllModal = document.getElementById('fillAllReasonsModal');
        if (!fillAllModal) {
          console.error("Modal #fillAllReasonsModal not found!");
          return;
        }
        const fillAllModalInstance = new bootstrap.Modal(fillAllModal);
        fillAllModalInstance.show();

        const applyButton = fillAllModal.querySelector('#applyCommonReason');
        if (applyButton) {
          applyButton.onclick = () => {
            const commonReason = fillAllModal.querySelector('#commonReason').value.trim();
            if (commonReason) {
              modalElement.querySelectorAll('.reason-input').forEach(input => {
                input.value = commonReason;
              });
              fillAllModalInstance.hide();
            }
          };
        }
      };
    }
  },

  saveAuditData: function(changedFields, reasonsData, callback) {
    console.log("Saving audit data with changedFields:", changedFields, "and reasonsData:", reasonsData);

    // Chỉ lấy dữ liệu từ các trường thay đổi thực sự
    const oldData = {};
    const newData = {};

    changedFields.forEach(fieldInfo => {
      const field = fieldInfo.field;
      oldData[field] = fieldInfo.old;
      newData[field] = fieldInfo.new;
    });
    
    const form = document.getElementById('lab-form');
    if (!form) {
      console.error("Form lab-form not found!");
      this.resetProcessingState();
      return;
    }

    // Tìm hoặc tạo các trường ẩn cần thiết
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

    // Lưu dữ liệu đã lọc vào các trường ẩn
    oldDataInput.value = JSON.stringify(oldData);
    newDataInput.value = JSON.stringify(newData);

    // Tạo cấu trúc lý do với label
    const reasonsJsonWithLabel = {};
    changedFields.forEach(change => {
      const field = change.field;
      const reason = reasonsData[field] || 'Cập nhật thông tin';
      const label = change.label || field;
      
      reasonsJsonWithLabel[field] = {
        label: label,
        reason: reason
      };
    });

    reasonsInput.value = JSON.stringify(reasonsJsonWithLabel);

    // Tạo chuỗi lý do thay đổi cho người đọc
    const changeReason = changedFields.map(fieldInfo => {
      const field = fieldInfo.field;
      const label = fieldInfo.label || field;
      const reason = reasonsData[field] || 'Cập nhật thông tin';
      return `${label}: ${reason}`;
    }).join('; ');

    reasonInput.value = changeReason;

    console.log("Audit data saved:", { oldData, newData, reasonsJsonWithLabel, changeReason });

    if (callback) callback();
  },

  submitForm: function() {
    const form = document.getElementById('lab-form');
    const $btn = $('.btn-primary:focus').length ? $('.btn-primary:focus') : $('#btnSaveLabTests');
    const originalHtml = $btn.html();

    let usubjid, labType;
    const actionMatch = form.action.match(/\/study_43en\/([^/]+)\/laboratory\/([^/]+)\/bulk-update\//);
    if (actionMatch) {
      usubjid = actionMatch[1];
      labType = actionMatch[2];
    } else {
      // Parse from URL path: /study_43en/{usubjid}/laboratory/{labType}/bulk-update/
      const pathParts = window.location.pathname.split('/').filter(p => p);
      const labIndex = pathParts.indexOf('laboratory');
      if (labIndex > 0) {
        usubjid = pathParts[labIndex - 1];
        labType = pathParts[labIndex + 1];
      }
    }

    console.log("Extracted usubjid:", usubjid, "labType:", labType);

    // Kiểm tra xem đây là thao tác tạo mới hay cập nhật
    const isCreate = $btn.text().includes('Tạo Mới Xét Nghiệm');
    
    const formData = new FormData(form);
    console.log("Submitting form with data:", Array.from(formData.entries()));

    const csrftoken = $('input[name="csrfmiddlewaretoken"]').val();
    if (!csrftoken) {
      console.error("CSRF token not found!");
      this.showMessage('Lỗi: Không tìm thấy CSRF token', 'danger');
      this.resetProcessingState();
      return;
    }

    if (!usubjid || !labType) {
      console.error("Invalid usubjid or labType:", { usubjid, labType });
      this.showMessage('Lỗi: Không thể xác định mã bệnh nhân hoặc lần xét nghiệm', 'danger');
      this.resetProcessingState();
      return;
    }

    $btn.html('<i class="fas fa-spinner fa-spin"></i> Đang lưu...').prop('disabled', true);

    // Chọn URL dựa vào loại thao tác - Sử dụng namespace đúng
    const url = isCreate 
      ? `/study_43en/${usubjid}/laboratory/${labType}/create/`
      : `/study_43en/${usubjid}/laboratory/${labType}/bulk-update/`;
      
    console.log("Sending AJAX request to:", url, "isCreate:", isCreate);

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
        console.log("Update success:", response);
        if (response.success) {
          this.showMessage('Đã lưu thông tin xét nghiệm thành công!', 'success');
          setTimeout(() => {
            window.location.href = response.redirect_url || `/study_43en/${usubjid}/laboratory/`;
          }, 500);
        } else {
          $btn.html(originalHtml).prop('disabled', false);
          this.resetProcessingState();
          this.showMessage(response.message || 'Có lỗi xảy ra khi lưu', 'danger');
        }
      },
      error: (xhr, status, error) => {
        console.error("Update error:", error, xhr.status, xhr.responseText);
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
    const performedInputs = document.querySelectorAll('input[name$="-PERFORMED"], input[name^="new_performed_"]');
    performedInputs.forEach(input => {
      input.addEventListener('change', () => {
        const card = input.closest('.lab-test-card');
        const details = card.querySelector('.test-details');
        if (input.checked) {
          details.style.display = 'block';
          card.classList.add('performed');
        } else {
          details.style.display = 'none';
          card.classList.remove('performed');
        }
      });
    });
  }
};

// Khởi tạo khi DOM ready
$(document).ready(function() {
  const form = document.getElementById('lab-form');
  const isViewOnly = form && form.classList.contains('view-only-form');

  if (!isViewOnly) {
    console.log("Initializing LaboratoryFormAudit");
    LaboratoryFormAudit.init();
  } else {
    console.log("Form is in view-only mode, skipping audit initialization");
  }
});
