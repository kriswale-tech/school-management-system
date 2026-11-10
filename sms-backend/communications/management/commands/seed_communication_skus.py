from django.core.management.base import BaseCommand

from communications.services.catalog import seed_default_skus


class Command(BaseCommand):
    help = 'Seed default SMS/email communication add-on SKUs.'

    def handle(self, *args, **options):
        skus = seed_default_skus()
        self.stdout.write(self.style.SUCCESS(f'Seeded {len(skus)} communication SKUs.'))
