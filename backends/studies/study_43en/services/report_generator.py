# backends/studies/study_43en/services/report_generator.py
"""
TMG Report Generator Service

Creates TMG (Trial Management Group) reports in Word format
following OUCRU standard template.

Backend-first approach - all logic here, no JavaScript.
"""

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from datetime import datetime
from io import BytesIO
import os
import logging

logger = logging.getLogger(__name__)


class TMGReportGenerator:
    """
    Service class để tạo báo cáo TMG theo format chuẩn OUCRU
    
    Tuân thủ nguyên tắc:
    - Backend xử lý toàn bộ business logic
    - Không có JavaScript
    - Validation ở server-side
    """
    
    # Constants
    DOCUMENT_CODE = 'TM-CTU-003'
    VERSION = '4.0'
    SECTION = 'CTU'
    EFFECTIVE_DATE = '06JAN22'
    
    # Font settings
    FONT_FAMILY = 'Calibri'
    TITLE_SIZE = Pt(20)
    HEADING_SIZE = Pt(12)
    BODY_SIZE = Pt(11)
    SMALL_SIZE = Pt(10)
    
    # Colors
    DARK_BLUE = RGBColor(8, 26, 59)  # #081A3B - Logo color
    BLACK = RGBColor(0, 0, 0)
    
    def __init__(self, study_code: str, reporting_date: datetime):
        """
        Khởi tạo generator
        
        Args:
            study_code: Mã nghiên cứu (ví dụ: '43EN')
            reporting_date: Ngày báo cáo
        """
        self.study_code = study_code
        self.reporting_date = reporting_date
        self.document = Document()
        self._setup_document()
    
    def _setup_document(self):
        """Cấu hình document cơ bản"""
        # Set page margins
        sections = self.document.sections
        for section in sections:
            section.top_margin = Cm(2)
            section.bottom_margin = Cm(2)
            section.left_margin = Cm(2)
            section.right_margin = Cm(2)
    
    def _add_header(self, logo_path: str = None):
        """
        Thêm header với:
        - Logo OUCRU (trái)
        - TMG REPORT (giữa)
        - Document info (phải)
        """
        # Tạo table 3 cột cho header layout
        header_table = self.document.add_table(rows=2, cols=3)
        header_table.autofit = False
        
        # Set column widths
        header_table.columns[0].width = Inches(1.5)  # Logo
        header_table.columns[1].width = Inches(4)     # Title
        header_table.columns[2].width = Inches(1.5)   # Version info
        
        # Row 1: Logo | TMG REPORT | Version
        # Cell 0,0: Logo
        logo_cell = header_table.cell(0, 0)
        logo_cell.merge(header_table.cell(1, 0))  # Merge 2 rows
        
        # Add logo image if path exists
        if logo_path and os.path.exists(logo_path):
            logo_para = logo_cell.paragraphs[0]
            run = logo_para.add_run()
            try:
                run.add_picture(logo_path, width=Inches(1.2))
            except Exception as e:
                logger.warning(f"Could not add logo: {e}")
                logo_para.add_run("[LOGO]")
        else:
            # Placeholder for logo
            logo_para = logo_cell.paragraphs[0]
            logo_run = logo_para.add_run("[OUCRU LOGO]")
            logo_run.font.size = self.SMALL_SIZE
            logo_run.font.name = self.FONT_FAMILY
        
        # Cell 0,1: TMG REPORT title
        title_cell = header_table.cell(0, 1)
        title_para = title_cell.paragraphs[0]
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_para.add_run("TMG REPORT")
        title_run.bold = True
        title_run.font.size = Pt(16)
        title_run.font.name = self.FONT_FAMILY
        
        # Cell 0,2: Version info
        version_cell = header_table.cell(0, 2)
        version_para = version_cell.paragraphs[0]
        version_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        version_run = version_para.add_run(f"Version: {self.VERSION}")
        version_run.font.size = self.SMALL_SIZE
        version_run.font.name = self.FONT_FAMILY
        
        # Row 2: Document code & Section | (empty) | Effective date
        # Cell 1,1: Document code & Section
        doc_cell = header_table.cell(1, 1)
        doc_para = doc_cell.paragraphs[0]
        doc_run = doc_para.add_run(f"Document code: {self.DOCUMENT_CODE}\nSection : {self.SECTION}")
        doc_run.font.size = self.SMALL_SIZE
        doc_run.font.name = self.FONT_FAMILY
        
        # Cell 1,2: Effective date
        eff_cell = header_table.cell(1, 2)
        eff_para = eff_cell.paragraphs[0]
        eff_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        eff_run = eff_para.add_run(f"Effective: {self.EFFECTIVE_DATE}")
        eff_run.font.size = self.SMALL_SIZE
        eff_run.font.name = self.FONT_FAMILY
        
        # Add horizontal line after header
        self.document.add_paragraph()
        self._add_horizontal_line()
    
    def _add_horizontal_line(self):
        """Thêm đường kẻ ngang"""
        para = self.document.add_paragraph()
        para_format = para.paragraph_format
        para_format.space_after = Pt(0)
        
        # Create border using XML
        pBdr = OxmlElement('w:pBdr')
        bottom = OxmlElement('w:bottom')
        bottom.set(qn('w:val'), 'single')
        bottom.set(qn('w:sz'), '6')
        bottom.set(qn('w:space'), '1')
        bottom.set(qn('w:color'), '000000')
        pBdr.append(bottom)
        para._p.get_or_add_pPr().append(pBdr)
    
    def _add_title_section(self):
        """
        Thêm title section:
        - Study code: UPDATE REPORT
        - Reporting Date với superscript
        """
        # Main title
        title_para = self.document.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_para.add_run(f"{self.study_code}: UPDATE REPORT")
        title_run.bold = True
        title_run.font.size = Pt(20)
        title_run.font.name = self.FONT_FAMILY
        
        # Reporting date with superscript ordinal
        date_para = self.document.add_paragraph()
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        day = self.reporting_date.day
        month = self.reporting_date.strftime('%b')
        year = self.reporting_date.year
        ordinal = self._get_ordinal_suffix(day)
        
        # "Reporting Date: Dec 1"
        date_run = date_para.add_run(f"Reporting Date: {month} {day}")
        date_run.bold = True
        date_run.font.size = Pt(14)
        date_run.font.name = self.FONT_FAMILY
        
        # Superscript "st/nd/rd/th"
        sup_run = date_para.add_run(ordinal)
        sup_run.bold = True
        sup_run.font.size = Pt(14)
        sup_run.font.name = self.FONT_FAMILY
        sup_run.font.superscript = True
        
        # ", 2025"
        year_run = date_para.add_run(f", {year}")
        year_run.bold = True
        year_run.font.size = Pt(14)
        year_run.font.name = self.FONT_FAMILY
        
        # Add empty paragraph for spacing
        self.document.add_paragraph()
    
    def _get_ordinal_suffix(self, day: int) -> str:
        """Trả về suffix ordinal (st, nd, rd, th) cho ngày"""
        if 11 <= day <= 13:
            return 'th'
        return {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    
    def _add_section_heading(self, number: int, title: str, underline: bool = True):
        """
        Thêm heading cho section
        
        Args:
            number: Số thứ tự section (1-10)
            title: Tiêu đề section
            underline: Có gạch chân không
        """
        para = self.document.add_paragraph()
        
        # Number
        num_run = para.add_run(f"{number}. ")
        num_run.bold = True
        num_run.font.size = self.HEADING_SIZE
        num_run.font.name = self.FONT_FAMILY
        
        # Title
        title_run = para.add_run(title)
        title_run.bold = True
        title_run.font.size = self.HEADING_SIZE
        title_run.font.name = self.FONT_FAMILY
        if underline:
            title_run.underline = True
    
    def _add_action_points_table(self, action_points: list):
        """
        Thêm bảng Outstanding Action Points
        
        Args:
            action_points: List of dicts với keys: action, actioned_by, complete
        """
        table = self.document.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        
        # Header row
        header_cells = table.rows[0].cells
        headers = ['Action Point', 'Actioned by', 'Complete?']
        for i, header in enumerate(headers):
            header_cells[i].paragraphs[0].add_run(header).bold = True
            header_cells[i].paragraphs[0].runs[0].font.size = self.BODY_SIZE
            header_cells[i].paragraphs[0].runs[0].font.name = self.FONT_FAMILY
        
        # Set column widths
        table.columns[0].width = Inches(4)
        table.columns[1].width = Inches(1.5)
        table.columns[2].width = Inches(1)
        
        # Data rows
        if action_points:
            for item in action_points:
                row = table.add_row().cells
                
                # Action Point với bullet
                action_para = row[0].paragraphs[0]
                action_run = action_para.add_run(f"• {item.get('action', '')}")
                action_run.font.size = self.BODY_SIZE
                action_run.font.name = self.FONT_FAMILY
                
                # Actioned by
                by_run = row[1].paragraphs[0].add_run(item.get('actioned_by', ''))
                by_run.font.size = self.BODY_SIZE
                by_run.font.name = self.FONT_FAMILY
                
                # Complete status
                complete_run = row[2].paragraphs[0].add_run(item.get('complete', ''))
                complete_run.font.size = self.BODY_SIZE
                complete_run.font.name = self.FONT_FAMILY
        else:
            # Empty row if no action points
            row = table.add_row().cells
            row[0].paragraphs[0].add_run("No outstanding action points")
        
        self.document.add_paragraph()  # Spacing
    
    def _add_recruitment_table(self, recruitment_data: dict):
        """
        Thêm bảng thống kê recruitment
        
        Args:
            recruitment_data: Dict với các key thống kê
        """
        table = self.document.add_table(rows=6, cols=2)
        table.style = 'Table Grid'
        
        rows_data = [
            ('Total Screened', recruitment_data.get('total_screened', 0)),
            ('Total Enrolled', recruitment_data.get('total_enrolled', 0)),
            ('Total Expected CRFs (sample size x No of forms)', recruitment_data.get('expected_crfs', '')),
            ('Total Received CRF', recruitment_data.get('received_crfs', '')),
            ('Total Entered CRF', recruitment_data.get('entered_crfs', '')),
            ('Queries Generated', recruitment_data.get('queries', '')),
        ]
        
        for i, (label, value) in enumerate(rows_data):
            label_run = table.rows[i].cells[0].paragraphs[0].add_run(label)
            label_run.bold = True
            label_run.font.size = self.BODY_SIZE
            label_run.font.name = self.FONT_FAMILY
            
            value_run = table.rows[i].cells[1].paragraphs[0].add_run(str(value))
            value_run.font.size = self.BODY_SIZE
            value_run.font.name = self.FONT_FAMILY
        
        self.document.add_paragraph()  # Spacing
    
    def _add_deviations_table(self, deviations: list):
        """
        Thêm bảng Protocol Deviations/Violations
        
        Args:
            deviations: List of dicts với keys: subject_id, deviation, violation, action
        """
        table = self.document.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        
        headers = ['Subject ID', 'Deviation description', 'Protocol violation?', 'Action']
        for i, header in enumerate(headers):
            cell = table.rows[0].cells[i]
            run = cell.paragraphs[0].add_run(header)
            run.bold = True
            run.font.size = self.BODY_SIZE
            run.font.name = self.FONT_FAMILY
        
        if deviations:
            for item in deviations:
                row = table.add_row().cells
                row[0].paragraphs[0].add_run(item.get('subject_id', '')).font.size = self.BODY_SIZE
                row[1].paragraphs[0].add_run(item.get('deviation', '')).font.size = self.BODY_SIZE
                row[2].paragraphs[0].add_run(item.get('violation', '')).font.size = self.BODY_SIZE
                row[3].paragraphs[0].add_run(item.get('action', '')).font.size = self.BODY_SIZE
        else:
            # Empty row if no deviations
            row = table.add_row().cells
            row[0].paragraphs[0].add_run("No protocol deviations reported")
        
        self.document.add_paragraph()  # Spacing
    
    def _add_text_content(self, content: str):
        """Thêm nội dung text thông thường"""
        if content:
            para = self.document.add_paragraph()
            run = para.add_run(content)
            run.font.size = self.BODY_SIZE
            run.font.name = self.FONT_FAMILY
        else:
            para = self.document.add_paragraph()
            run = para.add_run("N/A")
            run.font.size = self.BODY_SIZE
            run.font.name = self.FONT_FAMILY
            run.italic = True
        
        self.document.add_paragraph()  # Spacing
    
    def _add_sample_processing_table(self, sample_data: dict):
        """
        Thêm bảng thống kê sample processing
        
        Args:
            sample_data: Dict với các key thống kê mẫu
        """
        table = self.document.add_table(rows=5, cols=3)
        table.style = 'Table Grid'
        
        # Header
        headers = ['Sample Type', 'Patient Samples', 'Contact Samples']
        for i, header in enumerate(headers):
            run = table.rows[0].cells[i].paragraphs[0].add_run(header)
            run.bold = True
            run.font.size = self.BODY_SIZE
            run.font.name = self.FONT_FAMILY
        
        rows_data = [
            ('Stool (Day 0)', sample_data.get('stool_d0_patient', 0), sample_data.get('stool_d0_contact', 0)),
            ('Stool (Day 14)', sample_data.get('stool_d14_patient', 0), sample_data.get('stool_d14_contact', 0)),
            ('Stool (Day 28)', sample_data.get('stool_d28_patient', 0), sample_data.get('stool_d28_contact', 0)),
            ('Blood', sample_data.get('blood_patient', 0), sample_data.get('blood_contact', 0)),
        ]
        
        for i, (sample_type, patient_count, contact_count) in enumerate(rows_data, start=1):
            table.rows[i].cells[0].paragraphs[0].add_run(sample_type).font.size = self.BODY_SIZE
            table.rows[i].cells[1].paragraphs[0].add_run(str(patient_count)).font.size = self.BODY_SIZE
            table.rows[i].cells[2].paragraphs[0].add_run(str(contact_count)).font.size = self.BODY_SIZE
        
        self.document.add_paragraph()  # Spacing
    
    def _add_safety_table(self, safety_data: dict):
        """
        Thêm bảng thống kê Safety Reporting
        
        Args:
            safety_data: Dict với key thống kê AE/SAE
        """
        table = self.document.add_table(rows=4, cols=2)
        table.style = 'Table Grid'
        
        rows_data = [
            ('Total AEs reported', safety_data.get('total_ae', 0)),
            ('Total SAEs reported', safety_data.get('total_sae', 0)),
            ('Deaths', safety_data.get('deaths', 0)),
            ('AEs leading to discontinuation', safety_data.get('ae_discontinuation', 0)),
        ]
        
        for i, (label, value) in enumerate(rows_data):
            label_run = table.rows[i].cells[0].paragraphs[0].add_run(label)
            label_run.bold = True
            label_run.font.size = self.BODY_SIZE
            label_run.font.name = self.FONT_FAMILY
            
            value_run = table.rows[i].cells[1].paragraphs[0].add_run(str(value))
            value_run.font.size = self.BODY_SIZE
            value_run.font.name = self.FONT_FAMILY
        
        self.document.add_paragraph()  # Spacing
    
    def generate(self, report_data: dict, logo_path: str = None) -> BytesIO:
        """
        Tạo báo cáo hoàn chỉnh
        
        Args:
            report_data: Dict chứa tất cả dữ liệu báo cáo
                - action_points: list of dict with action, actioned_by, complete
                - general_procedures: str
                - ethics_regulatory: str
                - study_amendments: str
                - recruitment: dict with stats
                - deviations: list of dict
                - sample_processing: dict with stats
                - data_management: str
                - safety_reporting: dict with stats
                - aob: str
            logo_path: Path to logo image file (optional)
        
        Returns:
            BytesIO object chứa file DOCX
        """
        # Header
        self._add_header(logo_path)
        
        # Title
        self._add_title_section()
        
        # Section 1: Outstanding Action Points
        self._add_section_heading(1, "Outstanding Action Points")
        self._add_action_points_table(report_data.get('action_points', []))
        
        # Section 2: General Trial Procedures
        self._add_section_heading(2, "General Trial Procedures")
        self._add_text_content(report_data.get('general_procedures', ''))
        
        # Section 3: Ethics & Regulatory
        self._add_section_heading(3, "Ethics & Regulatory")
        self._add_text_content("List details of submissions/amendments:")
        self._add_text_content(report_data.get('ethics_regulatory', ''))
        
        # Section 4: Study Amendments
        self._add_section_heading(4, "Study Amendments")
        self._add_text_content(report_data.get('study_amendments', ''))
        
        # Section 5: Recruitment
        self._add_section_heading(5, "Recruitment")
        self._add_recruitment_table(report_data.get('recruitment', {}))
        
        # Section 6: Protocol Deviations/Violations
        self._add_section_heading(6, "Protocol Deviations/Violations")
        self._add_deviations_table(report_data.get('deviations', []))
        
        # Section 7: Sample Processing
        self._add_section_heading(7, "Sample Processing")
        sample_data = report_data.get('sample_processing', {})
        if sample_data:
            self._add_sample_processing_table(sample_data)
        else:
            self._add_text_content(report_data.get('sample_processing_text', ''))
        
        # Section 8: Data Management
        self._add_section_heading(8, "Data Management")
        self._add_text_content(report_data.get('data_management', ''))
        
        # Section 9: Safety Reporting
        self._add_section_heading(9, "Safety Reporting")
        safety_data = report_data.get('safety_reporting', {})
        if safety_data:
            self._add_safety_table(safety_data)
        else:
            self._add_text_content(report_data.get('safety_reporting_text', ''))
        
        # Section 10: AOB
        self._add_section_heading(10, "AOB")
        self._add_text_content(report_data.get('aob', ''))
        
        # Save to BytesIO
        buffer = BytesIO()
        self.document.save(buffer)
        buffer.seek(0)
        return buffer
