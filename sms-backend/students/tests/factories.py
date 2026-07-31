from datetime import date

from academics.models import ClassStream
from students.models import ClassEnrollment, Student


def create_student(
    *,
    school,
    student_id='STU-001',
    first_name='Ama',
    last_name='Mensah',
    other_names='',
    gender=Student.GenderChoices.FEMALE,
    date_of_birth=None,
    admission_date=None,
):
    return Student.objects.create(
        school=school,
        student_id=student_id,
        first_name=first_name,
        last_name=last_name,
        other_names=other_names,
        gender=gender,
        date_of_birth=date_of_birth or date(2010, 1, 15),
        admission_date=admission_date or date(2025, 9, 1),
    )


def ensure_default_stream(class_level):
    stream = ClassStream.objects.filter(
        class_level=class_level,
        is_default=True,
    ).first()
    if stream is None:
        stream = ClassStream.objects.create(
            class_level=class_level,
            is_default=True,
        )
    return stream


def enroll_student(
    *,
    student,
    term,
    class_level=None,
    stream=None,
    is_new_student=False,
):
    if stream is None:
        if class_level is None:
            raise ValueError('Provide stream or class_level.')
        stream = ensure_default_stream(class_level)

    return ClassEnrollment.objects.create(
        student=student,
        term=term,
        stream=stream,
        is_new_student=is_new_student,
    )
