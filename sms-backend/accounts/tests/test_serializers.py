from django.test import TestCase

from accounts.models import SchoolMembership, User
from accounts.serializers import AdminSignUpSerializer, AdminVerifyOtpSerializer
from accounts.tests.factories import (
    LOCAL_PHONE,
    PHONE,
    create_user,
    get_membership,
    signup_payload,
    user_school,
)


class AdminSignUpSerializerTests(TestCase):
    def test_valid_payload_creates_inactive_user_and_school(self):
        serializer = AdminSignUpSerializer(data=signup_payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save().user

        membership = get_membership(user)
        self.assertFalse(user.is_active)
        self.assertEqual(user.phone_number, PHONE)
        self.assertEqual(membership.school.name, 'Test Academy')
        self.assertEqual(membership.school.phone_number, PHONE)
        self.assertEqual(membership.role, User.RoleChoices.ADMIN)

    def test_normalizes_local_phone_number(self):
        serializer = AdminSignUpSerializer(data=signup_payload())
        serializer.is_valid(raise_exception=True)

        user = serializer.save().user
        self.assertEqual(user.phone_number, PHONE)

    def test_rejects_invalid_phone_number(self):
        serializer = AdminSignUpSerializer(
            data=signup_payload(phone_number='12345'),
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone_number', serializer.errors)

    def test_rejects_duplicate_school_name_for_active_user(self):
        create_user(is_active=True)

        serializer = AdminSignUpSerializer(
            data=signup_payload(school_name='Test School'),
        )
        # create_user defaults the school name to "Test School"
        self.assertFalse(serializer.is_valid())
        self.assertIn('school_name', serializer.errors)

    def test_allows_active_user_to_stage_a_new_school(self):
        existing = create_user(is_active=True)

        serializer = AdminSignUpSerializer(
            data=signup_payload(school_name='Second Academy'),
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        result = serializer.save()

        self.assertEqual(result.user.pk, existing.pk)
        self.assertTrue(result.linked_existing_account)
        self.assertEqual(User.objects.filter(phone_number=PHONE).count(), 1)
        # School is created only after OTP, not at signup.
        self.assertEqual(
            SchoolMembership.objects.filter(user=existing).count(),
            1,
        )

    def test_allows_resubmit_for_inactive_user(self):
        existing = create_user(is_active=False, first_name='Old')

        serializer = AdminSignUpSerializer(
            data=signup_payload(
                school_name='Updated Academy',
                first_name='New',
                email='new@test.com',
            ),
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save().user

        self.assertEqual(User.objects.filter(phone_number=PHONE).count(), 1)
        self.assertEqual(user.pk, existing.pk)
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.email, 'new@test.com')
        self.assertEqual(user_school(user).name, 'Updated Academy')

    def test_rejects_duplicate_active_email(self):
        create_user(is_active=True, email='taken@test.com')

        serializer = AdminSignUpSerializer(
            data=signup_payload(
                phone_number='0241111111',
                email='taken@test.com',
            ),
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_allows_inactive_user_to_keep_same_email_on_resubmit(self):
        create_user(is_active=False, email='kofi@test.com')

        serializer = AdminSignUpSerializer(data=signup_payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)


class AdminVerifyOtpSerializerTests(TestCase):
    def test_valid_payload_passes(self):
        serializer = AdminVerifyOtpSerializer(data={
            'phone_number': LOCAL_PHONE,
            'otp': '123456',
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['phone_number'], PHONE)

    def test_rejects_invalid_phone_number(self):
        serializer = AdminVerifyOtpSerializer(data={
            'phone_number': 'invalid',
            'otp': '123456',
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone_number', serializer.errors)
