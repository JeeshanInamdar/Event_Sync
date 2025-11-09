from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from .models import ClubMember, Club
from events.models import Event, EventEditHistory
from datetime import datetime
import os


def club_login(request):
    """Club member login view"""
    # If already logged in, redirect to dashboard
    if request.session.get('club_member_id'):
        return redirect('club_dashboard')

    if request.method == 'POST':
        club_login_id = request.POST.get('club_login_id', '').strip().lower()
        password = request.POST.get('password', '')

        try:
            # Find club member by login ID
            member = ClubMember.objects.select_related('club', 'student', 'role').get(
                club_login_id=club_login_id,
                is_active=True
            )

            # Check password
            if member.check_club_password(password):
                # Set session
                request.session['club_member_id'] = member.member_id
                request.session['club_id'] = member.club.club_id
                request.session['club_name'] = member.club.club_name
                request.session['member_name'] = member.student.get_full_name()
                request.session['member_role'] = member.role.role_name
                request.session['user_type'] = 'club_member'

                messages.success(request, f'Welcome, {member.student.first_name}!')
                return redirect('club_dashboard')
            else:
                messages.error(request, 'Invalid login ID or password')

        except ClubMember.DoesNotExist:
            messages.error(request, 'Invalid login ID or password')

    return render(request, 'clubs/login.html')


def club_logout(request):
    """Club member logout view"""
    # Clear session
    session_keys = ['club_member_id', 'club_id', 'club_name', 'member_name', 'member_role', 'user_type']
    for key in session_keys:
        if key in request.session:
            del request.session[key]

    messages.success(request, 'You have been logged out successfully')
    return redirect('club_login')


def club_dashboard(request):
    """Club member dashboard view"""
    # Check if logged in
    if not request.session.get('club_member_id'):
        messages.warning(request, 'Please login to access dashboard')
        return redirect('club_login')

    member_id = request.session.get('club_member_id')
    member = ClubMember.objects.select_related('club', 'student', 'role').get(member_id=member_id)

    # Get club events
    events = Event.objects.filter(club=member.club).order_by('-event_date')

    # Separate events
    upcoming_events = events.filter(
        event_status='SCHEDULED',
        event_date__gte=timezone.now().date()
    )

    ongoing_events = events.filter(event_status='ONGOING')
    completed_events = events.filter(event_status='COMPLETED')

    # Get club members count
    members_count = ClubMember.objects.filter(club=member.club, is_active=True).count()

    context = {
        'member': member,
        'club': member.club,
        'upcoming_events': upcoming_events,
        'ongoing_events': ongoing_events,
        'completed_events': completed_events,
        'total_events': events.count(),
        'members_count': members_count,
    }

    return render(request, 'clubs/dashboard.html', context)


def create_event(request):
    """Create a new event"""
    # Check if logged in
    if not request.session.get('club_member_id'):
        messages.warning(request, 'Please login first')
        return redirect('club_login')

    member_id = request.session.get('club_member_id')
    member = ClubMember.objects.select_related('club', 'role').get(member_id=member_id)

    # Check permission
    if not member.has_permission('create_events'):
        messages.error(request, 'You do not have permission to create events')
        return redirect('club_dashboard')

    if request.method == 'POST':
        try:
            # Get form data
            event_name = request.POST.get('event_name', '').strip()
            event_description = request.POST.get('event_description', '').strip()
            event_type = request.POST.get('event_type', 'NORMAL')
            activity_points = request.POST.get('activity_points', '').strip()
            event_date = request.POST.get('event_date', '')
            start_time = request.POST.get('start_time', '')
            end_time = request.POST.get('end_time', '').strip()
            venue = request.POST.get('venue', '').strip()
            max_participants = request.POST.get('max_participants', '').strip()

            # Validation
            if not all([event_name, event_date, start_time]):
                messages.error(request, 'Please fill all required fields')
                return redirect('create_event')

            # Validate event date is not in the past
            event_date_obj = datetime.strptime(event_date, '%Y-%m-%d').date()
            if event_date_obj < timezone.now().date():
                messages.error(request, 'Event date cannot be in the past')
                return redirect('create_event')

            # Create event
            event = Event(
                club=member.club,
                event_name=event_name,
                event_description=event_description if event_description else None,
                event_type=event_type,
                event_date=event_date,
                start_time=start_time,
                end_time=end_time if end_time else None,
                venue=venue if venue else None,
                max_participants=int(max_participants) if max_participants else None,
                created_by=member,
                event_status='SCHEDULED'
            )

            # Set activity points if event type is ACTIVITY_POINTS
            if event_type == 'ACTIVITY_POINTS':
                if not activity_points:
                    messages.error(request, 'Activity points are required for activity points events')
                    return redirect('create_event')
                event.activity_points = int(activity_points)

            # Validate
            event.full_clean()
            event.save()

            messages.success(request, f'Event "{event_name}" created successfully!')
            return redirect('club_dashboard')

        except ValidationError as e:
            messages.error(request, f'Validation error: {e}')
        except Exception as e:
            messages.error(request, f'Error creating event: {str(e)}')

    context = {
        'member': member,
        'club': member.club,
    }

    return render(request, 'clubs/create_event.html', context)


def edit_event(request, event_id):
    """Edit an existing event"""
    # Check if logged in
    if not request.session.get('club_member_id'):
        messages.warning(request, 'Please login first')
        return redirect('club_login')

    member_id = request.session.get('club_member_id')
    member = ClubMember.objects.select_related('club', 'role').get(member_id=member_id)

    # Check permission
    if not member.has_permission('edit_events'):
        messages.error(request, 'You do not have permission to edit events')
        return redirect('club_dashboard')

    # Get event
    event = get_object_or_404(Event, event_id=event_id, club=member.club)

    # Cannot edit completed or cancelled events
    if event.event_status in ['COMPLETED', 'CANCELLED']:
        messages.error(request, 'Cannot edit completed or cancelled events')
        return redirect('club_dashboard')

    if request.method == 'POST':
        try:
            # Track changes for history
            changes = []

            # Get form data
            event_name = request.POST.get('event_name', '').strip()
            event_description = request.POST.get('event_description', '').strip()
            event_type = request.POST.get('event_type', 'NORMAL')
            activity_points = request.POST.get('activity_points', '').strip()
            event_date = request.POST.get('event_date', '')
            start_time = request.POST.get('start_time', '')
            end_time = request.POST.get('end_time', '').strip()
            venue = request.POST.get('venue', '').strip()
            max_participants = request.POST.get('max_participants', '').strip()

            # Track changes
            if event.event_name != event_name:
                changes.append(('event_name', event.event_name, event_name))
                event.event_name = event_name

            if event.event_description != event_description:
                changes.append(('event_description', event.event_description, event_description))
                event.event_description = event_description if event_description else None

            if str(event.event_date) != event_date:
                changes.append(('event_date', str(event.event_date), event_date))
                event.event_date = event_date

            if str(event.start_time) != start_time:
                changes.append(('start_time', str(event.start_time), start_time))
                event.start_time = start_time

            if str(event.end_time or '') != (end_time or ''):
                changes.append(('end_time', str(event.end_time or ''), end_time or ''))
                event.end_time = end_time if end_time else None

            if (event.venue or '') != venue:
                changes.append(('venue', event.venue or '', venue))
                event.venue = venue if venue else None

            # Handle activity points
            if event_type == 'ACTIVITY_POINTS':
                if not activity_points:
                    messages.error(request, 'Activity points are required for activity points events')
                    return render(request, 'clubs/edit_event.html', {'member': member, 'event': event})

                new_points = int(activity_points)
                if event.activity_points != new_points:
                    changes.append(('activity_points', str(event.activity_points or ''), str(new_points)))
                    event.activity_points = new_points

            event.event_type = event_type
            event.max_participants = int(max_participants) if max_participants else None
            event.last_edited_by = member
            event.last_edited_at = timezone.now()

            # Validate and save
            event.full_clean()
            event.save()

            # Log changes to history
            for field_name, old_value, new_value in changes:
                EventEditHistory.objects.create(
                    event=event,
                    edited_by=member,
                    field_changed=field_name,
                    old_value=old_value,
                    new_value=new_value
                )

            messages.success(request, f'Event "{event_name}" updated successfully!')
            return redirect('club_dashboard')

        except ValidationError as e:
            messages.error(request, f'Validation error: {e}')
        except Exception as e:
            messages.error(request, f'Error updating event: {str(e)}')

    context = {
        'member': member,
        'event': event,
    }

    return render(request, 'clubs/edit_event.html', context)


def delete_event(request, event_id):
    """Delete an event"""
    # Check if logged in
    if not request.session.get('club_member_id'):
        messages.warning(request, 'Please login first')
        return redirect('club_login')

    member_id = request.session.get('club_member_id')
    member = ClubMember.objects.select_related('club', 'role').get(member_id=member_id)

    # Check permission
    if not member.has_permission('delete_events'):
        messages.error(request, 'You do not have permission to delete events')
        return redirect('club_dashboard')

    # Get event
    event = get_object_or_404(Event, event_id=event_id, club=member.club)

    # Cannot delete ongoing or completed events
    if event.event_status in ['ONGOING', 'COMPLETED']:
        messages.error(request, 'Cannot delete ongoing or completed events')
        return redirect('club_dashboard')

    event_name = event.event_name
    event.delete()

    messages.success(request, f'Event "{event_name}" deleted successfully!')
    return redirect('club_dashboard')


def start_event(request, event_id):
    """Start an event"""
    # Check if logged in
    if not request.session.get('club_member_id'):
        messages.warning(request, 'Please login first')
        return redirect('club_login')

    member_id = request.session.get('club_member_id')
    member = ClubMember.objects.select_related('club', 'role').get(member_id=member_id)

    # Check permission
    if not member.has_permission('start_events'):
        messages.error(request, 'You do not have permission to start events')
        return redirect('club_dashboard')

    # Get event
    event = get_object_or_404(Event, event_id=event_id, club=member.club)

    if event.event_status != 'SCHEDULED':
        messages.error(request, 'Only scheduled events can be started')
        return redirect('club_dashboard')

    # Start event
    event.event_status = 'ONGOING'
    event.event_started_at = timezone.now()
    event.started_by = member
    event.save()

    messages.success(request, f'Event "{event.event_name}" has been started!')
    return redirect('event_attendance', event_id=event_id)


def end_event(request, event_id):
    """End an event"""
    # Check if logged in
    if not request.session.get('club_member_id'):
        messages.warning(request, 'Please login first')
        return redirect('club_login')

    member_id = request.session.get('club_member_id')
    member = ClubMember.objects.select_related('club', 'role').get(member_id=member_id)

    # Check permission
    if not member.has_permission('end_events'):
        messages.error(request, 'You do not have permission to end events')
        return redirect('club_dashboard')

    # Get event
    event = get_object_or_404(Event, event_id=event_id, club=member.club)

    if event.event_status != 'ONGOING':
        messages.error(request, 'Only ongoing events can be ended')
        return redirect('club_dashboard')

    # End event
    event.event_status = 'COMPLETED'
    event.event_ended_at = timezone.now()
    event.ended_by = member
    event.save()

    # Generate report
    from attendance.models import EventReport
    report = EventReport.generate_report(event)

    # Generate PDF report
    from .pdf_utils import generate_event_pdf_report
    pdf_path = None
    try:
        pdf_path = generate_event_pdf_report(event, report)
        print(f"PDF generated at: {pdf_path}")  # Debug print
        messages.success(request, f'PDF report generated successfully!')
    except Exception as e:
        print(f"PDF generation error: {str(e)}")  # Debug print
        messages.warning(request, f'PDF generation failed: {str(e)}')

    # Send email report to club head with PDF attachment
    from .email_utils import send_event_report_email
    print(f"Sending email with PDF path: {pdf_path}")  # Debug print
    email_sent = send_event_report_email(event, report, pdf_path)

    if email_sent:
        if pdf_path:
            messages.success(
                request,
                f'Event "{event.event_name}" completed! Report sent to club head with PDF attachment.'
            )
        else:
            messages.success(
                request,
                f'Event "{event.event_name}" completed! Report sent to club head (PDF generation failed).'
            )
    else:
        messages.success(
            request,
            f'Event "{event.event_name}" completed! Report generated.'
        )
        messages.warning(request, 'Failed to send email report. Check email settings.')

    return redirect('club_dashboard')


def event_attendance(request, event_id):
    """Mark attendance for an event"""
    # Check if logged in
    if not request.session.get('club_member_id'):
        messages.warning(request, 'Please login first')
        return redirect('club_login')

    member_id = request.session.get('club_member_id')
    member = ClubMember.objects.select_related('club', 'role').get(member_id=member_id)

    # Check permission
    if not member.has_permission('mark_attendance'):
        messages.error(request, 'You do not have permission to mark attendance')
        return redirect('club_dashboard')

    # Get event
    event = get_object_or_404(Event, event_id=event_id, club=member.club)

    # Only ongoing events can have attendance marked
    if event.event_status != 'ONGOING':
        messages.error(request, 'Attendance can only be marked for ongoing events')
        return redirect('club_dashboard')

    # Get registered students
    from events.models import EventRegistration
    from attendance.models import Attendance

    registrations = EventRegistration.objects.filter(
        event=event,
        registration_status='REGISTERED'
    ).select_related('student').order_by('student__first_name')

    # Get existing attendance records
    attendance_records = Attendance.objects.filter(event=event)
    attendance_dict = {att.student_id: att for att in attendance_records}

    # Handle form submission
    if request.method == 'POST':
        for registration in registrations:
            attendance_status = request.POST.get(f'attendance_{registration.student_id}')

            if attendance_status in ['PRESENT', 'ABSENT']:
                # Create or update attendance
                attendance, created = Attendance.objects.get_or_create(
                    event=event,
                    student=registration.student,
                    defaults={
                        'marked_by': member,
                        'attendance_status': attendance_status
                    }
                )

                if not created:
                    attendance.attendance_status = attendance_status
                    attendance.marked_by = member
                    attendance.save()

        messages.success(request, 'Attendance marked successfully!')
        return redirect('event_attendance', event_id=event_id)

    # Prepare data for template
    attendance_data = []
    for registration in registrations:
        existing_attendance = attendance_dict.get(registration.student_id)
        attendance_data.append({
            'registration': registration,
            'student': registration.student,
            'attendance': existing_attendance
        })

    context = {
        'member': member,
        'event': event,
        'attendance_data': attendance_data,
    }

    return render(request, 'clubs/event_attendance.html', context)


def download_event_report(request, event_id):
    """Download PDF report for an event"""
    # Check if logged in
    if not request.session.get('club_member_id'):
        messages.warning(request, 'Please login first')
        return redirect('club_login')

    member_id = request.session.get('club_member_id')
    member = ClubMember.objects.select_related('club', 'role').get(member_id=member_id)

    # Check permission
    if not member.has_permission('view_reports'):
        messages.error(request, 'You do not have permission to view reports')
        return redirect('club_dashboard')

    # Get event
    event = get_object_or_404(Event, event_id=event_id, club=member.club)

    # Get or generate report
    from attendance.models import EventReport
    report = EventReport.objects.filter(event=event).first()

    if not report:
        report = EventReport.generate_report(event)

    # Check if PDF exists
    if report.report_file_path:
        pdf_path = os.path.join(settings.MEDIA_ROOT, report.report_file_path)
        if os.path.exists(pdf_path):
            from django.http import FileResponse
            return FileResponse(
                open(pdf_path, 'rb'),
                as_attachment=True,
                filename=f'Event_Report_{event.event_name.replace(" ", "_")}.pdf'
            )

    # Generate new PDF if doesn't exist
    from .pdf_utils import generate_event_pdf_report
    try:
        pdf_path = generate_event_pdf_report(event, report)
        from django.http import FileResponse
        return FileResponse(
            open(pdf_path, 'rb'),
            as_attachment=True,
            filename=f'Event_Report_{event.event_name.replace(" ", "_")}.pdf'
        )
    except Exception as e:
        messages.error(request, f'Failed to generate PDF: {str(e)}')
        return redirect('club_dashboard')


def club_member_profile(request):
    """View and edit club member profile"""
    # Check if logged in
    if not request.session.get('club_member_id'):
        messages.warning(request, 'Please login to access profile')
        return redirect('club_login')

    member_id = request.session.get('club_member_id')
    member = ClubMember.objects.select_related('club', 'student', 'role').get(member_id=member_id)
    student = member.student

    if request.method == 'POST':
        try:
            # Get form data
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip().lower()
            phone = request.POST.get('phone', '').strip()
            department = request.POST.get('department', '')

            # Validation
            if not all([first_name, last_name, email, department]):
                messages.error(request, 'Please fill all required fields')
                return redirect('club_member_profile')

            # Check if email already exists for another student
            from students.models import Student
            if Student.objects.exclude(student_id=student.student_id).filter(email=email).exists():
                messages.error(request, 'Email already exists')
                return redirect('club_member_profile')

            # Update student details
            student.first_name = first_name
            student.last_name = last_name
            student.email = email
            student.phone = phone if phone else None
            student.department = department

            student.save()

            # Update session name
            request.session['member_name'] = student.get_full_name()

            messages.success(request, 'Profile updated successfully!')
            return redirect('club_member_profile')

        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')

    context = {
        'member': member,
        'student': student
    }

    return render(request, 'clubs/profile.html', context)


def club_member_change_password(request):
    """Change club member's club password (not student password)"""
    # Check if logged in
    if not request.session.get('club_member_id'):
        messages.warning(request, 'Please login to change password')
        return redirect('club_login')

    member_id = request.session.get('club_member_id')
    member = ClubMember.objects.select_related('club', 'student').get(member_id=member_id)

    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # Validation
        if not all([current_password, new_password, confirm_password]):
            messages.error(request, 'All fields are required')
            return redirect('club_member_change_password')

        # Check current password
        if not member.check_club_password(current_password):
            messages.error(request, 'Current password is incorrect')
            return redirect('club_member_change_password')

        # Check new password length
        if len(new_password) < 8:
            messages.error(request, 'New password must be at least 8 characters long')
            return redirect('club_member_change_password')

        # Check if passwords match
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match')
            return redirect('club_member_change_password')

        # Update club password
        member.set_club_password(new_password)
        member.save()

        messages.success(request, 'Club password changed successfully!')
        return redirect('club_dashboard')

    context = {
        'member': member
    }

    return render(request, 'clubs/change_password.html', context)


def club_analytics(request):
    """Club analytics dashboard with charts"""
    # Check if logged in
    if not request.session.get('club_member_id'):
        messages.warning(request, 'Please login to access analytics')
        return redirect('club_login')

    member_id = request.session.get('club_member_id')
    member = ClubMember.objects.select_related('club', 'student', 'role').get(member_id=member_id)

    # Check permission
    if not member.has_permission('view_reports'):
        messages.error(request, 'You do not have permission to view analytics')
        return redirect('club_dashboard')

    # Get statistics
    from events.models import Event
    from attendance.models import Attendance

    total_events = Event.objects.filter(club=member.club).count()
    completed_events = Event.objects.filter(club=member.club, event_status='COMPLETED').count()
    total_registrations = 0
    total_attendees = 0

    for event in Event.objects.filter(club=member.club, event_status='COMPLETED'):
        summary = event.get_attendance_summary()
        total_registrations += summary['total_registered']
        total_attendees += summary['total_present']

    avg_attendance_rate = (total_attendees / total_registrations * 100) if total_registrations > 0 else 0

    # Generate charts
    from .analytics_utils import generate_club_analytics_charts
    charts = generate_club_analytics_charts(member.club)

    context = {
        'member': member,
        'club': member.club,
        'total_events': total_events,
        'completed_events': completed_events,
        'total_registrations': total_registrations,
        'total_attendees': total_attendees,
        'avg_attendance_rate': avg_attendance_rate,
        'charts': charts,
    }

    return render(request, 'clubs/analytics.html', context)