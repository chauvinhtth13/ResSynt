# # backend/studies/study_43en/urls.py

# from django.urls import path
# from ...api.studies.study_43en.services import dashboard

# # App name for namespacing
# app_name = 'study_43en'

# urlpatterns = [
#     # ===== MAIN DASHBOARD VIEW =====
#     path('dashboard/', 
#          dashboard.home_dashboard, 
#          name='home_dashboard'),
    
#     # ===== CHART DATA APIs =====
#     path('api/patient-cumulative/', 
#          dashboard.patient_cumulative_chart_data, 
#          name='patient_cumulative_chart_data'),
    
#     path('api/contact-cumulative/', 
#          dashboard.contact_cumulative_chart_data, 
#          name='contact_cumulative_chart_data'),
    
#     path('api/screening-comparison/', 
#          dashboard.screening_comparison_chart_data, 
#          name='screening_comparison_chart_data'),
    
#     path('api/gender-distribution/', 
#          dashboard.gender_distribution_chart_data, 
#          name='gender_distribution_chart_data'),
    
#     path('api/patient-enrollment/', 
#          dashboard.patient_enrollment_chart_data, 
#          name='patient_enrollment_chart_data'),
    
#     path('api/sample-distribution/', 
#          dashboard.sample_distribution_chart_data, 
#          name='sample_distribution_chart_data'),
# ]