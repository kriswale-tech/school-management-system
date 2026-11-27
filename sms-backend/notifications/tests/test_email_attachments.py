import base64

from django.test import SimpleTestCase, override_settings

from notifications.services.email_batch import _build_raw_message, _from_email


class EmailAttachmentMessageTests(SimpleTestCase):
    def test_raw_message_carries_the_pdf(self):
        raw = _build_raw_message(
            to_addr='guardian@example.com',
            subject='Receipt RCPT-1',
            text='The receipt is attached to this email.',
            html='<p>The receipt is attached to this email.</p>',
            attachments=[{
                'filename': 'RCPT-1.pdf',
                'content': b'%PDF-1.4 receipt',
                'mimetype': 'application/pdf',
            }],
        )

        self.assertIn(b'filename="RCPT-1.pdf"', raw)
        self.assertIn(b'application/pdf', raw)
        self.assertIn(
            base64.b64encode(b'%PDF-1.4 receipt'),
            raw,
        )

    @override_settings(
        DEFAULT_FROM_EMAIL='SchoolAssist <noreply@team.schoolassistgh.com>',
        GUARDIAN_FROM_EMAIL='SchoolAssist <noreply@notify.schoolassistgh.com>',
    )
    def test_parent_mail_uses_the_notify_address(self):
        self.assertEqual(
            _from_email(),
            'SchoolAssist <noreply@notify.schoolassistgh.com>',
        )
        raw = _build_raw_message(
            to_addr='guardian@example.com',
            subject='Fee reminder',
            text='Fees are due.',
            html='',
        )
        self.assertIn(b'noreply@notify.schoolassistgh.com', raw)
        self.assertNotIn(b'noreply@team.schoolassistgh.com', raw)

    @override_settings(
        DEFAULT_FROM_EMAIL='SchoolAssist <noreply@team.schoolassistgh.com>',
        GUARDIAN_FROM_EMAIL='',
    )
    def test_parent_mail_falls_back_to_the_team_address(self):
        self.assertEqual(
            _from_email(),
            'SchoolAssist <noreply@team.schoolassistgh.com>',
        )
