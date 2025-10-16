// Base audit log functions for CRF forms

window.AuditLogBase = {
  normalizeValue: function(val) {
    if (val === true || val === '1' || val === 1) return '1';
    if (val === false || val === '0' || val === 0) return '0';
    if (val === null || val === undefined) return '';
    const v = String(val).trim();
    if (['null', 'none', 'na', 'trống', ''].includes(v.toLowerCase())) return '';

    // Normalize date formats to YYYY-MM-DD for consistent comparison
    if (v.match(/^\d{1,2}\/\d{1,2}\/\d{4}$/)) {
      // DD/MM/YYYY to YYYY-MM-DD
      const parts = v.split('/');
      const day = parts[0].padStart(2, '0');
      const month = parts[1].padStart(2, '0');
      const year = parts[2];
      return `${year}-${month}-${day}`;
    }
    if (v.match(/^\d{4}-\d{2}-\d{2}$/)) {
      // Already YYYY-MM-DD
      return v;
    }
    if (v.match(/^\d{1,2}\/\d{1,2}\/\d{4}/)) {
      // Handle DD/MM/YYYY with time: take date part
      const datePart = v.split(' ')[0];
      const parts = datePart.split('/');
      const day = parts[0].padStart(2, '0');
      const month = parts[1].padStart(2, '0');
      const year = parts[2];
      return `${year}-${month}-${day}`;
    }

    // Giữ nguyên giá trị gốc cho các trường không phải boolean hoặc date
    return v;
  },

  compareFields: function(initialData, formData, fieldLabels, fieldTypes, fieldOptions) {
    // Trả về các trường đã thay đổi
    const changedFields = {};
    for (const key in formData) {
      if (
        initialData[key] !== undefined &&
        this.normalizeValue(initialData[key]) !== this.normalizeValue(formData[key])
      ) {
        changedFields[key] = {
          old: initialData[key],
          new: formData[key],
          label: fieldLabels[key] || key,
          type: fieldTypes[key] || 'text',
          options: fieldOptions[key] || {}
        };
      }
    }
    return changedFields;
  },

  showChangeModal: function(changedFields, onSubmitCallback) {
    $('#changeTableBody').empty();
    
    // Xử lý changedFields dạng Object (dùng cho clinical, enrollment form)
    if (!Array.isArray(changedFields)) {
      for (const field in changedFields) {
        // BỎ QUA các trường chứa 'formset-'
        if (field.includes('formset-')) continue;
        const fieldInfo = changedFields[field];
        const oldValue = this.formatFieldValue(fieldInfo, fieldInfo.old);
        const newValue = this.formatFieldValue(fieldInfo, fieldInfo.new);
        const textareaId = `reason_${field.replace(/[^a-zA-Z0-9]/g, '_')}`;
        $('#changeTableBody').append(`
          <tr data-field="${field}">
            <td><strong>${field}</strong></td>
            <td>${fieldInfo.label || field}</td>
            <td>${oldValue}</td>
            <td>${newValue}</td>
            <td>
              <textarea class="reason-textarea" id="${textareaId}" required></textarea>
              <div class="invalid-feedback-custom">Vui lòng nhập lý do thay đổi cho trường này</div>
            </td>
          </tr>
        `);
      }
    } 
    // Xử lý changedFields dạng Array (dùng cho laboratory form)
    else {
      for (let i = 0; i < changedFields.length; i++) {
        const fieldInfo = changedFields[i];
        const field = fieldInfo.field;
        
        // Skip formset fields that should be ignored
        if (field && field.includes('formset-')) continue;
        
        // Get display values
        const oldValue = fieldInfo.displayOldValue !== undefined ? 
                        fieldInfo.displayOldValue : 
                        this.formatFieldValue(fieldInfo, fieldInfo.oldValue || fieldInfo.old);
                        
        const newValue = fieldInfo.displayNewValue !== undefined ? 
                        fieldInfo.displayNewValue : 
                        this.formatFieldValue(fieldInfo, fieldInfo.newValue || fieldInfo.new);
        
        // Create a safe ID for the textarea
        const textareaId = `reason_${String(field).replace(/[^a-zA-Z0-9]/g, '_')}`;
        
        // Create the table row with the field information
        $('#changeTableBody').append(`
          <tr data-field="${field}" data-index="${i}">
            <td><strong>${field}</strong></td>
            <td>${fieldInfo.fieldDisplayName || fieldInfo.label || field}</td>
            <td>${oldValue}</td>
            <td>${newValue}</td>
            <td>
              <textarea class="reason-textarea" id="${textareaId}" required></textarea>
              <div class="invalid-feedback-custom">Vui lòng nhập lý do thay đổi cho trường này</div>
            </td>
          </tr>
        `);
      }
    }
    
    // Show the modal
    $('#changeReasonModal').modal('show');
    setTimeout(() => { $('#changeTableBody textarea:first').focus(); }, 500);

    // Handle saving reasons
    $('#saveWithReason').off('click').on('click', function() {
      let allValid = true;
      const reasonsData = {};
      
      $('#changeTableBody tr').each(function() {
        const field = $(this).data('field');
        const index = $(this).data('index');
        const textarea = $(this).find('textarea');
        const reason = textarea.val().trim();
        
        if (!reason) {
          textarea.addClass('is-invalid');
          allValid = false;
        } else {
          textarea.removeClass('is-invalid');
          
          // Luôn sử dụng tên trường gốc làm key cho reasonsData 
          // không chuyển thành uppercase để tránh mất khớp
          if (field) {
            reasonsData[field] = reason;
          } else {
            console.log("Warning: field is empty or undefined");
          }
        }
      });
      
      if (!allValid) return;

      // Xử lý kết quả tùy thuộc vào kiểu dữ liệu của changedFields
      if (!Array.isArray(changedFields)) {
        // Object-based changedFields (clinical, enrollment)
        $('#reasonsJson').val(JSON.stringify(reasonsData));
        $('#change_reason').val(Object.entries(reasonsData).map(([field, reason]) => {
          // Sử dụng key gốc từ changedFields để tìm label
          const label = changedFields[field]?.label || field;
          return `${label}: ${reason}`;
        }).join(' | '));
      } else {
        // Array-based changedFields (laboratory)
        $('#reasonsJson').val(JSON.stringify(reasonsData));
        
        // Create the human-readable change reason
        const changeReasonText = $('#changeTableBody tr').map(function() {
          const field = $(this).data('field');
          const index = $(this).data('index');
          const reason = $(this).find('textarea').val().trim();
          
          // Get field display name from the table row or from the original data
          const fieldLabel = $(this).find('td:nth-child(2)').text() || 
                             (changedFields[index] ? 
                               (changedFields[index].fieldDisplayName || 
                                changedFields[index].label || field) : field);
          
          return `${fieldLabel}: ${reason}`;
        }).get().join(' | ');
        
        $('#change_reason').val(changeReasonText);
      }
      
      // Hide modal and call callback
      $('#changeReasonModal').modal('hide');
      if (onSubmitCallback) onSubmitCallback(reasonsData);
    });

    // Clear validation on input
    $(document).on('input', '.reason-textarea', function() {
      $(this).removeClass('is-invalid');
    });

    // Fill all reasons functionality
    $('#fillAllReasons').off('click').on('click', function() {
      $('#fillAllReasonsModal').modal('show');
    });
    $('#applyCommonReason').off('click').on('click', function() {
      const commonReason = $('#commonReason').val().trim();
      if (commonReason) {
        $('.reason-textarea').val(commonReason).removeClass('is-invalid');
        $('#fillAllReasonsModal').modal('hide');
      }
    });
  },

  formatFieldValue: function(fieldInfo, value) {
    if (value === undefined || value === null || value === '') {
      return '<em class="null-value">Trống</em>';
    }
    
    // Determine the field type
    const fieldType = fieldInfo.type || 'text';
    
    switch (fieldType) {
      case 'checkbox':
        return value === '1' || value === 'true' || value === true ? 'Có' : 'Không';
      
      case 'select':
      case 'radio':
        if (fieldInfo.options && fieldInfo.options[value]) {
          return fieldInfo.options[value];
        }
        return value;
      
      case 'date':
        try {
          // Handle date formatting based on format
          if (typeof value === 'string') {
            if (value.includes('/')) {
              // Already in DD/MM/YYYY format
              return value;
            } else if (value.includes('-')) {
              // Convert from YYYY-MM-DD to DD/MM/YYYY
              const parts = value.split('-');
              if (parts.length === 3) {
                return `${parts[2]}/${parts[1]}/${parts[0]}`;
              }
            }
          }
          
          // Fall back to using Date object if the above didn't work
          try {
            const date = new Date(value);
            if (!isNaN(date.getTime())) {
              return date.toLocaleDateString('vi-VN');
            }
          } catch (e) { /* ignore error, we'll return the original value */ }
          
          return value;
        } catch (e) { 
          console.warn("Error formatting date:", e);
          return value; 
        }
      
      default:
        return value;
    }
  }
};