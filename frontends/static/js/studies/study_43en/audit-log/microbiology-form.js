// Microbiology Form Audit Logging
// Tích hợp với base.js để ghi lại log cho form nuôi cấy vi sinh

window.MicrobiologyFormAudit = {
  // Khởi tạo audit logging cho microbiology form
  init: function() {
    console.log("Initializing Microbiology Form Audit Logging");

    // Kiểm tra chế độ chỉ xem
    if (this.isViewOnly()) {
      console.log("View-only mode, disabling audit logging");
      return;
    }

    // Thiết lập giá trị ban đầu cho các trường
    this.setupInitialValues();

    // Thiết lập form submission handler cho form thêm mới
    this.setupAddFormSubmission();

    // Thiết lập form submission handler cho form edit
    this.setupEditFormSubmission();

    console.log("Microbiology Form Audit Logging initialized successfully");
  },

  // Kiểm tra xem đang ở chế độ chỉ xem không
  isViewOnly: function() {
    return document.querySelector('.readonly-form') !== null;
  },

  // Thiết lập giá trị ban đầu cho các trường
  setupInitialValues: function() {
    console.log("Setting up initial values for audit logging");

    // Thiết lập initial values cho form thêm mới
    const newForm = document.getElementById('newCultureForm');
    if (newForm) {
      const fields = newForm.querySelectorAll('input, select');
      fields.forEach(field => {
        if (field.name && field.name !== 'csrfmiddlewaretoken') {
          const value = field.value || '';
          field.setAttribute('data-initial-value', value);
          console.log(`Set initial value for ${field.name}: ${value}`);
        }
      });
    }

    // Thiết lập initial values cho modal edit
    const editForm = document.getElementById('editCultureForm');
    if (editForm) {
      console.log("Edit form found, initial values will be set when modal opens");
    }
  },

  // Thiết lập form submission handler cho form thêm mới
  setupAddFormSubmission: function() {
    const addButton = document.getElementById('btnAddCulture');
    if (!addButton) return;

    // Gỡ bỏ handler gốc
    $(addButton).off('click');
    addButton.onclick = null;

    $(addButton).on('click', (e) => {
      e.preventDefault();
      console.log("New form submit event triggered");

      // Validate
      const sampleType = $('#new-sample-type').val();
      const otherSample = $('#other-sample-type').val();
      if (!sampleType) {
        this.showMessage('Vui lòng chọn loại bệnh phẩm', 'warning');
        return;
      }
      if (sampleType === 'OTHER' && !otherSample.trim()) {
        this.showMessage('Vui lòng nhập loại bệnh phẩm khác', 'warning');
        return;
      }

      // Thu thập dữ liệu
      const currentData = this.collectFormData(false, 'newCultureForm');
      const initialData = this.collectFormData(true, 'newCultureForm');
      console.log("Initial data (new):", initialData);
      console.log("Current data (new):", currentData);

      // So sánh dữ liệu để tìm thay đổi
      const changedFields = this.compareData(initialData, currentData);
      console.log("Changed fields (new):", changedFields);

      // Luôn hiển thị modal lý do cho CREATE
      this.showChangeModal(changedFields, (reasonsData) => {
        this.saveAuditData(changedFields, reasonsData, 'newCultureForm', () => {
          this.submitAddForm();
        });
      });
    });
  },

  // Thiết lập form submission handler cho form edit
  setupEditFormSubmission: function() {
    const saveButton = document.getElementById('btnSaveEditedCulture');
    if (!saveButton) {
      console.warn("Edit form save button not found");
      return;
    }

    console.log("Setting up edit form submission handler");

    // Gỡ bỏ tất cả handler hiện có
    $(document).off('click', '#btnSaveEditedCulture');
    $(saveButton).off('click');
    saveButton.onclick = null;

    // Thiết lập handler mới
    $(saveButton).on('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      console.log("Edit form save button clicked");

      // Thu thập dữ liệu
      const currentData = this.collectFormData(false, 'editCultureForm');
      const initialData = this.collectFormData(true, 'editCultureForm');
      console.log("Initial data (edit):", initialData);
      console.log("Current data (edit):", currentData);

      // So sánh dữ liệu để tìm thay đổi
      const changedFields = this.compareData(initialData, currentData);
      console.log("Changed fields (edit):", changedFields);

      // Nếu không có thay đổi, thông báo và không submit
      if (Object.keys(changedFields).length === 0) {
        this.showMessage('Không có thay đổi để lưu', 'info');
        $('#btnSaveEditedCulture').html('<i class="fas fa-save"></i> Lưu thay đổi').prop('disabled', false);
        return;
      }

      // Hiển thị modal thay đổi để nhập lý do
      this.showChangeModal(changedFields, (reasonsData) => {
        this.saveAuditData(changedFields, reasonsData, 'editCultureForm', () => {
          console.log("Audit data saved, now submitting edit form");
          this.submitEditForm();
        });
      });
    });
  },

  // Thu thập dữ liệu từ form
  collectFormData: function(useInitialValues = false, formId) {
    const data = {};
    const form = document.getElementById(formId);
    if (!form) return data;

    // Thu thập từ input fields
    const inputs = form.querySelectorAll('input:not([type="hidden"])');
    inputs.forEach(input => {
      if (input.name) {
        if (useInitialValues) {
          const initialValue = input.getAttribute('data-initial-value') || '';
          data[input.name] = initialValue;
        } else {
          data[input.name] = input.value || '';
        }
      }
    });

    // Thu thập từ select fields
    const selects = form.querySelectorAll('select');
    selects.forEach(select => {
      if (select.name) {
        if (useInitialValues) {
          const initialValue = select.getAttribute('data-initial-value') || '';
          data[select.name] = initialValue;
        } else {
          data[select.name] = select.value || '';
        }
      }
    });

    return data;
  },

  // So sánh dữ liệu để tìm thay đổi
  compareData: function(oldData, newData) {
    const fieldOptions = this.getFieldOptions();
    const changedFields = window.AuditLogBase.compareFields(
      oldData, 
      newData, 
      this.getFieldLabels(), 
      this.getFieldTypes(), 
      this.getFieldOptions()
    );

    // Ánh xạ giá trị hiển thị cho các trường select
    Object.keys(changedFields).forEach(key => {
      if (key in fieldOptions) {
        const options = fieldOptions[key];
        changedFields[key].old = options[changedFields[key].old] || changedFields[key].old;
        changedFields[key].new = options[changedFields[key].new] || changedFields[key].new;
      }
    });

    return changedFields;
  },

  // Lấy nhãn của các trường
  getFieldLabels: function() {
    return {
      'SPECIMENTYPE': 'Loại bệnh phẩm',
      'OTHERSPECIMEN': 'Loại bệnh phẩm khác',
      'RESULT': 'Kết quả',
      'RESULTDETAILS': 'Chi tiết kết quả',
      'SPECIMENID': 'Mã số bệnh phẩm (SID)',
      'PERFORMEDDATE': 'Ngày thực hiện'
    };
  },

  // Lấy kiểu dữ liệu của các trường
  getFieldTypes: function() {
    return {
      'SPECIMENTYPE': 'select',
      'OTHERSPECIMEN': 'text',
      'RESULT': 'select',
      'RESULTDETAILS': 'text',
      'SPECIMENID': 'text',
      'PERFORMEDDATE': 'date'
    };
  },

  // Lấy tùy chọn của các trường select
  getFieldOptions: function() {
    return {
      'SPECIMENTYPE': {
        'BLOOD': 'Máu',
        'URINE': 'Nước tiểu',
        'PLEURAL_FLUID': 'Dịch màng bụng',
        'PERITONEAL_FLUID': 'Dịch màng phổi',
        'PUS': 'Đàm',
        'BRONCHIAL': 'Dịch rửa phế quản',
        'CSF': 'Dịch não tủy',
        'WOUND': 'Dịch vết thương',
        'OTHER': 'Khác'
      },
      'RESULT': {
        'POSITIVE': 'Dương tính',
        'NEGATIVE': 'Âm tính'
      }
    };
  },

  // Hiển thị thông báo
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

  // Hiển thị modal thay đổi
  showChangeModal: function(changedFields, callback) {
    console.log("MicrobiologyFormAudit.showChangeModal called with:", changedFields);
    if (!document.getElementById('changeReasonModal')) {
      console.error("Change reason modal not found!");
      return;
    }
    window.AuditLogBase.showChangeModal(changedFields, callback);
  },

  // Lưu dữ liệu audit log
  saveAuditData: function(changedFields, reasonsData, formId, callback) {
    const oldData = {};
    const newData = {};
    const reasonsJsonWithLabel = {};

    Object.keys(changedFields).forEach(key => {
      oldData[key] = changedFields[key].old; // Sử dụng giá trị hiển thị đã ánh xạ
      newData[key] = changedFields[key].new; // Sử dụng giá trị hiển thị đã ánh xạ
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

    // Tìm hoặc tạo hidden inputs
    const form = document.getElementById(formId);
    if (!form) {
      console.error(`Form ${formId} not found!`);
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

    console.log("Audit data saved for form", formId, ":", { oldData, newData, reasonsJsonWithLabel, changeReason });

    if (callback) callback();
  },

  // Gửi form thêm mới
  submitAddForm: function() {
    const form = document.getElementById('newCultureForm');
    const $btn = $('#btnAddCulture');
    const originalHtml = $btn.html();

    const formData = new FormData(form);
    console.log("Submitting new form with data:", Array.from(formData.entries()));

    // Parse usubjid từ URL path: /study_43en/{usubjid}/microbiology/
    const pathParts = window.location.pathname.split('/').filter(p => p);
    const microIndex = pathParts.indexOf('microbiology');
    const usubjid = microIndex > 0 ? pathParts[microIndex - 1] : pathParts[1];

    $btn.html('<i class="fas fa-spinner fa-spin"></i> Đang lưu...').prop('disabled', true);

    $.ajax({
      url: `/study_43en/${usubjid}/microbiology/quick-create/`,
      method: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: (response) => {
        console.log("Create success:", response);
        if (response.success) {
          this.showMessage('Đã thêm mẫu nuôi cấy mới thành công!', 'success');
          setTimeout(() => {
            window.location.reload();
          }, 500);
        } else {
          $btn.html(originalHtml).prop('disabled', false);
          this.showMessage(response.message || 'Có lỗi xảy ra', 'danger');
        }
      },
      error: (xhr, status, error) => {
        console.error("Create error:", error);
        $btn.html(originalHtml).prop('disabled', false);
        let errorMsg = 'Có lỗi xảy ra khi tạo mẫu';
        try {
          const response = JSON.parse(xhr.responseText);
          if (response.message) errorMsg = response.message;
        } catch (e) {
          console.log("Could not parse error response");
        }
        this.showMessage(errorMsg, 'danger');
      }
    });
  },

  // Gửi form edit
  submitEditForm: function() {
    const form = document.getElementById('editCultureForm');
    const $btn = $('#btnSaveEditedCulture');
    const originalHtml = $btn.html();
    const cultureId = $('#edit-culture-id').val();
    
    // Parse usubjid từ URL path: /study_43en/{usubjid}/microbiology/
    const pathParts = window.location.pathname.split('/').filter(p => p);
    const microIndex = pathParts.indexOf('microbiology');
    const usubjid = microIndex > 0 ? pathParts[microIndex - 1] : pathParts[1];

    const formData = new FormData(form);
    console.log("Submitting edit form with data:", Array.from(formData.entries()));

    $btn.html('<i class="fas fa-spinner fa-spin"></i> Đang lưu...').prop('disabled', true);

    $.ajax({
      url: `/study_43en/${usubjid}/microbiology/${cultureId}/update/`,
      method: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: (response) => {
        console.log("Update success:", response);
        if (response.success) {
          this.showMessage('Đã cập nhật thông tin mẫu nuôi cấy thành công!', 'success');
          $('#editCultureModal').modal('hide');
          setTimeout(() => {
            window.location.reload();
          }, 500);
        } else {
          $btn.html(originalHtml).prop('disabled', false);
          this.showMessage(response.message || 'Có lỗi xảy ra khi cập nhật', 'danger');
        }
      },
      error: (xhr, status, error) => {
        console.error("Update error:", error);
        $btn.html(originalHtml).prop('disabled', false);
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
  },

  // Cập nhật giá trị ban đầu sau khi mở modal edit
  updateEditFormInitialValues: function() {
    const editForm = document.getElementById('editCultureForm');
    if (!editForm) return;

    const fields = editForm.querySelectorAll('input, select');
    fields.forEach(field => {
      if (field.name && field.name !== 'csrfmiddlewaretoken' && field.name !== 'culture_id') {
        let value = '';
        if (field.tagName === 'SELECT') {
          value = field.value || '';
        } else {
          value = field.value || '';
        }
        field.setAttribute('data-initial-value', value);
        console.log(`Set initial value for ${field.name} in edit form: ${value}`);
      }
    });
  }
};

// Khởi tạo khi DOM ready
$(document).ready(function() {
  // Khởi tạo audit logging
  window.MicrobiologyFormAudit.init();

  // Thêm event listener cho modal edit khi mở để cập nhật giá trị ban đầu
  $('#editCultureModal').on('shown.bs.modal', function() {
    window.MicrobiologyFormAudit.updateEditFormInitialValues();
  });
});