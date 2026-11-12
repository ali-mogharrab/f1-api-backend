import heapq
import math
import time

from django.conf import settings
from django.db import connection
from django.db.models import Case, FloatField, Prefetch, When
from pgvector.django import CosineDistance

from apps.content.models import Tag

from .documents import embedding_profile, extract_article, published_articles
from .exceptions import ProviderTimeout
from .models import ArticleChunk
from .providers import embedding_provider, validate_embeddings


def cosine_similarity(left, right):
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm = math.sqrt(sum(a * a for a in left) * sum(b * b for b in right))
    return float(dot / norm) if norm else -1.0


def eligible_chunks():
    return (
        ArticleChunk.objects.filter(
            document__profile=embedding_profile(),
            document__article_id__in=published_articles().values("id"),
        )
        .select_related(
            "document__article__related_driver",
            "document__article__related_team",
            "document__article__related_race",
            "document__article__category",
        )
        .prefetch_related(
            Prefetch("document__article__tags", queryset=Tag.objects.order_by("name"))
        )
    )


def retrieve_articles(
    query,
    *,
    team=None,
    driver=None,
    race=None,
    latest=False,
    provider=None,
    timeout=None,
):
    """Exact cosine search on both backends. No document embeddings at request time."""
    deadline = time.monotonic() + timeout if timeout is not None else None

    def remaining_time():
        if deadline is None:
            return None
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProviderTimeout()
        return remaining

    remaining_time()
    queryset = eligible_chunks()
    for key, value in {
        "related_team": team,
        "related_driver": driver,
        "related_race": race,
    }.items():
        if value:
            queryset = queryset.filter(**{f"document__article__{key}_id": value.pk})
    if not queryset.exists():
        return {
            "data": [],
            "sources": [],
            "coverage": "No indexed published articles match. Run index_articles after publishing.",
        }
    provider = provider or embedding_provider()
    vector = validate_embeddings(provider.embed([query], timeout=remaining_time()), 1)[
        0
    ]
    remaining_time()
    if connection.vendor == "postgresql":
        candidates = (
            queryset.annotate(
                # CASE keeps PostgreSQL from evaluating distance on another
                # profile's dimensions before applying the document join filter.
                distance=Case(
                    When(
                        document__profile=embedding_profile(),
                        then=CosineDistance("embedding", vector),
                    ),
                    default=None,
                    output_field=FloatField(),
                )
            )
            .filter(
                distance__lte=1 - settings.RAG_MIN_SIMILARITY,
            )
            .order_by("distance", "id")
            .iterator(chunk_size=100)
        )
        scored = ((1 - float(chunk.distance), chunk) for chunk in candidates)
    else:
        scored = (
            (cosine_similarity(vector, chunk.embedding), chunk)
            for chunk in queryset.iterator(chunk_size=100)
        )
    fingerprints = {}

    def valid_candidates():
        for score, chunk in scored:
            remaining_time()
            if score < settings.RAG_MIN_SIMILARITY:
                continue
            article = chunk.document.article
            if article.pk not in fingerprints:
                fingerprints[article.pk] = extract_article(article)[2]
            if fingerprints[article.pk] != chunk.document.fingerprint:
                continue
            yield score, chunk

    def rank(item):
        score, chunk = item
        if latest:
            return chunk.document.article.published_at.timestamp(), score, str(chunk.id)
        return score, str(chunk.id)

    best = heapq.nlargest(settings.RAG_TOP_K, valid_candidates(), key=rank)
    remaining_time()
    data, sources = [], []
    for score, chunk in best:
        article = chunk.document.article
        source_id = f"article_chunk:{chunk.id}"
        sources.append(
            {
                "id": source_id,
                "type": "article",
                "entity_id": str(article.id),
                "chunk_id": str(chunk.id),
                "title": article.title,
                "slug": article.slug,
                "url": f"/articles/{article.slug}",
                "api_url": f"/api/content/articles/{article.id}/",
                "published_at": article.published_at.isoformat(),
            }
        )
        data.append(
            {
                "source_id": source_id,
                "text": chunk.text,
                "similarity": round(score, 5),
                "metadata": chunk.metadata,
            }
        )
    return {
        "data": data,
        "sources": sources,
        "coverage": "Only indexed, unchanged published articles; no live internet. Latest ordering applies after relevance filtering.",
    }
