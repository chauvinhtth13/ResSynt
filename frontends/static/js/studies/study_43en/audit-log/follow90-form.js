// Follow Up Form Audit Logging for 90 days
// Tích hợp với base.js để ghi lại log cho form theo dõi 90 ngày

window.FollowUpForm90Audit = {
  isProcessing: false,

  init: function() {
    console.log("Initializing Follow Up 90 Form Audit Logging");

    const form = document.getElementById('followUpForm');
    if (!form) {
      console.warn("Follow Up 90 form not found");
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
    console.log("Follow Up 90 Form Audit Logging initialized successfully");
  },

  isViewOnly: function() {
    return document.querySelector('.readonly-form') !== null;
  },

  resetProcessingState: function() {
    console.log("Resetting processing state");
    this.isProcessing = false;
    const saveButton = document.getElementById('btnSaveFollowUp');
    if (saveButton) {
      saveButton.disabled = false;
      if (saveButton.innerHTML.includes('fa-spinner')) {
        saveButton.innerHTML = '<i class="fas fa-save"></i> Cập Nhật';
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

    const form = document.getElementById('followUpForm');
    if (!form) {
      console.error("Follow Up 90 form not found for initial values setup");
      return;
    }

    const fields = document.querySelectorAll('#followUpForm input:not([type="hidden"]), #followUpForm select, #followUpForm textarea');
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
    const rehospitalizationForms = document.querySelectorAll('#rehospitalization-formset .rehospitalization-form');
    console.log(`Found ${rehospitalizationForms.length} rehospitalization90 forms`);
    
    rehospitalizationForms.forEach((form, index) => {
      const inputs = form.querySelectorAll('input, select, textarea');
      inputs.forEach(input => {
        const name = input.name;
        if (name && !name.includes('-DELETE') && !name.includes('-id') && !name.includes('-USUBJID')) {
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
          console.log(`Set initial value for rehospitalization90 ${name}: ${initialValue}`);
        }
      });
    });

    const antibioticForms = document.querySelectorAll('#antibiotic-formset .antibiotic-form');
    console.log(`Found ${antibioticForms.length} antibiotic90 forms`);
    
    antibioticForms.forEach((form, index) => {
      const inputs = form.querySelectorAll('input, select, textarea');
      inputs.forEach(input => {
        const name = input.name;
        if (name && !name.includes('-DELETE') && !name.includes('-id') && !name.includes('-USUBJID')) {
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
          console.log(`Set initial value for antibiotic90 ${name}: ${initialValue}`);
        }
      });
    });
  },

  setupFormSubmission: function() {
    const saveButton = document.getElementById('btnSaveFollowUp');
    if (!saveButton) {
      console.warn("Save button not found");
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
        return;
      }
      this.isProcessing = true;

      const hasErrors = this.validateForm();
      if (hasErrors) {
        console.log("Validation failed, stopping submission");
        this.resetProcessingState();
        return;
      }

      const form = document.getElementById('followUpForm');
      const isNew = form.getAttribute('data-is-create') === 'true';
      if (isNew) {
        console.log("Creating new form, submitting directly");
        this.submitForm();
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
        this.submitForm();
        return;
      }

      this.showChangeModal(changedFields, (reasonsData) => {
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
    
    if ($('input[name="ASSESSED"]:checked').val() === 'Yes' && !$('input[name="ASSESSDATE"]').val()) {
      hasErrors = true;
      errorMessages.push('Vui lòng nhập ngày đánh giá khi chọn "Có" cho câu hỏi đánh giá.');
    }
    
    if ($('input[name="DECEASED"]:checked').val() === 'Yes') {
      if (!$('input[name="DEATHDATE"]').val()) {
        hasErrors = true;
        errorMessages.push('Vui lòng nhập ngày tử vong.');
      }
      if (!$('textarea[name="DEATHCAUSE"]').val().trim()) {
        hasErrors = true;
        errorMessages.push('Vui lòng nhập nguyên nhân tử vong.');
      }
    }
    
    if ($('input[name="REHOSP"]:checked').val() === 'Yes') {
      if (!$('input[name="REHOSPCOUNT"]').val()) {
        hasErrors = true;
        errorMessages.push('Vui lòng nhập số lần tái nhập viện.');
      }
      let hasRehospData = false;
      $('#rehospitalization-formset .rehospitalization-form').each(function() {
        const deleteInput = $(this).find('input[id$="-DELETE"]');
        const hasData = (
          $(this).find('input[name$="-REHOSPDATE"]').val() ||
          $(this).find('input[name$="-REHOSPLOCATION"]').val() ||
          $(this).find('textarea[name$="-REHOSPREASONFOR"]').val()
        );
        const hasId = $(this).find('input[name$="-id"]').val();
        if ((hasId || hasData) && (!deleteInput.is(':checked'))) {
          hasRehospData = true;
          return false;
        }
      });
      if (!hasRehospData) {
        hasErrors = true;
        errorMessages.push('Vui lòng nhập ít nhất một lần tái nhập viện.');
      }
    }
    
    if ($('input[name="USEDANTIBIO"]:checked').val() === 'Yes') {
      if (!$('input[name="ANTIBIOCOUNT"]').val()) {
        hasErrors = true;
        errorMessages.push('Vui lòng nhập số đợt kháng sinh.');
      }
      let hasAntibioData = false;
      $('#antibiotic-formset .antibiotic-form').each(function() {
        const deleteInput = $(this).find('input[id$="-DELETE"]');
        const hasData = (
          $(this).find('input[name$="-ANTIBIONAME"]').val() ||
          $(this).find('input[name$="-ANTIBIODUR"]').val() ||
          $(this).find('textarea[name$="-ANTIBIOREASONFOR"]').val()
        );
        const hasId = $(this).find('input[name$="-id"]').val();
        if ((hasId || hasData) && (!deleteInput.is(':checked'))) {
          hasAntibioData = true;
          return false;
        }
      });
      if (!hasAntibioData) {
        hasErrors = true;
        errorMessages.push('Vui lòng nhập ít nhất một đợt kháng sinh.');
      }
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
      rehospitalization: [],
      antibiotic: []
    };

    const form = document.getElementById('followUpForm');
    if (!form) {
      console.error("Form followUpForm not found");
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

    // Thu thập dữ liệu từ formset rehospitalization90
    const rehospitalizationRows = document.querySelectorAll('.rehospitalization-form');
    rehospitalizationRows.forEach((row, rowIndex) => {
      const rowData = {};
      const inputs = row.querySelectorAll('input, select, textarea');
      
      const deleteInput = row.querySelector('input[name$="-DELETE"]');
      if (deleteInput && deleteInput.checked) {
        return;
      }
      
      inputs.forEach(input => {
        const name = input.name;
        if (name && !name.includes('-DELETE') && !name.includes('-id') && !name.includes('-USUBJID')) {
          const fieldMatch = name.match(/rehospitalization90_set-\d+-(\w+)/);
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
        data.rehospitalization.push(rowData);
      }
    });

    // Thu thập dữ liệu từ formset antibiotic90
    const antibioticRows = document.querySelectorAll('.antibiotic-form');
    antibioticRows.forEach((row, rowIndex) => {
      const rowData = {};
      const inputs = row.querySelectorAll('input, select, textarea');
      
      const deleteInput = row.querySelector('input[name$="-DELETE"]');
      if (deleteInput && deleteInput.checked) {
        return;
      }
      
      inputs.forEach(input => {
        const name = input.name;
        if (name && !name.includes('-DELETE') && !name.includes('-id') && !name.includes('-USUBJID')) {
          const fieldMatch = name.match(/antibiotic90_set-\d+-(\w+)/);
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
        data.antibiotic.push(rowData);
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

    // So sánh formset rehospitalization90
    const rehospitalizationOldRows = initialData.rehospitalization || [];
    const rehospitalizationNewRows = currentData.rehospitalization || [];
    const rehospitalizationMaxLength = Math.max(rehospitalizationOldRows.length, rehospitalizationNewRows.length);
    
    for (let i = 0; i < rehospitalizationMaxLength; i++) {
      const oldRow = rehospitalizationOldRows[i] || {};
      const newRow = rehospitalizationNewRows[i] || {};
      Object.keys(fieldLabels.rehospitalization || {}).forEach(field => {
        const fieldKey = `rehospitalization90_${i}_${field}`;
        const oldValue = AuditLogBase.normalizeValue(oldRow[field] || '');
        const newValue = AuditLogBase.normalizeValue(newRow[field] || '');
        if (oldValue !== newValue) {
          changedFields[fieldKey] = {
            old: oldRow[field] || '',
            new: newRow[field] || '',
            label: `${fieldLabels.rehospitalization[field] || field} (Đợt ${i + 1})`,
            type: fieldTypes[field] || 'text',
            options: fieldOptions[field] || {}
          };
        }
      });
    }

    // So sánh formset antibiotic90
    const antibioticOldRows = initialData.antibiotic || [];
    const antibioticNewRows = currentData.antibiotic || [];
    const antibioticMaxLength = Math.max(antibioticOldRows.length, antibioticNewRows.length);
    
    for (let i = 0; i < antibioticMaxLength; i++) {
      const oldRow = antibioticOldRows[i] || {};
      const newRow = antibioticNewRows[i] || {};
      Object.keys(fieldLabels.antibiotic || {}).forEach(field => {
        const fieldKey = `antibiotic90_${i}_${field}`;
        const oldValue = AuditLogBase.normalizeValue(oldRow[field] || '');
        const newValue = AuditLogBase.normalizeValue(newRow[field] || '');
        if (oldValue !== newValue) {
          changedFields[fieldKey] = {
            old: oldRow[field] || '',
            new: newRow[field] || '',
            label: `${fieldLabels.antibiotic[field] || field} (Đợt ${i + 1})`,
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
        'ASSESSED': 'Bệnh nhân được đánh giá tình trạng tại ngày 90?',
        'ASSESSDATE': 'Ngày đánh giá',
        'PATSTATUS': 'Tình trạng bệnh nhân',
        'REHOSP': 'Bệnh nhân tái nhập viện?',
        'REHOSPCOUNT': 'Số lần tái nhập viện',
        'DECEASED': 'Bệnh nhân tử vong?',
        'DEATHDATE': 'Ngày tử vong',
        'DEATHCAUSE': 'Nguyên nhân tử vong',
        'USEDANTIBIO': 'Bệnh nhân có sử dụng kháng sinh?',
        'ANTIBIOCOUNT': 'Số đợt kháng sinh',
        'FUNCASSESS': 'Đánh giá tình trạng chức năng tại ngày 90?',
        'MOBILITY': 'Vận động (đi lại)',
        'PERHYGIENE': 'Vệ sinh cá nhân',
        'DAILYACTIV': 'Sinh hoạt hằng ngày',
        'PAINDISCOMF': 'Đau/ khó chịu',
        'ANXIETY_DEPRESSION': 'Lo lắng/ Trầm cảm',
        'FBSISCORE': 'FBSI Score',
        'COMPLETEDBY': 'Người hoàn thành',
        'COMPLETEDDATE': 'Ngày hoàn thành'
      },
      rehospitalization: {
        'EPISODE': 'Đợt',
        'REHOSPDATE': 'Ngày tái nhập viện',
        'REHOSPREASONFOR': 'Lý do tái nhập viện',
        'REHOSPLOCATION': 'Nơi tái nhập viện',
        'REHOSPSTAYDUR': 'Thời gian nằm viện'
      },
      antibiotic: {
        'EPISODE': 'Đợt',
        'ANTIBIONAME': 'Tên thuốc',
        'ANTIBIOREASONFOR': 'Lý do sử dụng',
        'ANTIBIODUR': 'Thời gian sử dụng'
      }
    };
  },

  getFieldTypes: function() {
    return {
      'ASSESSED': 'radio',
      'ASSESSDATE': 'date',
      'PATSTATUS': 'select',
      'REHOSP': 'radio',
      'REHOSPCOUNT': 'number',
      'DECEASED': 'radio',
      'DEATHDATE': 'date',
      'DEATHCAUSE': 'textarea',
      'USEDANTIBIO': 'radio',
      'ANTIBIOCOUNT': 'number',
      'FUNCASSESS': 'radio',
      'MOBILITY': 'radio',
      'PERHYGIENE': 'radio',
      'DAILYACTIV': 'radio',
      'PAINDISCOMF': 'radio',
      'ANXIETY_DEPRESSION': 'radio',
      'FBSISCORE': 'select',
      'COMPLETEDBY': 'text',
      'COMPLETEDDATE': 'date',
      'EPISODE': 'number',
      'REHOSPDATE': 'date',
      'REHOSPREASONFOR': 'textarea',
      'REHOSPLOCATION': 'text',
      'REHOSPSTAYDUR': 'text',
      'ANTIBIONAME': 'text',
      'ANTIBIOREASONFOR': 'textarea',
      'ANTIBIODUR': 'text'
    };
  },

  getFieldOptions: function() {
    return {
      'PATSTATUS': {
        'Alive': 'Sống',
        'Rehospitalized': 'Tái nhập viện',
        'Deceased': 'Tử vong',
        'LostToFollowUp': 'Không liên hệ được'
      },
      'FBSISCORE': {
        '7': '7. Xuất viện; cơ bản khỏe mạnh; có thể hoàn thành các hoạt động hằng ngày mức độ cao',
        '6': '6. Xuất viện; có triệu chứng/ dấu hiệu bệnh trung bình; không thể hoàn thành các hoạt động hằng ngày',
        '5': '5. Xuất viện; tàn tật nghiêm trọng; yêu cầu chăm sóc và hỗ trợ hằng ngày mức độ cao',
        '4': '4. Nhập viện nhưng không nằm ở ICU',
        '3': '3. Nhập viện và nằm ở ICU',
        '2': '2. Nhập khoa thở máy kéo dài',
        '1': '1. Chăm sóc giảm nhẹ trong giai đoạn cuối đời (ở bệnh viện hoặc ở nhà)',
        '0': '0. Tử vong'
      },
      'ASSESSED': { 'Yes': 'Có', 'No': 'Không', 'NA': 'Không áp dụng' },
      'REHOSP': { 'Yes': 'Có', 'No': 'Không', 'NA': 'Không áp dụng' },
      'DECEASED': { 'Yes': 'Có', 'No': 'Không', 'NA': 'Không áp dụng' },
      'USEDANTIBIO': { 'Yes': 'Có', 'No': 'Không', 'NA': 'Không áp dụng' },
      'FUNCASSESS': { 'Yes': 'Có', 'No': 'Không', 'NA': 'Không áp dụng' },
      'MOBILITY': { 'Normal': 'Bình thường', 'Problem': 'Có vấn đề', 'Bedridden': 'Nằm một chỗ' },
      'PERHYGIENE': { 'Normal': 'Bình thường', 'Problem': 'Có vấn đề', 'Bedridden': 'Nằm một chỗ' },
      'DAILYACTIV': { 'Normal': 'Bình thường', 'Problem': 'Có vấn đề', 'Bedridden': 'Nằm một chỗ' },
      'PAINDISCOMF': { 'Normal': 'Bình thường', 'Problem': 'Có vấn đề', 'Bedridden': 'Nằm một chỗ' },
      'ANXIETY_DEPRESSION': { 'None': 'Không', 'Moderate': 'Trung bình', 'Severe': 'Nhiều' }
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
    console.log("FollowUpForm90Audit.showChangeModal called with:", changedFields);
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
    initialData.rehospitalization.forEach((item, idx) => {
      if (item) {
        for (const field in item) {
          oldData[`rehospitalization90_${idx}_${field}`] = item[field];
        }
      }
    });
    initialData.antibiotic.forEach((item, idx) => {
      if (item) {
        for (const field in item) {
          oldData[`antibiotic90_${idx}_${field}`] = item[field];
        }
      }
    });

    const newData = {};
    for (const key in currentData.main) {
      newData[key] = currentData.main[key];
    }
    currentData.rehospitalization.forEach((item, idx) => {
      if (item) {
        for (const field in item) {
          newData[`rehospitalization90_${idx}_${field}`] = item[field];
        }
      }
    });
    currentData.antibiotic.forEach((item, idx) => {
      if (item) {
        for (const field in item) {
          newData[`antibiotic90_${idx}_${field}`] = item[field];
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
      } else if (key.includes('rehospitalization90_')) {
        const [prefix, index, field] = key.split('_');
        const episode = parseInt(index) + 1;
        const possibleKeys = [
          `rehospitalization90-${episode}-${field}`,
          `rehospitalization90_set-${index}-${field}`,
          `rehospitalization90_${index}_${field}`,
          `${field}`
        ];
        
        for (const altKey of possibleKeys) {
          if (altKey in reasonsData) {
            reasonText = reasonsData[altKey];
            break;
          }
        }
      } else if (key.includes('antibiotic90_')) {
        const [prefix, index, field] = key.split('_');
        const episode = parseInt(index) + 1;
        const possibleKeys = [
          `antibiotic90-${episode}-${field}`,
          `antibiotic90_set-${index}-${field}`,
          `antibiotic90_${index}_${field}`,
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

    const form = document.getElementById('followUpForm');
    if (!form) {
      console.error("Form followUpForm not found!");
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

    console.log("Audit data saved for form followUpForm:", { oldData, newData, reasonsJsonWithLabel, changeReason });

    if (callback) callback();
  },

  submitForm: function() {
    const form = document.getElementById('followUpForm');
    const $btn = $('#btnSaveFollowUp');
    const originalHtml = $btn.html();
    const usubjid = form.action.match(/\/43en\/([^/]+)\/followup90\/update\//)?.[1] || window.location.pathname.split('/')[2];

    const formData = new FormData(form);
    console.log("Submitting form with data:", Array.from(formData.entries()));

    const csrftoken = $('input[name="csrfmiddlewaretoken"]').val();
    $btn.html('<i class="fas fa-spinner fa-spin"></i> Đang lưu...').prop('disabled', true);

    $.ajax({
      url: `/43en/${usubjid}/followup90/update/`,
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
          this.showMessage('Đã cập nhật thông tin theo dõi 90 ngày thành công!', 'success');
          setTimeout(() => {
            window.location.href = response.redirect_url || `/43en/patient/${usubjid}/`;
          }, 500);
        } else {
          $btn.html(originalHtml).prop('disabled', false);
          this.resetProcessingState();
          this.showMessage(response.message || 'Có lỗi xảy ra khi cập nhật', 'danger');
        }
      },
      error: (xhr, status, error) => {
        console.error("Update error:", error, xhr.status, xhr.responseText);
        $btn.html(originalHtml).prop('disabled', false);
        this.resetProcessingState();
        let errorMsg = 'Có lỗi xảy ra khi cập nhật. Vui lòng kiểm tra lại.';
        try {
          const response = JSON.parse(xhr.responseText);
          if (response.message) {
            errorMsg = response.message;
            if (response.errors) {
              errorMsg += '\nChi tiết lỗi:\n' + JSON.stringify(response.errors, null, 2);
            }
          }
        } catch (e) {
          console.log("Could not parse error response:", e);
        }
        this.showMessage(errorMsg, 'danger');
      }
    });
  },

  setupSpecialHandlers: function() {
    const rehospRadios = document.querySelectorAll('input[name="REHOSP"]');
    rehospRadios.forEach(radio => {
      radio.addEventListener('change', () => {
        const show = radio.value === 'Yes';
        const section = document.getElementById('rehospitalization-section');
        if (section) {
          section.style.display = show ? 'block' : 'none';
          console.log(`REHOSP changed to ${radio.value}, rehospitalization-section display: ${section.style.display}`);
        }
      });
    });

    const usedAntibioRadios = document.querySelectorAll('input[name="USEDANTIBIO"]');
    usedAntibioRadios.forEach(radio => {
      radio.addEventListener('change', () => {
        const show = radio.value === 'Yes';
        const section = document.getElementById('antibiotic-section');
        if (section) {
          section.style.display = show ? 'block' : 'none';
          console.log(`USEDANTIBIO changed to ${radio.value}, antibiotic-section display: ${section.style.display}`);
        }
      });
    });

    const addButtons = document.querySelectorAll('#add-rehospitalization, #add-antibiotic');
    addButtons.forEach(button => {
      button.addEventListener('click', () => {
        console.log("Add row button clicked");
        setTimeout(() => {
          this.setupFormsetInitialValues();
        }, 100);
      });
    });

    const formsetTables = document.querySelectorAll('#followUpForm div[id$="-formset"]');
    formsetTables.forEach(table => {
      table.addEventListener('change', (e) => {
        if (e.target.name && e.target.name.includes('-DELETE')) {
          console.log(`Delete checkbox changed for ${e.target.name}`);
          setTimeout(() => {
            this.setupFormsetInitialValues();
          }, 100);
        }
      });
    });
  }
};

// Khởi tạo khi DOM ready
$(document).ready(function() {
  const form = document.getElementById('followUpForm');
  const isViewOnly = form && form.classList.contains('readonly-form');

  if (!isViewOnly) {
    console.log("Initializing FollowUpForm90Audit");
    window.FollowUpForm90Audit.init();
  } else {
    console.log("Form is in view-only mode, skipping audit initialization");
  }
});