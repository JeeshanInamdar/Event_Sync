import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import base64
from datetime import datetime, timedelta
from django.db.models import Count, Avg, Q
from django.utils import timezone


def generate_club_analytics_charts(club):
    """
    Generate multiple analytics charts for a club
    Returns: Dictionary with base64 encoded chart images
    """
    charts = {}

    # 1. Events Timeline Chart
    charts['events_timeline'] = generate_events_timeline_chart(club)

    # 2. Event Status Distribution
    charts['event_status'] = generate_event_status_chart(club)

    # 3. Attendance Rate Trend
    charts['attendance_trend'] = generate_attendance_trend_chart(club)

    # 4. Department-wise Participation
    charts['department_participation'] = generate_department_chart(club)

    # 5. Monthly Event Count
    charts['monthly_events'] = generate_monthly_events_chart(club)

    # 6. Activity Points Distribution
    charts['activity_points'] = generate_activity_points_chart(club)

    return charts


def generate_events_timeline_chart(club):
    """Timeline of events over the past 6 months"""
    from events.models import Event

    try:
        # Get events from last 6 months
        six_months_ago = timezone.now() - timedelta(days=180)
        events = Event.objects.filter(
            club=club,
            event_date__gte=six_months_ago
        ).order_by('event_date')

        if not events.exists():
            return None

        # Prepare data
        dates = []
        registrations = []

        for event in events:
            dates.append(event.event_date)
            registrations.append(event.get_registered_count())

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor('white')

        # Plot
        ax.plot(dates, registrations, marker='o', linewidth=2, markersize=8,
                color='#2563eb', label='Registrations')

        # Formatting
        ax.set_xlabel('Event Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('Number of Registrations', fontsize=12, fontweight='bold')
        ax.set_title(f'{club.club_name} - Events Timeline (Last 6 Months)',
                     fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper left')

        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        plt.xticks(rotation=45)

        plt.tight_layout()

        return fig_to_base64(fig)

    except Exception as e:
        print(f"Error generating timeline chart: {str(e)}")
        return None


def generate_event_status_chart(club):
    """Pie chart showing event status distribution"""
    from events.models import Event

    try:
        # Count events by status
        status_counts = Event.objects.filter(club=club).values('event_status').annotate(
            count=Count('event_id')
        )

        if not status_counts:
            return None

        labels = []
        sizes = []
        colors = {
            'SCHEDULED': '#3b82f6',
            'ONGOING': '#f59e0b',
            'COMPLETED': '#10b981',
            'CANCELLED': '#ef4444'
        }

        chart_colors = []
        for item in status_counts:
            labels.append(item['event_status'].title())
            sizes.append(item['count'])
            chart_colors.append(colors.get(item['event_status'], '#6b7280'))

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 8))
        fig.patch.set_facecolor('white')

        # Pie chart
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            colors=chart_colors,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontsize': 12, 'weight': 'bold'},
            explode=[0.05] * len(sizes)
        )

        # Make percentage text white and bold
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(11)
            autotext.set_weight('bold')

        ax.set_title(f'{club.club_name} - Event Status Distribution',
                     fontsize=14, fontweight='bold', pad=20)

        plt.tight_layout()

        return fig_to_base64(fig)

    except Exception as e:
        print(f"Error generating status chart: {str(e)}")
        return None


def generate_attendance_trend_chart(club):
    """Line chart showing attendance rate over time"""
    from events.models import Event

    try:
        # Get completed events with attendance data
        events = Event.objects.filter(
            club=club,
            event_status='COMPLETED'
        ).order_by('event_date')[:15]  # Last 15 completed events

        if not events.exists():
            return None

        event_names = []
        attendance_rates = []

        for event in events:
            summary = event.get_attendance_summary()
            if summary['total_registered'] > 0:
                rate = (summary['total_present'] / summary['total_registered']) * 100
                event_names.append(event.event_name[:20])  # Truncate long names
                attendance_rates.append(rate)

        if not attendance_rates:
            return None

        # Create figure
        fig, ax = plt.subplots(figsize=(14, 6))
        fig.patch.set_facecolor('white')

        x_pos = range(len(event_names))
        bars = ax.bar(x_pos, attendance_rates, color='#10b981', alpha=0.8, edgecolor='black')

        # Add value labels on bars
        for i, (bar, rate) in enumerate(zip(bars, attendance_rates)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height,
                    f'{rate:.1f}%',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

        # Add target line at 75%
        ax.axhline(y=75, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Target: 75%')

        ax.set_xlabel('Events', fontsize=12, fontweight='bold')
        ax.set_ylabel('Attendance Rate (%)', fontsize=12, fontweight='bold')
        ax.set_title(f'{club.club_name} - Attendance Rate Trend',
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(event_names, rotation=45, ha='right')
        ax.set_ylim(0, 110)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.legend()

        plt.tight_layout()

        return fig_to_base64(fig)

    except Exception as e:
        print(f"Error generating attendance trend chart: {str(e)}")
        return None


def generate_department_chart(club):
    """Bar chart showing participation by department"""
    from events.models import EventRegistration
    from students.models import Student

    try:
        # Get registrations for this club's events
        registrations = EventRegistration.objects.filter(
            event__club=club,
            registration_status='REGISTERED'
        ).select_related('student')

        if not registrations.exists():
            return None

        # Count by department
        dept_counts = {}
        for reg in registrations:
            dept = reg.student.department or 'Unknown'
            dept_counts[dept] = dept_counts.get(dept, 0) + 1

        # Sort by count
        sorted_depts = sorted(dept_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        departments = [d[0] for d in sorted_depts]
        counts = [d[1] for d in sorted_depts]

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor('white')

        colors_gradient = plt.cm.viridis(range(len(departments)))
        bars = ax.barh(departments, counts, color=colors_gradient, edgecolor='black')

        # Add value labels
        for i, (bar, count) in enumerate(zip(bars, counts)):
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height() / 2.,
                    f' {count}',
                    ha='left', va='center', fontsize=10, fontweight='bold')

        ax.set_xlabel('Number of Registrations', fontsize=12, fontweight='bold')
        ax.set_ylabel('Department', fontsize=12, fontweight='bold')
        ax.set_title(f'{club.club_name} - Department-wise Participation',
                     fontsize=14, fontweight='bold', pad=20)
        ax.grid(axis='x', alpha=0.3, linestyle='--')

        plt.tight_layout()

        return fig_to_base64(fig)

    except Exception as e:
        print(f"Error generating department chart: {str(e)}")
        return None


def generate_monthly_events_chart(club):
    """Bar chart showing monthly event count"""
    from events.models import Event

    try:
        # Get events from last 12 months
        twelve_months_ago = timezone.now() - timedelta(days=365)
        events = Event.objects.filter(
            club=club,
            event_date__gte=twelve_months_ago
        )

        if not events.exists():
            return None

        # Group by month
        monthly_counts = {}
        for event in events:
            month_key = event.event_date.strftime('%b %Y')
            monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1

        # Sort by date
        sorted_months = sorted(monthly_counts.items(),
                               key=lambda x: datetime.strptime(x[0], '%b %Y'))

        months = [m[0] for m in sorted_months]
        counts = [m[1] for m in sorted_months]

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor('white')

        bars = ax.bar(months, counts, color='#3b82f6', alpha=0.8, edgecolor='black')

        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontsize=10, fontweight='bold')

        ax.set_xlabel('Month', fontsize=12, fontweight='bold')
        ax.set_ylabel('Number of Events', fontsize=12, fontweight='bold')
        ax.set_title(f'{club.club_name} - Monthly Event Count',
                     fontsize=14, fontweight='bold', pad=20)
        plt.xticks(rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3, linestyle='--')

        plt.tight_layout()

        return fig_to_base64(fig)

    except Exception as e:
        print(f"Error generating monthly events chart: {str(e)}")
        return None


def generate_activity_points_chart(club):
    """Horizontal bar chart showing top students by activity points"""
    from attendance.models import Attendance
    from students.models import Student

    try:
        # Get attendance records for this club's events
        attendances = Attendance.objects.filter(
            event__club=club,
            event__event_type='ACTIVITY_POINTS',
            attendance_status='PRESENT'
        ).select_related('student', 'event')

        if not attendances.exists():
            return None

        # Calculate points per student
        student_points = {}
        for att in attendances:
            student_id = att.student_id
            if student_id not in student_points:
                student_points[student_id] = {
                    'name': att.student.get_full_name(),
                    'points': 0
                }
            student_points[student_id]['points'] += att.event.activity_points

        # Sort and get top 10
        sorted_students = sorted(student_points.values(),
                                 key=lambda x: x['points'], reverse=True)[:10]

        names = [s['name'] for s in sorted_students]
        points = [s['points'] for s in sorted_students]

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8))
        fig.patch.set_facecolor('white')

        colors_gradient = plt.cm.plasma(range(len(names)))
        bars = ax.barh(names, points, color=colors_gradient, edgecolor='black')

        # Add value labels
        for bar, point in zip(bars, points):
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height() / 2.,
                    f' {point} pts',
                    ha='left', va='center', fontsize=10, fontweight='bold')

        ax.set_xlabel('Activity Points', fontsize=12, fontweight='bold')
        ax.set_ylabel('Students', fontsize=12, fontweight='bold')
        ax.set_title(f'{club.club_name} - Top 10 Students by Activity Points',
                     fontsize=14, fontweight='bold', pad=20)
        ax.grid(axis='x', alpha=0.3, linestyle='--')

        plt.tight_layout()

        return fig_to_base64(fig)

    except Exception as e:
        print(f"Error generating activity points chart: {str(e)}")
        return None


def fig_to_base64(fig):
    """Convert matplotlib figure to base64 string"""
    buffer = BytesIO()
    fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight', facecolor='white')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close(fig)

    graphic = base64.b64encode(image_png)
    return graphic.decode('utf-8')