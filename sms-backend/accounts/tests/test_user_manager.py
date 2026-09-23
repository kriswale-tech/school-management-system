from django.test import TestCase

from accounts.models import User


class UserManagerTests(TestCase):
    def test_create_superuser_uses_phone_number(self):
        user = User.objects.create_superuser(
            phone_number='+233200000099',
            password='test-pass-123',
        )

        self.assertEqual(user.phone_number, '+233200000099')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password('test-pass-123'))
