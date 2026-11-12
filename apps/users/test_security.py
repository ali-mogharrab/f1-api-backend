from django.contrib.auth import get_user_model
from unittest.mock import patch
from django.db import IntegrityError
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import caches
from django.test import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken


class AccountSecurityTests(APITestCase):
    def setUp(self):
        caches["ai"].clear()
        self.user = get_user_model().objects.create_user(
            username="security-user",
            email="security@example.com",
            password="Initial-secret-42!",
        )

    def test_malformed_reset_uid_is_a_validation_error(self):
        for value in ("not-a-uuid", "123", "\ufffd"):
            with self.subTest(value=value):
                response = self.client.post(
                    reverse("users:password-reset-confirm"),
                    {
                        "uid": urlsafe_base64_encode(force_bytes(value)),
                        "token": "invalid",
                        "new_password": "Replacement-secret-93!",
                        "new_password_confirm": "Replacement-secret-93!",
                    },
                )
                self.assertEqual(response.status_code, 400)

    def test_deleted_user_refresh_is_rejected_without_server_error(self):
        refresh = str(RefreshToken.for_user(self.user))
        self.user.delete()
        response = self.client.post(
            reverse("users:token-refresh"), {"refresh": refresh}
        )
        self.assertEqual(response.status_code, 401)

    @patch("apps.users.views.RegisterSerializer.save", side_effect=IntegrityError)
    def test_concurrent_registration_conflict_is_a_validation_error(self, save):
        response = self.client.post(
            reverse("users:register"),
            {
                "username": "new-user",
                "email": "new@example.com",
                "password": "Another-secret-77!",
                "password_confirm": "Another-secret-77!",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_password_reset_revokes_existing_access_and_refresh(self):
        refresh = RefreshToken.for_user(self.user)
        response = self.client.post(
            reverse("users:password-reset-confirm"),
            {
                "uid": urlsafe_base64_encode(force_bytes(self.user.pk)),
                "token": default_token_generator.make_token(self.user),
                "new_password": "Replacement-secret-93!",
                "new_password_confirm": "Replacement-secret-93!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        self.assertEqual(
            self.client.get(reverse("users:current-user")).status_code, 401
        )
        self.client.credentials()
        response = self.client.post(
            reverse("users:token-refresh"), {"refresh": str(refresh)}
        )
        self.assertEqual(response.status_code, 401)

    @override_settings(
        AUTH_THROTTLE_RATES={
            "login": "1/minute",
            "registration": "1/hour",
            "password_reset": "1/hour",
        }
    )
    def test_public_account_endpoints_are_throttled_by_ip(self):
        for endpoint, payload in (
            ("token-obtain-pair", {"username": "missing", "password": "invalid"}),
            ("register", {}),
            ("password-reset-request", {"email": "missing@example.com"}),
        ):
            with self.subTest(endpoint=endpoint):
                url = reverse(f"users:{endpoint}")
                self.assertNotEqual(self.client.post(url, payload).status_code, 429)
                response = self.client.post(url, payload)
                self.assertEqual(response.status_code, 429)
                self.assertIn("Retry-After", response)
