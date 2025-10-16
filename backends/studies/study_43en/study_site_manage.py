from django.db import models
from django.db.models import Q

class SiteFilteredQuerySet(models.QuerySet):
    """
    QuerySet tùy chỉnh để lọc các bản ghi theo SITEID được trích xuất từ USUBJID
    """
    def filter_by_site(self, site_id):
        """
        Lọc queryset theo SITEID
        
        Phương thức này xác định loại model và áp dụng bộ lọc phù hợp:
        - Nếu model có trường SITEID, lọc trực tiếp theo trường này
        - Nếu model có USUBJID, lọc theo prefix của USUBJID
        """
        if not site_id or site_id == 'all':
            return self
            
        model = self.model
        model_fields = [f.name for f in model._meta.get_fields()]
        
        # Trường hợp 1: Model có trường SITEID riêng (như ScreeningCase)
        if 'SITEID' in model_fields:
            return self.filter(SITEID=site_id)
            
        # Trường hợp 2: Model có trường USUBJID là CharField
        if 'USUBJID' in model_fields:
            field = model._meta.get_field('USUBJID')
            if isinstance(field, models.CharField):
                return self.filter(USUBJID__startswith=f"{site_id}-")
                
        # Trường hợp 3: Model có OneToOneField hoặc ForeignKey tên là USUBJID
        for field in model._meta.get_fields():
            if field.name == 'USUBJID' and (
                isinstance(field, models.OneToOneField) or
                isinstance(field, models.ForeignKey)
            ):
                try:
                    # Đối với mô hình ExpectedDates, ta cần tham chiếu đến related_model's USUBJID
                    related_model = field.related_model
                    related_fields = [f.name for f in related_model._meta.get_fields()]
                    
                    # Nếu model liên quan có SITEID, lọc theo SITEID
                    if 'SITEID' in related_fields:
                        return self.filter(USUBJID__SITEID=site_id)
                    
                    # Nếu model liên quan có USUBJID là CharField, lọc theo startswith
                    if 'USUBJID' in related_fields:
                        related_field = related_model._meta.get_field('USUBJID')
                        if isinstance(related_field, models.CharField):
                            return self.filter(USUBJID__USUBJID__startswith=f"{site_id}-")
                except Exception as e:
                    print(f"Error in filter_by_site for {model.__name__}: {str(e)}")
                    # If there's an error, return unfiltered queryset
                    return self
                
        # Trường hợp 4: Model có ENROLLCASE liên kết đến EnrollmentCase
        if 'ENROLLCASE' in model_fields:
            for field in model._meta.get_fields():
                if field.name == 'ENROLLCASE' and isinstance(field, models.ForeignKey):
                    return self.filter(ENROLLCASE__USUBJID__USUBJID__startswith=f"{site_id}-")
                
        return self

class SiteFilteredManage(models.Manager):
    """
    Manager tùy chỉnh để lọc các bản ghi theo SITEID được trích xuất từ USUBJID
    """
    def get_queryset(self):
        return SiteFilteredQuerySet(self.model, using=self._db)
        
    def filter_by_site(self, site_id):
        """
        Lọc queryset theo SITEID
        """
        return self.get_queryset().filter_by_site(site_id)