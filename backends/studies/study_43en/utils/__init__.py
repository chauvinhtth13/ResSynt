# Define utility functions for site filtering
# NOTE: Main implementation is in site_utils.py
# This file provides backwards-compatible imports

from backends.studies.study_43en.utils.site_utils import (
    get_site_filtered_object_or_404,
    get_filtered_queryset,
    get_site_filter_params,
    batch_get_related,
    batch_check_exists,
    invalidate_cache,
)


def get_queryset_for_model(model_class, site_id=None):
    """
    Trả về queryset phù hợp với model và site_id.
    Nếu site_id là 'all' hoặc None, trả về tất cả dữ liệu.
    Nếu site_id có giá trị, lọc theo site_id.
    
    Returns:
        QuerySet: Queryset đã được lọc theo site_id (nếu có)
    """
    if hasattr(model_class, 'site_objects'):
        if site_id is None or site_id == 'all':
            return model_class.objects.all()
        else:
            return model_class.site_objects.filter_by_site(site_id)
    else:
        return model_class.objects.all()
