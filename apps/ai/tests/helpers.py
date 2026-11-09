import json
from datetime import date
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.ai.providers import Generation
from apps.content.models import Article
from apps.racing.models import Circuit, Driver, Race, RaceResult, Season, Team
from apps.standings.models import ConstructorStanding, DriverStanding


def article(**kwargs):
    return Article.objects.create(
        **{
            "title": "McLaren race analysis",
            "content": "McLaren improved its race pace and tyre management.",
            "status": Article.ArticleStatus.PUBLISHED,
            "published_at": timezone.now(),
            **kwargs,
        }
    )


def embedder(vector=None):
    provider = Mock()
    provider.embed.side_effect = lambda texts, **kwargs: [
        vector or [1.0, 0.0, 0.0] for _ in texts
    ]
    return provider


def dataset():
    season = Season.objects.create(year=2026, is_current=True)
    team = Team.objects.create(name="McLaren")
    ferrari = Team.objects.create(name="Ferrari")
    norris = Driver.objects.create(
        first_name="Lando", last_name="Norris", abbreviation="NOR", current_team=team
    )
    leclerc = Driver.objects.create(
        first_name="Charles",
        last_name="Leclerc",
        abbreviation="LEC",
        current_team=ferrari,
    )
    circuit = Circuit.objects.create(name="Test Circuit", country="Test")
    race = Race.objects.create(
        season=season,
        circuit=circuit,
        name="Test GP",
        round_number=1,
        race_date=date(2026, 1, 1),
        status=Race.RaceStatus.COMPLETED,
    )
    result = RaceResult.objects.create(
        race=race, driver=norris, team=team, position=1, points=25
    )
    other_result = RaceResult.objects.create(
        race=race, driver=leclerc, team=ferrari, position=2, points=18
    )
    DriverStanding.objects.create(
        season=season,
        driver=norris,
        team=team,
        position=1,
        points=25,
        wins=1,
        podiums=1,
        races_entered=1,
    )
    ConstructorStanding.objects.create(
        season=season,
        team=team,
        position=1,
        points=25,
        wins=1,
        podiums=1,
        races_entered=1,
    )
    return locals()


def function_call(name, args, call_id="call_1"):
    return Generation(
        [
            {
                "type": "function_call",
                "name": name,
                "arguments": json.dumps(args),
                "call_id": call_id,
            }
        ],
        "",
    )


def answer(text="No evidence.", ids=None, insufficient=False):
    return Generation(
        [],
        json.dumps(
            {
                "answer": text,
                "source_ids": ids or [],
                "insufficient_evidence": insufficient,
            }
        ),
    )


def user(name="analyst"):
    return get_user_model().objects.create_user(
        username=name, email=f"{name}@example.com", password="test-password"
    )
