from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q, Count
from .models import Event, EventRegistration
from students.models import Student


def event_list(request):
    """Display list of all upcoming events"""
    # Check if student is logged in
    if not request.session.get('student_id'):
        messages.warning(request, 'Please login to view events')
        return redirect('student_login')

    student_id = request.session.get('student_id')
    student = Student.objects.get(student_id=student_id)

    # Get filter parameters
    event_type = request.GET.get('type', '')
    club_filter = request.GET.get('club', '')
    search_query = request.GET.get('search', '')

    # Base queryset - only upcoming and scheduled events
    events = Event.objects.filter(
        event_status='SCHEDULED',
        event_date__gte=timezone.now().date()
    ).select_related('club').order_by('event_date', 'start_time')

    # Apply filters
    if event_type:
        events = events.filter(event_type=event_type)

    if club_filter:
        events = events.filter(club__club_name__icontains=club_filter)

    if search_query:
        events = events.filter(
            Q(event_name__icontains=search_query) |
            Q(event_description__icontains=search_query) |
            Q(club__club_name__icontains=search_query)
        )

    # Get student's registered events
    registered_event_ids = EventRegistration.objects.filter(
        student=student,
        registration_status='REGISTERED'
    ).values_list('event_id', flat=True)

    # Add registration status and social score eligibility to each event
    for event in events:
        event.is_registered = event.event_id in registered_event_ids
        event.registered_count = event.get_registered_count()

        # Check if student can register based on social score
        event.can_register_social_score = True
        event.social_score_required = False

        if event.has_activity_points():
            event.social_score_required = True
            event.can_register_social_score = student.can_register_for_activity_event()

    # Get all clubs for filter dropdown
    from clubs.models import Club
    clubs = Club.objects.filter(is_active=True).order_by('club_name')

    context = {
        'events': events,
        'student': student,
        'clubs': clubs,
        'selected_type': event_type,
        'selected_club': club_filter,
        'search_query': search_query,
    }

    return render(request, 'events/event_list.html', context)


def event_detail(request, event_id):
    """Display detailed information about an event"""
    # Check if student is logged in
    if not request.session.get('student_id'):
        messages.warning(request, 'Please login to view event details')
        return redirect('student_login')

    student_id = request.session.get('student_id')
    student = Student.objects.get(student_id=student_id)

    # Get event
    event = get_object_or_404(Event, event_id=event_id)

    # Check if student is registered
    is_registered = EventRegistration.objects.filter(
        event=event,
        student=student,
        registration_status='REGISTERED'
    ).exists()

    # Get registration details if registered
    registration = None
    if is_registered:
        registration = EventRegistration.objects.get(
            event=event,
            student=student,
            registration_status='REGISTERED'
        )

    # Check social score eligibility for activity events
    can_register_social_score = True
    social_score_message = None
    social_score_required = False

    if event.has_activity_points():
        social_score_required = True
        if not student.can_register_for_activity_event():
            can_register_social_score = False
            social_score_message = (
                f"Your social score ({student.social_score}%) does not meet the required criteria (98%). "
                f"Please participate in non-activity point events to increase your social score."
            )

    context = {
        'event': event,
        'student': student,
        'is_registered': is_registered,
        'registration': registration,
        'registered_count': event.get_registered_count(),
        'can_register_social_score': can_register_social_score,
        'social_score_message': social_score_message,
        'social_score_required': social_score_required,
    }

    return render(request, 'events/event_detail.html', context)


def event_register(request, event_id):
    """Register student for an event"""
    # Check if student is logged in
    if not request.session.get('student_id'):
        messages.warning(request, 'Please login to register for events')
        return redirect('student_login')

    student_id = request.session.get('student_id')
    student = Student.objects.get(student_id=student_id)

    # Get event
    event = get_object_or_404(Event, event_id=event_id)

    # CRITICAL: Check social score for activity events
    if event.has_activity_points() and not student.can_register_for_activity_event():
        messages.error(
            request,
            f'❌ Registration Blocked: Your social score ({student.social_score}%) does not meet '
            f'the required criteria (98%). Please participate in non-activity point events to '
            f'increase your social score.'
        )
        return redirect('event_detail', event_id=event_id)

    # Check if event can accept registrations
    if not event.can_register():
        messages.error(request, 'Registration is closed for this event')
        return redirect('event_detail', event_id=event_id)

    # Check if already registered
    if EventRegistration.objects.filter(
            event=event,
            student=student,
            registration_status='REGISTERED'
    ).exists():
        messages.warning(request, 'You are already registered for this event')
        return redirect('event_detail', event_id=event_id)

    # Check if student can register for more events
    if not student.can_register_for_event():
        messages.error(
            request,
            f'You have reached your maximum event registration limit of {student.max_event_registrations}'
        )
        return redirect('event_detail', event_id=event_id)

    # Check if event is full
    if event.is_full():
        messages.error(request, 'This event has reached maximum participants')
        return redirect('event_detail', event_id=event_id)

    try:
        # Create registration
        registration = EventRegistration(
            event=event,
            student=student,
            registration_status='REGISTERED'
        )
        registration.full_clean()  # Validate
        registration.save()

        success_message = f'✓ Successfully registered for {event.event_name}!'
        if event.has_activity_points():
            success_message += f' (Activity Points: {event.activity_points})'

        messages.success(request, success_message)
        return redirect('event_detail', event_id=event_id)

    except ValidationError as e:
        messages.error(request, str(e))
        return redirect('event_detail', event_id=event_id)

    except Exception as e:
        messages.error(request, f'Registration failed: {str(e)}')
        return redirect('event_detail', event_id=event_id)


def event_cancel_registration(request, event_id):
    """Cancel student's event registration"""
    # Check if student is logged in
    if not request.session.get('student_id'):
        messages.warning(request, 'Please login first')
        return redirect('student_login')

    student_id = request.session.get('student_id')
    student = Student.objects.get(student_id=student_id)

    # Get event
    event = get_object_or_404(Event, event_id=event_id)

    # Get registration
    try:
        registration = EventRegistration.objects.get(
            event=event,
            student=student,
            registration_status='REGISTERED'
        )

        # Check if event has already started
        if event.event_status in ['ONGOING', 'COMPLETED']:
            messages.error(request, 'Cannot cancel registration for an ongoing or completed event')
            return redirect('event_detail', event_id=event_id)

        # Cancel registration
        cancellation_reason = request.POST.get('reason', 'Cancelled by student')
        registration.cancel_registration(cancellation_reason)

        messages.success(request, f'Successfully cancelled registration for {event.event_name}')
        return redirect('my_registrations')

    except EventRegistration.DoesNotExist:
        messages.error(request, 'Registration not found')
        return redirect('event_detail', event_id=event_id)


def my_registrations(request):
    """Display student's registered events"""
    # Check if student is logged in
    if not request.session.get('student_id'):
        messages.warning(request, 'Please login to view your registrations')
        return redirect('student_login')

    student_id = request.session.get('student_id')
    student = Student.objects.get(student_id=student_id)

    # Get all registrations
    registrations = EventRegistration.objects.filter(
        student=student
    ).select_related('event', 'event__club').order_by('-registration_date')

    # Separate into categories
    upcoming_registrations = registrations.filter(
        registration_status='REGISTERED',
        event__event_status='SCHEDULED',
        event__event_date__gte=timezone.now().date()
    )

    past_registrations = registrations.filter(
        Q(event__event_status='COMPLETED') |
        Q(event__event_date__lt=timezone.now().date())
    )

    cancelled_registrations = registrations.filter(
        registration_status='CANCELLED'
    )

    context = {
        'student': student,
        'upcoming_registrations': upcoming_registrations,
        'past_registrations': past_registrations,
        'cancelled_registrations': cancelled_registrations,
    }

    return render(request, 'events/my_registrations.html', context)


def my_attendance(request):
    """Display student's attendance history"""
    # Check if student is logged in
    if not request.session.get('student_id'):
        messages.warning(request, 'Please login to view your attendance')
        return redirect('student_login')

    student_id = request.session.get('student_id')
    student = Student.objects.get(student_id=student_id)

    # Get attendance records
    from attendance.models import Attendance
    attendance_records = Attendance.objects.filter(
        student=student
    ).select_related('event', 'event__club', 'marked_by').order_by('-marked_at')

    # Calculate statistics
    total_attended = attendance_records.filter(attendance_status='PRESENT').count()
    total_absent = attendance_records.filter(attendance_status='ABSENT').count()

    # Calculate attendance rate
    total_events = attendance_records.count()
    attendance_rate = (total_attended / total_events * 100) if total_events > 0 else 0

    # Calculate activity points breakdown
    activity_points_earned = []
    for record in attendance_records.filter(attendance_status='PRESENT'):
        if record.event.has_activity_points():
            activity_points_earned.append({
                'event': record.event,
                'points': record.event.activity_points,
                'date': record.marked_at
            })

    context = {
        'student': student,
        'attendance_records': attendance_records,
        'total_attended': total_attended,
        'total_absent': total_absent,
        'total_events': total_events,
        'attendance_rate': attendance_rate,
        'activity_points_earned': activity_points_earned,
    }

    return render(request, 'events/my_attendance.html', context)