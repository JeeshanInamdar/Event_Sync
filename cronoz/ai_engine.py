"""
CRONOZ AI Engine
Smart AI assistant for Event Management System
Uses Google Gemini API
"""

import google.generativeai as genai
from django.conf import settings
from datetime import datetime, timedelta
from django.utils import timezone


class CronozAI:
    """
    CRONOZ - AI Assistant for Event Management
    """

    def __init__(self):
        """Initialize Gemini AI"""
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        except Exception as e:
            print(f"CRONOZ AI Initialization Error: {e}")
            self.model = None

    def generate_response(self, prompt, context=""):
        """
        Generate AI response with context
        """
        if not self.model:
            return "CRONOZ AI is currently unavailable. Please try again later."

        try:
            full_prompt = f"{context}\n\nUser Query: {prompt}\n\nProvide a helpful, concise response:"
            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"I encountered an error: {str(e)}. Please try rephrasing your question."

    # ==========================================
    # STUDENT AI FEATURES
    # ==========================================

    def get_social_score_suggestions(self, student):
        """
        Generate personalized suggestions to improve social score
        """
        from events.models import Event

        current_score = float(student.social_score)
        target_score = 98.00
        deficit = target_score - current_score
        events_needed = int(deficit / 2.5) + (1 if deficit % 2.5 > 0 else 0)

        # Get upcoming non-activity events
        upcoming_events = Event.objects.filter(
            event_status='SCHEDULED',
            event_type='NORMAL',
            event_date__gte=timezone.now().date()
        ).order_by('event_date')[:5]

        context = f"""
        You are CRONOZ, an AI assistant for an event management system.

        Student Profile:
        - Name: {student.get_full_name()}
        - USN: {student.usn}
        - Current Social Score: {current_score}%
        - Target Score: {target_score}%
        - Score Deficit: {deficit:.2f}%
        - Events Needed: {events_needed}

        Social Score Rules:
        - Attending non-activity events increases score by +2.5%
        - Being absent decreases score by -5%
        - Score must be ≥98% to register for activity point events

        Upcoming Non-Activity Events:
        """

        for idx, event in enumerate(upcoming_events, 1):
            context += f"\n{idx}. {event.event_name} - {event.club.club_name} - {event.event_date} at {event.start_time}"

        if not upcoming_events:
            context += "\nNo upcoming non-activity events found."

        prompt = f"""
        Provide a strategic plan for {student.first_name} to improve their social score from {current_score}% to {target_score}%.

        Include:
        1. Urgency level assessment
        2. Specific events to attend (from the list above)
        3. Timeline to reach target
        4. Motivational advice
        5. Warning about avoiding absences

        Be encouraging, specific, and actionable. Keep response under 200 words.
        """

        return self.generate_response(prompt, context)

    def get_event_recommendations(self, student):
        """
        Recommend events based on student's profile and history
        """
        from events.models import Event
        from attendance.models import Attendance

        # Get student's attendance history
        attended_events = Attendance.objects.filter(
            student=student,
            attendance_status='PRESENT'
        ).select_related('event', 'event__club')

        # Get clubs student has attended
        preferred_clubs = set([att.event.club.club_name for att in attended_events[:10]])

        # Get upcoming events
        upcoming_events = Event.objects.filter(
            event_status='SCHEDULED',
            event_date__gte=timezone.now().date()
        ).order_by('event_date')[:10]

        context = f"""
        You are CRONOZ, recommending events for a student.

        Student Profile:
        - Name: {student.get_full_name()}
        - Department: {student.department}
        - Current Activity Points: {student.total_activity_points}
        - Social Score: {student.social_score}%
        - Previously Attended Clubs: {', '.join(preferred_clubs) if preferred_clubs else 'None yet'}

        Upcoming Events:
        """

        for idx, event in enumerate(upcoming_events, 1):
            event_type = "Activity Points" if event.has_activity_points() else "Non-Activity"
            context += f"\n{idx}. {event.event_name} ({event_type}) - {event.club.club_name} - {event.event_date}"

        prompt = """
        Recommend the TOP 3 events this student should attend.

        Consider:
        1. Social score requirements
        2. Past club preferences
        3. Activity points opportunities
        4. Event timing
        5. Department relevance

        For each recommendation, explain WHY it's a good fit.
        Be personalized and motivating. Keep under 250 words.
        """

        return self.generate_response(prompt, context)

    def answer_student_query(self, student, question):
        """
        Answer general student questions with context
        """
        context = f"""
        You are CRONOZ, an AI assistant for an event management system.

        Student Context:
        - Name: {student.get_full_name()}
        - USN: {student.usn}
        - Social Score: {student.social_score}%
        - Activity Points: {student.total_activity_points}
        - Active Registrations: {student.get_active_registrations_count()}/{student.max_event_registrations}

        System Rules:
        - Social score starts at 100%
        - -5% for absence, +2.5% for attending non-activity events
        - Need 98%+ to register for activity point events
        - Activity events award points for career development

        Answer the student's question helpfully and accurately.
        """

        return self.generate_response(question, context)

    # ==========================================
    # CLUB MEMBER AI FEATURES
    # ==========================================

    def suggest_event_ideas(self, club, member):
        """
        Suggest event ideas based on club history
        """
        from events.models import Event
        from attendance.models import Attendance

        # Get past successful events (high attendance)
        past_events = Event.objects.filter(
            club=club,
            event_status='COMPLETED'
        ).order_by('-event_date')[:10]

        event_data = []
        for event in past_events:
            summary = event.get_attendance_summary()
            if summary['total_registered'] > 0:
                attendance_rate = (summary['total_present'] / summary['total_registered']) * 100
                event_data.append({
                    'name': event.event_name,
                    'type': event.event_type,
                    'attendance': attendance_rate,
                    'participants': summary['total_present']
                })

        context = f"""
        You are CRONOZ, helping a club member plan events.

        Club: {club.club_name}
        Member: {member.student.get_full_name()} ({member.role.role_name})

        Past Events Performance:
        """

        for data in event_data[:5]:
            context += f"\n- {data['name']} ({data['type']}): {data['attendance']:.1f}% attendance, {data['participants']} attendees"

        if not event_data:
            context += "\nNo past event data available."

        prompt = """
        Suggest 3 innovative event ideas for this club.

        Consider:
        1. Past event success patterns
        2. Current trends in student activities
        3. Seasonal relevance
        4. Resource requirements
        5. Expected engagement

        For each idea:
        - Event name and theme
        - Target audience
        - Expected outcomes
        - Why it will succeed

        Be creative and practical. Keep under 300 words.
        """

        return self.generate_response(prompt, context)

    def optimize_event_timing(self, club):
        """
        Suggest best timing for events based on historical data
        """
        from events.models import Event
        from django.db.models import Avg, Count

        past_events = Event.objects.filter(
            club=club,
            event_status='COMPLETED'
        ).order_by('-event_date')[:20]

        # Analyze day of week and time patterns
        day_analysis = {}
        time_analysis = {}

        for event in past_events:
            day = event.event_date.strftime('%A')
            hour = event.start_time.hour
            summary = event.get_attendance_summary()

            if summary['total_registered'] > 0:
                rate = (summary['total_present'] / summary['total_registered']) * 100

                if day not in day_analysis:
                    day_analysis[day] = []
                day_analysis[day].append(rate)

                time_slot = "Morning" if hour < 12 else "Afternoon" if hour < 17 else "Evening"
                if time_slot not in time_analysis:
                    time_analysis[time_slot] = []
                time_analysis[time_slot].append(rate)

        context = f"""
        You are CRONOZ, analyzing event timing optimization.

        Club: {club.club_name}

        Historical Attendance by Day:
        """

        for day, rates in day_analysis.items():
            avg_rate = sum(rates) / len(rates)
            context += f"\n- {day}: {avg_rate:.1f}% average attendance ({len(rates)} events)"

        context += "\n\nHistorical Attendance by Time:"
        for time_slot, rates in time_analysis.items():
            avg_rate = sum(rates) / len(rates)
            context += f"\n- {time_slot}: {avg_rate:.1f}% average attendance ({len(rates)} events)"

        prompt = """
        Based on this data, recommend:
        1. Best day(s) of the week for events
        2. Best time slots
        3. Days/times to avoid
        4. Strategic scheduling tips

        Explain your reasoning with data. Keep under 200 words.
        """

        return self.generate_response(prompt, context)

    def answer_club_query(self, club, member, question):
        """
        Answer club-related questions
        """
        context = f"""
        You are CRONOZ, assisting a club member.

        Club: {club.club_name}
        Member: {member.student.get_full_name()} ({member.role.role_name})
        Member Permissions: 
        - Create Events: {member.role.can_create_events}
        - Edit Events: {member.role.can_edit_events}
        - Mark Attendance: {member.role.can_mark_attendance}

        Total Club Members: {club.get_members_count()}
        Total Events: {club.events.count()}
        """

        return self.generate_response(question, context)

    # ==========================================
    # FACULTY AI FEATURES
    # ==========================================

    def analyze_club_performance(self, faculty):
        """
        Analyze performance of all clubs managed by faculty
        """
        clubs = faculty.get_managed_clubs()

        club_metrics = []
        for club in clubs:
            total_events = club.events.filter(event_status='COMPLETED').count()
            total_members = club.get_members_count()

            # Calculate average attendance
            completed_events = club.events.filter(event_status='COMPLETED')
            total_attendance_rate = 0
            event_count = 0

            for event in completed_events:
                summary = event.get_attendance_summary()
                if summary['total_registered'] > 0:
                    rate = (summary['total_present'] / summary['total_registered']) * 100
                    total_attendance_rate += rate
                    event_count += 1

            avg_attendance = total_attendance_rate / event_count if event_count > 0 else 0

            club_metrics.append({
                'name': club.club_name,
                'members': total_members,
                'events': total_events,
                'avg_attendance': avg_attendance,
                'has_head': 'Yes' if club.club_head else 'No'
            })

        context = f"""
        You are CRONOZ, analyzing club performance for a faculty member.

        Faculty: {faculty.get_full_name()}
        Department: {faculty.department}
        Total Clubs Managed: {len(clubs)}

        Club Performance Metrics:
        """

        for metric in club_metrics:
            context += f"\n\n{metric['name']}:"
            context += f"\n- Members: {metric['members']}"
            context += f"\n- Completed Events: {metric['events']}"
            context += f"\n- Avg Attendance: {metric['avg_attendance']:.1f}%"
            context += f"\n- Has Club Head: {metric['has_head']}"

        prompt = """
        Provide a comprehensive analysis:

        1. Overall performance assessment
        2. Top performing clubs (and why)
        3. Clubs needing improvement (with specific issues)
        4. Actionable recommendations for each underperforming club
        5. Strategic suggestions for faculty

        Be data-driven and constructive. Keep under 400 words.
        """

        return self.generate_response(prompt, context)

    def suggest_club_improvements(self, club):
        """
        Suggest specific improvements for an underperforming club
        """
        from events.models import Event

        total_events = club.events.filter(event_status='COMPLETED').count()
        recent_events = club.events.filter(event_status='COMPLETED').order_by('-event_date')[:5]

        context = f"""
        You are CRONOZ, providing improvement strategies.

        Club: {club.club_name}
        Faculty In-Charge: {club.faculty_incharge.get_full_name() if club.faculty_incharge else 'None'}
        Club Head: {club.club_head.get_full_name() if club.club_head else 'Not Appointed'}
        Total Members: {club.get_members_count()}
        Total Events Completed: {total_events}

        Recent Events:
        """

        for event in recent_events:
            summary = event.get_attendance_summary()
            context += f"\n- {event.event_name}: {summary['total_present']}/{summary['total_registered']} attended"

        prompt = """
        Provide detailed improvement plan:

        1. Key issues identified
        2. Root causes
        3. Step-by-step action plan
        4. Quick wins (immediate actions)
        5. Long-term strategies
        6. Success metrics to track

        Be specific and actionable. Keep under 350 words.
        """

        return self.generate_response(prompt, context)

    def answer_faculty_query(self, faculty, question):
        """
        Answer faculty-related questions
        """
        clubs = faculty.get_managed_clubs()

        context = f"""
        You are CRONOZ, assisting a faculty member.

        Faculty: {faculty.get_full_name()}
        Department: {faculty.department}
        Clubs Managed: {', '.join([club.club_name for club in clubs])}
        Total Clubs: {clubs.count()}
        """

        return self.generate_response(question, context)