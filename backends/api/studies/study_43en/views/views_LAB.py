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
def antibiotic_sensitivity_list(request, usubjid, culture_id):
    """Hiển thị trang danh sách kết quả nhạy cảm kháng sinh của một mẫu nuôi cấy"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    culture = get_object_or_404(CLI_Microbiology, id=culture_id, USUBJID=enrollment_case)

    edit_mode = request.GET.get('mode') == 'edit'
    is_view_only = request.GET.get('mode') == 'view'

    if not culture.is_positive():
        messages.error(request, _("Chỉ có thể xem kết quả kháng sinh của mẫu nuôi cấy dương tính"))
        return redirect('microbiology_culture_list', usubjid=usubjid)

    tier_display_names = dict(AntibioticSensitivity.TIER_CHOICES)
    antibiotics_by_tier = {}
    for tier_code, tier_name in AntibioticSensitivity.TIER_CHOICES:
        sensitivities = AntibioticSensitivity.objects.filter(
            CULTURE=culture,
            TIER=tier_code
        ).order_by('SEQUENCE')
        antibiotics_by_tier[tier_code] = sensitivities

    antibiotic_choices = AntibioticSensitivity.ANTIBIOTIC_CHOICES
    sensitivity_choices = AntibioticSensitivity.SENSITIVITY_CHOICES

    all_antibiotics = AntibioticSensitivity.objects.filter(CULTURE=culture)
    total_antibiotics = 0
    complete_antibiotics = 0

    for sensitivity in all_antibiotics:
        if not sensitivity.ANTIBIOTIC_NAME:
            continue
        total_antibiotics += 1
        has_measurement = bool(sensitivity.IZDIAM or sensitivity.MIC)
        has_sensitivity = bool(sensitivity.SENSITIVITY_LEVEL and sensitivity.SENSITIVITY_LEVEL != 'ND')
        if has_measurement and has_sensitivity:
            complete_antibiotics += 1

    is_completed = total_antibiotics > 0 and complete_antibiotics == total_antibiotics

    context = {
        'usubjid': screening_case.USUBJID,
        'enrollment_case': enrollment_case,
        'culture': culture,
        'tier_display_names': tier_display_names,
        'antibiotics_by_tier': antibiotics_by_tier,
        'all_tiers': AntibioticSensitivity.TIER_CHOICES,
        'antibiotic_choices': antibiotic_choices,
        'sensitivity_choices': sensitivity_choices,
        'is_completed': is_completed,
        'total_antibiotics': total_antibiotics,
        'complete_antibiotics': complete_antibiotics,
        'completion_percentage': (complete_antibiotics / total_antibiotics * 100) if total_antibiotics > 0 else 0,
        'edit_mode': edit_mode,
        'is_view_only': is_view_only,
    }
    return render(request, 'studies/study_43en/CRF//antibiotic_sensitivity_list.html', context)

@login_required
@audit_log_decorator(model_name='ANTIBIOTICSENSITIVITY')
def antibiotic_sensitivity_list_api(request, usubjid, culture_id):
    """API trả về danh sách kết quả nhạy cảm kháng sinh theo định dạng JSON"""
    try:
        screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
        enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
        culture = get_object_or_404(CLI_Microbiology, id=culture_id, USUBJID=enrollment_case)

        if not culture.is_positive():
            return JsonResponse({
                'success': False,
                'message': _("Chỉ có thể xem kết quả kháng sinh của mẫu nuôi cấy dương tính")
            })

        results = {}
        for tier_code, _ in AntibioticSensitivity.TIER_CHOICES:
            sensitivities = AntibioticSensitivity.objects.filter(
                CULTURE=culture,
                TIER=tier_code
            ).order_by('SEQUENCE')
            results[tier_code] = []
            for sensitivity in sensitivities:
                results[tier_code].append({
                    'id': sensitivity.id,
                    'ANTIBIOTIC_NAME': sensitivity.ANTIBIOTIC_NAME,
                    'ANTIBIOTIC_DISPLAY_NAME': sensitivity.get_antibiotic_display_name(),
                    'OTHER_ANTIBIOTIC_NAME': sensitivity.OTHER_ANTIBIOTIC_NAME,
                    'SENSITIVITY_LEVEL': sensitivity.SENSITIVITY_LEVEL,
                    'IZDIAM': sensitivity.IZDIAM or '',
                    'MIC': sensitivity.MIC or '',
                    'SEQUENCE': sensitivity.SEQUENCE
                })

        return JsonResponse({
            'success': True,
            'results': results
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
@audit_log_decorator(model_name='ANTIBIOTICSENSITIVITY')
@require_POST
def antibiotic_sensitivity_update(request, usubjid, sensitivity_id):
    """API cập nhật kết quả nhạy cảm kháng sinh"""
    try:
        screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
        enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
        sensitivity = get_object_or_404(
            AntibioticSensitivity,
            id=sensitivity_id,
            CULTURE__USUBJID=enrollment_case
        )

        sensitivity.SENSITIVITY_LEVEL = request.POST.get('SENSITIVITY_LEVEL', sensitivity.SENSITIVITY_LEVEL)
        sensitivity.IZDIAM = request.POST.get('IZDIAM', sensitivity.IZDIAM)
        sensitivity.MIC = request.POST.get('MIC', sensitivity.MIC)
        sensitivity.save()

        return JsonResponse({
            'success': True,
            'message': _("Đã cập nhật kết quả kháng sinh thành công")
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
@audit_log_decorator(model_name='ANTIBIOTICSENSITIVITY')
@require_POST
def antibiotic_sensitivity_add(request, usubjid, culture_id):
    """API thêm kết quả nhạy cảm kháng sinh mới"""
    try:
        screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
        enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
        culture = get_object_or_404(CLI_Microbiology, id=culture_id, USUBJID=enrollment_case)

        if not culture.is_positive():
            return JsonResponse({
                'success': False,
                'message': _("Chỉ có thể thêm kết quả kháng sinh cho mẫu nuôi cấy dương tính")
            })

        tier = request.POST.get('TIER')
        antibiotic_name = request.POST.get('ANTIBIOTIC_NAME')
        other_antibiotic_name = request.POST.get('OTHER_ANTIBIOTIC_NAME')
        sensitivity_level = request.POST.get('SENSITIVITY_LEVEL', 'ND')
        izdiam = request.POST.get('IZDIAM')
        mic = request.POST.get('MIC')

        if not tier or not antibiotic_name:
            return JsonResponse({
                'success': False,
                'message': _("Vui lòng điền đầy đủ thông tin bắt buộc")
            })

        if antibiotic_name == 'OTHER' and not other_antibiotic_name:
            return JsonResponse({
                'success': False,
                'message': _("Vui lòng nhập tên kháng sinh khác")
            })

        max_sequence = AntibioticSensitivity.objects.filter(
            CULTURE=culture,
            TIER=tier
        ).aggregate(models.Max('SEQUENCE'))['SEQUENCE__max'] or 0

        sensitivity = AntibioticSensitivity(
            CULTURE=culture,
            TIER=tier,
            ANTIBIOTIC_NAME=antibiotic_name,
            OTHER_ANTIBIOTIC_NAME=other_antibiotic_name if antibiotic_name == 'OTHER' else None,
            SENSITIVITY_LEVEL=sensitivity_level,
            IZDIAM=izdiam,
            MIC=mic,
            SEQUENCE=max_sequence + 1
        )
        sensitivity.save()

        return JsonResponse({
            'success': True,
            'message': _("Đã thêm kết quả kháng sinh mới thành công"),
            'sensitivity_id': sensitivity.id
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
@audit_log_decorator(model_name='ANTIBIOTICSENSITIVITY')
@require_POST
def antibiotic_sensitivity_delete(request, usubjid, sensitivity_id):
    """API xóa kết quả nhạy cảm kháng sinh"""
    try:
        screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
        enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
        sensitivity = get_object_or_404(
            AntibioticSensitivity,
            id=sensitivity_id,
            CULTURE__USUBJID=enrollment_case
        )
        sensitivity.delete()
        return JsonResponse({
            'success': True,
            'message': _("Đã xóa kết quả kháng sinh thành công")
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
@audit_log_decorator(model_name='ANTIBIOTICSENSITIVITY')
def antibiotic_sensitivity_create(request, usubjid, culture_id):
    """Hiển thị form thêm mới kết quả nhạy cảm kháng sinh"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
    culture = get_object_or_404(CLI_Microbiology, id=culture_id, USUBJID=enrollment_case)

    if not culture.is_positive():
        messages.error(request, _("Chỉ có thể thêm kết quả kháng sinh cho mẫu nuôi cấy dương tính"))
        return redirect('microbiology_culture_list', usubjid=usubjid)

    form = AntibioticSensitivityForm(initial={'CULTURE': culture})

    context = {
        'enrollment_case': enrollment_case,
        'culture': culture,
        'form': form,
    }

    return render(request, 'studies/study_43en/CRF//antibiotic_sensitivity_form.html', context)

@login_required
@audit_log_decorator(model_name='ANTIBIOTICSENSITIVITY')
@require_POST
def antibiotic_sensitivity_bulk_update(request, usubjid, culture_id):
    """API cập nhật hàng loạt kết quả nhạy cảm kháng sinh"""
    try:
        screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
        enrollment_case = get_object_or_404(EnrollmentCase, USUBJID=screening_case)
        culture = get_object_or_404(CLI_Microbiology, id=culture_id, USUBJID=enrollment_case)

        if not culture.is_positive():
            return JsonResponse({
                'success': False,
                'message': _("Chỉ có thể thêm kết quả kháng sinh cho mẫu nuôi cấy dương tính")
            })

        bulk_data_json = request.POST.get('bulk_data')
        replace_existing = request.POST.get('replace_existing') == 'true'
        tier_code = None

        if not bulk_data_json:
            return JsonResponse({
                'success': False,
                'message': _("Không có dữ liệu để cập nhật")
            })

        try:
            bulk_data = json.loads(bulk_data_json)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': _("Dữ liệu không hợp lệ")
            })

        if bulk_data:
            tier_code = list(bulk_data.keys())[0]

        if replace_existing and tier_code:
            AntibioticSensitivity.objects.filter(CULTURE=culture, TIER=tier_code).delete()

        processed_ids = []
        updated_ids = []
        created_ids = []
        updated_count = 0
        created_count = 0

        for tier, sensitivities in bulk_data.items():
            for i, data in enumerate(sensitivities):
                antibiotic_name = data.get('ANTIBIOTIC_NAME')
                if not antibiotic_name:
                    continue

                other_antibiotic_name = data.get('OTHER_ANTIBIOTIC_NAME') if antibiotic_name == 'OTHER' else None
                sensitivity_level = data.get('SENSITIVITY_LEVEL', 'ND')
                izdiam = data.get('IZDIAM')
                mic = data.get('MIC')
                sensitivity_id = data.get('id')

                if sensitivity_id and not str(sensitivity_id).startswith('new-'):
                    try:
                        sensitivity = AntibioticSensitivity.objects.get(id=sensitivity_id, CULTURE=culture)
                        sensitivity.SENSITIVITY_LEVEL = sensitivity_level
                        sensitivity.IZDIAM = izdiam
                        sensitivity.MIC = mic
                        sensitivity.SEQUENCE = i + 1
                        sensitivity.save()
                        updated_count += 1
                        updated_ids.append(sensitivity_id)
                        processed_ids.append(sensitivity_id)
                    except AntibioticSensitivity.DoesNotExist:
                        sensitivity = AntibioticSensitivity.objects.create(
                            CULTURE=culture,
                            TIER=tier,
                            ANTIBIOTIC_NAME=antibiotic_name,
                            OTHER_ANTIBIOTIC_NAME=other_antibiotic_name,
                            SENSITIVITY_LEVEL=sensitivity_level,
                            IZDIAM=izdiam,
                            MIC=mic,
                            SEQUENCE=i + 1
                        )
                        created_count += 1
                        created_ids.append(sensitivity.id)
                        processed_ids.append(sensitivity.id)
                else:
                    existing_sensitivity = AntibioticSensitivity.objects.filter(
                        CULTURE=culture,
                        TIER=tier,
                        ANTIBIOTIC_NAME=antibiotic_name
                    ).first()

                    if existing_sensitivity:
                        existing_sensitivity.SENSITIVITY_LEVEL = sensitivity_level
                        existing_sensitivity.IZDIAM = izdiam
                        existing_sensitivity.MIC = mic
                        existing_sensitivity.SEQUENCE = i + 1
                        existing_sensitivity.OTHER_ANTIBIOTIC_NAME = other_antibiotic_name
                        existing_sensitivity.save()
                        updated_count += 1
                        updated_ids.append(existing_sensitivity.id)
                        processed_ids.append(existing_sensitivity.id)
                    else:
                        sensitivity = AntibioticSensitivity.objects.create(
                            CULTURE=culture,
                            TIER=tier,
                            ANTIBIOTIC_NAME=antibiotic_name,
                            OTHER_ANTIBIOTIC_NAME=other_antibiotic_name,
                            SENSITIVITY_LEVEL=sensitivity_level,
                            IZDIAM=izdiam,
                            MIC=mic,
                            SEQUENCE=i + 1
                        )
                        created_count += 1
                        created_ids.append(sensitivity.id)
                        processed_ids.append(sensitivity.id)

        if tier_code:
            AntibioticSensitivity.objects.filter(CULTURE=culture, TIER=tier_code).exclude(id__in=processed_ids).delete()

        updated_sensitivities = []
        if tier_code:
            sensitivities = AntibioticSensitivity.objects.filter(
                CULTURE=culture,
                TIER=tier_code
            ).order_by('SEQUENCE')

            for sensitivity in sensitivities:
                updated_sensitivities.append({
                    'id': sensitivity.id,
                    'ANTIBIOTIC_NAME': sensitivity.ANTIBIOTIC_NAME,
                    'ANTIBIOTIC_DISPLAY_NAME': sensitivity.get_antibiotic_display_name(),
                    'OTHER_ANTIBIOTIC_NAME': sensitivity.OTHER_ANTIBIOTIC_NAME,
                    'SENSITIVITY_LEVEL': sensitivity.SENSITIVITY_LEVEL,
                    'IZDIAM': sensitivity.IZDIAM or '',
                    'MIC': sensitivity.MIC or '',
                    'SEQUENCE': sensitivity.SEQUENCE
                })

        response_data = {
            'success': True,
            'message': _("Đã cập nhật {update} và thêm mới {create} kết quả kháng sinh").format(
                update=updated_count, create=created_count),
            'updated_count': updated_count,
            'created_count': created_count,
            'updated_ids': updated_ids,
            'created_ids': created_ids,
            'tier_data': updated_sensitivities
        }

        return JsonResponse(response_data)

    except Exception as e:
        import traceback
        print(f"Error in bulk_update: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

# @login_required
# @require_POST
# def microbiology_culture_delete(request, usubjid, culture_id):
#     """Xóa mẫu nuôi cấy vi sinh"""
#     try:
#         # Lấy thông tin mẫu nuôi cấy
#         screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
#         clinical_case = get_object_or_404(ClinicalCase, USUBJID=screening_case)
#         culture = get_object_or_404(MicrobiologyCulture, id=culture_id, clinical_case=screening_case)
        
#         # Lưu thông tin trước khi xóa để thông báo
#         sample_type = culture.get_sample_type_display()
        
#         # Xóa mẫu nuôi cấy
#         culture.delete()
        
#         return JsonResponse({
#             'success': True,
#             'message': f'Đã xóa thành công mẫu nuôi cấy {sample_type}.'
#         })
#     except Exception as e:
#         import traceback
#         print(f"Error in microbiology_culture_delete: {str(e)}")
#         print(traceback.format_exc())
#         return JsonResponse({
#             'success': False, 
#             'message': f'Lỗi khi xóa mẫu nuôi cấy: {str(e)}'
#         }, status=500)

