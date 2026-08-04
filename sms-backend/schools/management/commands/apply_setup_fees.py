from django.core.management.base import BaseCommand, CommandError

from fees.models import FeeStructure
from schools.models import School, Term
from schools.services.fees import apply_active_term_fees
from rest_framework.exceptions import ValidationError


class Command(BaseCommand):
    help = (
        'Publish and apply active-term fee structures for schools that have '
        'completed setup. Schools whose fees are already applied are skipped.'
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
            help='Report what would happen without applying fees.',
        )

    def handle(self, *args, **options):
        queryset = School.objects.filter(setup_completed=True).order_by('name')
        school_id = options.get('school_id')
        dry_run = options['dry_run']

        if school_id:
            queryset = queryset.filter(id=school_id)
            if not queryset.exists():
                raise CommandError(
                    f'No setup-complete school found with id {school_id}.',
                )

        applied = 0
        skipped = 0
        failed = 0

        if dry_run:
            self.stdout.write('Dry run — no changes will be saved.')

        for school in queryset.iterator():
            label = f'{school.name} ({school.id})'
            try:
                term = Term.objects.filter(school=school, is_active=True).first()
                if term is None:
                    self.stderr.write(self.style.ERROR(f'{label}: no active term'))
                    failed += 1
                    continue

                structure = FeeStructure.objects.filter(school=school, term=term).first()
                if structure is None:
                    self.stderr.write(self.style.ERROR(f'{label}: no fee structure'))
                    failed += 1
                    continue

                if structure.is_locked:
                    self.stdout.write(f'{label}: already applied — skipped')
                    skipped += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        f'{label}: would apply (status={structure.status})',
                    )
                    applied += 1
                    continue

                apply_active_term_fees(school)
                self.stdout.write(self.style.SUCCESS(f'{label}: applied'))
                applied += 1
            except ValidationError as exc:
                self.stderr.write(self.style.ERROR(f'{label}: {exc.detail}'))
                failed += 1
            except Exception as exc:  # noqa: BLE001 — report and continue other schools
                self.stderr.write(self.style.ERROR(f'{label}: {exc}'))
                failed += 1

        self.stdout.write(
            f'Done. applied/would-apply={applied} skipped={skipped} failed={failed}',
        )
