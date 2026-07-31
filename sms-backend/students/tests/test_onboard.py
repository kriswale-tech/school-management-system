from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, ClassStream, Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from schools.models import AcademicYear, Term
from students.models import Parent, Student
from students.tests.factories import ensure_default_stream


class StudentOnboardViewTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.user)
        self.school = user_school(self.user)
        self.school.name = 'Test Academy'
        self.school.save(update_fields=['name'])

        self.academic_year = AcademicYear.objects.create(
            school=self.school,
            academic_year='2025/2026',
            start_date=date(2025, 9, 1),
            end_date=date(2026, 7, 31),
            is_active=True,
        )
        self.term = Term.objects.create(
            school=self.school,
            academic_year=self.academic_year,
            term=Term.TermChoices.FIRST_TERM,
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 15),
            is_active=True,
        )
        self.level = Level.objects.create(
            school=self.school,
            name='Junior High',
            is_system_generated=False,
        )
        self.class_level = ClassLevel.objects.create(
            school=self.school,
            level=self.level,
            name='JHS 1',
            is_system_generated=False,
        )
        self.default_stream = ensure_default_stream(self.class_level)
        self.named_stream = ClassStream.objects.create(
            class_level=self.class_level,
            name='A',
            is_default=False,
        )
        self.url = reverse('student-onboard')

    def test_onboard_creates_student_guardians_and_enrollment(self):
        payload = {
            'first_name': 'Ama',
            'last_name': 'Mensah',
            'other_names': 'Serwaa',
            'gender': 'female',
            'date_of_birth': '2015-03-12',
            'admission_date': '2025-09-01',
            'guardians': [
                {
                    'name': 'Akosua Mensah',
                    'phone_number': '0244111222',
                    'email': 'akosua@example.com',
                    'relationship': 'mother',
                },
                {
                    'name': 'Kwame Mensah',
                    'phone_number': '0244333444',
                    'email': '',
                    'relationship': 'father',
                },
            ],
            'stream_id': str(self.named_stream.id),
            'is_new_student': True,
        }

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['student_id'], 'TA-0001')
        self.assertEqual(response.data['first_name'], 'Ama')
        self.assertEqual(response.data['stream']['name'], 'A')
        self.assertTrue(response.data['is_new_student'])
        self.assertEqual(response.data['primary_parent']['name'], 'Akosua Mensah')
        self.assertEqual(response.data['primary_parent']['phone_number'], '+233244111222')
        self.assertEqual(response.data['payment_status'], 'no_fees')

        student = Student.objects.get(student_id='TA-0001')
        self.assertEqual(student.parent_links.count(), 2)
        self.assertTrue(
            student.parent_links.get(parent__phone_number='+233244111222').is_primary,
        )
        self.assertFalse(
            student.parent_links.get(parent__phone_number='+233244333444').is_primary,
        )

    def test_onboard_reuses_existing_parent_by_phone(self):
        Parent.objects.create(
            school=self.school,
            name='Existing Parent',
            phone_number='+233244111222',
        )
        payload = {
            'first_name': 'Kofi',
            'last_name': 'Mensah',
            'gender': 'male',
            'date_of_birth': '2014-01-01',
            'admission_date': '2025-09-01',
            'guardians': [
                {
                    'name': 'Akosua Mensah',
                    'phone_number': '0244111222',
                    'relationship': 'mother',
                },
            ],
            'stream_id': str(self.default_stream.id),
            'is_new_student': False,
        }

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Parent.objects.filter(school=self.school).count(), 1)
        self.assertEqual(response.data['student_id'], 'TA-0001')

    def test_onboard_links_existing_parent_by_id(self):
        parent = Parent.objects.create(
            school=self.school,
            name='Existing Parent',
            phone_number='+233244111222',
            email='parent@example.com',
        )
        payload = {
            'first_name': 'Kofi',
            'last_name': 'Mensah',
            'gender': 'male',
            'date_of_birth': '2014-01-01',
            'admission_date': '2025-09-01',
            'guardians': [
                {
                    'parent_id': str(parent.id),
                    'relationship': 'father',
                },
            ],
            'stream_id': str(self.default_stream.id),
            'is_new_student': True,
        }

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Parent.objects.filter(school=self.school).count(), 1)
        self.assertEqual(response.data['primary_parent']['id'], str(parent.id))
        self.assertEqual(response.data['primary_parent']['name'], 'Existing Parent')
        self.assertEqual(response.data['primary_parent']['relationship'], 'father')

        student = Student.objects.get(student_id='TA-0001')
        self.assertEqual(student.parent_links.count(), 1)
        self.assertEqual(student.parent_links.get().parent_id, parent.id)

    def test_onboard_rejects_unknown_parent_id(self):
        payload = {
            'first_name': 'Kofi',
            'last_name': 'Mensah',
            'gender': 'male',
            'date_of_birth': '2014-01-01',
            'admission_date': '2025-09-01',
            'guardians': [
                {
                    'parent_id': '00000000-0000-0000-0000-000000000099',
                    'relationship': 'father',
                },
            ],
            'stream_id': str(self.default_stream.id),
            'is_new_student': True,
        }

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('parent_id', response.data['raw_detail'])