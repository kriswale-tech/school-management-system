"""Score computation for subject markbooks (matches product doc + frontend scoring)."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

EXAM_MAX = Decimal('100')
ZERO = Decimal('0')


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def ca_item_percent(mark: Decimal, max_marks: Decimal) -> Decimal:
    if max_marks <= 0:
        return ZERO
    return (mark / max_marks) * Decimal('100')


def compute_class_score(
    marks_by_item_id: dict,
    items: list,
    continuous_assessment_weight: Decimal,
) -> Decimal | None:
    """Mean of CA item percentages, scaled to CA weight. None if any mark missing."""
    if not items:
        return None
    percents: list[Decimal] = []
    for item in items:
        mark = marks_by_item_id.get(str(item.id))
        if mark is None:
            mark = marks_by_item_id.get(item.id)
        if mark is None:
            return None
        percents.append(ca_item_percent(Decimal(mark), Decimal(item.max_marks)))
    avg = sum(percents, ZERO) / Decimal(len(percents))
    return _round2(avg * (Decimal(continuous_assessment_weight) / Decimal('100')))


def compute_exam_contribution(
    exam_mark: Decimal | None,
    exam_weight: Decimal,
) -> Decimal | None:
    if exam_mark is None:
        return None
    return _round2((Decimal(exam_mark) / EXAM_MAX) * Decimal(exam_weight))


def compute_total(
    class_score: Decimal | None,
    exam_contribution: Decimal | None,
) -> Decimal | None:
    if class_score is None or exam_contribution is None:
        return None
    return _round2(class_score + exam_contribution)


def resolve_grade(total: Decimal | None, bands) -> str | None:
    if total is None:
        return None
    for band in bands:
        if Decimal(band.min_score) <= total <= Decimal(band.max_score):
            return band.grade
    return None


def resolve_status(
    class_score: Decimal | None,
    exam_contribution: Decimal | None,
    total: Decimal | None,
    *,
    is_published: bool = False,
) -> str:
    if is_published:
        return 'Published'
    if class_score is not None and exam_contribution is not None and total is not None:
        return 'Complete'
    return 'Incomplete'


def decimal_or_none(value) -> float | None:
    if value is None:
        return None
    return float(_round2(Decimal(value)))
