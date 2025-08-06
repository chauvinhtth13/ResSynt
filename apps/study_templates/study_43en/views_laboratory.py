from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt  # Trong trường hợp cần bypass CSRF
from django.db import models
from datetime import date
from .models import ScreeningCase, ClinicalCase, LaboratoryTest, SampleCollection
from .forms import LaboratoryTestForm, LaboratoryTestFormSet, LaboratoryTestBulkCreateForm, SampleCollectionForm                    


from django import template

@login_required
def laboratory_test_create(request, usubjid):
    """Tạo mới các xét nghiệm cho bệnh nhân"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    if request.method == 'POST':
        form = LaboratoryTestBulkCreateForm(request.POST)
        if form.is_valid():
            # Lấy danh sách các xét nghiệm cần tạo
            tests_to_create = form.get_tests_to_create()
            created_count = 0
            
            for test_type in tests_to_create:                # Kiểm tra xem đã có xét nghiệm này chưa
                if not LaboratoryTest.objects.filter(clinical_case=screening_case, test_type=test_type).exists():
                    # Tạo một instance tạm thời để sử dụng _get_category_from_test_type
                    temp_lab_test = LaboratoryTest(test_type=test_type)
                    category = temp_lab_test._get_category_from_test_type()
                    
                    # Tạo xét nghiệm mới
                    LaboratoryTest.objects.create(
                        clinical_case=screening_case,
                        test_type=test_type,
                        category=category,
                        performed=False
                    )
                    created_count += 1
            messages.success(request, f'Đã tạo {created_count} xét nghiệm cho bệnh nhân {usubjid} thành công.')
            return redirect('laboratory_test_list', usubjid=usubjid)
    else:
        form = LaboratoryTestBulkCreateForm()
    
    return render(request, 'study_43en/laboratory_test_create.html', {
        'form': form,
        'screening_case': screening_case,
    })

@login_required
def laboratory_test_list(request, usubjid):
    """Hiển thị danh sách các xét nghiệm của bệnh nhân"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    edit_mode = request.GET.get('mode') == 'edit'
    
    # Không cần ClinicalCase, LaboratoryTest FK là ScreeningCase
    # (Nếu cần tạo ClinicalCase mặc định cho logic khác, giữ lại đoạn này, nhưng filter LaboratoryTest phải dùng screening_case)

    # Mảng chứa tất cả các loại xét nghiệm cần tự động tạo
    default_test_types = [

        # 11. Đông máu
        'INR', 'DIC',

        # 12. Tổng phân tích tế bào máu
        'WBC', 'NEU', 'LYM', 'EOS', 'RBC', 'HEMOGLOBIN', 'PLATELETS',

        # 13. Sinh hóa, miễn dịch
        'NATRI', 'KALI', 'CLO', 'MAGNE', 'URE', 'CREATININE', 'AST', 'ALT', 
        'GLUCOSEBLOOD', 'BEDSIDE_GLUCOSE', 'BILIRUBIN_TP', 'BILIRUBIN_TT', 
        'PROTEIN', 'ALBUMIN', 'CRP_QUALITATIVE', 'CRP_QUANTITATIVE', 'CRP', 
        'PROCALCITONIN', 'HBA1C', 'CORTISOL', 'HIV', 'CD4',
        
        # 14-19. Các loại xét nghiệm khác
        'PH', 'PCO2', 'PO2', 'HCO3', 'BE', 'AADO2', 'LACTATE_ARTERIAL',
        'URINE_PH', 'NITRIT', 'URINE_PROTEIN', 'LEU', 'URINE_RBC', 'SEDIMENT','PERITONEAL_WBC', 'PERITONEAL_NEU', 'PERITONEAL_MONO', 'PERITONEAL_RBC',
        'PERITONEAL_PROTEIN', 'PERITONEAL_PROTEIN_BLOOD', 'PERITONEAL_ALBUMIN',
        'PERITONEAL_ALBUMIN_BLOOD', 'PERITONEAL_ADA', 'PERITONEAL_CELLBLOCK','PLEURAL_WBC', 'PLEURAL_NEU', 'PLEURAL_MONO', 'PLEURAL_EOS', 'PLEURAL_RBC',
                'PLEURAL_PROTEIN', 'PLEURAL_LDH', 'PLEURAL_LDH_BLOOD', 'PLEURAL_ADA', 'PLEURAL_CELLBLOCK','CSF_WBC', 'CSF_NEU', 'CSF_MONO', 'CSF_EOS', 'CSF_RBC',
                'CSF_PROTEIN', 'CSF_GLUCOSE', 'CSF_LACTATE', 'CSF_GRAM_STAIN',
        
        # 20-25. Chẩn đoán hình ảnh
        'CHEST_XRAY', 'ABDOMINAL_ULTRASOUND', 'BRAIN_CT_MRI', 
        'CHEST_ABDOMEN_CT', 'ECHOCARDIOGRAPHY', 'SOFT_TISSUE_ULTRASOUND',
    ]
    
    # Kiểm tra nếu đang ở chế độ tạo mới hoặc chưa có xét nghiệm nào
    existing_tests = LaboratoryTest.objects.filter(clinical_case=screening_case)
    is_new_creation = not existing_tests.exists()
    
    # Nếu là lần đầu tạo (chưa có xét nghiệm nào), tự động tạo các xét nghiệm mặc định
    if is_new_creation:
        # Tự động tạo các xét nghiệm mặc định 
        created_tests = 0
        for test_type in default_test_types:
            # Kiểm tra xét nghiệm đã tồn tại chưa
            if not LaboratoryTest.objects.filter(
                clinical_case=screening_case, 
                test_type=test_type,
                sequence=1
            ).exists():
                # Tạo một instance tạm thời để sử dụng _get_category_from_test_type
                temp_lab_test = LaboratoryTest(test_type=test_type)
                category = temp_lab_test._get_category_from_test_type()
                
                # Tạo xét nghiệm mới với sequence=1
                LaboratoryTest.objects.create(
                    clinical_case=screening_case,
                    test_type=test_type,
                    category=category,
                    performed=False,
                    sequence=1
                )
                created_tests += 1
        
        if created_tests > 0:
            messages.success(request, f'Đã tạo {created_tests} xét nghiệm mặc định cho bệnh nhân {usubjid}.')
    
    # Lấy tất cả các xét nghiệm của bệnh nhân (sau khi đã tạo tự động nếu cần)
    lab_tests = LaboratoryTest.objects.filter(clinical_case=screening_case)
    
    # Tạo dictionary để mapping từ test_type sang thứ tự trong default_test_types
    test_order_map = {test_type: index for index, test_type in enumerate(default_test_types)}
    
    # Sắp xếp lab_tests theo thứ tự trong default_test_types
    # Sử dụng sorted thay vì order_by vì cần sắp xếp theo custom order
    lab_tests = sorted(lab_tests, key=lambda test: (
        test_order_map.get(test.test_type, 999),  # Nếu test_type không có trong map thì để cuối
        test.category,  # Sau đó sắp xếp theo category
        test.sequence  # Cuối cùng sắp xếp theo sequence
    ))
    
    # Nhóm xét nghiệm theo category để hiển thị dạng dropdown
    lab_tests_by_category = {}
    for test in lab_tests:
        category = test.get_category_display()
        if category not in lab_tests_by_category:
            lab_tests_by_category[category] = []
        lab_tests_by_category[category].append(test)
    
    # Lấy danh sách các loại xét nghiệm cho form thêm nhanh
    test_type_choices = LaboratoryTest.TEST_TYPE_CHOICES
    
    # Quyết định nên sử dụng template gốc hay template được tối ưu
    template_name = 'study_43en/laboratory_test_list.html'
    
    # Check if all essential laboratory tests are completed to guide workflow
    all_tests = LaboratoryTest.objects.filter(clinical_case=screening_case)
    total_tests = all_tests.count()
    completed_tests = all_tests.filter(performed=True).count()
    
    # Calculate completion percentage
    completion_percentage = (completed_tests / total_tests * 100) if total_tests > 0 else 0
    show_next_step = completion_percentage >= 50  # Show option to proceed if at least 50% tests are completed
    
    return render(request, template_name, {
        'lab_tests_by_category': lab_tests_by_category,
        'screening_case': screening_case,
        'today': date.today(),
        'test_type_choices': test_type_choices,
        'usubjid': usubjid,  # Thêm usubjid để sử dụng trong JavaScript
        'completion_percentage': completion_percentage,
        'show_next_step': show_next_step,
        'edit_mode': edit_mode,  # Thêm biến này để biết là đang ở chế độ xem hay sửa
        'has_laboratory_tests': total_tests > 0,  # Thêm biến để biết đã có xét nghiệm chưa
    })

@login_required
def laboratory_test_edit(request, usubjid, test_id):
    """Cập nhật thông tin của một xét nghiệm cụ thể"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    lab_test = get_object_or_404(LaboratoryTest, id=test_id, clinical_case=screening_case)
    
    if request.method == 'POST':
        form = LaboratoryTestForm(request.POST, instance=lab_test)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật xét nghiệm {lab_test.get_test_type_display()} thành công.')
            return redirect('laboratory_test_list', usubjid=usubjid)
    else:
        form = LaboratoryTestForm(instance=lab_test)
    
    return render(request, 'study_43en/laboratory_test_edit.html', {
        'form': form,
        'lab_test': lab_test,
        'screening_case': screening_case,
    })

@login_required
def laboratory_test_bulk_update(request, usubjid, category):
    """Cập nhật hàng loạt các xét nghiệm cùng category"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    # Lấy tất cả các xét nghiệm thuộc category
    lab_tests = LaboratoryTest.objects.filter(
        clinical_case=screening_case,
        category=category
    ).order_by('test_type')
    
    if request.method == 'POST':
        formset = LaboratoryTestFormSet(request.POST, queryset=lab_tests)
        if formset.is_valid():
            formset.save()
            messages.success(request, f'Đã cập nhật {len(lab_tests)} xét nghiệm thành công.')
            return redirect('laboratory_test_list', usubjid=usubjid)
    else:
        formset = LaboratoryTestFormSet(queryset=lab_tests)
    
    return render(request, 'study_43en/laboratory_test_bulk_update.html', {
        'formset': formset,
        'category': dict(LaboratoryTest.CATEGORY_CHOICES)[category],
        'category_code': category,
        'screening_case': screening_case,
    })

@login_required
def laboratory_test_delete(request, usubjid, test_id):
    """Xóa một xét nghiệm cụ thể"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    lab_test = get_object_or_404(LaboratoryTest, id=test_id, clinical_case=screening_case)
    
    if request.method == 'POST':
        test_name = lab_test.get_test_type_display()
        lab_test.delete()
        messages.success(request, f'Đã xóa xét nghiệm {test_name} thành công.')
        return redirect('laboratory_test_list', usubjid=usubjid)
    
    return render(request, 'study_43en/laboratory_test_confirm_delete.html', {
        'lab_test': lab_test,
        'screening_case': screening_case,
    })

@login_required
@require_POST
def laboratory_test_inline_update(request, usubjid):
    """Cập nhật xét nghiệm trực tiếp từ trang list bằng AJAX"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    try:
        # Lấy thông tin từ request POST
        test_id = request.POST.get('test_id')
        result = request.POST.get('result', '')
        performed_date = request.POST.get('performed_date') or None
        performed = request.POST.get('performed') == 'true'

        # Tìm và cập nhật xét nghiệm (dùng clinical_case=screening_case)
        lab_test = get_object_or_404(LaboratoryTest, id=test_id, clinical_case=screening_case)
        lab_test.result = result
        lab_test.performed = performed

        if performed and performed_date:
            from datetime import datetime
            lab_test.performed_date = datetime.strptime(performed_date, '%Y-%m-%d').date()
        elif not performed:
            lab_test.performed_date = None

        lab_test.save()

        return JsonResponse({'success': True, 'message': 'Cập nhật thành công'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
@require_POST
def laboratory_category_update(request, usubjid, category):
    """Cập nhật tất cả các xét nghiệm trong một nhóm"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    try:
        # Lấy tất cả các xét nghiệm thuộc category
        lab_tests = LaboratoryTest.objects.filter(
            clinical_case=screening_case,
            category=category
        )
        
        # Lấy dữ liệu gửi đến từ form
        updated_tests = []
        errors = []
        
        for test_id, test_data in request.POST.items():
            if test_id.startswith('test_'):
                try:
                    test_id = test_id.replace('test_', '')
                    lab_test = get_object_or_404(LaboratoryTest, id=test_id, clinical_case=screening_case)
                    
                    # Cập nhật thông tin
                    lab_test.result = request.POST.get(f'result_{test_id}', '')
                    performed = request.POST.get(f'performed_{test_id}') == 'true'
                    lab_test.performed = performed
                    
                    performed_date = request.POST.get(f'performed_date_{test_id}')
                    if performed and performed_date:
                        from datetime import datetime
                        lab_test.performed_date = datetime.strptime(performed_date, '%Y-%m-%d').date()
                    elif not performed:
                        lab_test.performed_date = None
                    
                    lab_test.save()
                    updated_tests.append(test_id)
                except Exception as e:
                    errors.append(f"Lỗi khi cập nhật xét nghiệm {test_id}: {str(e)}")
        
        if errors:
            return JsonResponse({
                'success': False,
                'message': 'Có lỗi xảy ra khi cập nhật một số xét nghiệm',
                'errors': errors
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'message': f'Đã cập nhật {len(updated_tests)} xét nghiệm thành công'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
@require_POST
def laboratory_test_quick_create(request, usubjid):
    """Tạo nhanh xét nghiệm từ trang list bằng AJAX"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    try:
        # Lấy thông tin từ request POST
        test_type = request.POST.get('test_type')
        result = request.POST.get('result', '')
        performed_date = request.POST.get('performed_date') or None
        performed = request.POST.get('performed') == 'true'
        category = request.POST.get('category')

        # Log for debugging
        print(f"Received data: test_type={test_type}, category={category}, performed={performed}, result={result}")

        # Xử lý trường hợp khi test_type giống với category (cho Xquang, siêu âm...)
        imaging_categories = ["CHEST_XRAY", "ABDOMINAL_ULTRASOUND", "BRAIN_CT_MRI", 
                            "CHEST_ABDOMEN_CT", "ECHOCARDIOGRAPHY", "SOFT_TISSUE_ULTRASOUND"]

        if category in imaging_categories:
            test_type = category
            # Tìm sequence lớn nhất hiện tại cho test_type này
            max_sequence = LaboratoryTest.objects.filter(
                clinical_case=screening_case, 
                test_type=test_type
            ).aggregate(models.Max('sequence'))['sequence__max'] or 0
            # Tăng sequence lên 1
            next_sequence = max_sequence + 1
            # Tạo xét nghiệm mới với sequence mới
            lab_test = LaboratoryTest(
                clinical_case=screening_case,
                test_type=test_type,
                category=category,
                result=result,
                performed=performed,
                sequence=next_sequence
            )
        else:
            # Kiểm tra xem xét nghiệm đã tồn tại chưa
            existing_test = LaboratoryTest.objects.filter(
                clinical_case=screening_case,
                test_type=test_type
            ).first()
            if existing_test:
                return JsonResponse({
                    'success': False,
                    'message': f'Xét nghiệm {test_type} đã tồn tại cho bệnh nhân này'
                }, status=400)
            # Xét nghiệm thông thường, giữ sequence=1
            lab_test = LaboratoryTest(
                clinical_case=screening_case,
                test_type=test_type,
                category=category,
                result=result,
                performed=performed,
                sequence=1
            )

        # Xử lý performed_date nếu có
        if performed and performed_date:
            from datetime import datetime
            try:
                lab_test.performed_date = datetime.strptime(performed_date, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'success': False, 'message': 'Định dạng ngày không hợp lệ'}, status=400)

        lab_test.save()

        return JsonResponse({
            'success': True, 
            'message': f'Tạo xét nghiệm thành công',
            'test_id': lab_test.id,
            'sequence': lab_test.sequence
        })
    except Exception as e:
        import traceback
        print(f"Error in quick_create: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
@require_POST
def laboratory_test_delete_category(request, usubjid, category):
    """Xóa tất cả các xét nghiệm trong một nhóm"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    try:
        # Xóa tất cả xét nghiệm thuộc category
        lab_tests = LaboratoryTest.objects.filter(
            clinical_case=screening_case,
            category=category
        )
        
        count = lab_tests.count()
        lab_tests.delete()
        
        return JsonResponse({
            'success': True, 
            'message': f'Đã xóa {count} xét nghiệm trong nhóm thành công.',
            'deleted_count': count
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
def laboratory_test_category_tests(request, usubjid, category):
    """Lấy danh sách các loại xét nghiệm thuộc một nhóm"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    try:
        # Lấy tất cả các TEST_TYPE_CHOICES từ model LaboratoryTest
        all_test_types = dict(LaboratoryTest.TEST_TYPE_CHOICES)
        
        # Tìm các xét nghiệm đã tồn tại của bệnh nhân trong category này
        existing_tests = LaboratoryTest.objects.filter(
            clinical_case=screening_case,
            category=category
        ).values_list('test_type', flat=True)
        
        # Tạo một instance tạm thời để sử dụng _get_category_from_test_type
        temp = LaboratoryTest()
        
        # Lọc ra các loại xét nghiệm thuộc category
        category_tests = []
        for key, value in all_test_types.items():
            temp.test_type = key
            if temp._get_category_from_test_type() == category:
                # Chỉ thêm vào các loại xét nghiệm chưa tồn tại
                if key not in existing_tests:
                    category_tests.append({
                        'value': key,
                        'label': value
                    })
        
        return JsonResponse({
            'success': True,
            'tests': category_tests
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)
    
register = template.Library()

@register.filter
def has_any_results(tests):
    """Kiểm tra xem có xét nghiệm nào có kết quả không"""
    return any(test.result for test in tests)


@login_required
def sample_collection_edit(request, usubjid, sample_type=None):
    """Tạo mới hoặc chỉnh sửa mẫu thu thập"""
    # Lấy thông tin bệnh nhân
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    # Kiểm tra xem đã có mẫu cho loại mẫu này chưa
    try:
        sample = SampleCollection.objects.get(clinical_case=screening_case, sample_type=sample_type)
        is_new = False
    except SampleCollection.DoesNotExist:
        sample = SampleCollection(clinical_case=screening_case, sample_type=sample_type)
        is_new = True
    
    if request.method == 'POST':
        # Debug POST data
        print(f"POST Data: {request.POST}")
        
        # Xử lý dữ liệu boolean từ form
        post_data = request.POST.copy()
        
        # Đảm bảo các trường boolean được xử lý đúng
        for field_name in ['STOOL', 'THROATSWAB', 'RECTSWAB', 'BLOOD', 'KLEBPNEU', 'OTHERRES', 'KLEBPNEU_2', 'OTHERRES_2']:
            if field_name in post_data:
                if post_data[field_name] == 'on':
                    post_data[field_name] = 'True'
                elif post_data[field_name] == 'False':
                    post_data[field_name] = 'False'
        
        # Đảm bảo ngày hoàn thành luôn được thiết lập
        if not post_data.get('COMPLETEDDATE'):
            from datetime import date
            post_data['COMPLETEDDATE'] = date.today().strftime('%Y-%m-%d')
        
        form = SampleCollectionForm(post_data, instance=sample)
        if form.is_valid():
            sample = form.save(commit=False)
            sample.clinical_case = screening_case
            
            # Debug form data
            print(f"Form is valid. BLOOD field: {form.cleaned_data.get('BLOOD')}")
            
            # Nếu SAMPLE1 = False (không thu nhận mẫu), xóa các thông tin mẫu
            if not sample.SAMPLE1:
                sample.STOOL = False
                sample.THROATSWAB = False
                sample.RECTSWAB = False
                sample.BLOOD = False
                sample.CULTRESSTOOL = 'NoApply'
                sample.CULTRESRECTSWAB = 'NoApply'
                sample.CULTRESTHROATSWAB = 'NoApply'
                sample.KLEBPNEU = False
                sample.KLEBPNEU_2 = False
                sample.OTHERRES = False
                sample.OTHERRES_2 = False
                
            # Nếu không chọn "Phân", xóa ngày lấy mẫu phân
            if not sample.STOOL:
                sample.STOOLDATE = None
            
            # Nếu không chọn "Phết họng", xóa ngày lấy mẫu phết họng
            if not sample.THROATSWAB:
                sample.THROATSWABDATE = None
            
            # Nếu không chọn "Phết trực tràng", xóa ngày lấy mẫu phết trực tràng
            if not sample.RECTSWAB:
                sample.RECTSWABDATE = None
                
            # Nếu không chọn "Mẫu máu" hoặc là Sample 4, xóa ngày lấy mẫu máu
            if not sample.BLOOD or sample.sample_type == '4':
                sample.BLOOD = False  # Đảm bảo BLOOD luôn False cho Sample 4
                sample.BLOODDATE = None
            
            # Lưu người hoàn thành nếu chưa có
            if not sample.COMPLETEDBY:
                sample.COMPLETEDBY = request.user.username
                
            # Debug thông tin trước khi lưu
            debug_info = {
                'SAMPLE1': sample.SAMPLE1,
                'STOOL': sample.STOOL,
                'THROATSWAB': sample.THROATSWAB,
                'RECTSWAB': sample.RECTSWAB,
                'BLOOD': sample.BLOOD,
                'BLOODDATE': sample.BLOODDATE,
                'sample_type': sample.sample_type
            }
            
            # Lưu dữ liệu vào database
            sample.save()
            
            # Log debug info
            messages.debug(request, f'Thông tin đã lưu: {debug_info}')
            messages.success(request, f'Đã {"tạo mới" if is_new else "cập nhật"} thông tin mẫu thành công!')
            return redirect('sample_collection_list', usubjid=usubjid)
    else:
        form = SampleCollectionForm(instance=sample)
    
    from datetime import date
    return render(request, 'study_43en/sample_collection_form.html', {
        'form': form,
        'sample': sample,
        'screening_case': screening_case,
        'is_new': is_new,
        'usubjid': usubjid,
        'sample_type': sample_type,
        'today': date.today(),
    })

@login_required
def sample_collection_list(request, usubjid):
    """Hiển thị danh sách các mẫu đã thu thập của bệnh nhân"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    # Kiểm tra chế độ xem/chỉnh sửa
    mode = request.GET.get('mode', 'edit')  # Mặc định là chế độ chỉnh sửa
    is_view_only = mode == 'view'  # Xác định chế độ chỉ xem
    
    # Lấy tất cả các loại mẫu có thể thu thập
    sample_types = SampleCollection.SAMPLE_TYPE_CHOICES
    
    # Lấy tất cả các mẫu của bệnh nhân
    samples = SampleCollection.objects.filter(clinical_case=screening_case)
    
    # Tạo dictionary để lưu trữ mẫu theo loại
    samples_by_type = {}
    for sample in samples:
        # Sửa từ SAMPLETYPE thành sample_type
        samples_by_type[sample.sample_type] = sample
    
    return render(request, 'study_43en/sample_collection_list.html', {
        'usubjid': usubjid,
        'screening_case': screening_case,
        'sample_types': sample_types,
        'samples': samples,
        'samples_by_type': samples_by_type,
        'is_view_only': is_view_only,
    })

@login_required
def sample_collection_view(request, usubjid, sample_type):
    """Xem thông tin mẫu ở chế độ chỉ đọc"""
    screening_case = get_object_or_404(ScreeningCase, USUBJID=usubjid)
    
    # Sửa SAMPLETYPE thành sample_type
    sample = get_object_or_404(SampleCollection, clinical_case=screening_case, sample_type=sample_type)
    
    # Tạo form với instance nhưng disable tất cả các field
    form = SampleCollectionForm(instance=sample)
    
    # Disable tất cả các field để chỉ có thể xem
    for field in form.fields.values():
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True
    
    return render(request, 'study_43en/sample_collection_form.html', {
        'form': form,
        'sample': sample,
        'screening_case': screening_case,
        'is_view_only': True,
        'usubjid': usubjid,
        'sample_type': sample_type,
    })