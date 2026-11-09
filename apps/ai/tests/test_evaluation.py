import json
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.ai.evaluation.runner import DEFAULT_CASES, evaluate
from apps.ai.indexing import index_article

from .helpers import article, dataset, embedder


@override_settings(AI_EMBEDDING_DIMENSIONS=3)
class EvaluationTests(TestCase):
    def test_shipped_fixture_loads_and_tool_gold_matches(self):
        from io import StringIO

        from django.core.management import call_command

        call_command("loaddata", "ai_evaluation", stdout=StringIO())
        cases = [
            case for case in json.loads(DEFAULT_CASES.read_text()) if "tool" in case
        ]
        measured = evaluate(cases)
        self.assertEqual(measured["summary"]["structured_assertion_accuracy"], 1.0)

    def test_runner_measures_real_tools_and_curated_fixture_vectors(self):
        dataset()
        article_obj = article(slug="evaluation-mclaren-pace")
        index_article(article_obj, provider=embedder())
        cases = json.loads(DEFAULT_CASES.read_text())
        with patch("apps.ai.retrieval.embedding_provider", return_value=embedder()):
            measured = evaluate(cases)
        self.assertEqual(len(measured["cases"]), 6)
        self.assertEqual(measured["summary"]["structured_assertion_accuracy"], 1.0)
        self.assertEqual(measured["summary"]["retrieval_recall_at_k"], 1.0)
        self.assertNotIn("answer_pattern_accuracy", measured["summary"])
