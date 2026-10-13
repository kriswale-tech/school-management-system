from decimal import Decimal

from django.db.models import DecimalField, Exists, F, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from accounts.models import User
from accounts.services.access_scope import resolve_access_scope
from assessments.models import StudentResult
from fees.models import Payment, StudentFee
from schools.models import Term
from students.models import ClassEnrollment


def _money(value) -> str:
    return f'{Decimal(value):.2f}'


def _plural(count: int, singular: str, plural: str) -> str:
    return singular if count == 1 else plural


def count_outstanding_students(*, school, term, threshold) -> int:
    decimal_field = DecimalField(max_digits=12, decimal_places=2)
    paid_sq = (
        Payment.objects.filter(student_id=OuterRef('student_id'), term=term)
        .values('student_id')
        .annotate(total=Sum('amount'))
        .values('total')[:1]
    )
    return (
        StudentFee.objects.filter(term=term, student__school=school)
        .values('student_id')
        .annotate(
            billed=Sum('amount'),
            paid=Coalesce(
                Subquery(paid_sq, output_field=decimal_field),
                Value(Decimal('0.00')),
                output_field=decimal_field,
            ),
        )
        .annotate(balance=F('billed') - F('paid'))
        .filter(balance__gte=threshold)
        .count()
    )


def _unreleased_result_count(*, school, term, membership) -> int:
    """Enrolled students on this term whose report is not released.

    Students with no result row count, matching the assessments inbox where
    those reports are still with the class teacher.
    """
    enrollments = ClassEnrollment.objects.filter(term=term, student__school=school)
    if membership.role == User.RoleChoices.TEACHER:
        scope = resolve_access_scope(membership)
        if not scope.is_class_teacher:
            return 0
        enrollments = enrollments.filter(stream_id__in=scope.visible_stream_ids)
    elif membership.role != User.RoleChoices.ADMIN:
        return 0

    released = StudentResult.objects.filter(
        term_id=OuterRef('term_id'),
        student_id=OuterRef('student_id'),
        stream_id=OuterRef('stream_id'),
        status=StudentResult.Status.RELEASED,
    )
    return enrollments.exclude(Exists(released)).count()


def list_school_alerts(*, school, membership) -> list[dict]:
    from schools.services.settings import get_school_settings

    preferences = get_school_settings(school)

    term = Term.objects.filter(school=school, is_active=True).first()
    if term is None:
        return []

    role = membership.role
    alerts = []

    if preferences.fees_alert_enabled and role in (
        User.RoleChoices.ADMIN,
        User.RoleChoices.ACCOUNTANT,
    ):
        count = count_outstanding_students(
            school=school,
            term=term,
            threshold=preferences.fees_alert_threshold,
        )
        if count:
            amount = _money(preferences.fees_alert_threshold)
            alerts.append({
                'kind': 'fees',
                'title': 'Outstanding fees',
                'summary': (
                    f'{count} {_plural(count, "student owes", "students owe")} '
                    f'at least {amount} this term.'
                ),
                'count': count,
                'href': '/fees?debtors=true',
            })

    if preferences.results_alert_enabled and _can_see_results(membership):
        count = _unreleased_result_count(school=school, term=term, membership=membership)
        if count:
            alerts.append({
                'kind': 'results',
                'title': 'Unreleased results',
                'summary': (
                    f'{count} {_plural(count, "result is", "results are")} '
                    'not released this term.'
                ),
                'count': count,
                'href': '/assessments',
            })

    if preferences.enrollments_alert_enabled and role == User.RoleChoices.ADMIN:
        count = ClassEnrollment.objects.filter(
            term=term,
            student__school=school,
            is_new_student=True,
        ).count()
        if count:
            alerts.append({
                'kind': 'enrollments',
                'title': 'New enrollments',
                'summary': (
                    f'{count} new {_plural(count, "student", "students")} '
                    'enrolled this term.'
                ),
                'count': count,
                'href': '/students',
            })

    return alerts


def _can_see_results(membership) -> bool:
    if membership.role == User.RoleChoices.ADMIN:
        return True
    if membership.role != User.RoleChoices.TEACHER:
        return False
    return resolve_access_scope(membership).is_class_teacher
