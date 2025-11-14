from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
import json

from .ai_engine import CronozAI
from students.models import Student
from faculty.models import Faculty
from clubs.models import ClubMember, Club


def check_cronoz_enabled():
    """Check if CRONOZ AI is enabled"""
    return getattr(settings, 'CRONOZ_ENABLED', False)


# ==========================================
# STUDENT AI VIEWS
# ==========================================

def student_ai_suggestions(request):
    """
    Get AI suggestions for student dashboard (auto-suggestions)
    """
    if not request.session.get('student_id'):
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    if not check_cronoz_enabled():
        return JsonResponse({'error': 'CRONOZ AI is disabled'}, status=503)

    try:
        student_id = request.session.get('student_id')
        student = Student.objects.get(student_id=student_id)

        ai = CronozAI()

        suggestions = {}

        # Social score suggestions (if needed)
        if float(student.social_score) < 98:
            suggestions['social_score'] = ai.get_social_score_suggestions(student)

        # Event recommendations
        suggestions['events'] = ai.get_event_recommendations(student)

        return JsonResponse({
            'success': True,
            'suggestions': suggestions
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
def student_ai_chat(request):
    """
    Chat interface for students
    """
    if not request.session.get('student_id'):
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    if not check_cronoz_enabled():
        return JsonResponse({'error': 'CRONOZ AI is disabled'}, status=503)

    try:
        student_id = request.session.get('student_id')
        student = Student.objects.get(student_id=student_id)

        data = json.loads(request.body)
        question = data.get('question', '').strip()

        if not question:
            return JsonResponse({'error': 'Question is required'}, status=400)

        ai = CronozAI()
        response = ai.answer_student_query(student, question)

        return JsonResponse({
            'success': True,
            'response': response,
            'user_type': 'student'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ==========================================
# CLUB MEMBER AI VIEWS
# ==========================================

def club_ai_suggestions(request):
    """
    Get AI suggestions for club members (auto-suggestions)
    """
    if not request.session.get('club_member_id'):
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    if not check_cronoz_enabled():
        return JsonResponse({'error': 'CRONOZ AI is disabled'}, status=503)

    try:
        member_id = request.session.get('club_member_id')
        member = ClubMember.objects.select_related('club', 'student', 'role').get(member_id=member_id)

        ai = CronozAI()

        suggestions = {}

        # Event ideas (if can create events)
        if member.role.can_create_events:
            suggestions['event_ideas'] = ai.suggest_event_ideas(member.club, member)

        # Timing optimization
        suggestions['timing'] = ai.optimize_event_timing(member.club)

        return JsonResponse({
            'success': True,
            'suggestions': suggestions
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
def club_ai_chat(request):
    """
    Chat interface for club members
    """
    if not request.session.get('club_member_id'):
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    if not check_cronoz_enabled():
        return JsonResponse({'error': 'CRONOZ AI is disabled'}, status=503)

    try:
        member_id = request.session.get('club_member_id')
        member = ClubMember.objects.select_related('club', 'student', 'role').get(member_id=member_id)

        data = json.loads(request.body)
        question = data.get('question', '').strip()

        if not question:
            return JsonResponse({'error': 'Question is required'}, status=400)

        ai = CronozAI()
        response = ai.answer_club_query(member.club, member, question)

        return JsonResponse({
            'success': True,
            'response': response,
            'user_type': 'club_member'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ==========================================
# FACULTY AI VIEWS
# ==========================================

def faculty_ai_suggestions(request):
    """
    Get AI suggestions for faculty (auto-suggestions)
    """
    if not request.session.get('faculty_id'):
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    if not check_cronoz_enabled():
        return JsonResponse({'error': 'CRONOZ AI is disabled'}, status=503)

    try:
        faculty_id = request.session.get('faculty_id')
        faculty = Faculty.objects.get(faculty_id=faculty_id)

        ai = CronozAI()

        suggestions = {}

        # Overall club performance analysis
        suggestions['performance'] = ai.analyze_club_performance(faculty)

        # Improvement suggestions for underperforming clubs
        clubs = faculty.get_managed_clubs()
        improvements = []

        for club in clubs:
            total_events = club.events.filter(event_status='COMPLETED').count()
            if total_events < 3 or club.get_members_count() < 5:
                improvements.append({
                    'club_name': club.club_name,
                    'suggestions': ai.suggest_club_improvements(club)
                })

        if improvements:
            suggestions['improvements'] = improvements

        return JsonResponse({
            'success': True,
            'suggestions': suggestions
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
def faculty_ai_chat(request):
    """
    Chat interface for faculty
    """
    if not request.session.get('faculty_id'):
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    if not check_cronoz_enabled():
        return JsonResponse({'error': 'CRONOZ AI is disabled'}, status=503)

    try:
        faculty_id = request.session.get('faculty_id')
        faculty = Faculty.objects.get(faculty_id=faculty_id)

        data = json.loads(request.body)
        question = data.get('question', '').strip()

        if not question:
            return JsonResponse({'error': 'Question is required'}, status=400)

        ai = CronozAI()
        response = ai.answer_faculty_query(faculty, question)

        return JsonResponse({
            'success': True,
            'response': response,
            'user_type': 'faculty'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ==========================================
# COMMON AI CHAT VIEW
# ==========================================

def ai_chat_interface(request):
    """
    Render AI chat interface based on user type
    """
    user_type = None
    user_name = None

    if request.session.get('student_id'):
        user_type = 'student'
        try:
            student = Student.objects.get(student_id=request.session.get('student_id'))
            user_name = student.get_full_name()
        except:
            pass
    elif request.session.get('club_member_id'):
        user_type = 'club_member'
        try:
            member = ClubMember.objects.select_related('student').get(
                member_id=request.session.get('club_member_id')
            )
            user_name = member.student.get_full_name()
        except:
            pass
    elif request.session.get('faculty_id'):
        user_type = 'faculty'
        try:
            faculty = Faculty.objects.get(faculty_id=request.session.get('faculty_id'))
            user_name = faculty.get_full_name()
        except:
            pass

    if not user_type:
        messages.warning(request, 'Please login to use CRONOZ AI')
        return redirect('student_login')

    if not check_cronoz_enabled():
        messages.error(request, 'CRONOZ AI is currently disabled')
        return redirect('/')

    context = {
        'user_type': user_type,
        'user_name': user_name,
        'cronoz_enabled': True
    }

    return render(request, 'cronoz/chat_interface.html', context)