from contextlib import contextmanager
from contextvars import ContextVar

from django.core.exceptions import ValidationError

_allow_system_record_writes = ContextVar('allow_system_record_writes', default=False)


def system_record_writes_allowed():
    return _allow_system_record_writes.get()


@contextmanager
def allow_system_record_writes():
    """Curriculum adoption may update provisioned rows. School users cannot."""
    token = _allow_system_record_writes.set(True)
    try:
        yield
    finally:
        _allow_system_record_writes.reset(token)


SYSTEM_GENERATED_MUTABLE_FIELDS = frozenset({
    'is_active',
    'order',
    'updated_at',
})


class SystemGeneratedRecordMixin:
    """Prevent schools from editing or deleting provisioned curriculum records."""

    def _assert_system_record_is_mutable(self):
        if system_record_writes_allowed():
            return
        if not self.pk or not self.is_system_generated:
            return

        previous = type(self).objects.filter(pk=self.pk).first()
        if not previous or not previous.is_system_generated:
            return

        for field in self._meta.concrete_fields:
            if field.name in SYSTEM_GENERATED_MUTABLE_FIELDS:
                continue
            if field.primary_key:
                continue
            if getattr(self, field.attname) != getattr(previous, field.attname):
                raise ValidationError({
                    field.name: 'System-generated records cannot be modified.',
                })

    def clean(self):
        super().clean()
        self._assert_system_record_is_mutable()

    def delete(self, *args, **kwargs):
        if self.is_system_generated:
            raise ValidationError('System-generated records cannot be deleted.')
        super().delete(*args, **kwargs)
