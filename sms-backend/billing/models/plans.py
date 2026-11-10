from decimal import Decimal

from django.db import models

from shared.models import BaseModel


class Plan(BaseModel):
    """Application subscription tier priced by student + staff capacity."""

    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=100)
    student_min = models.PositiveIntegerField(default=1)
    student_max = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Null means open-ended (Enterprise).',
    )
    staff_min = models.PositiveIntegerField(default=1)
    staff_max = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Null means open-ended (Enterprise). Active SchoolMembership seats.',
    )
    price_monthly_ghs = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    price_annual_ghs = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    warning_thresholds = models.JSONField(
        default=list,
        blank=True,
        help_text='Fractions of capacity that trigger warnings, e.g. [0.8, 0.95].',
    )
    sort_order = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(
        default=False,
        help_text='Inactive until explicitly activated. Schools only see active plans.',
    )

    class Meta:
        ordering = ['sort_order', 'student_min', 'name']

    def __str__(self):
        return f'{self.name} ({self.code})'

    def price_for_interval(self, interval: str) -> Decimal:
        if interval == 'annual':
            return self.price_annual_ghs
        return self.price_monthly_ghs

    def covers_student_count(self, count: int) -> bool:
        if count < self.student_min:
            return False
        if self.student_max is None:
            return True
        return count <= self.student_max

    def covers_staff_count(self, count: int) -> bool:
        """Staff mins are display bands; gating uses max only."""
        if count <= 0:
            return True
        if self.staff_max is None:
            return True
        return count <= self.staff_max

    def covers_usage(self, *, students: int, staff: int) -> bool:
        """Whether this plan can host the school's current usage (upgrade/downgrade)."""
        if self.student_max is not None and students > self.student_max:
            return False
        if self.staff_max is not None and staff > self.staff_max:
            return False
        return True
