from decimal import Decimal
import re

from django.db import transaction
from django.db.models import (
    Case,
    CharField,
    DecimalField,
    F,
    Prefetch,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from rest_framework.exceptions import ValidationError

from academics.models import ClassStream
from schools.models import Term
from shared.helpers import format_phone_number
from students.models import ClassEnrollment, Parent, Student, StudentParent


def get_active_term(school, *, detail='Set an active term before viewing students.'):
    term = (
        Term.objects.filter(school=school, is_active=True)
        .select_related('academic_year')
        .first()
    )
    if term is None:
        raise ValidationError({'detail': detail})
    return term


def resolve_term(school, term_id=None):
    if term_id:
        term = (
            Term.objects.filter(school=school, id=term_id)
            .select_related('academic_year')
            .first()
        )
        if term is None:
            raise ValidationError({'term': 'Term not found in this school.'})
        return term
    return get_active_term(school)


def school_initials(name: str) -> str:
    words = re.findall(r'[A-Za-z0-9]+', name or '')
    if not words:
        return 'SCH'
    initials = ''.join(word[0].upper() for word in words)
    return initials[:6] or 'SCH'


def generate_student_id(*, school) -> str:
    prefix = school_initials(school.name)
    pattern = f'{prefix}-'
    existing = (
        Student.objects.select_for_update()
        .filter(school=school, student_id__startswith=pattern)
        .values_list('student_id', flat=True)
    )
    max_n = 0
    for student_id in existing:
        suffix = student_id[len(pattern):]
        if suffix.isdigit():
            max_n = max(max_n, int(suffix))
    return f'{prefix}-{max_n + 1:04d}'


def _annotate_payment_totals(queryset, *, term):
    return queryset.annotate(
        total_billed=Coalesce(
            Sum(
                'student__student_fees__amount',
                filter=Q(student__student_fees__term=term),
            ),
            Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ),
        total_paid=Coalesce(
            Sum(
                'student__payments__amount',
                filter=Q(student__payments__term=term),
            ),
            Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ),
    )


def _annotate_payment_status(queryset):
    return queryset.annotate(
        payment_status=Case(
            When(
                total_billed__gt=0,
                total_paid__gte=F('total_billed'),
                then=Value('fully_paid'),
            ),
            When(total_paid__gt=0, then=Value('partially_paid')),
            When(total_billed__gt=0, then=Value('owing')),
            default=Value('no_fees'),
            output_field=CharField(),
        ),
    )


def list_enrollments_for_term(*, school, term):
    queryset = ClassEnrollment.objects.filter(
        student__school=school,
        term=term,
    ).select_related(
        'student',
        'class_level',
        'class_level__level',
        'stream',
    ).prefetch_related(
        Prefetch(
            'student__parent_links',
            queryset=StudentParent.objects.filter(
                is_primary=True,
            ).select_related('parent'),
            to_attr='primary_parent_links',
        ),
    ).order_by(
        'student__last_name',
        'student__first_name',
    )
    queryset = _annotate_payment_totals(queryset, term=term)
    return _annotate_payment_status(queryset)


def get_enrollment_for_student(*, school, term, student):
    return list_enrollments_for_term(school=school, term=term).filter(student=student).first()


def get_student_stats(*, school, term):
    enrollments = list_enrollments_for_term(school=school, term=term)

    return {
        'term_id': term.id,
        'total_students': enrollments.count(),
        'new_students': enrollments.filter(is_new_student=True).count(),
        'continuing_students': enrollments.filter(is_new_student=False).count(),
        'boys': enrollments.filter(student__gender=Student.GenderChoices.MALE).count(),
        'girls': enrollments.filter(student__gender=Student.GenderChoices.FEMALE).count(),
        'fully_paid': enrollments.filter(payment_status='fully_paid').count(),
        'partially_paid': enrollments.filter(payment_status='partially_paid').count(),
        'owing': enrollments.filter(payment_status='owing').count(),
        'no_fees': enrollments.filter(payment_status='no_fees').count(),
    }


def _resolve_stream(*, school, stream_id):
    stream = (
        ClassStream.objects.select_related('class_level', 'class_level__level')
        .filter(
            id=stream_id,
            class_level__school=school,
            is_active=True,
            class_level__is_active=True,
            class_level__level__is_active=True,
        )
        .first()
    )
    if stream is None:
        raise ValidationError({'stream_id': 'Stream not found in this school.'})
    return stream


def list_parents_for_school(*, school):
    return Parent.objects.filter(school=school).order_by('name')


def _get_or_create_parent(*, school, guardian):
    try:
        phone = format_phone_number(guardian['phone_number'])
    except ValueError as exc:
        raise ValidationError({'phone_number': str(exc)}) from exc

    parent, created = Parent.objects.get_or_create(
        school=school,
        phone_number=phone,
        defaults={
            'name': guardian['name'].strip(),
            'email': (guardian.get('email') or '').strip(),
        },
    )
    if not created:
        updates = []
        name = guardian['name'].strip()
        email = (guardian.get('email') or '').strip()
        if name and parent.name != name:
            parent.name = name
            updates.append('name')
        if email and not parent.email:
            parent.email = email
            updates.append('email')
        if updates:
            parent.save(update_fields=[*updates, 'updated_at'])
    return parent


def _resolve_parent(*, school, guardian):
    parent_id = guardian.get('parent_id')
    if parent_id:
        parent = Parent.objects.filter(school=school, id=parent_id).first()
        if parent is None:
            raise ValidationError({'parent_id': 'Parent not found in this school.'})
        return parent
    return _get_or_create_parent(school=school, guardian=guardian)


@transaction.atomic
def onboard_student(
    *,
    school,
    first_name,
    last_name,
    gender,
    date_of_birth,
    admission_date,
    guardians,
    stream_id,
    is_new_student,
    other_names='',
):
    if not guardians:
        raise ValidationError({'guardians': 'At least one guardian is required.'})

    term = get_active_term(school)
    stream = _resolve_stream(school=school, stream_id=stream_id)
    student_id = generate_student_id(school=school)

    student = Student.objects.create(
        school=school,
        student_id=student_id,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        other_names=(other_names or '').strip(),
        gender=gender,
        date_of_birth=date_of_birth,
        admission_date=admission_date,
    )

    seen_parent_ids = set()
    for index, guardian in enumerate(guardians):
        parent = _resolve_parent(school=school, guardian=guardian)
        if parent.id in seen_parent_ids:
            raise ValidationError({
                'guardians': 'Duplicate guardians are not allowed.',
            })
        seen_parent_ids.add(parent.id)

        StudentParent.objects.create(
            student=student,
            parent=parent,
            relationship=guardian['relationship'],
            is_primary=(index == 0),
        )

    ClassEnrollment.objects.create(
        student=student,
        term=term,
        stream=stream,
        is_new_student=is_new_student,
    )

    return get_enrollment_for_student(school=school, term=term, student=student)
