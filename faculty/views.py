from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.db import IntegrityError
from .models import Faculty
from clubs.models import Club, ClubMember, ClubRole
from students.models import Student
import secrets
import string


def faculty_login(request):
    """Faculty login view"""
    # If already logged in, redirect to dashboard
    if request.session.get('faculty_id'):
        return redirect('faculty_dashboard')

    if request.method == 'POST':
        faculty_code = request.POST.get('faculty_code', '').strip().upper()
        password = request.POST.get('password', '')

        try:
            # Find faculty by code
            faculty = Faculty.objects.get(faculty_code=faculty_code, is_active=True)

            # Check password
            if faculty.check_password(password):
                # Set session
                request.session['faculty_id'] = faculty.faculty_id
                request.session['faculty_code'] = faculty.faculty_code
                request.session['faculty_name'] = faculty.get_full_name()
                request.session['user_type'] = 'faculty'

                messages.success(request, f'Welcome, {faculty.first_name}!')
                return redirect('faculty_dashboard')
            else:
                messages.error(request, 'Invalid faculty code or password')

        except Faculty.DoesNotExist:
            messages.error(request, 'Invalid faculty code or password')

    return render(request, 'faculty/login.html')


def faculty_logout(request):
    """Faculty logout view"""
    # Clear session
    if 'faculty_id' in request.session:
        del request.session['faculty_id']
    if 'faculty_code' in request.session:
        del request.session['faculty_code']
    if 'faculty_name' in request.session:
        del request.session['faculty_name']
    if 'user_type' in request.session:
        del request.session['user_type']

    messages.success(request, 'You have been logged out successfully')
    return redirect('faculty_login')


def faculty_dashboard(request):
    """Faculty dashboard view"""
    # Check if logged in
    if not request.session.get('faculty_id'):
        messages.warning(request, 'Please login to access dashboard')
        return redirect('faculty_login')

    faculty_id = request.session.get('faculty_id')
    faculty = Faculty.objects.get(faculty_id=faculty_id)

    # Get managed clubs
    clubs = Club.objects.filter(
        faculty_incharge=faculty,
        is_active=True
    ).prefetch_related('club_members', 'events')

    # Statistics
    total_clubs = clubs.count()
    total_members = sum(club.get_members_count() for club in clubs)

    # Get upcoming events from managed clubs
    from events.models import Event
    from django.utils import timezone
    upcoming_events = Event.objects.filter(
        club__in=clubs,
        event_status='SCHEDULED',
        event_date__gte=timezone.now().date()
    ).order_by('event_date')[:5]

    context = {
        'faculty': faculty,
        'clubs': clubs,
        'total_clubs': total_clubs,
        'total_members': total_members,
        'upcoming_events': upcoming_events,
    }

    return render(request, 'faculty/dashboard.html', context)


def club_detail(request, club_id):
    """View club details and members"""
    # Check if logged in
    if not request.session.get('faculty_id'):
        messages.warning(request, 'Please login first')
        return redirect('faculty_login')

    faculty_id = request.session.get('faculty_id')
    faculty = Faculty.objects.get(faculty_id=faculty_id)

    # Get club and verify faculty is in-charge
    club = get_object_or_404(Club, club_id=club_id)

    if club.faculty_incharge != faculty:
        messages.error(request, 'You are not authorized to manage this club')
        return redirect('faculty_dashboard')

    # Get club members with roles
    members = ClubMember.objects.filter(
        club=club,
        is_active=True
    ).select_related('student', 'role').order_by('role__role_name', 'student__first_name')

    # Get club events
    from events.models import Event
    events = Event.objects.filter(club=club).order_by('-event_date')[:10]

    context = {
        'faculty': faculty,
        'club': club,
        'members': members,
        'events': events,
    }

    return render(request, 'faculty/club_detail.html', context)


def appoint_club_head(request, club_id):
    """Appoint a student as club head"""
    # Check if logged in
    if not request.session.get('faculty_id'):
        messages.warning(request, 'Please login first')
        return redirect('faculty_login')

    faculty_id = request.session.get('faculty_id')
    faculty = Faculty.objects.get(faculty_id=faculty_id)

    # Get club
    club = get_object_or_404(Club, club_id=club_id)

    if club.faculty_incharge != faculty:
        messages.error(request, 'You are not authorized to manage this club')
        return redirect('faculty_dashboard')

    if request.method == 'POST':
        student_usn = request.POST.get('student_usn', '').strip().upper()

        try:
            # Get student
            student = Student.objects.get(usn=student_usn, is_active=True)

            # Check if student is already club head of another club
            if student.headed_clubs.filter(is_active=True).exists():
                messages.error(request, f'{student.get_full_name()} is already head of another club')
                return redirect('club_detail', club_id=club_id)

            # Set as club head
            club.club_head = student
            club.save()

            # Generate club login credentials
            club_login_id = f"{club.club_name.replace(' ', '_').lower()}_{student.usn.lower()}"
            club_password = generate_random_password()

            # Get HEAD role
            head_role = ClubRole.objects.get(role_name='HEAD')

            # Create or update club member
            member, created = ClubMember.objects.get_or_create(
                club=club,
                student=student,
                defaults={
                    'role': head_role,
                    'club_login_id': club_login_id,
                    'is_active': True
                }
            )

            if not created:
                member.role = head_role
                member.club_login_id = club_login_id
                member.is_active = True

            member.set_club_password(club_password)
            member.save()

            # Send email with credentials
            from clubs.email_utils import send_club_member_welcome_email
            send_club_member_welcome_email(
                student,
                club,
                club_login_id,
                club_password,
                head_role.role_name
            )

            messages.success(
                request,
                f'{student.get_full_name()} has been appointed as club head. Login credentials sent to {student.email}'
            )
            return redirect('club_detail', club_id=club_id)

        except Student.DoesNotExist:
            messages.error(request, f'Student with USN {student_usn} not found')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')

    return redirect('club_detail', club_id=club_id)


def add_club_member(request, club_id):
    """Add a member to the club"""
    # Check if logged in
    if not request.session.get('faculty_id'):
        messages.warning(request, 'Please login first')
        return redirect('faculty_login')

    faculty_id = request.session.get('faculty_id')
    faculty = Faculty.objects.get(faculty_id=faculty_id)

    # Get club
    club = get_object_or_404(Club, club_id=club_id)

    if club.faculty_incharge != faculty:
        messages.error(request, 'You are not authorized to manage this club')
        return redirect('faculty_dashboard')

    if request.method == 'POST':
        student_usn = request.POST.get('student_usn', '').strip().upper()
        role_name = request.POST.get('role', 'MEMBER')

        try:
            # Get student
            student = Student.objects.get(usn=student_usn, is_active=True)

            # Check if already a member
            if ClubMember.objects.filter(club=club, student=student, is_active=True).exists():
                messages.error(request, f'{student.get_full_name()} is already a member of this club')
                return redirect('club_detail', club_id=club_id)

            # Get role
            role = ClubRole.objects.get(role_name=role_name)

            # Generate credentials
            club_login_id = f"{club.club_name.replace(' ', '_').lower()}_{student.usn.lower()}"
            club_password = generate_random_password()

            # Create member
            member = ClubMember.objects.create(
                club=club,
                student=student,
                role=role,
                club_login_id=club_login_id,
                is_active=True
            )
            member.set_club_password(club_password)
            member.save()

            # Send email
            from clubs.email_utils import send_club_member_welcome_email
            send_club_member_welcome_email(
                student,
                club,
                club_login_id,
                club_password,
                role.role_name
            )

            messages.success(
                request,
                f'{student.get_full_name()} added as {role_name}. Credentials sent to {student.email}'
            )
            return redirect('club_detail', club_id=club_id)

        except Student.DoesNotExist:
            messages.error(request, f'Student with USN {student_usn} not found')
        except ClubRole.DoesNotExist:
            messages.error(request, 'Invalid role selected')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')

    return redirect('club_detail', club_id=club_id)


def remove_club_member(request, club_id, member_id):
    """Remove a member from the club"""
    # Check if logged in
    if not request.session.get('faculty_id'):
        messages.warning(request, 'Please login first')
        return redirect('faculty_login')

    faculty_id = request.session.get('faculty_id')
    faculty = Faculty.objects.get(faculty_id=faculty_id)

    # Get club
    club = get_object_or_404(Club, club_id=club_id)

    if club.faculty_incharge != faculty:
        messages.error(request, 'You are not authorized to manage this club')
        return redirect('faculty_dashboard')

    # Get member
    member = get_object_or_404(ClubMember, member_id=member_id, club=club)

    # Store student name before deletion
    student_name = member.student.get_full_name()

    # If member is club head, remove from club head position
    if club.club_head == member.student:
        club.club_head = None
        club.save()

    # Delete member entry from database
    member.delete()

    messages.success(request, f'{student_name} has been removed from the club')
    return redirect('club_detail', club_id=club_id)


# Helper functions
def generate_random_password(length=12):
    """Generate a random password"""
    characters = string.ascii_letters + string.digits + "!@#$%"
    password = ''.join(secrets.choice(characters) for _ in range(length))
    return password


def faculty_analytics(request):
    """Faculty analytics dashboard"""
    # Check if logged in
    if not request.session.get('faculty_id'):
        messages.warning(request, 'Please login to access analytics')
        return redirect('faculty_login')

    faculty_id = request.session.get('faculty_id')
    faculty = Faculty.objects.get(faculty_id=faculty_id)

    # Get all managed clubs
    clubs = Club.objects.filter(faculty_incharge=faculty, is_active=True)

    # Overall statistics
    from events.models import Event
    total_events = Event.objects.filter(club__in=clubs).count()
    completed_events = Event.objects.filter(club__in=clubs, event_status='COMPLETED').count()

    # Get charts for each club
    from clubs.analytics_utils import generate_club_analytics_charts
    club_analytics = []
    for club in clubs:
        charts = generate_club_analytics_charts(club)
        club_analytics.append({
            'club': club,
            'charts': charts
        })

    context = {
        'faculty': faculty,
        'clubs': clubs,
        'total_events': total_events,
        'completed_events': completed_events,
        'club_analytics': club_analytics,
    }

    return render(request, 'faculty/analytics.html', context)


def club_analytics_faculty(request, club_id):
    """View analytics for a specific club (faculty access)"""
    # Check if logged in
    if not request.session.get('faculty_id'):
        messages.warning(request, 'Please login to access analytics')
        return redirect('faculty_login')

    faculty_id = request.session.get('faculty_id')
    faculty = Faculty.objects.get(faculty_id=faculty_id)

    # Get club and verify faculty is in-charge
    club = get_object_or_404(Club, club_id=club_id)

    if club.faculty_incharge != faculty:
        messages.error(request, 'You are not authorized to view this club\'s analytics')
        return redirect('faculty_dashboard')

    # Get statistics
    from events.models import Event
    total_events = Event.objects.filter(club=club).count()
    completed_events = Event.objects.filter(club=club, event_status='COMPLETED').count()
    total_registrations = 0
    total_attendees = 0

    for event in Event.objects.filter(club=club, event_status='COMPLETED'):
        summary = event.get_attendance_summary()
        total_registrations += summary['total_registered']
        total_attendees += summary['total_present']

    avg_attendance_rate = (total_attendees / total_registrations * 100) if total_registrations > 0 else 0

    # Generate charts
    from clubs.analytics_utils import generate_club_analytics_charts
    charts = generate_club_analytics_charts(club)

    # Get club members
    members_count = ClubMember.objects.filter(club=club, is_active=True).count()

    context = {
        'faculty': faculty,
        'club': club,
        'total_events': total_events,
        'completed_events': completed_events,
        'total_registrations': total_registrations,
        'total_attendees': total_attendees,
        'avg_attendance_rate': avg_attendance_rate,
        'members_count': members_count,
        'charts': charts,
    }

    return render(request, 'faculty/club_analytics.html', context)


def faculty_profile(request):
    """View and edit faculty profile"""
    # Check if logged in
    if not request.session.get('faculty_id'):
        messages.warning(request, 'Please login to access profile')
        return redirect('faculty_login')

    faculty_id = request.session.get('faculty_id')
    faculty = Faculty.objects.get(faculty_id=faculty_id)

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
                return redirect('faculty_profile')

            # Check if email already exists for another faculty
            if Faculty.objects.exclude(faculty_id=faculty_id).filter(email=email).exists():
                messages.error(request, 'Email already exists')
                return redirect('faculty_profile')

            # Update faculty
            faculty.first_name = first_name
            faculty.last_name = last_name
            faculty.email = email
            faculty.phone = phone if phone else None
            faculty.department = department

            faculty.save()

            # Update session name
            request.session['faculty_name'] = faculty.get_full_name()

            messages.success(request, 'Profile updated successfully!')
            return redirect('faculty_profile')

        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')

    context = {
        'faculty': faculty
    }

    return render(request, 'faculty/profile.html', context)


def faculty_change_password(request):
    """Change faculty password"""
    # Check if logged in
    if not request.session.get('faculty_id'):
        messages.warning(request, 'Please login to change password')
        return redirect('faculty_login')

    faculty_id = request.session.get('faculty_id')
    faculty = Faculty.objects.get(faculty_id=faculty_id)

    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # Validation
        if not all([current_password, new_password, confirm_password]):
            messages.error(request, 'All fields are required')
            return redirect('faculty_change_password')

        # Check current password
        if not faculty.check_password(current_password):
            messages.error(request, 'Current password is incorrect')
            return redirect('faculty_change_password')

        # Check new password length
        if len(new_password) < 8:
            messages.error(request, 'New password must be at least 8 characters long')
            return redirect('faculty_change_password')

        # Check if passwords match
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match')
            return redirect('faculty_change_password')

        # Update password
        faculty.set_password(new_password)
        faculty.save()

        messages.success(request, 'Password changed successfully!')
        return redirect('faculty_dashboard')

    context = {
        'faculty': faculty
    }

    return render(request, 'faculty/change_password.html', context)