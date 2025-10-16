# backend/api/studies/study_43en/urls.py

from django.urls import path, include
from django.conf import settings

# Import views từ folder views/
from .views import views_Base ,views_DISCH
from .views import views_SCR,views_ENR,views_Schedule, views_CLI
from .views import views_LAB,views_CLI_Micro ,views_EndCase
from .views import views_CLI_Labtest, views_SAM, views_FU_contact, views_FU_patient
from .views import views_Audit

# Import dashboard từ services
from .services import dashboard

# App name for namespacing
app_name = 'study_43en'

urlpatterns = [
    # ===== DASHBOARD & CHARTS =====
    path('dashboard/', dashboard.home_dashboard, name='home_dashboard'),
    
    # Chart APIs
    path('api/patient-cumulative/', dashboard.patient_cumulative_chart_data, name='patient_cumulative_chart_data'),
    path('api/contact-cumulative/', dashboard.contact_cumulative_chart_data, name='contact_cumulative_chart_data'),
    path('api/screening-comparison/', dashboard.screening_comparison_chart_data, name='screening_comparison_chart_data'),
    path('api/gender-distribution/', dashboard.gender_distribution_chart_data, name='gender_distribution_chart_data'),
    path('api/patient-enrollment/', dashboard.patient_enrollment_chart_data, name='patient_enrollment_chart_data'),
    path('api/sample-distribution/', dashboard.sample_distribution_chart_data, name='sample_distribution_chart_data'),

    # ===== AUDIT LOG =====
    path('audit-logs/', views_Audit.audit_log_list, name='audit_log_list'),
    path('audit-logs/<int:log_id>/', views_Audit.audit_log_detail, name='audit_log_detail'),

    # ===== SCREENING CASE =====
    path('screening/', views_SCR.screening_case_list, name='screening_case_list'),
    path('screening/create/', views_SCR.screening_case_create, name='screening_case_create'),
    path('screening/<str:SCRID>/view/', views_SCR.screening_case_view, name='screening_case_view'),
    path('screening/<str:usubjid>/update/', views_SCR.screening_case_update, name='screening_case_update'),  
    path('screening/<str:usubjid>/delete/', views_SCR.screening_case_delete, name='screening_case_delete'),  
    
    # ===== PATIENTS =====
    path('patients/', views_Base.patient_list, name='patient_list'),
    path('patient/<str:usubjid>/', views_Base.patient_detail, name='patient_detail'),
    
    # ===== ENROLLMENT CASE =====
    path('<str:usubjid>/enroll/', views_ENR.enrollment_case_create, name='enrollment_case_create'),
    path('<str:usubjid>/enroll/update/', views_ENR.enrollment_case_update, name='enrollment_case_update'),
    path('<str:usubjid>/enroll/delete/', views_ENR.enrollment_case_delete, name='enrollment_case_delete'),
    path('enrollment/<str:usubjid>/view/', views_ENR.enrollment_case_view, name='enrollment_case_view'),

    # # ===== CLINICAL CASE =====
    path('<str:usubjid>/clinical_form/', views_CLI.clinical_form, name='clinical_form'),
    path('<str:usubjid>/clinical/view/', views_CLI.clinical_form_view, name='clinical_form_view'),
    path('<str:usubjid>/clinical/', views_CLI.clinical_case_create, name='clinical_case_create'),
    path('<str:usubjid>/clinical/update/', views_CLI.clinical_case_update, name='clinical_case_update'),
    path('<str:usubjid>/clinical/detail/', views_CLI.clinical_case_detail, name='clinical_case_detail'),
    path('<str:usubjid>/clinical/delete/', views_CLI.clinical_case_delete, name='clinical_case_delete'),
    
    # # ===== LABORATORY TEST =====
    path('<str:usubjid>/laboratory/', views_CLI_Labtest.laboratory_test_list, name='laboratory_test_list'),
    path('<str:usubjid>/laboratory/<str:lab_type>/create/', views_CLI_Labtest.laboratory_test_create, name='laboratory_test_create'),
    path('<str:usubjid>/laboratory/<str:lab_type>/bulk-update/', views_CLI_Labtest.laboratory_test_bulk_update, name='laboratory_test_bulk_update'),
    path('<str:usubjid>/laboratory/category/<str:category>/tests/', views_CLI_Labtest.laboratory_test_category_tests, name='laboratory_test_category_tests'),
    path('<str:usubjid>/laboratory/<str:lab_type>/create-category/', views_CLI_Labtest.laboratory_test_create_category, name='laboratory_test_create_category'),

    # ===== MICROBIOLOGY =====
    path('<str:usubjid>/microbiology/', views_CLI_Micro.microbiology_culture_list, name='microbiology_culture_list'),
    path('<str:usubjid>/microbiology/create/', views_CLI_Micro.microbiology_culture_quick_create, name='microbiology_culture_quick_create'),
    path('<str:usubjid>/microbiology/quick-create/', views_CLI_Micro.microbiology_culture_quick_create, name='microbiology_culture_quick_create'),
    path('<str:usubjid>/microbiology/<int:culture_id>/update/', views_CLI_Micro.microbiology_culture_update, name='microbiology_culture_update'),
    path('<str:usubjid>/microbiology/<int:culture_id>/get/', views_CLI_Micro.microbiology_culture_get, name='microbiology_culture_get'),
    path('<str:usubjid>/microbiology/<int:culture_id>/delete/', views_CLI_Micro.microbiology_culture_delete, name='microbiology_culture_delete'),
    path('<str:usubjid>/microbiology/<int:culture_id>/antibiotics/', views_LAB.antibiotic_sensitivity_list, name='antibiotic_sensitivity_list'),
    path('<str:usubjid>/microbiology/<int:culture_id>/antibiotics/api/', views_LAB.antibiotic_sensitivity_list_api, name='antibiotic_sensitivity_list_api'),
    path('<str:usubjid>/microbiology/<int:culture_id>/antibiotics/create/', views_LAB.antibiotic_sensitivity_create, name='antibiotic_sensitivity_create'),
    path('<str:usubjid>/microbiology/<int:culture_id>/antibiotics/add/', views_LAB.antibiotic_sensitivity_add, name='antibiotic_sensitivity_add'),
    path('<str:usubjid>/microbiology/antibiotics/<int:sensitivity_id>/update/', views_LAB.antibiotic_sensitivity_update, name='antibiotic_sensitivity_update'),
    path('<str:usubjid>/microbiology/antibiotics/<int:sensitivity_id>/delete/', views_LAB.antibiotic_sensitivity_delete, name='antibiotic_sensitivity_delete'),
    path('<str:usubjid>/microbiology/<int:culture_id>/antibiotics/bulk-update/', views_LAB.antibiotic_sensitivity_bulk_update, name='antibiotic_sensitivity_bulk_update'),
    path('<str:usubjid>/microbiology/<int:culture_id>/sensitivity/', views_LAB.antibiotic_sensitivity_list, name='antibiotic_sensitivity_list'),

    # # ===== SAMPLE COLLECTION =====
    path('<str:usubjid>/samples/', views_SAM.sample_collection_list, name='sample_collection_list'),
    path('<str:usubjid>/samples/<str:sample_type>/create/', views_SAM.sample_collection_create, name='sample_collection_create'),
    path('<str:usubjid>/samples/<str:sample_type>/update/', views_SAM.sample_collection_update, name='sample_collection_update'),
    path('<str:usubjid>/samples/<str:sample_type>/view/', views_SAM.sample_collection_view, name='sample_collection_view'),

    # ===== FOLLOW-UP (Day 28) =====
    path('<str:usubjid>/followup/', views_FU_patient.followup_form, name='followup_form'),
    path('<str:usubjid>/followup/view/', views_FU_patient.followup_form_view, name='followup_form_view'),
    path('<str:usubjid>/followup/create/', views_FU_patient.followup_case_create, name='followup_case_create'),
    path('<str:usubjid>/followup/update/', views_FU_patient.followup_case_update, name='followup_case_update'),

    # ===== FOLLOW-UP (Day 90) =====
    path('<str:usubjid>/followup90/create/', views_FU_patient.followup_case90_create, name='followup_case90_create'),
    path('<str:usubjid>/followup90/update/', views_FU_patient.followup_case90_update, name='followup_case90_update'),
    path('<str:usubjid>/followup90/view/', views_FU_patient.followup_case90_view, name='followup_case90_view'),
    path('<str:usubjid>/followup90/', views_FU_patient.followup_form90, name='followup_form90'),
    path('<str:usubjid>/followup90/view/', views_FU_patient.followup_form90_view, name='followup_form90_view'),

    # ===== CONTACT SCREENING =====
    path('contacts/screening/', views_SCR.screening_contact_list, name='screening_contact_list'),
    path('contacts/screening/create/', views_SCR.screening_contact_create, name='screening_contact_create'),
    path('contacts/screening/<str:SCRID>/view/', views_SCR.screening_contact_view, name='screening_contact_view'),
    path('contacts/screening/<str:SCRID>/update/', views_SCR.screening_contact_update, name='screening_contact_update'),
    path('contacts/screening/<str:SCRID>/delete/', views_SCR.screening_contact_delete, name='screening_contact_delete'),
    
    # ===== CONTACT ENROLLMENT =====
    path('contact/<str:usubjid>/enroll/', views_ENR.enrollment_contact_create, name='enrollment_contact_create'),
    path('contact/<str:usubjid>/enroll/update/', views_ENR.enrollment_contact_update, name='enrollment_contact_update'),
    path('contact/<str:usubjid>/enroll/view/', views_ENR.enrollment_contact_view, name='enrollment_contact_view'),

    # # ===== DISCHARGE =====
    path('<str:usubjid>/discharge/', views_DISCH.discharge_form, name='discharge_form'),
    path('<str:usubjid>/discharge/view/', views_DISCH.discharge_form_view, name='discharge_form_view'),
    path('<str:usubjid>/discharge/create/', views_DISCH.discharge_case_create, name='discharge_case_create'),
    path('<str:usubjid>/discharge/update/', views_DISCH.discharge_case_update, name='discharge_case_update'),

    # # ===== CONTACT SAMPLE COLLECTION =====
    path('contact/<str:usubjid>/sample/view/', views_SAM.contact_sample_collection_view, name='contact_sample_collection_view'),
    path('contact/<str:usubjid>/samples/list/', views_SAM.contact_sample_collection_list, name='contact_sample_collection_list'),
    path('contact/<str:usubjid>/samples/<str:sample_type>/create/', views_SAM.contact_sample_collection_create, name='contact_sample_collection_create'),
    path('contact/<str:usubjid>/samples/<str:sample_type>/update/', views_SAM.contact_sample_collection_update, name='contact_sample_collection_update'),

    # ===== CONTACT MANAGEMENT =====
    path('contacts/', views_Base.contact_list, name='contact_list'),
    path('contact/<str:usubjid>/detail/', views_Base.contact_detail, name='contact_detail'),
    path('contact/<str:usubjid>/', views_Base.contact_detail, name='contact_detail'),

    # ===== CONTACT FOLLOW-UP =====
    path('contact/<str:usubjid>/followup/28/create/', views_FU_contact.contact_followup_28_create, name='contact_followup_28_create'),
    path('contact/<str:usubjid>/followup/28/update/', views_FU_contact.contact_followup_28_update, name='contact_followup_28_update'),
    path('contact/<str:usubjid>/followup/28/view/', views_FU_contact.contact_followup_28_view, name='contact_followup_28_view'),
    path('contact/<str:usubjid>/followup/90/create/', views_FU_contact.contact_followup_90_create, name='contact_followup_90_create'),
    path('contact/<str:usubjid>/followup/90/update/', views_FU_contact.contact_followup_90_update, name='contact_followup_90_update'),
    path('contact/<str:usubjid>/followup/90/view/', views_FU_contact.contact_followup_90_view, name='contact_followup_90_view'),

    # ===== END CASE CRF =====
    path('patient/<str:usubjid>/endcasecrf/create/', views_EndCase.endcasecrf_create, name='endcasecrf_create'),
    path('patient/<str:usubjid>/endcasecrf/update/', views_EndCase.endcasecrf_update, name='endcasecrf_update'),
    path('patient/<str:usubjid>/endcasecrf/view/', views_EndCase.endcasecrf_view, name='endcasecrf_view'),

    # ===== CONTACT END CASE CRF =====
    path('contact/<str:usubjid>/endcasecrf/create/', views_EndCase.contactendcasecrf_create, name='contactendcasecrf_create'),
    path('contact/<str:usubjid>/endcasecrf/update/', views_EndCase.contactendcasecrf_update, name='contactendcasecrf_update'),
    path('contact/<str:usubjid>/endcasecrf/view/', views_EndCase.contactendcasecrf_view, name='contactendcasecrf_view'),

    # ===== FOLLOW-UP TRACKING =====
    path('followup-tracking/', views_Schedule.followup_tracking_list, name='followup_tracking_list'),
    path('followup-tracking/<int:pk>/update/', views_Schedule.update_followup_status, name='update_followup_status'),
    path('followup-tracking/export/', views_Schedule.export_followup_tracking, name='export_followup_tracking'),

    # ===== EXPORT =====
    path('export-excel/', views_Base.export_to_excel, name='export_to_excel'),
]

