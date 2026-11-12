import hashlib
import json

from apps.racing.models import RaceResult
from apps.standings.models import ConstructorStanding, DriverStanding

from .documents import extract_article
from .retrieval import eligible_chunks


def structured_fingerprint(record):
    """Snapshot facts and related labels, including changes made by bulk updates."""
    values = {
        field.attname: getattr(record, field.attname)
        for field in record._meta.concrete_fields
    }
    values["team_name"] = record.team.name if record.team else None
    if isinstance(record, (RaceResult, DriverStanding)):
        values["driver_name"] = record.driver.full_name
    if isinstance(record, RaceResult):
        values["race"] = {
            "name": record.race.name,
            "date": record.race.race_date,
            "status": record.race.status,
            "season": record.race.season.year,
        }
    else:
        values["season"] = record.season.year
    return hashlib.sha256(
        json.dumps(values, sort_keys=True, default=str).encode()
    ).hexdigest()


def sources_still_valid(sources):
    by_type = {}
    for source in sources:
        by_type.setdefault(source["type"], []).append(source)
    article_sources = by_type.pop("article", [])
    if article_sources:
        expected = {src["chunk_id"] for src in article_sources}
        chunks = list(eligible_chunks().filter(pk__in=expected))
        if {str(chunk.pk) for chunk in chunks} != expected:
            return False
        if any(
            extract_article(chunk.document.article)[2] != chunk.document.fingerprint
            for chunk in chunks
        ):
            return False
    models = {
        "race_result": RaceResult,
        "driver_standing": DriverStanding,
        "constructor_standing": ConstructorStanding,
    }
    for kind, records in by_type.items():
        model = models.get(kind)
        expected = {src["entity_id"] for src in records}
        if model is None:
            return False
        related = {
            "race_result": ("race__season", "driver", "team"),
            "driver_standing": ("season", "driver", "team"),
            "constructor_standing": ("season", "team"),
        }[kind]
        current = {
            str(row.pk): structured_fingerprint(row)
            for row in model.objects.filter(pk__in=expected).select_related(*related)
        }
        if set(current) != expected or any(
            current[src["entity_id"]] != src.get("_fingerprint") for src in records
        ):
            return False
    return True
