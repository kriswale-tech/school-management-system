"""Publish a new Ghana curriculum version and adopt it school by school.

Publishing leaves every existing school on the version it was provisioned from.
Adoption adds what is new, retires what the new version dropped, and keeps a
taught name on the historical row when a rename already has marks.
"""

from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from academics.curriculum_guard import allow_curriculum_writes
from academics.mixins import allow_system_record_writes
from academics.services.curriculum import GHANA_CURRICULUM_CODE, get_active_curriculum

GHANA_CURRICULUM_NAME = 'Ghana Education Curriculum'


def _parse_uuid(value, label):
    if not value:
        return uuid.uuid4()
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise ValidationError(f'{label} is not a valid id.') from exc


def next_version_label(current: str) -> str:
    text = (current or '').strip()
    if text.isdigit() and len(text) == 4:
        return str(int(text) + 1)
    return f'{text}-2' if text else '2025'


def _active():
    from academics.models import Curriculum

    curriculum = (
        Curriculum.objects.filter(
            code=GHANA_CURRICULUM_CODE,
            is_active=True,
            status=Curriculum.Status.PUBLISHED,
        )
        .order_by('-published_at', '-version')
        .first()
    )
    return curriculum or get_active_curriculum()


def _draft():
    from academics.models import Curriculum

    return Curriculum.objects.filter(
        code=GHANA_CURRICULUM_CODE,
        status=Curriculum.Status.DRAFT,
    ).first()


def serialize_curriculum(curriculum) -> dict:
    levels = []
    queryset = curriculum.levels.prefetch_related('class_levels__subjects', 'subjects').order_by(
        'order',
        'name',
    )
    for level in queryset:
        class_rows = []
        for class_template in level.class_levels.all():
            class_subjects = [
                {
                    'lineage_id': str(subject.lineage_id),
                    'name': subject.name,
                }
                for subject in class_template.subjects.all()
            ]
            class_rows.append({
                'lineage_id': str(class_template.lineage_id),
                'name': class_template.name,
                'order': class_template.order,
                'subjects': class_subjects,
            })
        level_subjects = [
            {'lineage_id': str(subject.lineage_id), 'name': subject.name}
            for subject in level.subjects.all()
            if subject.curriculum_class_level_id is None
        ]
        levels.append({
            'lineage_id': str(level.lineage_id),
            'name': level.name,
            'description': level.description or '',
            'order': level.order,
            'subject_scope': level.subject_scope,
            'allows_custom_classes': level.allows_custom_classes,
            'classes': class_rows,
            'subjects': level_subjects,
        })
    return {
        'id': str(curriculum.id),
        'name': curriculum.name,
        'code': curriculum.code,
        'version': curriculum.version,
        'status': curriculum.status,
        'is_active': curriculum.is_active,
        'published_at': curriculum.published_at,
        'levels': levels,
    }


def curriculum_overview() -> dict:
    from schools.models import School

    active = _active()
    draft = _draft()
    behind = []
    if active is not None:
        behind = [
            {
                'id': str(school.id),
                'name': school.name,
                'version': school.provisioned_curriculum.version,
            }
            for school in School.objects.filter(provisioned_curriculum__isnull=False)
            .exclude(provisioned_curriculum=active)
            .select_related('provisioned_curriculum')
            .order_by('name')
        ]
    versions = []
    from django.db.models import Count

    from academics.models import Curriculum

    published = (
        Curriculum.objects.filter(
            code=GHANA_CURRICULUM_CODE,
            status=Curriculum.Status.PUBLISHED,
        )
        .annotate(school_count=Count('schools'))
        .order_by('-is_active', '-published_at', '-version')
    )
    for row in published:
        payload = serialize_curriculum(row)
        payload['school_count'] = row.school_count
        versions.append(payload)
    return {
        'active': serialize_curriculum(active) if active else None,
        'draft': serialize_curriculum(draft) if draft else None,
        'versions': versions,
        'schools_behind': behind,
    }


def _require_draft(curriculum_id):
    from academics.models import Curriculum

    curriculum = Curriculum.objects.filter(pk=curriculum_id).first()
    if curriculum is None:
        raise ValidationError('Curriculum version not found.')
    if curriculum.status != Curriculum.Status.DRAFT:
        raise ValidationError('Only a draft can be edited.')
    return curriculum


@transaction.atomic
def start_draft():
    from academics.models import Curriculum, CurriculumClassLevel, CurriculumLevel, CurriculumSubject

    if _draft() is not None:
        raise ValidationError('A draft is already open. Publish or keep editing it.')
    active = _active()
    version = next_version_label(active.version)
    if Curriculum.objects.filter(code=GHANA_CURRICULUM_CODE, version=version).exists():
        version = f'{version}-{uuid.uuid4().hex[:4]}'
    with allow_curriculum_writes():
        draft = Curriculum.objects.create(
            name=GHANA_CURRICULUM_NAME,
            code=GHANA_CURRICULUM_CODE,
            version=version,
            status=Curriculum.Status.DRAFT,
            is_active=False,
        )
        for level in active.levels.prefetch_related('class_levels', 'subjects').order_by('order'):
            new_level = CurriculumLevel.objects.create(
                curriculum=draft,
                lineage_id=level.lineage_id,
                name=level.name,
                description=level.description,
                subject_scope=level.subject_scope,
                allows_custom_classes=level.allows_custom_classes,
                order=level.order,
            )
            class_map = {}
            for class_template in level.class_levels.all():
                class_map[class_template.id] = CurriculumClassLevel.objects.create(
                    level=new_level,
                    lineage_id=class_template.lineage_id,
                    name=class_template.name,
                    order=class_template.order,
                )
            for subject in level.subjects.all():
                CurriculumSubject.objects.create(
                    level=new_level,
                    curriculum_class_level=class_map.get(subject.curriculum_class_level_id),
                    lineage_id=subject.lineage_id,
                    name=subject.name,
                )
    return serialize_curriculum(draft)


def _clean_levels(payload) -> list[dict]:
    if not isinstance(payload, list) or not payload:
        raise ValidationError('A version needs at least one level.')
    cleaned = []
    seen_levels = set()
    for index, raw in enumerate(payload, start=1):
        name = str(raw.get('name') or '').strip()
        if not name:
            raise ValidationError('Every level needs a name.')
        lineage = _parse_uuid(raw.get('lineage_id'), 'Level')
        if lineage in seen_levels:
            raise ValidationError(f'Level "{name}" is listed twice.')
        seen_levels.add(lineage)
        scope = raw.get('subject_scope') or 'level'
        if scope not in ('level', 'class'):
            raise ValidationError(f'Level "{name}" has an unknown subject scope.')
        classes = []
        seen_classes = set()
        for class_index, class_raw in enumerate(raw.get('classes') or [], start=1):
            class_name = str(class_raw.get('name') or '').strip()
            if not class_name:
                raise ValidationError(f'A class on {name} needs a name.')
            class_lineage = _parse_uuid(class_raw.get('lineage_id'), 'Class')
            if class_lineage in seen_classes:
                raise ValidationError(f'Class "{class_name}" is listed twice.')
            seen_classes.add(class_lineage)
            class_subjects = _clean_subjects(class_raw.get('subjects') or [], f'{name} / {class_name}')
            classes.append({
                'lineage_id': class_lineage,
                'name': class_name,
                'order': int(class_raw.get('order') or class_index),
                'subjects': class_subjects,
            })
        subjects = _clean_subjects(raw.get('subjects') or [], name) if scope == 'level' else []
        cleaned.append({
            'lineage_id': lineage,
            'name': name,
            'description': str(raw.get('description') or '').strip(),
            'order': int(raw.get('order') or index),
            'subject_scope': scope,
            'allows_custom_classes': bool(raw.get('allows_custom_classes')),
            'classes': classes,
            'subjects': subjects,
        })
    return cleaned


def _clean_subjects(rows, label) -> list[dict]:
    cleaned = []
    seen = set()
    for raw in rows:
        name = str(raw.get('name') or '').strip()
        if not name:
            continue
        lineage = _parse_uuid(raw.get('lineage_id'), 'Subject')
        if lineage in seen or name.casefold() in {item['name'].casefold() for item in cleaned}:
            raise ValidationError(f'Subject "{name}" is listed twice on {label}.')
        seen.add(lineage)
        cleaned.append({'lineage_id': lineage, 'name': name})
    return cleaned


@transaction.atomic
def save_draft(curriculum_id, *, version: str, levels) -> dict:
    from academics.models import Curriculum, CurriculumClassLevel, CurriculumLevel, CurriculumSubject

    curriculum = _require_draft(curriculum_id)
    version = (version or '').strip()
    if not version:
        raise ValidationError('A version label is required.')
    if Curriculum.objects.exclude(pk=curriculum.pk).filter(
        code=GHANA_CURRICULUM_CODE,
        version=version,
    ).exists():
        raise ValidationError(f'Version {version} already exists.')
    cleaned = _clean_levels(levels)
    with allow_curriculum_writes():
        curriculum.version = version
        curriculum.save(update_fields=['version', 'updated_at'])
        curriculum.levels.all().delete()
        for level_data in cleaned:
            level = CurriculumLevel.objects.create(
                curriculum=curriculum,
                lineage_id=level_data['lineage_id'],
                name=level_data['name'],
                description=level_data['description'],
                subject_scope=level_data['subject_scope'],
                allows_custom_classes=level_data['allows_custom_classes'],
                order=level_data['order'],
            )
            class_map = {}
            for class_data in level_data['classes']:
                class_map[class_data['lineage_id']] = CurriculumClassLevel.objects.create(
                    level=level,
                    lineage_id=class_data['lineage_id'],
                    name=class_data['name'],
                    order=class_data['order'],
                )
            if level_data['subject_scope'] == 'level':
                for subject in level_data['subjects']:
                    CurriculumSubject.objects.create(
                        level=level,
                        lineage_id=subject['lineage_id'],
                        name=subject['name'],
                    )
            else:
                for class_data in level_data['classes']:
                    class_template = class_map[class_data['lineage_id']]
                    for subject in class_data['subjects']:
                        CurriculumSubject.objects.create(
                            level=level,
                            curriculum_class_level=class_template,
                            lineage_id=subject['lineage_id'],
                            name=subject['name'],
                        )
    curriculum.refresh_from_db()
    return serialize_curriculum(curriculum)


@transaction.atomic
def publish_draft(curriculum_id) -> dict:
    from academics.models import Curriculum

    curriculum = _require_draft(curriculum_id)
    if not curriculum.levels.exists():
        raise ValidationError('Add at least one level before publishing.')
    now = timezone.now()
    with allow_curriculum_writes():
        Curriculum.objects.filter(
            code=GHANA_CURRICULUM_CODE,
            is_active=True,
        ).update(is_active=False)
        curriculum.status = Curriculum.Status.PUBLISHED
        curriculum.is_active = True
        curriculum.published_at = now
        curriculum.save(update_fields=['status', 'is_active', 'published_at', 'updated_at'])
    from schools.models import School

    schools = list(
        School.objects.filter(provisioned_curriculum__isnull=False)
        .exclude(provisioned_curriculum=curriculum)
        .select_related('provisioned_curriculum')
        .order_by('name')
    )
    _email_curriculum_published(curriculum, schools)
    return {
        'curriculum': serialize_curriculum(curriculum),
        'schools_alerted': len(schools),
    }


def _email_curriculum_published(curriculum, schools) -> None:
    """Tell each school still on an older version. A mail failure does not undo publish."""
    from django.conf import settings
    from django.core.mail import send_mail

    from accounts.models import SchoolMembership, User

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'noreply@schoolasst.local'
    base = getattr(settings, 'FRONTEND_URL', 'http://localhost:3003').rstrip('/')
    link = f'{base}/classes/manage'
    subject = f'{curriculum.name} {curriculum.version} is ready'
    for school in schools:
        recipients: list[str] = []
        school_email = (school.email or '').strip()
        if school_email:
            recipients.append(school_email)
        admin_emails = SchoolMembership.objects.filter(
            school=school,
            is_active=True,
            role=User.RoleChoices.ADMIN,
        ).values_list('user__email', flat=True)
        for email in admin_emails:
            cleaned = (email or '').strip()
            if cleaned and cleaned not in recipients:
                recipients.append(cleaned)
        if not recipients:
            continue
        current = (
            school.provisioned_curriculum.version
            if school.provisioned_curriculum_id
            else 'an older version'
        )
        body = (
            f'{school.name} is on curriculum {current}.\n\n'
            f'{curriculum.name} {curriculum.version} is ready. '
            'The term already in progress stays as it is. '
            'When the school adopts this version, the new classes and subjects '
            'take effect at the start of the next term.\n\n'
            f'{link}\n'
        )
        try:
            send_mail(subject, body, from_email, recipients, fail_silently=True)
        except Exception:
            continue


def pending_update(school):
    active = _active()
    if active is None or school.provisioned_curriculum_id is None:
        return None
    if school.provisioned_curriculum_id == active.id:
        return None
    if school.accepted_curriculum_id == active.id:
        return None
    return active


def _has_open_term(school) -> bool:
    from schools.models import Term

    return Term.objects.filter(school=school, is_active=True).exists()


def _timing_copy(*, has_term: bool) -> str:
    if has_term:
        return (
            'This term stays as it is. The new classes and subjects take effect '
            'when the next term starts.'
        )
    return 'No term is open, so adopting applies this version now.'


def _class_has_history(class_level) -> bool:
    from assessments.models import StudentResult
    from students.models import ClassEnrollment
    from teachers.models import ClassTeacher

    return (
        ClassEnrollment.objects.filter(class_level=class_level).exists()
        or StudentResult.objects.filter(class_level=class_level).exists()
        or ClassTeacher.objects.filter(class_level=class_level).exists()
    )


def _subject_has_history(subject) -> bool:
    from teachers.models import TeachingAssignment

    return TeachingAssignment.objects.filter(class_subject__subject=subject).exists()


def _level_has_history(level) -> bool:
    return any(_class_has_history(class_level) for class_level in level.class_levels.all())


def plan_adoption(school) -> dict:
    active = _active()
    current = school.provisioned_curriculum
    has_term = _has_open_term(school)
    applies_on = 'next_term' if has_term else 'now'
    base = {
        'from_version': current.version if current is not None else None,
        'to_version': active.version,
        'to_id': str(active.id),
        'applies_on': applies_on,
        'summary': _timing_copy(has_term=has_term),
        'scheduled': False,
        'applied': False,
    }
    if current is not None and current.id == active.id:
        return {**base, 'up_to_date': True, 'changes': []}
    if school.accepted_curriculum_id == active.id:
        return {
            **base,
            'up_to_date': True,
            'scheduled': True,
            'applies_on': 'next_term',
            'summary': (
                f'Version {active.version} is accepted. This term stays as it is. '
                'The new classes and subjects take effect when the next term starts.'
            ),
            'changes': [],
        }
    return {
        **base,
        'up_to_date': False,
        'changes': _plan_changes(school, active),
    }


def _indexed_school_levels(school):
    from academics.models import Level

    by_lineage = {}
    for level in Level.objects.filter(school=school, is_system_generated=True).select_related(
        'curriculum_level',
    ):
        if level.curriculum_level_id:
            by_lineage[level.curriculum_level.lineage_id] = level
    return by_lineage


def _plan_changes(school, target) -> list[dict]:
    from academics.models import Level

    if not Level.objects.filter(school=school).exists():
        return [{
            'action': 'add',
            'kind': 'curriculum',
            'summary': f'Copy {target.name} {target.version} onto this school.',
        }]
    changes = []
    school_levels = _indexed_school_levels(school)
    target_level_lineages = set()
    for level in target.levels.prefetch_related('class_levels__subjects', 'subjects').order_by('order'):
        target_level_lineages.add(level.lineage_id)
        current = school_levels.get(level.lineage_id)
        if current is None:
            changes.append({
                'action': 'add',
                'kind': 'level',
                'summary': f'Add level {level.name}.',
            })
            continue
        if current.name != level.name:
            if _level_has_history(current):
                changes.append({
                    'action': 'preserve',
                    'kind': 'level',
                    'summary': (
                        f'{current.name} already has classes with records. '
                        f'It stays, and {level.name} is added going forward.'
                    ),
                })
            else:
                changes.append({
                    'action': 'rename',
                    'kind': 'level',
                    'summary': f'Rename level {current.name} to {level.name}.',
                })
        changes.extend(_plan_classes(current, level))
        changes.extend(_plan_subjects(current, level))
    for lineage, current in school_levels.items():
        if lineage not in target_level_lineages and current.is_active:
            changes.append({
                'action': 'retire',
                'kind': 'level',
                'summary': f'Retire level {current.name}. Past records stay.',
            })
    unique = []
    seen = set()
    for change in changes:
        key = (change['action'], change['summary'])
        if key in seen:
            continue
        seen.add(key)
        unique.append(change)
    return unique


def _plan_classes(school_level, level_template) -> list[dict]:
    from academics.models import ClassLevel

    current_by_lineage = {
        row.curriculum_class_level.lineage_id: row
        for row in ClassLevel.objects.filter(
            level=school_level,
            is_system_generated=True,
            curriculum_class_level__isnull=False,
        ).select_related('curriculum_class_level')
    }
    target_lineages = set()
    changes = []
    for class_template in level_template.class_levels.all():
        target_lineages.add(class_template.lineage_id)
        current = current_by_lineage.get(class_template.lineage_id)
        if current is None:
            changes.append({
                'action': 'add',
                'kind': 'class',
                'summary': f'Add class {class_template.name} under {level_template.name}.',
            })
        elif current.name != class_template.name:
            if _class_has_history(current):
                changes.append({
                    'action': 'preserve',
                    'kind': 'class',
                    'summary': (
                        f'{current.name} already has records. It stays, and '
                        f'{class_template.name} is added going forward.'
                    ),
                })
            else:
                changes.append({
                    'action': 'rename',
                    'kind': 'class',
                    'summary': f'Rename class {current.name} to {class_template.name}.',
                })
    for lineage, current in current_by_lineage.items():
        if lineage not in target_lineages and current.is_active:
            changes.append({
                'action': 'retire',
                'kind': 'class',
                'summary': f'Retire class {current.name}. Past records stay.',
            })
    return changes


def _target_subject_rows(level_template):
    rows = []
    if level_template.subject_scope == 'level':
        for subject in level_template.subjects.all():
            if subject.curriculum_class_level_id is None:
                rows.append(subject)
    else:
        rows.extend(list(level_template.subjects.all()))
    return rows


def _present_subject_lineages(school_level):
    """Lineages already on the school, including a subject shared by several classes.

    Pre-School stores one template row per class. Nursery 1 and Nursery 2 share
    names, and the school keeps a single subject. The level link points at one
    of those rows; the other classes still have the subject.
    """
    from academics.models import ClassSubject, LevelSubject

    lineages = set(
        LevelSubject.objects.filter(
            level=school_level,
            is_system_generated=True,
            curriculum_subject__isnull=False,
        ).values_list('curriculum_subject__lineage_id', flat=True)
    )
    lineages.update(
        ClassSubject.objects.filter(
            class_level__level=school_level,
            is_system_generated=True,
            curriculum_subject__isnull=False,
        ).values_list('curriculum_subject__lineage_id', flat=True)
    )
    return lineages


def _present_subject_names(school_level):
    from academics.models import ClassSubject, LevelSubject

    names = {
        name.casefold()
        for name in LevelSubject.objects.filter(
            level=school_level,
            is_system_generated=True,
            is_active=True,
        ).values_list('subject__name', flat=True)
        if name
    }
    names.update(
        name.casefold()
        for name in ClassSubject.objects.filter(
            class_level__level=school_level,
            is_system_generated=True,
            is_active=True,
        ).values_list('subject__name', flat=True)
        if name
    )
    return names


def _plan_subjects(school_level, level_template) -> list[dict]:
    from academics.models import LevelSubject

    current_by_lineage = {}
    for row in LevelSubject.objects.filter(
        level=school_level,
        is_system_generated=True,
        curriculum_subject__isnull=False,
    ).select_related('curriculum_subject', 'subject'):
        current_by_lineage[row.curriculum_subject.lineage_id] = row
    present_lineages = _present_subject_lineages(school_level)
    present_names = _present_subject_names(school_level)
    target_lineages = set()
    changes = []
    for subject in _target_subject_rows(level_template):
        target_lineages.add(subject.lineage_id)
        current = current_by_lineage.get(subject.lineage_id)
        if current is None and (
            subject.lineage_id in present_lineages or subject.name.casefold() in present_names
        ):
            continue
        if current is None:
            changes.append({
                'action': 'add',
                'kind': 'subject',
                'summary': f'Add subject {subject.name} to {level_template.name}.',
            })
        elif current.subject.name != subject.name:
            if _subject_has_history(current.subject):
                changes.append({
                    'action': 'preserve',
                    'kind': 'subject',
                    'summary': (
                        f'{current.subject.name} has already been taught. It stays on record, '
                        f'and {subject.name} is added going forward.'
                    ),
                })
            else:
                changes.append({
                    'action': 'rename',
                    'kind': 'subject',
                    'summary': (
                        f'Rename subject {current.subject.name} to {subject.name}.'
                    ),
                })
    for lineage, current in current_by_lineage.items():
        if lineage not in target_lineages and current.is_active:
            changes.append({
                'action': 'retire',
                'kind': 'subject',
                'summary': f'Retire subject {current.subject.name}. Past records stay.',
            })
    return changes


def apply_curriculum(school, curriculum):
    """Copy a curriculum version onto the school. Callers choose the moment."""
    from academics.models import Level
    from academics.services.curriculum import provision_school_curriculum

    with allow_system_record_writes():
        if not Level.objects.filter(school=school).exists():
            provision_school_curriculum(school, curriculum=curriculum)
        else:
            _apply(school, curriculum)
            school.provisioned_curriculum = curriculum
        school.accepted_curriculum = None
        school.save(update_fields=['provisioned_curriculum', 'accepted_curriculum', 'updated_at'])


def apply_accepted_curriculum(school):
    """Apply the version the school already accepted. Used when a term starts."""
    accepted = school.accepted_curriculum
    if accepted is None:
        return
    if school.provisioned_curriculum_id == accepted.id:
        school.accepted_curriculum = None
        school.save(update_fields=['accepted_curriculum', 'updated_at'])
        return
    apply_curriculum(school, accepted)


@transaction.atomic
def adopt(school) -> dict:
    active = _active()
    plan = plan_adoption(school)
    if school.provisioned_curriculum_id == active.id:
        return plan
    if _has_open_term(school):
        school.accepted_curriculum = active
        school.save(update_fields=['accepted_curriculum', 'updated_at'])
        return {
            **plan,
            'scheduled': True,
            'applied': False,
            'up_to_date': True,
            'applies_on': 'next_term',
            'summary': (
                f'Version {active.version} is accepted. This term stays as it is. '
                'The new classes and subjects take effect when the next term starts.'
            ),
        }
    apply_curriculum(school, active)
    school.refresh_from_db()
    return {
        'up_to_date': True,
        'scheduled': False,
        'applied': True,
        'applies_on': 'now',
        'from_version': plan['from_version'],
        'to_version': active.version,
        'summary': f'Version {active.version} is now in use.',
        'changes': plan['changes'],
    }


def _apply(school, target):
    school_levels = _indexed_school_levels(school)
    target_level_lineages = set()
    for level_template in target.levels.prefetch_related(
        'class_levels__subjects',
        'subjects',
    ).order_by('order'):
        target_level_lineages.add(level_template.lineage_id)
        current = school_levels.get(level_template.lineage_id)
        if current is None:
            _create_level(school, level_template)
            continue
        if current.name != level_template.name and _level_has_history(current):
            _detach_level(current)
            _create_level(school, level_template)
            continue
        else:
            current.name = level_template.name
            current.description = level_template.description
            current.order = level_template.order
            current.subject_scope = level_template.subject_scope
            current.allows_custom_classes = level_template.allows_custom_classes
            current.curriculum_level = level_template
            current.is_active = True
            current.save()
        _apply_classes(school, current, level_template)
        _apply_subjects(school, current, level_template)

    for lineage, current in school_levels.items():
        if lineage not in target_level_lineages and current.is_active:
            current.is_active = False
            current.save(update_fields=['is_active', 'updated_at'])


def _create_level(school, level_template):
    from academics.models import Level

    level = Level.objects.create(
        school=school,
        curriculum_level=level_template,
        name=level_template.name,
        description=level_template.description,
        order=level_template.order,
        subject_scope=level_template.subject_scope,
        allows_custom_classes=level_template.allows_custom_classes,
        is_system_generated=True,
        is_active=True,
    )
    _apply_classes(school, level, level_template)
    _apply_subjects(school, level, level_template)
    return level


def _detach_level(level):
    level.is_system_generated = False
    level.curriculum_level = None
    level.save()


def _apply_classes(school, school_level, level_template):
    from academics.models import ClassLevel, ClassStream

    current_by_lineage = {
        row.curriculum_class_level.lineage_id: row
        for row in ClassLevel.objects.filter(
            level=school_level,
            is_system_generated=True,
            curriculum_class_level__isnull=False,
        ).select_related('curriculum_class_level')
    }
    target_lineages = set()
    for class_template in level_template.class_levels.all():
        target_lineages.add(class_template.lineage_id)
        current = current_by_lineage.get(class_template.lineage_id)
        if current is None:
            created = ClassLevel.objects.create(
                level=school_level,
                school=school,
                curriculum_class_level=class_template,
                name=class_template.name,
                order=class_template.order,
                is_system_generated=True,
                is_active=True,
            )
            ClassStream.objects.create(class_level=created, is_default=True)
        elif current.name != class_template.name and _class_has_history(current):
            current.is_system_generated = False
            current.curriculum_class_level = None
            current.save()
            created = ClassLevel.objects.create(
                level=school_level,
                school=school,
                curriculum_class_level=class_template,
                name=class_template.name,
                order=class_template.order,
                is_system_generated=True,
                is_active=True,
            )
            ClassStream.objects.create(class_level=created, is_default=True)
        else:
            current.name = class_template.name
            current.order = class_template.order
            current.curriculum_class_level = class_template
            current.is_active = True
            current.save()
    for lineage, current in current_by_lineage.items():
        if lineage not in target_lineages and current.is_active:
            current.is_active = False
            current.save(update_fields=['is_active', 'updated_at'])


def _subject_for(school, name):
    from academics.models import Subject

    subject = Subject.objects.filter(school=school, name=name).first()
    if subject is not None:
        if not subject.is_active:
            subject.is_active = True
            subject.save(update_fields=['is_active', 'updated_at'])
        return subject
    return Subject.objects.create(school=school, name=name, is_system_generated=True, is_active=True)


def _ensure_level_subject(school, school_level, subject, template):
    from academics.models import LevelSubject

    row = LevelSubject.objects.filter(level=school_level, subject=subject).first()
    if row is None:
        return LevelSubject.objects.create(
            school=school,
            level=school_level,
            subject=subject,
            curriculum_subject=template,
            is_system_generated=True,
            is_active=True,
        )
    row.curriculum_subject = template
    row.is_system_generated = True
    row.is_active = True
    row.save()
    return row


def _ensure_class_subject(school, class_level, subject, template):
    from academics.models import ClassSubject

    row = ClassSubject.objects.filter(class_level=class_level, subject=subject).first()
    if row is None:
        return ClassSubject.objects.create(
            school=school,
            class_level=class_level,
            subject=subject,
            curriculum_subject=template,
            is_system_generated=True,
            is_active=True,
        )
    row.curriculum_subject = template
    row.is_system_generated = True
    row.is_active = True
    row.save()
    return row


def _apply_subjects(school, school_level, level_template):
    from academics.models import ClassLevel, ClassSubject, LevelSubject

    current_by_lineage = {
        row.curriculum_subject.lineage_id: row
        for row in LevelSubject.objects.filter(
            level=school_level,
            is_system_generated=True,
            curriculum_subject__isnull=False,
        ).select_related('curriculum_subject', 'subject')
    }
    target_rows = _target_subject_rows(level_template)
    target_lineages = {row.lineage_id for row in target_rows}
    standard_classes = list(
        ClassLevel.objects.filter(
            level=school_level,
            is_system_generated=True,
            is_active=True,
        ),
    )
    for template in target_rows:
        current = current_by_lineage.get(template.lineage_id)
        if current is not None and current.subject.name != template.name:
            from academics.models import LevelSubject as LevelSubjectModel

            shared = LevelSubjectModel.objects.filter(
                subject=current.subject,
                is_system_generated=True,
            ).exclude(pk=current.pk).exists()
            if shared or _subject_has_history(current.subject):
                _detach_subject(current)
                current = None
        if current is None:
            subject = _subject_for(school, template.name)
        else:
            subject = current.subject
            if subject.name != template.name:
                subject.name = template.name
                subject.is_system_generated = True
                subject.is_active = True
                subject.save()
        _ensure_level_subject(school, school_level, subject, template)
        if template.curriculum_class_level_id:
            match = next(
                (
                    class_level
                    for class_level in standard_classes
                    if class_level.curriculum_class_level_id
                    and class_level.curriculum_class_level.lineage_id
                    == template.curriculum_class_level.lineage_id
                ),
                None,
            )
            targets = [match] if match is not None else []
        else:
            targets = standard_classes
        for class_level in targets:
            _ensure_class_subject(school, class_level, subject, template)

    for lineage, current in current_by_lineage.items():
        if lineage not in target_lineages and current.is_active:
            current.is_active = False
            current.save(update_fields=['is_active', 'updated_at'])
            ClassSubject.objects.filter(
                class_level__level=school_level,
                subject=current.subject,
                is_system_generated=True,
            ).update(is_active=False)


def _detach_subject(level_subject):
    from academics.models import ClassSubject

    level_subject.is_system_generated = False
    level_subject.curriculum_subject = None
    level_subject.save()
    ClassSubject.objects.filter(
        class_level__level=level_subject.level,
        subject=level_subject.subject,
        is_system_generated=True,
    ).update(is_system_generated=False, curriculum_subject=None)
