from django.urls import reverse
from rest_framework import status

from accounts.models import PhoneOtp, User
from accounts.tests.base import AccountsAPITestCase
from accounts.tests.factories import PHONE, create_user, set_client_auth_cookies


TEACHER_PHONE = '+233244567891'
TEACHER_LOCAL_PHONE = '0244567891'
NEW_TEACHER_PHONE = '+233244567892'
NEW_TEACHER_LOCAL_PHONE = '0244567892'


class UpdateUserPhoneDuringSetupTests(AccountsAPITestCase):
    def setUp(self):
        self.admin = create_user(is_active=True)
        self.teacher = create_user(
            phone_number=TEACHER_PHONE,
            email='teacher@test.com',
            school=self.admin.school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
            first_name='Ama',
            last_name='Boateng',
        )
        set_client_auth_cookies(self.client, self.admin)
        self.url = reverse('user-detail', kwargs={'pk': self.teacher.id})

    def test_admin_can_change_phone_during_setup(self):
        PhoneOtp.objects.create(
            phone_number=TEACHER_PHONE,
            purpose=PhoneOtp.Purpose.LOGIN,
            otp='123456',
            expires_at=PhoneOtp.default_expires_at(),
            sent_at=PhoneOtp.default_expires_at(),
        )

        response = self.client.patch(
            self.url,
            {'phone_number': NEW_TEACHER_LOCAL_PHONE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone_number'], NEW_TEACHER_PHONE)
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.phone_number, NEW_TEACHER_PHONE)
        self.assertFalse(
            PhoneOtp.objects.filter(phone_number=TEACHER_PHONE).exists(),
        )

    def test_admin_cannot_change_phone_after_setup_completed(self):
        school = self.admin.school
        school.setup_completed = True
        school.save(update_fields=['setup_completed', 'updated_at'])

        response = self.client.patch(
            self.url,
            {'phone_number': NEW_TEACHER_LOCAL_PHONE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.phone_number, TEACHER_PHONE)

    def test_staff_cannot_change_phone_during_setup(self):
        staff = create_user(
            phone_number='+233244567893',
            email='staff@test.com',
            school=self.admin.school,
            role=User.RoleChoices.STAFF,
            is_active=True,
        )
        set_client_auth_cookies(self.client, staff)

        response = self.client.patch(
            self.url,
            {'phone_number': NEW_TEACHER_LOCAL_PHONE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.phone_number, TEACHER_PHONE)

    def test_admin_phone_change_updates_school_phone_when_it_matches(self):
        response = self.client.patch(
            reverse('user-detail', kwargs={'pk': self.admin.id}),
            {'phone_number': '+233244567899'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin.school.refresh_from_db()
        self.assertEqual(self.admin.school.phone_number, '+233244567899')
