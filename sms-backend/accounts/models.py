from django.db import models
from shared.models import BaseModel
from django.contrib.auth.models import AbstractUser
from datetime import timedelta
from django.utils import timezone
# Create your models here.
class User(BaseModel, AbstractUser):
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='users')
    role = models.ForeignKey('accounts.Role', on_delete=models.PROTECT, related_name='users')
    phone_number = models.CharField(max_length=15, unique=True)

    username = None

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []




class Role(BaseModel):
    class RoleChoices(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        TEACHER = 'teacher', 'Teacher'
        ACCOUNTANT = 'accountant', 'Accountant'
        STAFF = 'staff', 'Staff'
    name = models.CharField(max_length=50, choices=RoleChoices.choices, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.get_name_display()


class Profile(BaseModel):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    phone_number_alt = models.CharField(max_length=15, null=True, blank=True)


class Permission(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    code = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class RolePermission(BaseModel):
    role = models.ForeignKey('accounts.Role', on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey('accounts.Permission', on_delete=models.CASCADE, related_name='role_permissions')

    class Meta:
        unique_together = ('role', 'permission')

    def __str__(self):
        return f"{self.role.name} - {self.permission.name}"


class PhoneOtp(BaseModel):
    phone_number = models.CharField(max_length=15, unique=True)
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)

    @property
    def is_expired(self):
        return self.created_at + timedelta(minutes=5) < timezone.now()

    def __str__(self):
        return f"{self.phone_number} - {self.otp}"
    
    
    