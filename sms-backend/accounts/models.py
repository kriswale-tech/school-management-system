from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from shared.models import BaseModel


class User(BaseModel, AbstractUser):
    class RoleChoices(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        TEACHER = 'teacher', 'Teacher'
        ACCOUNTANT = 'accountant', 'Accountant'
        STAFF = 'staff', 'Staff'

    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='users')
    role = models.CharField(max_length=50, choices=RoleChoices.choices)
    phone_number = models.CharField(max_length=15, unique=True)

    username = None

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []


class Profile(BaseModel):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        null=True,
        blank=True,
    )
    address = models.TextField(null=True, blank=True)
    phone_number_alt = models.CharField(max_length=15, null=True, blank=True)


class Permission(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    code = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class RolePermission(BaseModel):
    role = models.CharField(max_length=50, choices=User.RoleChoices.choices)
    permission = models.ForeignKey(
        'accounts.Permission',
        on_delete=models.CASCADE,
        related_name='role_permissions',
    )

    class Meta:
        unique_together = ('role', 'permission')

    def __str__(self):
        return f"{self.get_role_display()} - {self.permission.name}"


class PhoneOtp(BaseModel):
    class Purpose(models.TextChoices):
        SIGNUP = 'signup', 'Signup'
        LOGIN = 'login', 'Login'

    phone_number = models.CharField(max_length=15)
    purpose = models.CharField(max_length=10, choices=Purpose.choices)
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    expires_at = models.DateTimeField()
    sent_at = models.DateTimeField()

    class Meta:
        unique_together = ('phone_number', 'purpose')

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @classmethod
    def default_expires_at(cls):
        from django.conf import settings

        return timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

    def __str__(self):
        return f"{self.phone_number} ({self.purpose}) - {self.otp}"
