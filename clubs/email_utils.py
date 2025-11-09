from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import os


def send_event_report_email(event, report, pdf_path=None):
    """
    Send comprehensive event report to club head via email with PDF attachment
    """
    club = event.club
    club_head = club.club_head

    if not club_head:
        print("No club head assigned to send report")
        return False

    # Get attendance summary
    summary = event.get_attendance_summary()

    # Get all registered students with their attendance
    from events.models import EventRegistration
    from attendance.models import Attendance

    registrations = EventRegistration.objects.filter(
        event=event,
        registration_status='REGISTERED'
    ).select_related('student').order_by('student__usn')

    attendance_dict = {}
    for att in Attendance.objects.filter(event=event).select_related('student'):
        attendance_dict[att.student_id] = att

    # Build attendance list
    attendance_list = []
    for reg in registrations:
        att = attendance_dict.get(reg.student_id)
        attendance_list.append({
            'usn': reg.student.usn,
            'name': reg.student.get_full_name(),
            'department': reg.student.department,
            'status': att.attendance_status if att else 'Not Marked',
            'marked_at': att.marked_at if att else None
        })

    # Subject
    subject = f'Event Report: {event.event_name} - {club.club_name}'

    # Plain text version
    text_content = generate_text_report(event, report, summary, attendance_list)

    # HTML version
    html_content = generate_html_report(event, report, summary, attendance_list)

    # Create email
    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[club_head.email]
        )

        # Attach HTML version
        email.attach_alternative(html_content, "text/html")

        # Attach PDF if provided
        if pdf_path:
            try:
                # Check if file exists
                if os.path.exists(pdf_path):
                    filename = f'Event_Report_{event.event_name.replace(" ", "_")}.pdf'
                    with open(pdf_path, 'rb') as pdf_file:
                        email.attach(filename, pdf_file.read(), 'application/pdf')
                    print(f"PDF attached: {filename}")
                else:
                    print(f"PDF file not found at: {pdf_path}")
            except Exception as e:
                print(f"Failed to attach PDF: {str(e)}")
        else:
            print("No PDF path provided")

        # Send
        email.send()

        # Update report with sent status
        report.report_sent_to = club_head.email
        report.save()

        print(f"Report sent successfully to {club_head.email}")
        return True

    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False


def generate_text_report(event, report, summary, attendance_list):
    """Generate plain text report"""

    text = f"""
EVENT REPORT
{'=' * 60}

Event Details:
--------------
Event Name: {event.event_name}
Club: {event.club.club_name}
Date: {event.event_date.strftime('%B %d, %Y')}
Time: {event.start_time.strftime('%I:%M %p')}
Venue: {event.venue or 'Not specified'}
Event Type: {'Activity Points Event' if event.event_type == 'ACTIVITY_POINTS' else 'Normal Event'}
"""

    if event.has_activity_points():
        text += f"Activity Points: {event.activity_points}\n"

    text += f"""
Event Status:
-------------
Started At: {event.event_started_at.strftime('%B %d, %Y %I:%M %p') if event.event_started_at else 'N/A'}
Ended At: {event.event_ended_at.strftime('%B %d, %Y %I:%M %p') if event.event_ended_at else 'N/A'}

Attendance Summary:
-------------------
Total Registered: {summary['total_registered']}
Total Present: {summary['total_present']}
Total Absent: {summary['total_absent']}
Not Marked: {summary['not_marked']}
Attendance Rate: {report.attendance_percentage:.1f}%

Detailed Attendance:
--------------------
{'USN':<15} {'Name':<30} {'Department':<20} {'Status':<10}
{'-' * 80}
"""

    for att in attendance_list:
        text += f"{att['usn']:<15} {att['name']:<30} {att['department']:<20} {att['status']:<10}\n"

    text += f"""
{'-' * 80}

Report Generated: {timezone.now().strftime('%B %d, %Y at %I:%M %p')}

This is an automated report from Event Assistant.
For any queries, please contact the faculty in-charge.

Best regards,
Event Assistant Team
"""

    return text


def generate_html_report(event, report, summary, attendance_list):
    """Generate HTML formatted report"""

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #2563eb, #1e40af);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 28px;
        }}
        .header p {{
            margin: 5px 0;
            opacity: 0.9;
        }}
        .section {{
            background-color: #f9fafb;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #2563eb;
        }}
        .section h2 {{
            margin-top: 0;
            color: #1f2937;
            font-size: 20px;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 10px;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e5e7eb;
        }}
        .info-label {{
            font-weight: 600;
            color: #4b5563;
        }}
        .info-value {{
            color: #1f2937;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-card {{
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{
            margin: 0 0 10px 0;
            font-size: 32px;
            color: #2563eb;
        }}
        .stat-card p {{
            margin: 0;
            color: #6b7280;
            font-size: 14px;
            text-transform: uppercase;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background-color: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        thead {{
            background-color: #f3f4f6;
        }}
        th {{
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #374151;
            border-bottom: 2px solid #e5e7eb;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
        }}
        tr:hover {{
            background-color: #f9fafb;
        }}
        .status-present {{
            color: #059669;
            font-weight: 600;
        }}
        .status-absent {{
            color: #dc2626;
            font-weight: 600;
        }}
        .status-not-marked {{
            color: #9ca3af;
            font-style: italic;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge-activity {{
            background-color: #fef3c7;
            color: #92400e;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #e5e7eb;
            text-align: center;
            color: #6b7280;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Event Report</h1>
        <p><strong>{event.event_name}</strong></p>
        <p>{event.club.club_name}</p>
    </div>

    <div class="section">
        <h2>Event Details</h2>
        <div class="info-row">
            <span class="info-label">Event Name:</span>
            <span class="info-value">{event.event_name}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Date:</span>
            <span class="info-value">{event.event_date.strftime('%B %d, %Y')}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Time:</span>
            <span class="info-value">{event.start_time.strftime('%I:%M %p')}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Venue:</span>
            <span class="info-value">{event.venue or 'Not specified'}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Event Type:</span>
            <span class="info-value">
                {'Activity Points Event' if event.event_type == 'ACTIVITY_POINTS' else 'Normal Event'}
                {f'<span class="badge badge-activity">⭐ {event.activity_points} Points</span>' if event.has_activity_points() else ''}
            </span>
        </div>
    </div>

    <div class="section">
        <h2>Attendance Summary</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h3>{summary['total_registered']}</h3>
                <p>Total Registered</p>
            </div>
            <div class="stat-card">
                <h3>{summary['total_present']}</h3>
                <p>Present</p>
            </div>
            <div class="stat-card">
                <h3>{summary['total_absent']}</h3>
                <p>Absent</p>
            </div>
            <div class="stat-card">
                <h3>{report.attendance_percentage:.1f}%</h3>
                <p>Attendance Rate</p>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Detailed Attendance</h2>
        <table>
            <thead>
                <tr>
                    <th>USN</th>
                    <th>Student Name</th>
                    <th>Department</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
"""

    for att in attendance_list:
        status_class = 'status-not-marked'
        if att['status'] == 'PRESENT':
            status_class = 'status-present'
        elif att['status'] == 'ABSENT':
            status_class = 'status-absent'

        html += f"""
                <tr>
                    <td>{att['usn']}</td>
                    <td>{att['name']}</td>
                    <td>{att['department']}</td>
                    <td class="{status_class}">{att['status']}</td>
                </tr>
"""

    html += f"""
            </tbody>
        </table>
    </div>

    <div class="footer">
        <p><strong>Report Generated:</strong> {timezone.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        <p>This is an automated report from Event Assistant.</p>
        <p>For any queries, please contact the faculty in-charge.</p>
    </div>
</body>
</html>
"""

    return html


def send_club_member_welcome_email(student, club, club_login_id, club_password, role_name):
    """
    Send welcome email to new club member with credentials
    """
    subject = f'Welcome to {club.club_name} - Login Credentials'

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #2563eb, #1e40af);
            color: white;
            padding: 30px;
            border-radius: 8px;
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .content {{
            background-color: #f9fafb;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .credentials {{
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #2563eb;
            margin: 20px 0;
        }}
        .credential-row {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #e5e7eb;
        }}
        .credential-label {{
            font-weight: 600;
            color: #4b5563;
        }}
        .credential-value {{
            color: #1f2937;
            font-family: monospace;
            background-color: #f3f4f6;
            padding: 4px 8px;
            border-radius: 4px;
        }}
        .role-badge {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            background-color: #fef3c7;
            color: #92400e;
            margin: 10px 0;
        }}
        .btn {{
            display: inline-block;
            padding: 12px 24px;
            background-color: #2563eb;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin-top: 20px;
        }}
        .warning {{
            background-color: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            color: #6b7280;
            font-size: 14px;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎉 Welcome to {club.club_name}!</h1>
    </div>

    <div class="content">
        <p>Dear <strong>{student.get_full_name()}</strong>,</p>

        <p>Congratulations! You have been added to <strong>{club.club_name}</strong> as a club member.</p>

        <div class="role-badge">
            Your Role: {role_name}
        </div>

        <p>Your club login credentials are:</p>

        <div class="credentials">
            <div class="credential-row">
                <span class="credential-label">Login ID:</span>
                <span class="credential-value">{club_login_id}</span>
            </div>
            <div class="credential-row">
                <span class="credential-label">Password:</span>
                <span class="credential-value">{club_password}</span>
            </div>
        </div>

        <div class="warning">
            <strong>⚠️ Important:</strong> Please keep your credentials secure and change your password after first login.
        </div>

        <p>You can now login to the club portal and start managing events!</p>

        <center>
            <a href="{settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'http://localhost:8000'}/club/login/" class="btn">
                Login to Club Portal
            </a>
        </center>

        <p style="margin-top: 30px;">If you have any questions, please contact your club head or faculty in-charge.</p>
    </div>

    <div class="footer">
        <p>Best regards,<br>Event Assistant Team</p>
        <p style="font-size: 12px; margin-top: 20px;">This is an automated email. Please do not reply.</p>
    </div>
</body>
</html>
"""

    text_content = f"""
Welcome to {club.club_name}!

Dear {student.get_full_name()},

You have been added to {club.club_name} as a {role_name}.

Your club login credentials are:
Login ID: {club_login_id}
Password: {club_password}

Please keep your credentials secure and change your password after first login.

Login URL: {settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'http://localhost:8000'}/club/login/

Best regards,
Event Assistant Team
"""

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[student.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        return True
    except Exception as e:
        print(f"Failed to send welcome email: {str(e)}")
        return False