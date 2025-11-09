from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.core.validators import RegexValidator


class Student(models.Model):
    """
    Student model for storing student information
    """
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    student_id = models.AutoField(primary_key=True)
    usn = models.CharField(
        max_length=20,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^(?=.*[A-Za-z])(?=.*[0-9])[A-Za-z0-9]+$',
                message='USN must contain both letters and numbers (e.g., 1AB20CS001)'
            )
        ],
        help_text='University Seat Number (must contain both letters and numbers)'
    )
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(max_length=100, unique=True)
    phone = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Phone number must be 10-15 digits'
            )
        ]
    )
    department = models.CharField(max_length=100, blank=True, null=True)
    semester = models.IntegerField(blank=True, null=True)
    password_hash = models.CharField(max_length=255)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    max_event_registrations = models.IntegerField(default=10)
    total_activity_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'students'
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return f"{self.usn} - {self.first_name} {self.last_name}"

    def get_full_name(self):
        """Return the full name of the student"""
        return f"{self.first_name} {self.last_name}"

    def set_password(self, raw_password):
        """Hash and set the password"""
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        """Check if the provided password matches the stored hash"""
        return check_password(raw_password, self.password_hash)

    def get_active_registrations_count(self):
        """Get count of active event registrations"""
        from events.models import EventRegistration
        return EventRegistration.objects.filter(
            student=self,
            registration_status='REGISTERED',
            event__event_status__in=['SCHEDULED', 'ONGOING']
        ).count()

    def can_register_for_event(self):
        """Check if student can register for more events"""
        return self.get_active_registrations_count() < self.max_event_registrations

    def calculate_activity_points(self):
        """Calculate total activity points from attended events"""
        from attendance.models import Attendance

        total_points = 0
        attended_events = Attendance.objects.filter(
            student=self,
            attendance_status='PRESENT'
        ).select_related('event')

        for attendance in attended_events:
            if attendance.event.has_activity_points():
                total_points += attendance.event.activity_points

        return total_points

    def update_activity_points(self):
        """Update total activity points"""
        self.total_activity_points = self.calculate_activity_points()
        self.save()