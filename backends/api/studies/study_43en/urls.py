# backends/api/studies/study_43en/urls.py

from django.urls import path

# Base views
from .views import views_Base, views_Schedule, views_audit, views_report

# Patient views
from .views.patient.screening import views_scr_case, views_scr_case_list, api_views as scr_api
from .views.patient.enrollment import views_enr_case
from .views.patient.clinical import views_clinical_case, views_readonly, views_clinical_lab
from .views.patient.laboratory import views_lab_micro, views_antibiotic_sensitivity
from .views.patient.sample import views_sample
from .views.patient.followup_28 import views_fu_28
from .views.patient.followup_90 import views_fu_90
from .views.patient.discharge import views_disch
from .views.patient.endcase import views_endcase

# Contact views
from .views.contact.screening import views_contact_scr, api_views as contact_scr_api
from .views.contact.enrollment import views_enr_contact
from .views.contact.sample import views_contact_sample
from .views.contact.followup_28 import views_contact_fu_28
from .views.contact.followup_90 import views_contact_fu_90
from .views.contact.endcase import views_contact_endcase

# Dashboard
from .services import dashboard

# App namespace
app_name = 'study_43en'

urlpatterns = [
    # ===== MANAGEMENT REPORT & CHARTS =====
    path('dashboard/', dashboard.management_report, name='management_report'),
    
    path('api/dashboard-stats/', 
         dashboard.get_dashboard_stats_api, 
         name='dashboard_stats_api'),
    
    # Enrollment chart data
    path('api/enrollment-chart/', 
         dashboard.get_enrollment_chart_api, 
         name='enrollment_chart_api'),
    
    # Monthly screening & enrollment statistics
    path('api/patient-monthly-stats/', 
         dashboard.get_monthly_screening_enrollment_api, 
         name='patient_monthly_stats_api'),

    # Contact monthly screening & enrollment statistics
    path('api/contact-monthly-stats/', 
         dashboard.get_monthly_contact_stats_api, 
         name='contact_monthly_stats_api'),
    # Sampling follow-up (patient & contact)
    path('api/sampling-followup/', 
         dashboard.get_sampling_followup_stats_api, 
         name='sampling_followup_api'),
    path('api/kpneumoniae-isolation/', 
         dashboard.get_kpneumoniae_isolation_stats_api, 
         name='kpneumoniae_isolation_api'),

    # ===== SCREENING CASE =====
    path('screening/', views_scr_case_list.screening_case_list, name='screening_case_list'),
    path('screening/create/', views_scr_case.screening_case_create, name='screening_case_create'),
    path('screening/<str:SCRID>/view/', views_scr_case.screening_case_view, name='screening_case_view'),
    
    # ⬅️ FIX: Change from 'usubjid' to 'scrid'
    path('screening/<str:SCRID>/update/', views_scr_case.screening_case_update, name='screening_case_update'),
    
    # ===== SCREENING API =====
    path('api/screening/generate-scrid/', scr_api.generate_scrid, name='api_generate_scrid'),
    
    
    # ===== PATIENTS =====
    path('patients/', views_Base.patient_list, name='patient_list'),
    path('patient/<str:usubjid>/', views_Base.patient_detail, name='patient_detail'),
    
    # ===== ENROLLMENT CASE =====
    path('<str:usubjid>/enroll/', views_enr_case.enrollment_case_create, name='enrollment_case_create'),
    path('<str:usubjid>/enroll/update/', views_enr_case.enrollment_case_update, name='enrollment_case_update'),
    path('enrollment/<str:usubjid>/view/', views_enr_case.enrollment_case_view, name='enrollment_case_view'),

    # ===== CLINICAL CASE =====
    path('<str:usubjid>/clinical/create/', views_clinical_case.clinical_case_create, name='clinical_case_create'),
    path('<str:usubjid>/clinical/update/', views_clinical_case.clinical_case_update, name='clinical_case_update'),
    path('<str:usubjid>/clinical/view/', views_readonly.clinical_case_view, name='clinical_case_view'),
    
    # ===== LABORATORY TEST =====
    path('<str:usubjid>/laboratory/', views_clinical_lab.laboratory_test_list, name='laboratory_test_list'),
    path('<str:usubjid>/laboratory/<str:lab_type>/create/', views_clinical_lab.laboratory_test_create, name='laboratory_test_create'),
    path('<str:usubjid>/laboratory/<str:lab_type>/bulk-update/', views_clinical_lab.laboratory_test_bulk_update, name='laboratory_test_bulk_update'),
    path('patient/<str:usubjid>/laboratory/view/<str:lab_type>/', 
     views_clinical_lab.laboratory_test_view, 
     name='laboratory_test_view'),


    # ===== MICROBIOLOGY =====
    path('<str:usubjid>/microbiology/', 
        views_lab_micro.microbiology_list, 
        name='microbiology_list'),

    path('<str:usubjid>/microbiology/create/', 
        views_lab_micro.microbiology_create, 
        name='microbiology_create'),

    #  Update endpoint
    path('<str:usubjid>/microbiology/<int:culture_id>/update/', 
        views_lab_micro.microbiology_update, 
        name='microbiology_update'),

    #  GET endpoint  
    path('<str:usubjid>/microbiology/<int:culture_id>/get/', 
        views_lab_micro.microbiology_get, 
        name='microbiology_get'),
        



    # ===== ANTIBIOTIC SENSITIVITY =====
    path('<str:usubjid>/microbiology/<int:culture_id>/antibiotics/', views_antibiotic_sensitivity.antibiotic_list, name='antibiotic_list'),
    path('<str:usubjid>/microbiology/<int:culture_id>/antibiotics/create/', views_antibiotic_sensitivity.antibiotic_create, name='antibiotic_create'),
    path('<str:usubjid>/microbiology/<int:culture_id>/antibiotics/<int:test_id>/update/', views_antibiotic_sensitivity.antibiotic_update, name='antibiotic_update'),
    path('<str:usubjid>/microbiology/<int:culture_id>/antibiotics/<int:test_id>/get/', views_antibiotic_sensitivity.antibiotic_get, name='antibiotic_get'),
    path('<str:usubjid>/antibiotics/statistics/', views_antibiotic_sensitivity.antibiotic_statistics, name='antibiotic_statistics'),
    path(
        'patient/<str:usubjid>/culture/<int:culture_id>/antibiotics/create-other/',
        views_antibiotic_sensitivity.antibiotic_create_other,  #  AJAX endpoint
        name='antibiotic_create_other'
    ),
    path('<str:usubjid>/antibiotics/statistics/', 
     views_antibiotic_sensitivity.antibiotic_statistics, 
     name='antibiotic_statistics'),

    # ===== SAMPLE COLLECTION =====
    path('<str:usubjid>/samples/', views_sample.sample_collection_list, name='sample_collection_list'),
    path('<str:usubjid>/samples/<str:sample_type>/create/', views_sample.sample_collection_create, name='sample_collection_create'),
    path('<str:usubjid>/samples/<str:sample_type>/update/', views_sample.sample_collection_update, name='sample_collection_update'),
    path('<str:usubjid>/samples/<str:sample_type>/view/', views_sample.sample_collection_view, name='sample_collection_view'),

    # ===== FOLLOW-UP (Day 28) =====
    path(
        '<str:usubjid>/followup/28/create/',
        views_fu_28.followup_28_create,
        name='followup_28_create'
    ),
    path(
        '<str:usubjid>/followup/28/update/',
        views_fu_28.followup_28_update,
        name='followup_28_update'
    ),
    path(
        '<str:usubjid>/followup/28/view/',
        views_fu_28.followup_28_view,
        name='followup_28_view'
    ),

    # ===== FOLLOW-UP (Day 90) =====
    path('<str:usubjid>/followup90/create/', views_fu_90.followup_90_create, name='followup_90_create'),
    path('<str:usubjid>/followup90/update/', views_fu_90.followup_90_update, name='followup_90_update'),
    path('<str:usubjid>/followup90/view/', views_fu_90.followup_90_view, name='followup_90_view'),

    # ===== CONTACT SCREENING =====
    path('contacts/screening/', views_contact_scr.screening_contact_list, name='screening_contact_list'),
    path('contacts/screening/create/', views_contact_scr.screening_contact_create, name='screening_contact_create'),
    path('contacts/screening/<str:SCRID>/view/', views_contact_scr.screening_contact_view, name='screening_contact_view'),
    path('contacts/screening/<str:SCRID>/update/', views_contact_scr.screening_contact_update, name='screening_contact_update'),
    
    # ===== CONTACT SCREENING API =====
    path('api/contact-screening/generate-scrid/', contact_scr_api.generate_contact_scrid, name='api_generate_contact_scrid'),
    
    # ===== CONTACT ENROLLMENT =====
    path('contact/<str:usubjid>/enroll/', views_enr_contact.enrollment_contact_create, name='enrollment_contact_create'),
    path('contact/<str:usubjid>/enroll/update/', views_enr_contact.enrollment_contact_update, name='enrollment_contact_update'),
    path('contact/<str:usubjid>/enroll/view/', views_enr_contact.enrollment_contact_view, name='enrollment_contact_view'),

    # ===== DISCHARGE =====
    path('<str:usubjid>/discharge/view/', views_disch.discharge_view, name='discharge_view'),
    path('<str:usubjid>/discharge/create/', views_disch.discharge_create, name='discharge_create'),
    path('<str:usubjid>/discharge/update/', views_disch.discharge_update, name='discharge_update'),

    # ===== CONTACT SAMPLE COLLECTION =====
    path('contact/<str:usubjid>/sample/view/', views_contact_sample.contact_sample_collection_view, name='contact_sample_collection_view'),
    path('contact/<str:usubjid>/samples/list/', views_contact_sample.contact_sample_collection_list, name='contact_sample_collection_list'),
    path('contact/<str:usubjid>/samples/<str:sample_type>/create/', views_contact_sample.contact_sample_collection_create, name='contact_sample_collection_create'),
    path('contact/<str:usubjid>/samples/<str:sample_type>/update/', views_contact_sample.contact_sample_collection_update, name='contact_sample_collection_update'),

    # ===== CONTACT MANAGEMENT =====
    path('contacts/', views_Base.contact_list, name='contact_list'),
    path('contact/<str:usubjid>/detail/', views_Base.contact_detail, name='contact_detail'),
    path('contact/<str:usubjid>/', views_Base.contact_detail, name='contact_detail'),

    # ===== CONTACT FOLLOW-UP =====
    path('contact/<str:usubjid>/followup/28/create/', views_contact_fu_28.contact_followup_28_create, name='contact_followup_28_create'),
    path('contact/<str:usubjid>/followup/28/update/', views_contact_fu_28.contact_followup_28_update, name='contact_followup_28_update'),
    path('contact/<str:usubjid>/followup/28/view/', views_contact_fu_28.contact_followup_28_view, name='contact_followup_28_view'),
    path('contact/<str:usubjid>/followup/90/create/', views_contact_fu_90.contact_followup_90_create, name='contact_followup_90_create'),
    path('contact/<str:usubjid>/followup/90/update/', views_contact_fu_90.contact_followup_90_update, name='contact_followup_90_update'),
    path('contact/<str:usubjid>/followup/90/view/', views_contact_fu_90.contact_followup_90_view, name='contact_followup_90_view'),

    # ===== END CASE CRF =====
    path('patient/<str:usubjid>/endcase/create/', 
         views_endcase.endcase_create, 
         name='endcase_create'),
    
    path('patient/<str:usubjid>/endcase/update/', 
         views_endcase.endcase_update, 
         name='endcase_update'),
    
    path('patient/<str:usubjid>/endcase/view/', 
         views_endcase.endcase_view, 
         name='endcase_view'),

    # ===== CONTACT END CASE CRF =====
    path('contact/<str:usubjid>/endcasecrf/create/', views_contact_endcase.contactendcase_create, name='contactendcasecrf_create'),
    path('contact/<str:usubjid>/endcasecrf/update/', views_contact_endcase.contactendcase_update, name='contactendcasecrf_update'),
    path('contact/<str:usubjid>/endcasecrf/view/', views_contact_endcase.contactendcase_view, name='contactendcasecrf_view'),

    # ===== FOLLOW-UP TRACKING =====
    path('followup-tracking/', views_Schedule.followup_tracking_list, name='followup_tracking_list'),
    path('followup-tracking/<int:pk>/complete/', views_Schedule.complete_followup_ajax, name='complete_followup_ajax'),
    path('followup-tracking/<int:pk>/update/', views_Schedule.update_followup_status, name='update_followup_status'),
    path('followup-tracking/export/', views_Schedule.export_followup_tracking, name='export_followup_tracking'),
    path('followup-tracking/<int:pk>/missed/', views_Schedule.mark_followup_missed, name='mark_followup_missed'),

    
    # ===== EXPORT =====
    path('export/', views_Base.export_data_page, name='export_data_page'),  
    path('export/download/', views_Base.export_data, name='export_data'),  
    path('export-excel/', views_Base.export_to_excel, name='export_to_excel'),

    # Audit Log URLs
    path('audit-logs/', views_audit.audit_log_list, name='audit_log_list'),
    path('audit-logs/<int:log_id>/', views_audit.audit_log_detail, name='audit_log_detail'),


    #  NOTIFICATION API
    path('api/notification/read/', views_Schedule.mark_notification_read, name='notification_mark_read'),
    path('api/notification/read-all/', views_Schedule.mark_all_notifications_read, name='notification_mark_all_read'),
    path('api/notification/count/', views_Schedule.get_notification_count, name='notification_count'),

    # ===== TMG REPORT EXPORT =====
    path('report/export/', views_report.report_export_view, name='report_export'),

]
