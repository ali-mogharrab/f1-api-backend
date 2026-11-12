from django.conf import settings
from django.db import transaction

from .documents import (
    article_queryset,
    chunk_text,
    embedding_profile,
    extract_article,
    published_articles,
)
from .models import ArticleChunk, ArticleDocument
from .providers import embedding_provider, validate_embeddings


def prune_documents():
    """FK cascades remove deleted articles; this removes unpublished/scheduled ones."""
    return ArticleDocument.objects.exclude(
        article_id__in=published_articles().values("id")
    ).delete()[0]


def index_article(article, *, provider=None, force=False):
    if not published_articles().filter(pk=article.pk).exists():
        ArticleDocument.objects.filter(article_id=article.pk).delete()
        return "removed"
    text, metadata, fingerprint = extract_article(article)
    profile = embedding_profile()
    if (
        not force
        and ArticleDocument.objects.filter(
            article=article, fingerprint=fingerprint, profile=profile
        ).exists()
    ):
        return "unchanged"
    if len(text) > settings.RAG_MAX_ARTICLE_CHARS:
        raise ValueError(
            "Article exceeds RAG_MAX_ARTICLE_CHARS; split it before indexing."
        )
    chunks = chunk_text(text)
    provider = provider or embedding_provider()
    vectors = []
    for start in range(0, len(chunks), settings.RAG_EMBEDDING_BATCH_SIZE):
        batch = chunks[start : start + settings.RAG_EMBEDDING_BATCH_SIZE]
        vectors.extend(validate_embeddings(provider.embed(batch), len(batch)))

    with transaction.atomic():
        current = (
            article_queryset()
            .select_for_update(of=("self",))
            .filter(pk=article.pk)
            .first()
        )
        if current is None:
            ArticleDocument.objects.filter(article_id=article.pk).delete()
            return "removed"
        if extract_article(current)[2] != fingerprint:
            raise ValueError("Article changed while embedding; rerun indexing.")
        document, _ = ArticleDocument.objects.get_or_create(
            article=current,
            defaults={"fingerprint": fingerprint, "profile": profile},
        )
        document.fingerprint, document.profile = fingerprint, profile
        document.save()
        document.chunks.all().delete()
        ArticleChunk.objects.bulk_create(
            [
                ArticleChunk(
                    document=document,
                    ordinal=i,
                    text=chunk,
                    embedding=vector,
                    metadata=metadata,
                )
                for i, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
            ]
        )
    return "indexed"
