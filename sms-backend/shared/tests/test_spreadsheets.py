from datetime import date, datetime

from django.test import SimpleTestCase

from shared.services.spreadsheets import normalize_cell


class NormalizeCellTests(SimpleTestCase):
    def test_none_becomes_empty_string(self):
        self.assertEqual(normalize_cell(None), '')

    def test_datetime_becomes_iso_date(self):
        self.assertEqual(
            normalize_cell(datetime(2015, 3, 12, 15, 30, 0)),
            '2015-03-12',
        )

    def test_date_becomes_iso_date(self):
        self.assertEqual(normalize_cell(date(2025, 9, 1)), '2025-09-01')

    def test_string_is_stripped(self):
        self.assertEqual(normalize_cell('  Ama  '), 'Ama')
