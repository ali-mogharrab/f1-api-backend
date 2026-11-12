from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

from apps.ai.exceptions import ProviderTimeout, ProviderUnavailable
from apps.ai.indexing import index_article
from apps.ai.retrieval import retrieve_articles
from apps.ai.orchestration import NO_EVIDENCE, analyze
from apps.ai.providers import Generation, validate_embeddings
from apps.ai.tools import execute_tool
from apps.racing.models import Race, RaceResult

from .helpers import answer, article, dataset, embedder, function_call


@override_settings(AI_EMBEDDING_DIMENSIONS=3)
class EvidenceRegressionTests(TestCase):
    def test_changed_structured_evidence_is_rejected(self):
        data = dataset()
        source_id = f"race_result:{data['result'].pk}"
        for model, pk, changes in (
            (RaceResult, data["result"].pk, {"points": 18}),
            (Race, data["race"].pk, {"status": Race.RaceStatus.CANCELLED}),
        ):
            with self.subTest(changes=changes):
                RaceResult.objects.filter(pk=data["result"].pk).update(points=25)
                Race.objects.filter(pk=data["race"].pk).update(
                    status=Race.RaceStatus.COMPLETED
                )

                def generate(model=model, pk=pk, changes=changes, **kwargs):
                    if kwargs["tool_choice"] == "required":
                        return function_call(
                            "get_driver_recent_results",
                            {"driver": "NOR", "season": 2026, "limit": 5},
                        )
                    model.objects.filter(pk=pk).update(**changes)
                    return answer(f"25 points [{source_id}]", [source_id])

                result = analyze(
                    "Norris results", provider=Mock(generate=Mock(side_effect=generate))
                )
                self.assertEqual(result.answer, NO_EVIDENCE)
                self.assertEqual(result.sources, [])

    def test_malformed_provider_calls_fail_as_sanitized_provider_errors(self):
        for item in (
            {},
            {"type": "function_call"},
            {
                "type": "function_call",
                "name": "search_articles",
                "arguments": {},
                "call_id": "call",
            },
        ):
            with self.subTest(item=item), self.assertRaises(ProviderUnavailable):
                analyze(
                    "Question",
                    provider=Mock(generate=Mock(return_value=Generation([item], ""))),
                )

    def test_deeply_nested_tool_json_is_rejected(self):
        output = execute_tool("get_race_results", "[" * 1500 + "]" * 1500)
        self.assertEqual(output["sources"], [])
        self.assertIn("error", output)

    def test_invalid_embedding_shapes_fail_as_provider_errors(self):
        for vectors in (
            None,
            [None],
            [["1", 0, 0]],
            [[True, 0, 0]],
            [[1e100, 0, 0]],
            [[10**400, 0, 0]],
        ):
            with self.subTest(vectors=vectors), self.assertRaises(ProviderUnavailable):
                validate_embeddings(vectors, 1)

    def test_retrieval_stops_when_embedding_exhausts_deadline(self):
        index_article(article(), provider=embedder())
        with patch("apps.ai.retrieval.time.monotonic", side_effect=[0, 0, 0, 11]):
            with self.assertRaises(ProviderTimeout):
                retrieve_articles("pace", provider=embedder(), timeout=10)

    def test_snapshot_checks_do_not_add_per_row_queries(self):
        dataset()
        with self.assertNumQueries(2):
            output = execute_tool(
                "get_driver_standings",
                '{"season": 2026, "driver": null, "order_by": "position"}',
            )
        self.assertEqual(len(output["data"]), 1)
