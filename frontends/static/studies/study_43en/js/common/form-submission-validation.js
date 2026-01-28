/**
 * form-submission-validation.js
 * Validate form before submission, focusing on date of birth validation
 */

$(document).ready(function() {
    console.log('Form submission validation initialized');

    // Validate form before submission
    $('#enrollmentForm').on('submit', function(e) {
        console.log('Form submission validation triggered');

        // Đảm bảo dữ liệu date của datepicker được chuyển vào các trường ẩn
        const dateOfBirthVal = $('#dateOfBirth').val();
        if (dateOfBirthVal) {
            const parts = dateOfBirthVal.split('/');
            if (parts.length === 3) {
                $('#id_DAYOFBIRTH').val(parseInt(parts[0]));
                $('#id_MONTHOFBIRTH').val(parseInt(parts[1]));
                $('#id_YEAROFBIRTH').val(parseInt(parts[2]));
                console.log(`Form submit: Updated birth date fields - Day: ${parts[0]}, Month: ${parts[1]}, Year: ${parts[2]}`);
            }
        } else if ($('#direct_day').val() && $('#direct_month').val() && $('#direct_year').val()) {
            // Nếu nhập trực tiếp, cập nhật trường ẩn
            $('#id_DAYOFBIRTH').val($('#direct_day').val());
            $('#id_MONTHOFBIRTH').val($('#direct_month').val());
            $('#id_YEAROFBIRTH').val($('#direct_year').val());
            console.log(`Form submit: Used direct inputs - Day: ${$('#direct_day').val()}, Month: ${$('#direct_month').val()}, Year: ${$('#direct_year').val()}`);
        }
        
        // Validate ngày sinh hoặc tuổi
        const day = $('#id_DAYOFBIRTH').val();
        const month = $('#id_MONTHOFBIRTH').val();
        const year = $('#id_YEAROFBIRTH').val();
        const age = $('#id_AGEIFDOBUNKNOWN').val();
        
        // Debug log
        console.log(`Validation - Day: ${day}, Month: ${month}, Year: ${year}, Age: ${age}`);
        
        if (!age && (!day || !month || !year)) {
            // Nếu không nhập tuổi và không đủ thông tin ngày sinh
            const missingFields = [];
            if (!day) missingFields.push('ngày');
            if (!month) missingFields.push('tháng'); 
            if (!year) missingFields.push('năm');
            
            if (missingFields.length > 0) {
                e.preventDefault();
                $('.date-error').text(`Vui lòng nhập đủ thông tin ngày sinh (thiếu: ${missingFields.join(', ')}) hoặc nhập tuổi`).show();
                $('html, body').animate({
                    scrollTop: $('.date-error').offset().top - 100
                }, 500);
                return false;
            }
        } else if (day && month && year) {
            // Validate ngày sinh nếu có đầy đủ thông tin
            try {
                const birthDate = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
                const today = new Date();
                
                // Kiểm tra ngày hợp lệ
                if (birthDate.getFullYear() !== parseInt(year) || 
                    birthDate.getMonth() !== parseInt(month) - 1 || 
                    birthDate.getDate() !== parseInt(day)) {
                    e.preventDefault();
                    $('.date-error').text('Ngày sinh không hợp lệ').show();
                    $('html, body').animate({
                        scrollTop: $('.date-error').offset().top - 100
                    }, 500);
                    return false;
                }
                
                // Kiểm tra ngày trong tương lai
                if (birthDate > today) {
                    e.preventDefault();
                    $('.date-error').text('Ngày sinh không thể trong tương lai').show();
                    $('html, body').animate({
                        scrollTop: $('.date-error').offset().top - 100
                    }, 500);
                    return false;
                }
                
                // Kiểm tra tuổi tối thiểu (16 tuổi theo điều kiện của nghiên cứu)
                let age = today.getFullYear() - birthDate.getFullYear();
                const m = today.getMonth() - birthDate.getMonth();
                if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
                    age--;
                }
                
                if (age < 16) {
                    e.preventDefault();
                    $('.date-error').text('Bệnh nhân cần từ 16 tuổi trở lên để đủ điều kiện tham gia nghiên cứu').show();
                    $('html, body').animate({
                        scrollTop: $('.date-error').offset().top - 100
                    }, 500);
                    return false;
                }
            } catch (error) {
                console.error("Lỗi kiểm tra ngày sinh:", error);
                e.preventDefault();
                $('.date-error').text(`Lỗi kiểm tra ngày sinh: ${error.message}`).show();
                $('html, body').animate({
                    scrollTop: $('.date-error').offset().top - 100
                }, 500);
                return false;
            }
        }
        
        // All validations passed
        console.log('Form validation passed');
        return true;
    });
});
