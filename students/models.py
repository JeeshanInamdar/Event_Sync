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
    social_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
        help_text='Social score percentage (100.00 by default)'
    )
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

    def can_register_for_activity_event(self):
        """Check if student can register for activity points events based on social score"""
        return float(self.social_score) >= 98.00

    def decrease_social_score(self, amount=5.00):
        """Decrease social score by specified amount (default 5%)"""
        new_score = float(self.social_score) - amount
        # Ensure score doesn't go below 0
        self.social_score = max(0.00, new_score)
        self.save()

        # Log the change
        SocialScoreLog.objects.create(
            student=self,
            change_amount=-amount,
            new_score=self.social_score,
            reason='ABSENT_FROM_EVENT'
        )

    def increase_social_score(self, amount=2.50):
        """Increase social score by specified amount (default 2.5%)"""
        new_score = float(self.social_score) + amount
        # Cap at 100%
        self.social_score = min(100.00, new_score)
        self.save()

        # Log the change
        SocialScoreLog.objects.create(
            student=self,
            change_amount=amount,
            new_score=self.social_score,
            reason='PRESENT_AT_NON_ACTIVITY_EVENT'
        )

    def get_social_score_status(self):
        """Get social score status description"""
        score = float(self.social_score)
        if score >= 98.00:
            return {
                'status': 'EXCELLENT',
                'color': 'success',
                'message': 'You can participate in all events!'
            }
        elif score >= 90.00:
            return {
                'status': 'GOOD',
                'color': 'warning',
                'message': 'Attend non-activity events to increase your score to 98% or above.'
            }
        else:
            return {
                'status': 'NEEDS_IMPROVEMENT',
                'color': 'danger',
                'message': 'Your social score is low. Please attend non-activity events to improve.'
            }


class SocialScoreLog(models.Model):
    """
    Track all social score changes with reasons
    """
    REASON_CHOICES = [
        ('ABSENT_FROM_EVENT', 'Marked Absent from Event'),
        ('PRESENT_AT_NON_ACTIVITY_EVENT', 'Present at Non-Activity Event'),
        ('MANUAL_ADJUSTMENT', 'Manual Adjustment'),
    ]

    log_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='social_score_logs'
    )
    change_amount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text='Positive for increase, negative for decrease'
    )
    new_score = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='social_score_changes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'social_score_logs'
        verbose_name = 'Social Score Log'
        verbose_name_plural = 'Social Score Logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.change_amount:+.2f}% - {self.get_reason_display()}"

    def get_change_display(self):
        """Get formatted change amount"""
        return f"{self.change_amount:+.2f}%"