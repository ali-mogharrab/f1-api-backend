from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.ai.documents import chunk_text, normalize
from apps.ai.exceptions import ProviderUnavailable
from apps.ai.indexing import index_article, prune_documents
from apps.ai.models import ArticleChunk, ArticleDocument
from apps.ai.retrieval import retrieve_articles
from apps.content.models import Article, Tag

from .helpers import article, embedder


class ChunkTests(TestCase):
    def test_overlap_and_boundary(self):
        self.assertEqual(
            chunk_text("abcdefghij", size=5, overlap=2), ["abcde", "defgh", "ghij"]
        )
        self.assertEqual(chunk_text("abcde", size=5, overlap=2), ["abcde"])
        self.assertEqual(chunk_text("", size=5, overlap=2), [])
        for size, overlap in [(0, 0), (5, 5), (5, -1)]:
            with self.assertRaises(ValueError):
                chunk_text("text", size=size, overlap=overlap)

    def test_html_normalization(self):
        self.assertEqual(
            normalize("<h1>Race</h1><script>steal()</script><p>Pace &amp; tyres</p>"),
            "Race Pace & tyres",
        )


@override_settings(AI_EMBEDDING_DIMENSIONS=3)
class IndexRetrievalTests(TestCase):
    def test_mixed_embedding_dimensions_are_isolated_during_model_transition(self):
        old_article = article(title="Old model article")
        new_article = article(title="New model article")
        index_article(old_article, provider=embedder())
        with override_settings(AI_EMBEDDING_DIMENSIONS=2):
            index_article(new_article, provider=embedder([1.0, 0.0]))
            result = retrieve_articles("pace", provider=embedder([1.0, 0.0]))
        self.assertEqual(
            [src["entity_id"] for src in result["sources"]], [str(new_article.pk)]
        )

    def test_idempotent_and_update_replaces_chunks(self):
        obj, provider = article(), embedder()
        self.assertEqual(index_article(obj, provider=provider), "indexed")
        ids = list(ArticleChunk.objects.values_list("pk", flat=True))
        self.assertEqual(index_article(obj, provider=provider), "unchanged")
        self.assertEqual(provider.embed.call_count, 1)
        self.assertEqual(list(ArticleChunk.objects.values_list("pk", flat=True)), ids)
        obj.content = "Revised strategy after the latest race."
        obj.save()
        self.assertEqual(index_article(obj, provider=provider), "indexed")
        self.assertEqual(ArticleDocument.objects.count(), 1)
        self.assertFalse(ArticleChunk.objects.filter(pk__in=ids).exists())

    def test_force_and_profile_change(self):
        obj, provider = article(), embedder()
        index_article(obj, provider=provider)
        index_article(obj, provider=provider, force=True)
        with override_settings(AI_EMBEDDING_MODEL="another-model"):
            self.assertEqual(retrieve_articles("pace", provider=provider)["data"], [])
            self.assertEqual(index_article(obj, provider=provider), "indexed")
        self.assertEqual(provider.embed.call_count, 3)

    def test_failure_preserves_previous_index_but_stale_content_not_retrieved(self):
        obj, provider = article(), embedder()
        index_article(obj, provider=provider)
        old_ids = list(ArticleChunk.objects.values_list("pk", flat=True))
        obj.content = "New content"
        obj.save()
        provider.embed.side_effect = ProviderUnavailable()
        with self.assertRaises(ProviderUnavailable):
            index_article(obj, provider=provider)
        self.assertEqual(
            list(ArticleChunk.objects.values_list("pk", flat=True)), old_ids
        )
        self.assertEqual(retrieve_articles("pace", provider=embedder())["data"], [])

    def test_no_drafts_future_articles_and_unpublication_immediate(self):
        published = article()
        draft = article(
            title="Secret draft", status=Article.ArticleStatus.DRAFT, published_at=None
        )
        future = article(
            title="Scheduled", published_at=timezone.now() + timedelta(days=2)
        )
        provider = embedder()
        for obj in [published, draft, future]:
            index_article(obj, provider=provider)
        self.assertEqual(provider.embed.call_count, 1)
        self.assertEqual(ArticleDocument.objects.count(), 1)
        published.status = Article.ArticleStatus.ARCHIVED
        published.save()
        self.assertEqual(retrieve_articles("pace", provider=provider)["sources"], [])
        prune_documents()
        self.assertEqual(ArticleChunk.objects.count(), 0)

    def test_deleted_articles_cascade(self):
        obj = article()
        index_article(obj, provider=embedder())
        obj.delete()
        self.assertEqual(ArticleDocument.objects.count(), 0)
        self.assertEqual(ArticleChunk.objects.count(), 0)

    @override_settings(RAG_TOP_K=1, RAG_MIN_SIMILARITY=0.8)
    def test_similarity_ranking_threshold_and_verified_urls(self):
        relevant = article()
        unrelated = article(title="Circuit history")
        index_article(relevant, provider=embedder([1.0, 0.0, 0.0]))
        index_article(unrelated, provider=embedder([0.0, 1.0, 0.0]))
        result = retrieve_articles(
            "McLaren performance", provider=embedder([1.0, 0.0, 0.0])
        )
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["sources"][0]["entity_id"], str(relevant.pk))
        self.assertEqual(result["sources"][0]["url"], f"/articles/{relevant.slug}")
        self.assertEqual(result["data"][0]["similarity"], 1.0)
        self.assertEqual(
            retrieve_articles("unknown", provider=embedder([0.0, 0.0, 1.0]))["data"], []
        )

    def test_tag_change_invalidates_evidence(self):
        obj = article()
        index_article(obj, provider=embedder())
        obj.tags.add(Tag.objects.create(name="new tag"))
        self.assertEqual(retrieve_articles("pace", provider=embedder())["data"], [])

    def test_article_changed_during_embedding_is_not_committed(self):
        obj, provider = article(), embedder()

        def change(texts):
            Article.objects.filter(pk=obj.pk).update(content="Changed during request")
            return [[1.0, 0.0, 0.0] for _ in texts]

        provider.embed.side_effect = change
        with self.assertRaises(ValueError):
            index_article(obj, provider=provider)
        self.assertEqual(ArticleDocument.objects.count(), 0)

    def test_invalid_vectors_rejected(self):
        for vector in [[0.0, 0.0, 0.0], [1.0, 2.0], [float("nan"), 0.0, 1.0]]:
            with self.assertRaises(ProviderUnavailable):
                index_article(article(title=str(vector)), provider=embedder(vector))

    def test_command_idempotent_publish_update_unpublish_and_errors(self):
        obj = article()
        provider = embedder()
        with patch("apps.ai.indexing.embedding_provider", return_value=provider):
            call_command("index_articles", stdout=StringIO())
            call_command("index_articles", stdout=StringIO())
        self.assertEqual(provider.embed.call_count, 1)
        obj.status = Article.ArticleStatus.DRAFT
        obj.save()
        call_command("index_articles", stdout=StringIO())
        self.assertEqual(ArticleChunk.objects.count(), 0)
        obj.status = Article.ArticleStatus.PUBLISHED
        obj.save()
        provider.embed.side_effect = ProviderUnavailable()
        with (
            patch("apps.ai.indexing.embedding_provider", return_value=provider),
            self.assertRaises(CommandError),
        ):
            call_command("index_articles", stdout=StringIO(), stderr=StringIO())
