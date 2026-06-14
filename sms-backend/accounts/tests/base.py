from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.views import AdminSignUpView, AdminVerifyOtpView

TEST_REST_FRAMEWORK = {
    **settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
}


@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
class AccountsAPITestCase(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._throttle_patches = [
            patch.object(AdminSignUpView, 'throttle_classes', []),
            patch.object(AdminVerifyOtpView, 'throttle_classes', []),
        ]
        for throttle_patch in cls._throttle_patches:
            throttle_patch.start()

    @classmethod
    def tearDownClass(cls):
        for throttle_patch in cls._throttle_patches:
            throttle_patch.stop()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        cache.clear()
