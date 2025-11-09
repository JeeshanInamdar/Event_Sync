from django.contrib import admin
from .models import Event, EventRegistration, EventEditHistory


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        'event_name',
        'club',
        'event_type',
        'activity_points',
        'event_date',
        'start_time',
        'venue',
        'event_status',
        'get_registered_count',
        'created_at'
    ]

    list_filter = [
        'event_status',
        'event_date',
        'club',
        'created_at'
    ]

    search_fields = [
        'event_name',
        'event_description',
        'venue',
        'club__club_name'
    ]

    readonly_fields = [
        'event_id',
        'created_at',
        'updated_at',
        'get_registered_count',
        'get_attendance_summary_display'
    ]

    fieldsets = (
        ('Event Information', {
            'fields': (
                'event_id',
                'event_name',
                'event_description',
                'club'
            )
        }),
        ('Schedule', {
            'fields': (
                'event_date',
                'start_time',
                'end_time',
                'venue'
            )
        }),
        ('Registration', {
            'fields': (
                'max_participants',
                'get_registered_count'
            )
        }),
        ('Status & Control', {
            'fields': (
                'event_status',
                'event_started_at',
                'event_ended_at',
                'started_by',
                'ended_by'
            )
        }),
        ('Creation & Editing', {
            'fields': (
                'created_by',
                'last_edited_by',
                'last_edited_at'
            )
        }),
        ('Attendance', {
            'fields': (
                'get_attendance_summary_display',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at'
            )
        }),
    )

    def get_registered_count(self, obj):
        """Display registration count"""
        return obj.get_registered_count()

    get_registered_count.short_description = 'Registered Students'

    def get_attendance_summary_display(self, obj):
        """Display attendance summary"""
        summary = obj.get_attendance_summary()
        return f"Present: {summary['total_present']} | Absent: {summary['total_absent']} | Not Marked: {summary['not_marked']}"

    get_attendance_summary_display.short_description = 'Attendance Summary'

    actions = ['mark_as_completed', 'mark_as_cancelled']

    def mark_as_completed(self, request, queryset):
        """Mark selected events as completed"""
        updated = queryset.update(event_status='COMPLETED')
        self.message_user(request, f'{updated} event(s) marked as completed.')

    mark_as_completed.short_description = 'Mark as Completed'

    def mark_as_cancelled(self, request, queryset):
        """Mark selected events as cancelled"""
        updated = queryset.update(event_status='CANCELLED')
        self.message_user(request, f'{updated} event(s) marked as cancelled.')

    mark_as_cancelled.short_description = 'Mark as Cancelled'


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = [
        'student',
        'event',
        'registration_status',
        'registration_date',
        'cancelled_at'
    ]

    list_filter = [
        'registration_status',
        'registration_date',
        'event__club',
        'event__event_date'
    ]

    search_fields = [
        'student__first_name',
        'student__last_name',
        'student__usn',
        'event__event_name'
    ]

    readonly_fields = [
        'registration_id',
        'registration_date',
        'cancelled_at'
    ]

    fieldsets = (
        ('Registration Information', {
            'fields': (
                'registration_id',
                'event',
                'student',
                'registration_status'
            )
        }),
        ('Timestamps', {
            'fields': (
                'registration_date',
                'cancelled_at',
                'cancellation_reason'
            )
        }),
    )

    actions = ['cancel_registrations']

    def cancel_registrations(self, request, queryset):
        """Cancel selected registrations"""
        from django.utils import timezone
        updated = queryset.update(
            registration_status='CANCELLED',
            cancelled_at=timezone.now(),
            cancellation_reason='Cancelled by admin'
        )
        self.message_user(request, f'{updated} registration(s) cancelled.')

    cancel_registrations.short_description = 'Cancel selected registrations'


@admin.register(EventEditHistory)
class EventEditHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'event',
        'field_changed',
        'edited_by',
        'edited_at'
    ]

    list_filter = [
        'field_changed',
        'edited_at',
        'event'
    ]

    search_fields = [
        'event__event_name',
        'field_changed'
    ]

    readonly_fields = [
        'edit_id',
        'event',
        'edited_by',
        'field_changed',
        'old_value',
        'new_value',
        'edited_at'
    ]

    fieldsets = (
        ('Edit Information', {
            'fields': (
                'edit_id',
                'event',
                'edited_by',
                'field_changed',
                'edited_at'
            )
        }),
        ('Changes', {
            'fields': (
                'old_value',
                'new_value'
            )
        }),
    )

    def has_add_permission(self, request):
        """Disable manual adding of edit history"""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable editing of edit history"""
        return False