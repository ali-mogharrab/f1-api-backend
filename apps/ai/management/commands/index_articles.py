from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from apps.ai.documents import article_queryset
from apps.ai.exceptions import ProviderTimeout, ProviderUnavailable
from apps.ai.indexing import index_article, prune_documents


class Command(BaseCommand):
    help = "Idempotently index published articles; remove unpublished/deleted content."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-embed unchanged articles too (incurs provider cost).",
        )

    def handle(self, *args, **options):
        counts = Counter()
        self.stdout.write(f"Pruned records: {prune_documents()}")
        for article in article_queryset().order_by("id").iterator(chunk_size=100):
            try:
                result = index_article(article, force=options["force"])
                counts[result] += 1
                self.stdout.write(f"{article.pk}: {result}")
            except (ProviderTimeout, ProviderUnavailable, ValueError):
                counts["errors"] += 1
                # Do not log article text, provider bodies, or credentials.
                self.stderr.write(
                    f"{article.pk}: indexing failed; check provider/configuration and rerun."
                )
        self.stdout.write(f"Indexing summary: {dict(counts)}")
        if counts["errors"]:
            raise CommandError(
                f"{counts['errors']} article(s) failed. Existing chunks were preserved atomically."
            )
