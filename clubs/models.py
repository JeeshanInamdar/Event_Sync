from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from students.models import Student
from faculty.models import Faculty


class Club(models.Model):
    """
    Club model for storing club information
    """
    club_id = models.AutoField(primary_key=True)
    club_name = models.CharField(max_length=100, unique=True)
    club_description = models.TextField(blank=True, null=True)
    faculty_incharge = models.ForeignKey(
        Faculty,
        on_delete=models.SET_NULL,
        null=True,
        related_name='clubs'
    )
    club_head = models.ForeignKey(
        Student,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_clubs'
    )
    club_email = models.EmailField(max_length=100, blank=True, null=True)
    established_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'clubs'
        verbose_name = 'Club'
        verbose_name_plural = 'Clubs'
        ordering = ['club_name']

    def __str__(self):
        return self.club_name

    def get_members_count(self):
        """Get total count of active members"""
        return self.club_members.filter(is_active=True).count()

    def get_upcoming_events(self):
        """Get upcoming events for this club"""
        from events.models import Event
        from django.utils import timezone
        return Event.objects.filter(
            club=self,
            event_status='SCHEDULED',
            event_date__gte=timezone.now().date()
        ).order_by('event_date')


class ClubRole(models.Model):
    """
    ClubRole model for defining permissions for different club roles
    """
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=50, unique=True)
    can_create_events = models.BooleanField(default=False)
    can_edit_events = models.BooleanField(default=False)
    can_delete_events = models.BooleanField(default=False)
    can_start_events = models.BooleanField(default=False)
    can_end_events = models.BooleanField(default=False)
    can_mark_attendance = models.BooleanField(default=False)
    can_add_members = models.BooleanField(default=False)
    can_remove_members = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'club_roles'
        verbose_name = 'Club Role'
        verbose_name_plural = 'Club Roles'
        ordering = ['role_name']

    def __str__(self):
        return self.role_name


class ClubMember(models.Model):
    """
    ClubMember model for storing club membership with roles
    """
    member_id = models.AutoField(primary_key=True)
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name='club_members'
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='club_memberships'
    )
    role = models.ForeignKey(
        ClubRole,
        on_delete=models.PROTECT,
        related_name='members'
    )
    club_login_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    club_password_hash = models.CharField(max_length=255, blank=True, null=True)
    joined_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'club_members'
        verbose_name = 'Club Member'
        verbose_name_plural = 'Club Members'
        unique_together = ['club', 'student']
        ordering = ['club', '-joined_date']

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.club.club_name} ({self.role.role_name})"

    def set_club_password(self, raw_password):
        """Hash and set the club password"""
        self.club_password_hash = make_password(raw_password)

    def check_club_password(self, raw_password):
        """Check if the provided password matches the stored hash"""
        if not self.club_password_hash:
            return False
        return check_password(raw_password, self.club_password_hash)

    def has_permission(self, permission):
        """
        Check if member has a specific permission
        permission: 'create_events', 'edit_events', etc.
        """
        return getattr(self.role, f'can_{permission}', False)