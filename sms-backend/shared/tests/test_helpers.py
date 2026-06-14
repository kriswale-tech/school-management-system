from django.test import SimpleTestCase
from shared.helpers import format_phone_number

class FormatPhoneNumberTests(SimpleTestCase):
    def test_accepts_international_format(self):
        result = format_phone_number('+233244567890')
        self.assertEqual(result, '+233244567890')

    def test_accepts_local_format(self):
        result = format_phone_number('0244567890')
        self.assertEqual(result, '+233244567890')

    def test_raises_error_for_invalid_format(self):
        with self.assertRaises(ValueError):
            format_phone_number('1234567890')

    def test_raises_error_for_invalid_country_code(self):
        with self.assertRaises(ValueError):
            format_phone_number('+234244567890')

    def test_strips_surrounding_whitespace(self):
        result = format_phone_number(' 0244567890 ')
        self.assertEqual(result, '+233244567890')