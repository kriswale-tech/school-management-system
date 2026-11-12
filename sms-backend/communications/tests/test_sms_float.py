from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.tests.factories import create_school, create_user
from communications.models import Provider, ProviderAccount, ProviderChannel
from communications.services.ledger import get_balances
from communications.services.providers.accounts import get_provider_account
from communications.services.providers.arkesel_balance import sync_arkesel_balance
from communications.tests.helpers import seed_test_credits
from notifications.models import GuardianDelivery, Notification
from notifications.services.deliver_guardian import deliver_guardian_sms_batch
from platform_admin.models import PlatformUser
from students.models import Parent, StudentParent
from students.tests.factories import create_student


def _set_float(units, *, age=None, reserved=0):
    account = get_provider_account(provider=Provider.ARKESEL, channel=ProviderChannel.SMS)
    account.sms_float_units = units
    account.sms_float_reserved = reserved
    account.sms_float_synced_at = timezone.now() - (age or timedelta(0))
    account.sms_low_balance_alerted_at = None
    account.sms_hold_alerted_at = None
    account.save()
    return account


def _float():
    return ProviderAccount.objects.get(provider=Provider.ARKESEL, channel=ProviderChannel.SMS)


@override_settings(ARKESEL_FLOAT_ASSUME_UNITS=None, EMAIL_ENABLED=False)
class ArkeselFloatTests(TestCase):
    def setUp(self):
        self.school = create_school(name='Float School', phone_number='+233244910001')
        self.admin = create_user(
            school=self.school,
            is_active=True,
            phone_number='+233244910002',
            email='float-admin@test.com',
        )
        seed_test_credits(self.school, sms=10, email=0)
        self.student = create_student(school=self.school, student_id='FL-1')
        self.parent = Parent.objects.create(
            school=self.school,
            name='Parent Float',
            phone_number='+233244910099',
        )
        StudentParent.objects.create(
            student=self.student,
            parent=self.parent,
            relationship='mother',
        )
        self.ops = PlatformUser.objects.create_user(
            email='ops-messages@test.com',
            password='secret-pass-1',
            role=PlatformUser.Role.OPERATIONS,
        )
        self.support = PlatformUser.objects.create_user(
            email='support-messages@test.com',
            password='secret-pass-1',
            role=PlatformUser.Role.SUPPORT,
        )
        self.curriculum = PlatformUser.objects.create_user(
            email='curriculum@test.com',
            password='secret-pass-1',
            role=PlatformUser.Role.CURRICULUM,
        )
        mail.outbox.clear()

    def _items(self, *keys):
        return [
            {
                'school_id': str(self.school.pk),
                'parent_id': str(self.parent.pk),
                'student_id': str(self.student.pk),
                'event_type': GuardianDelivery.EventType.DEBT_REMINDER,
                'recipient_address': self.parent.phone_number,
                'body': f'Message {key}',
                'idempotency_key': key,
            }
            for key in keys
        ]

    def _subjects(self):
        return [message.subject for message in mail.outbox]

    def test_short_wallet_holds_the_rest_and_keeps_school_credits(self):
        _set_float(1)
        with patch(
            'notifications.services.deliver_guardian.send_personalized_sms_batch',
            return_value=[{
                'key': 'float-1',
                'ok': True,
                'outcome': 'submitted',
                'provider_message_id': 'ark-1',
            }],
        ):
            result = deliver_guardian_sms_batch(self._items('float-1', 'float-2'))

        self.assertEqual(result['sent'], 1)
        self.assertEqual(result['skipped'], 1)
        self.assertEqual(get_balances(self.school)['sms'], 9)
        held = GuardianDelivery.objects.get(idempotency_key='float-2')
        self.assertEqual(held.status, GuardianDelivery.Status.SKIPPED)
        self.assertEqual(held.skip_reason, 'provider_wallet_unavailable')
        self.assertIn('credits were not used', held.user_error_message)
        self.assertEqual(held.credits_charged, 0)
        account = _float()
        self.assertEqual(account.sms_float_units, 0)
        self.assertEqual(account.sms_float_reserved, 0)
        self.assertTrue(
            Notification.objects.filter(
                school=self.school,
                title='SMS is temporarily unavailable',
            ).exists(),
        )
        paused = [
            message for message in mail.outbox
            if message.subject.startswith('School SMS is paused')
        ]
        self.assertEqual(len(paused), 1)
        self.assertEqual(
            sorted(paused[0].to),
            ['ops-messages@test.com', 'support-messages@test.com'],
        )
        self.assertNotIn('curriculum@test.com', paused[0].to)

    def test_missing_balance_holds_every_message(self):
        result = deliver_guardian_sms_batch(self._items('missing-1'))

        self.assertEqual(result['sent'], 0)
        self.assertEqual(result['skipped'], 1)
        self.assertEqual(get_balances(self.school)['sms'], 10)
        self.assertEqual(
            GuardianDelivery.objects.get(idempotency_key='missing-1').skip_reason,
            'provider_wallet_unavailable',
        )
        self.assertTrue(any('No Arkesel balance' in message.body for message in mail.outbox))

    def test_stale_balance_holds_without_spending_the_float(self):
        _set_float(50, age=timedelta(hours=3))
        result = deliver_guardian_sms_batch(self._items('stale-1'))

        self.assertEqual(result['skipped'], 1)
        self.assertEqual(get_balances(self.school)['sms'], 10)
        self.assertEqual(_float().sms_float_units, 50)
        self.assertTrue(any('older than' in message.body for message in mail.outbox))

    def test_rejected_send_returns_units_to_the_float(self):
        _set_float(5)
        with patch(
            'notifications.services.deliver_guardian.send_personalized_sms_batch',
            return_value=[{
                'key': 'fail-1',
                'ok': False,
                'outcome': 'failed',
                'user_message': 'The SMS could not be sent.',
            }],
        ):
            result = deliver_guardian_sms_batch(self._items('fail-1'))

        self.assertEqual(result['failed'], 1)
        self.assertEqual(get_balances(self.school)['sms'], 10)
        self.assertEqual(_float().sms_float_units, 5)
        self.assertEqual(_float().sms_float_reserved, 0)

    def test_hold_email_does_not_repeat_inside_the_cooldown(self):
        _set_float(0)
        deliver_guardian_sms_batch(self._items('cool-1'))
        mail.outbox.clear()
        deliver_guardian_sms_batch(self._items('cool-2'))
        self.assertEqual(self._subjects(), [])

    @patch(
        'communications.services.providers.sms_float.recent_sms_units',
        return_value=70,
    )
    @patch('communications.services.providers.arkesel_balance.fetch_arkesel_balance')
    def test_low_balance_sync_emails_message_admins(self, fetch_balance, _usage):
        fetch_balance.return_value = {'sms_balance': 10}
        result = sync_arkesel_balance()

        self.assertTrue(result['ok'])
        self.assertEqual(_float().sms_float_units, 10)
        low = [message for message in mail.outbox if message.subject == 'Arkesel SMS balance is low']
        self.assertEqual(len(low), 1)
        self.assertEqual(
            sorted(low[0].to),
            ['ops-messages@test.com', 'support-messages@test.com'],
        )
        self.assertNotIn('curriculum@test.com', low[0].to)

    @patch('communications.services.providers.arkesel_balance.fetch_arkesel_balance')
    def test_empty_wallet_sync_emails_message_admins(self, fetch_balance):
        fetch_balance.return_value = {'sms_balance': 0}
        sync_arkesel_balance()

        self.assertEqual(_float().sms_float_units, 0)
        self.assertTrue(
            any(message.subject == 'Arkesel SMS wallet is empty' for message in mail.outbox),
        )

    @patch('communications.services.providers.arkesel_balance.fetch_arkesel_balance')
    def test_sync_failure_emails_once(self, fetch_balance):
        fetch_balance.side_effect = RuntimeError('ARKESEL_API_KEY is not configured.')
        sync_arkesel_balance()
        self.assertEqual(
            [message.subject for message in mail.outbox],
            ['Arkesel balance could not be read'],
        )
        mail.outbox.clear()
        sync_arkesel_balance()

        self.assertEqual(mail.outbox, [])
        self.assertIsNone(_float().sms_float_synced_at)
