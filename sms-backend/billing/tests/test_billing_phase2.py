from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.tests.factories import create_school, create_user, set_client_auth_cookies
from billing.models import Invoice, InvoiceLine, Plan, SchoolSubscription
from billing.services.capacity import ensure_can_add_students, get_capacity_snapshot
from billing.services.catalog import seed_default_plans, seed_first_year_free_campaign
from billing.services.migrate import ensure_complimentary_subscription, migrate_existing_schools
from billing.services.subscriptions import schedule_plan_change, start_subscription
from billing.services.upgrades import (
    apply_capacity_upgrade,
    compute_capacity_upgrade_proration,
    quote_capacity_upgrade,
)
from platform_admin.models import PlatformAuditLog, PlatformUser
from students.tests.factories import create_student


class BillingPhase2ServiceTests(APITestCase):
    def setUp(self):
        seed_default_plans()
        seed_first_year_free_campaign()
        self.school = create_school(name='Billing School', phone_number='+233244000001')

    def test_plan_for_bands_and_first_year_invoice_zero(self):
        subscription = start_subscription(
            school=self.school,
            apply_first_year_free=True,
            interval=SchoolSubscription.Interval.ANNUAL,
        )
        self.assertEqual(subscription.plan.code, 'starter')
        invoice = subscription.invoices.get()
        self.assertEqual(invoice.total_ghs, Decimal('0.00'))
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertTrue(
            invoice.lines.filter(kind=InvoiceLine.Kind.APPLICATION).exists(),
        )
        self.assertTrue(
            invoice.lines.filter(kind=InvoiceLine.Kind.DISCOUNT).exists(),
        )

    def test_capacity_blocks_when_at_max(self):
        starter = Plan.objects.get(code='starter')
        start_subscription(school=self.school, plan=starter, apply_first_year_free=True)
        # Force capacity max to 1 for a cheap test
        starter.student_max = 1
        starter.save(update_fields=['student_max', 'updated_at'])
        create_student(school=self.school)
        snapshot = get_capacity_snapshot(self.school)
        self.assertTrue(snapshot.at_or_over_student_capacity)
        self.assertTrue(snapshot.at_or_over_capacity)
        with self.assertRaises(Exception):
            ensure_can_add_students(self.school, additional=1)

    def test_staff_capacity_blocks_and_plan_for_usage(self):
        from accounts.models import User
        from accounts.services.memberships import link_user_to_school
        from accounts.tests.factories import create_user
        from billing.services.catalog import plan_for_usage

        starter = Plan.objects.get(code='starter')
        start_subscription(school=self.school, plan=starter, apply_first_year_free=True)
        starter.staff_max = 1
        starter.save(update_fields=['staff_max', 'updated_at'])

        create_user(
            school=self.school,
            is_active=True,
            phone_number='+233244000050',
            email='staff1@test.com',
            role=User.RoleChoices.TEACHER,
        )
        snapshot = get_capacity_snapshot(self.school)
        self.assertEqual(snapshot.active_staff, 1)
        self.assertTrue(snapshot.at_or_over_staff_capacity)
        self.assertTrue(snapshot.at_or_over_capacity)

        lone = User.objects.create(
            phone_number='+233244000052',
            email='staff3@test.com',
            first_name='Extra',
            last_name='Teacher',
            is_active=True,
        )
        with self.assertRaises(Exception):
            link_user_to_school(lone, self.school, User.RoleChoices.TEACHER)

        # 50 students + 30 staff needs Standard (staff_max 50)
        chosen = plan_for_usage(students=50, staff=30)
        self.assertEqual(chosen.code, 'standard')

    def test_ordinary_upgrade_schedules_pending(self):
        starter = Plan.objects.get(code='starter')
        basic = Plan.objects.get(code='basic')
        subscription = start_subscription(
            school=self.school,
            plan=starter,
            apply_first_year_free=True,
        )
        schedule_plan_change(subscription=subscription, plan=basic)
        subscription.refresh_from_db()
        self.assertEqual(subscription.pending_plan_id, basic.pk)
        self.assertEqual(subscription.plan_id, starter.pk)

    def test_capacity_upgrade_prorates_and_keeps_period_end(self):
        starter = Plan.objects.get(code='starter')
        basic = Plan.objects.get(code='basic')
        subscription = start_subscription(
            school=self.school,
            plan=starter,
            apply_first_year_free=False,
            interval=SchoolSubscription.Interval.MONTHLY,
        )
        original_end = subscription.current_period_end
        # Move period start back so remaining fraction is meaningful
        subscription.current_period_start = timezone.now() - timedelta(days=10)
        subscription.save(update_fields=['current_period_start', 'updated_at'])

        proration = compute_capacity_upgrade_proration(
            old_plan=starter,
            new_plan=basic,
            interval=subscription.interval,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
        )
        self.assertGreater(proration['amount_due_ghs'], Decimal('0.00'))
        quote = quote_capacity_upgrade(school=self.school, new_plan=basic)

        subscription, invoice = apply_capacity_upgrade(
            school=self.school,
            new_plan=basic,
            mark_paid=True,
        )
        subscription.refresh_from_db()
        self.assertEqual(subscription.plan_id, basic.pk)
        self.assertEqual(subscription.current_period_end, original_end)
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertTrue(
            invoice.lines.filter(kind=InvoiceLine.Kind.APPLICATION_PRORATION).exists(),
        )
        self.assertEqual(Decimal(quote['amount_ghs']), invoice.total_ghs)
        audit = PlatformAuditLog.objects.get(
            action='billing.subscription.capacity_upgrade',
            target_id=str(self.school.pk),
        )
        self.assertTrue(audit.detail['recorded_as_paid'])
        self.assertEqual(audit.detail['old_plan'], 'starter')
        self.assertEqual(audit.detail['new_plan'], 'basic')

    def test_migrate_existing_schools(self):
        other = create_school(name='Legacy School', phone_number='+233244000099')
        result = migrate_existing_schools()
        self.assertGreaterEqual(result['created'], 1)
        self.assertTrue(
            SchoolSubscription.objects.filter(school=other, is_current=True).exists(),
        )
        # Idempotent
        again = migrate_existing_schools()
        self.assertEqual(again['created'], 0)


class BillingPhase2ApiTests(APITestCase):
    def setUp(self):
        seed_default_plans()
        seed_first_year_free_campaign()
        self.school = create_school(name='API Billing School', phone_number='+233244000010')
        self.admin = create_user(
            school=self.school,
            is_active=True,
            phone_number='+233244000011',
            email='billing-admin@test.com',
        )
        ensure_complimentary_subscription(self.school)
        set_client_auth_cookies(self.client, self.admin)

        self.ops = PlatformUser.objects.create_user(
            email='billing-ops@schoolasst.test',
            password='SecurePass123!',
            role=PlatformUser.Role.SUPER_ADMIN,
        )
        from django.conf import settings

        login = self.client.post(
            reverse('platform-login'),
            {'email': 'billing-ops@schoolasst.test', 'password': 'SecurePass123!'},
            format='json',
        )
        self.platform_cookie = settings.PLATFORM_JWT['AUTH_COOKIE']
        # School client cookies already set; use a second client for platform
        self.platform_client = self.client_class()
        self.platform_client.cookies[self.platform_cookie] = (
            login.cookies[self.platform_cookie].value
        )

    def test_school_subscription_and_capacity(self):
        sub = self.client.get(reverse('school-billing-subscription'))
        self.assertEqual(sub.status_code, status.HTTP_200_OK)
        self.assertEqual(sub.data['plan']['code'], 'starter')
        cap = self.client.get(reverse('school-billing-capacity'))
        self.assertEqual(cap.status_code, status.HTTP_200_OK)
        self.assertIn('active_students', cap.data)

    def test_platform_plans_and_school_subscription(self):
        plans = self.platform_client.get(reverse('platform-billing-plans'))
        self.assertEqual(plans.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(plans.data), 5)
        detail = self.platform_client.get(
            reverse('platform-school-subscription', kwargs={'pk': self.school.pk}),
        )
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data['plan']['code'], 'starter')
