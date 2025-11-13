from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from events.models import Event
from students.models import Student
from clubs.models import ClubMember


class Attendance(models.Model):
    """
    Attendance model for storing attendance records
    """
    ATTENDANCE_STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
    ]

    attendance_id = models.AutoField(primary_key=True)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    marked_by = models.ForeignKey(
        ClubMember,
        on_delete=models.SET_NULL,
        null=True,
        related_name='marked_attendance'
    )
    attendance_status = models.CharField(
        max_length=20,
        choices=ATTENDANCE_STATUS_CHOICES
    )
    marked_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'attendance'
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendance Records'
        unique_together = ['event', 'student']
        ordering = ['-marked_at']

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.event.event_name} - {self.attendance_status}"


class EventReport(models.Model):
    """
    EventReport model for storing generated event reports
    """
    report_id = models.AutoField(primary_key=True)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    total_registered = models.IntegerField(default=0)
    total_present = models.IntegerField(default=0)
    total_absent = models.IntegerField(default=0)
    attendance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )
    report_generated_at = models.DateTimeField(auto_now_add=True)
    report_sent_to = models.CharField(max_length=255, blank=True, null=True)
    report_file_path = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'event_reports'
        verbose_name = 'Event Report'
        verbose_name_plural = 'Event Reports'
        ordering = ['-report_generated_at']

    def __str__(self):
        return f"Report for {self.event.event_name} - {self.report_generated_at.strftime('%Y-%m-%d')}"

    def calculate_attendance_percentage(self):
        """Calculate and update attendance percentage"""
        if self.total_registered > 0:
            self.attendance_percentage = (self.total_present / self.total_registered) * 100
        else:
            self.attendance_percentage = 0
        return self.attendance_percentage

    @classmethod
    def generate_report(cls, event):
        """Generate a new report for an event"""
        summary = event.get_attendance_summary()

        report = cls.objects.create(
            event=event,
            total_registered=summary['total_registered'],
            total_present=summary['total_present'],
            total_absent=summary['total_absent']
        )

        report.calculate_attendance_percentage()
        report.save()

        return report


# ==========================================
# SIGNALS FOR AUTOMATIC UPDATES
# ==========================================

# Signal to update activity points when attendance is marked
@receiver(post_save, sender=Attendance)
def update_student_activity_points(sender, instance, created, **kwargs):
    """
    Automatically update student's activity points when attendance is marked as PRESENT
    """
    if instance.attendance_status == 'PRESENT':
        instance.student.update_activity_points()


# Signal to update social score when attendance is marked
@receiver(post_save, sender=Attendance)
def update_student_social_score(sender, instance, created, **kwargs):
    """
    Update student's social score based on attendance:
    - ABSENT: Decrease by 5% (for any event)
    - PRESENT at non-activity event: Increase by 2.5%
    - PRESENT at activity event: No social score change (only activity points)
    """
    from students.models import SocialScoreLog

    student = instance.student
    event = instance.event

    if instance.attendance_status == 'ABSENT':
        # Decrease social score by 5% for any absence
        old_score = float(student.social_score)
        student.decrease_social_score(5.00)

        # Update the log with event reference
        latest_log = student.social_score_logs.first()
        if latest_log:
            latest_log.event = event
            latest_log.remarks = f"Marked absent from: {event.event_name}"
            latest_log.save()

        print(f"[Social Score] {student.usn}: {old_score}% → {student.social_score}% (ABSENT from {event.event_name})")

    elif instance.attendance_status == 'PRESENT':
        # Only increase score for non-activity events
        if not event.has_activity_points():
            old_score = float(student.social_score)
            student.increase_social_score(2.50)

            # Update the log with event reference
            latest_log = student.social_score_logs.first()
            if latest_log:
                latest_log.event = event
                latest_log.remarks = f"Marked present at: {event.event_name} (Non-Activity Event)"
                latest_log.save()

            print(
                f"[Social Score] {student.usn}: {old_score}% → {student.social_score}% (PRESENT at non-activity: {event.event_name})")
        else:
            # Activity event - no social score change
            print(f"[Social Score] {student.usn}: No change (PRESENT at activity event: {event.event_name})")