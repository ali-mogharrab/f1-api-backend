"""Revalidate cited records after generation, including publication changes mid-turn."""

from apps.racing.models import RaceResult
from apps.standings.models import ConstructorStanding, DriverStanding

from .documents import extract_article
from .retrieval import eligible_chunks


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
        if (
            model is None
            or {
                str(pk)
                for pk in model.objects.filter(pk__in=expected).values_list(
                    "pk", flat=True
                )
            }
            != expected
        ):
            return False
    return True
