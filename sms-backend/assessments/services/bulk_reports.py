"""Queue and run bulk student report PDF generation."""

from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound

from assessments.models import ReportGenerateJob
from assessments.services.admin_overview import _load_stream
from assessments.services.report_pdf import generate_student_report
from students.models import Student
from students.services import resolve_term

logger = logging.getLogger(__name__)

MAX_FAILURES_STORED = 40


def _unique_student_ids(student_ids) -> list[str]:
    seen = set()
    ordered = []
    for raw in student_ids:
        key = str(raw)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ordered


def serialize_report_generate_job(job: ReportGenerateJob) -> dict:
    return {
        'id': str(job.id),
        'status': job.status,
        'force': job.force,
        'stream_id': str(job.stream_id),
        'term_id': str(job.term_id),
        'total': job.total,
        'generated': job.generated,
        'skipped': job.skipped,
        'failed': job.failed,
        'error_message': job.error_message,
        'failures': job.failures or [],
        'created_at': job.created_at.isoformat() if job.created_at else None,
        'finished_at': job.finished_at.isoformat() if job.finished_at else None,
        'done': job.status in {
            ReportGenerateJob.Status.COMPLETED,
            ReportGenerateJob.Status.FAILED,
        },
    }


def queue_bulk_report_generate(
    *,
    school,
    membership,
    stream_id,
    term_id,
    student_ids,
    force: bool = False,
) -> dict:
    """Validate selection, create a job row, enqueue Celery. Returns job payload."""
    student_ids = _unique_student_ids(student_ids)
    if not student_ids:
        raise ValidationError({'student_ids': 'Select at least one student.'})

    stream = _load_stream(school=school, stream_id=stream_id)
    term = resolve_term(school, term_id)

    found = {
        str(student.id): student
        for student in Student.objects.filter(school=school, id__in=student_ids)
    }
    missing = [sid for sid in student_ids if sid not in found]
    if missing:
        raise ValidationError({
            'student_ids': f'{len(missing)} student(s) were not found in this school.',
        })

    job = ReportGenerateJob.objects.create(
        school=school,
        stream=stream,
        term=term,
        created_by=getattr(membership, 'user', None),
        status=ReportGenerateJob.Status.PENDING,
        force=bool(force),
        student_ids=student_ids,
        total=len(student_ids),
    )

    from assessments.tasks import run_report_generate_job_task

    transaction.on_commit(lambda: run_report_generate_job_task.delay(str(job.id)))
    return serialize_report_generate_job(job)


def get_report_generate_job(*, school, stream_id, job_id) -> dict:
    job = (
        ReportGenerateJob.objects.filter(
            id=job_id,
            school=school,
            stream_id=stream_id,
        ).first()
    )
    if job is None:
        raise NotFound('Report generate job not found.')
    return serialize_report_generate_job(job)


def process_report_generate_job(*, job_id) -> dict:
    """Worker entry: generate PDFs for each student on the job."""
    job = ReportGenerateJob.objects.select_related(
        'school',
        'stream',
        'term',
        'created_by',
    ).filter(id=job_id).first()
    if job is None:
        return {'ok': False, 'error': 'job_missing'}

    if job.status in {
        ReportGenerateJob.Status.COMPLETED,
        ReportGenerateJob.Status.FAILED,
    }:
        return serialize_report_generate_job(job)

    job.status = ReportGenerateJob.Status.RUNNING
    job.save(update_fields=['status', 'updated_at'])

    # Membership-like object for generated_by attribution.
    class _Membership:
        def __init__(self, user):
            self.user = user

    membership = _Membership(job.created_by)
    failures: list[dict] = []
    generated = 0
    skipped = 0
    failed = 0

    students = {
        str(student.id): student
        for student in Student.objects.filter(
            school=job.school,
            id__in=job.student_ids,
        )
    }

    for student_id in job.student_ids:
        student = students.get(str(student_id))
        full_name = ''
        if student is not None:
            full_name = ' '.join(
                part
                for part in (student.first_name, student.other_names, student.last_name)
                if part
            ).strip()
        try:
            from assessments.models import Report
            from assessments.services.report_pdf import _report_file_exists

            before = (
                Report.objects.filter(
                    school=job.school,
                    stream_id=job.stream_id,
                    student_id=student_id,
                    term_id=job.term_id,
                ).first()
            )
            existed = before is not None and _report_file_exists(before) and not job.force

            generate_student_report(
                school=job.school,
                membership=membership,
                stream_id=job.stream_id,
                student_id=student_id,
                term_id=job.term_id,
                force=job.force,
            )
            if existed:
                skipped += 1
            else:
                generated += 1
        except Exception as exc:
            failed += 1
            if len(failures) < MAX_FAILURES_STORED:
                failures.append({
                    'student_id': str(student_id),
                    'full_name': full_name,
                    'reason': str(exc)[:200],
                })
            logger.exception(
                'Report generate failed job=%s student=%s',
                job_id,
                student_id,
            )

        job.generated = generated
        job.skipped = skipped
        job.failed = failed
        job.failures = failures
        job.save(update_fields=[
            'generated',
            'skipped',
            'failed',
            'failures',
            'updated_at',
        ])

    job.status = ReportGenerateJob.Status.COMPLETED
    job.finished_at = timezone.now()
    job.save(update_fields=['status', 'finished_at', 'updated_at'])
    return serialize_report_generate_job(job)
