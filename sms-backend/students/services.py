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
from rest_framework.exceptions import NotFound, ValidationError

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


def get_student(*, school, student_id):
    student = (
        Student.objects.filter(school=school, id=student_id)
        .prefetch_related(
            Prefetch(
                'parent_links',
                queryset=StudentParent.objects.select_related('parent').order_by(
                    '-is_primary',
                    'created_at',
                ),
            ),
        )
        .first()
    )
    if student is None:
        raise NotFound({'detail': 'Student not found in this school.'})
    return student


def get_student_active_enrollment(*, school, student, term=None):
    term = term or get_active_term(school)
    return (
        ClassEnrollment.objects.filter(student=student, term=term)
        .select_related('stream', 'class_level')
        .first()
    )


def compute_age(date_of_birth, *, today=None):
    from datetime import date as date_cls

    today = today or date_cls.today()
    years = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return years


def build_student_detail(*, school, student, term=None):
    term = term or get_active_term(school)
    enrollment = get_student_active_enrollment(school=school, student=student, term=term)

    class_payload = None
    is_new_student = None
    if enrollment is not None:
        stream = enrollment.stream
        class_payload = {
            'id': stream.id,
            'class_level_id': enrollment.class_level_id,
            'display_name': (
                enrollment.class_level.name
                if stream.is_default
                else stream.full_name
            ),
            'is_default': stream.is_default,
        }
        is_new_student = enrollment.is_new_student

    guardians = [
        {
            'id': link.id,
            'parent_id': link.parent_id,
            'name': link.parent.name,
            'phone_number': link.parent.phone_number,
            'phone_number_alt': link.parent.phone_number_alt,
            'email': link.parent.email,
            'address': link.parent.address,
            'relationship': link.relationship,
            'is_primary': link.is_primary,
            'is_emergency_contact': link.is_emergency_contact,
        }
        for link in student.parent_links.all()
    ]

    other = (student.other_names or '').strip()
    full_name = f'{student.first_name} {other} {student.last_name}'.replace('  ', ' ').strip()
    if not other:
        full_name = f'{student.first_name} {student.last_name}'

    return {
        'id': student.id,
        'student_id': student.student_id,
        'full_name': full_name,
        'first_name': student.first_name,
        'last_name': student.last_name,
        'other_names': student.other_names,
        'gender': student.gender,
        'date_of_birth': student.date_of_birth,
        'age': compute_age(student.date_of_birth),
        'admission_date': student.admission_date,
        'address': student.address,
        'is_active': student.is_active,
        'is_new_student': is_new_student,
        'class_assignment': class_payload,
        'guardians': guardians,
        'term_id': term.id,
    }


@transaction.atomic
def update_student(*, school, student_id, **fields):
    student = get_student(school=school, student_id=student_id)
    allowed = {
        'first_name',
        'last_name',
        'other_names',
        'gender',
        'date_of_birth',
        'admission_date',
        'address',
    }
    updates = []
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key in ('first_name', 'last_name', 'other_names', 'address') and isinstance(value, str):
            value = value.strip()
        setattr(student, key, value)
        updates.append(key)
    if updates:
        student.save(update_fields=[*updates, 'updated_at'])
    return build_student_detail(
        school=school,
        student=get_student(school=school, student_id=student.id),
    )


def list_student_guardians(*, school, student_id):
    student = get_student(school=school, student_id=student_id)
    return build_student_detail(school=school, student=student)['guardians']


def _get_student_parent_link(*, school, student_id, link_id):
    link = (
        StudentParent.objects.select_related('parent', 'student')
        .filter(
            id=link_id,
            student_id=student_id,
            student__school=school,
        )
        .first()
    )
    if link is None:
        raise NotFound({'detail': 'Guardian association not found for this student.'})
    return link


def _serialize_guardian_link(link):
    return {
        'id': link.id,
        'parent_id': link.parent_id,
        'name': link.parent.name,
        'phone_number': link.parent.phone_number,
        'phone_number_alt': link.parent.phone_number_alt,
        'email': link.parent.email,
        'address': link.parent.address,
        'relationship': link.relationship,
        'is_primary': link.is_primary,
        'is_emergency_contact': link.is_emergency_contact,
    }


@transaction.atomic
def add_student_guardian(*, school, student_id, guardian):
    student = get_student(school=school, student_id=student_id)
    parent = _resolve_parent(school=school, guardian=guardian)
    if StudentParent.objects.filter(student=student, parent=parent).exists():
        raise ValidationError({'detail': 'This guardian is already linked to the student.'})

    make_primary = guardian.get('is_primary', False)
    if make_primary:
        StudentParent.objects.filter(student=student, is_primary=True).update(is_primary=False)

    has_primary = StudentParent.objects.filter(student=student, is_primary=True).exists()
    link = StudentParent.objects.create(
        student=student,
        parent=parent,
        relationship=guardian['relationship'],
        is_primary=make_primary or not has_primary,
        is_emergency_contact=guardian.get('is_emergency_contact', False),
    )
    return _serialize_guardian_link(link)


@transaction.atomic
def update_student_guardian(*, school, student_id, link_id, **fields):
    link = _get_student_parent_link(school=school, student_id=student_id, link_id=link_id)
    parent = link.parent

    parent_updates = []
    for key in ('name', 'phone_number', 'phone_number_alt', 'email', 'address'):
        if key not in fields:
            continue
        value = fields[key]
        if key == 'phone_number':
            try:
                value = format_phone_number(value)
            except ValueError as exc:
                raise ValidationError({'phone_number': str(exc)}) from exc
            if (
                Parent.objects.filter(school=school, phone_number=value)
                .exclude(id=parent.id)
                .exists()
            ):
                raise ValidationError({
                    'phone_number': 'Another parent in this school already uses this phone number.',
                })
        elif isinstance(value, str) and key != 'email':
            value = value.strip()
        elif key == 'email' and isinstance(value, str):
            value = value.strip()
        setattr(parent, key, value)
        parent_updates.append(key)
    if parent_updates:
        parent.save(update_fields=[*parent_updates, 'updated_at'])

    link_updates = []
    if 'relationship' in fields:
        link.relationship = fields['relationship']
        link_updates.append('relationship')
    if 'is_emergency_contact' in fields:
        link.is_emergency_contact = fields['is_emergency_contact']
        link_updates.append('is_emergency_contact')
    if fields.get('is_primary') is True and not link.is_primary:
        StudentParent.objects.filter(student_id=student_id, is_primary=True).update(
            is_primary=False,
        )
        link.is_primary = True
        link_updates.append('is_primary')
    elif fields.get('is_primary') is False and link.is_primary:
        raise ValidationError({
            'is_primary': 'Promote another guardian to primary instead of unsetting this one.',
        })

    if link_updates:
        link.save(update_fields=[*link_updates, 'updated_at'])

    link.refresh_from_db()
    return _serialize_guardian_link(
        StudentParent.objects.select_related('parent').get(id=link.id),
    )


@transaction.atomic
def remove_student_guardian(*, school, student_id, link_id):
    link = _get_student_parent_link(school=school, student_id=student_id, link_id=link_id)
    remaining = StudentParent.objects.filter(student_id=student_id).exclude(id=link.id)
    if not remaining.exists():
        raise ValidationError({
            'detail': 'Cannot remove the last guardian. A student must have at least one.',
        })

    was_primary = link.is_primary
    link.delete()

    if was_primary:
        next_link = remaining.order_by('created_at').first()
        if next_link is not None:
            next_link.is_primary = True
            next_link.save(update_fields=['is_primary', 'updated_at'])
