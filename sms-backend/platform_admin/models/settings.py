from django.db import models

from shared.models import BaseModel


class PlatformSettings(BaseModel):
    """Singleton-style platform configuration (one logical row)."""

    public_school_registration_enabled = models.BooleanField(
        default=True,
        help_text='When false, public school admin signup is disabled.',
    )
    subscription_grace_days = models.PositiveIntegerField(
        default=7,
        help_text='Days after a failed/overdue payment before suspension.',
    )

    class Meta:
        verbose_name_plural = 'Platform settings'

    def __str__(self):
        return 'Platform settings'
