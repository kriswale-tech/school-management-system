"""Celery tasks for assessment report generation."""

from celery import shared_task


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 2},
    name='assessments.run_report_generate_job',
)
def run_report_generate_job_task(self, job_id: str) -> dict:
    from assessments.services.bulk_reports import process_report_generate_job

    return process_report_generate_job(job_id=job_id)
