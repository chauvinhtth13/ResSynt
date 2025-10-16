// Debug version of clinical-form.js with additional logging
// Audit logging for Clinical Form (clinicalForm)

window.ClinicalFormAudit = {
  // Khởi tạo audit logging cho clinical form
  init: function() {
    console.log("Initializing Clinical Form Audit Logging");

    const form = document.getElementById('clinicalForm');
    if (!form) {
      console.warn("Clinical form not found");
      return;
    }

    // Thiết lập giá trị ban đầu cho các trường
    this.setupInitialValues();

    // Thiết lập form submission handler
    this.setupFormSubmission();

    // Thiết lập các event handlers đặc biệt
    this.setupSpecialHandlers();

    this.setupSpecialFields();

    console.log("Clinical Form Audit Logging initialized successfully");
    
    // DEBUG: Check hidden fields for audit log
    this.checkAuditFields();
  },
  
  // DEBUG: Check if audit fields exist and are accessible
  checkAuditFields: function() {
    console.log("DEBUG: Checking audit fields...");
    const oldDataField = document.getElementById('oldDataJson');
    const newDataField = document.getElementById('newDataJson');
    const reasonsField = document.getElementById('reasons_json');
    const changeReasonField = document.getElementById('change_reason');
    
    console.log("oldDataJson field exists:", !!oldDataField);
    console.log("newDataJson field exists:", !!newDataField);
    console.log("reasons_json field exists:", !!reasonsField);
    console.log("change_reason field exists:", !!changeReasonField);
    
    if (oldDataField) {
      console.log("oldDataJson initial value:", oldDataField.value);
    }
    if (newDataField) {
      console.log("newDataJson initial value:", newDataField.value);
    }
    if (reasonsField) {
      console.log("reasons_json initial value:", reasonsField.value);
    }
    if (changeReasonField) {
      console.log("change_reason initial value:", changeReasonField.value);
    }
  },

  // Thiết lập giá trị ban đầu cho các trường
  setupInitialValues: function() {
    console.log("Setting up initial values for audit logging");

    const form = document.getElementById('clinicalForm');
    if (!form) {
      console.error("Clinical form not found for initial values setup");
      return;
    }

    // Lấy tất cả các trường input, select, textarea
    const fields = document.querySelectorAll('#clinicalForm input, #clinicalForm select, #clinicalForm textarea');
    console.log("Found", fields.length, "fields to set initial values for");

    fields.forEach(field => {
      const name = field.name;
      if (!name || name === 'csrfmiddlewaretoken' || name === 'oldDataJson' || name === 'newDataJson' || name === 'reasons_json' || name === 'change_reason') return;

      let initialValue = '';
      if (field.type === 'checkbox') {
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

      field.setAttribute('data-initial-value', initialValue);
      console.log(`Field ${name}: initial value = "${initialValue}"`);
    });

    // Thiết lập initial values cho các formset
    this.setupFormsetInitialValues();
  },

  // Thiết lập initial values cho các formset
  setupFormsetInitialValues: function() {
    const formsetPrefixes = ['vasoidrug', 'hospiprocess', 'main-antibiotic', 'prior-antibiotic', 'initial-antibiotic', 'aehospevent', 'improvesympt'];
    
    formsetPrefixes.forEach(prefix => {
      const rows = document.querySelectorAll(`#${prefix}-formset tbody tr:not(.empty-row)`);
      console.log(`Found ${rows.length} rows for formset ${prefix}`);
      rows.forEach((row, index) => {
        const inputs = row.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
          const name = input.name;
          if (name && !name.includes('-DELETE')) {
            let initialValue = '';
            if (input.type === 'checkbox') {
              initialValue = input.checked ? '1' : '0';
            } else if (input.type === 'radio') {
              if (input.checked) {
                initialValue = input.value;
              } else {
                return;
              }
            } else {
              initialValue = input.value || '';
            }
            input.setAttribute('data-initial-value', initialValue);
            console.log(`Formset ${prefix} field ${name}_${index}: initial value = "${initialValue}"`);
          }
        });
      });
    });
  },

  // Thiết lập form submission handler
  setupFormSubmission: function() {
    const form = document.getElementById('clinicalForm');
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
      console.log("Number of changed fields:", Object.keys(changedFields).length);

      // Nếu có thay đổi, hiển thị modal để nhập lý do
      if (Object.keys(changedFields).length > 0) {
        console.log("Changes detected, showing modal");
        this.showChangeModal(changedFields, () => {
          console.log("Modal callback executed, submitting form");
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
    const formsetPrefixes = ['vasoidrug', 'hospiprocess', 'main-antibiotic', 'prior-antibiotic', 'initial-antibiotic', 'aehospevent', 'improvesympt'];

    // Thu thập từ input fields
    const inputs = document.querySelectorAll('#clinicalForm input:not([type="hidden"])');
    inputs.forEach(input => {
      const name = input.name;
      if (!name || name === 'csrfmiddlewaretoken') return;
      // BỎ QUA các trường thuộc formset
      if (/.*_formset-\d+-[A-Z_]+/.test(name)) return;
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

    // Thu thập từ select fields
    const selects = document.querySelectorAll('#clinicalForm select');
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
    const textareas = document.querySelectorAll('#clinicalForm textarea');
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

    // Thu thập dữ liệu từ formset
    formsetPrefixes.forEach(prefix => {
      const rows = document.querySelectorAll(`#${prefix}-formset tbody tr:not(.empty-row)`);
      data[prefix] = [];
      rows.forEach((row, index) => {
        const rowData = {};
        const inputs = row.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
          const name = input.name;
          if (name && !name.includes('-DELETE')) {
            const fieldName = name.split('-').pop();
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
                  return;
                }
              } else {
                value = input.value || '';
              }
            }
            rowData[fieldName] = value;
          }
        });
        data[prefix].push(rowData);
      });
    });

    return data;
  },

  // So sánh dữ liệu để tìm thay đổi
  compareData: function(oldData, newData) {
    const changedFields = {};
    const fieldLabels = this.getFieldLabels();
    const fieldTypes = this.getFieldTypes();
    const fieldOptions = this.getFieldOptions();

    // DEBUG: Log all field types
    console.log("Field types:", fieldTypes);
    console.log("Field labels:", fieldLabels);
    console.log("Field options:", fieldOptions);
    
    // DEBUG: Check if AuditLogBase exists
    console.log("AuditLogBase exists:", typeof AuditLogBase !== 'undefined');
    if (typeof AuditLogBase === 'undefined') {
      console.error("AuditLogBase is not defined. Make sure base.js is loaded before clinical-form.js");
      return changedFields;
    }

    // So sánh các trường thông thường
    for (const key in newData) {
      // Bỏ qua các key có dạng *_set-<number>-FIELDNAME
      if (
        !Array.isArray(newData[key]) &&
        oldData[key] !== undefined &&
        !/^.*_set-\d+-/.test(key)
      ) {
        const oldValue = AuditLogBase.normalizeValue(oldData[key]);
        const newValue = AuditLogBase.normalizeValue(newData[key]);
        
        // DEBUG: Log normalization
        console.log(`Comparing field ${key}: old="${oldValue}", new="${newValue}"`);
        
        if (oldValue !== newValue) {
          changedFields[key] = {
            old: oldData[key],
            new: newData[key],
            label: fieldLabels[key] || key,
            type: fieldTypes[key] || 'text',
            options: fieldOptions[key] || {}
          };
          
          // DEBUG: Log change
          console.log(`Field ${key} changed: "${oldValue}" -> "${newValue}"`);
        }
      }
    }

    // So sánh formset
    const formsetPrefixes = ['vasoidrug', 'hospiprocess', 'main-antibiotic', 'prior-antibiotic', 'initial-antibiotic', 'aehospevent', 'improvesympt'];
    formsetPrefixes.forEach(prefix => {
      const oldRows = oldData[prefix] || [];
      const newRows = newData[prefix] || [];
      const maxLength = Math.max(oldRows.length, newRows.length);
      
      console.log(`Comparing formset ${prefix}: ${oldRows.length} old rows, ${newRows.length} new rows`);
      
      for (let i = 0; i < maxLength; i++) {
        const oldRow = oldRows[i] || {};
        const newRow = newRows[i] || {};
        const rowKey = `${prefix}_${i}`;
        
        Object.keys(fieldLabels[prefix] || {}).forEach(field => {
          const fieldKey = `${prefix}_${i}_${field}`;
          const oldValue = AuditLogBase.normalizeValue(oldRow[field]);
          const newValue = AuditLogBase.normalizeValue(newRow[field]);
          
          console.log(`Comparing formset field ${fieldKey}: old="${oldValue}", new="${newValue}"`);
          
          if (oldValue !== newValue) {
            changedFields[fieldKey] = {
              old: oldRow[field] || '',
              new: newRow[field] || '',
              label: `${fieldLabels[prefix][field] || field} (Row ${i + 1})`,
              type: fieldTypes[field] || 'text',
              options: fieldOptions[field] || {}
            };
            
            console.log(`Formset field ${fieldKey} changed: "${oldValue}" -> "${newValue}"`);
          }
        });
      }
    });

    return changedFields;
  },

  // Lấy nhãn của các trường
  getFieldLabels: function() {
    const labels = {
      // Page 1 - Thông tin chung
      'STUDYID': 'Mã số nghiên cứu',
      'SITEID': 'Địa điểm NC',
      'SUBJID': 'Mã số đối tượng NC',
      'ADMISDATE': 'Ngày nhập viện',
      'ADMISREASON': 'Lý do nhập viện',
      'SYMPTOMONSETDATE': 'Ngày khởi phát triệu chứng',
      'ADMISDEPT': 'Nhập viện vào khoa',
      'OUTPATIENT_ERDEPT': 'Khoa khám bệnh/Cấp cứu',
      'SYMPTOMADMISDEPT': 'Khoa nhập viện',
      'AWARENESS': 'Ý thức',
      'GCS': 'GCS (điểm)',
      'EYES': 'Mắt (E)',
      'MOTOR': 'Vận động (M)',
      'VERBAL': 'Lời nói (V)',
      'PULSE': 'Mạch (lần/phút)',
      'AMPLITUDE': 'Biên độ',
      'CAPILLARYMOIS': 'Độ ẩm chì',
      'CRT': 'CRT (giây)',
      'CRT_OPTION': 'CRT Option',
      'TEMPERATURE': 'Nhiệt độ (°C)',
      'BLOODPRESSURE_SYS': 'Huyết áp tâm thu (mmHg)',
      'BLOODPRESSURE_DIAS': 'Huyết áp tâm trương (mmHg)',
      'RESPRATE': 'Nhịp thở (lần/phút)',
      'SPO2': 'SpO2 (%)',
      'FIO2': 'FiO2 (%)',
      'RESPPATTERN': 'Kiểu hô hấp',
      'RESPPATTERNOTHERSPEC': 'Kiểu hô hấp khác',
      'RESPSUPPORT': 'Hỗ trợ hô hấp',
      'VASOMEDS': 'Thuốc vận mạch',
      'HYPOTENSION': 'Tụt huyết áp',
      'QSOFA': 'qSOFA',
      'NEWS2': 'NEWS2',
      // Page 2 - Triệu chứng
      'FEVER': 'Sốt (cơ năng)',
      'FATIGUE': 'Mệt mỏi',
      'MUSCLEPAIN': 'Đau cơ',
      'LOSSAPPETITE': 'Chán ăn',
      'COUGH': 'Ho',
      'CHESTPAIN': 'Đau ngực',
      'SHORTBREATH': 'Thở mệt',
      'JAUNDICE': 'Vàng da',
      'PAINURINATION': 'Tiểu đau',
      'BLOODYURINE': 'Tiểu máu',
      'CLOUDYURINE': 'Tiểu đục',
      'EPIGASTRICPAIN': 'Đau thượng vị (cơ năng)',
      'LOWERABDPAIN': 'Đau bụng dưới (cơ năng)',
      'FLANKPAIN': 'Đau hông lưng (cơ năng)',
      'URINARYHESITANCY': 'Tiểu khó/thắt',
      'SUBCOSTALPAIN': 'Đau hạ sườn (cơ năng)',
      'HEADACHE': 'Nhức đầu',
      'POORCONTACT': 'Tiếp xúc kém/li bì',
      'DELIRIUMAGITATION': 'Sảng/kích động',
      'VOMITING': 'Nôn',
      'SEIZURES': 'Co giật',
      'EYEPAIN': 'Đau mắt',
      'REDEYES': 'Đỏ mắt (cơ năng)',
      'NAUSEA': 'Buồn nôn',
      'BLURREDVISION': 'Mờ mắt',
      'SKINLESIONS': 'Sang thương da (cơ năng)',
      'OTHERSYMPTOM': 'Triệu chứng cơ năng khác',
      'SPECIFYOTHERSYMPTOM': 'Triệu chứng cơ năng khác (chi tiết)',
      'WEIGHT': 'Cân nặng (kg)',
      'HEIGHT': 'Chiều cao (cm)',
      'BMI': 'BMI',
      'FEVER_2': 'Sốt (thực thể)',
      'RASH': 'Phát ban',
      'SKINBLEEDING': 'Xuất huyết da',
      'MUCOSALBLEEDING': 'Xuất huyết niêm mạc',
      'SKINLESIONS_2': 'Sang thương da (thực thể)',
      'LUNGCRACKLES': 'Ran ở phổi',
      'CONSOLIDATIONSYNDROME': 'Hội chứng đông đặc',
      'PLEURALEFFUSION': 'Tràn dịch màng phổi',
      'PNEUMOTHORAX': 'Tràn khí màng phổi',
      'HEARTMURMUR': 'Âm thổi tim',
      'ABNORHEARTSOUNDS': 'Tiếng tim bất thường',
      'JUGULARVEIN': 'Tĩnh mạch cổ nổi',
      'HEPATOSPLENOMEGALY': 'Dấu hiệu suy gan',
      'LIVERSPLEEN': 'Dấu hiệu TALTMC',
      'TENDERPERCUSSION': 'Gõ/Lách to',
      'CONSCIOUSNESSDISTURBANCE': 'Rối loạn ý thức',
      'LIMBWEAKNESSPARALYSIS': 'Yếu/liệt chi',
      'WEAKANKLES': 'Liệt TK sọ',
      'MENINGITIS': 'Dấu màng não',
      'REDEYES_2': 'Đỏ mắt (thực thể)',
      'SELFPROTECT': 'Tư mở tấn phòng',
      'LUNGPLUERA': 'Phù',
      'CUSHINGSYNDROME': 'Kiểu hình Cushing',
      'EPIGASTRICPAIN_2': 'Đau thượng vị (thực thể)',
      'RIGHTUPPERABDPAIN': 'Đau hạ vị',
      'FLANKPAIN_2': 'Đau hông lưng (thực thể)',
      'LOWERABDPAIN_2': 'Đau hạ sườn (thực thể)',
      'OTHERSYMPTOM_2': 'Triệu chứng thực thể khác',
      'SPECIFYOTHERSYMPTOM_2': 'Triệu chứng thực thể khác (chi tiết)',
      'COMPLETEDBY': 'Người hoàn thiện',
      'COMPLETEDDATE': 'Ngày hoàn thiện',
      // Page 3 - Chi tiết lâm sàng
      'INFECTFOCUS48H': 'Nguồn nhiễm khuẩn sau 48 giờ',
      'SPECIFYOTHERINFECT48H': 'Nguồn nhiễm khuẩn khác',
      'BLOODINFECT': 'Nhiễm trùng huyết',
      'SOFABASELINE': 'Điểm SOFA nền',
      'DIAGSOFA': 'Điểm SOFA lúc chẩn đoán',
      'SEPTICSHOCK': 'Sốc nhiễm trùng',
      'INFECTSRC': 'Nguồn gốc nhiễm trùng',
      'RESPISUPPORT': 'Hỗ trợ hô hấp (nằm viện)',
      'SUPPORTTYPE': 'Hình thức hỗ trợ hô hấp',
      'OXYMASKDURATION': 'Thời gian Oxy mặt/mask',
      'HFNCNIVDURATION': 'Thời gian HFNC/NIV',
      'VENTILATORDURATION': 'Thời gian thở máy',
      'RESUSFLUID': 'Dịch truyền hồi sức',
      'FLUID6HOURS': 'Tổng dịch truyền 6 giờ',
      'CRYSTAL6HRS': 'Dịch tinh thể 6 giờ',
      'COL6HRS': 'Dịch keo 6 giờ',
      'FLUID24HOURS': 'Tổng dịch truyền 24 giờ',
      'CRYSTAL24HRS': 'Dịch tinh thể 24 giờ',
      'COL24HRS': 'Dịch keo 24 giờ',
      'VASOINOTROPES': 'Thuốc vận mạch/tăng co bóp',
      'DIALYSIS': 'Lọc máu',
      'DRAINAGE': 'Dẫn lưu',
      'DRAINAGETYPE': 'Hình thức dẫn lưu',
      'SPECIFYOTHERDRAINAGE': 'Dẫn lưu khác',
      'PRIORANTIBIOTIC': 'Kháng sinh trước nhập viện',
      'INITIALANTIBIOTIC': 'Kháng sinh ban đầu',
      'INITIALABXAPPROP': 'Kháng sinh ban đầu phù hợp',
      // Formset labels
      'vasoidrug': {
        'VASOIDRUGNAME': 'Tên thuốc vận mạch',
        'VASOIDRUGDOSAGE': 'Liều dùng',
        'VASOIDRUGSTARTDTC': 'Ngày bắt đầu',
        'VASOIDRUGENDDTC': 'Ngày kết thúc'
      },
      'hospiprocess': {
        'DEPTNAME': 'Khoa',
        'STARTDTC': 'Từ thời gian',
        'ENDDTC': 'Đến thời gian',
        'TRANSFER_REASON': 'Lý do chuyển'
      },
      'main-antibiotic': {
        'MAINANTIBIONAME': 'Tên kháng sinh chính',
        'MAINANTIBIODOSAGE': 'Liều dùng',
        'MAINANTIBIOSTARTDTC': 'Ngày bắt đầu',
        'MAINANTIBIOENDDTC': 'Ngày kết thúc'
      },
      'prior-antibiotic': {
        'PRIORANTIBIONAME': 'Tên kháng sinh trước',
        'PRIORANTIBIODOSAGE': 'Liều dùng',
        'PRIORANTIBIOSTARTDTC': 'Ngày bắt đầu',
        'PRIORANTIBIOENDDTC': 'Ngày kết thúc'
      },
      'initial-antibiotic': {
        'INITIALANTIBIONAME': 'Tên kháng sinh ban đầu',
        'INITIALANTIBIODOSAGE': 'Liều dùng',
        'INITIALANTIBIOSTARTDTC': 'Ngày bắt đầu',
        'INITIALANTIBIOENDDTC': 'Ngày kết thúc'
      },
      'aehospevent': {
        'AENAME': 'Biến cố',
        'AEDETAILS': 'Chi tiết biến cố',
        'AEDTC': 'Thời gian đánh giá'
      },
      'improvesympt': {
        'IMPROVE_SYMPTS': 'Cải thiện triệu chứng',
        'SYMPTS': 'Triệu chứng',
        'IMPROVE_CONDITIONS': 'Tình trạng cải thiện',
        'SYMPTSDTC': 'Thời gian đánh giá'
      }
    };

    // Lấy labels từ các thẻ label trong form
    const labelElements = document.querySelectorAll('#clinicalForm label');
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

    return labels;
  },

  // Lấy loại của các trường
  getFieldTypes: function() {
    const types = {};
    const checkboxes = [
      'FEVER', 'FATIGUE', 'MUSCLEPAIN', 'LOSSAPPETITE', 'COUGH', 'CHESTPAIN', 'SHORTBREATH',
      'JAUNDICE', 'PAINURINATION', 'BLOODYURINE', 'CLOUDYURINE', 'EPIGASTRICPAIN', 'LOWERABDPAIN',
      'FLANKPAIN', 'URINARYHESITANCY', 'SUBCOSTALPAIN', 'HEADACHE', 'POORCONTACT', 'DELIRIUMAGITATION',
      'VOMITING', 'SEIZURES', 'EYEPAIN', 'REDEYES', 'NAUSEA', 'BLURREDVISION', 'SKINLESIONS',
      'OTHERSYMPTOM', 'FEVER_2', 'RASH', 'SKINBLEEDING', 'MUCOSALBLEEDING', 'SKINLESIONS_2',
      'LUNGCRACKLES', 'CONSOLIDATIONSYNDROME', 'PLEURALEFFUSION', 'PNEUMOTHORAX', 'HEARTMURMUR',
      'ABNORHEARTSOUNDS', 'JUGULARVEIN', 'HEPATOSPLENOMEGALY', 'LIVERSPLEEN', 'TENDERPERCUSSION',
      'CONSCIOUSNESSDISTURBANCE', 'LIMBWEAKNESSPARALYSIS', 'WEAKANKLES', 'MENINGITIS', 'REDEYES_2',
      'SELFPROTECT', 'LUNGPLUERA', 'CUSHINGSYNDROME', 'EPIGASTRICPAIN_2', 'RIGHTUPPERABDPAIN',
      'FLANKPAIN_2', 'LOWERABDPAIN_2', 'OTHERSYMPTOM_2', 'RESUSFLUID', 'VASOINOTROPES',
      'PRIORANTIBIOTIC', 'INITIALANTIBIOTIC'
    ];
    checkboxes.forEach(name => { types[name] = 'checkbox'; });

    const radios = [
      'RESPPATTERN', 'RESPSUPPORT', 'HYPOTENSION', 'QSOFA', 'NEWS2', 'CRT_OPTION',
      'BLOODINFECT', 'SEPTICSHOCK', 'INFECTSRC', 'RESPISUPPORT', 'DIALYSIS', 'DRAINAGE',
      'DRAINAGETYPE', 'INITIALABXAPPROP'
    ];
    radios.forEach(name => { types[name] = 'radio'; });

    const dates = [
      'ADMISDATE', 'SYMPTOMONSETDATE', 'COMPLETEDDATE', 'VASOIDRUGSTARTDTC', 'VASOIDRUGENDDTC',
      'MAINANTIBIOSTARTDTC', 'MAINANTIBIOENDDTC', 'PRIORANTIBIOSTARTDTC', 'PRIORANTIBIOENDDTC',
      'INITIALANTIBIOSTARTDTC', 'INITIALANTIBIOENDDTC', 'AEDTC', 'SYMPTSDTC', 'STARTDTC', 'ENDDTC'
    ];
    dates.forEach(name => { types[name] = 'date'; });

    const decimals = ['CRT', 'TEMPERATURE', 'WEIGHT', 'HEIGHT', 'BMI'];
    decimals.forEach(name => { types[name] = 'decimal'; });

    const selects = document.querySelectorAll('#clinicalForm select');
    selects.forEach(select => {
      if (select.name) types[select.name] = 'select';
    });

    return types;
  },

  // Lấy options cho các trường select
  getFieldOptions: function() {
    const options = {};
    const selects = document.querySelectorAll('#clinicalForm select');
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
    console.log("ClinicalFormAudit.showChangeModal called with:", changedFields);
    if (!document.getElementById('changeReasonModal')) {
      console.error("Change reason modal not found!");
      return;
    }
    if (typeof AuditLogBase === 'undefined') {
      console.error("AuditLogBase is not defined!");
      return;
    }
    const self = this;
    AuditLogBase.showChangeModal(changedFields, function(reasonsData) {
      console.log("Reasons data received:", reasonsData);
      self.saveAuditData(changedFields, reasonsData);
      if (callback) callback();
    });
  },

  // Lưu dữ liệu audit vào hidden fields
  saveAuditData: function(changedFields, reasonsData) {
    console.log("saveAuditData called with:", changedFields, reasonsData);
    
    // DEBUG: Check if reasonsData exists
    if (!reasonsData) {
      console.error("reasonsData is empty or null!");
      reasonsData = {};
    }
    
    // DEBUG: Check form fields
    const oldDataField = document.getElementById('oldDataJson');
    const newDataField = document.getElementById('newDataJson');
    const reasonsField = document.getElementById('reasons_json');
    const changeReasonField = document.getElementById('change_reason');
    
    if (!oldDataField || !newDataField || !reasonsField || !changeReasonField) {
      console.error("One or more audit fields not found in the form:");
      console.error("oldDataJson exists:", !!oldDataField);
      console.error("newDataJson exists:", !!newDataField);
      console.error("reasons_json exists:", !!reasonsField);
      console.error("change_reason exists:", !!changeReasonField);
      return;
    }
    
    // Lọc bỏ các key dạng *_formset-<number>-FIELDNAME khỏi changedFields
    const filteredChangedFields = {};
    Object.keys(changedFields).forEach(key => {
      if (!/.*_formset-\d+-/.test(key)) {
        filteredChangedFields[key] = changedFields[key];
      }
    });

    const oldData = {};
    const newData = {};
    const reasonsJsonWithLabel = {};

    Object.keys(filteredChangedFields).forEach(key => {
      oldData[key] = filteredChangedFields[key].old;
      newData[key] = filteredChangedFields[key].new;

      // Map lý do thay đổi
      let reasonKey = key;
      if (!(reasonKey in reasonsData)) {
        if (reasonsData[key.toUpperCase()]) reasonKey = key.toUpperCase();
        else if (reasonsData[key.toLowerCase()]) reasonKey = key.toLowerCase();
      }
      if (typeof reasonsData[reasonKey] === 'string') {
        reasonsJsonWithLabel[key] = {
          label: filteredChangedFields[key].label || key,
          reason: reasonsData[reasonKey]
        };
      } else if (typeof reasonsData[reasonKey] === 'object' && reasonsData[reasonKey] !== null) {
        reasonsJsonWithLabel[key] = reasonsData[reasonKey];
      }
    });

    // DEBUG: Log values before setting them
    console.log("Setting oldDataJson to:", oldData);
    console.log("Setting newDataJson to:", newData);
    console.log("Setting reasons_json to:", reasonsJsonWithLabel);

    oldDataField.value = JSON.stringify(oldData);
    newDataField.value = JSON.stringify(newData);
    reasonsField.value = JSON.stringify(reasonsJsonWithLabel);

    const changeReason = Object.entries(reasonsJsonWithLabel)
      .map(([field, obj]) => {
        const label = obj.label || field;
        return `${label}: ${obj.reason}`;
      })
      .join(' | ');

    console.log("Setting change_reason to:", changeReason);
    changeReasonField.value = changeReason;

    console.log("Audit data saved:");
    console.log("- oldDataJson:", oldDataField.value);
    console.log("- newDataJson:", newDataField.value);
    console.log("- reasons_json:", reasonsField.value);
    console.log("- change_reason:", changeReasonField.value);

    Object.keys(reasonsJsonWithLabel).forEach(key => {
      if (key.startsWith('vasoidrug')) {
        console.log('[VASOIDRUG] reasonsJsonWithLabel:', key, reasonsJsonWithLabel[key]);
      }
    });
  },

  // Submit form
  submitForm: function() {
    const form = document.getElementById('clinicalForm');
    
    // DEBUG: Log form values before submitting
    const oldDataField = document.getElementById('oldDataJson');
    const newDataField = document.getElementById('newDataJson');
    const reasonsField = document.getElementById('reasons_json');
    const changeReasonField = document.getElementById('change_reason');
    
    console.log("Form submission - audit fields values:");
    console.log("- oldDataJson:", oldDataField ? oldDataField.value : "field not found");
    console.log("- newDataJson:", newDataField ? newDataField.value : "field not found");
    console.log("- reasons_json:", reasonsField ? reasonsField.value : "field not found");
    console.log("- change_reason:", changeReasonField ? changeReasonField.value : "field not found");
    
    form.submit();
  },

  // Thiết lập các event handlers đặc biệt
  setupSpecialHandlers: function() {
    const form = document.getElementById('clinicalForm');

    // Handle OTHERSYMPTOM checkbox
    const othersymptomCheckbox = document.getElementById('id_OTHERSYMPTOM');
    if (othersymptomCheckbox) {
      othersymptomCheckbox.addEventListener('change', () => {
        document.getElementById('othersymptom_detail').style.display = othersymptomCheckbox.checked ? 'block' : 'none';
      });
    }

    // Handle OTHERSYMPTOM_2 checkbox
    const othersymptom2Checkbox = document.getElementById('id_OTHERSYMPTOM_2');
    if (othersymptom2Checkbox) {
      othersymptom2Checkbox.addEventListener('change', () => {
        document.getElementById('othersymptom_2_detail').style.display = othersymptom2Checkbox.checked ? 'block' : 'none';
      });
    }

    // Handle RESPPATTERN radio
    const resppatternRadios = document.querySelectorAll('input[name="RESPPATTERN"]');
    resppatternRadios.forEach(radio => {
      radio.addEventListener('change', () => {
        document.getElementById('resppattern_other_detail').style.display = radio.value === 'Khác' ? 'block' : 'none';
      });
    });

    // Log khi tick/untick các loại hỗ trợ hô hấp
    const supportTypeCheckboxes = document.querySelectorAll('input[name="SUPPORTTYPE"]');
    supportTypeCheckboxes.forEach(checkbox => {
      checkbox.addEventListener('change', function() {
        const label = document.querySelector(`label[for="${checkbox.id}"]`);
        const labelText = label ? label.textContent.trim() : checkbox.value;
        const checked = checkbox.checked ? '1' : '0';
        console.log(`[AuditLog] SUPPORTTYPE changed: ${labelText} -> ${checked}`);
        // Nếu muốn lưu vào hệ thống log, có thể gọi hàm lưu log tại đây
      });
    });


    // Handle PRIORANTIBIOTIC checkbox
    const priorAntibioticCheckbox = document.getElementById('id_PRIORANTIBIOTIC');
    if (priorAntibioticCheckbox) {
      priorAntibioticCheckbox.addEventListener('change', () => {
        document.getElementById('prior-antibiotic-section').style.display = priorAntibioticCheckbox.checked ? 'block' : 'none';
      });
    }

    // Handle INITIALANTIBIOTIC checkbox
    const initialAntibioticCheckbox = document.getElementById('id_INITIALANTIBIOTIC');
    if (initialAntibioticCheckbox) {
      initialAntibioticCheckbox.addEventListener('change', () => {
        document.getElementById('initial-antibiotic-section').style.display = initialAntibioticCheckbox.checked ? 'block' : 'none';
      });
    }

    // Handle RESPISUPPORT radio
    const respiSupportRadios = document.querySelectorAll('input[name="RESPISUPPORT"]');
    respiSupportRadios.forEach(radio => {
      radio.addEventListener('change', () => {
        const show = radio.value === 'true';
        document.getElementById('respi-support-options').style.display = show ? 'block' : 'none';
        document.getElementById('respi-support-section').style.display = show ? 'block' : 'none';
      });
    });

    // Handle RESUSFLUID radio
    const resusFluidRadios = document.querySelectorAll('input[name="resusfluid_radio"]');
    resusFluidRadios.forEach(radio => {
      radio.addEventListener('change', () => {
        const show = radio.value === 'true';
        document.getElementById('resus-fluid-section').style.display = show ? 'block' : 'none';
        document.getElementById('id_RESUSFLUID').checked = show;
      });
    });

    // Handle VASOINOTROPES radio
    const vasoInotropesRadios = document.querySelectorAll('input[name="vasoinotropes_radio"]');
    vasoInotropesRadios.forEach(radio => {
      radio.addEventListener('change', () => {
        const show = radio.value === 'true';
        document.getElementById('vasodrug-section').style.display = show ? 'block' : 'none';
        document.getElementById('id_VASOINOTROPES').checked = show;
      });
    });

    // Handle DIALYSIS radio
    const dialysisRadios = document.querySelectorAll('input[name="dialysis_radio"]');
    dialysisRadios.forEach(radio => {
      radio.addEventListener('change', () => {
        document.getElementById('id_DIALYSIS').value = radio.value;
      });
    });

    // Handle DRAINAGE radio
    const drainageRadios = document.querySelectorAll('input[name="drainage_radio"]');
    drainageRadios.forEach(radio => {
      radio.addEventListener('change', () => {
        document.getElementById('drainage_type_section').style.display = radio.value === 'yes' ? 'block' : 'none';
        document.getElementById('id_DRAINAGE').value = radio.value;
      });
    });

    // Handle formset add row
    const addButtons = document.querySelectorAll('.add-row');
    addButtons.forEach(button => {
      button.addEventListener('click', () => {
        setTimeout(() => {
          this.setupFormsetInitialValues();
        }, 100);
      });
    });

    // Handle formset delete row
    const formsetTables = document.querySelectorAll('#clinicalForm table[id$="-formset"]');
    formsetTables.forEach(table => {
      table.addEventListener('change', (e) => {
        if (e.target.name && e.target.name.includes('-DELETE')) {
          setTimeout(() => {
            this.setupFormsetInitialValues();
          }, 100);
        }
      });
    });
  },

  // Handle special fields for audit logging
  setupSpecialFields: function() {
    console.log("Loading special fields fix for audit log");
    
    // Thiết lập giá trị ban đầu cho radio buttons đặc biệt
    function setInitialRadioValues() {
      // Xử lý has_aehospevent
      if ($('#aehospevent-formset tbody tr').length > 1 || $('#aehospevent-formset .empty-row').length === 0) {
        $('input[name="has_aehospevent"]').attr('data-initial-value', 'yes');
      } else {
        $('input[name="has_aehospevent"]').attr('data-initial-value', 'no');
      }
      
      // Xử lý has_improvesympt
      if ($('#improvesympt-formset tbody tr').length > 1 || $('#improvesympt-formset .empty-row').length === 0) {
        $('input[name="has_improvesympt"]').attr('data-initial-value', 'yes');
      } else {
        $('input[name="has_improvesympt"]').attr('data-initial-value', 'no');
      }
      
      console.log("Initial values set:");
      console.log("- has_aehospevent:", $('input[name="has_aehospevent"]').attr('data-initial-value'));
      console.log("- has_improvesympt:", $('input[name="has_improvesympt"]').attr('data-initial-value'));
    }
    
    // Thiết lập sự kiện change riêng cho radio buttons
    function setupRadioChangeEvents() {
      // has_aehospevent
      $('input[name="has_aehospevent"]').on('change', function() {
        console.log(`has_aehospevent changed from ${$('input[name="has_aehospevent"]').attr('data-initial-value')} to ${$(this).val()}`);
      });
      
      // has_improvesympt
      $('input[name="has_improvesympt"]').on('change', function() {
        console.log(`has_improvesympt changed from ${$('input[name="has_improvesympt"]').attr('data-initial-value')} to ${$(this).val()}`);
      });
    }
    
    // Override hàm saveAuditData để xử lý đặc biệt cho radio buttons
    const originalSaveAuditData = this.saveAuditData;
    
    this.saveAuditData = function(changedFields, reasonsData) {
      // Gọi hàm gốc
      if (typeof originalSaveAuditData === 'function') {
        originalSaveAuditData.call(this, changedFields, reasonsData);
      }
      
      // Thêm xử lý đặc biệt cho radio buttons
      let specialFields = ['has_aehospevent', 'has_improvesympt'];
      
      specialFields.forEach(function(fieldName) {
        let initialValue = $(`input[name="${fieldName}"]`).attr('data-initial-value') || '';
        let currentValue = $(`input[name="${fieldName}"]:checked`).val() || '';
        
        console.log(`Special field ${fieldName}: initial=${initialValue}, current=${currentValue}`);
        
        // Nếu có thay đổi, ghi đè vào reasons_json
        if (initialValue !== currentValue) {
          let oldReasons = JSON.parse($('#reasons_json').val() || '{}');
          
          oldReasons[fieldName] = {
            label: fieldName,
            reason: '1'
          };
          
          $('#reasons_json').val(JSON.stringify(oldReasons));
          
          // Ghi đè vào oldDataJson và newDataJson
          let oldData = JSON.parse($('#oldDataJson').val() || '{}');
          let newData = JSON.parse($('#newDataJson').val() || '{}');
          
          oldData[fieldName] = initialValue;
          newData[fieldName] = currentValue;
          
          $('#oldDataJson').val(JSON.stringify(oldData));
          $('#newDataJson').val(JSON.stringify(newData));
          
          console.log(`Updated audit data for ${fieldName}`);
        }
      });
    };
    
    // Thực hiện ngay khi trang tải xong
    setInitialRadioValues();
    setupRadioChangeEvents();
    
    // Kiểm tra giá trị khi submit form
    $('#clinicalForm').on('submit', function() {
      console.log("Form submitting, checking special fields...");
      console.log("has_aehospevent:", $('input[name="has_aehospevent"]').attr('data-initial-value'), "->", $('input[name="has_aehospevent"]:checked').val());
      console.log("has_improvesympt:", $('input[name="has_improvesympt"]').attr('data-initial-value'), "->", $('input[name="has_improvesympt"]:checked').val());
    });
  },
};

// Khởi tạo khi DOM ready
document.addEventListener('DOMContentLoaded', function() {
  const form = document.getElementById('clinicalForm');
  const isViewOnly = form && form.classList.contains('view-only-form');

  if (!isViewOnly) {
    ClinicalFormAudit.init();
  }
});
