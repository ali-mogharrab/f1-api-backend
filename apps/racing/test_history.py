from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.racing.models import Circuit, Driver, Race, Season, Team


class HistoricalDataTests(APITestCase):
    def setUp(self):
        self.season = Season.objects.create(year=2025)
        self.old_team = Team.objects.create(name="Previous team")
        self.new_team = Team.objects.create(name="Current team")
        self.driver = Driver.objects.create(
            first_name="Test",
            last_name="Driver",
            abbreviation="TST",
            current_team=self.new_team,
        )
        self.race = Race.objects.create(
            season=self.season,
            circuit=Circuit.objects.create(name="Test", country="Test"),
            name="Completed race",
            race_date=timezone.localdate() - timedelta(days=7),
            round_number=1,
            status=Race.RaceStatus.COMPLETED,
        )
        self.client.force_authenticate(
            get_user_model().objects.create_user(
                username="history-admin", is_staff=True
            )
        )

    def test_historical_results_can_use_the_race_time_team(self):
        for resource in ("race-result", "qualifying-result", "sprint-result"):
            with self.subTest(resource=resource):
                response = self.client.post(
                    reverse(f"racing:{resource}-list-create"),
                    {
                        "race": str(self.race.pk),
                        "driver": str(self.driver.pk),
                        "team": str(self.old_team.pk),
                        "position": 1,
                    },
                )
                self.assertEqual(response.status_code, 201, response.data)
                response = self.client.patch(
                    reverse(
                        f"racing:{resource}-detail", args=[response.data["data"]["id"]]
                    ),
                    {"position": 2},
                )
                self.assertEqual(response.status_code, 200, response.data)

    def test_historical_standings_can_use_the_season_team(self):
        response = self.client.post(
            reverse("standings:driver-standing-list-create"),
            {
                "season": str(self.season.pk),
                "driver": str(self.driver.pk),
                "team": str(self.old_team.pk),
                "position": 1,
            },
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_latest_race_excludes_an_unfinished_race_today(self):
        Race.objects.create(
            season=self.season,
            circuit=self.race.circuit,
            name="Later scheduled race",
            race_date=timezone.localdate(),
            round_number=2,
            status=Race.RaceStatus.SCHEDULED,
        )
        response = self.client.get(reverse("racing:latest-race"))
        self.assertEqual(response.data["id"], str(self.race.pk))

    def test_model_validation_is_returned_as_400(self):
        response = self.client.post(
            reverse("racing:race-result-list-create"),
            {
                "race": str(self.race.pk),
                "driver": str(self.driver.pk),
                "team": str(self.old_team.pk),
                "position": 0,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("position", response.data["errors"])
