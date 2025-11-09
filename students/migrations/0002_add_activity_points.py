# This is a manual data migration to handle the new activity points field
# You can run this after creating the automated migrations

from django.db import migrations


def set_default_activity_points(apps, schema_editor):
    """Set default activity points to 0 for existing students"""
    Student = apps.get_model('students', 'Student')
    Student.objects.filter(total_activity_points__isnull=True).update(total_activity_points=0)


def set_default_event_type(apps, schema_editor):
    """Set default event type to NORMAL for existing events"""
    Event = apps.get_model('events', 'Event')
    Event.objects.filter(event_type__isnull=True).update(event_type='NORMAL')


class Migration(migrations.Migration):
    dependencies = [
        ('students', '0001_initial'),  # Adjust this to your actual last migration
        ('events', '0001_initial'),  # Adjust this to your actual last migration
    ]

    operations = [
        migrations.RunPython(set_default_activity_points),
        migrations.RunPython(set_default_event_type),
    ]