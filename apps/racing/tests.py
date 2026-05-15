import uuid
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from apps.racing.models import (
    Circuit,
    Driver,
    QualifyingResult,
    Race,
    RaceResult,
    Season,
    SprintResult,
    Team,
)

class RacingAPITests(APITestCase):
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

    def test_season_list(self):
        url = reverse("racing:season-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["year"], 2026)

    def test_team_list(self):
        url = reverse("racing:team-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Red Bull Racing")

    def test_driver_detail(self):
        url = reverse(
            "racing:driver-detail",
            kwargs={"pk": self.driver.pk},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Max Verstappen")
        self.assertEqual(response.data["current_team_name"], "Red Bull Racing")

    def test_circuit_list_filter_by_country(self):
        url = reverse("racing:circuit-list-create")
        response = self.client.get(url, {"country": "Monaco"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Circuit de Monaco")

    def test_race_detail(self):
        url = reverse(
            "racing:race-detail",
            kwargs={"pk": self.race.pk},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Monaco Grand Prix")
        self.assertEqual(response.data["season_year"], 2026)
        self.assertEqual(response.data["circuit_name"], "Circuit de Monaco")

    def test_public_user_can_read_seasons(self):
        url = reverse("racing:season-list-create")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_public_user_cannot_create_season(self):
        url = reverse("racing:season-list-create")
        payload = {
            "year": 2027,
            "name": "2027 Formula One World Championship",
            "is_current": False,
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_user_can_create_season(self):
        User = get_user_model()

        admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="strong-test-password",
            is_staff=True,
        )

        self.client.force_authenticate(user=admin_user)

        url = reverse("racing:season-list-create")
        payload = {
            "year": 2027,
            "name": "2027 Formula One World Championship",
            "is_current": False,
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Season created successfully.")
        self.assertEqual(response.data["data"]["year"], 2027)
        self.assertEqual(Season.objects.count(), 2)

    def test_admin_user_gets_structured_validation_error(self):
        User = get_user_model()

        admin_user = User.objects.create_user(
            username="admin-validation",
            email="admin-validation@example.com",
            password="strong-test-password",
            is_staff=True,
        )

        self.client.force_authenticate(user=admin_user)

        url = reverse("racing:season-list-create")
        payload = {}

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], "Validation error.")
        self.assertIn("year", response.data["errors"])

    def test_detail_not_found_returns_structured_error(self):
        random_id = uuid.uuid4()

        url = reverse(
            "racing:season-detail",
            kwargs={"pk": random_id},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data["success"])
        self.assertIn("message", response.data)
        self.assertIn("errors", response.data)

    def test_race_result_list(self):
        RaceResult.objects.create(
            race=self.race,
            driver=self.driver,
            team=self.team,
            position=1,
            classified_position="1",
            grid_position=1,
            laps_completed=78,
            points="25.00",
            status=RaceResult.ResultStatus.CLASSIFIED,
        )

        url = reverse("racing:race-result-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["driver_name"], "Max Verstappen")
        self.assertEqual(response.data["results"][0]["team_name"], "Red Bull Racing")


    def test_qualifying_result_list(self):
        QualifyingResult.objects.create(
            race=self.race,
            driver=self.driver,
            team=self.team,
            position=1,
            q1_time="1:11.456",
            q2_time="1:10.982",
            q3_time="1:10.270",
            laps_completed=18,
        )

        url = reverse("racing:qualifying-result-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["position"], 1)
        self.assertEqual(response.data["results"][0]["driver_abbreviation"], "VER")


    def test_sprint_result_list(self):
        SprintResult.objects.create(
            race=self.race,
            driver=self.driver,
            team=self.team,
            position=1,
            grid_position=1,
            laps_completed=19,
            points="8.00",
            status=SprintResult.SprintStatus.CLASSIFIED,
        )

        url = reverse("racing:sprint-result-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["points"], "8.00")
        self.assertEqual(response.data["results"][0]["race_name"], "Monaco Grand Prix")
