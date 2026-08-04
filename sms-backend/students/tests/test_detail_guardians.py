from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from academics.models import ClassLevel, Level
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school
from schools.models import AcademicYear, Term
from students.models import Parent, StudentParent
from students.tests.factories import create_student, enroll_student, ensure_default_stream


class StudentDetailGuardianViewTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=True)
        set_client_auth_cookies(self.client, self.user)
        self.school = user_school(self.user)
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
        self.stream = ensure_default_stream(self.class_level)
        self.student = create_student(
            school=self.school,
            student_id='TA-0001',
            first_name='Ama',
            last_name='Mensah',
            date_of_birth=date(2015, 3, 12),
        )
        self.student.address = 'Accra'
        self.student.save(update_fields=['address', 'updated_at'])
        enroll_student(
            student=self.student,
            term=self.term,
            stream=self.stream,
            is_new_student=True,
        )

        self.parent_a = Parent.objects.create(
            school=self.school,
            name='Akosua Mensah',
            phone_number='+233244111222',
            email='akosua@example.com',
        )
        self.parent_b = Parent.objects.create(
            school=self.school,
            name='Kwame Mensah',
            phone_number='+233244333444',
        )
        self.link_a = StudentParent.objects.create(
            student=self.student,
            parent=self.parent_a,
            relationship=StudentParent.RelationshipChoices.MOTHER,
            is_primary=True,
        )
        self.link_b = StudentParent.objects.create(
            student=self.student,
            parent=self.parent_b,
            relationship=StudentParent.RelationshipChoices.FATHER,
            is_primary=False,
        )

        self.detail_url = reverse('student-detail', kwargs={'student_id': self.student.id})
        self.guardians_url = reverse(
            'student-guardians',
            kwargs={'student_id': self.student.id},
        )

    def test_get_student_detail(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['student_id'], 'TA-0001')
        self.assertEqual(response.data['full_name'], 'Ama Mensah')
        self.assertEqual(response.data['address'], 'Accra')
        self.assertTrue(response.data['is_active'])
        self.assertTrue(response.data['is_new_student'])
        self.assertEqual(response.data['class_assignment']['display_name'], 'JHS 1')
        self.assertEqual(len(response.data['guardians']), 2)
        self.assertIsInstance(response.data['age'], int)

    def test_patch_student_updates_editable_fields_only(self):
        response = self.client.patch(
            self.detail_url,
            {
                'address': 'Kumasi',
                'other_names': 'Serwaa',
                'student_id': 'HACKED',
                'is_new_student': False,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['address'], 'Kumasi')
        self.assertEqual(response.data['other_names'], 'Serwaa')
        self.assertEqual(response.data['full_name'], 'Ama Serwaa Mensah')
        self.assertEqual(response.data['student_id'], 'TA-0001')
        self.assertTrue(response.data['is_new_student'])

        self.student.refresh_from_db()
        self.assertEqual(self.student.student_id, 'TA-0001')

    def test_update_guardian_phone_and_relationship(self):
        url = reverse(
            'student-guardian-detail',
            kwargs={'student_id': self.student.id, 'link_id': self.link_a.id},
        )
        response = self.client.patch(
            url,
            {
                'phone_number': '0244999888',
                'relationship': 'guardian',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone_number'], '+233244999888')
        self.assertEqual(response.data['relationship'], 'guardian')
        self.parent_a.refresh_from_db()
        self.assertEqual(self.parent_a.phone_number, '+233244999888')

    def test_delete_primary_promotes_another_guardian(self):
        url = reverse(
            'student-guardian-detail',
            kwargs={'student_id': self.student.id, 'link_id': self.link_a.id},
        )
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(StudentParent.objects.filter(id=self.link_a.id).exists())
        self.link_b.refresh_from_db()
        self.assertTrue(self.link_b.is_primary)

    def test_cannot_delete_last_guardian(self):
        self.link_b.delete()
        url = reverse(
            'student-guardian-detail',
            kwargs={'student_id': self.student.id, 'link_id': self.link_a.id},
        )
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(StudentParent.objects.filter(id=self.link_a.id).exists())

    def test_add_guardian(self):
        parent = Parent.objects.create(
            school=self.school,
            name='Auntie Efua',
            phone_number='+233200111222',
        )
        response = self.client.post(
            self.guardians_url,
            {
                'parent_id': str(parent.id),
                'relationship': 'aunt',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Auntie Efua')
        self.assertEqual(self.student.parent_links.count(), 3)
