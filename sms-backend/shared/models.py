import uuid

from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Curriculum(BaseModel):
    """Standard curriculum template (source of truth for school provisioning)."""

    name = models.CharField(max_length=255)
    code = models.SlugField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class CurriculumLevel(BaseModel):
    curriculum = models.ForeignKey(
        Curriculum,
        on_delete=models.CASCADE,
        related_name='levels',
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['order', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['curriculum', 'parent', 'name'],
                name='unique_curriculum_level_name',
            ),
        ]

    def __str__(self):
        if self.parent_id:
            return f'{self.parent.name} / {self.name}'
        return self.name


class CurriculumClassLevel(BaseModel):
    level = models.ForeignKey(
        CurriculumLevel,
        on_delete=models.CASCADE,
        related_name='class_levels',
    )
    name = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['order', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['level', 'name'],
                name='unique_curriculum_class_level_name',
            ),
        ]

    def __str__(self):
        return self.name


class CurriculumSubject(BaseModel):
    level = models.ForeignKey(
        CurriculumLevel,
        on_delete=models.CASCADE,
        related_name='subjects',
    )
    name = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['order', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['level', 'name'],
                name='unique_curriculum_subject_name',
            ),
        ]

    def __str__(self):
        return self.name
