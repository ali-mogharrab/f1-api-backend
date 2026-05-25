from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

from apps.racing.models import Circuit, Driver, Race, Season, Team
from apps.users.models import FavoriteDriver, FavoriteRace, FavoriteTeam, UserProfile


User = get_user_model()


class UsersAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ali",
            email="ali@example.com",
            first_name="Ali",
            last_name="Example",
            password="StrongPassword123!",
        )

        self.other_user = User.objects.create_user(
            username="sara",
            email="sara@example.com",
            first_name="Sara",
            last_name="Example",
            password="StrongPassword123!",
        )

        self.season = Season.objects.create(
            year=2026,
            name="2026 Formula One World Championship",
            is_current=True,
        )

        self.team = Team.objects.create(
            name="Red Bull Racing",
            official_name="Oracle Red Bull Racing",
            country="Austria",
            base_location="Milton Keynes, United Kingdom",
            power_unit="Red Bull Ford Powertrains",
            first_team_entry=2005,
            world_championships=6,
            is_active=True,
        )

        self.driver = Driver.objects.create(
            first_name="Max",
            last_name="Verstappen",
            abbreviation="VER",
            number=1,
            country="Netherlands",
            status=Driver.DriverStatus.ACTIVE,
            current_team=self.team,
        )

        self.circuit = Circuit.objects.create(
            name="Circuit de Monaco",
            country="Monaco",
            city="Monte Carlo",
            length_km="3.337",
            number_of_laps=78,
            race_distance_km="260.286",
        )

        self.race = Race.objects.create(
            season=self.season,
            circuit=self.circuit,
            name="Monaco Grand Prix",
            official_name="Formula 1 Grand Prix de Monaco 2026",
            round_number=8,
            race_date="2026-06-07",
            race_time="15:00:00",
            status=Race.RaceStatus.SCHEDULED,
        )

    def test_user_can_register(self):
        url = reverse("users:register")
        payload = {
            "username": "reza",
            "email": "reza@example.com",
            "first_name": "Reza",
            "last_name": "Example",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["username"], "reza")
        self.assertTrue(User.objects.filter(username="reza").exists())

    def test_user_cannot_register_with_mismatched_passwords(self):
        url = reverse("users:register")
        payload = {
            "username": "reza",
            "email": "reza@example.com",
            "first_name": "Reza",
            "last_name": "Example",
            "password": "StrongPassword123!",
            "password_confirm": "DifferentPassword123!",
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("password_confirm", response.data["errors"])

    def test_user_cannot_register_with_duplicate_email_case_insensitive(self):
        url = reverse("users:register")
        payload = {
            "username": "ali-two",
            "email": "ALI@EXAMPLE.COM",
            "first_name": "Ali",
            "last_name": "Duplicate",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("email", response.data["errors"])

    def test_user_can_get_token_pair(self):
        url = reverse("users:token-obtain-pair")
        payload = {
            "username": "ali",
            "password": "StrongPassword123!",
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_profile_is_created_automatically(self):
        self.assertTrue(
            UserProfile.objects.filter(user=self.user).exists()
        )

    def test_authenticated_user_can_view_current_user(self):
        self.client.force_authenticate(user=self.user)

        url = reverse("users:current-user")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["username"], "ali")
        self.assertEqual(response.data["data"]["full_name"], "Ali Example")
        self.assertIn("profile", response.data["data"])

    def test_anonymous_user_cannot_view_current_user(self):
        url = reverse("users:current-user")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_view_profile(self):
        self.client.force_authenticate(user=self.user)

        url = reverse("users:profile")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("bio", response.data["data"])
        self.assertIn("country", response.data["data"])

    def test_authenticated_user_can_update_profile(self):
        self.client.force_authenticate(user=self.user)

        url = reverse("users:profile")
        payload = {
            "bio": "Formula 1 fan and backend developer.",
            "country": "Iran",
            "favorite_driver_name": "Max Verstappen",
            "favorite_team_name": "Red Bull Racing",
        }

        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["country"], "Iran")
        self.assertEqual(
            response.data["data"]["favorite_driver_name"],
            "Max Verstappen",
        )

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.country, "Iran")

    def test_anonymous_user_cannot_view_profile(self):
        url = reverse("users:profile")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_change_password(self):
        self.client.force_authenticate(user=self.user)

        url = reverse("users:password-change")
        payload = {
            "old_password": "StrongPassword123!",
            "new_password": "NewStrongPassword123!",
            "new_password_confirm": "NewStrongPassword123!",
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPassword123!"))

    def test_user_cannot_change_password_with_wrong_old_password(self):
        self.client.force_authenticate(user=self.user)

        url = reverse("users:password-change")
        payload = {
            "old_password": "WrongPassword123!",
            "new_password": "NewStrongPassword123!",
            "new_password_confirm": "NewStrongPassword123!",
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("old_password", response.data["errors"])

    def test_user_cannot_change_password_with_mismatched_confirmation(self):
        self.client.force_authenticate(user=self.user)

        url = reverse("users:password-change")
        payload = {
            "old_password": "StrongPassword123!",
            "new_password": "NewStrongPassword123!",
            "new_password_confirm": "DifferentPassword123!",
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("new_password_confirm", response.data["errors"])

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        FRONTEND_URL="https://formula1.example",
    )
    def test_password_reset_request_sends_email_for_existing_user(self):
        url = reverse("users:password-reset-request")
        payload = {"email": "ALI@EXAMPLE.COM"}

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ali@example.com"])
        self.assertIn(
            "https://formula1.example/reset-password-confirm",
            mail.outbox[0].body,
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_request_does_not_reveal_unknown_email(self):
        url = reverse("users:password-reset-request")
        payload = {"email": "unknown@example.com"}

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(len(mail.outbox), 0)

    def test_user_can_reset_password_with_valid_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        url = reverse("users:password-reset-confirm")
        payload = {
            "uid": uid,
            "token": token,
            "new_password": "ResetStrongPassword123!",
            "new_password_confirm": "ResetStrongPassword123!",
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ResetStrongPassword123!"))

    def test_user_cannot_reuse_password_reset_token_after_successful_reset(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        url = reverse("users:password-reset-confirm")
        payload = {
            "uid": uid,
            "token": token,
            "new_password": "ResetStrongPassword123!",
            "new_password_confirm": "ResetStrongPassword123!",
        }

        first_response = self.client.post(url, payload, format="json")
        second_response = self.client.post(url, payload, format="json")

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(second_response.data["success"])
        self.assertIn("token", second_response.data["errors"])

    def test_user_cannot_reset_password_with_invalid_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        url = reverse("users:password-reset-confirm")
        payload = {
            "uid": uid,
            "token": "invalid-token",
            "new_password": "ResetStrongPassword123!",
            "new_password_confirm": "ResetStrongPassword123!",
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("token", response.data["errors"])

    def test_user_cannot_reset_password_with_mismatched_confirmation(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        url = reverse("users:password-reset-confirm")
        payload = {
            "uid": uid,
            "token": token,
            "new_password": "ResetStrongPassword123!",
            "new_password_confirm": "DifferentPassword123!",
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("new_password_confirm", response.data["errors"])

    def test_authenticated_user_can_add_favorite_driver(self):
        self.client.force_authenticate(user=self.user)

        url = reverse("users:favorite-driver-list-create")
        payload = {
            "driver": str(self.driver.id),
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["driver_name"], "Max Verstappen")
        self.assertEqual(FavoriteDriver.objects.count(), 1)
        self.assertEqual(FavoriteDriver.objects.first().user, self.user)

    def test_authenticated_user_can_list_own_favorite_drivers_only(self):
        FavoriteDriver.objects.create(
            user=self.user,
            driver=self.driver,
        )

        FavoriteDriver.objects.create(
            user=self.other_user,
            driver=self.driver,
        )

        self.client.force_authenticate(user=self.user)

        url = reverse("users:favorite-driver-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["driver_name"], "Max Verstappen")

    def test_user_cannot_add_duplicate_favorite_driver(self):
        FavoriteDriver.objects.create(
            user=self.user,
            driver=self.driver,
        )

        self.client.force_authenticate(user=self.user)

        url = reverse("users:favorite-driver-list-create")
        payload = {
            "driver": str(self.driver.id),
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("driver", response.data["errors"])
        self.assertEqual(FavoriteDriver.objects.count(), 1)

    def test_authenticated_user_can_delete_own_favorite_driver(self):
        favorite = FavoriteDriver.objects.create(
            user=self.user,
            driver=self.driver,
        )

        self.client.force_authenticate(user=self.user)

        url = reverse(
            "users:favorite-driver-detail",
            kwargs={"pk": favorite.id},
        )
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(FavoriteDriver.objects.count(), 0)

    def test_user_cannot_delete_other_users_favorite_driver(self):
        favorite = FavoriteDriver.objects.create(
            user=self.other_user,
            driver=self.driver,
        )

        self.client.force_authenticate(user=self.user)

        url = reverse(
            "users:favorite-driver-detail",
            kwargs={"pk": favorite.id},
        )
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data["success"])
        self.assertEqual(FavoriteDriver.objects.count(), 1)

    def test_authenticated_user_can_add_favorite_team(self):
        self.client.force_authenticate(user=self.user)

        url = reverse("users:favorite-team-list-create")
        payload = {
            "team": str(self.team.id),
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["team_name"], "Red Bull Racing")
        self.assertEqual(FavoriteTeam.objects.count(), 1)

    def test_authenticated_user_can_delete_own_favorite_team(self):
        favorite = FavoriteTeam.objects.create(
            user=self.user,
            team=self.team,
        )

        self.client.force_authenticate(user=self.user)

        url = reverse(
            "users:favorite-team-detail",
            kwargs={"pk": favorite.id},
        )
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(FavoriteTeam.objects.count(), 0)

    def test_authenticated_user_can_add_favorite_race(self):
        self.client.force_authenticate(user=self.user)

        url = reverse("users:favorite-race-list-create")
        payload = {
            "race": str(self.race.id),
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["race_name"], "Monaco Grand Prix")
        self.assertEqual(response.data["data"]["season_year"], 2026)
        self.assertEqual(FavoriteRace.objects.count(), 1)

    def test_authenticated_user_can_delete_own_favorite_race(self):
        favorite = FavoriteRace.objects.create(
            user=self.user,
            race=self.race,
        )

        self.client.force_authenticate(user=self.user)

        url = reverse(
            "users:favorite-race-detail",
            kwargs={"pk": favorite.id},
        )
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(FavoriteRace.objects.count(), 0)

    def test_anonymous_user_cannot_access_favorites(self):
        url = reverse("users:favorite-driver-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_add_duplicate_favorite_team(self):
        FavoriteTeam.objects.create(
            user=self.user,
            team=self.team,
        )

        self.client.force_authenticate(user=self.user)

        url = reverse("users:favorite-team-list-create")
        payload = {
            "team": str(self.team.id),
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("team", response.data["errors"])
        self.assertEqual(FavoriteTeam.objects.count(), 1)

    def test_user_cannot_add_duplicate_favorite_race(self):
        FavoriteRace.objects.create(
            user=self.user,
            race=self.race,
        )

        self.client.force_authenticate(user=self.user)

        url = reverse("users:favorite-race-list-create")
        payload = {
            "race": str(self.race.id),
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("race", response.data["errors"])
        self.assertEqual(FavoriteRace.objects.count(), 1)

    def test_authenticated_user_can_view_dashboard(self):
        FavoriteDriver.objects.create(
            user=self.user,
            driver=self.driver,
        )
        FavoriteTeam.objects.create(
            user=self.user,
            team=self.team,
        )
        FavoriteRace.objects.create(
            user=self.user,
            race=self.race,
        )

        self.client.force_authenticate(user=self.user)

        url = reverse("users:dashboard")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["user"]["username"], "ali")
        self.assertEqual(response.data["data"]["favorites_summary"]["drivers_count"], 1)
        self.assertEqual(response.data["data"]["favorites_summary"]["teams_count"], 1)
        self.assertEqual(response.data["data"]["favorites_summary"]["races_count"], 1)
        self.assertEqual(
            response.data["data"]["recent_favorite_drivers"][0]["driver_name"],
            "Max Verstappen",
        )

    def test_anonymous_user_cannot_view_dashboard(self):
        url = reverse("users:dashboard")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
