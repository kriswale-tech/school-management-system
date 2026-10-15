"""Open the next term: place pupils, copy teachers, bill, then activate."""

from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from academics.models import ClassLevel, ClassSubject, StudentSubjectGroup, SubjectGroup
from fees.models import FeeStructure
from fees.services.settings import _resolve_applies_to_name
from fees.services.fees import (
    apply_fee_structure,
    ensure_enrollment_fees,
    get_or_create_fee_structure,
    publish_fee_structure,
)
from schools.models import Term
from schools.services.academic_calendar import (
    _unreleased_report_count,
    expected_next_term,
    preview_term_switch,
)
from schools.services.settings import get_school_settings
from students.models import ClassEnrollment, Student
from teachers.models import ClassTeacher, TeachingAssignment

TRANSITION_LEAD_DAYS = 7


def _sid(value):
    return str(value) if value is not None else None


def _stream_key(stream):
    name = (stream.name or '').strip().casefold()
    if stream.is_default or not name:
        return ''
    return name


def _stream_label(stream):
    if stream.is_default or not (stream.name or '').strip():
        return 'Default stream'
    return stream.name


def _ordered_classes(school):
    return list(
        ClassLevel.objects.filter(school=school)
        .select_related('level')
        .order_by('level__order', 'order', 'name')
    )


def _next_active_class(ordered, source_id):
    seen = False
    for class_level in ordered:
        if not seen:
            if class_level.id == source_id:
                seen = True
            continue
        if class_level.is_active and class_level.level.is_active:
            return class_level
    return None


def _active_term(school):
    return (
        Term.objects.filter(school=school, is_active=True)
        .select_related('academic_year')
        .first()
    )


def _matching_stream(source, dest_streams):
    key = _stream_key(source)
    for stream in dest_streams:
        if stream.is_active and _stream_key(stream) == key:
            return stream
    return None


def _student_name(student):
    return ' '.join(
        part for part in (student.first_name, student.last_name) if part
    ).strip()


def _fee_item_row(item):
    return {
        'id': _sid(item.id),
        'name': item.name,
        'amount': f'{item.amount:.2f}',
        'applies_to': _resolve_applies_to_name(item) or 'Unknown',
        'student_type': item.get_student_type_display(),
    }


def _empty_fees():
    return {
        'status': 'missing',
        'locked': False,
        'items': [],
    }


def _fee_snapshot(school, target, active):
    structure = (
        FeeStructure.objects.filter(school=school, term=target)
        .prefetch_related('fee_items')
        .first()
    )
    source_structure = None
    if structure is None:
        source_structure = (
            FeeStructure.objects.filter(school=school, term=active)
            .prefetch_related('fee_items')
            .first()
        )
    items = []
    if structure is not None:
        items = list(structure.fee_items.all())
        status = structure.status
        locked = structure.is_locked
    elif source_structure is not None and source_structure.fee_items.exists():
        items = list(source_structure.fee_items.all())
        status = FeeStructure.Status.CARRIED_FORWARD
        locked = False
    else:
        status = 'missing'
        locked = False

    rows = [
        _fee_item_row(item)
        for item in sorted(items, key=lambda item: item.name.casefold())
    ]
    return {
        'status': status,
        'locked': locked,
        'items': rows,
        '_items': items,
    }


def _placement_groups(school, active, target):
    ordered = _ordered_classes(school)
    is_year_change = active.academic_year_id != target.academic_year_id
    enrollments = list(
        ClassEnrollment.objects.filter(
            term=active,
            student__school=school,
            student__is_active=True,
            student__is_graduated=False,
        ).select_related(
            'student',
            'stream',
            'stream__class_level',
            'stream__class_level__level',
            'class_level',
            'class_level__level',
        )
    )
    already = set(
        ClassEnrollment.objects.filter(
            term=target,
            student_id__in=[row.student_id for row in enrollments],
        ).values_list('student_id', flat=True)
    )
    by_stream = {}
    for enrollment in enrollments:
        by_stream.setdefault(enrollment.stream_id, []).append(enrollment)

    streams = {
        stream.id: stream
        for stream in [
            row.stream for row in enrollments
        ]
    }
    dest_streams = {}
    groups = []
    for stream_id, rows in by_stream.items():
        stream = streams[stream_id]
        pending = [row for row in rows if row.student_id not in already]
        if not pending:
            continue
        source_class = stream.class_level
        if not is_year_change:
            destination_class = source_class
            options = [
                option for option in source_class.streams.all()
                if option.is_active
            ]
            matched = stream if stream.is_active else None
        else:
            destination_class = _next_active_class(ordered, source_class.id)
            options = []
            matched = None
            if destination_class is not None:
                options = [
                    option for option in destination_class.streams.all()
                    if option.is_active
                ]
                matched = _matching_stream(stream, options)

        if is_year_change and destination_class is None:
            outcome = 'graduate'
            destination_stream = None
        elif matched is not None:
            outcome = 'stay' if not is_year_change else 'promote'
            destination_stream = matched
        else:
            outcome = 'needs_stream'
            destination_stream = None

        if destination_class is not None:
            dest_streams.setdefault(destination_class.id, options)

        groups.append({
            'source_stream_id': _sid(stream.id),
            'source_label': stream.full_name,
            'source_class_name': source_class.name,
            'student_count': len(pending),
            'destination_class_id': _sid(destination_class.id) if destination_class else None,
            'destination_class_name': destination_class.name if destination_class else None,
            'destination_stream_id': _sid(destination_stream.id) if destination_stream else None,
            'destination_stream_name': (
                _stream_label(destination_stream) if destination_stream else None
            ),
            'outcome': outcome,
            'stream_options': [
                {'id': _sid(option.id), 'name': _stream_label(option)}
                for option in options
            ],
            '_students': [row.student for row in pending],
            '_source_stream': stream,
            '_source_class': source_class,
            '_destination_class': destination_class,
            '_destination_stream': destination_stream,
        })

    groups.sort(key=lambda group: (group['source_class_name'], group['source_label']))
    return is_year_change, ordered, groups, len(already)


def _public_group(group):
    return {
        key: value
        for key, value in group.items()
        if not key.startswith('_')
    }


def _unenrolled_students(school, active):
    students = (
        Student.objects.filter(school=school, is_active=True, is_graduated=False)
        .exclude(enrollments__term=active)
        .order_by('last_name', 'first_name')
    )
    return [
        {'id': _sid(student.id), 'name': _student_name(student)}
        for student in students
    ]


def build_transition_preview(school, *, today=None):
    today = today or date.today()
    active = _active_term(school)
    blockers = []
    warnings = []
    if active is None:
        return {
            'can_confirm': False,
            'blockers': ['There is no current term to switch from.'],
            'warnings': [],
            'is_year_change': False,
            'term_id': None,
            'term_label': None,
            'placements': [],
            'unenrolled_students': [],
            'already_enrolled_count': 0,
            'graduate_count': 0,
            'unreleased_reports': 0,
            'unmatched_subjects': [],
            'fees': _empty_fees(),
        }

    target = expected_next_term(active)
    switch = preview_term_switch(school, target.id, today=today) if target else None
    if switch:
        blockers.extend(switch['blockers'])
    elif target is None:
        blockers.append('The next term is not set up yet.')

    if target is None or blockers:
        label = None
        if target is not None:
            label = f'{target.get_term_display()} {target.academic_year.academic_year}'
        return {
            'can_confirm': False,
            'blockers': blockers,
            'warnings': warnings,
            'is_year_change': bool(
                target and active.academic_year_id != target.academic_year_id
            ),
            'term_id': _sid(target.id) if target else None,
            'term_label': label,
            'placements': [],
            'unenrolled_students': _unenrolled_students(school, active),
            'already_enrolled_count': 0,
            'graduate_count': 0,
            'unreleased_reports': _unreleased_report_count(school=school, term=active),
            'unmatched_subjects': [],
            'fees': _empty_fees(),
        }

    is_year_change, _, groups, already_count = _placement_groups(school, active, target)
    for group in groups:
        if group['outcome'] == 'needs_stream' and not group['stream_options']:
            class_name = group['destination_class_name'] or group['source_class_name']
            blockers.append(f'{class_name} has no stream for {group["source_label"]}.')

    fee = _fee_snapshot(school, target, active)
    if fee['status'] == 'missing':
        blockers.append('The next term has no fee catalog yet.')
    elif not fee['_items']:
        blockers.append("The next term's fee catalog has no items.")

    unreleased = _unreleased_report_count(school=school, term=active)
    if unreleased:
        noun = 'report is' if unreleased == 1 else 'reports are'
        warnings.append(f'{unreleased} {noun} still unreleased on the current term.')

    unenrolled = _unenrolled_students(school, active)
    if unenrolled:
        count = len(unenrolled)
        noun = 'pupil is' if count == 1 else 'pupils are'
        warnings.append(
            f'{count} active {noun} not in a class this term and will not be moved.'
        )

    if today < target.start_date:
        warnings.append(
            f'This term starts on {target.start_date.isoformat()}. Today is still before then.'
        )

    graduate_count = sum(
        group['student_count'] for group in groups if group['outcome'] == 'graduate'
    )
    needs_choice = any(group['outcome'] == 'needs_stream' for group in groups)
    return {
        'can_confirm': not blockers and not needs_choice,
        'blockers': blockers,
        'warnings': warnings,
        'is_year_change': is_year_change,
        'term_id': _sid(target.id),
        'term_label': f'{target.get_term_display()} {target.academic_year.academic_year}',
        'placements': [_public_group(group) for group in groups],
        'unenrolled_students': unenrolled,
        'already_enrolled_count': already_count,
        'graduate_count': graduate_count,
        'unreleased_reports': unreleased,
        'unmatched_subjects': [],
        'fees': {
            'status': fee['status'],
            'locked': fee['locked'],
            'items': fee['items'],
        },
    }


def _resolve_destinations(groups, stream_choices):
    choices = {
        item['source_stream_id']: item['destination_stream_id']
        for item in stream_choices
    }
    resolved = []
    errors = []
    for group in groups:
        destination_stream = group['_destination_stream']
        if group['outcome'] == 'needs_stream':
            chosen = choices.get(group['source_stream_id'])
            allowed = {option['id']: option for option in group['stream_options']}
            if chosen not in allowed:
                errors.append(
                    f'Choose a stream for {group["source_label"]}.'
                )
                continue
            from academics.models import ClassStream

            destination_stream = ClassStream.objects.select_related('class_level').get(id=chosen)
        resolved.append({
            **group,
            '_destination_stream': destination_stream,
        })
    if errors:
        raise ValidationError({'streams': errors})
    return resolved


def _copy_class_teachers(active, target, resolved):
    notes = []
    seen = set()
    for group in resolved:
        if group['outcome'] == 'graduate':
            continue
        source_stream = group['_source_stream']
        destination_stream = group['_destination_stream']
        destination_class = group['_destination_class']
        assignments = ClassTeacher.objects.filter(term=active).filter(
            stream=source_stream,
        ) | ClassTeacher.objects.filter(
            term=active,
            class_level=source_stream.class_level,
            stream__isnull=True,
        )
        for assignment in assignments.select_related('teacher'):
            stream = None if assignment.stream_id is None else destination_stream
            key = (assignment.teacher_id, destination_class.id, getattr(stream, 'id', None))
            if key in seen:
                continue
            seen.add(key)
            exists = ClassTeacher.objects.filter(
                term=target,
                class_level=destination_class,
                stream=stream,
            ).exists()
            if exists:
                continue
            try:
                ClassTeacher.objects.create(
                    teacher=assignment.teacher,
                    class_level=destination_class,
                    stream=stream,
                    term=target,
                )
            except DjangoValidationError:
                notes.append(
                    f'{assignment.teacher.get_full_name()} could not be copied to '
                    f'{destination_class.name}.'
                )
    return notes


def _copy_teaching_assignments(active, target, resolved):
    notes = []
    copied_classwide = set()
    for group in resolved:
        if group['outcome'] == 'graduate':
            continue
        source_class = group['_source_class']
        destination_class = group['_destination_class']
        destination_stream = group['_destination_stream']
        subjects = {
            row.subject.name.casefold(): row
            for row in ClassSubject.objects.filter(
                class_level=destination_class,
                is_active=True,
            ).select_related('subject')
        }
        assignments = TeachingAssignment.objects.filter(
            term=active,
            class_subject__class_level=source_class,
        ).select_related('teacher', 'class_subject__subject', 'subject_group', 'stream')
        for assignment in assignments:
            if assignment.stream_id and assignment.stream_id != group['_source_stream'].id:
                continue
            if assignment.stream_id is None and assignment.subject_group_id is None:
                key = (assignment.id, destination_class.id)
                if key in copied_classwide:
                    continue
                copied_classwide.add(key)
            subject_name = assignment.class_subject.subject.name
            dest_subject = subjects.get(subject_name.casefold())
            if dest_subject is None:
                notes.append(
                    f'{subject_name} has no match on {destination_class.name}.'
                )
                continue
            dest_group = None
            if assignment.subject_group_id:
                dest_group = SubjectGroup.objects.filter(
                    class_subject=dest_subject,
                    name__iexact=assignment.subject_group.name,
                    is_active=True,
                ).first()
                if dest_group is None:
                    notes.append(
                        f'{subject_name} on {destination_class.name} has no '
                        f'{assignment.subject_group.name} group.'
                    )
                    continue
            stream = destination_stream if assignment.stream_id else None
            exists = TeachingAssignment.objects.filter(
                term=target,
                class_subject=dest_subject,
                stream=stream,
                subject_group=dest_group,
            ).exists()
            if exists:
                continue
            try:
                TeachingAssignment.objects.create(
                    teacher=assignment.teacher,
                    class_subject=dest_subject,
                    stream=stream,
                    subject_group=dest_group,
                    term=target,
                )
            except DjangoValidationError:
                notes.append(
                    f'{assignment.teacher.get_full_name()} could not be copied onto '
                    f'{subject_name}.'
                )
    return list(dict.fromkeys(notes))


def _copy_subject_groups(active, target, resolved):
    if active.academic_year_id == target.academic_year_id:
        return []
    notes = []
    for group in resolved:
        if group['outcome'] == 'graduate':
            continue
        destination_class = group['_destination_class']
        subjects = {
            row.subject.name.casefold(): row
            for row in ClassSubject.objects.filter(
                class_level=destination_class,
                is_active=True,
            ).select_related('subject')
        }
        student_ids = [student.id for student in group['_students']]
        placements = StudentSubjectGroup.objects.filter(
            academic_year=active.academic_year,
            student_id__in=student_ids,
            class_subject__class_level=group['_source_class'],
        ).select_related('subject_group', 'class_subject__subject')
        missing = {}
        for placement in placements:
            subject_name = placement.class_subject.subject.name
            dest_subject = subjects.get(subject_name.casefold())
            dest_group = None
            if dest_subject is not None:
                dest_group = SubjectGroup.objects.filter(
                    class_subject=dest_subject,
                    name__iexact=placement.subject_group.name,
                    is_active=True,
                ).first()
            if dest_group is None:
                missing.setdefault(
                    (subject_name, placement.subject_group.name, destination_class.name),
                    0,
                )
                missing[(subject_name, placement.subject_group.name, destination_class.name)] += 1
                continue
            StudentSubjectGroup.objects.get_or_create(
                student_id=placement.student_id,
                class_subject=dest_subject,
                academic_year=target.academic_year,
                defaults={'subject_group': dest_group},
            )
        for (subject_name, group_name, class_name), count in missing.items():
            noun = 'pupil was' if count == 1 else 'pupils were'
            notes.append(
                f'{subject_name} on {class_name} has no {group_name} group, '
                f'so {count} {noun} not placed.'
            )
    return notes


def _bill_target(school, target, user):
    existing = FeeStructure.objects.filter(school=school, term=target).first()
    if existing is None:
        previous = FeeStructure.objects.filter(school=school, term__school=school).filter(
            term__start_date__lt=target.start_date,
        )
        if not previous.exists():
            raise ValidationError({'fees': 'The next term has no fee catalog yet.'})
    structure = get_or_create_fee_structure(school=school, term=target, created_by=user)
    if structure.status == FeeStructure.Status.APPLIED:
        return structure
    if not structure.fee_items.exists():
        raise ValidationError({'fees': "The next term's fee catalog has no items."})
    if structure.status == FeeStructure.Status.DRAFT:
        publish_fee_structure(structure)
    apply_fee_structure(structure)
    return structure


@transaction.atomic
def confirm_transition(
    school,
    user,
    *,
    stream_choices,
    acknowledge_warnings,
    today=None,
):
    today = today or date.today()
    active = _active_term(school)
    target = expected_next_term(active) if active else None
    preview = build_transition_preview(school, today=today)
    if preview['blockers']:
        raise ValidationError({'detail': ' '.join(preview['blockers'])})
    if target is None or active is None:
        raise ValidationError({'detail': 'The next term is not set up yet.'})

    _, _, groups, _already = _placement_groups(school, active, target)
    resolved = _resolve_destinations(groups, stream_choices)

    warnings = list(preview['warnings'])
    for note in _unmatched_subject_notes(active, resolved):
        if note not in warnings:
            warnings.append(note)
    for note in _copy_subject_group_notes_preview(active, target, resolved):
        if note not in warnings:
            warnings.append(note)

    if warnings and not acknowledge_warnings:
        raise ValidationError({'warnings': warnings})

    created = []
    for group in resolved:
        if group['outcome'] == 'graduate':
            student_ids = [student.id for student in group['_students']]
            Student.objects.filter(id__in=student_ids, school=school).update(is_graduated=True)
            continue
        destination_stream = group['_destination_stream']
        for student in group['_students']:
            enrollment = ClassEnrollment(
                student=student,
                term=target,
                stream=destination_stream,
                is_new_student=False,
            )
            enrollment.save()
            created.append(enrollment)

    _copy_class_teachers(active, target, resolved)
    _copy_teaching_assignments(active, target, resolved)
    _copy_subject_groups(active, target, resolved)

    structure = FeeStructure.objects.filter(school=school, term=target).first()
    already_applied = bool(structure and structure.status == FeeStructure.Status.APPLIED)
    if already_applied:
        for enrollment in created:
            ensure_enrollment_fees(enrollment)
    else:
        _bill_target(school, target, user)

    from schools.services.academic_calendar import activate_term

    return activate_term(
        school,
        target.id,
        acknowledge_warnings=True,
        today=today,
    )


def _unmatched_subject_notes(active, resolved):
    notes = []
    seen = set()
    for group in resolved:
        if group['outcome'] == 'graduate':
            continue
        destination_class = group['_destination_class']
        subjects = {
            row.subject.name.casefold()
            for row in ClassSubject.objects.filter(
                class_level=destination_class,
                is_active=True,
            ).select_related('subject')
        }
        assignments = TeachingAssignment.objects.filter(
            term=active,
            class_subject__class_level=group['_source_class'],
        ).select_related('class_subject__subject')
        for assignment in assignments:
            if assignment.stream_id and assignment.stream_id != group['_source_stream'].id:
                continue
            subject_name = assignment.class_subject.subject.name
            if subject_name.casefold() in subjects:
                continue
            key = (subject_name, destination_class.name)
            if key in seen:
                continue
            seen.add(key)
            notes.append(f'{subject_name} has no match on {destination_class.name}.')
    return notes


def _copy_subject_group_notes_preview(active, target, resolved):
    if active.academic_year_id == target.academic_year_id:
        return []
    notes = []
    for group in resolved:
        if group['outcome'] == 'graduate':
            continue
        destination_class = group['_destination_class']
        subjects = {
            row.subject.name.casefold(): row
            for row in ClassSubject.objects.filter(
                class_level=destination_class,
                is_active=True,
            ).select_related('subject')
        }
        student_ids = [student.id for student in group['_students']]
        placements = StudentSubjectGroup.objects.filter(
            academic_year=active.academic_year,
            student_id__in=student_ids,
            class_subject__class_level=group['_source_class'],
        ).select_related('subject_group', 'class_subject__subject')
        missing = set()
        for placement in placements:
            subject_name = placement.class_subject.subject.name
            dest_subject = subjects.get(subject_name.casefold())
            dest_group = None
            if dest_subject is not None:
                dest_group = SubjectGroup.objects.filter(
                    class_subject=dest_subject,
                    name__iexact=placement.subject_group.name,
                    is_active=True,
                ).first()
            if dest_group is None:
                missing.add((subject_name, placement.subject_group.name, destination_class.name))
        for subject_name, group_name, class_name in missing:
            notes.append(
                f'{subject_name} on {class_name} has no {group_name} group, '
                'so those pupils will not be placed in it.'
            )
    return notes


def transition_status(school, *, today=None):
    today = today or date.today()
    active = _active_term(school)
    settings_row = get_school_settings(school)
    empty = {
        'visible': False,
        'urgency': None,
        'title': '',
        'days_remaining': None,
        'term_ends_on': None,
        'popup_enabled': settings_row.transition_popup_enabled,
        'unfinished_count': 0,
        'checklist': [],
        'term_label': None,
    }
    if active is None:
        return empty

    days_remaining = (active.end_date - today).days
    visible = days_remaining <= TRANSITION_LEAD_DAYS
    target = expected_next_term(active)
    preview = build_transition_preview(school, today=today) if visible else None
    checklist = []
    if visible:
        if target is None:
            checklist.append({
                'kind': 'next_term',
                'title': 'Add the next term',
                'summary': 'The next term is not on the calendar yet.',
                'done': False,
                'href': '/settings/academic-year',
            })
        else:
            checklist.append({
                'kind': 'next_term',
                'title': 'Next term is set',
                'summary': f'{target.get_term_display()} {target.academic_year.academic_year}',
                'done': True,
                'href': '/settings/academic-year',
            })
        unreleased = preview['unreleased_reports'] if preview else 0
        checklist.append({
            'kind': 'reports',
            'title': 'Release reports',
            'summary': (
                'Reports for this term are released.'
                if unreleased == 0
                else f'{unreleased} still unreleased.'
            ),
            'done': unreleased == 0,
            'href': '/assessments',
        })
        fee_status = (preview or {}).get('fees', {}).get('status', 'missing')
        fee_locked = (preview or {}).get('fees', {}).get('locked', False)
        if fee_status == 'missing':
            fee_summary = 'The next term has no fee catalog yet.'
        elif fee_locked:
            fee_summary = 'Fees for the next term are applied.'
        else:
            fee_summary = 'Review and apply the next term’s fee catalog in the transition.'
        checklist.append({
            'kind': 'fees',
            'title': 'Next term fees',
            'summary': fee_summary,
            'done': fee_locked,
            'href': '/fees/settings',
        })
        if preview and preview['is_year_change']:
            needs_stream = any(
                row['outcome'] == 'needs_stream' for row in preview['placements']
            )
            no_stream = any(
                'has no stream' in blocker for blocker in preview['blockers']
            )
            checklist.append({
                'kind': 'streams',
                'title': 'Match class streams',
                'summary': (
                    'A destination class has no matching stream. Choose where those pupils go.'
                    if needs_stream or no_stream
                    else 'Every class has a matching stream.'
                ),
                'done': not needs_stream and not no_stream,
                'href': '/settings/classes',
            })
            checklist.append({
                'kind': 'graduation',
                'title': 'Pupils leaving',
                'summary': (
                    f'{preview["graduate_count"]} will be marked graduated and not enrolled.'
                    if preview['graduate_count']
                    else 'No class is at the end of the school.'
                ),
                'done': True,
                'href': None,
            })
    unfinished = sum(1 for item in checklist if not item['done'])
    if days_remaining >= 0:
        title = f'Term ends {active.end_date.isoformat()}'
    else:
        title = f'Term ended {active.end_date.isoformat()}. Next term is not open.'
    if unfinished:
        noun = 'action' if unfinished == 1 else 'actions'
        title = f'{title}. {unfinished} {noun} left.'

    return {
        'visible': visible,
        'urgency': 'red' if days_remaining <= 7 else 'amber',
        'title': title,
        'days_remaining': days_remaining,
        'term_ends_on': active.end_date.isoformat(),
        'popup_enabled': settings_row.transition_popup_enabled,
        'unfinished_count': unfinished,
        'checklist': checklist,
        'term_label': preview['term_label'] if preview else None,
    }
