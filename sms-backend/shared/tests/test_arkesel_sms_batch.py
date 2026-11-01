from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from shared.services.arkesel_sms import send_personalized_sms_batch, send_sms_to_recipients


class ArkeselSmsBatchTests(SimpleTestCase):
    @override_settings(ARKESEL_API_KEY='test-key', ARKESEL_SMS_SENDER='SCHOOL', DEBUG=True)
    @patch('shared.services.arkesel_sms.requests.post')
    def test_send_sms_to_recipients_posts_batch(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'status': 'success',
            'data': [{'id': 'a'}, {'id': 'b'}],
        }
        mock_post.return_value.raise_for_status = lambda: None

        payload = send_sms_to_recipients(['+233111', '+233222'], 'Hello')

        self.assertEqual(payload['status'], 'success')
        body = mock_post.call_args.kwargs['json']
        self.assertEqual(body['recipients'], ['+233111', '+233222'])
        self.assertEqual(body['message'], 'Hello')
        self.assertTrue(body['sandbox'])

    @override_settings(ARKESEL_API_KEY='test-key', ARKESEL_SMS_SENDER='SCHOOL', DEBUG=False)
    @patch('shared.services.arkesel_sms.send_sms_to_recipients')
    def test_personalized_groups_identical_bodies(self, mock_send):
        mock_send.return_value = {
            'status': 'success',
            'data': [{'id': '1'}, {'id': '2'}],
        }

        results = send_personalized_sms_batch([
            {'phone': '+233111', 'message': 'Same', 'key': 'k1'},
            {'phone': '+233222', 'message': 'Same', 'key': 'k2'},
            {'phone': '+233333', 'message': 'Other', 'key': 'k3'},
        ])

        self.assertEqual(mock_send.call_count, 2)
        first_recipients = mock_send.call_args_list[0].args[0]
        self.assertEqual(first_recipients, ['+233111', '+233222'])
        self.assertTrue(all(row['ok'] for row in results))
        self.assertEqual(results[0]['provider_message_id'], '1')
        self.assertEqual(results[1]['provider_message_id'], '2')
