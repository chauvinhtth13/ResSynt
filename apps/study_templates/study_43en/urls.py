from django.urls import path, include
from django.conf import settings
from . import views
from . import views_laboratory
from . import views_microbiology
from . import views_chart


urlpatterns = [
    # Screening URLs - Tab riêng cho sàng lọc
    path('screening/', views.screening_case_list, name='screening_case_list'),
    path('screening/create/', views.screening_case_create, name='screening_case_create'),
    path('screening/<str:screening_id>/view/', views.screening_case_view, name='screening_case_view'),
    path('screening/<str:usubjid>/update/', views.screening_case_update, name='screening_case_update'),  
    path('screening/<str:usubjid>/delete/', views.screening_case_delete, name='screening_case_delete'),  
    
    # Patients URLs - Tab riêng cho bệnh nhân đã tham gia
    path('patients/', views.patient_list, name='patient_list'),
    path('patient/<str:usubjid>/', views.patient_detail, name='patient_detail'),
    
    # EnrollmentCase urls
    path('<str:usubjid>/enroll/', views.enrollment_case_create, name='enrollment_case_create'),
    path('<str:usubjid>/enroll/update/', views.enrollment_case_update, name='enrollment_case_update'),
    path('<str:usubjid>/enroll/delete/', views.enrollment_case_delete, name='enrollment_case_delete'),
    path('enrollment/<str:usubjid>/view/', views.enrollment_case_view, name='enrollment_case_view'),
    # ClinicalCase urls
    path('<str:usubjid>/clinical_form/', views.clinical_form, name='clinical_form'),
    # Clinical form read-only view
    path('<str:usubjid>/clinical/view/', views.clinical_form_view, name='clinical_form_view'),
    path('<str:usubjid>/clinical/', views.clinical_case_create, name='clinical_case_create'),
    path('<str:usubjid>/clinical/update/', views.clinical_case_update, name='clinical_case_update'),
    path('<str:usubjid>/clinical/detail/', views.clinical_case_detail, name='clinical_case_detail'),
    path('<str:usubjid>/clinical/delete/', views.clinical_case_delete, name='clinical_case_delete'),
      # LaboratoryTest urls
    path('<str:usubjid>/laboratory/', views_laboratory.laboratory_test_list, name='laboratory_test_list'),
    path('<str:usubjid>/laboratory/create/', views_laboratory.laboratory_test_create, name='laboratory_test_create'),
    path('<str:usubjid>/laboratory/<int:test_id>/edit/', views_laboratory.laboratory_test_edit, name='laboratory_test_edit'),
    path('<str:usubjid>/laboratory/<str:category>/bulk-update/', views_laboratory.laboratory_test_bulk_update, name='laboratory_test_bulk_update'),
    path('<str:usubjid>/laboratory/<int:test_id>/delete/', views_laboratory.laboratory_test_delete, name='laboratory_test_delete'),
    path('<str:usubjid>/laboratory/inline-update/', views_laboratory.laboratory_test_inline_update, name='laboratory_test_inline_update'),
    path('<str:usubjid>/laboratory/category/<str:category>/update/', views_laboratory.laboratory_category_update, name='laboratory_category_update'),
    path('<str:usubjid>/laboratory/quick-create/', views_laboratory.laboratory_test_quick_create, name='laboratory_test_quick_create'),
    path('<str:usubjid>/laboratory/category/<str:category>/delete/', views_laboratory.laboratory_test_delete_category, name='laboratory_test_delete_category'),
    path('<str:usubjid>/laboratory/category/<str:category>/tests/', views_laboratory.laboratory_test_category_tests, name='laboratory_test_category_tests'),


    # MicrobiologyCulture urls
    path('<str:usubjid>/microbiology/', views_microbiology.microbiology_culture_list, name='microbiology_culture_list'),
    path('<str:usubjid>/microbiology/create/', views_microbiology.microbiology_culture_quick_create, name='microbiology_culture_quick_create'),
    path('<str:usubjid>/microbiology/quick-create/', views_microbiology.microbiology_culture_quick_create, name='microbiology_culture_quick_create'),  # Thêm URL mới này
    path('<str:usubjid>/microbiology/<int:culture_id>/update/', views_microbiology.microbiology_culture_update, name='microbiology_culture_update'),
    path('<str:usubjid>/microbiology/<int:culture_id>/get/', views_microbiology.microbiology_culture_get, name='microbiology_culture_get'),
    path('<str:usubjid>/microbiology/<int:culture_id>/delete/', views_microbiology.microbiology_culture_delete, name='microbiology_culture_delete'),
    path('<str:usubjid>/microbiology/<int:culture_id>/antibiotics/', views_microbiology.antibiotic_sensitivity_list, name='antibiotic_sensitivity_list'),
    path('<str:usubjid>/microbiology/<int:culture_id>/antibiotics/api/', views_microbiology.antibiotic_sensitivity_list_api, name='antibiotic_sensitivity_list_api'),
    path('<str:usubjid>/microbiology/<int:culture_id>/antibiotics/create/', views_microbiology.antibiotic_sensitivity_create, name='antibiotic_sensitivity_create'),
    path('<str:usubjid>/microbiology/<int:culture_id>/antibiotics/add/', views_microbiology.antibiotic_sensitivity_add, name='antibiotic_sensitivity_add'),
    path('<str:usubjid>/microbiology/antibiotics/<int:sensitivity_id>/update/', views_microbiology.antibiotic_sensitivity_update, name='antibiotic_sensitivity_update'),
    path('<str:usubjid>/microbiology/antibiotics/<int:sensitivity_id>/delete/', views_microbiology.antibiotic_sensitivity_delete, name='antibiotic_sensitivity_delete'),
    path('<str:usubjid>/microbiology/<int:culture_id>/antibiotics/bulk-update/', views_microbiology.antibiotic_sensitivity_bulk_update, name='antibiotic_sensitivity_bulk_update'),
    path('<str:usubjid>/microbiology/<int:culture_id>/sensitivity/', 
     views_microbiology.antibiotic_sensitivity_list, 
     name='antibiotic_sensitivity_list'),

    # SampleCollection urls
    path('<str:usubjid>/samples/', views_laboratory.sample_collection_list, name='sample_collection_list'),
    path('<str:usubjid>/samples/<str:sample_type>/', views_laboratory.sample_collection_edit, name='sample_collection_edit'),
    path('<str:usubjid>/samples/<str:sample_type>/view/', views_laboratory.sample_collection_view, name='sample_collection_view'),

    # FollowUpCase urls 
    path('<str:usubjid>/followup/', views.followup_form, name='followup_form'),
    path('<str:usubjid>/followup/view/', views.followup_form_view, name='followup_form_view'),
    path('<str:usubjid>/followup/create/', views.followup_case_create, name='followup_case_create'),
    path('<str:usubjid>/followup/update/', views.followup_case_update, name='followup_case_update'),
    path('<str:usubjid>/followup/detail/', views.followup_case_detail, name='followup_case_detail'),

    # Thêm vào urls.py
    path('patient/<str:usubjid>/followup90/create/', views.followup_case90_create, name='followup_case90_create'),
    path('patient/<str:usubjid>/followup90/update/', views.followup_case90_update, name='followup_case90_update'),
    path('patient/<str:usubjid>/followup90/view/', views.followup_case90_view, name='followup_case90_view'),
    path('patient/<str:usubjid>/followup90/detail/', views.followup_case90_detail, name='followup_case90_detail'),
    path('patient/<str:usubjid>/followup/form90/', views.followup_form90, name='followup_form90'),
    path('patient/<str:usubjid>/followup/form90/view/', views.followup_form90_view, name='followup_form90_view'),

    # Contact Screening URLs
    path('contacts/screening/', views.screening_contact_list, name='screening_contact_list'),
    path('contacts/screening/create/', views.screening_contact_create, name='screening_contact_create'),
    path('contacts/screening/<str:usubjid_or_id>/view/', views.screening_contact_view, name='screening_contact_view'),
    path('contacts/screening/<str:usubjid_or_id>/update/', views.screening_contact_update, name='screening_contact_update'),
    path('contacts/screening/<str:usubjid_or_id>/delete/', views.screening_contact_delete, name='screening_contact_delete'),

    # Contact Enrollment URLs
    path('contact/<str:usubjid>/enroll/', views.enrollment_contact_create, name='enrollment_contact_create'),
    path('contact/<str:usubjid>/enroll/update/', views.enrollment_contact_update, name='enrollment_contact_update'),
    path('contact/<str:usubjid>/enroll/view/', views.enrollment_contact_view, name='enrollment_contact_view'),

    # DischargeCase urls
    path('patient/<str:usubjid>/discharge/', views.discharge_form, name='discharge_form'),
    path('patient/<str:usubjid>/discharge/view/', views.discharge_form_view, name='discharge_form_view'),


    # Contact Sample Collection URLs
    path('contact/<str:usubjid>/sample/view/', views.contact_sample_collection_view, name='contact_sample_collection_view'),
    path('contact/<str:usubjid>/samples/list/', views.contact_sample_collection_list, name='contact_sample_collection_list'), # THÊM DÒNG NÀY
    path('contact/<str:usubjid>/samples/<str:sample_type>/edit/', views.contact_sample_collection_edit, name='contact_sample_collection_edit'),

    # Contact Management URLs
    path('contacts/', views.contact_list, name='contact_list'),
    path('contact/<str:usubjid>/detail/', views.contact_detail, name='contact_detail'),

    # Contact Follow-up URLs
    path('contact/<str:usubjid>/followup-28/', views.contact_followup_28_edit, name='contact_followup_28_edit'),
    path('contact/<str:usubjid>/followup-28/view/', views.contact_followup_28_view, name='contact_followup_28_view'),
    path('contact/<str:usubjid>/followup-90/', views.contact_followup_90_edit, name='contact_followup_90_edit'),
    path('contact/<str:usubjid>/followup-90/view/', views.contact_followup_90_view, name='contact_followup_90_view'),

     # API cho biểu đồ tích lũy bệnh nhân và contact
    path('api/patient-cumulative-chart-data/', views_chart.patient_cumulative_chart_data, name='patient_cumulative_chart_data'),
    path('api/contact-cumulative-chart-data/', views_chart.contact_cumulative_chart_data, name='contact_cumulative_chart_data'),
    # Thêm vào urlpatterns
    path('api/screening-comparison-chart/', views_chart.screening_comparison_chart_data, name='screening_comparison_chart_data'),
    path('api/sample-distribution-chart/', views_chart.sample_distribution_chart_data, name='sample_distribution_chart_data'),
    path('api/gender-distribution-chart-data/', views_chart.gender_distribution_chart_data, name='gender_distribution_chart_data'),
    path('api/charts/patient-enrollment/', views_chart.patient_enrollment_chart_data, name='patient_enrollment_chart_data'),
]

# Thêm Debug Toolbar URLs khi debug mode được bật
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns