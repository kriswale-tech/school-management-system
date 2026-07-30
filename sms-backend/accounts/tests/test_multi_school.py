from django.urls import reverse
from rest_framework import status

from accounts.models import SchoolMembership, User
from accounts.tests.base import AccountsAPITestCase
from accounts.tests.factories import (
    LOCAL_PHONE,
    PHONE,
    create_membership,
    create_phone_otp,
    create_school,
    create_user,
    get_membership,
    set_client_auth_cookies,
    user_school,
)
from accounts.models import PhoneOtp

SECOND_PHONE = '+233244567891'
SECOND_LOCAL_PHONE = '0244567891'
THIRD_PHONE = '+233244567892'
THIRD_LOCAL_PHONE = '0244567892'


class LoginSchoolSelectionTests(AccountsAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = create_user(is_active=True)
        self.first_school = user_school(self.user)
        self.login_verify_url = reverse('login-verify-otp')
        self.select_url = reverse('select-school')
        self.me_url = reverse('me')

    def _login(self):
        create_phone_otp(purpose=PhoneOtp.Purpose.LOGIN)
        return self.client.post(
            self.login_verify_url,
            {'phone_number': LOCAL_PHONE, 'otp': '123456'},
            format='json',
        )

    def test_single_school_user_is_scoped_without_selecting(self):
        response = self._login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['requires_school_selection'])
        self.assertEqual(
            response.data['active_school']['school_id'],
            str(self.first_school.id),
        )
        self.assertEqual(len(response.data['schools']), 1)

    def test_single_school_user_can_use_school_endpoints_immediately(self):
        self._login()

        response = self.client.get(reverse('school'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_multi_school_user_must_select_a_school(self):
        create_membership(self.user, create_school(name='Second School'))

        response = self._login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['requires_school_selection'])
        self.assertIsNone(response.data['active_school'])
        self.assertEqual(len(response.data['schools']), 2)

    def test_unscoped_session_cannot_reach_school_data(self):
        create_membership(self.user, create_school(name='Second School'))
        self._login()

        response = self.client.get(reverse('school'))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unscoped_session_can_still_read_me(self):
        create_membership(self.user, create_school(name='Second School'))
        self._login()

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['requires_school_selection'])
        self.assertIsNone(response.data['school_id'])
        self.assertIsNone(response.data['role'])
        self.assertEqual(len(response.data['schools']), 2)

    def test_selecting_a_school_scopes_the_session(self):
        second_school = create_school(name='Second School')
        create_membership(self.user, second_school, role=User.RoleChoices.TEACHER)
        self._login()

        response = self.client.post(
            self.select_url,
            {'school_id': str(second_school.id)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['requires_school_selection'])
        self.assertEqual(
            response.data['active_school']['school_id'],
            str(second_school.id),
        )

        me = self.client.get(self.me_url)
        self.assertEqual(me.data['school_id'], str(second_school.id))
        self.assertEqual(me.data['role'], User.RoleChoices.TEACHER)

    def test_selecting_a_school_records_last_active_at(self):
        self._login()
        membership = get_membership(self.user, self.first_school)

        self.assertIsNotNone(membership.last_active_at)

    def test_cannot_select_a_school_without_membership(self):
        other_school = create_school(name='Someone Elses School')
        self._login()

        response = self.client.post(
            self.select_url,
            {'school_id': str(other_school.id)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_is_refused_without_any_school_access(self):
        get_membership(self.user, self.first_school).delete()

        response = self._login()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_revoked_membership_loses_access_on_next_request(self):
        self._login()
        membership = get_membership(self.user, self.first_school)
        membership.is_active = False
        membership.save(update_fields=['is_active'])

        response = self.client.get(reverse('school'))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SwitchSchoolIsolationTests(AccountsAPITestCase):
    def setUp(self):
        super().setUp()
        self.admin = create_user(is_active=True)
        self.school_a = user_school(self.admin)
        self.school_b = create_school(name='School B')
        create_membership(self.admin, self.school_b)

        create_user(
            phone_number=SECOND_PHONE,
            email='a-teacher@test.com',
            school=self.school_a,
            role=User.RoleChoices.TEACHER,
            is_active=True,
            first_name='Ama',
        )
        create_user(
            phone_number=THIRD_PHONE,
            email='b-teacher@test.com',
            school=self.school_b,
            role=User.RoleChoices.TEACHER,
            is_active=True,
            first_name='Kojo',
        )
        self.user_list_url = reverse('user-list')

    def test_user_list_only_shows_the_selected_school(self):
        set_client_auth_cookies(self.client, self.admin, school=self.school_a)

        response = self.client.get(self.user_list_url)

        names = {item['first_name'] for item in response.data['results']}
        self.assertIn('Ama', names)
        self.assertNotIn('Kojo', names)

    def test_switching_school_changes_visible_users(self):
        set_client_auth_cookies(self.client, self.admin, school=self.school_a)

        self.client.post(
            reverse('select-school'),
            {'school_id': str(self.school_b.id)},
            format='json',
        )
        response = self.client.get(self.user_list_url)

        names = {item['first_name'] for item in response.data['results']}
        self.assertIn('Kojo', names)
        self.assertNotIn('Ama', names)

    def test_cannot_open_a_user_from_another_school(self):
        set_client_auth_cookies(self.client, self.admin, school=self.school_a)
        other_teacher = User.objects.get(phone_number=THIRD_PHONE)

        response = self.client.get(
            reverse('user-detail', kwargs={'pk': other_teacher.id}),
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AddExistingPersonToSchoolTests(AccountsAPITestCase):
    def setUp(self):
        super().setUp()
        self.admin = create_user(is_active=True)
        self.school = user_school(self.admin)
        set_client_auth_cookies(self.client, self.admin, school=self.school)
        self.url = reverse('user-list')

        self.other_school = create_school(name='Other School')
        self.existing = create_user(
            phone_number=SECOND_PHONE,
            email='ama@test.com',
            school=self.other_school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
            first_name='Ama',
            last_name='Boateng',
        )

    def test_adding_a_known_phone_reuses_the_identity(self):
        response = self.client.post(
            self.url,
            {
                'first_name': 'Typo',
                'last_name': 'Name',
                'phone_number': SECOND_LOCAL_PHONE,
                'role': User.RoleChoices.TEACHER,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.filter(phone_number=SECOND_PHONE).count(), 1)
        self.assertEqual(response.data['id'], str(self.existing.id))
        # The person's own name stays authoritative across schools.
        self.assertEqual(response.data['first_name'], 'Ama')
        self.assertEqual(
            SchoolMembership.objects.filter(user=self.existing).count(),
            2,
        )

    def test_person_can_hold_different_roles_in_each_school(self):
        self.client.post(
            self.url,
            {
                'first_name': 'Ama',
                'last_name': 'Boateng',
                'phone_number': SECOND_LOCAL_PHONE,
                'role': User.RoleChoices.ACCOUNTANT,
            },
            format='json',
        )

        self.assertEqual(
            get_membership(self.existing, self.school).role,
            User.RoleChoices.ACCOUNTANT,
        )
        self.assertEqual(
            get_membership(self.existing, self.other_school).role,
            User.RoleChoices.TEACHER,
        )

    def test_adding_someone_already_in_this_school_is_rejected(self):
        create_membership(self.existing, self.school, role=User.RoleChoices.TEACHER)

        response = self.client.post(
            self.url,
            {
                'first_name': 'Ama',
                'last_name': 'Boateng',
                'phone_number': SECOND_LOCAL_PHONE,
                'role': User.RoleChoices.TEACHER,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_removing_a_member_keeps_their_other_school_access(self):
        create_membership(self.existing, self.school, role=User.RoleChoices.TEACHER)

        response = self.client.delete(
            reverse('user-detail', kwargs={'pk': self.existing.id}),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.filter(pk=self.existing.pk).exists())
        self.assertIsNone(get_membership(self.existing, self.school))
        self.assertIsNotNone(get_membership(self.existing, self.other_school))


class PhoneCorrectionDuringSetupTests(AccountsAPITestCase):
    def setUp(self):
        super().setUp()
        self.admin = create_user(is_active=True)
        self.school = user_school(self.admin)
        set_client_auth_cookies(self.client, self.admin, school=self.school)
        self.teacher = create_user(
            phone_number=SECOND_PHONE,
            email='typo@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
            first_name='Typo',
            last_name='Teacher',
        )
        self.url = reverse('user-detail', kwargs={'pk': self.teacher.id})

    def test_corrected_number_updates_identity_in_place(self):
        response = self.client.patch(
            self.url,
            {'phone_number': THIRD_LOCAL_PHONE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['linked_existing_user'])
        self.assertEqual(response.data['user']['id'], str(self.teacher.id))
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.phone_number, THIRD_PHONE)

    def test_corrected_number_links_a_person_from_another_school(self):
        other_school = create_school(name='Other School')
        existing = create_user(
            phone_number=THIRD_PHONE,
            email='ama@test.com',
            school=other_school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
            first_name='Ama',
            last_name='Boateng',
        )

        response = self.client.patch(
            self.url,
            {'phone_number': THIRD_LOCAL_PHONE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['linked_existing_user'])
        self.assertEqual(response.data['user']['id'], str(existing.id))
        self.assertEqual(response.data['user']['first_name'], 'Ama')
        self.assertIsNotNone(get_membership(existing, self.school))
        # The mistakenly created person is cleaned up.
        self.assertFalse(User.objects.filter(pk=self.teacher.pk).exists())

    def test_splitting_a_shared_identity_leaves_other_schools_alone(self):
        other_school = create_school(name='Other School')
        create_membership(
            self.teacher,
            other_school,
            role=User.RoleChoices.TEACHER,
        )

        response = self.client.patch(
            self.url,
            {'phone_number': THIRD_LOCAL_PHONE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.teacher.refresh_from_db()
        # The shared login is untouched; this school gets a separate identity.
        self.assertEqual(self.teacher.phone_number, SECOND_PHONE)
        self.assertEqual(
            User.objects.get(phone_number=THIRD_PHONE).first_name,
            'Typo',
        )
        self.assertIsNotNone(get_membership(self.teacher, other_school))
        self.assertIsNone(get_membership(self.teacher, self.school))

    def test_cannot_correct_onto_someone_already_in_this_school(self):
        create_user(
            phone_number=THIRD_PHONE,
            email='ama@test.com',
            school=self.school,
            role=User.RoleChoices.TEACHER,
            is_active=True,
        )

        response = self.client.patch(
            self.url,
            {'phone_number': THIRD_LOCAL_PHONE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CreateAdditionalSchoolTests(AccountsAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = create_user(is_active=True)
        self.first_school = user_school(self.user)
        set_client_auth_cookies(self.client, self.user, school=self.first_school)
        self.url = reverse('create-school')

    def test_existing_user_can_start_another_school(self):
        response = self.client.post(
            self.url,
            {'school_name': 'Second Academy'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['school_name'], 'Second Academy')
        self.assertEqual(response.data['role'], User.RoleChoices.ADMIN)
        self.assertEqual(SchoolMembership.objects.filter(user=self.user).count(), 2)

    def test_cannot_create_school_with_same_name(self):
        response = self.client.post(
            self.url,
            {'school_name': self.first_school.name},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_create_school_with_same_name_ignoring_case_and_spaces(self):
        response = self.client.post(
            self.url,
            {'school_name': f'  {self.first_school.name.upper()}  '},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_lets_existing_users_create_another_school(self):
        response = self.client.post(
            reverse('admin-signup'),
            {
                'school_name': 'Another Academy',
                'first_name': 'Kofi',
                'last_name': 'Mensah',
                'phone_number': LOCAL_PHONE,
                'email': 'kofi@test.com',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['linked_existing_account'])
        self.assertEqual(User.objects.filter(phone_number=PHONE).count(), 1)
        # Still only one membership until OTP verify.
        self.assertEqual(SchoolMembership.objects.filter(user=self.user).count(), 1)

        phone_otp = PhoneOtp.objects.get(
            phone_number=PHONE,
            purpose=PhoneOtp.Purpose.SIGNUP,
        )
        verify = self.client.post(
            reverse('admin-verify-otp'),
            {'phone_number': LOCAL_PHONE, 'otp': phone_otp.otp},
            format='json',
        )

        self.assertEqual(verify.status_code, status.HTTP_200_OK)
        self.assertTrue(verify.data['linked_existing_account'])
        self.assertFalse(verify.data['requires_school_selection'])
        self.assertEqual(
            verify.data['active_school']['school_name'],
            'Another Academy',
        )
        self.assertEqual(SchoolMembership.objects.filter(user=self.user).count(), 2)

    def test_signup_rejects_same_admin_school_name(self):
        response = self.client.post(
            reverse('admin-signup'),
            {
                'school_name': self.first_school.name,
                'first_name': 'Kofi',
                'last_name': 'Mensah',
                'phone_number': LOCAL_PHONE,
                'email': 'kofi@test.com',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
