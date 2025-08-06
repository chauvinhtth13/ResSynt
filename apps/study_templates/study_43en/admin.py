from django.contrib import admin
from .models import ScreeningCase, VasoIDrug , MicrobiologyCulture, AntibioticSensitivity, ExpectedDates, ScreeningContact

@admin.register(ScreeningCase)
class ScreeningCaseAdmin(admin.ModelAdmin):
    list_display = ['USUBJID', 'STUDYID', 'SITEID', 'SUBJID', 'INITIAL', 'SCREENINGFORMDATE']
    search_fields = ['USUBJID', 'SUBJID', 'INITIAL']
    list_filter = ['STUDYID', 'SITEID', 'SCREENINGFORMDATE']

@admin.register(VasoIDrug)
class VasoIDrugAdmin(admin.ModelAdmin):
    list_display = ['USUBJID', 'VASOIDRUGNAME', 'VASOIDRUGDOSAGE', 'VASOIDRUGSTARTDTC', 'VASOIDRUGENDDTC']
    search_fields = ['USUBJID__USUBJID', 'VASOIDRUGNAME']
    list_filter = ['VASOIDRUGSTARTDTC', 'VASOIDRUGENDDTC']

@admin.register(MicrobiologyCulture)
class MicrobiologyCultureAdmin(admin.ModelAdmin):
    list_display = ['id', 'clinical_case', 'sample_type', 'performed_date', 'is_positive', 'get_sensitivity_count']
    list_filter = ['sample_type', 'performed', 'result_type', 'performed_date']
    search_fields = ['clinical_case__USUBJID__USUBJID', 'sample_id', 'result_details']

@admin.register(AntibioticSensitivity)
class AntibioticSensitivityAdmin(admin.ModelAdmin):
    list_display = ['id', 'culture', 'tier', 'antibiotic_name', 'sensitivity_level', 
                   'inhibition_zone_diameter', 'mic_value']
    list_filter = ['tier', 'sensitivity_level']
    search_fields = ['culture__clinical_case__USUBJID__USUBJID', 'antibiotic_name', 'other_antibiotic_name']

# admin.py
@admin.register(ExpectedDates)
class ExpectedDatesAdmin(admin.ModelAdmin):
    list_display = ['enrollment_case', 'd10_expected_date_display', 'd28_expected_date_display', 'd90_expected_date_display']
    readonly_fields = ['d10_start_date_display', 'd10_end_date_display', 'd10_expected_date_display',
                      'd28_start_date_display', 'd28_end_date_display', 'd28_expected_date_display',
                      'd90_start_date_display', 'd90_end_date_display', 'd90_expected_date_display']