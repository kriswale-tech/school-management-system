from datetime import timedelta
from decimal import Decimal

from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from accounts.tests.factories import create_school, create_user, set_client_auth_cookies
from billing.models import Invoice, Plan, SchoolSubscription
from billing.services.catalog import seed_default_plans, seed_first_year_free_campaign
from billing.services.dunning import run_dunning_cycle, suspend_for_nonpayment
from billing.services.interval_change import change_billing_interval
from billing.services.subscriptions import (
    open_renewal_period,
    schedule_plan_change,
    start_subscription,
)
from schools.models import School
from rest_framework.exceptions import ValidationError


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class Phase6DunningIntervalTests(APITestCase):
    def setUp(self):
        seed_default_plans()
        seed_first_year_free_campaign()
        self.school = create_school(
            name='Dunning School',
            phone_number='+233244000201',
        )
        self.school.email = 'school@dunning.test'
        self.school.save(update_fields=['email', 'updated_at'])
        self.admin = create_user(
            school=self.school,
            is_active=True,
            phone_number='+233244000202',
            email='admin@dunning.test',
        )
        set_client_auth_cookies(self.client, self.admin)
        self.subscription = start_subscription(
            school=self.school,
            plan=Plan.objects.get(code='starter'),
            apply_first_year_free=False,
            interval=SchoolSubscription.Interval.MONTHLY,
        )

    def test_dunning_suspends_after_grace(self):
        self.subscription.status = SchoolSubscription.Status.PAST_DUE
        self.subscription.grace_period_ends_at = timezone.now() - timedelta(hours=1)
        self.subscription.save(
            update_fields=['status', 'grace_period_ends_at', 'updated_at'],
        )
        result = run_dunning_cycle()
        self.assertEqual(result['suspended'], 1)
        self.subscription.refresh_from_db()
        self.school.refresh_from_db()
        self.assertEqual(self.subscription.status, SchoolSubscription.Status.SUSPENDED)
        self.assertFalse(self.subscription.billing_suspended_school)
        # School app stays accessible so admins can pay open invoices.
        self.assertEqual(self.school.status, School.Status.ACTIVE)
        self.assertTrue(mail.outbox)

    def test_dunning_sends_grace_reminder(self):
        self.subscription.status = SchoolSubscription.Status.PAST_DUE
        self.subscription.grace_period_ends_at = timezone.now() + timedelta(days=1)
        self.subscription.save(
            update_fields=['status', 'grace_period_ends_at', 'updated_at'],
        )
        result = run_dunning_cycle(notice_days_before=2)
        self.assertEqual(result['reminded'], 1)
        self.subscription.refresh_from_db()
        self.assertIsNotNone(self.subscription.dunning_notice_sent_at)
        # Idempotent
        again = run_dunning_cycle(notice_days_before=2)
        self.assertEqual(again['reminded'], 0)

    def test_mid_period_interval_change_is_disabled(self):
        with self.assertRaises(ValidationError):
            change_billing_interval(
                school=self.school,
                new_interval=SchoolSubscription.Interval.ANNUAL,
                mark_paid=True,
            )
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.interval, SchoolSubscription.Interval.MONTHLY)

    def test_schedule_interval_change_applies_on_renewal(self):
        schedule_plan_change(
            subscription=self.subscription,
            interval=SchoolSubscription.Interval.ANNUAL,
        )
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.interval, SchoolSubscription.Interval.MONTHLY)
        self.assertEqual(self.subscription.pending_interval, SchoolSubscription.Interval.ANNUAL)
        self.assertEqual(
            self.subscription.pending_change_effective_at,
            self.subscription.current_period_end,
        )

        url = reverse('school-billing-schedule-change')
        response = self.client.post(url, {'interval': 'annual'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['pending_interval'], 'annual')

        # Renewal applies the pending interval
        plan = self.subscription.plan
        plan.price_monthly_ghs = Decimal('0.00')
        plan.price_annual_ghs = Decimal('0.00')
        plan.save(update_fields=['price_monthly_ghs', 'price_annual_ghs', 'updated_at'])
        subscription, _invoice = open_renewal_period(subscription=self.subscription)
        self.assertEqual(subscription.interval, SchoolSubscription.Interval.ANNUAL)
        self.assertEqual(subscription.pending_interval, '')

    def test_payment_reactivates_billing_locked_school(self):
        suspend_for_nonpayment(subscription=self.subscription, lock_school=True)
        self.subscription.refresh_from_db()
        self.school.refresh_from_db()
        self.assertEqual(self.school.status, School.Status.SUSPENDED)
        self.assertTrue(self.subscription.billing_suspended_school)

        from billing.services.dunning import reactivate_subscription_after_payment

        reactivate_subscription_after_payment(subscription=self.subscription)
        self.subscription.refresh_from_db()
        self.school.refresh_from_db()
        self.assertEqual(self.subscription.status, SchoolSubscription.Status.ACTIVE)
        self.assertFalse(self.subscription.billing_suspended_school)
        self.assertEqual(self.school.status, School.Status.ACTIVE)

    def test_open_renewal_sets_past_due_when_payable(self):
        # Force prices so renewal is non-zero
        plan = self.subscription.plan
        plan.price_monthly_ghs = Decimal('100.00')
        plan.save(update_fields=['price_monthly_ghs', 'updated_at'])
        self.subscription.app_price_snapshot_ghs = Decimal('100.00')
        self.subscription.current_period_end = timezone.now()
        self.subscription.save(
            update_fields=['app_price_snapshot_ghs', 'current_period_end', 'updated_at'],
        )
        subscription, invoice = open_renewal_period(subscription=self.subscription)
        self.assertEqual(invoice.status, Invoice.Status.OPEN)
        self.assertEqual(subscription.status, SchoolSubscription.Status.PAST_DUE)
        self.assertIsNotNone(subscription.grace_period_ends_at)
