from django.contrib import admin
from django.utils.html import format_html
from .models import Student, SocialScoreLog


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = [
        'usn',
        'first_name',
        'last_name',
        'email',
        'department',
        'semester',
        'total_activity_points',
        'social_score_display',
        'max_event_registrations',
        'is_active',
        'created_at'
    ]

    list_filter = [
        'department',
        'semester',
        'gender',
        'is_active',
        'created_at',
        ('social_score', admin.EmptyFieldListFilter),
    ]

    search_fields = [
        'usn',
        'first_name',
        'last_name',
        'email',
        'phone'
    ]

    readonly_fields = [
        'student_id',
        'created_at',
        'updated_at',
        'get_active_registrations_count',
        'total_activity_points',
        'social_score_status'
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'student_id',
                'usn',
                'first_name',
                'last_name',
                'email',
                'phone'
            )
        }),
        ('Academic Details', {
            'fields': (
                'department',
                'semester'
            )
        }),
        ('Personal Information', {
            'fields': (
                'date_of_birth',
                'gender',
                'address'
            )
        }),
        ('Account Settings', {
            'fields': (
                'password_hash',
                'max_event_registrations',
                'is_active'
            )
        }),
        ('Performance Metrics', {
            'fields': (
                'total_activity_points',
                'social_score',
                'social_score_status'
            ),
            'description': 'Activity points and social score tracking'
        }),
        ('Statistics', {
            'fields': (
                'get_active_registrations_count',
                'created_at',
                'updated_at'
            )
        }),
    )

    def social_score_display(self, obj):
        """Display social score with color coding"""
        score = float(obj.social_score)
        if score >= 98:
            color = '#10b981'  # Green
            icon = '✓'
        elif score >= 90:
            color = '#f59e0b'  # Orange
            icon = '⚠'
        else:
            color = '#ef4444'  # Red
            icon = '✗'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}%</span>',
            color,
            icon,
            score
        )

    social_score_display.short_description = 'Social Score'
    social_score_display.admin_order_field = 'social_score'

    def social_score_status(self, obj):
        """Display social score status with styling"""
        status_info = obj.get_social_score_status()
        colors = {
            'success': '#10b981',
            'warning': '#f59e0b',
            'danger': '#ef4444'
        }
        color = colors.get(status_info['color'], '#6b7280')

        return format_html(
            '<div style="padding: 10px; background-color: {}; color: white; border-radius: 5px; font-weight: bold;">'
            '{}: {}</div>',
            color,
            status_info['status'],
            status_info['message']
        )

    social_score_status.short_description = 'Social Score Status'

    def get_active_registrations_count(self, obj):
        """Display active registrations count"""
        return obj.get_active_registrations_count()

    get_active_registrations_count.short_description = 'Active Registrations'

    def save_model(self, request, obj, form, change):
        """Hash password before saving if it's changed"""
        if 'password_hash' in form.changed_data:
            # If password_hash field is modified directly, assume it's a plain password
            if not obj.password_hash.startswith('pbkdf2_'):
                obj.set_password(obj.password_hash)
        super().save_model(request, obj, form, change)

    actions = [
        'activate_students',
        'deactivate_students',
        'recalculate_activity_points',
        'reset_social_score',
        'view_low_social_score'
    ]

    def activate_students(self, request, queryset):
        """Activate selected students"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} student(s) activated successfully.')

    activate_students.short_description = 'Activate selected students'

    def deactivate_students(self, request, queryset):
        """Deactivate selected students"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} student(s) deactivated successfully.')

    deactivate_students.short_description = 'Deactivate selected students'

    def recalculate_activity_points(self, request, queryset):
        """Recalculate activity points for selected students"""
        count = 0
        for student in queryset:
            student.update_activity_points()
            count += 1
        self.message_user(request, f'Activity points recalculated for {count} student(s).')

    recalculate_activity_points.short_description = 'Recalculate activity points'

    def reset_social_score(self, request, queryset):
        """Reset social score to 100% for selected students"""
        count = 0
        for student in queryset:
            old_score = student.social_score
            student.social_score = 100.00
            student.save()

            # Create log entry
            SocialScoreLog.objects.create(
                student=student,
                change_amount=100.00 - float(old_score),
                new_score=100.00,
                reason='MANUAL_ADJUSTMENT',
                remarks=f'Reset by admin from {old_score}% to 100%'
            )
            count += 1

        self.message_user(request, f'Social score reset to 100% for {count} student(s).')

    reset_social_score.short_description = 'Reset social score to 100%'

    def view_low_social_score(self, request, queryset):
        """Filter to show only students with social score below 98%"""
        low_score = queryset.filter(social_score__lt=98.00).count()
        self.message_user(
            request,
            f'{low_score} student(s) have social score below 98%.',
            level='warning' if low_score > 0 else 'info'
        )

    view_low_social_score.short_description = 'Check students with low social score'


@admin.register(SocialScoreLog)
class SocialScoreLogAdmin(admin.ModelAdmin):
    list_display = [
        'student_usn',
        'student_name',
        'change_display',
        'new_score',
        'reason_display',
        'event_name',
        'created_at'
    ]

    list_filter = [
        'reason',
        'created_at',
        ('event', admin.EmptyFieldListFilter),
    ]

    search_fields = [
        'student__usn',
        'student__first_name',
        'student__last_name',
        'event__event_name',
        'remarks'
    ]

    readonly_fields = [
        'student',
        'change_amount',
        'new_score',
        'reason',
        'event',
        'created_at',
        'remarks'
    ]

    date_hierarchy = 'created_at'

    fieldsets = (
        ('Student Information', {
            'fields': ('student',)
        }),
        ('Score Change', {
            'fields': ('change_amount', 'new_score', 'reason')
        }),
        ('Event Details', {
            'fields': ('event', 'remarks')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )

    def student_usn(self, obj):
        """Display student USN"""
        return obj.student.usn

    student_usn.short_description = 'USN'
    student_usn.admin_order_field = 'student__usn'

    def student_name(self, obj):
        """Display student name"""
        return obj.student.get_full_name()

    student_name.short_description = 'Student Name'
    student_name.admin_order_field = 'student__first_name'

    def change_display(self, obj):
        """Display change amount with color coding"""
        change = float(obj.change_amount)
        if change > 0:
            color = '#10b981'  # Green
            icon = '↑'
        elif change < 0:
            color = '#ef4444'  # Red
            icon = '↓'
        else:
            color = '#6b7280'  # Gray
            icon = '='

        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {:+.2f}%</span>',
            color,
            icon,
            change
        )

    change_display.short_description = 'Change'
    change_display.admin_order_field = 'change_amount'

    def reason_display(self, obj):
        """Display reason with better formatting"""
        reason_colors = {
            'ABSENT_FROM_EVENT': '#ef4444',
            'PRESENT_AT_NON_ACTIVITY_EVENT': '#10b981',
            'MANUAL_ADJUSTMENT': '#3b82f6'
        }
        color = reason_colors.get(obj.reason, '#6b7280')

        return format_html(
            '<span style="color: {}; font-weight: 500;">{}</span>',
            color,
            obj.get_reason_display()
        )

    reason_display.short_description = 'Reason'
    reason_display.admin_order_field = 'reason'

    def event_name(self, obj):
        """Display event name if available"""
        if obj.event:
            return format_html(
                '<a href="/admin/events/event/{}/change/">{}</a>',
                obj.event.event_id,
                obj.event.event_name
            )
        return '-'

    event_name.short_description = 'Event'

    def has_add_permission(self, request):
        """Prevent manual creation of logs"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of logs"""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent editing of logs"""
        return False