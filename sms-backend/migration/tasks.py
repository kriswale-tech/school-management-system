from celery import shared_task


@shared_task(name='migration.inspect_file')
def inspect_migration_file_task(file_id: str) -> None:
    from migration.services.ingest import inspect_migration_file

    inspect_migration_file(file_id)


@shared_task(name='migration.commit_students')
def commit_student_migration_task(job_id: str) -> None:
    from migration.services.student_commit import process_student_commit

    process_student_commit(job_id)


@shared_task(name='migration.commit_opening_balances')
def commit_opening_migration_task(job_id: str) -> None:
    from migration.services.opening_commit import process_opening_commit

    process_opening_commit(job_id)


@shared_task(name='migration.commit_historical_finance')
def commit_historical_migration_task(job_id: str) -> None:
    from migration.services.historical_commit import process_historical_commit

    process_historical_commit(job_id)
