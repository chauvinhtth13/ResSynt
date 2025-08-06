from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.views.generic import RedirectView
from django.conf.urls.i18n import i18n_patterns  # Import i18n_patterns

from . import views

urlpatterns = [
    # Thêm URL path cho i18n
    # path('i18n/', include('django.conf.urls.i18n')),  # Để xử lý set_language
    
    # path('admin/', admin.site.urls),
    # path('', RedirectView.as_view(url='select-study/')),  # Chuyển hướng đến trang select-study
    # path('dashboard/', views.admin_dashboard, name='admin_dashboard'),  # Dashboard chính
    # path('select-study/', views.select_study, name='select_study'),  # Giữ lại cho tương thích ngược
    # path('patient-statistics/', views.patient_statistics, name='patient_statistics'),  # Thống kê bệnh nhân
    # path('43en/', include(('study_43en.urls', 'study_43en'), namespace='43en')),  # URLs for app study_43en with namespace
    
    # # Thêm URL patterns không có namespace - để tương thích với template cũ
    # path('', include('study_43en.urls')),  # Thêm URL patterns không có namespace
    
    # # Authentication
    # path('accounts/login/', auth_views.LoginView.as_view(
    #     template_name='registration/login.html',
    #     redirect_authenticated_user=True
    # ), name='login'),
    # path('accounts/logout/', auth_views.LogoutView.as_view(
    #     next_page='login'
    # ), name='logout'),
    
    # # Error pages
    # path('404/', lambda request: views.custom_404(request, Exception())),
    path("admin/", admin.site.urls),
]