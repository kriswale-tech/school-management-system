from django.test import TestCase

from schools.models import Term
from schools.setup_serializers import SetupAcademicYearTermSerializer
from schools.tests.factories import academic_year_term_payload


class SetupAcademicYearTermSerializerTests(TestCase):
    def test_valid_payload_passes(self):
        serializer = SetupAcademicYearTermSerializer(data=academic_year_term_payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_rejects_missing_term(self):
        payload = academic_year_term_payload()
        payload['terms'] = payload['terms'][:2]

        serializer = SetupAcademicYearTermSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn('terms', serializer.errors)

    def test_rejects_mismatched_academic_year_label(self):
        payload = academic_year_term_payload(academic_year='2025/2026')

        serializer = SetupAcademicYearTermSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn('academic_year', serializer.errors)

    def test_rejects_overlapping_term_dates(self):
        payload = academic_year_term_payload()
        payload['terms'][1]['start_date'] = '2026-12-01'

        serializer = SetupAcademicYearTermSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn('terms', serializer.errors)

    def test_rejects_term_with_invalid_date_order(self):
        payload = academic_year_term_payload()
        payload['terms'][0]['end_date'] = '2026-08-01'

        serializer = SetupAcademicYearTermSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
