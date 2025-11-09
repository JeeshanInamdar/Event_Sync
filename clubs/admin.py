from django.contrib import admin
from .models import Club, ClubRole, ClubMember


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = [
        'club_name',
        'faculty_incharge',
        'club_head',
        'get_members_count',
        'is_active',
        'established_date',
        'created_at'
    ]

    list_filter = [
        'is_active',
        'established_date',
        'created_at'
    ]

    search_fields = [
        'club_name',
        'club_description',
        'club_email'
    ]

    readonly_fields = [
        'club_id',
        'created_at',
        'updated_at',
        'get_members_count'
    ]

    fieldsets = (
        ('Club Information', {
            'fields': (
                'club_id',
                'club_name',
                'club_description',
                'club_email'
            )
        }),
        ('Management', {
            'fields': (
                'faculty_incharge',
                'club_head'
            )
        }),
        ('Details', {
            'fields': (
                'established_date',
                'is_active'
            )
        }),
        ('Statistics', {
            'fields': (
                'get_members_count',
                'created_at',
                'updated_at'
            )
        }),
    )

    def get_members_count(self, obj):
        """Display member count"""
        return obj.get_members_count()

    get_members_count.short_description = 'Total Members'

    actions = ['activate_clubs', 'deactivate_clubs']

    def activate_clubs(self, request, queryset):
        """Activate selected clubs"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} club(s) activated successfully.')

    activate_clubs.short_description = 'Activate selected clubs'

    def deactivate_clubs(self, request, queryset):
        """Deactivate selected clubs"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} club(s) deactivated successfully.')

    deactivate_clubs.short_description = 'Deactivate selected clubs'


@admin.register(ClubRole)
class ClubRoleAdmin(admin.ModelAdmin):
    list_display = [
        'role_name',
        'can_create_events',
        'can_edit_events',
        'can_delete_events',
        'can_start_events',
        'can_end_events',
        'can_mark_attendance',
        'can_add_members',
        'can_remove_members',
        'can_view_reports'
    ]

    list_filter = [
        'can_create_events',
        'can_edit_events',
        'can_mark_attendance'
    ]

    search_fields = [
        'role_name',
        'description'
    ]

    readonly_fields = ['role_id']

    fieldsets = (
        ('Role Information', {
            'fields': (
                'role_id',
                'role_name',
                'description'
            )
        }),
        ('Event Permissions', {
            'fields': (
                'can_create_events',
                'can_edit_events',
                'can_delete_events',
                'can_start_events',
                'can_end_events'
            )
        }),
        ('Other Permissions', {
            'fields': (
                'can_mark_attendance',
                'can_add_members',
                'can_remove_members',
                'can_view_reports'
            )
        }),
    )


@admin.register(ClubMember)
class ClubMemberAdmin(admin.ModelAdmin):
    list_display = [
        'student',
        'club',
        'role',
        'club_login_id',
        'is_active',
        'joined_date'
    ]

    list_filter = [
        'club',
        'role',
        'is_active',
        'joined_date'
    ]

    search_fields = [
        'student__first_name',
        'student__last_name',
        'student__usn',
        'club__club_name',
        'club_login_id'
    ]

    readonly_fields = [
        'member_id',
        'joined_date'
    ]

    fieldsets = (
        ('Membership Information', {
            'fields': (
                'member_id',
                'club',
                'student',
                'role'
            )
        }),
        ('Club Login Credentials', {
            'fields': (
                'club_login_id',
                'club_password_hash'
            )
        }),
        ('Status', {
            'fields': (
                'is_active',
                'joined_date'
            )
        }),
    )

    def save_model(self, request, obj, form, change):
        """Hash club password before saving if it's changed"""
        if 'club_password_hash' in form.changed_data:
            if obj.club_password_hash and not obj.club_password_hash.startswith('pbkdf2_'):
                obj.set_club_password(obj.club_password_hash)
        super().save_model(request, obj, form, change)

    actions = ['activate_members', 'deactivate_members']

    def activate_members(self, request, queryset):
        """Activate selected members"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} member(s) activated successfully.')

    activate_members.short_description = 'Activate selected members'

    def deactivate_members(self, request, queryset):
        """Deactivate selected members"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} member(s) deactivated successfully.')

    deactivate_members.short_description = 'Deactivate selected members'