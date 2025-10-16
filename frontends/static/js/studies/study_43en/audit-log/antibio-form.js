// AntibioticSensitivity Form Audit Logging
// Tích hợp với base.js để ghi log cho form kết quả độ nhạy kháng sinh

window.AntibioticSensitivityAudit = {
  isProcessing: false,

  // Định nghĩa ANTIBIOTIC_CHOICES và SENSITIVITY_CHOICES từ models
  ANTIBIOTIC_CHOICES: {
    'Ampicillin': 'Ampicillin',
    'Cefazolin': 'Cefazolin',
    'Cefotaxime': 'Cefotaxime',
    'Ceftriaxone': 'Ceftriaxone',
    'AmoxicillinClavulanate': 'Amoxicillin-Clavulanate',
    'AmpicillinSulbactam': 'Ampicillin-Sulbactam',
    'PiperacillinTazobactam': 'Piperacillin-Tazobactam',
    'Gentamicin': 'Gentamicin',
    'Ciprofloxacin': 'Ciprofloxacin',
    'Levofloxacin': 'Levofloxacin',
    'TrimethoprimSulfamethoxazole': 'Trimethoprim-Sulfamethoxazole',
    'Cefepime': 'Cefepime',
    'Imipenem': 'Imipenem',
    'Meropenem': 'Meropenem',
    'Cefuroxime': 'Cefuroxime',
    'Ertapenem': 'Ertapenem',
    'Cefoxitin': 'Cefoxitin',
    'Tobramycin': 'Tobramycin',
    'Amikacin': 'Amikacin',
    'Cefotetan': 'Cefotetan',
    'Tetracycline': 'Tetracycline',
    'Cefiderocol': 'Cefiderocol',
    'CeftazidimeAvibactam': 'Ceftazidime-Avibactam',
    'ImipenemRelebactam': 'Imipenem-Relebactam',
    'MeropenemVaborbactam': 'Meropenem-Vaborbactam',
    'Plazomicin': 'Plazomicin',
    'Aztreonam': 'Aztreonam',
    'Ceftaroline': 'Ceftaroline',
    'Ceftazidime': 'Ceftazidime',
    'CeftolozaneTazobactam': 'Ceftolozane-Tazobactam',
    'Colistin': 'Colistin',
    'Cefazolin_Urine': 'Cefazolin (Nước tiểu)',
    'Nitrofurantoin': 'Nitrofurantoin',
    'Fosfomycin': 'Fosfomycin',
    'Ceftriazone': 'Ceftriazone',
    'Tigecycline': 'Tigecycline',
    'TicarcillinClavulanic': 'Ticarcillin-Clavulanic',
    'CefoperazoneSulbactam': 'Cefoperazone-Sulbactam',
    'OTHER': 'Kháng sinh khác'
  },

  SENSITIVITY_CHOICES: {
    'S': 'Nhạy cảm (S)',
    'I': 'Trung gian (I)',
    'R': 'Kháng thuốc (R)',
    'ND': 'Không xác định (ND)',
    'U': 'Không biết (U)'
  },

  init: function() {
    console.log("Initializing AntibioticSensitivity Form Audit Logging");

    if (this.isViewOnly()) {
      console.log("View-only mode, disabling audit logging");
      return;
    }

    // Using base.js functionality instead of custom modal
    this.setupInitialValues();
    this.setupFormSubmission();
    this.setupModalHandlers();
    this.setupFieldTracking();
    console.log("AntibioticSensitivity Form Audit Logging initialized successfully");
  },

  setupFieldTracking: function() {
    // Đánh dấu các trường khi người dùng tương tác
    $(document).on('change', '.antibiotic-item select, .antibiotic-item input', function() {
      $(this).addClass('touched');
      // Đánh dấu cả row để biết đã tương tác
      $(this).closest('.antibiotic-item').addClass('touched');
    });
  },

  isViewOnly: function() {
    return window.location.search.includes('mode=view');
  },

  resetProcessingState: function() {
    console.log("Resetting processing state");
    this.isProcessing = false;
    const saveButtons = document.querySelectorAll('.btn-save-tier');
    saveButtons.forEach(button => {
      button.disabled = false;
      if (button.innerHTML.includes('fa-spinner')) {
        button.innerHTML = '<i class="fas fa-save"></i> Lưu thay đổi';
      }
    });
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

    const usubjid = document.getElementById('usubjid')?.value;
    const cultureId = document.getElementById('culture-id')?.value;
    if (!usubjid || !cultureId) {
      console.error("Missing usubjid or culture-id");
      this.showMessage('Lỗi: Không thể xác định mã bệnh nhân hoặc mẫu nuôi cấy', 'danger');
      return;
    }

    // Lấy dữ liệu ban đầu từ API
    $.ajax({
      url: `/43en/${usubjid}/microbiology/${cultureId}/antibiotics/api/`,
      method: 'GET',
      success: (response) => {
        if (response.success) {
          console.log("Initial data fetched:", response.results);
          this.storeInitialValues(response.results);
        } else {
          console.error("Failed to fetch initial data:", response.message);
          this.showMessage('Lỗi khi lấy dữ liệu ban đầu: ' + response.message, 'danger');
        }
      },
      error: (xhr, status, error) => {
        console.error("Error fetching initial data:", error, xhr.status, xhr.responseText);
        this.showMessage('Lỗi khi lấy dữ liệu ban đầu', 'danger');
      }
    });
  },

  storeInitialValues: function(data) {
    console.log("Storing initial values for tiers:", Object.keys(data));
    const initialData = {};

    // Tạo các input ẩn nếu chưa tồn tại
    const requiredInputs = ['oldDataJson', 'newDataJson', 'reasonsJson', 'change_reason'];
    requiredInputs.forEach(inputId => {
      if (!document.getElementById(inputId)) {
        console.log(`Creating ${inputId} input element`);
        const input = document.createElement('input');
        input.type = 'hidden';
        input.id = inputId;
        input.name = inputId;
        document.body.appendChild(input);
      }
    });

    // Lưu giá trị ban đầu từ API
    Object.entries(data).forEach(([tier, sensitivities]) => {
      sensitivities.forEach(sensitivity => {
        const antibioticId = sensitivity.id || `new-${tier}-${sensitivity.SEQUENCE}`;
        const prefix = `antibiotic-${antibioticId}`;
        const fields = [
          { name: "antibiotic_name", value: sensitivity.ANTIBIOTIC_NAME },
          { name: "other_antibiotic_name", value: sensitivity.OTHER_ANTIBIOTIC_NAME || '' },
          { name: "sensitivity_level", value: sensitivity.SENSITIVITY_LEVEL || 'ND' },
          { name: "inhibition_zone_diameter", value: sensitivity.IZDIAM || '' },
          { name: "mic_value", value: sensitivity.MIC || '' }
        ];
        
        fields.forEach(field => {
          // Store with prefix to match collectFormData
          const prefixedName = `${prefix}-${field.name}`;
          initialData[prefixedName] = field.value;
          
          // Find input in the DOM - try both with and without prefix to be safe
          const input = document.querySelector(`[name="${field.name}"]`) || 
                        document.querySelector(`[name="${prefixedName}"]`);
                        
          if (input) {
            input.setAttribute('data-initial-value', field.value);
            console.log(`Field ${field.name} (${prefixedName}): initial value = "${field.value}"`);
          } else {
            console.log(`Input field ${field.name} not found in DOM`);
          }
        });
      });
    });

    // Lưu dữ liệu ban đầu vào oldDataJson
    document.getElementById('oldDataJson').value = JSON.stringify(initialData);
    console.log("Initial data stored:", initialData);
    
    // Set initial values directly on inputs that might be dynamically added later
    setTimeout(() => {
      document.querySelectorAll('.antibiotic-item').forEach(item => {
        const antibioticId = item.id.replace('antibiotic-item-', '');
        const prefix = `antibiotic-${antibioticId}`;
        
        item.querySelectorAll('input, select').forEach(input => {
          const name = input.name;
          if (!name || name.includes('csrfmiddlewaretoken')) return;
          
          const prefixedName = `${prefix}-${name}`;
          if (initialData[prefixedName] !== undefined) {
            input.setAttribute('data-initial-value', initialData[prefixedName]);
            console.log(`Late-binding field ${name}: initial value = "${initialData[prefixedName]}"`);
          }
        });
      });
    }, 500);
  },

  setupFormSubmission: function() {
    const saveButtons = document.querySelectorAll('.btn-save-tier');
    if (!saveButtons.length) {
      console.warn("No save buttons found");
      this.showMessage('Lỗi: Không tìm thấy nút lưu', 'danger');
      return;
    }

    console.log(`Found ${saveButtons.length} save buttons, attaching events`);
    saveButtons.forEach(button => {
      $(button).off('click').on('click', (e) => {
        e.preventDefault();
        e.stopPropagation(); // Ngăn sự kiện click lan truyền từ antibiotic_sensitivity.js
        const tier = button.getAttribute('data-tier');
        console.log(`Save button clicked for tier: ${tier}`);

        if (this.isProcessing) {
          console.log("Form is already processing, preventing duplicate submission");
          return;
        }
        this.isProcessing = true;

        const hasErrors = this.validateForm(tier);
        if (hasErrors) {
          console.log("Validation failed, stopping submission");
          this.resetProcessingState();
          return;
        }

        const initialData = this.collectFormData(true, tier);
        console.log("Initial data:", initialData);
        const currentData = this.collectFormData(false, tier);
        console.log("Current data:", currentData);

        // Debugging to see what fields are different
        console.log("Comparing values for change detection:");
        for (const key in currentData) {
          if (initialData[key] !== undefined) {
            const initialVal = AuditLogBase.normalizeValue(initialData[key]);
            const currentVal = AuditLogBase.normalizeValue(currentData[key]);
            if (initialVal !== currentVal) {
              console.log(`Field ${key} changed: "${initialVal}" -> "${currentVal}"`);
            }
          }
        }

        // Use AuditLogBase to compare the fields with a simpler approach
        const changedFields = {};
        
        // Compare each field and build a properly formatted changedFields object
        for (const key in currentData) {
          if (
            initialData[key] !== undefined &&
            AuditLogBase.normalizeValue(initialData[key]) !== AuditLogBase.normalizeValue(currentData[key])
          ) {
            // Extract the actual field name from the prefixed key (antibiotic-123-sensitivity_level -> sensitivity_level)
            const matches = key.match(/antibiotic-[^-]+-(.+)/);
            const actualFieldName = matches && matches[1] ? matches[1] : key;
            
            // Get the field information
            const fieldLabels = this.getFieldLabels();
            const fieldTypes = this.getFieldTypes();
            const fieldOptions = this.getFieldOptions();
            
            // Create the changed field entry with proper display name
            changedFields[key] = {
              old: initialData[key],
              new: currentData[key],
              label: fieldLabels[actualFieldName] || actualFieldName,
              type: fieldTypes[actualFieldName] || 'text',
              options: fieldOptions[actualFieldName] || {}
            };
          }
        }
        
        console.log("Changed fields with proper labels:", changedFields);

        if (Object.keys(changedFields).length === 0) {
          console.log("No changes detected, submitting form directly");
          this.submitForm(tier, button);
          return;
        }

        // Pass the properly labeled fields to the change modal
        AuditLogBase.showChangeModal(changedFields, (reasonsData) => {
          console.log("Reasons data received:", reasonsData);
          this.saveAuditData(changedFields, reasonsData, tier, () => {
            console.log("Audit data saved, now submitting form");
            this.submitForm(tier, button);
          });
        });
      });
    });
  },

  validateForm: function(tier) {
    let hasErrors = false;
    const errorMessages = [];
    const tierContainer = document.getElementById(`tier-${tier}`);
    if (!tierContainer) {
      console.error(`Tier container tier-${tier} not found`);
      errorMessages.push('Lỗi: Không tìm thấy nhóm kháng sinh');
      hasErrors = true;
    } else {
      // Lọc chỉ các dòng đã có dữ liệu hoặc đã bắt đầu nhập
      const antibioticsList = tierContainer.querySelectorAll('.antibiotic-item');
      let hasValidItems = false;
      
      antibioticsList.forEach(item => {
        const antibioticId = item.id.replace('antibiotic-item-', '');
        const prefix = `antibiotic-${antibioticId}`;
        
        // Trong giao diện hiện tại, tên kháng sinh được set sẵn và không thể thay đổi
        // Nên không cần kiểm tra tên kháng sinh nữa
        const antibioticName = item.querySelector(`[name="antibiotic_name"]`)?.value;
        
        // Kiểm tra xem dòng này có dữ liệu nào không
        const sensitivityValue = item.querySelector(`[name="sensitivity_level"]`)?.value || '';
        const izdiamValue = item.querySelector(`[name="inhibition_zone_diameter"]`)?.value || '';
        const micValue = item.querySelector(`[name="mic_value"]`)?.value || '';
        
        // Kiểm tra xem người dùng đã tương tác với dòng này chưa
        const hasUserInteraction = item.classList.contains('touched') || 
                                  (sensitivityValue && sensitivityValue !== 'ND') || 
                                  izdiamValue.trim() !== '' || 
                                  micValue.trim() !== '';
        
        // Bỏ qua dòng này nếu người dùng chưa tương tác
        if (!hasUserInteraction) {
          console.log(`Skipping validation for untouched row: ${antibioticId}`);
          return;
        }
        
        hasValidItems = true;
        
        // Không cần kiểm tra tên kháng sinh nữa vì đã được set sẵn
        
        // Chỉ kiểm tra cho kháng sinh 'OTHER' nếu cần
        if (antibioticName === 'OTHER') {
          const otherInput = item.querySelector(`[name="other_antibiotic_name"]`);
          if (!otherInput?.value.trim()) {
            errorMessages.push(`Vui lòng nhập tên kháng sinh khác cho ${this.ANTIBIOTIC_CHOICES[antibioticName]}.`);
            hasErrors = true;
          }
        }

        const sensitivityLevel = item.querySelector(`[name="sensitivity_level"]`)?.value;
        if (sensitivityLevel && sensitivityLevel !== 'ND') {
          const izdiam = item.querySelector(`[name="inhibition_zone_diameter"]`)?.value;
          const mic = item.querySelector(`[name="mic_value"]`)?.value;
          if (!izdiam?.trim() && !mic?.trim()) {
            // Lấy tên kháng sinh trực tiếp từ giao diện để hiển thị lỗi
            const displayName = item.querySelector('strong')?.textContent || 'Kháng sinh này';
            errorMessages.push(`Vui lòng nhập ít nhất một giá trị Vòng ức chế hoặc MIC cho ${displayName} khi độ nhạy không phải ND.`);
            hasErrors = true;
          }
        }
      });
      
      // Nếu không có mục hợp lệ nào, có thể là người dùng đang lưu một tier trống
      if (!hasValidItems) {
        console.log("No valid items found for tier " + tier + ", allowing empty save");
      }
    }

    if (hasErrors) {
      // Lọc bỏ những thông báo lỗi trùng lặp
      const uniqueErrors = [...new Set(errorMessages)];
      this.showMessage('Có lỗi trong form:<br>' + uniqueErrors.join('<br>'), 'danger');
      return true;
    }
    return false;
  },

  collectFormData: function(useInitialValues = false, tier) {
    const data = {};
    const tierContainer = document.getElementById(`tier-${tier}`);
    if (!tierContainer) {
      console.error(`Tier container tier-${tier} not found`);
      return data;
    }

    const antibioticsList = tierContainer.querySelectorAll('.antibiotic-item');
    antibioticsList.forEach(item => {
      const antibioticId = item.id.replace('antibiotic-item-', '');
      
      // Lấy tên kháng sinh đã được set sẵn trong HTML
      const antibioticName = item.querySelector('[name="antibiotic_name"]')?.value;
      
      // Với mỗi dòng kháng sinh, tạo một tiền tố để ID các trường
      // Điều này giúp phân biệt giữa các dòng khác nhau trong tier
      const prefix = `antibiotic-${antibioticId}`;
      
      // Lấy tất cả các input và select trong dòng kháng sinh này
      const inputs = item.querySelectorAll('input, select');
      inputs.forEach(input => {
        const name = input.name;
        if (!name || name.includes('csrfmiddlewaretoken')) return;

        let value = '';
        if (useInitialValues) {
          value = input.getAttribute('data-initial-value') || '';
        } else {
          value = input.value || '';
        }
        
        // Sử dụng tên trường có tiền tố để tránh trùng lặp giữa các dòng
        const fieldKey = `${prefix}-${name}`;
        data[fieldKey] = value;
        console.log(`Field ${fieldKey}: ${useInitialValues ? 'initial' : 'current'} value = "${value}"`);
      });
    });

    return data;
  },

  getFieldLabels: function() {
    return {
      'antibiotic_name': 'Tên kháng sinh',
      'other_antibiotic_name': 'Tên kháng sinh khác',
      'sensitivity_level': 'Mức độ nhạy cảm',
      'inhibition_zone_diameter': 'Đường kính vòng vô khuẩn (mm)',
      'mic_value': 'MIC (μg/ml)'
    };
  },

  getFieldTypes: function() {
    return {
      'antibiotic_name': 'select',
      'other_antibiotic_name': 'text',
      'sensitivity_level': 'select',
      'inhibition_zone_diameter': 'text',
      'mic_value': 'text'
    };
  },

  getFieldOptions: function() {
    return {
      'antibiotic_name': this.ANTIBIOTIC_CHOICES,
      'sensitivity_level': this.SENSITIVITY_CHOICES
    };
  },

  showMessage: function(message, type = 'success') {
    clearTimeout(window.saveIndicatorTimeout);
    const $indicator = $('#saveIndicator');
    $indicator.removeClass('alert-success alert-danger alert-warning alert-info')
      .addClass(`alert-${type}`);
    $indicator.find('.message').html(message); // Sử dụng .html() để hỗ trợ HTML từ antibiotic_sensitivity.js
    $indicator.addClass('show').show();

    window.saveIndicatorTimeout = setTimeout(() => {
      $indicator.removeClass('show');
      setTimeout(() => $indicator.hide(), 150);
    }, 5000);
  },

  saveAuditData: function(changedFields, reasonsData, tier, callback) {
    console.log("Saving audit data with changedFields:", changedFields, "and reasonsData:", reasonsData);

    const initialData = this.collectFormData(true, tier);
    const currentData = this.collectFormData(false, tier);

    const oldData = {};
    const newData = {};
    Object.keys(changedFields).forEach(key => {
      oldData[key] = initialData[key] || '';
      newData[key] = currentData[key] || '';
    });

    const reasonsJsonWithLabel = {};
    Object.keys(changedFields).forEach(key => {
      const reason = reasonsData[key] || 'Cập nhật thông tin';
      // Use the proper display name from changedFields
      const label = changedFields[key].label || key;
      
      // Extract antibioticId from key to add context
      const antibioticIdMatch = key.match(/antibiotic-([^-]+)-/);
      const antibioticId = antibioticIdMatch ? antibioticIdMatch[1] : '';
      
      // Find the antibiotic name for this ID to add context
      const antibioticItem = document.getElementById(`antibiotic-item-${antibioticId}`);
      let antibioticName = '';
      if (antibioticItem) {
        // Get the antibiotic name from the strong tag within the item
        const nameElement = antibioticItem.querySelector('strong');
        if (nameElement) {
          antibioticName = nameElement.textContent.trim();
        }
      }
      
      // Create a more descriptive label that includes the antibiotic name
      const contextLabel = antibioticName ? 
        `${antibioticName} - ${label}` : 
        label;
        
      reasonsJsonWithLabel[key] = { 
        label: contextLabel, 
        reason 
      };
    });

    let oldDataInput = document.getElementById('oldDataJson');
    let newDataInput = document.getElementById('newDataJson');
    let reasonsInput = document.getElementById('reasonsJson');
    let reasonInput = document.getElementById('change_reason');

    if (!oldDataInput) {
      oldDataInput = document.createElement('input');
      oldDataInput.type = 'hidden';
      oldDataInput.id = 'oldDataJson';
      oldDataInput.name = 'oldDataJson';
      document.body.appendChild(oldDataInput);
    }
    if (!newDataInput) {
      newDataInput = document.createElement('input');
      newDataInput.type = 'hidden';
      newDataInput.id = 'newDataJson';
      newDataInput.name = 'newDataJson';
      document.body.appendChild(newDataInput);
    }
    if (!reasonsInput) {
      reasonsInput = document.createElement('input');
      reasonsInput.type = 'hidden';
      reasonsInput.id = 'reasonsJson';
      reasonsInput.name = 'reasonsJson';
      document.body.appendChild(reasonsInput);
    }
    if (!reasonInput) {
      reasonInput = document.createElement('input');
      reasonInput.type = 'hidden';
      reasonInput.id = 'change_reason';
      reasonInput.name = 'change_reason';
      document.body.appendChild(reasonInput);
    }

    oldDataInput.value = JSON.stringify(oldData);
    newDataInput.value = JSON.stringify(newData);
    reasonsInput.value = JSON.stringify(reasonsJsonWithLabel);

    const changeReason = Object.entries(reasonsJsonWithLabel)
      .map(([field, obj]) => `${obj.label}: ${obj.reason}`)
      .join(' | ');

    reasonInput.value = changeReason;

    console.log("Audit data saved:", { oldData, newData, reasonsJsonWithLabel, changeReason });

    if (callback) callback();
  },

  submitForm: function(tier, button) {
    const usubjid = document.getElementById('usubjid')?.value;
    const cultureId = document.getElementById('culture-id')?.value;
    if (!usubjid || !cultureId) {
      console.error("Missing usubjid or culture-id");
      this.showMessage('Lỗi: Không thể xác định mã bệnh nhân hoặc mẫu nuôi cấy', 'danger');
      this.resetProcessingState();
      return;
    }

    const tierContainer = document.getElementById(`tier-${tier}`);
    if (!tierContainer) {
      console.error(`Tier container tier-${tier} not found`);
      this.showMessage('Lỗi: Không tìm thấy nhóm kháng sinh', 'danger');
      this.resetProcessingState();
      return;
    }

    const antibioticsList = tierContainer.querySelectorAll('.antibiotic-item');
    const bulkData = { [tier]: [] };

    let sequence = 1;
    antibioticsList.forEach(item => {
      const antibioticId = item.id.replace('antibiotic-item-', '');
      
      // Tên kháng sinh đã được set sẵn trong HTML
      const antibioticName = item.querySelector('[name="antibiotic_name"]')?.value;
      
      // Kháng sinh luôn đã có sẵn trong danh sách, nhưng vẫn kiểm tra để chắc chắn
      if (!antibioticName) {
        console.log(`Skipping row with no antibiotic name: ${antibioticId}`);
        return;
      }
      
      // Thu thập dữ liệu cho kháng sinh này
      const entry = {
        id: antibioticId.startsWith('new-') ? null : antibioticId,
        TIER: tier,
        ANTIBIOTIC_NAME: antibioticName,
        OTHER_ANTIBIOTIC_NAME: item.querySelector('[name="other_antibiotic_name"]')?.value || '',
        SENSITIVITY_LEVEL: item.querySelector('[name="sensitivity_level"]')?.value || 'ND',
        IZDIAM: item.querySelector('[name="inhibition_zone_diameter"]')?.value || '',
        MIC: item.querySelector('[name="mic_value"]')?.value || '',
        SEQUENCE: sequence++
      };

      if (entry.ANTIBIOTIC_NAME !== 'OTHER') {
        entry.OTHER_ANTIBIOTIC_NAME = '';
      }

      bulkData[tier].push(entry);
    });

    const formData = new FormData();
    formData.append('bulk_data', JSON.stringify(bulkData));
    formData.append('replace_existing', 'true');
    formData.append('csrfmiddlewaretoken', document.querySelector('[name="csrfmiddlewaretoken"]').value);
    formData.append('oldDataJson', document.getElementById('oldDataJson')?.value || '{}');
    formData.append('newDataJson', document.getElementById('newDataJson')?.value || '{}');
    formData.append('reasonsJson', document.getElementById('reasonsJson')?.value || '{}');
    formData.append('change_reason', document.getElementById('change_reason')?.value || '');

    console.log("Submitting form with data:", Array.from(formData.entries()));

    const url = `/43en/${usubjid}/microbiology/${cultureId}/antibiotics/bulk-update/`;
    $(button).html('<i class="fas fa-spinner fa-spin"></i> Đang lưu...').prop('disabled', true);

    $.ajax({
      url: url,
      method: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: (response) => {
        console.log("Request success:", response);
        if (response.success) {
          // Reset editing flag to prevent browser warning
          window.editingInProgress = false;
          
          this.showMessage('Đã lưu kết quả độ nhạy kháng sinh thành công!', 'success');
          // Cập nhật giao diện từ antibiotic_sensitivity.js
          if (response.tier_data && response.tier_data.length > 0 && typeof updateTierWithServerData === 'function') {
            updateTierWithServerData(tier, response.tier_data);
          }
          setTimeout(() => {
            window.location.reload();
          }, 500);
        } else {
          $(button).html('<i class="fas fa-save"></i> Lưu thay đổi').prop('disabled', false);
          this.resetProcessingState();
          this.showMessage(response.message || 'Có lỗi xảy ra khi lưu', 'danger');
        }
      },
      error: (xhr, status, error) => {
        console.error("Request error:", error, xhr.status, xhr.responseText);
        $(button).html('<i class="fas fa-save"></i> Lưu thay đổi').prop('disabled', false);
        this.resetProcessingState();
        
        // Keep editingInProgress true because the form still has unsaved changes
        // This will maintain the warning if the user tries to navigate away
        
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
  }
};

// Khởi tạo khi DOM ready
$(document).ready(function() {
  if (!AntibioticSensitivityAudit.isViewOnly()) {
    console.log("Initializing AntibioticSensitivityAudit");
    AntibioticSensitivityAudit.init();
  } else {
    console.log("Form is in view-only mode, skipping audit initialization");
  }
});