from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.core.validators import RegexValidator


class Faculty(models.Model):
    """
    Faculty model for storing faculty information
    """
    faculty_id = models.AutoField(primary_key=True)
    faculty_code = models.CharField(
        max_length=20,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z0-9]+$',
                message='Faculty code must be alphanumeric'
            )
        ]
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
    password_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'faculty'
        verbose_name = 'Faculty'
        verbose_name_plural = 'Faculty'
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return f"{self.faculty_code} - {self.first_name} {self.last_name}"

    def get_full_name(self):
        """Return the full name of the faculty"""
        return f"{self.first_name} {self.last_name}"

    def set_password(self, raw_password):
        """Hash and set the password"""
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        """Check if the provided password matches the stored hash"""
        return check_password(raw_password, self.password_hash)

    def get_managed_clubs(self):
        """Get all clubs managed by this faculty"""
        from clubs.models import Club
        return Club.objects.filter(faculty_incharge=self, is_active=True)