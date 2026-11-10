from django.db import models

from shared.models import BaseModel


class SchoolAdminInvite(BaseModel):
    """Invitation for a school's first (or additional) administrator."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        EXPIRED = 'expired', 'Expired'
        REVOKED = 'revoked', 'Revoked'

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='admin_invites',
    )
    phone_number = models.CharField(max_length=15)
    email = models.EmailField()
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, blank=True, default='')
    token = models.CharField(max_length=64, unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        'platform_admin.PlatformUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='school_invites_created',
    )
    accepted_user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accepted_school_admin_invites',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['school', 'status']),
        ]

    def __str__(self):
        return f'Invite {self.phone_number} → {self.school_id} ({self.status})'

    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING
