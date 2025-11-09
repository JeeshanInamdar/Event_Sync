from django.contrib import admin
from .models import Faculty


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = [
        'faculty_code',
        'first_name',
        'last_name',
        'email',
        'department',
        'is_active',
        'get_managed_clubs_count',
        'created_at'
    ]

    list_filter = [
        'department',
        'is_active',
        'created_at'
    ]

    search_fields = [
        'faculty_code',
        'first_name',
        'last_name',
        'email',
        'phone'
    ]

    readonly_fields = [
        'faculty_id',
        'created_at',
        'updated_at',
        'get_managed_clubs_count'
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'faculty_id',
                'faculty_code',
                'first_name',
                'last_name',
                'email',
                'phone'
            )
        }),
        ('Department Details', {
            'fields': (
                'department',
            )
        }),
        ('Account Settings', {
            'fields': (
                'password_hash',
                'is_active'
            )
        }),
        ('Timestamps', {
            'fields': (
                'get_managed_clubs_count',
                'created_at',
                'updated_at'
            )
        }),
    )

    def get_managed_clubs_count(self, obj):
        """Display number of clubs managed"""
        return obj.get_managed_clubs().count()

    get_managed_clubs_count.short_description = 'Clubs Managed'

    def save_model(self, request, obj, form, change):
        """Hash password before saving if it's changed"""
        if 'password_hash' in form.changed_data:
            if not obj.password_hash.startswith('pbkdf2_'):
                obj.set_password(obj.password_hash)
        super().save_model(request, obj, form, change)

    actions = ['activate_faculty', 'deactivate_faculty']

    def activate_faculty(self, request, queryset):
        """Activate selected faculty"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} faculty member(s) activated successfully.')

    activate_faculty.short_description = 'Activate selected faculty'

    def deactivate_faculty(self, request, queryset):
        """Deactivate selected faculty"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} faculty member(s) deactivated successfully.')

    deactivate_faculty.short_description = 'Deactivate selected faculty'