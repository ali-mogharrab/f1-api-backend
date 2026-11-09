"""Versioned, deterministic extraction shared by indexing and stale-evidence checks."""

import hashlib
import html
import json
import re
import unicodedata
from html.parser import HTMLParser

from django.conf import settings
from django.utils import timezone

from apps.content.models import Article


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        if not self.hidden:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        if not self.hidden:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def normalize(text):
    parser = _TextExtractor()
    parser.feed(text)
    return re.sub(
        r"\s+", " ", unicodedata.normalize("NFKC", html.unescape("".join(parser.parts)))
    ).strip()


def chunk_text(text, size=None, overlap=None):
    """Character windows, preserving exact overlap; no tokenizer dependency."""
    size = settings.RAG_CHUNK_SIZE if size is None else size
    overlap = settings.RAG_CHUNK_OVERLAP if overlap is None else overlap
    if not 0 <= overlap < size:
        raise ValueError(
            "Chunk overlap must be nonnegative and smaller than chunk size."
        )
    chunks = []
    for start in range(0, len(text), size - overlap):
        chunks.append(text[start : start + size])
        if start + size >= len(text):
            break
    return chunks


def published_articles():
    return Article.objects.filter(
        status=Article.ArticleStatus.PUBLISHED, published_at__lte=timezone.now()
    )


def article_queryset():
    return (
        published_articles()
        .select_related("related_driver", "related_team", "related_race", "category")
        .prefetch_related("tags")
    )


def _hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def embedding_profile():
    return _hash(
        {
            "version": 1,
            "provider": settings.AI_EMBEDDING_PROVIDER,
            "model": settings.AI_EMBEDDING_MODEL,
            "dimensions": settings.AI_EMBEDDING_DIMENSIONS,
            "size": settings.RAG_CHUNK_SIZE,
            "overlap": settings.RAG_CHUNK_OVERLAP,
        }
    )


def extract_article(article):
    metadata = {
        "article_id": str(article.id),
        "title": article.title,
        "slug": article.slug,
        "published_at": article.published_at.isoformat()
        if article.published_at
        else None,
        "driver": article.related_driver.full_name if article.related_driver else None,
        "team": article.related_team.name if article.related_team else None,
        "race": article.related_race.name if article.related_race else None,
        "category": article.category.name if article.category else None,
        "tags": sorted(tag.name for tag in article.tags.all()),
    }
    text = normalize(
        "\n".join(
            filter(
                None,
                [
                    article.title,
                    article.subtitle,
                    article.summary,
                    metadata["driver"],
                    metadata["team"],
                    metadata["race"],
                    " ".join(metadata["tags"]),
                    article.content,
                ],
            )
        )
    )
    return text, metadata, _hash({"text": text, "metadata": metadata})
