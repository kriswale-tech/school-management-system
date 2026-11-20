from django.urls import reverse
from rest_framework import status

from accounts.models import SchoolMembership, User
from accounts.tests.base import AccountsAPITestCase
from accounts.tests.factories import create_school, create_user, set_client_auth_cookies, user_school


class StaffIdTests(AccountsAPITestCase):
    def setUp(self):
        self.admin = create_user(is_active=True)
        self.school = user_school(self.admin)
        self.school.student_id_prefix = 'UA'
        self.school.save(update_fields=['student_id_prefix', 'updated_at'])
        set_client_auth_cookies(self.client, self.admin)
        self.url = reverse('user-list')

    def test_blank_staff_id_is_generated(self):
        response = self.client.post(
            self.url,
            {
                'first_name': 'Ama',
                'last_name': 'Boateng',
                'phone_number': '0244111222',
                'role': User.RoleChoices.TEACHER,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['staff_id'], 'UA-S0001')

    def test_provided_staff_id_is_saved(self):
        response = self.client.post(
            self.url,
            {
                'first_name': 'Ama',
                'last_name': 'Boateng',
                'phone_number': '0244111222',
                'role': User.RoleChoices.TEACHER,
                'staff_id': 'EMP-9',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['staff_id'], 'EMP-9')

    def test_duplicate_staff_id_is_rejected(self):
        self.client.post(
            self.url,
            {
                'first_name': 'Ama',
                'last_name': 'Boateng',
                'phone_number': '0244111222',
                'role': User.RoleChoices.TEACHER,
                'staff_id': 'EMP-9',
            },
            format='json',
        )

        response = self.client.post(
            self.url,
            {
                'first_name': 'Kojo',
                'last_name': 'Mensah',
                'phone_number': '0244111333',
                'role': User.RoleChoices.STAFF,
                'staff_id': 'EMP-9',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already exists', str(response.data))

    def test_clearing_staff_id_generates_a_new_one(self):
        created = self.client.post(
            self.url,
            {
                'first_name': 'Ama',
                'last_name': 'Boateng',
                'phone_number': '0244111222',
                'role': User.RoleChoices.TEACHER,
                'staff_id': 'EMP-9',
            },
            format='json',
        )
        detail_url = reverse('user-detail', kwargs={'pk': created.data['id']})

        response = self.client.patch(detail_url, {'staff_id': ''}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['staff_id'], 'UA-S0001')
        self.assertFalse(
            SchoolMembership.objects.filter(school=self.school, staff_id='EMP-9').exists(),
        )

    def test_directory_search_matches_staff_id(self):
        self.client.post(
            self.url,
            {
                'first_name': 'Ama',
                'last_name': 'Boateng',
                'phone_number': '0244111222',
                'role': User.RoleChoices.TEACHER,
                'staff_id': 'FIND-ME',
            },
            format='json',
        )

        response = self.client.get(reverse('staff-desk-list'), {'search': 'FIND-ME'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['staff_id'], 'FIND-ME')
        self.assertEqual(response.data['results'][0]['first_name'], 'Ama')

    def test_another_school_can_use_the_same_staff_id(self):
        self.client.post(
            self.url,
            {
                'first_name': 'Ama',
                'last_name': 'Boateng',
                'phone_number': '0244111222',
                'role': User.RoleChoices.TEACHER,
                'staff_id': 'EMP-9',
            },
            format='json',
        )
        other_school = create_school(name='Other Academy', phone_number='+233240000111')
        other_admin = create_user(
            phone_number='+233240000112',
            email='other-admin@test.com',
            school=other_school,
            is_active=True,
        )
        set_client_auth_cookies(self.client, other_admin, school=other_school)

        response = self.client.post(
            self.url,
            {
                'first_name': 'Esi',
                'last_name': 'Owusu',
                'phone_number': '0244111444',
                'role': User.RoleChoices.TEACHER,
                'staff_id': 'EMP-9',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['staff_id'], 'EMP-9')
