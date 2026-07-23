from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.db.models import Prefetch
from rest_framework.exceptions import NotFound, ValidationError

from accounts.models import Profile, User
from academics.models import ClassLevel, ClassSubject, ClassStream, SubjectGroup
from schools.models import SchoolSetup, Term
from schools.services.setup import advance_setup_if_needed, require_prior_setup_steps
from teachers.models import ClassTeacher, TeachingAssignment


def _raise_drf_validation_error(exc: DjangoValidationError):
    if hasattr(exc, 'message_dict'):
        raise ValidationError(exc.message_dict) from exc
    if hasattr(exc, 'messages'):
        raise ValidationError(list(exc.messages)) from exc
    raise ValidationError(str(exc)) from exc


def _get_active_term(school):
    term = Term.objects.filter(school=school, is_active=True).first()
    if term is None:
        raise ValidationError({
            'detail': 'Set an active term before configuring teachers.',
        })
    return term


def _serialize_profile(user) -> dict | None:
    try:
        profile = user.profile
    except Profile.DoesNotExist:
        return None

    return {
        'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
        'bio': profile.bio,
        'date_of_birth': profile.date_of_birth,
        'gender': profile.gender,
        'address': profile.address,
        'phone_number_alt': profile.phone_number_alt,
    }


def _serialize_stream_name(stream) -> str | None:
    if stream is None or stream.is_default:
        return None
    return stream.name


def _serialize_class_teacher_assignment(assignment) -> dict:
    return {
        'id': assignment.id,
        'class_level_id': assignment.class_level_id,
        'class_level_name': assignment.class_level.name,
        'stream_id': assignment.stream_id,
        'stream_name': _serialize_stream_name(assignment.stream),
    }


def _serialize_teaching_assignment(assignment) -> dict:
    class_subject = assignment.class_subject
    return {
        'id': assignment.id,
        'class_subject_id': assignment.class_subject_id,
        'class_level_id': class_subject.class_level_id,
        'class_level_name': class_subject.class_level.name,
        'subject_id': class_subject.subject_id,
        'subject_name': class_subject.subject.name,
        'stream_id': assignment.stream_id,
        'stream_name': _serialize_stream_name(assignment.stream),
        'subject_group_id': assignment.subject_group_id,
        'subject_group_name': (
            assignment.subject_group.name if assignment.subject_group_id else None
        ),
    }


def _serialize_teacher(user) -> dict:
    return {
        'id': user.id,
        'full_name': user.get_full_name(),
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone_number': user.phone_number,
        'email': user.email,
        'role': user.role,
        'is_active': user.is_active,
        'profile': _serialize_profile(user),
        'class_teacher_assignments': [
            _serialize_class_teacher_assignment(assignment)
            for assignment in user.class_teacher_assignments.all()
        ],
        'teaching_assignments': [
            _serialize_teaching_assignment(assignment)
            for assignment in user.teaching_assignments.all()
        ],
    }


def get_teachers_setup_queryset(school):
    term = _get_active_term(school)

    return (
        User.objects.filter(
            school=school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
        )
        .select_related('profile')
        .prefetch_related(
            Prefetch(
                'class_teacher_assignments',
                queryset=ClassTeacher.objects.filter(term=term).select_related(
                    'class_level',
                    'stream',
                ),
            ),
            Prefetch(
                'teaching_assignments',
                queryset=TeachingAssignment.objects.filter(term=term).select_related(
                    'class_subject__class_level',
                    'class_subject__subject',
                    'stream',
                    'subject_group',
                ),
            ),
        )
        .order_by('last_name', 'first_name')
    )


def serialize_teacher_for_setup(user) -> dict:
    return _serialize_teacher(user)


def get_teachers_setup(school):
    return [
        serialize_teacher_for_setup(teacher)
        for teacher in get_teachers_setup_queryset(school)
    ]


def _get_school_teacher(school, teacher_id) -> User:
    try:
        return User.objects.get(
            pk=teacher_id,
            school=school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
        )
    except User.DoesNotExist as exc:
        raise ValidationError({'teacher_id': 'Teacher not found.'}) from exc


def _get_school_class_level(school, class_level_id) -> ClassLevel:
    try:
        return ClassLevel.objects.get(pk=class_level_id, school=school)
    except ClassLevel.DoesNotExist as exc:
        raise ValidationError({'class_level_id': 'Class not found.'}) from exc


def _get_school_class_subject(school, class_subject_id) -> ClassSubject:
    try:
        return ClassSubject.objects.select_related('class_level', 'subject').get(
            pk=class_subject_id,
            school=school,
        )
    except ClassSubject.DoesNotExist as exc:
        raise ValidationError({'class_subject_id': 'Class subject not found.'}) from exc


def _get_class_stream(class_level, stream_id):
    if stream_id is None:
        return None

    try:
        return ClassStream.objects.get(pk=stream_id, class_level=class_level)
    except ClassStream.DoesNotExist as exc:
        raise ValidationError({'stream_id': 'Stream not found for this class.'}) from exc


def _get_subject_group(class_subject, subject_group_id):
    if subject_group_id is None:
        return None

    try:
        return SubjectGroup.objects.get(
            pk=subject_group_id,
            class_subject=class_subject,
        )
    except SubjectGroup.DoesNotExist as exc:
        raise ValidationError({
            'subject_group_id': 'Subject group not found for this class subject.',
        }) from exc


def _get_class_teacher_assignment(school, assignment_id, term) -> ClassTeacher:
    try:
        return ClassTeacher.objects.select_related('class_level', 'stream').get(
            pk=assignment_id,
            term=term,
            class_level__school=school,
        )
    except ClassTeacher.DoesNotExist as exc:
        raise NotFound('Class teacher assignment not found.') from exc


def _get_teaching_assignment(school, assignment_id, term) -> TeachingAssignment:
    try:
        return TeachingAssignment.objects.select_related(
            'class_subject__class_level',
            'class_subject__subject',
            'stream',
            'subject_group',
        ).get(
            pk=assignment_id,
            term=term,
            class_subject__school=school,
        )
    except TeachingAssignment.DoesNotExist as exc:
        raise NotFound('Teaching assignment not found.') from exc


def _save_assignment(assignment):
    try:
        assignment.save()
    except DjangoValidationError as exc:
        _raise_drf_validation_error(exc)
    except IntegrityError as exc:
        raise ValidationError({
            'detail': 'This assignment slot is already filled.',
        }) from exc


def create_class_teacher_assignment(
    school,
    *,
    teacher_id,
    class_level_id,
    stream_id=None,
):
    term = _get_active_term(school)
    teacher = _get_school_teacher(school, teacher_id)
    class_level = _get_school_class_level(school, class_level_id)
    stream = _get_class_stream(class_level, stream_id)

    assignment = ClassTeacher(
        teacher=teacher,
        class_level=class_level,
        stream=stream,
        term=term,
    )
    _save_assignment(assignment)
    return _serialize_class_teacher_assignment(assignment)


def delete_class_teacher_assignment(school, *, assignment_id):
    term = _get_active_term(school)
    assignment = _get_class_teacher_assignment(school, assignment_id, term)
    assignment.delete()


def create_teaching_assignment(
    school,
    *,
    teacher_id,
    class_subject_id,
    stream_id=None,
    subject_group_id=None,
):
    term = _get_active_term(school)
    teacher = _get_school_teacher(school, teacher_id)
    class_subject = _get_school_class_subject(school, class_subject_id)
    stream = _get_class_stream(class_subject.class_level, stream_id)
    subject_group = _get_subject_group(class_subject, subject_group_id)

    assignment = TeachingAssignment(
        teacher=teacher,
        class_subject=class_subject,
        stream=stream,
        subject_group=subject_group,
        term=term,
    )
    _save_assignment(assignment)
    return _serialize_teaching_assignment(assignment)


def delete_teaching_assignment(school, *, assignment_id):
    term = _get_active_term(school)
    assignment = _get_teaching_assignment(school, assignment_id, term)
    assignment.delete()


def validate_teachers_setup_ready(school):
    _get_active_term(school)

    if not User.objects.filter(
        school=school,
        role=User.RoleChoices.TEACHER,
        is_active=True,
    ).exists():
        raise ValidationError({
            'detail': 'Add at least one active teacher before completing teachers setup.',
        })


def complete_teachers_setup(school):
    school_setup, _ = SchoolSetup.objects.get_or_create(school=school)
    require_prior_setup_steps(
        school_setup,
        SchoolSetup.SetupStep.TEACHERS,
    )
    validate_teachers_setup_ready(school)
    return advance_setup_if_needed(
        school_setup,
        SchoolSetup.SetupStep.TEACHERS,
    )
