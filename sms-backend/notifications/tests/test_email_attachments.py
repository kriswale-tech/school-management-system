import base64

from django.test import SimpleTestCase

from notifications.services.email_batch import _build_raw_message


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
