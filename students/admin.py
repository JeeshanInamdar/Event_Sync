from django.contrib import admin
from .models import Student


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
        'max_event_registrations',
        'is_active',
        'created_at'
    ]

    list_filter = [
        'department',
        'semester',
        'gender',
        'is_active',
        'created_at'
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
        'get_active_registrations_count'
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
                'total_activity_points',
                'is_active'
            )
        }),
        ('Statistics', {
            'fields': (
                'get_active_registrations_count',
                'created_at',
                'updated_at'
            )
        }),
    )

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

    actions = ['activate_students', 'deactivate_students', 'recalculate_activity_points']

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