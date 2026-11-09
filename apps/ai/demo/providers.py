"""Deterministic adapters; no ORM access, network, model downloads, or execution."""

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

from apps.ai.configuration import require_demo_configuration
from apps.ai.exceptions import ProviderTimeout
from apps.ai.providers import Generation, validate_embeddings

DEMO_NOTICE = "Demo Mode: scripted output using synthetic demonstration data, not historical F1 statistics."
STOP_WORDS = frozenset(
    "a an and are as at be by do for from has in is it of on or say that the their this to was were what with".split()
)


def normalize_question(question):
    text = unicodedata.normalize("NFKC", question).casefold().replace("’", "'")
    return " ".join(text.split()).rstrip(".?!")


@dataclass(frozen=True)
class Scenario:
    steps: tuple
    renderer: str


def article_step(team):
    return (
        "search_articles",
        {
            "query": f"{team} performance race pace",
            "team": team,
            "driver": None,
            "race": None,
            "latest": True,
        },
    )


SUPPORTED_QUESTIONS = (
    "Compare Ferrari and McLaren's performance.",
    "What do the articles say about Ferrari?",
    "What do the articles say about McLaren?",
    "Analyze McLaren's race results and related articles.",
    "Who won the 2030 championship?",
)
SCENARIOS = dict(
    zip(
        (normalize_question(q) for q in SUPPORTED_QUESTIONS),
        (
            Scenario(
                (("get_constructor_standings", {"season": None, "team": None}),),
                "constructors",
            ),
            Scenario((article_step("Ferrari"),), "articles"),
            Scenario((article_step("McLaren"),), "articles"),
            Scenario(
                (
                    (
                        "get_team_recent_results",
                        {"team": "McLaren", "season": None, "limit": 5},
                    ),
                    article_step("McLaren"),
                ),
                "hybrid",
            ),
            Scenario(
                (
                    (
                        "get_driver_standings",
                        {"season": 2030, "driver": None, "order_by": "points"},
                    ),
                ),
                "drivers",
            ),
        ),
        strict=True,
    )
)


def _answer(
    text="Evidence is unavailable for this demo scenario.", ids=(), insufficient=True
):
    return Generation(
        [],
        json.dumps(
            {
                "answer": text,
                "source_ids": list(dict.fromkeys(ids)),
                "insufficient_evidence": insufficient,
            }
        ),
    )


def _evidence_rows(result):
    sources = {src["id"] for src in result.get("sources", [])}
    return [row for row in result.get("data", []) if row.get("source_id") in sources]


def _article_excerpts(result):
    """Extract evidence, never interpret instructions embedded in an article."""
    excerpts, ids, seen = [], [], set()
    sources = {src["id"]: src for src in result.get("sources", [])}
    for row in _evidence_rows(result):
        src = sources[row["source_id"]]
        if src["entity_id"] in seen:
            continue
        seen.add(src["entity_id"])
        excerpt = row["text"][:280]
        excerpts.append(f"Published normalized excerpt: “{excerpt}” [{src['id']}].")
        ids.append(src["id"])
        if len(excerpts) == 2:
            break
    return excerpts, ids


class DemoEmbeddingProvider:
    is_demo = True

    def embed(self, texts, *, timeout=None):
        require_demo_configuration()
        if timeout is not None and timeout <= 0:
            raise ProviderTimeout()
        vectors = []
        for text in texts:
            words = re.findall(
                r"[^\W_]+", unicodedata.normalize("NFKC", text).casefold()
            )
            counts = Counter(word for word in words if word not in STOP_WORDS)
            vector = [0.0] * settings.AI_EMBEDDING_DIMENSIONS
            for word, count in sorted((counts or {"__empty__": 1}).items()):
                digest = hashlib.sha256(f"demo-token-hash-v1:{word}".encode()).digest()
                index = int.from_bytes(digest[:8], "big") % len(vector)
                vector[index] += 1 + math.log(count)
            norm = math.sqrt(sum(value * value for value in vector))
            vectors.append([value / norm for value in vector])
        return validate_embeddings(vectors, len(texts))


class DemoGenerationProvider:
    is_demo = True

    def generate(self, *, messages, instructions, tools, tool_choice, timeout):
        require_demo_configuration()
        if timeout <= 0:
            raise ProviderTimeout()
        # Only the last user message selects a script; neither history nor
        # retrieved article text can choose tools or alter the plan.
        user_index = next(
            (
                i
                for i in range(len(messages) - 1, -1, -1)
                if messages[i].get("role") == "user"
            ),
            None,
        )
        if user_index is None:
            return _answer()
        scenario = SCENARIOS.get(normalize_question(messages[user_index]["content"]))
        if scenario is None:
            return _answer()
        calls, results = {}, []
        for item in messages[user_index + 1 :]:
            if item.get("type") == "function_call":
                calls[item["call_id"]] = item
            elif item.get("type") == "function_call_output":
                call = calls.get(item["call_id"])
                if not call or len(results) >= len(scenario.steps):
                    return _answer()
                expected_name, expected_args = scenario.steps[len(results)]
                if (
                    call["name"] != expected_name
                    or json.loads(call["arguments"]) != expected_args
                ):
                    return _answer()
                results.append(json.loads(item["output"]))
        if len(results) < len(scenario.steps):
            name, args = scenario.steps[len(results)]
            if tool_choice == "none" or name not in {tool["name"] for tool in tools}:
                return _answer()
            return Generation(
                [
                    {
                        "type": "function_call",
                        "name": name,
                        "arguments": json.dumps(args),
                        "call_id": f"demo_call_{len(results) + 1}",
                    }
                ],
                "",
            )
        if any(result.get("error") or not _evidence_rows(result) for result in results):
            return _answer()
        text, ids = self._render(scenario.renderer, results)
        return (
            _answer(
                f"{DEMO_NOTICE}\n\n{text}",
                ids,
                insufficient=scenario.renderer == "drivers",
            )
            if ids
            else _answer()
        )

    def _render(self, renderer, results):
        if renderer == "drivers":
            row = _evidence_rows(results[0])[0]
            return (
                f"Stored {row['season']} synthetic snapshot: {row['driver']} is P{row['position']} with {row['points']} points [{row['source_id']}]. "
                "A snapshot does not verify a completed championship winner; that information is unavailable.",
                [row["source_id"]],
            )
        if renderer == "constructors":
            rows = {row["team"]: row for row in _evidence_rows(results[0])}
            if not {"Ferrari", "McLaren"} <= rows.keys():
                return "", []
            chosen = [rows[team] for team in ("Ferrari", "McLaren")]
            lines = [
                f"{r['season']} synthetic snapshot — {r['team']}: P{r['position']}, {r['points']} points, {r['wins']} wins [{r['source_id']}]."
                for r in chosen
            ]
            return (
                " ".join(lines)
                + " These are stored demonstration snapshots, not complete historical standings.",
                [r["source_id"] for r in chosen],
            )
        if renderer == "articles":
            lines, ids = _article_excerpts(results[0])
            return "\n".join(
                lines
            ) + "\nThese are extractive excerpts, not an LLM summary.", ids
        rows = _evidence_rows(results[0])
        points = sum((Decimal(row["points"]) for row in rows), Decimal("0"))
        ids = [row["source_id"] for row in rows]
        citations = " ".join(f"[{source_id}]" for source_id in ids)
        lines = [
            f"McLaren has {len(rows)} stored driver results across {len({row['race_id'] for row in rows})} races, totaling {points:.2f} race points (sprints excluded). {citations}"
        ]
        excerpts, article_ids = _article_excerpts(results[1])
        lines.extend(excerpts)
        lines.append(
            "This script displays numeric results alongside article excerpts; it does not infer causes or perform LLM reasoning. Missing races remain unknown."
        )
        return "\n".join(lines), ids + article_ids
