import json
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _

# Import models
from backends.studies.study_43en.models.patient import (
    ScreeningCase, EnrollmentCase,AntibioticSensitivity,CLI_Microbiology
)


# Import forms
from backends.studies.study_43en.forms_patient import (
    AntibioticSensitivityForm
)

# Import utils
from backends.studies.study_43en.utils.audit_log_cross_db import audit_log_decorator
from backends.studies.study_43en import models

logger = logging.getLogger(__name__)


@login_required
@audit_log_decorator(model_name='MICROBIOLOGYCULTURE')
def microbiology_culture_list(request, usubjid):
    """Hiển thị danh sách các mẫu nuôi cấy vi sinh của bệnh nhân"""
    # Lấy thông tin EnrollmentCase từ USUBJID
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)

    # Kiểm tra mode từ query parameter (edit or view-only)
    edit_mode = request.GET.get('mode') == 'edit'
    is_view_only = request.GET.get('mode') == 'view'

    # Lấy tất cả các mẫu nuôi cấy của bệnh nhân, sắp xếp theo ngày thực hiện (mới nhất lên đầu)
    cultures = CLI_Microbiology.objects.filter(USUBJID=enrollment_case).order_by('-PERFORMEDDATE', '-id')

    # Kiểm tra trạng thái hoàn thành của từng mẫu nuôi cấy
    for culture in cultures:
        if culture.RESULT == 'POSITIVE':
            # Kiểm tra độ nhạy kháng sinh đã hoàn thành chưa
            antibiotic_sensitivities = AntibioticSensitivity.objects.filter(CULTURE=culture)
            culture.has_sensitivities = antibiotic_sensitivities.exists()

            if culture.has_sensitivities:
                total_antibiotics = 0
                complete_antibiotics = 0

                for sensitivity in antibiotic_sensitivities:
                    if not sensitivity.ANTIBIOTIC_NAME:
                        continue

                    total_antibiotics += 1

                    # Một kháng sinh được coi là hoàn thành khi:
                    # 1. Có ít nhất một trong hai giá trị: IZDIAM hoặc MIC
                    # 2. Có giá trị SENSITIVITY_LEVEL khác ND
                    has_measurement = sensitivity.IZDIAM or sensitivity.MIC
                    has_sensitivity = sensitivity.SENSITIVITY_LEVEL and sensitivity.SENSITIVITY_LEVEL != 'ND'

                    if has_measurement and has_sensitivity:
                        complete_antibiotics += 1

                if total_antibiotics > 0 and complete_antibiotics == total_antibiotics:
                    culture.sensitivity_status = 'complete'
                else:
                    culture.sensitivity_status = 'incomplete'
            else:
                culture.sensitivity_status = 'not_started'
        else:
            culture.sensitivity_status = 'not_required'

    # Lấy danh sách các loại bệnh phẩm để hiển thị trong dropdown
    sample_types = dict(CLI_Microbiology.SPECIMENTYPE_CHOICES)

    # Kiểm tra nếu đã có mẫu nuôi cấy
    has_microbiology_cultures = cultures.exists()

    return render(request, 'studies/study_43en/CRF//microbiology_culture_list.html', {
        'enrollment_case': enrollment_case,
        'cultures': cultures,
        'sample_types': sample_types,
        'usubjid': screening_case.USUBJID,
        'edit_mode': edit_mode,
        'is_view_only': is_view_only,
        'has_microbiology_cultures': has_microbiology_cultures,
    })


@login_required
@audit_log_decorator(model_name='MICROBIOLOGYCULTURE')
def microbiology_culture_get(request, usubjid, culture_id):
    """Lấy thông tin của một mẫu nuôi cấy cụ thể"""
    try:
        # Lấy EnrollmentCase từ USUBJID
        screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
        enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
        
        # Lấy mẫu nuôi cấy
        culture = get_object_or_404(CLI_Microbiology, id=culture_id, USUBJID=enrollment_case)

        # Format date cho JavaScript
        performed_date = culture.PERFORMEDDATE.isoformat() if culture.PERFORMEDDATE else None
        bacstrainisoldate = culture.BACSTRAINISOLDATE.isoformat() if culture.BACSTRAINISOLDATE else None
        completeddate = culture.COMPLETEDDATE.isoformat() if culture.COMPLETEDDATE else None

        # Trả về thông tin mẫu dưới dạng JSON
        data = {
            'id': culture.id,
            'USUBJID': culture.USUBJID_id,
            'SPECIMENTYPE': culture.SPECIMENTYPE,
            'OTHERSPECIMEN': culture.OTHERSPECIMEN,
            'RESULT': culture.RESULT,
            'RESULTDETAILS': culture.RESULTDETAILS,
            'SPECIMENID': culture.SPECIMENID,
            'PERFORMEDDATE': performed_date,
            'SEQUENCE': culture.SEQUENCE,
            'ORDEREDBYDEPT': culture.ORDEREDBYDEPT,
            'DEPTDIAGSENT': culture.DEPTDIAGSENT,
            'BACSTRAINISOLDATE': bacstrainisoldate,
            'COMPLETEDBY': culture.COMPLETEDBY,
            'COMPLETEDDATE': completeddate,
        }
        return JsonResponse(data)
    except Exception as e:
        import traceback
        print(f"Error in microbiology_culture_get: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'message': f'Lỗi: {str(e)}'}, status=500)


@login_required
@audit_log_decorator(model_name='MICROBIOLOGYCULTURE')
@require_POST
def microbiology_culture_update(request, usubjid, culture_id):
    """Cập nhật thông tin mẫu nuôi cấy"""
    try:
        culture = get_object_or_404(CLI_Microbiology, id=culture_id, USUBJID=usubjid)

        # Lấy dữ liệu từ form
        specimentype = request.POST.get('SPECIMENTYPE')
        otherspecimen = request.POST.get('OTHERSPECIMEN', '')
        result = request.POST.get('RESULT')
        resultdetails = request.POST.get('RESULTDETAILS', '')
        specimenid = request.POST.get('SPECIMENID', '')
        performeddate = request.POST.get('PERFORMEDDATE') or None
        orderedbydept = request.POST.get('ORDEREDBYDEPT', '')
        deptdiagsent = request.POST.get('DEPTDIAGSENT', '')
        bacstrainisoldate = request.POST.get('BACSTRAINISOLDATE') or None
        completedby = request.POST.get('COMPLETEDBY', '')
        completeddate = request.POST.get('COMPLETEDDATE') or None

        # Kiểm tra thay đổi SPECIMENTYPE và cập nhật SEQUENCE nếu cần
        if specimentype != culture.SPECIMENTYPE:
            max_sequence = CLI_Microbiology.objects.filter(
                USUBJID=culture.USUBJID,
                SPECIMENTYPE=specimentype
            ).aggregate(models.Max('SEQUENCE'))['SEQUENCE__max'] or 0
            culture.SEQUENCE = max_sequence + 1

        # Cập nhật thông tin
        culture.SPECIMENTYPE = specimentype
        culture.OTHERSPECIMEN = otherspecimen
        culture.RESULT = result
        culture.RESULTDETAILS = resultdetails
        culture.SPECIMENID = specimenid
        culture.ORDEREDBYDEPT = orderedbydept
        culture.DEPTDIAGSENT = deptdiagsent
        culture.COMPLETEDBY = completedby

        # Xử lý ngày
        from datetime import datetime
        date_fields = [
            ('PERFORMEDDATE', performeddate),
            ('BACSTRAINISOLDATE', bacstrainisoldate),
            ('COMPLETEDDATE', completeddate),
        ]
        for field, value in date_fields:
            if value:
                try:
                    setattr(culture, field, datetime.strptime(value, '%Y-%m-%d').date())
                except ValueError:
                    setattr(culture, field, None)
            else:
                setattr(culture, field, None)

        culture.save()

        return JsonResponse({
            'success': True,
            'message': 'Cập nhật thông tin mẫu nuôi cấy thành công!'
        })
    except Exception as e:
        import traceback
        print(f"Error in microbiology_culture_update: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': f'Lỗi khi cập nhật: {str(e)}'
        }, status=500)


@login_required
@audit_log_decorator(model_name='MICROBIOLOGYCULTURE')
@require_POST
def microbiology_culture_quick_create(request, usubjid):
    """Thêm nhanh mẫu nuôi cấy mới"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    try:
        # Lấy thông tin từ request
        specimentype_input = request.POST.get('SPECIMENTYPE')
        otherspecimen_input = request.POST.get('OTHERSPECIMEN', '')
        result = request.POST.get('RESULT', '')
        resultdetails = request.POST.get('RESULTDETAILS', '')
        performeddate = request.POST.get('PERFORMEDDATE') or None
        specimenid = request.POST.get('SPECIMENID', '')

        # Xử lý loại mẫu "OTHER"
        if specimentype_input == 'OTHER':
            specimentype = "OTHER"
            otherspecimen = otherspecimen_input if otherspecimen_input else None
        elif specimentype_input and specimentype_input.startswith('OTHER:'):
            custom_type = specimentype_input[6:]
            specimentype = "OTHER"
            otherspecimen = custom_type
        else:
            specimentype = specimentype_input
            otherspecimen = None

        # Tìm sequence lớn nhất hiện tại cho loại bệnh phẩm này
        max_sequence = CLI_Microbiology.objects.filter(
            USUBJID=enrollment_case,
            SPECIMENTYPE=specimentype
        ).aggregate(models.Max('SEQUENCE'))['SEQUENCE__max'] or 0

        next_sequence = max_sequence + 1

        # Tạo mẫu nuôi cấy mới
        culture = CLI_Microbiology(
            USUBJID=enrollment_case,
            SPECIMENTYPE=specimentype,
            OTHERSPECIMEN=otherspecimen,
            RESULT=result,
            RESULTDETAILS=resultdetails,
            SPECIMENID=specimenid,
            SEQUENCE=next_sequence
        )

        # Xử lý ngày thực hiện
        if performeddate:
            from datetime import datetime
            try:
                culture.PERFORMEDDATE = datetime.strptime(performeddate, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'success': False, 'message': 'Định dạng ngày không hợp lệ'}, status=400)
        else:
            culture.PERFORMEDDATE = None

        culture.save()
        return JsonResponse({
            'success': True,
            'message': 'Tạo mẫu nuôi cấy thành công',
            'culture_id': culture.id,
            'sequence': culture.SEQUENCE
        })
    except Exception as e:
        print(f"Error in quick_create: {str(e)}")
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@audit_log_decorator(model_name='MICROBIOLOGYCULTURE')
@require_POST
def microbiology_culture_delete(request, usubjid, culture_id):
    """Xóa mẫu nuôi cấy vi sinh"""
    try:
        screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
        enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
        culture = get_object_or_404(CLI_Microbiology, id=culture_id, USUBJID=enrollment_case)
        sample_type = culture.get_SPECIMENTYPE_display()
        culture.delete()
        return JsonResponse({
            'success': True,
            'message': f'Đã xóa thành công mẫu nuôi cấy {sample_type}.'
        })
    except Exception as e:
        import traceback
        print(f"Error in microbiology_culture_delete: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False, 
            'message': f'Lỗi khi xóa mẫu nuôi cấy: {str(e)}'
        }, status=500)