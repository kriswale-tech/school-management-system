from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models

from shared.models import BaseModel


class PlatformUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_super_admin(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', PlatformUser.Role.SUPER_ADMIN)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)


class PlatformUser(AbstractBaseUser, BaseModel):
    """Platform operator identity — separate from school phone-OTP users."""

    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super Admin'
        OPERATIONS = 'operations', 'Platform Operations'
        FINANCE = 'finance', 'Finance Admin'
        SUPPORT = 'support', 'Support Admin'
        CURRICULUM = 'curriculum', 'Curriculum Admin'

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True, default='')
    last_name = models.CharField(max_length=150, blank=True, default='')
    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.OPERATIONS,
    )
    is_active = models.BooleanField(default=True)
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=64, blank=True, default='')

    objects = PlatformUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ['email']

    def __str__(self):
        return self.email

    @property
    def full_name(self) -> str:
        return f'{self.first_name} {self.last_name}'.strip() or self.email
