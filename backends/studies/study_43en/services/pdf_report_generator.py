# backends/studies/study_43en/services/pdf_report_generator.py
"""
PDF Report Generator Service

Creates TMG reports in PDF format using ReportLab.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    Image, PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
from io import BytesIO
import os
import logging

logger = logging.getLogger(__name__)


class PDFReportGenerator:
    """
    Service class để tạo báo cáo TMG dạng PDF
    """
    
    # Constants
    DOCUMENT_CODE = 'TM-CTU-003'
    VERSION = '4.0'
    SECTION = 'CTU'
    EFFECTIVE_DATE = '06JAN22'
    
    # Colors
    HEADER_BG = colors.Color(0.85, 0.89, 0.95)  # Light blue
    DARK_BLUE = colors.Color(0.03, 0.1, 0.23)
    
    def __init__(self, study_code: str, reporting_date: datetime):
        self.study_code = study_code
        self.reporting_date = reporting_date
        self.styles = getSampleStyleSheet()
        self._setup_styles()
    
    def _setup_styles(self):
        """Setup custom styles"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            alignment=TA_CENTER,
            spaceAfter=6,
        ))
        self.styles.add(ParagraphStyle(
            name='CustomReportDate',
            parent=self.styles['Normal'],
            fontSize=14,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=12,
        ))
        self.styles.add(ParagraphStyle(
            name='CustomSectionHeading',
            parent=self.styles['Heading2'],
            fontSize=12,
            fontName='Helvetica-Bold',
            spaceAfter=6,
            spaceBefore=12,
        ))
        self.styles.add(ParagraphStyle(
            name='CustomBodyText',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
        ))
        self.styles.add(ParagraphStyle(
            name='CustomTableCell',
            parent=self.styles['Normal'],
            fontSize=9,
        ))
    
    def _get_ordinal_suffix(self, day: int) -> str:
        if 11 <= day <= 13:
            return 'th'
        return {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    
    def _create_header(self, logo_path: str = None) -> list:
        """Create header elements"""
        elements = []
        
        # Header table
        header_data = [
            ['[OUCRU LOGO]', 'TMG REPORT', f'Version: {self.VERSION}'],
            ['', f'Document code: {self.DOCUMENT_CODE}\nSection: {self.SECTION}', f'Effective: {self.EFFECTIVE_DATE}'],
        ]
        
        # If logo exists, use it
        if logo_path and os.path.exists(logo_path):
            try:
                img = Image(logo_path, width=3*cm, height=1.5*cm)
                header_data[0][0] = img
            except Exception as e:
                logger.warning(f"Could not load logo: {e}")
        
        header_table = Table(header_data, colWidths=[4*cm, 10*cm, 4*cm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (1, 0), (1, 0), 16),
            ('FONTSIZE', (0, 0), (0, 0), 10),
            ('FONTSIZE', (2, 0), (2, -1), 9),
            ('FONTSIZE', (1, 1), (1, 1), 9),
            ('SPAN', (0, 0), (0, 1)),
        ]))
        
        elements.append(header_table)
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=10, spaceAfter=10))
        
        return elements
    
    def _create_title_section(self) -> list:
        """Create title section"""
        elements = []
        
        # Main title
        title = Paragraph(f"<b>{self.study_code}: UPDATE REPORT</b>", self.styles['CustomTitle'])
        elements.append(title)
        
        # Reporting date
        day = self.reporting_date.day
        month = self.reporting_date.strftime('%b')
        year = self.reporting_date.year
        ordinal = self._get_ordinal_suffix(day)
        
        date_text = f"Reporting Date: {month} {day}<super>{ordinal}</super>, {year}"
        date_para = Paragraph(f"<b>{date_text}</b>", self.styles['CustomReportDate'])
        elements.append(date_para)
        elements.append(Spacer(1, 12))
        
        return elements
    
    def _create_section_heading(self, number: int, title: str) -> Paragraph:
        """Create section heading"""
        return Paragraph(f"<b><u>{number}. {title}</u></b>", self.styles['CustomSectionHeading'])
    
    def _create_text_content(self, content: str) -> Paragraph:
        """Create text paragraph"""
        if content:
            return Paragraph(content, self.styles['CustomBodyText'])
        else:
            return Paragraph("<i>N/A</i>", self.styles['CustomBodyText'])
    
    def _create_action_points_table(self, action_points: list) -> Table:
        """Create action points table"""
        data = [['Action Point', 'Actioned by', 'Complete?']]
        
        if action_points:
            for item in action_points:
                data.append([
                    f"• {item.get('action', '')}",
                    item.get('actioned_by', ''),
                    item.get('complete', '')
                ])
        else:
            data.append(['No outstanding action points', '', ''])
        
        table = Table(data, colWidths=[10*cm, 4*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.HEADER_BG),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        return table
    
    def _create_recruitment_table(self, recruitment_data: dict) -> Table:
        """Create recruitment table"""
        data = [
            ['Category', 'Patients', 'Contacts'],
            ['Total Screened', 
             str(recruitment_data.get('total_screened_patients', 0)),
             str(recruitment_data.get('total_screened_contacts', 0))],
            ['Total Enrolled', 
             str(recruitment_data.get('total_enrolled_patients', 0)),
             str(recruitment_data.get('total_enrolled_contacts', 0))],
        ]
        
        table = Table(data, colWidths=[6*cm, 4*cm, 4*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.HEADER_BG),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        return table
    
    def _create_sample_processing_table(self, sample_data: dict) -> Table:
        """Create sample processing table"""
        data = [['Schedule', 'Patient Total', 'Patient Blood', 'Contact Total', 'Contact Blood']]
        
        patient_stats = sample_data.get('patient', {})
        contact_stats = sample_data.get('contact', {})
        
        schedules = [
            ('Day 1 (Enrollment)', 'visit1'),
            ('Day 10 (±3 days)', 'visit2'),
            ('Day 28 (±3 days)', 'visit3'),
            ('Day 90 (±3 days)', 'visit4'),
        ]
        
        for schedule_name, visit_key in schedules:
            p_data = patient_stats.get(visit_key, {})
            c_data = contact_stats.get(visit_key, {})
            
            p_total = str(p_data.get('total', 0)) if p_data else '0'
            p_blood = str(p_data.get('blood', 0)) if p_data else '0'
            
            if visit_key == 'visit2':
                c_total = 'N/A'
                c_blood = 'N/A'
            else:
                c_total = str(c_data.get('total', 0)) if c_data else '0'
                c_blood = str(c_data.get('blood', 0)) if c_data else '0'
            
            data.append([schedule_name, p_total, p_blood, c_total, c_blood])
        
        table = Table(data, colWidths=[4.5*cm, 3*cm, 3*cm, 3*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.HEADER_BG),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        return table
    
    def _create_deviations_table(self, deviations: list) -> Table:
        """Create protocol deviations table"""
        data = [['Subject ID', 'Deviation description', 'Violation?', 'Action']]
        
        if deviations:
            for item in deviations:
                data.append([
                    item.get('subject_id', ''),
                    item.get('deviation', ''),
                    item.get('violation', ''),
                    item.get('action', '')
                ])
        else:
            data.append(['No protocol deviations reported', '', '', ''])
        
        table = Table(data, colWidths=[3*cm, 7*cm, 2.5*cm, 4*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.HEADER_BG),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        return table
    
    def _create_safety_table(self, safety_data: dict) -> Table:
        """Create safety reporting table"""
        data = [
            ['Category', 'Count'],
            ['Total AEs reported', str(safety_data.get('total_ae', 0))],
            ['Total SAEs reported', str(safety_data.get('total_sae', 0))],
            ['Deaths', str(safety_data.get('deaths', 0))],
            ['AEs leading to discontinuation', str(safety_data.get('ae_discontinuation', 0))],
        ]
        
        table = Table(data, colWidths=[10*cm, 4*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.HEADER_BG),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        return table
    
    def generate(self, report_data: dict, logo_path: str = None) -> BytesIO:
        """Generate complete PDF report"""
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2*cm,
            rightMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )
        
        elements = []
        
        # Header
        elements.extend(self._create_header(logo_path))
        
        # Title
        elements.extend(self._create_title_section())
        
        # Section 1: Outstanding Action Points
        elements.append(self._create_section_heading(1, "Outstanding Action Points"))
        elements.append(self._create_action_points_table(report_data.get('action_points', [])))
        elements.append(Spacer(1, 12))
        
        # Section 2: General Trial Procedures
        elements.append(self._create_section_heading(2, "General Trial Procedures"))
        elements.append(self._create_text_content(report_data.get('general_procedures', '')))
        
        # Section 3: Ethics & Regulatory
        elements.append(self._create_section_heading(3, "Ethics & Regulatory"))
        elements.append(self._create_text_content(report_data.get('ethics_regulatory', '')))
        
        # Section 4: Study Amendments
        elements.append(self._create_section_heading(4, "Study Amendments"))
        elements.append(self._create_text_content(report_data.get('study_amendments', '')))
        
        # Section 5: Recruitment
        elements.append(self._create_section_heading(5, "Recruitment"))
        elements.append(self._create_recruitment_table(report_data.get('recruitment', {})))
        elements.append(Spacer(1, 12))
        
        # Section 6: Protocol Deviations/Violations
        elements.append(self._create_section_heading(6, "Protocol Deviations/Violations"))
        elements.append(self._create_deviations_table(report_data.get('deviations', [])))
        elements.append(Spacer(1, 12))
        
        # Section 7: Sample Processing
        elements.append(self._create_section_heading(7, "Sample Processing"))
        sample_data = report_data.get('sample_processing', {})
        if sample_data and (sample_data.get('patient') or sample_data.get('contact')):
            elements.append(self._create_sample_processing_table(sample_data))
        else:
            elements.append(self._create_text_content(''))
        elements.append(Spacer(1, 12))
        
        # Section 8: Data Management
        elements.append(self._create_section_heading(8, "Data Management"))
        elements.append(self._create_text_content(report_data.get('data_management', '')))
        
        # Section 9: Safety Reporting
        elements.append(self._create_section_heading(9, "Safety Reporting"))
        safety_data = report_data.get('safety_reporting', {})
        if safety_data:
            elements.append(self._create_safety_table(safety_data))
        else:
            elements.append(self._create_text_content(''))
        elements.append(Spacer(1, 12))
        
        # Section 10: AOB
        elements.append(self._create_section_heading(10, "AOB"))
        elements.append(self._create_text_content(report_data.get('aob', '')))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer
