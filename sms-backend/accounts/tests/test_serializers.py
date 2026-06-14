from django.test import TestCase

from accounts.models import User
from accounts.serializers import AdminSignUpSerializer, AdminVerifyOtpSerializer
from accounts.tests.factories import PHONE, LOCAL_PHONE, create_user, signup_payload


class AdminSignUpSerializerTests(TestCase):
    def test_valid_payload_creates_inactive_user_and_school(self):
        serializer = AdminSignUpSerializer(data=signup_payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save()

        self.assertFalse(user.is_active)
        self.assertEqual(user.phone_number, PHONE)
        self.assertEqual(user.school.name, 'Test Academy')
        self.assertEqual(user.school.phone_number, PHONE)
        self.assertEqual(user.role.name, 'admin')

    def test_normalizes_local_phone_number(self):
        serializer = AdminSignUpSerializer(data=signup_payload())
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        self.assertEqual(user.phone_number, PHONE)

    def test_rejects_invalid_phone_number(self):
        serializer = AdminSignUpSerializer(
            data=signup_payload(phone_number='12345'),
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone_number', serializer.errors)

    def test_rejects_active_duplicate_phone(self):
        create_user(is_active=True)

        serializer = AdminSignUpSerializer(data=signup_payload())
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone_number', serializer.errors)

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

        user = serializer.save()

        self.assertEqual(User.objects.filter(phone_number=PHONE).count(), 1)
        self.assertEqual(user.pk, existing.pk)
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.email, 'new@test.com')
        self.assertEqual(user.school.name, 'Updated Academy')

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
