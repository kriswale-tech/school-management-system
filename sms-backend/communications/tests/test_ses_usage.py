from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings

from communications.models import Provider
from notifications.views_webhooks import confirm_sns_subscription
from communications.services.providers.ses_usage import (
    fetch_ses_usage,
    send_ses_test_email,
    sync_ses_usage,
)

class SnsConfirmTests(SimpleTestCase):
    def test_rejects_a_non_sns_host(self):
        self.assertFalse(confirm_sns_subscription('https://evil.example/confirm'))

    @override_settings(SES_SNS_TOPIC_ARN='arn:aws:sns:eu-north-1:039077528182:sms-ses-events')
    def test_rejects_a_different_topic(self):
        self.assertFalse(confirm_sns_subscription(
            'https://sns.eu-north-1.amazonaws.com/?Action=ConfirmSubscription',
            'arn:aws:sns:eu-north-1:039077528182:other',
        ))


LIVE_SETTINGS = dict(
    EMAIL_ENABLED=True,
    EMAIL_PROVIDER='ses',
    AWS_ACCESS_KEY_ID='AKIAtest',
    AWS_SECRET_ACCESS_KEY='secret',
    AWS_REGION='eu-north-1',
)


def _clients():
    ses = MagicMock()
    ses.get_send_quota.return_value = {
        'Max24HourSend': 200.0,
        'SentLast24Hours': 1.0,
        'MaxSendRate': 1.0,
    }
    cloudwatch = MagicMock()
    cloudwatch.get_metric_statistics.return_value = {
        'Datapoints': [{'Sum': 3.0}, {'Sum': 2.0}],
    }
    clients = {'ses': ses, 'cloudwatch': cloudwatch}
    return clients


@override_settings(**LIVE_SETTINGS)
class SesUsageSyncTests(TestCase):
    @patch('communications.services.providers.ses_usage._boto_client')
    def test_fetch_reads_quota_and_monthly_sends(self, boto_client):
        clients = _clients()
        boto_client.side_effect = lambda service: clients[service]

        payload = fetch_ses_usage()

        self.assertEqual(payload['emails']['daily']['used'], 1)
        self.assertEqual(payload['emails']['daily']['limit'], 200)
        self.assertEqual(payload['emails']['monthly']['used'], 5)
        self.assertEqual(payload['emails']['monthly']['sent'], 5)
        self.assertEqual(payload['emails']['monthly']['received'], 0)
        self.assertIsNone(payload['emails']['monthly']['limit'])
        cloudwatch_call = clients['cloudwatch'].get_metric_statistics.call_args.kwargs
        self.assertEqual(cloudwatch_call['Namespace'], 'AWS/SES')
        self.assertEqual(cloudwatch_call['MetricName'], 'Send')

    @patch('communications.services.providers.ses_usage.fetch_ses_usage')
    def test_sync_stores_live_snapshot(self, fetch):
        fetch.return_value = {
            'object': 'ses_usage',
            'configured': True,
            'emails': {
                'monthly': {'used': 5, 'limit': None, 'sent': 5, 'received': 0},
                'daily': {'used': 1, 'limit': 200, 'sent': 1, 'received': 0},
            },
        }

        result = sync_ses_usage()

        self.assertTrue(result['ok'])
        self.assertFalse(result['placeholder'])
        snapshot = result['snapshot']
        self.assertEqual(snapshot.monthly_used, 5)
        self.assertIsNone(snapshot.monthly_limit)
        self.assertEqual(snapshot.daily_used, 1)
        self.assertEqual(snapshot.daily_limit, 200)
        self.assertEqual(snapshot.sent_count, 5)
        self.assertEqual(snapshot.received_count, 0)
        self.assertEqual(snapshot.provider_account.provider, Provider.SES)
        self.assertEqual(snapshot.provider_account.api_status, 'ok')

    @patch('notifications.services.email_batch.send_email_batch')
    @patch('notifications.services.email_batch.ses_configured', return_value=True)
    def test_send_uses_the_app_ses_path(self, _configured, send_batch):
        send_batch.return_value = [{'ok': True, 'provider_message_id': 'ses-123'}]

        result = send_ses_test_email(
            to='pseudofaux25@gmail.com',
            subject='SES test',
            body='Hello from the platform.',
        )

        self.assertTrue(result['ok'])
        self.assertEqual(result['provider_message_id'], 'ses-123')
        payload = send_batch.call_args.args[0][0]
        self.assertEqual(payload['to'], 'pseudofaux25@gmail.com')
        self.assertEqual(payload['subject'], 'SES test')
        self.assertEqual(payload['text'], 'Hello from the platform.')
