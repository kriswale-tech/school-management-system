from django.core.management.base import BaseCommand

from communications.services.pricing import (
    ensure_default_email_config,
    ensure_default_sms_configs,
)
from communications.services.providers import ensure_provider_accounts


class Command(BaseCommand):
    help = 'Seed default SMS/email pricing configs and provider account rows.'

    def handle(self, *args, **options):
        sms = ensure_default_sms_configs()
        email = ensure_default_email_config()
        accounts = ensure_provider_accounts()
        self.stdout.write(
            self.style.SUCCESS(
                f'Seeded {len(sms)} SMS encoding config(s), '
                f'email={"created/ensured" if email else "skipped"}, '
                f'{len(accounts)} provider account(s).',
            ),
        )
