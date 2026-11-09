import json
from datetime import date

from django.test import TestCase

from apps.ai.tools import execute_tool, tool_definitions
from apps.racing.models import Driver, Race, RaceResult, Season

from .helpers import dataset


class ToolTests(TestCase):
    def setUp(self):
        self.data = dataset()

    def test_strict_validation_and_closed_registry(self):
        for args in [
            {"driver": "NOR", "season": 2026, "limit": "5"},
            {"driver": "NOR", "season": 2026, "limit": True},
            {"driver": "NOR", "season": 2026, "limit": 50},
            {"driver": "NOR", "season": 2026, "limit": 5, "sql": "DROP TABLE"},
            {"driver": "NOR", "limit": 5},
        ]:
            self.assertIn(
                "error", execute_tool("get_driver_recent_results", json.dumps(args))
            )
        self.assertIn("error", execute_tool("run_python", "{}"))
        self.assertIn("error", execute_tool("compare_drivers", "invalid json"))
        self.assertIn("error", execute_tool("get_driver_recent_results", "{}" * 3000))
        for definition in tool_definitions():
            schema = definition["parameters"]
            self.assertTrue(definition["strict"])
            self.assertFalse(schema["additionalProperties"])
            self.assertEqual(set(schema["required"]), set(schema["properties"]))

    def test_recent_results_and_missing_driver(self):
        result = execute_tool(
            "get_driver_recent_results",
            json.dumps({"driver": "Lando Norris", "season": 2026, "limit": 5}),
        )
        self.assertEqual(result["data"][0]["points"], "25.00")
        self.assertEqual(result["returned_races"], 1)
        self.assertEqual(result["sources"][0]["entity_id"], str(self.data["result"].pk))
        result = execute_tool(
            "get_driver_recent_results",
            json.dumps({"driver": "Unknown", "season": None, "limit": 5}),
        )
        self.assertEqual(result["data"], [])
        self.assertIn("error", result)

    def test_shared_race_window_and_missing_rows(self):
        race = Race.objects.create(
            season=self.data["season"],
            circuit=self.data["circuit"],
            name="Second GP",
            round_number=2,
            race_date=date(2026, 2, 1),
            status="completed",
        )
        RaceResult.objects.create(
            race=race,
            driver=self.data["norris"],
            team=self.data["team"],
            position=1,
            points=25,
        )
        args = {"driver_a": "NOR", "driver_b": "LEC", "season": 2026, "limit": 1}
        result = execute_tool("compare_drivers", json.dumps(args))
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["driver"], "Lando Norris")
        self.assertEqual(result["comparison"]["race_window_ids"], [str(race.pk)])

    def test_latest_completed_race_ignores_scheduled(self):
        Race.objects.create(
            season=self.data["season"],
            circuit=self.data["circuit"],
            name="Future GP",
            round_number=2,
            race_date=date(2027, 1, 1),
        )
        result = execute_tool("get_race_results", '{"race":null,"season":null}')
        self.assertEqual(result["race"]["id"], str(self.data["race"].pk))
        self.assertEqual([row["position"] for row in result["data"]], [1, 2])

    def test_standings_season_resolution_and_order_validation(self):
        result = execute_tool(
            "get_driver_standings", '{"season":2026,"driver":null,"order_by":"points"}'
        )
        self.assertEqual(result["data"][0]["points"], "25.00")
        result = execute_tool(
            "get_driver_standings", '{"season":2030,"driver":null,"order_by":"points"}'
        )
        self.assertIn("error", result)
        result = execute_tool(
            "get_driver_standings",
            '{"season":2026,"driver":null,"order_by":"password"}',
        )
        self.assertIn("error", result)
        Season.objects.create(year=2025, is_current=True)
        result = execute_tool(
            "get_constructor_standings", '{"season":null,"team":null}'
        )
        self.assertIn("Ambiguous", result["error"])

    def test_constructor_and_team_results(self):
        result = execute_tool(
            "get_constructor_standings", '{"season":2026,"team":"McLaren"}'
        )
        self.assertEqual(result["data"][0]["team"], "McLaren")
        result = execute_tool(
            "get_team_recent_results", '{"team":"McLaren","season":2026,"limit":5}'
        )
        self.assertEqual(result["returned_races"], 1)
        self.assertEqual(result["data"][0]["team_id"], str(self.data["team"].pk))

    def test_ambiguous_driver_is_not_silently_chosen(self):
        Driver.objects.create(
            first_name="Another", last_name="Norris", abbreviation="ANO"
        )
        result = execute_tool(
            "get_driver_recent_results", '{"driver":"Norris","season":null,"limit":5}'
        )
        self.assertIn("Ambiguous", result["error"])

    def test_empty_results_are_unknown(self):
        self.data["result"].delete()
        result = execute_tool(
            "get_driver_recent_results", '{"driver":"NOR","season":null,"limit":5}'
        )
        self.assertEqual(result["data"], [])
        self.assertIn("unknown", result["coverage"])
