from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.tests.factories import create_school
from communications.models import MessagingAllowancePolicy, SmsEncodingConfig
from communications.services.allowances import resolve_classification
from communications.services.pricing import create_sms_config_version, ensure_default_sms_configs
from communications.services.segments import analyze_sms, invalidate_limit_cache, sms_segment_count
from notifications.models import GuardianDelivery
from platform_admin.models import PlatformUser
from students.models import Parent


class SegmentConfigTests(TestCase):
    def test_defaults_match_hardcoded_limits(self):
        ensure_default_sms_configs()
        self.assertEqual(sms_segment_count('Hello'), 1)
        self.assertEqual(sms_segment_count('x' * 160), 1)
        self.assertEqual(sms_segment_count('x' * 161), 2)
        self.assertEqual(sms_segment_count('€' * 80), 1)  # extended septets

    def test_calculator_matches_segment_count(self):
        ensure_default_sms_configs()
        body = 'Fees due — please pay'
        analysis = analyze_sms(body)
        self.assertEqual(analysis['segments'], sms_segment_count(body))
        self.assertEqual(analysis['credits_per_recipient'], analysis['segments'])

    def test_config_driven_multipart_limit(self):
        ensure_default_sms_configs()
        create_sms_config_version(
            encoding=SmsEncodingConfig.Encoding.GSM7,
            single_segment_limit=10,
            multipart_segment_limit=8,
        )
        invalidate_limit_cache()
        self.assertEqual(sms_segment_count('abcdefghijk'), 2)


class PricingVersionTests(TestCase):
    def test_versioning_does_not_mutate_history(self):
        ensure_default_sms_configs()
        first = SmsEncodingConfig.objects.get(
            encoding=SmsEncodingConfig.Encoding.GSM7,
            is_active=True,
        )
        first_id = first.pk
        first_cost = first.provider_cost_per_segment_ghs
        second = create_sms_config_version(
            encoding=SmsEncodingConfig.Encoding.GSM7,
            provider_cost_per_segment_ghs=Decimal('0.050000'),
        )
        first.refresh_from_db()
        self.assertFalse(first.is_active)
        self.assertEqual(first.provider_cost_per_segment_ghs, first_cost)
        self.assertEqual(first.pk, first_id)
        self.assertTrue(second.is_active)
        self.assertEqual(second.provider_cost_per_segment_ghs, Decimal('0.050000'))


class ClassificationTests(TestCase):
    def setUp(self):
        self.school = create_school(name='Msg School', phone_number='+233244911001')

    def test_default_is_paid_without_allowance(self):
        classification, policy, reason = resolve_classification(
            school=self.school,
            channel='sms',
            event_type='ward_enrolled',
            units=1,
        )
        self.assertEqual(classification, 'paid')
        self.assertIsNone(policy)
        self.assertEqual(reason, 'no_allowance')


class MessagesOverviewApiTests(TestCase):
    def setUp(self):
        self.user = PlatformUser.objects.create_user(
            email='messages-admin@example.com',
            password='SecurePass123!',
            role=PlatformUser.Role.SUPER_ADMIN,
        )
        self.client = APIClient()
        login = self.client.post(
            reverse('platform-login'),
            {'email': 'messages-admin@example.com', 'password': 'SecurePass123!'},
            format='json',
        )
        access = settings.PLATFORM_JWT['AUTH_COOKIE']
        self.client.cookies[access] = login.cookies[access].value

    def test_overview_ok(self):
        response = self.client.get('/api/v1/platform/messages/overview/?range=last_7')
        self.assertEqual(response.status_code, 200)
        self.assertIn('range', response.data)
        self.assertIn('channels', response.data)

    def test_overview_accepts_legacy_range_alias(self):
        response = self.client.get('/api/v1/platform/messages/overview/?range=30d')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['range']['range'], 'last_30')

    def test_sms_calculator(self):
        ensure_default_sms_configs()
        response = self.client.post(
            '/api/v1/platform/messages/calculator/sms/',
            {'body': 'Hello world'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['segments'], 1)


class FreeUsageApiTests(TestCase):
    def setUp(self):
        self.user = PlatformUser.objects.create_user(
            email='free-usage@example.com',
            password='SecurePass123!',
            role=PlatformUser.Role.SUPER_ADMIN,
        )
        self.client = APIClient()
        login = self.client.post(
            reverse('platform-login'),
            {'email': 'free-usage@example.com', 'password': 'SecurePass123!'},
            format='json',
        )
        access = settings.PLATFORM_JWT['AUTH_COOKIE']
        self.client.cookies[access] = login.cookies[access].value

        self.alpha = create_school(name='Alpha School', phone_number='+233244911101')
        self.beta = create_school(name='Beta School', phone_number='+233244911102')
        self.paid_only = create_school(name='Gamma School', phone_number='+233244911103')
        self.alpha_parent = Parent.objects.create(
            school=self.alpha,
            name='Alpha Guardian',
            phone_number='+233244911201',
        )
        self.beta_parent = Parent.objects.create(
            school=self.beta,
            name='Beta Guardian',
            phone_number='+233244911202',
        )
        self.gamma_parent = Parent.objects.create(
            school=self.paid_only,
            name='Gamma Guardian',
            phone_number='+233244911203',
        )
        now = timezone.now()
        self.platform_allowance = MessagingAllowancePolicy.objects.create(
            name='Platform free SMS',
            scope=MessagingAllowancePolicy.Scope.PLATFORM,
            channel=MessagingAllowancePolicy.Channel.SMS,
            classification=MessagingAllowancePolicy.Classification.FREE,
            monthly_free_units=100,
            budget_ghs=Decimal('10.00'),
            starts_at=now - timedelta(days=1),
            is_active=True,
            created_by=self.user,
        )
        MessagingAllowancePolicy.objects.create(
            name='Retired platform budget',
            scope=MessagingAllowancePolicy.Scope.PLATFORM,
            channel=MessagingAllowancePolicy.Channel.EMAIL,
            budget_ghs=Decimal('100.00'),
            starts_at=now - timedelta(days=10),
            is_active=False,
            created_by=self.user,
        )
        MessagingAllowancePolicy.objects.create(
            name='Alpha school budget',
            scope=MessagingAllowancePolicy.Scope.SCHOOL,
            school=self.alpha,
            channel=MessagingAllowancePolicy.Channel.SMS,
            budget_ghs=Decimal('50.00'),
            starts_at=now - timedelta(days=1),
            is_active=True,
            created_by=self.user,
        )

        self._delivery(
            self.alpha,
            self.alpha_parent,
            'alpha-free-sms',
            channel=GuardianDelivery.Channel.SMS,
            classification=GuardianDelivery.BillingClassification.FREE,
            segments=2,
            cost='0.40',
            allowance=self.platform_allowance,
        )
        self._delivery(
            self.alpha,
            self.alpha_parent,
            'alpha-free-email',
            channel=GuardianDelivery.Channel.EMAIL,
            classification=GuardianDelivery.BillingClassification.FREE,
            segments=0,
            cost='0.10',
        )
        self._delivery(
            self.alpha,
            self.alpha_parent,
            'alpha-paid-sms',
            channel=GuardianDelivery.Channel.SMS,
            classification=GuardianDelivery.BillingClassification.PAID,
            segments=4,
            cost='9.00',
        )
        self._delivery(
            self.beta,
            self.beta_parent,
            'beta-sponsored-sms',
            channel=GuardianDelivery.Channel.SMS,
            classification=GuardianDelivery.BillingClassification.SPONSORED,
            segments=3,
            cost='0.30',
            allowance=self.platform_allowance,
        )
        self._delivery(
            self.paid_only,
            self.gamma_parent,
            'gamma-paid-sms',
            channel=GuardianDelivery.Channel.SMS,
            classification=GuardianDelivery.BillingClassification.PAID,
            segments=1,
            cost='1.00',
        )

    def _delivery(
        self,
        school,
        parent,
        key,
        *,
        channel,
        classification,
        segments,
        cost,
        allowance=None,
    ):
        GuardianDelivery.objects.create(
            school=school,
            parent=parent,
            event_type=GuardianDelivery.EventType.DEBT_REMINDER,
            channel=channel,
            status=GuardianDelivery.Status.DELIVERED,
            recipient_address=parent.phone_number,
            body_preview='Hello',
            idempotency_key=key,
            segments=segments,
            billing_classification=classification,
            allowance=allowance,
            provider_cost_snapshot_ghs=Decimal(cost),
        )

    def test_free_usage_includes_budget_and_schools(self):
        response = self.client.get('/api/v1/platform/messages/free-usage/?range=last_30')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['budget_ghs'], '10.00')
        self.assertEqual(response.data['budget_used_pct'], 7.0)
        rows = {row['school_name']: row for row in response.data['by_school']}
        self.assertEqual(list(rows), ['Alpha School', 'Beta School'])
        self.assertEqual(rows['Alpha School']['free_sms_segments'], 2)
        self.assertEqual(rows['Alpha School']['free_email_credits'], 1)
        self.assertEqual(rows['Alpha School']['sponsored_sms_segments'], 0)
        self.assertEqual(rows['Alpha School']['expense_ghs'], '0.50')
        self.assertEqual(rows['Beta School']['sponsored_sms_segments'], 3)
        self.assertEqual(rows['Beta School']['expense_ghs'], '0.30')
        self.assertEqual(response.data['sms']['free']['units'], 2)
        self.assertEqual(response.data['sms']['sponsored']['units'], 3)
