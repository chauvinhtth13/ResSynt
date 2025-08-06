/**
 * Xử lý validation cho các trường ngày tháng trong form 43EN
 * File này chịu trách nhiệm xử lý các trường ngày tháng, đặc biệt là ngày sinh
 * để đảm bảo dữ liệu được chuyển đổi đúng định dạng
 */

// Hàm chuyển đổi từ chuỗi DD/MM/YYYY thành các ngày/tháng/năm riêng biệt
function parseBirthDateComponents(dateString) {
    if (!dateString || dateString === 'Invalid date' || dateString.trim() === '') {
        return { day: '', month: '', year: '' };
    }

    let day = '', month = '', year = '';

    // Xử lý trường hợp định dạng DD/MM/YYYY
    if (dateString.indexOf('/') > -1) {
        const parts = dateString.split('/');
        if (parts.length === 3) {
            day = parseInt(parts[0], 10);
            month = parseInt(parts[1], 10);
            year = parseInt(parts[2], 10);
            
            // Kiểm tra tính hợp lệ của các giá trị
            if (isNaN(day) || day < 1 || day > 31) day = '';
            if (isNaN(month) || month < 1 || month > 12) month = '';
            if (isNaN(year) || year < 1900 || year > new Date().getFullYear()) year = '';
            
            return { day, month, year };
        }
    }

    // Xử lý trường hợp là đối tượng Date
    try {
        const date = new Date(dateString);
        if (!isNaN(date.getTime())) {
            day = date.getDate();
            month = date.getMonth() + 1; // JavaScript months are 0-based
            year = date.getFullYear();
            
            // Kiểm tra tính hợp lệ của các giá trị
            if (day < 1 || day > 31) day = '';
            if (month < 1 || month > 12) month = '';
            if (year < 1900 || year > new Date().getFullYear()) year = '';
            
            return { day, month, year };
        }
    } catch (e) {
        console.error("Error parsing date", e);
    }

    return { day: '', month: '', year: '' };
}

// Hàm xử lý trường date picker ngày sinh
function setupBirthDatePicker() {
    if ($('#dateOfBirth').length) {
        // Khởi tạo date picker
        $('#dateOfBirth').daterangepicker({
            singleDatePicker: true,
            showDropdowns: true,
            autoUpdateInput: true, // Tự động cập nhật để tránh lỗi
            locale: {
                format: 'DD/MM/YYYY',
                cancelLabel: 'Clear'
            },
            minYear: 1900,
            maxYear: (new Date()).getFullYear()
        });

        // Set giá trị ban đầu cho date picker nếu đã có dữ liệu
        const day = $('#id_DAYOFBIRTH').val();
        const month = $('#id_MONTHOFBIRTH').val();
        const year = $('#id_YEAROFBIRTH').val();

        if (day && month && year && 
            !isNaN(parseInt(day)) && 
            !isNaN(parseInt(month)) && 
            !isNaN(parseInt(year))) {
            // Đảm bảo các giá trị là số nguyên hợp lệ
            const dayValue = parseInt(day, 10);
            const monthValue = parseInt(month, 10);
            const yearValue = parseInt(year, 10);
            
            // Kiểm tra phạm vi hợp lệ
            if (dayValue >= 1 && dayValue <= 31 && 
                monthValue >= 1 && monthValue <= 12 && 
                yearValue >= 1900 && yearValue <= new Date().getFullYear()) {
                const paddedDay = String(dayValue).padStart(2, '0');
                const paddedMonth = String(monthValue).padStart(2, '0');
                $('#dateOfBirth').val(`${paddedDay}/${paddedMonth}/${yearValue}`);
                
                // Cập nhật lại các trường ẩn với số nguyên
                $('#id_DAYOFBIRTH').val(dayValue);
                $('#id_MONTHOFBIRTH').val(monthValue);
                $('#id_YEAROFBIRTH').val(yearValue);
            } else {
                $('#dateOfBirth').val('');
                $('#id_DAYOFBIRTH').val('');
                $('#id_MONTHOFBIRTH').val('');
                $('#id_YEAROFBIRTH').val('');
            }
        } else {
            $('#dateOfBirth').val('');
        }

        // Xử lý sự kiện khi người dùng chọn ngày
        $('#dateOfBirth').on('apply.daterangepicker', function(ev, picker) {
            // Cập nhật trường hiển thị
            $(this).val(picker.startDate.format('DD/MM/YYYY'));
            
            // Cập nhật các trường ngày/tháng/năm riêng biệt với số nguyên
            const day = parseInt(picker.startDate.format('D'), 10);
            const month = parseInt(picker.startDate.format('M'), 10);
            const year = parseInt(picker.startDate.format('YYYY'), 10);
            
            $('#id_DAYOFBIRTH').val(day);
            $('#id_MONTHOFBIRTH').val(month);
            $('#id_YEAROFBIRTH').val(year);
            
            console.log("Birth date selected from picker:", day, month, year);
        });

        // Xử lý khi người dùng xóa giá trị ngày
        $('#dateOfBirth').on('cancel.daterangepicker', function() {
            $(this).val('');
            $('#id_DAYOFBIRTH').val('');
            $('#id_MONTHOFBIRTH').val('');
            $('#id_YEAROFBIRTH').val('');
        });
    }
}

// Hàm xử lý trường USUBJID để đảm bảo luôn có giá trị
function ensureUSUBJIDExists() {
    // Kiểm tra tất cả các nguồn USUBJID có thể có
    let usubjid = '';
    
    // Kiểm tra theo thứ tự ưu tiên
    if ($('input[name="USUBJID_id"]').length) {
        usubjid = $('input[name="USUBJID_id"]').val();
        console.log("Found USUBJID_id:", usubjid);
    } else if ($('input[name="hidJUBJID"]').length) {
        usubjid = $('input[name="hidJUBJID"]').val();
        console.log("Found hidJUBJID:", usubjid);    } else if (typeof window.screeningCaseId !== 'undefined' && window.screeningCaseId) {
        usubjid = window.screeningCaseId;
        console.log("Using screeningCaseId:", usubjid);
    } else if ($('#enrollmentForm').data('screening-id')) {
        // Lấy từ thuộc tính data-screening-id của form
        usubjid = $('#enrollmentForm').data('screening-id');
        console.log("Found from form data attribute:", usubjid);
    }
    
    // Chỉ tiếp tục nếu tìm thấy USUBJID từ một nguồn nào đó
    if (usubjid) {
        // Xóa tất cả trường USUBJID hiện có để tránh trùng lặp
        $('input[name="USUBJID"]').remove();
        
        // Tạo hidden field cho USUBJID
        $('<input>').attr({
            type: 'hidden',
            id: 'id_USUBJID',
            name: 'USUBJID',
            value: usubjid
        }).appendTo('#enrollmentForm');
        
        console.log("USUBJID field added with value:", usubjid);
        return true;    } else {
        // Kiểm tra USUBJID trong HTML của trang
        const pageHtml = document.documentElement.innerHTML;
        const usubjidMatch = pageHtml.match(/USUBJID['"]*:\s*['"]([A-Z0-9-]+)['"]/i);
        
        if (usubjidMatch && usubjidMatch[1]) {
            usubjid = usubjidMatch[1];
            console.log("Extracted USUBJID from page HTML:", usubjid);
            
            // Tạo hidden field cho USUBJID
            $('<input>').attr({
                type: 'hidden',
                id: 'id_USUBJID',
                name: 'USUBJID',
                value: usubjid
            }).appendTo('#enrollmentForm');
            
            return true;
        } else {
            console.error("No USUBJID source found!");
            return false;
        }
    }
}

/**
 * Hàm xử lý đặc biệt cho các trường ngày tháng năm sinh
 * Đảm bảo các giá trị được chuyển thành số nguyên hợp lệ
 */
function processDateOfBirthFields() {
    // Nếu đã có giá trị hiển thị trong dateOfBirth, phân tích và cập nhật các trường ẩn
    if ($('#dateOfBirth').val() && $('#dateOfBirth').val() !== 'Invalid date') {
        const dateValue = $('#dateOfBirth').val();
        const parts = dateValue.split('/');
        
        if (parts.length === 3) {
            // Chuyển đổi thành số nguyên
            const day = parseInt(parts[0], 10);
            const month = parseInt(parts[1], 10);
            const year = parseInt(parts[2], 10);
            
            // Kiểm tra tính hợp lệ và đặt giá trị
            if (!isNaN(day) && day >= 1 && day <= 31) {
                $('#id_DAYOFBIRTH').val(day);
            } else {
                $('#id_DAYOFBIRTH').val('');
            }
            
            if (!isNaN(month) && month >= 1 && month <= 12) {
                $('#id_MONTHOFBIRTH').val(month);
            } else {
                $('#id_MONTHOFBIRTH').val('');
            }
            
            if (!isNaN(year) && year >= 1900 && year <= new Date().getFullYear()) {
                $('#id_YEAROFBIRTH').val(year);
            } else {
                $('#id_YEAROFBIRTH').val('');
            }
            
            console.log("Date of birth processed:", day, month, year);
        }
    }
    
    // Trong mọi trường hợp, đảm bảo các giá trị trong trường ẩn là số nguyên hợp lệ
    ['DAYOFBIRTH', 'MONTHOFBIRTH', 'YEAROFBIRTH'].forEach(function(field) {
        const inputField = $(`#id_${field}`);
        if (inputField.length) {
            const value = inputField.val();
            if (value && value.toString().trim() !== '') {
                const parsedValue = parseInt(value, 10);
                if (!isNaN(parsedValue)) {
                    // Đảm bảo giá trị nằm trong phạm vi hợp lệ
                    let isValid = true;
                    if (field === 'DAYOFBIRTH' && (parsedValue < 1 || parsedValue > 31)) {
                        isValid = false;
                    } else if (field === 'MONTHOFBIRTH' && (parsedValue < 1 || parsedValue > 12)) {
                        isValid = false;
                    } else if (field === 'YEAROFBIRTH' && (parsedValue < 1900 || parsedValue > new Date().getFullYear())) {
                        isValid = false;
                    }
                    
                    if (isValid) {
                        // Gán giá trị số nguyên hợp lệ
                        inputField.val(parsedValue);
                    } else {
                        console.warn(`Invalid ${field} value: ${parsedValue}, setting to empty`);
                        inputField.val('');
                    }
                } else {
                    console.warn(`Failed to parse ${field} value: ${value}, setting to empty`);
                    inputField.val('');
                }
            }
        }
    });
    
    return {
        day: $('#id_DAYOFBIRTH').val(),
        month: $('#id_MONTHOFBIRTH').val(),
        year: $('#id_YEAROFBIRTH').val()
    };
}

// Hàm khởi tạo toàn bộ xử lý ngày tháng
function initializeDateHandling() {
    // Thiết lập xử lý ngày sinh
    setupBirthDatePicker();
    
    // Đảm bảo USUBJID luôn tồn tại
    ensureUSUBJIDExists();
    
    // Xử lý trường hợp submit form
    $('#enrollmentForm').on('submit', function(e) {
        // Đảm bảo lại một lần nữa USUBJID luôn tồn tại
        ensureUSUBJIDExists();
        
        // Xử lý đặc biệt cho các trường ngày tháng năm sinh
        processDateOfBirthFields();
        
        // Kiểm tra lại các trường ngày sinh sau khi xử lý
        if (!$('#id_DAYOFBIRTH').val() || !$('#id_MONTHOFBIRTH').val() || !$('#id_YEAROFBIRTH').val()) {
            // Nếu dateOfBirth có giá trị, thử phân tích lần nữa
            if ($('#dateOfBirth').val() && $('#dateOfBirth').val() !== 'Invalid date') {
                console.log("Trying to parse birth date from display field:", $('#dateOfBirth').val());
                const { day, month, year } = parseBirthDateComponents($('#dateOfBirth').val());
                
                // Đảm bảo các giá trị là số nguyên hợp lệ
                if (day && month && year) {
                    $('#id_DAYOFBIRTH').val(parseInt(day, 10));
                    $('#id_MONTHOFBIRTH').val(parseInt(month, 10));
                    $('#id_YEAROFBIRTH').val(parseInt(year, 10));
                    console.log("Birth date parsed as integers:", parseInt(day, 10), parseInt(month, 10), parseInt(year, 10));
                }
            }
        }
        
        // Xử lý các trường ngày tháng khác
        $('.date input').each(function() {
            var $input = $(this);
            var dateValue = $input.val();
            
            // Xóa các giá trị "Invalid date"
            if (dateValue === 'Invalid date') {
                $input.val('');
            }
            
            // Chuyển đổi các giá trị không ở định dạng DD/MM/YYYY
            if (dateValue && dateValue.trim() !== '' && dateValue.indexOf('/') === -1) {
                try {
                    var date = new Date(dateValue);
                    if (!isNaN(date.getTime())) {
                        $input.val(
                            date.getDate().toString().padStart(2, '0') + '/' +
                            (date.getMonth() + 1).toString().padStart(2, '0') + '/' +
                            date.getFullYear()
                        );
                    }
                } catch (e) {
                    $input.val('');
                }
            }
        });
    });
}

// Khởi tạo khi DOM đã sẵn sàng
$(document).ready(function() {
    initializeDateHandling();
});