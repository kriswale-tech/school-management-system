from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.tests.factories import create_school
from billing.models import InvoiceLine, Plan, PromotionCampaign, PromotionRedemption, SchoolSubscription
from billing.services.catalog import seed_default_plans, seed_first_year_free_campaign
from billing.services.period import add_billing_interval
from billing.services.subscriptions import open_renewal_period, schedule_plan_change, start_subscription
from platform_admin.models import PlatformUser


def _discount(**overrides):
    payload = {
        'code': 'six-months',
        'name': 'First six months',
        'discount_percent': Decimal('20.00'),
        'schedule': PromotionCampaign.Schedule.INTRODUCTORY,
        'audience': PromotionCampaign.Audience.ALL,
        'billing_interval': '',
        'duration_months': 6,
        'applies_to': PromotionCampaign.AppliesTo.APPLICATION,
        'is_active': True,
    }
    payload.update(overrides)
    return PromotionCampaign.objects.create(**payload)


class DiscountServiceTests(APITestCase):
    def setUp(self):
        seed_default_plans()
        seed_first_year_free_campaign()
        self.school = create_school(name='Discount School', phone_number='+233244009001')
        self.starter = Plan.objects.get(code='starter')

    def _start(self, *, interval='annual'):
        return start_subscription(
            school=self.school,
            plan=self.starter,
            interval=interval,
            apply_first_year_free=False,
        )

    def test_first_six_months_discounts_half_of_an_annual_invoice(self):
        _discount()
        subscription = self._start(interval='annual')
        invoice = subscription.invoices.get()
        self.assertEqual(invoice.discount_ghs, Decimal('80.00'))
        self.assertEqual(invoice.total_ghs, Decimal('720.00'))
        line = invoice.lines.get(kind=InvoiceLine.Kind.DISCOUNT)
        self.assertEqual(line.metadata['qualified_months'], 6)
        self.assertEqual(line.metadata['covered_months'], 12)

    def test_first_six_months_discounts_each_monthly_invoice_then_stops(self):
        _discount()
        subscription = self._start(interval='monthly')
        first = subscription.invoices.get()
        self.assertEqual(first.discount_ghs, Decimal('16.00'))
        self.assertEqual(first.total_ghs, Decimal('64.00'))

        invoice = None
        for _ in range(5):
            subscription, invoice = open_renewal_period(subscription=subscription)
            self.assertEqual(invoice.discount_ghs, Decimal('16.00'))
        subscription, invoice = open_renewal_period(subscription=subscription)
        self.assertEqual(invoice.discount_ghs, Decimal('0.00'))
        self.assertEqual(invoice.total_ghs, Decimal('80.00'))

    def test_switching_to_annual_keeps_only_the_remaining_months(self):
        _discount()
        subscription = self._start(interval='monthly')
        for _ in range(2):
            subscription, _invoice = open_renewal_period(subscription=subscription)
        schedule_plan_change(subscription=subscription, interval='annual')
        subscription, invoice = open_renewal_period(subscription=subscription)
        self.assertEqual(subscription.interval, 'annual')
        self.assertEqual(invoice.discount_ghs, Decimal('40.00'))
        self.assertEqual(invoice.total_ghs, Decimal('760.00'))
        self.assertEqual(
            invoice.lines.get(kind=InvoiceLine.Kind.DISCOUNT).metadata['qualified_months'],
            3,
        )

    def test_larger_cedi_saving_wins(self):
        _discount()
        _discount(
            code='always-15',
            name='Always 15',
            discount_percent=Decimal('15.00'),
            schedule=PromotionCampaign.Schedule.RECURRING,
            duration_months=12,
        )
        subscription = self._start(interval='annual')
        invoice = subscription.invoices.get()
        self.assertEqual(invoice.discount_ghs, Decimal('120.00'))
        self.assertEqual(invoice.lines.filter(kind=InvoiceLine.Kind.DISCOUNT).count(), 1)
        self.assertEqual(
            invoice.lines.get(kind=InvoiceLine.Kind.DISCOUNT).metadata['campaign_code'],
            'always-15',
        )

    def test_selected_school_is_the_only_one_discounted(self):
        other = create_school(name='Other School', phone_number='+233244009002')
        campaign = _discount(audience=PromotionCampaign.Audience.SELECTED, code='picked')
        campaign.schools.add(self.school)
        chosen = self._start(interval='monthly')
        skipped = start_subscription(
            school=other,
            plan=self.starter,
            interval='monthly',
            apply_first_year_free=False,
        )
        self.assertEqual(chosen.invoices.get().discount_ghs, Decimal('16.00'))
        self.assertEqual(skipped.invoices.get().discount_ghs, Decimal('0.00'))

    def test_new_school_offer_skips_a_second_subscription(self):
        first = self._start(interval='monthly')
        first.is_current = False
        first.status = SchoolSubscription.Status.CANCELLED
        first.save(update_fields=['is_current', 'status', 'updated_at'])
        _discount(audience=PromotionCampaign.Audience.NEW, code='new-only')
        second = self._start(interval='monthly')
        self.assertEqual(second.invoices.get().discount_ghs, Decimal('0.00'))

    def test_introductory_offer_is_spent_when_the_school_is_older_than_the_window(self):
        subscription = self._start(interval='monthly')
        origin = timezone.now() - timedelta(days=800)
        period = subscription.periods.get()
        period.starts_at = origin
        period.save(update_fields=['starts_at', 'updated_at'])
        subscription.current_period_start = origin
        subscription.current_period_end = timezone.now()
        subscription.save(update_fields=['current_period_start', 'current_period_end', 'updated_at'])
        _discount()
        _subscription, invoice = open_renewal_period(subscription=subscription)
        self.assertEqual(invoice.discount_ghs, Decimal('0.00'))
        self.assertEqual(invoice.total_ghs, Decimal('80.00'))

    def test_date_range_covers_only_overlapping_months(self):
        start = timezone.now()
        benefit_start = start
        for _ in range(2):
            benefit_start = add_billing_interval(benefit_start, 'monthly')
        benefit_end = start
        for _ in range(5):
            benefit_end = add_billing_interval(benefit_end, 'monthly')
        _discount(
            code='summer',
            name='Summer',
            schedule=PromotionCampaign.Schedule.DATE_RANGE,
            discount_percent=Decimal('25.00'),
            starts_at=benefit_start,
            ends_at=benefit_end,
        )
        subscription = self._start(interval='annual')
        invoice = subscription.invoices.get()
        self.assertEqual(invoice.discount_ghs, Decimal('50.00'))
        self.assertEqual(
            invoice.lines.get(kind=InvoiceLine.Kind.DISCOUNT).metadata['qualified_months'],
            3,
        )

    def test_revoked_redemption_stops_and_deactivated_introductory_continues(self):
        campaign = _discount(code='keep-going')
        subscription = self._start(interval='monthly')
        redemption = PromotionRedemption.objects.get(school=self.school, campaign=campaign)
        redemption.revoked_at = timezone.now()
        redemption.save(update_fields=['revoked_at', 'updated_at'])
        subscription, invoice = open_renewal_period(subscription=subscription)
        self.assertEqual(invoice.discount_ghs, Decimal('0.00'))

        campaign.is_active = False
        campaign.save(update_fields=['is_active', 'updated_at'])
        redemption.revoked_at = None
        redemption.save(update_fields=['revoked_at', 'updated_at'])
        subscription, invoice = open_renewal_period(subscription=subscription)
        self.assertEqual(invoice.discount_ghs, Decimal('16.00'))

    def test_deactivated_recurring_discount_stops(self):
        campaign = _discount(
            code='forever',
            schedule=PromotionCampaign.Schedule.RECURRING,
            discount_percent=Decimal('10.00'),
        )
        subscription = self._start(interval='monthly')
        self.assertEqual(subscription.invoices.get().discount_ghs, Decimal('8.00'))
        campaign.is_active = False
        campaign.save(update_fields=['is_active', 'updated_at'])
        _subscription, invoice = open_renewal_period(subscription=subscription)
        self.assertEqual(invoice.discount_ghs, Decimal('0.00'))


class DiscountApiTests(APITestCase):
    def setUp(self):
        seed_default_plans()
        seed_first_year_free_campaign()
        self.school = create_school(name='API Discount School', phone_number='+233244009010')
        self.ops = PlatformUser.objects.create_user(
            email='discount-ops@schoolasst.test',
            password='SecurePass123!',
            role=PlatformUser.Role.SUPER_ADMIN,
        )
        from django.conf import settings

        login = self.client.post(
            reverse('platform-login'),
            {'email': 'discount-ops@schoolasst.test', 'password': 'SecurePass123!'},
            format='json',
        )
        self.client.cookies[settings.PLATFORM_JWT['AUTH_COOKIE']] = (
            login.cookies[settings.PLATFORM_JWT['AUTH_COOKIE']].value
        )

    def test_create_list_and_reject_a_date_range_without_dates(self):
        created = self.client.post(
            reverse('platform-billing-discounts'),
            {
                'code': 'picked-monthly',
                'name': 'Picked monthly',
                'discount_percent': '15.00',
                'schedule': 'recurring',
                'audience': 'selected',
                'billing_interval': 'monthly',
                'applies_to': 'application',
                'school_ids': [str(self.school.pk)],
                'is_active': True,
            },
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        self.assertEqual(created.data['audience'], 'selected')
        self.assertEqual(created.data['schools'][0]['id'], str(self.school.pk))

        listed = self.client.get(reverse('platform-billing-discounts'))
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertTrue(any(row['code'] == 'picked-monthly' for row in listed.data))

        missing = self.client.post(
            reverse('platform-billing-discounts'),
            {
                'code': 'summer-missing',
                'name': 'Summer',
                'discount_percent': '10.00',
                'schedule': 'date_range',
                'audience': 'all',
                'applies_to': 'application',
            },
            format='json',
        )
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)

    def test_restore_clears_a_revocation(self):
        from billing.models import Plan

        campaign = PromotionCampaign.objects.create(
            code='restore-me',
            name='Restore me',
            discount_percent=Decimal('20.00'),
            schedule=PromotionCampaign.Schedule.INTRODUCTORY,
            audience=PromotionCampaign.Audience.ALL,
            duration_months=6,
            applies_to=PromotionCampaign.AppliesTo.APPLICATION,
            is_active=True,
        )
        subscription = start_subscription(
            school=self.school,
            plan=Plan.objects.get(code='starter'),
            interval='monthly',
            apply_first_year_free=False,
        )
        redemption = PromotionRedemption.objects.get(school=self.school, campaign=campaign)
        revoked = self.client.post(
            reverse(
                'platform-billing-discount-revoke',
                kwargs={'pk': campaign.pk, 'redemption_id': redemption.pk},
            ),
            format='json',
        )
        self.assertEqual(revoked.status_code, status.HTTP_200_OK)
        redemption.refresh_from_db()
        self.assertIsNotNone(redemption.revoked_at)

        restored = self.client.post(
            reverse(
                'platform-billing-discount-restore',
                kwargs={'pk': campaign.pk, 'redemption_id': redemption.pk},
            ),
            format='json',
        )
        self.assertEqual(restored.status_code, status.HTTP_200_OK, restored.data)
        self.assertIsNone(restored.data['revoked_at'])
        _subscription, invoice = open_renewal_period(subscription=subscription)
        self.assertEqual(invoice.discount_ghs, Decimal('16.00'))
