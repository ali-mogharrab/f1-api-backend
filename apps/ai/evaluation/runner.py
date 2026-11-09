"""Measured checks, not an LLM judge. Regex checks are only smoke assertions."""

import json
import re
from pathlib import Path

from apps.ai.documents import published_articles
from apps.ai.orchestration import analyze
from apps.ai.retrieval import retrieve_articles
from apps.ai.tools import execute_tool
from apps.racing.models import RaceResult
from apps.standings.models import ConstructorStanding, DriverStanding

DEFAULT_CASES = Path(__file__).with_name("cases.json")


def get_path(value, path):
    for part in path.split("."):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def source_valid(source):
    model = {
        "article": None,
        "race_result": RaceResult,
        "driver_standing": DriverStanding,
        "constructor_standing": ConstructorStanding,
    }.get(source.get("type"))
    if source.get("type") == "article":
        return (
            published_articles()
            .filter(pk=source["entity_id"], slug=source.get("slug"))
            .exists()
        )
    return bool(model and model.objects.filter(pk=source["entity_id"]).exists())


def evaluate(cases, *, answers=False):
    results = []
    for case in cases:
        row = {"id": case["id"], "category": case["category"]}
        if "tool" in case:
            output = execute_tool(case["tool"], json.dumps(case["arguments"]))
            assertions = []
            for path, expected in case["expected_values"].items():
                try:
                    assertions.append(get_path(output, path) == expected)
                except (KeyError, IndexError, TypeError):
                    assertions.append(False)
            row["structured_assertion_accuracy"] = sum(assertions) / len(assertions)
        if "expected_article_slugs" in case:
            retrieval = retrieve_articles(case["question"])
            expected = set(case["expected_article_slugs"])
            actual = {src["slug"] for src in retrieval["sources"]}
            row["retrieval_recall_at_k"] = len(expected & actual) / len(expected)
        if answers:
            result = analyze(case["question"])
            row["answer"] = result.answer
            row["sources"] = result.sources
            row["answer_pattern_accuracy"] = sum(
                bool(re.search(pattern, result.answer, re.I))
                for pattern in case["answer_patterns"]
            ) / len(case["answer_patterns"])
            row["citation_validity"] = (
                (sum(source_valid(src) for src in result.sources) / len(result.sources))
                if result.sources
                else None
            )
            required = set(case.get("required_tools", []))
            row["required_tool_coverage"] = (
                len(required & set(result.metadata["tool_calls"])) / len(required)
                if required
                else None
            )
            if "expected_insufficient" in case:
                row["missing_evidence_correct"] = (
                    result.metadata["insufficient_evidence"]
                    == case["expected_insufficient"]
                )
        results.append(row)
    metric_names = {
        key
        for row in results
        for key in row
        if key not in {"id", "category", "answer", "sources"}
    }
    summary = {}
    for name in sorted(metric_names):
        values = [
            row[name] for row in results if isinstance(row.get(name), (float, bool))
        ]
        summary[name] = sum(values) / len(values) if values else None
    return {
        "summary": summary,
        "cases": results,
        "limitations": "Recall measures labeled fixture articles. Pattern accuracy is a smoke assertion, not general answer correctness. Citation validity checks source existence/publication, not claim entailment; review answers manually.",
    }
