/**
 * clinical-form-date-handler.js
 * 
 * File xử lý đặc biệt các trường ngày tháng trong form thông tin lâm sàng (ClinicalCase)
 * Giải quyết lỗi "Enter a valid date" khi submit form lâm sàng
 */

(function() {
    // Hàm chính để xử lý các trường ngày tháng trong form lâm sàng
    function initClinicalFormDateHandling() {
        console.log('Clinical form date handling initialized');
        
        // Danh sách các trường ngày tháng cần xử lý
        const dateFields = [
            { 
                id: '#id_ADMISDATE', 
                label: 'Admission Date',
                name: 'ADMISDATE'
            },
            { 
                id: '#id_SYMPTOMONSETDATE', 
                label: 'Ngày bắt đầu triệu chứng',
                name: 'SYMPTOMONSETDATE'
            },
            { 
                id: '#id_COMPLETEDDATE', 
                label: 'Ngày hoàn thành',
                name: 'COMPLETEDDATE'
            }
        ];

        // Xử lý từng trường ngày tháng
        dateFields.forEach(field => {
            processDateField(field);
        });

        // Xử lý sự kiện submit form
        $('#clinicalForm').on('submit', function(e) {
            // Kiểm tra lại tất cả các trường ngày tháng trước khi submit
            let hasError = false;
            
            dateFields.forEach(field => {
                const $field = $(field.id);
                if ($field.length) {
                    // Chuyển đổi định dạng ngày từ DD/MM/YYYY sang YYYY-MM-DD
                    const dateValue = $field.val();
                    if (dateValue && dateValue.trim() !== '') {
                        const formattedDate = formatDateForDjango(dateValue);
                        if (formattedDate) {
                            $field.val(formattedDate);
                            console.log(`Đã chuyển đổi ${field.label}: ${dateValue} -> ${formattedDate}`);
                        } else {
                            hasError = true;
                            console.error(`Không thể chuyển đổi giá trị ngày cho ${field.label}: ${dateValue}`);
                            showErrorForField($field, `Định dạng ngày không hợp lệ. Vui lòng nhập theo định dạng DD/MM/YYYY hoặc YYYY-MM-DD`);
                        }
                    }
                }
            });
            
            if (hasError) {
                e.preventDefault();
                return false;
            }
        });
    }
    
    // Xử lý một trường ngày tháng cụ thể
    function processDateField(field) {
        const $field = $(field.id);
        
        if ($field.length) {
            console.log(`Processing field: ${field.label}`);
            
            // Đảm bảo có thuộc tính type="date" và định dạng đúng
            if (!$field.attr('type') || $field.attr('type') !== 'date') {
                // Xử lý khi không có type="date" - cần sử dụng datepicker
                
                // Thêm class datepicker nếu chưa có
                if (!$field.hasClass('datepicker')) {
                    $field.addClass('datepicker');
                }
                
                // Thêm thuộc tính autocomplete="off" để tránh xung đột
                $field.attr('autocomplete', 'off');
                
                // Khởi tạo bootstrap-datepicker
                $field.datepicker({
                    format: 'yyyy-mm-dd',  // Format phù hợp với Django
                    autoclose: true,
                    todayHighlight: true,
                    clearBtn: true
                });
                
                // Xử lý sự kiện khi datepicker thay đổi
                $field.on('changeDate', function(e) {
                    // Đảm bảo định dạng ngày là YYYY-MM-DD
                    if (e.date) {
                        const year = e.date.getFullYear();
                        const month = String(e.date.getMonth() + 1).padStart(2, '0');
                        const day = String(e.date.getDate()).padStart(2, '0');
                        const formattedDate = `${year}-${month}-${day}`;
                        
                        $(this).val(formattedDate);
                        console.log(`${field.label} updated to: ${formattedDate}`);
                        
                        // Xóa thông báo lỗi nếu có
                        clearErrorForField($(this));
                    }
                });
                
                // Xử lý khi người dùng trực tiếp nhập vào trường input
                $field.on('change', function() {
                    const dateValue = $(this).val();
                    if (dateValue && dateValue.trim() !== '') {
                        const formattedDate = formatDateForDjango(dateValue);
                        if (formattedDate) {
                            $(this).val(formattedDate);
                            console.log(`${field.label} manually entered and reformatted: ${formattedDate}`);
                            clearErrorForField($(this));
                        } else {
                            console.warn(`Invalid date format for ${field.label}: ${dateValue}`);
                            showErrorForField($(this), 'Định dạng ngày không hợp lệ. Vui lòng nhập theo định dạng DD/MM/YYYY hoặc YYYY-MM-DD');
                        }
                    }
                });
                
                // Kiểm tra giá trị hiện tại và định dạng lại nếu cần
                const currentValue = $field.val();
                if (currentValue && currentValue.trim() !== '') {
                    const formattedDate = formatDateForDjango(currentValue);
                    if (formattedDate) {
                        $field.val(formattedDate);
                        console.log(`${field.label} initial value reformatted: ${currentValue} -> ${formattedDate}`);
                    }
                }
            }
            
            // Thêm hidden field để đảm bảo giá trị luôn được gửi với định dạng YYYY-MM-DD
            const hiddenFieldId = `hidden_${field.name}`;
            
            // Chỉ tạo hidden field nếu chưa tồn tại
            if ($(`#${hiddenFieldId}`).length === 0) {
                $('<input>').attr({
                    type: 'hidden',
                    id: hiddenFieldId,
                    name: `${field.name}_iso`
                }).insertAfter($field);
            }
            
            // Cập nhật hidden field mỗi khi visible field thay đổi
            $field.on('change changeDate', function() {
                const dateValue = $(this).val();
                if (dateValue && dateValue.trim() !== '') {
                    const formattedDate = formatDateForDjango(dateValue);
                    if (formattedDate) {
                        $(`#${hiddenFieldId}`).val(formattedDate);
                    }
                } else {
                    $(`#${hiddenFieldId}`).val('');
                }
            });
        }
    }
    
    // Hàm chuyển đổi định dạng ngày từ nhiều định dạng khác nhau sang YYYY-MM-DD
    function formatDateForDjango(dateStr) {
        if (!dateStr || dateStr.trim() === '') return '';
        
        // Nếu đã đúng định dạng YYYY-MM-DD
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
            return dateStr;
        }
        
        // Thử với định dạng DD/MM/YYYY
        if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(dateStr)) {
            const parts = dateStr.split('/');
            const day = parseInt(parts[0], 10);
            const month = parseInt(parts[1], 10);
            const year = parseInt(parts[2], 10);
            
            // Kiểm tra tính hợp lệ
            if (isValidDate(year, month, day)) {
                return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            }
        }
        
        // Thử với định dạng MM/DD/YYYY
        if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(dateStr)) {
            const parts = dateStr.split('/');
            const month = parseInt(parts[0], 10);
            const day = parseInt(parts[1], 10);
            const year = parseInt(parts[2], 10);
            
            // Kiểm tra tính hợp lệ
            if (isValidDate(year, month, day)) {
                return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            }
        }
        
        // Thử với định dạng DD-MM-YYYY
        if (/^\d{1,2}-\d{1,2}-\d{4}$/.test(dateStr)) {
            const parts = dateStr.split('-');
            const day = parseInt(parts[0], 10);
            const month = parseInt(parts[1], 10);
            const year = parseInt(parts[2], 10);
            
            // Kiểm tra tính hợp lệ
            if (isValidDate(year, month, day)) {
                return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            }
        }
        
        // Thử với định dạng YYYY/MM/DD
        if (/^\d{4}\/\d{1,2}\/\d{1,2}$/.test(dateStr)) {
            const parts = dateStr.split('/');
            const year = parseInt(parts[0], 10);
            const month = parseInt(parts[1], 10);
            const day = parseInt(parts[2], 10);
            
            // Kiểm tra tính hợp lệ
            if (isValidDate(year, month, day)) {
                return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            }
        }
        
        // Sử dụng Date.parse để thử các định dạng khác
        try {
            const date = new Date(dateStr);
            if (!isNaN(date.getTime())) {
                const year = date.getFullYear();
                const month = date.getMonth() + 1;
                const day = date.getDate();
                
                if (isValidDate(year, month, day)) {
                    return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                }
            }
        } catch (e) {
            console.error("Lỗi chuyển đổi ngày:", e);
        }
        
        // Không thể chuyển đổi
        return null;
    }
    
    // Kiểm tra tính hợp lệ của ngày tháng
    function isValidDate(year, month, day) {
        if (month < 1 || month > 12) return false;
        if (day < 1 || day > 31) return false;
        
        // Kiểm tra chính xác số ngày trong tháng
        if (month === 2) {
            // Tháng 2
            const isLeapYear = ((year % 4 === 0) && (year % 100 !== 0)) || (year % 400 === 0);
            return day <= (isLeapYear ? 29 : 28);
        } else if ([4, 6, 9, 11].includes(month)) {
            // Tháng 4, 6, 9, 11 có 30 ngày
            return day <= 30;
        } else {
            // Các tháng còn lại có 31 ngày
            return day <= 31;
        }
    }
    
    // Hiển thị thông báo lỗi cho trường
    function showErrorForField($field, message) {
        // Xóa thông báo lỗi cũ nếu có
        clearErrorForField($field);
        
        // Thêm class lỗi
        $field.addClass('is-invalid');
        
        // Tạo feedback element
        const $feedback = $('<div>').addClass('invalid-feedback').text(message);
        $field.after($feedback);
    }
    
    // Xóa thông báo lỗi cho trường
    function clearErrorForField($field) {
        $field.removeClass('is-invalid');
        $field.next('.invalid-feedback').remove();
    }
    
    // Khởi tạo khi DOM đã sẵn sàng
    $(document).ready(function() {
        console.log('Clinical form date handler checking for form...');
        
        // Tìm form lâm sàng - có thể có nhiều id khác nhau
        if ($('#clinicalForm').length) {
            console.log('Found #clinicalForm');
            initClinicalFormDateHandling();
        } else if ($('#clinical_case_form').length) {
            console.log('Found #clinical_case_form, renaming to clinicalForm');
            $('#clinical_case_form').attr('id', 'clinicalForm');
            initClinicalFormDateHandling();
        } else if ($('form').has('input[name="ADMISDATE"]').length) {
            // Nếu không tìm thấy theo id, tìm theo input field
            console.log('Found form with ADMISDATE input, renaming to clinicalForm');
            $('form').has('input[name="ADMISDATE"]').first().attr('id', 'clinicalForm');
            initClinicalFormDateHandling();
        } else {
            console.log('Clinical form not found on this page');
        }
    });
})();
