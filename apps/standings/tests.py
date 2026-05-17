from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.racing.models import Circuit, Driver, Race, Season, Team
from apps.standings.models import ConstructorStanding, DriverStanding


class StandingsAPITests(APITestCase):
    def setUp(self):
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

        self.other_team = Team.objects.create(
            name="Ferrari",
            official_name="Scuderia Ferrari",
            country="Italy",
            base_location="Maranello, Italy",
            power_unit="Ferrari",
            first_team_entry=1950,
            world_championships=16,
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

    def test_driver_standing_list(self):
        DriverStanding.objects.create(
            season=self.season,
            driver=self.driver,
            team=self.team,
            position=1,
            points="275.00",
            wins=8,
            podiums=13,
            poles=5,
            fastest_laps=4,
            races_entered=14,
            races_finished=13,
            dnfs=1,
        )

        url = reverse("standings:driver-standing-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["driver_name"], "Max Verstappen")
        self.assertEqual(response.data["results"][0]["driver_abbreviation"], "VER")
        self.assertEqual(response.data["results"][0]["team_name"], "Red Bull Racing")

    def test_constructor_standing_list(self):
        ConstructorStanding.objects.create(
            season=self.season,
            team=self.team,
            position=1,
            points="430.00",
            wins=9,
            podiums=18,
            poles=6,
            fastest_laps=5,
            races_entered=14,
            double_podiums=4,
            double_points_finishes=12,
        )

        url = reverse("standings:constructor-standing-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["team_name"], "Red Bull Racing")
        self.assertEqual(response.data["results"][0]["points"], "430.00")

    def test_public_user_cannot_create_driver_standing(self):
        url = reverse("standings:driver-standing-list-create")
        payload = {
            "season": self.season.id,
            "driver": self.driver.id,
            "team": self.team.id,
            "position": 1,
            "points": "275.00",
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_user_can_create_driver_standing(self):
        User = get_user_model()

        admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="strong-test-password",
            is_staff=True,
        )

        self.client.force_authenticate(user=admin_user)

        url = reverse("standings:driver-standing-list-create")
        payload = {
            "season": self.season.id,
            "driver": self.driver.id,
            "team": self.team.id,
            "position": 1,
            "points": "275.00",
            "wins": 8,
            "podiums": 13,
            "poles": 5,
            "fastest_laps": 4,
            "races_entered": 14,
            "races_finished": 13,
            "dnfs": 1,
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["driver_name"], "Max Verstappen")
        self.assertEqual(response.data["data"]["position"], 1)
        self.assertEqual(DriverStanding.objects.count(), 1)

    def test_admin_user_can_create_constructor_standing(self):
        User = get_user_model()

        admin_user = User.objects.create_user(
            username="constructor-admin",
            email="constructor-admin@example.com",
            password="strong-test-password",
            is_staff=True,
        )

        self.client.force_authenticate(user=admin_user)

        url = reverse("standings:constructor-standing-list-create")
        payload = {
            "season": self.season.id,
            "team": self.team.id,
            "position": 1,
            "points": "430.00",
            "wins": 9,
            "podiums": 18,
            "poles": 6,
            "fastest_laps": 5,
            "races_entered": 14,
            "double_podiums": 4,
            "double_points_finishes": 12,
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["team_name"], "Red Bull Racing")
        self.assertEqual(response.data["data"]["points"], "430.00")
        self.assertEqual(ConstructorStanding.objects.count(), 1)

    def test_admin_cannot_create_driver_standing_with_wrong_team(self):
        User = get_user_model()

        admin_user = User.objects.create_user(
            username="standing-admin",
            email="standing-admin@example.com",
            password="strong-test-password",
            is_staff=True,
        )

        self.client.force_authenticate(user=admin_user)

        url = reverse("standings:driver-standing-list-create")
        payload = {
            "season": str(self.season.id),
            "driver": str(self.driver.id),
            "team": str(self.other_team.id),
            "position": 1,
            "points": "275.00",
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("team", response.data["errors"])

    def test_admin_cannot_create_constructor_standing_with_negative_points(self):
        User = get_user_model()

        admin_user = User.objects.create_user(
            username="constructor-validation-admin",
            email="constructor-validation-admin@example.com",
            password="strong-test-password",
            is_staff=True,
        )

        self.client.force_authenticate(user=admin_user)

        url = reverse("standings:constructor-standing-list-create")
        payload = {
            "season": str(self.season.id),
            "team": str(self.team.id),
            "position": 1,
            "points": "-10.00",
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("points", response.data["errors"])
