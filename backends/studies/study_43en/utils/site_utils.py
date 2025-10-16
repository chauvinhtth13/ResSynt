# from functools import wraps
# from django.db import models
# from django.db.models import Q
# import re

# def extract_site_id_from_usubjid(usubjid):
#     """
#     Trích xuất SITEID từ USUBJID (định dạng: 003-A-002)
#     """
#     if not usubjid:
#         return None
    
#     # Lấy phần đầu tiên của USUBJID (trước dấu gạch ngang đầu tiên)
#     match = re.match(r'^(\d+)-', str(usubjid))
#     if match:
#         return match.group(1)
#     return None

# def filter_by_site(view_func):
#     """
#     Decorator lọc queryset theo site được chọn trong session
#     """
#     @wraps(view_func)
#     def _wrapped_view(request, *args, **kwargs):
#         # Lấy site_id từ request (đã được thêm bởi middleware)
#         site_id = getattr(request, 'selected_site_id', None)
        
#         # Gọi view gốc
#         response = view_func(request, *args, **kwargs)
        
#         # Nếu response là QuerySet hoặc model instance
#         if hasattr(response, 'model'):
#             # Nếu model có custom manager site_objects
#             if hasattr(response.model, 'site_objects'):
#                 # Áp dụng bộ lọc site
#                 if site_id:
#                     return response.model.site_objects.filter_by_site(site_id)
        
#         return response
    
#     return _wrapped_view

# def apply_site_filter(func):
#     """
#     Decorator để tự động áp dụng bộ lọc site cho hàm sử dụng objects.all(), objects.filter(), v.v.
#     Thêm decorator này vào các view để đảm bảo tự động lọc theo site.
#     """
#     @wraps(func)
#     def wrapper(request, *args, **kwargs):
#         # Lưu lại objects.all, objects.filter, v.v.
#         old_all = models.Manager.all
#         old_filter = models.Manager.filter
#         old_exclude = models.Manager.exclude
#         old_get = models.Manager.get
        
#         # Lấy site_id từ session
#         site_id = request.session.get('selected_site_id')
        
#         # Chỉ áp dụng nếu có site_id và không phải 'all'
#         if site_id and site_id != 'all':
#             # Thay thế các phương thức của Manager để tự động lọc theo site
#             def filtered_all(self, *args, **kwargs):
#                 qs = old_all(self, *args, **kwargs)
#                 model = self.model
#                 # Kiểm tra xem model có site_objects không
#                 if hasattr(model, 'site_objects'):
#                     # Lọc theo site
#                     try:
#                         return model.site_objects.filter_by_site(site_id)
#                     except:
#                         return qs
#                 return qs
                
#             def filtered_filter(self, *args, **kwargs):
#                 qs = old_filter(self, *args, **kwargs)
#                 model = self.model
#                 # Kiểm tra xem model có site_objects không
#                 if hasattr(model, 'site_objects'):
#                     # Lọc theo site
#                     try:
#                         # Lọc qs theo site_id
#                         if 'SITEID' in [f.name for f in model._meta.get_fields()]:
#                             kwargs['SITEID'] = site_id
#                             return qs.filter(**kwargs)
#                         elif hasattr(model, 'USUBJID') and isinstance(model._meta.get_field('USUBJID'), models.CharField):
#                             return qs.filter(USUBJID__startswith=f"{site_id}-")
#                         return qs
#                     except:
#                         return qs
#                 return qs
                
#             # Thay thế các phương thức
#             models.Manager.all = filtered_all
#             models.Manager.filter = filtered_filter
            
#         # Gọi hàm gốc
#         result = func(request, *args, **kwargs)
        
#         # Khôi phục các phương thức ban đầu
#         models.Manager.all = old_all
#         models.Manager.filter = old_filter
#         models.Manager.exclude = old_exclude
#         models.Manager.get = old_get
        
#         return result
        
#     return wrapper

# def site_context_processor(request):
#     """
#     Context processor để thêm thông tin site vào mọi template
#     """
#     # Danh sách các site có sẵn - bạn có thể lấy từ cơ sở dữ liệu
#     available_sites = [
#         {'id': '003', 'name': 'Site 003'},
#         {'id': '011', 'name': 'Site 011'},
#         {'id': '020', 'name': 'Site 020'},
#         # Thêm các site khác nếu cần
#     ]
    
#     # Lấy site được chọn từ session hoặc từ parameter
#     selected_site_id = None
    
#     # Ưu tiên lấy từ tham số URL
#     if 'site_id' in request.GET:
#         selected_site_id = request.GET.get('site_id')
#         # Lưu vào session để dùng cho các request tiếp theo
#         request.session['selected_site_id'] = selected_site_id
#     # Nếu không có tham số, lấy từ session
#     else:
#         selected_site_id = request.session.get('selected_site_id', None)
    
#     return {
#         'available_sites': available_sites,
#         'selected_site_id': selected_site_id
#     }