from django.core.management.base import BaseCommand, CommandError

from fees.services.backfill_advances import backfill_advances
from schools.models import School


class Command(BaseCommand):
    help = (
        'Create advance credits for historical overpayments '
        '(paid > billed on a term) recorded before advance tracking existed. '
        'Also removes duplicate backfill credits when a live advance already '
        'covers the excess.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--school-id',
            type=str,
            help='Limit to a single school UUID.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would change without writing.',
        )

    def handle(self, *args, **options):
        school_id = options.get('school_id')
        dry_run = options['dry_run']

        if school_id and not School.objects.filter(id=school_id).exists():
            raise CommandError(f'No school found with id {school_id}.')

        results = backfill_advances(school_id=school_id, dry_run=dry_run)
        total_created = 0
        total_skipped = 0
        total_removed = 0

        for school_result in results:
            created = school_result['created']
            skipped = school_result['skipped']
            removed = school_result.get('removed') or []
            total_created += len(created)
            total_skipped += len(skipped)
            total_removed += len(removed)

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"{school_result['school']} "
                    f"({'dry-run' if dry_run else 'applied'})",
                ),
            )
            for entry in removed:
                self.stdout.write(
                    self.style.WARNING(
                        f"  - removed duplicate backfill {entry['student']} | "
                        f"{entry['term']} | {entry['amount']}",
                    ),
                )
            for entry in created:
                amount = entry.get('uncovered', entry['excess'])
                self.stdout.write(
                    f"  + {entry['student']} | {entry['term']} | "
                    f"paid {entry['paid']} billed {entry['billed']} "
                    f"→ advance {amount}",
                )
            for entry in skipped:
                self.stdout.write(
                    f"  · skipped {entry['student']} | {entry['term']} "
                    f"({entry['reason']})",
                )

        prefix = 'Would create' if dry_run else 'Created'
        remove_prefix = 'Would remove' if dry_run else 'Removed'
        self.stdout.write(
            self.style.SUCCESS(
                f'{prefix} {total_created} advance credit(s); '
                f'{remove_prefix} {total_removed} duplicate(s); '
                f'skipped {total_skipped}.',
            ),
        )
