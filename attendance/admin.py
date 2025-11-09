from django.contrib import admin
from .models import Attendance, EventReport


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = [
        'student',
        'event',
        'attendance_status',
        'marked_by',
        'marked_at'
    ]

    list_filter = [
        'attendance_status',
        'event__club',
        'event__event_date',
        'marked_at'
    ]

    search_fields = [
        'student__first_name',
        'student__last_name',
        'student__usn',
        'event__event_name'
    ]

    readonly_fields = [
        'attendance_id',
        'marked_at'
    ]

    fieldsets = (
        ('Attendance Information', {
            'fields': (
                'attendance_id',
                'event',
                'student',
                'attendance_status'
            )
        }),
        ('Marked By', {
            'fields': (
                'marked_by',
                'marked_at',
                'remarks'
            )
        }),
    )

    actions = ['mark_present', 'mark_absent']

    def mark_present(self, request, queryset):
        """Mark selected as present"""
        updated = queryset.update(attendance_status='PRESENT')
        self.message_user(request, f'{updated} attendance record(s) marked as present.')

    mark_present.short_description = 'Mark as Present'

    def mark_absent(self, request, queryset):
        """Mark selected as absent"""
        updated = queryset.update(attendance_status='ABSENT')
        self.message_user(request, f'{updated} attendance record(s) marked as absent.')

    mark_absent.short_description = 'Mark as Absent'


@admin.register(EventReport)
class EventReportAdmin(admin.ModelAdmin):
    list_display = [
        'event',
        'total_registered',
        'total_present',
        'total_absent',
        'attendance_percentage',
        'report_generated_at'
    ]

    list_filter = [
        'event__club',
        'report_generated_at',
        'event__event_date'
    ]

    search_fields = [
        'event__event_name',
        'report_sent_to'
    ]

    readonly_fields = [
        'report_id',
        'event',
        'total_registered',
        'total_present',
        'total_absent',
        'attendance_percentage',
        'report_generated_at'
    ]

    fieldsets = (
        ('Report Information', {
            'fields': (
                'report_id',
                'event',
                'report_generated_at'
            )
        }),
        ('Attendance Statistics', {
            'fields': (
                'total_registered',
                'total_present',
                'total_absent',
                'attendance_percentage'
            )
        }),
        ('Distribution', {
            'fields': (
                'report_sent_to',
                'report_file_path'
            )
        }),
    )

    actions = ['regenerate_reports']

    def regenerate_reports(self, request, queryset):
        """Regenerate selected reports"""
        for report in queryset:
            summary = report.event.get_attendance_summary()
            report.total_registered = summary['total_registered']
            report.total_present = summary['total_present']
            report.total_absent = summary['total_absent']
            report.calculate_attendance_percentage()
            report.save()
        self.message_user(request, f'{queryset.count()} report(s) regenerated successfully.')

    regenerate_reports.short_description = 'Regenerate Reports'

    def has_add_permission(self, request):
        """Disable manual adding - reports should be generated automatically"""
        return False