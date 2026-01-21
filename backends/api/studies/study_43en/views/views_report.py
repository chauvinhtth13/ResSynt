# backends/api/studies/study_43en/views/views_report.py
"""
TMG Report Export Views

Handles report generation and download in DOCX and PDF formats.
Backend-first approach - all logic here, no JavaScript.
"""

from django.http import HttpResponse
from django.views import View
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from datetime import datetime
import logging
import os

from backends.studies.study_43en.forms.report_forms import ReportExportForm
from backends.studies.study_43en.services.report_generator import TMGReportGenerator
from backends.studies.study_43en.services.pdf_report_generator import PDFReportGenerator
from backends.studies.study_43en.services.report_data_service import ReportDataService

logger = logging.getLogger(__name__)


@method_decorator(login_required, name='dispatch')
class ReportExportView(View):
    """
    View xuất báo cáo TMG
    
    GET: Display export form
    POST: Generate and download report (DOCX or PDF)
    """
    
    template_name = 'studies/study_43en/report/report_export_form.html'
    
    def get(self, request):
        """Hiển thị form xuất báo cáo"""
        form = ReportExportForm()
        
        context = {
            'form': form,
            'page_title': 'Export TMG Report',
            'study_code': '43EN',
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Xử lý request xuất báo cáo"""
        form = ReportExportForm(request.POST)
        
        if not form.is_valid():
            context = {
                'form': form,
                'page_title': 'Export TMG Report',
                'study_code': '43EN',
            }
            return render(request, self.template_name, context)
        
        try:
            # Get form data
            start_date, end_date = form.get_date_range()
            reporting_date = form.cleaned_data['reporting_date']
            export_format = form.cleaned_data['export_format']
            
            # Get site filter from middleware
            site_filter = getattr(request, 'site_filter', 'all')
            
            # Get data from database (uses dashboard-consistent logic)
            data_service = ReportDataService(site_filter=site_filter)
            report_data = data_service.get_report_data()
            
            # Add manual input data
            report_data['action_points'] = form.parse_action_points()
            report_data['general_procedures'] = form.cleaned_data.get('general_procedures', '')
            report_data['ethics_regulatory'] = form.cleaned_data.get('ethics_regulatory', '')
            report_data['study_amendments'] = form.cleaned_data.get('study_amendments', '')
            report_data['deviations'] = form.parse_deviations()
            report_data['data_management'] = form.cleaned_data.get('data_management', '')
            report_data['aob'] = form.cleaned_data.get('aob', '')
            
            # Clear auto-generated sections if not selected
            if not form.cleaned_data.get('include_recruitment'):
                report_data['recruitment'] = {}
            if not form.cleaned_data.get('include_samples'):
                report_data['sample_processing'] = {}
            if not form.cleaned_data.get('include_safety'):
                report_data['safety_reporting'] = {}
            
            # Get logo path
            logo_path = self._get_logo_path()
            
            # Generate report based on format
            date_str = reporting_date.strftime('%d%b%Y').upper()
            
            if export_format == 'pdf':
                # Generate PDF
                generator = PDFReportGenerator(
                    study_code='43EN',
                    reporting_date=reporting_date
                )
                document_buffer = generator.generate(report_data, logo_path)
                
                filename = f"43EN_Update_Report_{date_str}.pdf"
                content_type = 'application/pdf'
            else:
                # Generate DOCX (default)
                generator = TMGReportGenerator(
                    study_code='43EN',
                    reporting_date=reporting_date
                )
                document_buffer = generator.generate(report_data, logo_path)
                
                filename = f"43EN_Update_Report_{date_str}.docx"
                content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            
            # Return response
            response = HttpResponse(
                document_buffer.getvalue(),
                content_type=content_type
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # Log the export action
            logger.info(
                f"TMG Report ({export_format.upper()}) exported by {request.user.username} "
                f"for date range {start_date} to {end_date}"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating TMG report: {e}", exc_info=True)
            
            context = {
                'form': form,
                'page_title': 'Export TMG Report',
                'study_code': '43EN',
                'error_message': f'Error generating report: {str(e)}',
            }
            return render(request, self.template_name, context)
    
    def _get_logo_path(self) -> str:
        """Get path to OUCRU logo file"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )))
        
        possible_paths = [
            os.path.join(base_dir, 'frontends', 'static', 'studies', 'study_43en', 'images', 'logo_oucru.png'),
            os.path.join(base_dir, 'frontends', 'static', 'studies', 'study_43en', 'images', 'logo.png'),
            os.path.join(base_dir, 'frontends', 'static', 'studies', 'study_43en', 'images', 'logo.webp'),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None


# Function-based view wrapper for URL routing
def report_export_view(request):
    """Wrapper function for ReportExportView"""
    view = ReportExportView.as_view()
    return view(request)
