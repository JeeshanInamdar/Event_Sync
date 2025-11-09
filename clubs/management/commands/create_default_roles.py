from django.core.management.base import BaseCommand
from clubs.models import ClubRole


class Command(BaseCommand):
    help = 'Creates default club roles (HEAD, CO-COORDINATOR, MEMBER)'

    def handle(self, *args, **kwargs):
        roles_data = [
            {
                'role_name': 'HEAD',
                'can_create_events': True,
                'can_edit_events': True,
                'can_delete_events': True,
                'can_start_events': True,
                'can_end_events': True,
                'can_mark_attendance': True,
                'can_add_members': True,
                'can_remove_members': True,
                'can_view_reports': True,
                'description': 'Club Head with full permissions'
            },
            {
                'role_name': 'CO-COORDINATOR',
                'can_create_events': True,
                'can_edit_events': True,
                'can_delete_events': False,
                'can_start_events': True,
                'can_end_events': True,
                'can_mark_attendance': True,
                'can_add_members': False,
                'can_remove_members': False,
                'can_view_reports': True,
                'description': 'Co-coordinator can manage events and mark attendance but cannot manage members'
            },
            {
                'role_name': 'MEMBER',
                'can_create_events': True,
                'can_edit_events': False,
                'can_delete_events': False,
                'can_start_events': False,
                'can_end_events': False,
                'can_mark_attendance': True,
                'can_add_members': False,
                'can_remove_members': False,
                'can_view_reports': False,
                'description': 'Regular member can create events and mark attendance during active events'
            }
        ]

        created_count = 0
        for role_data in roles_data:
            role, created = ClubRole.objects.get_or_create(
                role_name=role_data['role_name'],
                defaults=role_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created role: {role.role_name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'→ Role already exists: {role.role_name}')
                )

        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\n{created_count} role(s) created successfully!')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\nAll roles already exist!')
            )