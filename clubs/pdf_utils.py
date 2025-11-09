import os
from io import BytesIO
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
import matplotlib

matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from datetime import datetime


def generate_event_pdf_report(event, report):
    """
    Generate comprehensive PDF report with charts for an event
    Returns: PDF file path
    """
    # Create reports directory if it doesn't exist
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"event_report_{event.event_id}_{timestamp}.pdf"
    filepath = os.path.join(reports_dir, filename)

    # Create PDF
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=1 * inch,
        bottomMargin=0.75 * inch
    )

    # Container for PDF elements
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )

    normal_style = styles['Normal']

    # Title
    elements.append(Paragraph("EVENT ATTENDANCE REPORT", title_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Event Information Section
    elements.append(Paragraph("Event Information", heading_style))

    event_data = [
        ['Event Name:', event.event_name],
        ['Club:', event.club.club_name],
        ['Date:', event.event_date.strftime('%B %d, %Y')],
        ['Time:', f"{event.start_time.strftime('%I:%M %p')}"],
        ['Venue:', event.venue or 'Not specified'],
        ['Event Type:', 'Activity Points Event' if event.event_type == 'ACTIVITY_POINTS' else 'Normal Event'],
    ]

    if event.has_activity_points():
        event_data.append(['Activity Points:', f"{event.activity_points} points"])

    event_data.append(['Status:', event.event_status])

    event_table = Table(event_data, colWidths=[2 * inch, 4 * inch])
    event_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
    ]))

    elements.append(event_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Attendance Summary Section
    elements.append(Paragraph("Attendance Summary", heading_style))

    summary = event.get_attendance_summary()
    summary_data = [
        ['Metric', 'Count', 'Percentage'],
        ['Total Registered', str(summary['total_registered']), '100%'],
        ['Present', str(summary['total_present']), f"{report.attendance_percentage:.1f}%"],
        ['Absent', str(summary['total_absent']), f"{100 - report.attendance_percentage:.1f}%"],
        ['Not Marked', str(summary['not_marked']), '-'],
    ]

    summary_table = Table(summary_data, colWidths=[2 * inch, 2 * inch, 2 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Generate Charts
    charts_buffer = generate_attendance_charts(event, summary, report)
    if charts_buffer:
        elements.append(Paragraph("Visual Analysis", heading_style))
        # Add chart image
        img = Image(charts_buffer, width=6 * inch, height=4 * inch)
        elements.append(img)
        elements.append(Spacer(1, 0.3 * inch))

    # Page Break before detailed attendance
    elements.append(PageBreak())

    # Detailed Attendance Section
    elements.append(Paragraph("Detailed Attendance", heading_style))

    # Get attendance data
    from events.models import EventRegistration
    from attendance.models import Attendance

    registrations = EventRegistration.objects.filter(
        event=event,
        registration_status='REGISTERED'
    ).select_related('student').order_by('student__usn')

    attendance_dict = {}
    for att in Attendance.objects.filter(event=event).select_related('student'):
        attendance_dict[att.student_id] = att

    # Build attendance table data
    attendance_table_data = [
        ['S.No', 'USN', 'Student Name', 'Department', 'Status']
    ]

    for idx, reg in enumerate(registrations, 1):
        att = attendance_dict.get(reg.student_id)
        status = att.attendance_status if att else 'Not Marked'

        attendance_table_data.append([
            str(idx),
            reg.student.usn,
            reg.student.get_full_name(),
            reg.student.department or '-',
            status
        ])

    # Create attendance table
    attendance_table = Table(
        attendance_table_data,
        colWidths=[0.5 * inch, 1.2 * inch, 2 * inch, 1.5 * inch, 1 * inch]
    )

    # Style for attendance table
    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # S.No center
        ('ALIGN', (-1, 0), (-1, -1), 'CENTER'),  # Status center
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
    ]

    # Color code status
    for idx, row in enumerate(attendance_table_data[1:], 1):
        if row[4] == 'PRESENT':
            table_style.append(('TEXTCOLOR', (4, idx), (4, idx), colors.HexColor('#059669')))
            table_style.append(('FONTNAME', (4, idx), (4, idx), 'Helvetica-Bold'))
        elif row[4] == 'ABSENT':
            table_style.append(('TEXTCOLOR', (4, idx), (4, idx), colors.HexColor('#dc2626')))
            table_style.append(('FONTNAME', (4, idx), (4, idx), 'Helvetica-Bold'))
        else:
            table_style.append(('TEXTCOLOR', (4, idx), (4, idx), colors.HexColor('#9ca3af')))

    attendance_table.setStyle(TableStyle(table_style))
    elements.append(attendance_table)

    # Footer
    elements.append(Spacer(1, 0.5 * inch))
    footer_text = f"Report Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
    elements.append(Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=normal_style,
        fontSize=9,
        textColor=colors.HexColor('#6b7280'),
        alignment=TA_CENTER
    )))

    elements.append(Paragraph("Event Assistant - Automated Report System", ParagraphStyle(
        'Footer2',
        parent=normal_style,
        fontSize=8,
        textColor=colors.HexColor('#9ca3af'),
        alignment=TA_CENTER
    )))

    # Build PDF
    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)

    # Update report with file path
    report.report_file_path = os.path.join('reports', filename)
    report.save()

    return filepath


def add_page_number(canvas, doc):
    """Add page number to each page"""
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.saveState()
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(colors.HexColor('#6b7280'))
    canvas.drawRightString(7.5 * inch, 0.5 * inch, text)
    canvas.restoreState()


def generate_attendance_charts(event, summary, report):
    """
    Generate charts for attendance visualization
    Returns: BytesIO buffer with chart image
    """
    try:
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        fig.patch.set_facecolor('white')

        # Chart 1: Pie Chart - Attendance Distribution
        sizes = [summary['total_present'], summary['total_absent'], summary['not_marked']]
        labels = ['Present', 'Absent', 'Not Marked']
        colors_pie = ['#10b981', '#ef4444', '#9ca3af']
        explode = (0.1, 0, 0)  # Explode present slice

        # Remove zero values
        sizes_filtered = []
        labels_filtered = []
        colors_filtered = []
        explode_filtered = []
        for i, size in enumerate(sizes):
            if size > 0:
                sizes_filtered.append(size)
                labels_filtered.append(labels[i])
                colors_filtered.append(colors_pie[i])
                explode_filtered.append(explode[i])

        ax1.pie(
            sizes_filtered,
            explode=explode_filtered,
            labels=labels_filtered,
            colors=colors_filtered,
            autopct='%1.1f%%',
            shadow=True,
            startangle=90,
            textprops={'fontsize': 11, 'weight': 'bold'}
        )
        ax1.set_title('Attendance Distribution', fontsize=14, fontweight='bold', pad=20)

        # Chart 2: Bar Chart - Statistics
        categories = ['Registered', 'Present', 'Absent']
        values = [summary['total_registered'], summary['total_present'], summary['total_absent']]
        colors_bar = ['#3b82f6', '#10b981', '#ef4444']

        bars = ax2.bar(categories, values, color=colors_bar, alpha=0.8, edgecolor='black', linewidth=1.2)
        ax2.set_ylabel('Number of Students', fontsize=11, fontweight='bold')
        ax2.set_title('Attendance Statistics', fontsize=14, fontweight='bold', pad=20)
        ax2.set_ylim(0, max(values) * 1.2)

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2.,
                height,
                f'{int(height)}',
                ha='center',
                va='bottom',
                fontsize=11,
                fontweight='bold'
            )

        # Add grid
        ax2.grid(axis='y', alpha=0.3, linestyle='--')
        ax2.set_axisbelow(True)

        # Adjust layout
        plt.tight_layout()

        # Save to buffer
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        plt.close()

        return buffer

    except Exception as e:
        print(f"Error generating charts: {str(e)}")
        return None