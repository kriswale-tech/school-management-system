from django.core.management.base import BaseCommand

from billing.services.catalog import seed_default_plans, seed_first_year_free_campaign
from billing.services.catalog_topups import seed_default_topup_packages


class Command(BaseCommand):
    help = 'Seed default SaaS plans, first-year campaign, and top-up packages.'

    def handle(self, *args, **options):
        plans = seed_default_plans()
        campaign = seed_first_year_free_campaign()
        packages = seed_default_topup_packages()
        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(plans)} plans, campaign {campaign.code}, '
            f'and {len(packages)} top-up packages.',
        ))
