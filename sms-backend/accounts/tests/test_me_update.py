from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Profile, User
from accounts.tests.factories import create_user, set_client_auth_cookies, user_school


class MeUpdateTests(APITestCase):
    def setUp(self):
        self.url = reverse('me')
        self.user = create_user(is_active=True, email='me@test.com')
        set_client_auth_cookies(self.client, self.user)
        self.school = user_school(self.user)
        self.membership = self.user.memberships.get(school=self.school)
        self.membership.last_active_at = timezone.now()
        self.membership.save(update_fields=['last_active_at', 'updated_at'])

    def test_patch_updates_identity_and_profile(self):
        response = self.client.patch(
            self.url,
            {
                'first_name': 'Updated',
                'last_name': 'Person',
                'email': 'updated@test.com',
                'bio': 'Teacher bio',
                'gender': 'female',
                'address': 'Accra',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Updated')
        self.assertEqual(response.data['profile']['bio'], 'Teacher bio')
        self.assertIsNotNone(response.data['last_active_at'])
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'updated@test.com')

    def test_patch_rejects_login_phone_change(self):
        response = self.client.patch(
            self.url,
            {'phone_number': '+233200000099'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.phone_number, '+233200000099')

    def test_patch_rejects_role_change(self):
        response = self.client.patch(
            self.url,
            {'role': User.RoleChoices.TEACHER},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.membership.role, User.RoleChoices.ADMIN)

    def test_teacher_can_update_own_profile(self):
        teacher = create_user(
            phone_number='+233200000055',
            email='teacher-me@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
        )
        set_client_auth_cookies(self.client, teacher, school=self.school)
        Profile.objects.get_or_create(user=teacher)

        response = self.client.patch(
            self.url,
            {'first_name': 'Teach', 'last_name': 'Er'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        teacher.refresh_from_db()
        self.assertEqual(teacher.first_name, 'Teach')
