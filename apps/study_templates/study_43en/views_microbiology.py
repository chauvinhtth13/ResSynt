# Thêm vào file views_laboratory.py hoặc tạo file views_microbiology.py mới
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import models
from .models import ScreeningCase, ClinicalCase, MicrobiologyCulture, AntibioticSensitivity
from django.utils.translation import gettext as _
import json
from .views_laboratory import sample_collection_list, sample_collection_edit


@login_required
def microbiology_culture_list(request, usubjid):
    """Hiển thị danh sách các mẫu nuôi cấy vi sinh của bệnh nhân"""
    # Lấy thông tin screeningCase từ USUBJID
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    # Kiểm tra mode từ query parameter (edit or view-only)
    edit_mode = request.GET.get('mode') == 'edit'
    is_view_only = request.GET.get('mode') == 'view'
    
    # Kiểm tra xem đã có ClinicalCase chưa, nếu chưa thì tạo mới
    try:
        clinical_case = ClinicalCase.objects.get(USUBJID=screening_case)
    except ClinicalCase.DoesNotExist:
        # Tạo ClinicalCase mới
        from datetime import date
        clinical_case = ClinicalCase(
            USUBJID=screening_case,
            STUDYID='43EN',
            SITEID=screening_case.SITEID,
            SUBJID=screening_case.SUBJID,
            INITIAL=screening_case.INITIAL,
            COMPLETEDBY=screening_case.COMPLETEDBY if screening_case.COMPLETEDBY else request.user.username,
            COMPLETEDDATE=date.today()
        )
        clinical_case.save()
        messages.info(request, f'Đã tạo thông tin lâm sàng cơ bản cho bệnh nhân {usubjid}. Vui lòng cập nhật đầy đủ sau khi hoàn tất các xét nghiệm.')
    
    # Lấy tất cả các mẫu nuôi cấy của bệnh nhân, sắp xếp theo ngày thực hiện (mới nhất lên đầu)
    cultures = MicrobiologyCulture.objects.filter(clinical_case=screening_case).order_by('-performed_date', '-id')
    
    # Kiểm tra trạng thái hoàn thành của từng mẫu nuôi cấy
    for culture in cultures:
        if culture.result_type == 'POSITIVE':
            # Kiểm tra độ nhạy kháng sinh đã hoàn thành chưa
            antibiotic_sensitivities = AntibioticSensitivity.objects.filter(culture=culture)
            culture.has_sensitivities = antibiotic_sensitivities.exists()
            
            if culture.has_sensitivities:
                # Đếm số lượng kháng sinh có dữ liệu đầy đủ
                total_antibiotics = 0
                complete_antibiotics = 0
                
                for sensitivity in antibiotic_sensitivities:
                    if not sensitivity.antibiotic_name:
                        continue
                        
                    total_antibiotics += 1
                    
                    # Một kháng sinh được coi là hoàn thành khi:
                    # 1. Có ít nhất một trong hai giá trị: vòng ức chế hoặc MIC
                    # 2. Có giá trị sensitivity_level khác ND (Not Determined)
                    has_measurement = sensitivity.inhibition_zone_diameter or sensitivity.mic_value
                    has_sensitivity = sensitivity.sensitivity_level and sensitivity.sensitivity_level != 'ND'
                    
                    # Nếu có cả hai tiêu chí, kháng sinh này được xem là hoàn thành
                    if has_measurement and has_sensitivity:
                        complete_antibiotics += 1
                
                # Nếu tất cả kháng sinh đều hoàn thành và có ít nhất 1 kháng sinh
                if total_antibiotics > 0 and complete_antibiotics == total_antibiotics:
                    culture.sensitivity_status = 'complete'
                else:
                    culture.sensitivity_status = 'incomplete'
            else:
                culture.sensitivity_status = 'not_started'
        else:
            # Mẫu âm tính không cần độ nhạy kháng sinh
            culture.sensitivity_status = 'not_required'
    
    # Lấy danh sách các loại bệnh phẩm để hiển thị trong dropdown
    sample_types = dict(MicrobiologyCulture.SAMPLE_TYPES)
    
    # Kiểm tra nếu đã có mẫu nuôi cấy
    has_microbiology_cultures = cultures.exists()
    
    return render(request, 'study_43en/microbiology_culture_list.html', {
        'screening_case': screening_case,
        'clinical_case': clinical_case,
        'cultures': cultures,
        'sample_types': sample_types,
        'usubjid': usubjid,
        'edit_mode': edit_mode,
        'is_view_only': is_view_only,
        'has_microbiology_cultures': has_microbiology_cultures,
    })

@login_required
def microbiology_culture_get(request, usubjid, culture_id):
    """Lấy thông tin của một mẫu nuôi cấy cụ thể"""
    try:
        # Log request details for debugging
        print(f"GET request for culture {culture_id} from USUBJID {usubjid}")
        
        # Get the culture record
        culture = get_object_or_404(MicrobiologyCulture, id=culture_id)
        
        # Đảm bảo rằng mẫu thuộc về bệnh nhân hiện tại
        screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
        clinical_case = get_object_or_404(ClinicalCase, USUBJID=screening_case.USUBJID)

        # Lấy chuỗi USUBJID từ cả hai bên để so sánh
        culture_usubjid = str(culture.clinical_case.USUBJID)
        request_usubjid = str(usubjid)
        
        print(f"Debug - Culture USUBJID: '{culture_usubjid}', Request USUBJID: '{request_usubjid}'")
        print(f"Types - Culture USUBJID: {type(culture_usubjid)}, Request USUBJID: {type(request_usubjid)}")
        
        # Đơn giản hóa kiểm tra quyền truy cập - kiểm tra chính xác mẫu này có thuộc bệnh nhân không
        # Cách 1: So sánh đối tượng ClinicalCase
        if culture.clinical_case == clinical_case:
            print("Access granted: Culture belongs to the clinical case")
        else:
            print("Access check by object comparison failed")
            
            # Cách 2: So sánh chuỗi USUBJID
            if culture_usubjid == request_usubjid:
                print("Access granted: USUBJIDs match")
            else:
                print(f"Access denied: USUBJIDs do not match - '{culture_usubjid}' vs '{request_usubjid}'")
                return JsonResponse({'success': False, 'message': 'Không có quyền truy cập mẫu này'}, status=403)
        
        # Format date cho JavaScript
        performed_date = None
        if culture.performed_date:
            performed_date = culture.performed_date.isoformat()
        
        # Trả về thông tin mẫu dưới dạng JSON
        data = {
            'id': culture.id,
            'sample_type': culture.sample_type,
            'other_sample': culture.other_sample,
            'result_type': culture.result_type,
            'result_details': culture.result_details,
            'sample_id': culture.sample_id,
            'performed': culture.performed,
            'performed_date': performed_date,
            'sequence': culture.sequence
        }
        
        print(f"Returning culture data: {data}")
        return JsonResponse(data)
    except Exception as e:
        import traceback
        print(f"Error in microbiology_culture_get: {str(e)}")
        print(traceback.format_exc())
        print(f"Request details: USUBJID={usubjid}, culture_id={culture_id}")
        return JsonResponse({'success': False, 'message': f'Lỗi: {str(e)}'}, status=500)
    
@login_required
@require_POST
def microbiology_culture_update(request, usubjid, culture_id):
    """Cập nhật thông tin mẫu nuôi cấy"""
    try:
        # Detailed logging for debugging
        print(f"Update request for culture {culture_id} from USUBJID {usubjid}")
        print(f"POST data: {request.POST}")
        
        culture = get_object_or_404(MicrobiologyCulture, id=culture_id)
        
        # Đảm bảo rằng mẫu thuộc về bệnh nhân hiện tại
        screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
        clinical_case = get_object_or_404(ClinicalCase, USUBJID=screening_case)
        
        # Đơn giản hóa kiểm tra quyền truy cập - so sánh trực tiếp đối tượng clinical_case
        if culture.clinical_case == clinical_case:
            print("Update access granted: Culture belongs to the clinical case")
        else:
            # Nếu so sánh đối tượng thất bại, thử so sánh chuỗi USUBJID
            culture_usubjid = str(culture.clinical_case.USUBJID)
            request_usubjid = str(usubjid)
            
            if culture_usubjid == request_usubjid:
                print("Update access granted: USUBJIDs match")
            else:
                print(f"Update access denied: USUBJIDs do not match - '{culture_usubjid}' vs '{request_usubjid}'")
                return JsonResponse({
                    'success': False, 
                    'message': 'Không có quyền cập nhật mẫu này'
                }, status=403)
                
        
        try:
            # Cập nhật từ form
            result_type = request.POST.get('result_type')
            result_details = request.POST.get('result_details', '')
            performed_date = request.POST.get('performed_date') or None
            performed = request.POST.get('performed') == 'true'
            sample_id = request.POST.get('sample_id', '')
            
            print(f"Update values: result_type={result_type}, performed_date={performed_date}, performed={performed}")
              # Cập nhật thông tin
            culture.result_type = result_type
            culture.result_details = result_details
            culture.sample_id = sample_id
            culture.performed = performed
            
            # Xử lý ngày thực hiện
            if performed_date:
                from datetime import datetime
                try:
                    culture.performed_date = datetime.strptime(performed_date, '%Y-%m-%d').date()
                    culture.performed = True
                except ValueError as e:
                    print(f"Date parsing error: {str(e)}")
                    return JsonResponse({
                        'success': False, 
                        'message': f'Định dạng ngày không hợp lệ: {performed_date}'
                    }, status=400)
            else:
                culture.performed_date = None
                culture.performed = False
            
            culture.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Cập nhật thông tin mẫu nuôi cấy thành công!'
            })
        
        except Exception as e:
            print(f"Error updating culture: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                'success': False, 
                'message': f'Lỗi khi cập nhật: {str(e)}'
            }, status=500)
            
    except Exception as e:
        print(f"General error in update view: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'success': False, 
            'message': f'Lỗi hệ thống: {str(e)}'
        }, status=500)

@login_required
@require_POST
def microbiology_culture_quick_create(request, usubjid):
    """Thêm nhanh mẫu nuôi cấy mới"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    clinical_case = get_object_or_404(ClinicalCase, USUBJID=screening_case)
    try:
        # Lấy thông tin từ request
        sample_type_input = request.POST.get('sample_type')
        other_sample_input = request.POST.get('other_sample', '')
        result_type = request.POST.get('result_type', '')
        result_details = request.POST.get('result_details', '')
        performed_date = request.POST.get('performed_date') or None
        performed = request.POST.get('performed') == 'true'
        sample_id = request.POST.get('sample_id', '')
        
        # Log tất cả các tham số để debug
        print(f"Quick create params: sample_type={sample_type_input}, other_sample={other_sample_input}, " +
              f"result_type={result_type}, result_details={result_details}, " +
              f"performed={performed}, performed_date={performed_date}, sample_id={sample_id}")
        
        # Xử lý loại mẫu "OTHER"
        if sample_type_input == 'OTHER':
            # Sử dụng giá trị other_sample được gửi từ client
            sample_type = "OTHER"
            other_sample = other_sample_input if other_sample_input else None
        elif sample_type_input and sample_type_input.startswith('OTHER:'):
            # Hỗ trợ cả cách cũ (cho các client cũ)
            custom_type = sample_type_input[6:]  # Cắt phần "OTHER:" ở đầu
            sample_type = "OTHER"
            other_sample = custom_type
        else:
            sample_type = sample_type_input
            other_sample = None
        
        # Tìm sequence lớn nhất hiện tại cho sample_type này
        max_sequence = MicrobiologyCulture.objects.filter(
            clinical_case=screening_case, 
            sample_type=sample_type
        ).aggregate(models.Max('sequence'))['sequence__max'] or 0
        
        # Tăng sequence lên 1
        next_sequence = max_sequence + 1
        
        # Tạo mẫu nuôi cấy mới
        culture = MicrobiologyCulture(
            clinical_case=screening_case,
            sample_type=sample_type,
            other_sample=other_sample,
            result_type=result_type,
            result_details=result_details,
            sample_id=sample_id,
            performed=performed,
            sequence=next_sequence
        )
          # Xử lý ngày thực hiện
        if performed_date:
            from datetime import datetime
            try:
                culture.performed_date = datetime.strptime(performed_date, '%Y-%m-%d').date()
                culture.performed = True
            except ValueError:
                return JsonResponse({'success': False, 'message': 'Định dạng ngày không hợp lệ'}, status=400)
        else:
            culture.performed_date = None
            culture.performed = False
        
        culture.save()
        return JsonResponse({
            'success': True,
            'message': 'Tạo mẫu nuôi cấy thành công',
            'culture_id': culture.id,
            'sequence': culture.sequence
        })
    except Exception as e:
        print(f"Error in quick_create: {str(e)}")
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
@login_required
def antibiotic_sensitivity_list(request, usubjid, culture_id):
    """Hiển thị trang danh sách kết quả nhạy cảm kháng sinh của một mẫu nuôi cấy"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    clinical_case = get_object_or_404(ClinicalCase, USUBJID=screening_case)
    culture = get_object_or_404(MicrobiologyCulture, id=culture_id, clinical_case=screening_case)
    
    # Kiểm tra mode từ query parameter (edit or view-only)
    edit_mode = request.GET.get('mode') == 'edit'
    is_view_only = request.GET.get('mode') == 'view'
    
    # Kiểm tra xem mẫu có phải dương tính hay không
    if not culture.is_positive():
        messages.error(request, _("Chỉ có thể xem kết quả kháng sinh của mẫu nuôi cấy dương tính"))
        return redirect('microbiology_culture_list', usubjid=usubjid)
    
    # Tạo dictionary để mapping tier_code -> display_name
    tier_display_names = dict(AntibioticSensitivity.TIER_CHOICES)
      
    # Lấy tất cả kết quả kháng sinh theo tier
    antibiotics_by_tier = {}
    # Đảm bảo tất cả các tier đều được truyền vào template, kể cả khi chưa có dữ liệu
    for tier_code, tier_name in AntibioticSensitivity.TIER_CHOICES:
        # Sử dụng distinct để tránh trùng lặp, và prefetch_related để tối ưu hiệu suất
        sensitivities = AntibioticSensitivity.objects.filter(
            culture=culture,
            tier=tier_code
        ).order_by('sequence').distinct()
        
        # Debug log để kiểm tra dữ liệu
        print(f"Tier {tier_code}: Tìm thấy {sensitivities.count()} kháng sinh")
        for sensitivity in sensitivities:
            print(f"  - {sensitivity.antibiotic_name}: {sensitivity.sensitivity_level}, MIC: {sensitivity.mic_value}, Zone: {sensitivity.inhibition_zone_diameter}")
        
        # Luôn thêm tier vào dictionary, ngay cả khi không có dữ liệu
        antibiotics_by_tier[tier_code] = sensitivities
      
    # Chuẩn bị các choices cho dropdown
    antibiotic_choices = AntibioticSensitivity.ANTIBIOTIC_CHOICES
    sensitivity_choices = AntibioticSensitivity.SENSITIVITY_CHOICES

    # Kiểm tra trạng thái hoàn thành
    all_antibiotics = AntibioticSensitivity.objects.filter(culture=culture)
    total_antibiotics = 0
    complete_antibiotics = 0
    
    for sensitivity in all_antibiotics:
        if not sensitivity.antibiotic_name:
            continue
            
        total_antibiotics += 1
        
        # Một kháng sinh được coi là hoàn thành khi có ít nhất một giá trị đo lường (vòng ức chế hoặc MIC)
        # và có giá trị sensitivity_level
        has_measurement = bool(sensitivity.inhibition_zone_diameter or sensitivity.mic_value)
        has_sensitivity = bool(sensitivity.sensitivity_level and sensitivity.sensitivity_level != 'ND')
        
        if has_measurement and has_sensitivity:
            complete_antibiotics += 1
    
    is_completed = total_antibiotics > 0 and complete_antibiotics == total_antibiotics
    
    context = {
        'screening_case': screening_case,
        'clinical_case': clinical_case,
        'culture': culture,
        'tier_display_names': tier_display_names,
        'antibiotics_by_tier': antibiotics_by_tier,
        'all_tiers': AntibioticSensitivity.TIER_CHOICES,  # Truyền danh sách tất cả các tier
        'antibiotic_choices': antibiotic_choices,
        'sensitivity_choices': sensitivity_choices,
        'is_completed': is_completed,
        'total_antibiotics': total_antibiotics,
        'complete_antibiotics': complete_antibiotics,
        'completion_percentage': (complete_antibiotics / total_antibiotics * 100) if total_antibiotics > 0 else 0,
        'edit_mode': edit_mode,
        'is_view_only': is_view_only,
    }
    
    return render(request, 'study_43en/antibiotic_sensitivity_list.html', context)

@login_required
def antibiotic_sensitivity_list_api(request, usubjid, culture_id):
    """API trả về danh sách kết quả nhạy cảm kháng sinh theo định dạng JSON"""
    try:
        screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
        clinical_case = get_object_or_404(ClinicalCase, USUBJID=screening_case)
        culture = get_object_or_404(MicrobiologyCulture, id=culture_id, clinical_case=screening_case)
        
        # Ghi lại mode để debug
        mode = request.GET.get('mode')
        print(f"API mode: {mode}")
        
        # Kiểm tra xem mẫu có phải dương tính hay không
        if not culture.is_positive():
            return JsonResponse({
                'success': False,
                'message': _("Chỉ có thể xem kết quả kháng sinh của mẫu nuôi cấy dương tính")
            })
        
        # Lấy tất cả kết quả kháng sinh theo nhóm
        results = {}
        for tier_code, _ in AntibioticSensitivity.TIER_CHOICES:
            sensitivities = AntibioticSensitivity.objects.filter(
                culture=culture,
                tier=tier_code
            ).order_by('sequence')
            
            results[tier_code] = []
            for sensitivity in sensitivities:
                results[tier_code].append({
                    'id': sensitivity.id,
                    'antibiotic_name': sensitivity.antibiotic_name,
                    'antibiotic_display_name': sensitivity.get_antibiotic_display_name(),
                    'sensitivity_level': sensitivity.sensitivity_level,
                    'inhibition_zone_diameter': sensitivity.inhibition_zone_diameter or '',
                    'mic_value': sensitivity.mic_value or '',
                    'sequence': sensitivity.sequence
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
@require_POST
def antibiotic_sensitivity_update(request, usubjid, sensitivity_id):
    """API cập nhật kết quả nhạy cảm kháng sinh"""
    try:
        # Lấy kết quả kháng sinh
        screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
        clinical_case = get_object_or_404(ClinicalCase, USUBJID=screening_case)
        sensitivity = get_object_or_404(
            AntibioticSensitivity, 
            id=sensitivity_id, 
            culture__clinical_case=screening_case
        )
        
        # Lấy dữ liệu từ request
        sensitivity_level = request.POST.get('sensitivity_level', sensitivity.sensitivity_level)
        inhibition_zone = request.POST.get('inhibition_zone_diameter', sensitivity.inhibition_zone_diameter)
        mic_value = request.POST.get('mic_value', sensitivity.mic_value)
        
        # Cập nhật kết quả kháng sinh
        sensitivity.sensitivity_level = sensitivity_level
        sensitivity.inhibition_zone_diameter = inhibition_zone
        sensitivity.mic_value = mic_value
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
@require_POST
def antibiotic_sensitivity_add(request, usubjid, culture_id):
    """API thêm kết quả nhạy cảm kháng sinh mới"""
    try:
        # Lấy culture
        screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
        clinical_case = get_object_or_404(ClinicalCase, USUBJID=screening_case)
        culture = get_object_or_404(MicrobiologyCulture, id=culture_id, clinical_case=screening_case)
        
        # Kiểm tra xem mẫu có phải dương tính hay không
        if not culture.is_positive():
            return JsonResponse({
                'success': False,
                'message': _("Chỉ có thể thêm kết quả kháng sinh cho mẫu nuôi cấy dương tính")
            })
        
        # Lấy dữ liệu từ request
        tier = request.POST.get('tier')
        antibiotic_name = request.POST.get('antibiotic_name')
        other_antibiotic_name = request.POST.get('other_antibiotic_name')
        sensitivity_level = request.POST.get('sensitivity_level', 'ND')
        inhibition_zone = request.POST.get('inhibition_zone_diameter')
        mic_value = request.POST.get('mic_value')
        
        # Validate dữ liệu
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
        
        # Tìm sequence cao nhất hiện tại
        max_sequence = AntibioticSensitivity.objects.filter(
            culture=culture,
            tier=tier
        ).aggregate(models.Max('sequence'))['sequence__max'] or 0
        
        # Tạo kết quả kháng sinh mới
        sensitivity = AntibioticSensitivity(
            culture=culture,
            tier=tier,
            antibiotic_name=antibiotic_name,
            other_antibiotic_name=other_antibiotic_name if antibiotic_name == 'OTHER' else None,
            sensitivity_level=sensitivity_level,
            inhibition_zone_diameter=inhibition_zone,
            mic_value=mic_value,
            sequence=max_sequence + 1
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
@require_POST
def antibiotic_sensitivity_delete(request, usubjid, sensitivity_id):
    """API xóa kết quả nhạy cảm kháng sinh"""
    try:
        # Lấy kết quả kháng sinh
        screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
        clinical_case = get_object_or_404(ClinicalCase, USUBJID=screening_case)
        sensitivity = get_object_or_404(
            AntibioticSensitivity, 
            id=sensitivity_id, 
            culture__clinical_case=screening_case
        )
        
        # Xóa kết quả
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
def antibiotic_sensitivity_create(request, usubjid, culture_id):
    """Hiển thị form thêm mới kết quả nhạy cảm kháng sinh"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    clinical_case = get_object_or_404(ClinicalCase, USUBJID=screening_case)
    culture = get_object_or_404(MicrobiologyCulture, id=culture_id, clinical_case=screening_case)
    
    # Kiểm tra xem mẫu có phải dương tính hay không
    if not culture.is_positive():
        messages.error(request, _("Chỉ có thể thêm kết quả kháng sinh cho mẫu nuôi cấy dương tính"))
        return redirect('microbiology_culture_list', usubjid=usubjid)
    
    # Import form
    from .forms import AntibioticSensitivityForm
    
    # Khởi tạo form
    form = AntibioticSensitivityForm(initial={'culture': culture})
    
    context = {
        'screening_case': screening_case,
        'clinical_case': clinical_case,
        'culture': culture,
        'form': form,
    }
    
    return render(request, 'study_43en/antibiotic_sensitivity_form.html', context)

@login_required
@require_POST
def antibiotic_sensitivity_bulk_update(request, usubjid, culture_id):
    """API cập nhật hàng loạt kết quả nhạy cảm kháng sinh"""
    try:
        # Lấy culture
        screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
        clinical_case = get_object_or_404(ClinicalCase, USUBJID=screening_case)
        culture = get_object_or_404(MicrobiologyCulture, id=culture_id, clinical_case=screening_case)
        
        # Kiểm tra xem mẫu có phải dương tính hay không
        if not culture.is_positive():
            return JsonResponse({
                'success': False,
                'message': _("Chỉ có thể thêm kết quả kháng sinh cho mẫu nuôi cấy dương tính")
            })
        
        # Lấy dữ liệu từ request
        bulk_data_json = request.POST.get('bulk_data')
        replace_existing = request.POST.get('replace_existing') == 'true'
        tier_code = None
        
        if not bulk_data_json:
            return JsonResponse({
                'success': False,
                'message': _("Không có dữ liệu để cập nhật")
            })
        
        # Parse JSON data
        try:
            bulk_data = json.loads(bulk_data_json)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': _("Dữ liệu không hợp lệ")
            })
        
        # Lấy tier_code từ dữ liệu
        if bulk_data:
            tier_code = list(bulk_data.keys())[0]
            
        # Xóa dữ liệu cũ nếu yêu cầu
        if replace_existing and tier_code:
            # Chỉ xóa dữ liệu của tier đang cập nhật
            AntibioticSensitivity.objects.filter(culture=culture, tier=tier_code).delete()
        
        # Lưu lại danh sách ID đã xử lý để trả về
        processed_ids = []
        updated_ids = []
        created_ids = []
        
        # Thêm các kết quả mới
        updated_count = 0
        created_count = 0
        for tier, sensitivities in bulk_data.items():
            for i, data in enumerate(sensitivities):
                # Validate dữ liệu
                antibiotic_name = data.get('antibiotic_name')
                if not antibiotic_name:
                    continue
                
                other_antibiotic_name = data.get('other_antibiotic_name') if antibiotic_name == 'OTHER' else None
                sensitivity_level = data.get('sensitivity_level', 'ND')
                inhibition_zone = data.get('inhibition_zone_diameter')
                mic_value = data.get('mic_value')
                sensitivity_id = data.get('id')
                
                print(f"Xử lý kháng sinh: {antibiotic_name}, id={sensitivity_id}, sensitivity={sensitivity_level}")
                
                # Xử lý kháng sinh đã tồn tại (có ID số nguyên, không phải ID tạm thời)
                if sensitivity_id and not str(sensitivity_id).startswith('new-'):
                    try:
                        # Cập nhật kháng sinh đã có
                        sensitivity = AntibioticSensitivity.objects.get(id=sensitivity_id, culture=culture)
                        sensitivity.sensitivity_level = sensitivity_level
                        sensitivity.inhibition_zone_diameter = inhibition_zone
                        sensitivity.mic_value = mic_value
                        sensitivity.sequence = i + 1
                        sensitivity.save()
                        updated_count += 1
                        updated_ids.append(sensitivity_id)
                        processed_ids.append(sensitivity_id)
                        print(f"Đã cập nhật kháng sinh ID {sensitivity_id}")
                    except AntibioticSensitivity.DoesNotExist:
                        # Nếu không tìm thấy kháng sinh, tạo mới
                        sensitivity = AntibioticSensitivity.objects.create(
                            culture=culture,
                            tier=tier,
                            antibiotic_name=antibiotic_name,
                            other_antibiotic_name=other_antibiotic_name,
                            sensitivity_level=sensitivity_level,
                            inhibition_zone_diameter=inhibition_zone,
                            mic_value=mic_value,
                            sequence=i + 1
                        )
                        created_count += 1
                        created_ids.append(sensitivity.id)
                        processed_ids.append(sensitivity.id)
                        print(f"Đã tạo mới kháng sinh thay thế ID {sensitivity.id} (ID cũ {sensitivity_id} không tồn tại)")
                else:
                    # Kiểm tra xem kháng sinh này đã tồn tại trong tier này chưa
                    existing_sensitivity = AntibioticSensitivity.objects.filter(
                        culture=culture,
                        tier=tier,
                        antibiotic_name=antibiotic_name
                    ).first()
                    
                    if existing_sensitivity:
                        # Cập nhật kháng sinh hiện có
                        existing_sensitivity.sensitivity_level = sensitivity_level
                        existing_sensitivity.inhibition_zone_diameter = inhibition_zone
                        existing_sensitivity.mic_value = mic_value
                        existing_sensitivity.sequence = i + 1
                        existing_sensitivity.other_antibiotic_name = other_antibiotic_name
                        existing_sensitivity.save()
                        updated_count += 1
                        updated_ids.append(existing_sensitivity.id)
                        processed_ids.append(existing_sensitivity.id)
                        print(f"Đã cập nhật kháng sinh hiện có {antibiotic_name} với ID {existing_sensitivity.id}")
                    else:
                        # Tạo kháng sinh mới nếu chưa tồn tại
                        sensitivity = AntibioticSensitivity.objects.create(
                            culture=culture,
                            tier=tier,
                            antibiotic_name=antibiotic_name,
                            other_antibiotic_name=other_antibiotic_name,
                            sensitivity_level=sensitivity_level,
                            inhibition_zone_diameter=inhibition_zone,
                            mic_value=mic_value,
                            sequence=i + 1
                        )
                        created_count += 1
                        created_ids.append(sensitivity.id)
                        processed_ids.append(sensitivity.id)
                        print(f"Đã tạo mới kháng sinh {antibiotic_name} với ID {sensitivity.id}, sensitivity={sensitivity_level}")
        
        # Xóa các kháng sinh còn lại trong tier này nếu không nằm trong processed_ids
        if tier_code:
            # Chỉ xóa kháng sinh không được xử lý trong tier hiện tại
            AntibioticSensitivity.objects.filter(culture=culture, tier=tier_code).exclude(id__in=processed_ids).delete()
        
        # Lấy dữ liệu cập nhật của tier hiện tại để trả về
        updated_sensitivities = []
        if tier_code:
            sensitivities = AntibioticSensitivity.objects.filter(
                culture=culture,
                tier=tier_code
            ).order_by('sequence')
            
            for sensitivity in sensitivities:
                updated_sensitivities.append({
                    'id': sensitivity.id,
                    'antibiotic_name': sensitivity.antibiotic_name,
                    'antibiotic_display_name': sensitivity.get_antibiotic_display_name(),
                    'other_antibiotic_name': sensitivity.other_antibiotic_name,
                    'sensitivity_level': sensitivity.sensitivity_level,
                    'inhibition_zone_diameter': sensitivity.inhibition_zone_diameter or '',
                    'mic_value': sensitivity.mic_value or '',
                    'sequence': sensitivity.sequence
                })
        
        response_data = {
            'success': True,
            'message': _("Đã cập nhật {update} và thêm mới {create} kết quả kháng sinh").format(
                update=updated_count, create=created_count),
            'updated_count': updated_count,
            'created_count': created_count,
            'updated_ids': updated_ids,
            'created_ids': created_ids,
            'tier_data': updated_sensitivities  # Trả về dữ liệu cập nhật của tier
        }
        
        # Debug thông tin trả về
        print(f"Trả về response với {len(updated_sensitivities)} kháng sinh cập nhật")
        
        return JsonResponse(response_data)
        
    except Exception as e:
        import traceback
        print(f"Error in bulk_update: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
@require_POST
def microbiology_culture_delete(request, usubjid, culture_id):
    """Xóa mẫu nuôi cấy vi sinh"""
    try:
        # Lấy thông tin mẫu nuôi cấy
        screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
        clinical_case = get_object_or_404(ClinicalCase, USUBJID=screening_case)
        culture = get_object_or_404(MicrobiologyCulture, id=culture_id, clinical_case=screening_case)
        
        # Lưu thông tin trước khi xóa để thông báo
        sample_type = culture.get_sample_type_display()
        
        # Xóa mẫu nuôi cấy
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

