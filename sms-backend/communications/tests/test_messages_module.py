from decimal import Decimal

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tests.factories import create_school
from communications.models import SmsEncodingConfig
from communications.services.allowances import resolve_classification
from communications.services.pricing import create_sms_config_version, ensure_default_sms_configs
from communications.services.segments import analyze_sms, invalidate_limit_cache, sms_segment_count
from platform_admin.models import PlatformUser


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
