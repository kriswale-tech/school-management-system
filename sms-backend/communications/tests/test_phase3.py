from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.tests.factories import create_school, create_user, set_client_auth_cookies
from billing.models import SchoolSubscription
from billing.services.catalog import seed_default_plans, seed_first_year_free_campaign
from billing.services.subscriptions import open_renewal_period, start_subscription
from communications.models import CreditLedgerEntry
from communications.services.addons import schedule_addon_change
from communications.services.catalog import seed_default_skus
from communications.services.gates import can_send_channel, communications_billing_active
from communications.services.ledger import debit_usage, get_balances, write_ledger_entry
from communications.services.segments import sms_segment_count
from notifications.models import GuardianDelivery
from notifications.services.deliver_guardian import deliver_guardian_sms_batch
from students.tests.factories import create_student


class SegmentCountingTests(APITestCase):
    def test_gsm7_single_and_concat(self):
        self.assertEqual(sms_segment_count('Hello'), 1)
        self.assertEqual(sms_segment_count('a' * 160), 1)
        self.assertEqual(sms_segment_count('a' * 161), 2)

    def test_unicode_segments(self):
        self.assertEqual(sms_segment_count('你好'), 1)
        self.assertEqual(sms_segment_count('你' * 70), 1)
        self.assertEqual(sms_segment_count('你' * 71), 2)


class CommunicationsPhase3Tests(APITestCase):
    def setUp(self):
        seed_default_plans()
        seed_first_year_free_campaign()
        seed_default_skus()
        self.school = create_school(name='Comms School', phone_number='+233244900001')
        self.subscription = start_subscription(
            school=self.school,
            apply_first_year_free=True,
            interval=SchoolSubscription.Interval.ANNUAL,
        )
        self.admin = create_user(
            school=self.school,
            is_active=True,
            phone_number='+233244900002',
            email='comms-admin@test.com',
        )
        set_client_auth_cookies(self.client, self.admin)

    def test_zero_balance_blocks_sends(self):
        self.assertTrue(communications_billing_active(self.school))
        eligibility = can_send_channel(self.school, channel='sms', body='Hi')
        self.assertFalse(eligibility.allowed)
        self.assertEqual(eligibility.reason, 'insufficient_credits')
        self.assertEqual(eligibility.balance, 0)
        self.assertTrue(eligibility.billing_active)

    def test_cancel_scheduled_addon_change(self):
        schedule_addon_change(school=self.school, channel='sms', enabled=True)
        self.subscription.refresh_from_db()
        self.assertTrue(self.subscription.pending_sms_enabled)
        self.assertIsNotNone(self.subscription.pending_change_effective_at)

        # Scheduling the current (disabled) state clears the pending enable.
        schedule_addon_change(school=self.school, channel='sms', enabled=False)
        self.subscription.refresh_from_db()
        self.assertIsNone(self.subscription.pending_sms_enabled)
        self.assertIsNone(self.subscription.pending_sms_sku)
        self.assertIsNone(self.subscription.pending_change_effective_at)

    def test_schedule_addon_and_allocate_on_renewal(self):
        schedule_addon_change(school=self.school, channel='sms', enabled=True)
        self.subscription.refresh_from_db()
        self.assertTrue(self.subscription.pending_sms_enabled)
        self.assertFalse(self.subscription.sms_addon_enabled)

        # Force period end to now so renewal advances cleanly
        self.subscription.current_period_end = timezone.now()
        self.subscription.save(update_fields=['current_period_end', 'updated_at'])

        subscription, invoice = open_renewal_period(subscription=self.subscription)
        # Addon line keeps invoice non-zero even under first-year app promo.
        if invoice.status != invoice.Status.PAID:
            from billing.services.invoices import mark_invoice_paid
            from communications.services.addons import allocate_period_addons

            mark_invoice_paid(invoice)
            period = subscription.periods.order_by('-starts_at').first()
            allocate_period_addons(
                subscription=subscription,
                period=period,
                invoice=invoice,
            )

        self.subscription.refresh_from_db()
        self.assertTrue(self.subscription.sms_addon_enabled)
        self.assertTrue(communications_billing_active(self.school))
        balances = get_balances(self.school)
        self.assertEqual(balances['sms'], self.subscription.sms_sku.credits_per_period)
        self.assertTrue(
            CreditLedgerEntry.objects.filter(
                school=self.school,
                entry_type=CreditLedgerEntry.EntryType.ALLOCATION_RECURRING,
                channel='sms',
            ).exists(),
        )

    def test_debit_and_skip_when_insufficient(self):
        write_ledger_entry(
            school=self.school,
            channel='sms',
            entry_type=CreditLedgerEntry.EntryType.PROMO_GRANT,
            delta=1,
            idempotency_key='promo:test:1',
        )
        self.assertTrue(communications_billing_active(self.school))

        student = create_student(school=self.school)
        from students.models import Parent, StudentParent

        parent = Parent.objects.create(
            school=self.school,
            name='Parent One',
            phone_number='+233244900099',
        )
        StudentParent.objects.create(student=student, parent=parent, relationship='mother')

        items = [
            {
                'school_id': str(self.school.pk),
                'parent_id': str(parent.pk),
                'student_id': str(student.pk),
                'event_type': GuardianDelivery.EventType.DEBT_REMINDER,
                'recipient_address': parent.phone_number,
                'body': 'Pay fees please',
                'idempotency_key': 'test-sms-1',
            },
            {
                'school_id': str(self.school.pk),
                'parent_id': str(parent.pk),
                'student_id': str(student.pk),
                'event_type': GuardianDelivery.EventType.DEBT_REMINDER,
                'recipient_address': parent.phone_number,
                'body': 'Second message',
                'idempotency_key': 'test-sms-2',
            },
        ]

        with patch(
            'notifications.services.deliver_guardian.send_personalized_sms_batch',
            return_value=[
                {
                    'key': 'test-sms-1',
                    'phone': parent.phone_number,
                    'ok': True,
                    'provider_message_id': 'ark-1',
                },
            ],
        ):
            result = deliver_guardian_sms_batch(items)

        self.assertEqual(result['sent'], 1)
        self.assertEqual(result['skipped'], 1)
        self.assertEqual(get_balances(self.school)['sms'], 0)
        self.assertEqual(
            GuardianDelivery.objects.filter(
                status=GuardianDelivery.Status.SENT,
            ).count(),
            1,
        )
        self.assertEqual(
            GuardianDelivery.objects.filter(
                status=GuardianDelivery.Status.SKIPPED,
                skip_reason='insufficient_credits',
            ).count(),
            1,
        )

    def test_debit_idempotent(self):
        write_ledger_entry(
            school=self.school,
            channel='email',
            entry_type=CreditLedgerEntry.EntryType.PROMO_GRANT,
            delta=5,
            idempotency_key='promo:email:1',
        )
        first = debit_usage(
            school=self.school,
            channel='email',
            units=2,
            idempotency_key='usage:abc',
        )
        second = debit_usage(
            school=self.school,
            channel='email',
            units=2,
            idempotency_key='usage:abc',
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(get_balances(self.school)['email'], 3)

    def test_school_credits_api(self):
        response = self.client.get(reverse('school-comms-credits'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sms'], 0)
        self.assertTrue(response.data['billing_active'])
