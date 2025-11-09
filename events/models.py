from django.db import models
from django.core.exceptions import ValidationError
from clubs.models import Club, ClubMember
from students.models import Student


class Event(models.Model):
    """
    Event model for storing event information
    """
    EVENT_STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    EVENT_TYPE_CHOICES = [
        ('NORMAL', 'Normal Event'),
        ('ACTIVITY_POINTS', 'Event with Activity Points'),
    ]

    event_id = models.AutoField(primary_key=True)
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name='events'
    )
    event_name = models.CharField(max_length=200)
    event_description = models.TextField(blank=True, null=True)
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
        default='NORMAL'
    )
    activity_points = models.IntegerField(
        blank=True,
        null=True,
        help_text='Activity points awarded for participation (only for Activity Points events)'
    )
    event_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(blank=True, null=True)
    venue = models.CharField(max_length=200, blank=True, null=True)
    max_participants = models.IntegerField(blank=True, null=True)
    created_by = models.ForeignKey(
        ClubMember,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_events'
    )
    last_edited_by = models.ForeignKey(
        ClubMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edited_events'
    )
    last_edited_at = models.DateTimeField(blank=True, null=True)
    event_status = models.CharField(
        max_length=20,
        choices=EVENT_STATUS_CHOICES,
        default='SCHEDULED'
    )
    event_started_at = models.DateTimeField(blank=True, null=True)
    event_ended_at = models.DateTimeField(blank=True, null=True)
    started_by = models.ForeignKey(
        ClubMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='started_events'
    )
    ended_by = models.ForeignKey(
        ClubMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ended_events'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'events'
        verbose_name = 'Event'
        verbose_name_plural = 'Events'
        ordering = ['-event_date', '-start_time']

    def __str__(self):
        return f"{self.event_name} - {self.event_date}"

    def clean(self):
        """Validate event data"""
        from django.core.exceptions import ValidationError

        # If event type is ACTIVITY_POINTS, activity_points must be provided
        if self.event_type == 'ACTIVITY_POINTS' and not self.activity_points:
            raise ValidationError({
                'activity_points': 'Activity points must be specified for events with activity points'
            })

        # If event type is NORMAL, activity_points should be None
        if self.event_type == 'NORMAL' and self.activity_points:
            raise ValidationError({
                'activity_points': 'Activity points should not be set for normal events'
            })

        # Validate activity points range
        if self.activity_points and (self.activity_points < 1 or self.activity_points > 100):
            raise ValidationError({
                'activity_points': 'Activity points must be between 1 and 100'
            })

    def has_activity_points(self):
        """Check if event awards activity points"""
        return self.event_type == 'ACTIVITY_POINTS' and self.activity_points

    def get_registered_count(self):
        """Get count of registered students"""
        return self.registrations.filter(registration_status='REGISTERED').count()

    def get_attendance_summary(self):
        """Get attendance summary for this event"""
        from attendance.models import Attendance
        total_registered = self.get_registered_count()
        total_present = Attendance.objects.filter(
            event=self,
            attendance_status='PRESENT'
        ).count()
        total_absent = Attendance.objects.filter(
            event=self,
            attendance_status='ABSENT'
        ).count()

        return {
            'total_registered': total_registered,
            'total_present': total_present,
            'total_absent': total_absent,
            'not_marked': total_registered - (total_present + total_absent)
        }

    def is_full(self):
        """Check if event has reached maximum participants"""
        if self.max_participants:
            return self.get_registered_count() >= self.max_participants
        return False

    def can_register(self):
        """Check if students can still register"""
        from django.utils import timezone
        return (
                self.event_status == 'SCHEDULED' and
                not self.is_full() and
                self.event_date >= timezone.now().date()
        )


class EventRegistration(models.Model):
    """
    EventRegistration model for storing student registrations for events
    """
    REGISTRATION_STATUS_CHOICES = [
        ('REGISTERED', 'Registered'),
        ('CANCELLED', 'Cancelled'),
    ]

    registration_id = models.AutoField(primary_key=True)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='registrations'
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='event_registrations'
    )
    registration_date = models.DateTimeField(auto_now_add=True)
    registration_status = models.CharField(
        max_length=20,
        choices=REGISTRATION_STATUS_CHOICES,
        default='REGISTERED'
    )
    cancelled_at = models.DateTimeField(blank=True, null=True)
    cancellation_reason = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'event_registrations'
        verbose_name = 'Event Registration'
        verbose_name_plural = 'Event Registrations'
        unique_together = ['event', 'student']
        ordering = ['-registration_date']

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.event.event_name}"

    def clean(self):
        """Validate registration before saving"""
        # Check if student has reached registration limit
        if self.registration_status == 'REGISTERED':
            if not self.student.can_register_for_event():
                raise ValidationError(
                    f"Student has reached maximum event registration limit of {self.student.max_event_registrations}"
                )

        # Check if event is full
        if self.registration_status == 'REGISTERED' and self.event.is_full():
            raise ValidationError("Event has reached maximum participants")

    def cancel_registration(self, reason=None):
        """Cancel the registration"""
        from django.utils import timezone
        self.registration_status = 'CANCELLED'
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason
        self.save()


class EventEditHistory(models.Model):
    """
    EventEditHistory model for tracking all edits made to events
    """
    edit_id = models.AutoField(primary_key=True)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='edit_history'
    )
    edited_by = models.ForeignKey(
        ClubMember,
        on_delete=models.SET_NULL,
        null=True,
        related_name='event_edits'
    )
    field_changed = models.CharField(max_length=100)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    edited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'event_edit_history'
        verbose_name = 'Event Edit History'
        verbose_name_plural = 'Event Edit History'
        ordering = ['-edited_at']

    def __str__(self):
        return f"{self.event.event_name} - {self.field_changed} changed"