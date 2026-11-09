"""Closed read-only tool registry. All arguments validated before ORM access."""

import json
from typing import Literal
from uuid import UUID

from django.db.models import F, Q, Value
from django.db.models.functions import Concat
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from apps.racing.models import Driver, Race, RaceResult, Season, Team
from apps.standings.models import ConstructorStanding, DriverStanding

from .exceptions import ToolInputError
from .retrieval import retrieve_articles


class Arguments(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class RecentResultsArgs(Arguments):
    driver: str = Field(
        min_length=1,
        max_length=150,
        description="Driver UUID, full name, unique surname or abbreviation.",
    )
    season: int | None = Field(
        ge=1950,
        le=2100,
        description="Season year; null means all locally available seasons.",
    )
    limit: int = Field(
        ge=1, le=10, description="Maximum recent completed race results."
    )


class CompareDriversArgs(Arguments):
    driver_a: str = Field(min_length=1, max_length=150)
    driver_b: str = Field(min_length=1, max_length=150)
    season: int | None = Field(ge=1950, le=2100)
    limit: int = Field(ge=1, le=10)


class RaceResultsArgs(Arguments):
    race: str | None = Field(
        min_length=1,
        max_length=150,
        description="Race UUID or exact name. Null selects the latest completed race in the chosen scope.",
    )
    season: int | None = Field(ge=1950, le=2100)


class DriverStandingsArgs(Arguments):
    season: int | None = Field(
        ge=1950,
        le=2100,
        description="Year; null requires one unambiguous current season.",
    )
    driver: str | None = Field(min_length=1, max_length=150)
    order_by: Literal["position", "points", "podiums", "wins"]


class ConstructorStandingsArgs(Arguments):
    season: int | None = Field(ge=1950, le=2100)
    team: str | None = Field(min_length=1, max_length=150)


class TeamResultsArgs(Arguments):
    team: str = Field(min_length=1, max_length=150)
    season: int | None = Field(ge=1950, le=2100)
    limit: int = Field(
        ge=1,
        le=10,
        description="Number of recent races, including all locally recorded team drivers.",
    )


class SearchArticlesArgs(Arguments):
    query: str = Field(
        min_length=1,
        max_length=1000,
        description="Semantic retrieval query; include topic and time context.",
    )
    team: str | None = Field(min_length=1, max_length=150)
    driver: str | None = Field(min_length=1, max_length=150)
    race: str | None = Field(
        min_length=1,
        max_length=150,
        description="Exact race name or UUID; names must be unambiguous across seasons.",
    )
    latest: bool = Field(
        description="Order relevant chunks by publication date for latest news questions."
    )


def _one(queryset, label):
    rows = list(queryset[:2])
    if not rows:
        raise ToolInputError(f"No {label} is available in the local database.")
    if len(rows) > 1:
        raise ToolInputError(
            f"Ambiguous {label}. Ask for a full name, UUID, or season."
        )
    return rows[0]


def resolve_entity(model, value):
    value = value.strip()
    try:
        return _one(model.objects.filter(pk=UUID(value)), model.__name__.lower())
    except ValueError:
        pass
    if model is Driver:
        query = model.objects.annotate(
            full=Concat("first_name", Value(" "), "last_name")
        ).filter(
            Q(full__iexact=value)
            | Q(abbreviation__iexact=value)
            | Q(last_name__iexact=value),
        )
    elif model in (Team, Race):
        query = model.objects.filter(
            Q(name__iexact=value) | Q(official_name__iexact=value)
        )
    else:
        raise ToolInputError("Unsupported entity type.")
    return _one(query, model.__name__.lower())


def resolve_season(year):
    return _one(
        Season.objects.filter(year=year)
        if year is not None
        else Season.objects.filter(is_current=True),
        "season",
    )


def source(record, kind, title, path):
    return {
        "id": f"{kind}:{record.pk}",
        "type": kind,
        "entity_id": str(record.pk),
        "title": title,
        "api_url": f"/api/{path}/{record.pk}/",
    }


def results_payload(rows):
    rows = list(rows)
    return {
        "data": [
            {
                "source_id": f"race_result:{r.pk}",
                "race_id": str(r.race_id),
                "race": r.race.name,
                "season": r.race.season.year,
                "date": r.race.race_date.isoformat(),
                "driver_id": str(r.driver_id),
                "driver": r.driver.full_name,
                "team_id": str(r.team_id),
                "team": r.team.name,
                "position": r.position,
                "points": str(r.points),
                "status": r.status,
                "updated_at": r.updated_at.isoformat(),
            }
            for r in rows
        ],
        "sources": [
            source(
                r,
                "race_result",
                f"{r.driver.full_name} — {r.race.name}",
                "racing/race-results",
            )
            for r in rows
        ],
        "coverage": "Only stored results for completed races. Missing rows are unknown, not zero. Race points exclude sprint points; this is not a complete career or season dataset.",
    }


def result_queryset(season):
    query = RaceResult.objects.filter(
        race__status=Race.RaceStatus.COMPLETED
    ).select_related("race__season", "driver", "team")
    if season is not None:
        query = query.filter(race__season=resolve_season(season))
    return query


def get_driver_recent_results(args, **kwargs):
    driver = resolve_entity(Driver, args.driver)
    query = (
        result_queryset(args.season)
        .filter(driver=driver)
        .order_by("-race__race_date", "-race__round_number", "id")
    )
    result = results_payload(query[: args.limit])
    result.update(
        requested_races=args.limit,
        returned_races=len(result["data"]),
        driver=driver.full_name,
    )
    return result


def compare_drivers(args, **kwargs):
    a = resolve_entity(Driver, args.driver_a)
    b = resolve_entity(Driver, args.driver_b)
    if a.pk == b.pk:
        raise ToolInputError("Choose two different drivers.")
    # Shared race window makes comparison fair; absent rows stay absent.
    query = result_queryset(args.season).filter(driver__in=[a, b])
    races = list(
        query.order_by("-race__race_date", "-race__round_number")
        .values_list("race_id", flat=True)
        .distinct()[: args.limit]
    )
    result = results_payload(
        query.filter(race_id__in=races).order_by("-race__race_date", "driver_id")
    )
    result["comparison"] = {
        "driver_a": a.full_name,
        "driver_b": b.full_name,
        "race_window_ids": [str(pk) for pk in races],
        "requested_races": args.limit,
    }
    return result


def get_race_results(args, **kwargs):
    query = Race.objects.filter(status=Race.RaceStatus.COMPLETED).select_related(
        "season"
    )
    if args.season is not None:
        query = query.filter(season=resolve_season(args.season))
    if args.race is None:
        race = query.order_by("-race_date", "-round_number", "id").first()
        if race is None:
            raise ToolInputError("No completed race is available in the chosen scope.")
    else:
        try:
            query = query.filter(pk=UUID(args.race))
        except ValueError:
            query = query.filter(
                Q(name__iexact=args.race.strip())
                | Q(official_name__iexact=args.race.strip())
            )
        race = _one(query, "completed race")
    result = results_payload(
        result_queryset(args.season)
        .filter(race=race)
        .order_by(F("position").asc(nulls_last=True), "id")[:100]
    )
    result["race"] = {
        "id": str(race.pk),
        "name": race.name,
        "date": race.race_date.isoformat(),
        "season": race.season.year,
    }
    return result


def get_team_recent_results(args, **kwargs):
    team = resolve_entity(Team, args.team)
    query = result_queryset(args.season).filter(team=team)
    races = list(
        query.order_by("-race__race_date", "-race__round_number")
        .values_list("race_id", flat=True)
        .distinct()[: args.limit]
    )
    result = results_payload(
        query.filter(race_id__in=races).order_by("-race__race_date", "driver_id")[:100]
    )
    result.update(team=team.name, requested_races=args.limit, returned_races=len(races))
    return result


def get_driver_standings(args, **kwargs):
    season = resolve_season(args.season)
    query = DriverStanding.objects.filter(season=season).select_related(
        "driver", "team"
    )
    if args.driver:
        query = query.filter(driver=resolve_entity(Driver, args.driver))
    ordering = args.order_by if args.order_by == "position" else f"-{args.order_by}"
    rows = list(query.order_by(ordering, "position", "id")[:100])
    return {
        "data": [
            {
                "source_id": f"driver_standing:{r.pk}",
                "driver_id": str(r.driver_id),
                "driver": r.driver.full_name,
                "team": r.team.name if r.team else None,
                "season": season.year,
                "position": r.position,
                "points": str(r.points),
                "wins": r.wins,
                "podiums": r.podiums,
                "races_entered": r.races_entered,
                "updated_at": r.updated_at.isoformat(),
            }
            for r in rows
        ],
        "sources": [
            source(
                r,
                "driver_standing",
                f"{season.year} {r.driver.full_name} standings",
                "standings/drivers",
            )
            for r in rows
        ],
        "coverage": f"Stored {season.year} championship snapshot; completeness and freshness are not guaranteed. Podiums refer only to this season.",
    }


def get_constructor_standings(args, **kwargs):
    season = resolve_season(args.season)
    query = ConstructorStanding.objects.filter(season=season).select_related("team")
    if args.team:
        query = query.filter(team=resolve_entity(Team, args.team))
    rows = list(query.order_by("position", "id")[:100])
    return {
        "data": [
            {
                "source_id": f"constructor_standing:{r.pk}",
                "team_id": str(r.team_id),
                "team": r.team.name,
                "season": season.year,
                "position": r.position,
                "points": str(r.points),
                "wins": r.wins,
                "podiums": r.podiums,
                "races_entered": r.races_entered,
                "updated_at": r.updated_at.isoformat(),
            }
            for r in rows
        ],
        "sources": [
            source(
                r,
                "constructor_standing",
                f"{season.year} {r.team.name} standings",
                "standings/constructors",
            )
            for r in rows
        ],
        "coverage": f"Stored {season.year} championship snapshot; completeness and freshness are not guaranteed.",
    }


def search_articles(args, *, timeout=None):
    return retrieve_articles(
        args.query,
        team=resolve_entity(Team, args.team) if args.team else None,
        driver=resolve_entity(Driver, args.driver) if args.driver else None,
        race=resolve_entity(Race, args.race) if args.race else None,
        latest=args.latest,
        timeout=timeout,
    )


REGISTRY = {
    "get_driver_recent_results": (
        RecentResultsArgs,
        get_driver_recent_results,
        "Recent stored results for a driver; scope may span seasons.",
    ),
    "compare_drivers": (
        CompareDriversArgs,
        compare_drivers,
        "Compare two drivers in a shared recent race window; missing rows remain unknown.",
    ),
    "get_race_results": (
        RaceResultsArgs,
        get_race_results,
        "Stored results from one completed race, optionally the latest locally completed race.",
    ),
    "get_driver_standings": (
        DriverStandingsArgs,
        get_driver_standings,
        "Stored season driver standings, sortable by points, podiums, wins or position.",
    ),
    "get_constructor_standings": (
        ConstructorStandingsArgs,
        get_constructor_standings,
        "Stored constructor championship standings for a season.",
    ),
    "get_team_recent_results": (
        TeamResultsArgs,
        get_team_recent_results,
        "Recent results for all locally recorded drivers of a team, using result-time team membership.",
    ),
    "search_articles": (
        SearchArticlesArgs,
        search_articles,
        "Semantic search over indexed published site articles. Use for reports/commentary, and alongside data tools for hybrid analysis. Entity filters match explicit article relationships only; null searches all articles.",
    ),
}


def tool_definitions():
    return [
        {
            "type": "function",
            "name": name,
            "description": description,
            "strict": True,
            "parameters": schema.model_json_schema(),
        }
        for name, (schema, _, description) in REGISTRY.items()
    ]


def execute_tool(name, arguments, *, timeout=None):
    if name not in REGISTRY:
        return {"data": [], "sources": [], "error": "Unknown read-only tool."}
    schema, function, _ = REGISTRY[name]
    try:
        if len(arguments) > 5000:
            raise ToolInputError("Tool arguments exceed the size limit.")
        payload = json.loads(arguments)
        args = schema.model_validate(payload)
        return function(args, timeout=timeout)
    except (json.JSONDecodeError, ValidationError):
        return {
            "data": [],
            "sources": [],
            "error": "Invalid tool arguments; use the declared schema and strict types.",
        }
    except ToolInputError as exc:
        return {"data": [], "sources": [], "error": str(exc)}
