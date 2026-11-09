import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.ai.evaluation.runner import DEFAULT_CASES, evaluate


class Command(BaseCommand):
    help = "Evaluate labeled cases against the current database/index. Retrieval and --answers incur API costs."

    def add_arguments(self, parser):
        parser.add_argument("--cases", default=str(DEFAULT_CASES))
        parser.add_argument(
            "--answers",
            action="store_true",
            help="Also generate answers (incurs generation costs).",
        )
        parser.add_argument(
            "--output", help="Write measured JSON results to this file."
        )

    def handle(self, *args, **options):
        cases = json.loads(Path(options["cases"]).read_text())
        result = evaluate(cases, answers=options["answers"])
        result["configuration"] = {
            "model": settings.AI_MODEL,
            "embedding_model": settings.AI_EMBEDDING_MODEL,
            "top_k": settings.RAG_TOP_K,
            "min_similarity": settings.RAG_MIN_SIMILARITY,
        }
        text = json.dumps(result, indent=2)
        if options["output"]:
            Path(options["output"]).write_text(text + "\n")
        self.stdout.write(text)
