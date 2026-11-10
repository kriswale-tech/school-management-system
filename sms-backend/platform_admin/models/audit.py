from django.db import models

from shared.models import BaseModel


class PlatformAuditLog(BaseModel):
    """Append-only record of sensitive platform actions."""

    actor = models.ForeignKey(
        'platform_admin.PlatformUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100, blank=True, default='')
    target_id = models.CharField(max_length=64, blank=True, default='')
    detail = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['target_type', 'target_id']),
        ]

    def __str__(self):
        return f'{self.action} @ {self.created_at}'

    def save(self, *args, **kwargs):
        if not self._state.adding and self.pk:
            raise ValueError('Platform audit log entries cannot be modified.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Platform audit log entries cannot be deleted.')
