from contextlib import contextmanager
from contextvars import ContextVar

from django.core.exceptions import ValidationError

_allow_curriculum_writes = ContextVar('allow_curriculum_writes', default=False)


def curriculum_writes_allowed():
    return _allow_curriculum_writes.get()


@contextmanager
def allow_curriculum_writes():
    token = _allow_curriculum_writes.set(True)
    try:
        yield
    finally:
        _allow_curriculum_writes.reset(token)


class ImmutableCurriculumMixin:
    """Master curriculum rows are read-only outside seed/migration contexts."""

    def save(self, *args, **kwargs):
        if not curriculum_writes_allowed():
            raise ValidationError('Master curriculum records are read-only.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if not curriculum_writes_allowed():
            raise ValidationError('Master curriculum records cannot be deleted.')
        super().delete(*args, **kwargs)
