$(document).ready(function() {
  // Chỉ xử lý nếu không phải readonly
  if ($('#screeningForm').length && !window.isReadonly) {
    const $form = $('#screeningForm');

    // Định nghĩa các labels, types, options
    const fieldLabels = {
      SCRID: "Mã sàng lọc",
      USUBJID: "USUBJID",
      STUDYID: "Mã nghiên cứu",
      SITEID: "Mã cơ sở",
      SUBJID: "Mã bệnh nhân",
      INITIAL: "Viết tắt",
      UPPER16AGE: "Trên 16 tuổi",
      INFPRIOR2OR48HRSADMIT: "Nhiễm trùng trước nhập viện 2 hoặc 48 giờ",
      ISOLATEDKPNFROMINFECTIONORBLOOD: "Phân lập KPN từ nhiễm trùng hoặc máu",
      KPNISOUNTREATEDSTABLE: "KPN chưa điều trị, ổn định",
      CONSENTTOSTUDY: "Đồng ý tham gia nghiên cứu",
      SCREENINGFORMDATE: "Ngày điền phiếu sàng lọc",
      COMPLETEDBY: "Người hoàn thành",
      COMPLETEDDATE: "Ngày hoàn thành",
      ENTRY: "Entry",
      ENTEREDTIME: "Thời gian nhập",
      CONFIRMED: "Đã xác nhận",
      UNRECRUITED_REASON: "Lý do không tuyển",
      WARD: "Khoa/Phòng",
      is_confirmed: "Đã xác nhận"
    };
    const fieldTypes = {}; // nếu cần, bổ sung như enrollment
    const fieldOptions = {}; // nếu cần, bổ sung như enrollment

    // LẤY INITIAL DATA CHÍNH XÁC HƠN
    const initialData = {};
    $form.find('input[type="text"], input[type="date"], textarea').each(function() {
      const name = $(this).attr('name');
      if (name && name !== 'csrfmiddlewaretoken') {
        initialData[name] = ($(this).attr('data-initial-value') || '').trim();
      }
    });

    // Đặc biệt xử lý radio buttons để lấy đúng giá trị ban đầu
    const radioFields = [
      'UPPER16AGE', 'INFPRIOR2OR48HRSADMIT',
      'ISOLATEDKPNFROMINFECTIONORBLOOD',
      'KPNISOUNTREATEDSTABLE', 'CONSENTTOSTUDY'
    ];
    radioFields.forEach(fieldName => {
      const checkedRadio = $(`input[name="${fieldName}"]:checked`);
      if (checkedRadio.length) {
        initialData[fieldName] = checkedRadio.val();
      } else {
        initialData[fieldName] = '';
      }
    });

    $form.on('submit', function(e) {
      const formData = {};
      $form.serializeArray().forEach(function(item) {
        if (item.name !== 'csrfmiddlewaretoken') {
          formData[item.name] = item.value.trim();
        }
      });
      $form.find('input[type="checkbox"]').each(function() {
        const name = $(this).attr('name');
        if (name) {
          formData[name] = $(this).prop('checked') ? '1' : '0';
        }
      });

      // So sánh dữ liệu để tìm các trường thay đổi và gán label động
      const changedFields = {};
      for (const key in formData) {
        if (initialData.hasOwnProperty(key)) {
          // Chuẩn hóa giá trị để so sánh
          const oldValue = (initialData[key] === undefined || initialData[key] === null) ? '' : initialData[key].toString().trim();
          const newValue = (formData[key] === undefined || formData[key] === null) ? '' : formData[key].toString().trim();
          if (oldValue !== newValue) {
            changedFields[key] = {
              old: initialData[key],
              new: formData[key],
              label: fieldLabels[key] || key,
              type: fieldTypes[key] || 'text',
              options: fieldOptions[key] || {}
            };
          }
        }
      }

      if (Object.keys(changedFields).length > 0) {
        e.preventDefault();
        $('#oldDataJson').val(JSON.stringify(Object.fromEntries(
          Object.entries(changedFields).map(([k, v]) => [k, v.old])
        )));
        $('#newDataJson').val(JSON.stringify(Object.fromEntries(
          Object.entries(changedFields).map(([k, v]) => [k, v.new])
        )));

        // Hiển thị modal nhập lý do thay đổi
        AuditLogBase.showChangeModal(changedFields, function(reasonsData) {
          // Đảm bảo reasons_json chứa cả label động
          const reasonsJsonWithLabel = {};
          Object.keys(changedFields).forEach(key => {
            if (typeof reasonsData[key] === 'string') {
              reasonsJsonWithLabel[key] = {
                label: changedFields[key].label || key,
                reason: reasonsData[key]
              };
            } else if (typeof reasonsData[key] === 'object' && reasonsData[key] !== null) {
              reasonsJsonWithLabel[key] = reasonsData[key];
            }
          });

          $('#reasons_json').val(JSON.stringify(reasonsJsonWithLabel));
          const changeReason = Object.entries(reasonsJsonWithLabel)
            .map(([field, obj]) => {
              const label = obj.label || field;
              return `${label}: ${obj.reason}`;
            })
            .join(' | ');
          $('#change_reason').val(changeReason);

          $form.off('submit').submit();
        });
      }
    });
  }
});