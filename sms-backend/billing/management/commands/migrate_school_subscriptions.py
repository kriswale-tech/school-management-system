from django.core.management.base import BaseCommand

from billing.services.migrate import migrate_existing_schools


class Command(BaseCommand):
    help = (
        'Create complimentary first-year annual subscriptions for schools '
        'that do not yet have a current subscription.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report schools that would receive a subscription without writing.',
        )

    def handle(self, *args, **options):
        result = migrate_existing_schools(dry_run=options['dry_run'])
        verb = 'Would create' if result['dry_run'] else 'Created'
        self.stdout.write(self.style.SUCCESS(
            f'{verb} {result["created"]} subscription(s); skipped {result["skipped"]}.',
        ))
