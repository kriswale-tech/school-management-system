"""Celery tasks for SaaS billing (dunning)."""

from celery import shared_task


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
    name='billing.run_dunning_cycle',
)
def run_dunning_cycle_task(self) -> dict:
    from billing.services.dunning import run_dunning_cycle

    return run_dunning_cycle()
