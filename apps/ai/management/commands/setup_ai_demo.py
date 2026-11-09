from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from apps.ai.demo.dataset import prepare_demo_database, seed_demo_records


class Command(BaseCommand):
    help = "Prepare an isolated synthetic SQLite demo, migrate, create missing fixture rows, and index articles offline."

    def handle(self, *args, **options):
        path = prepare_demo_database()
        call_command("migrate", interactive=False, verbosity=0, stdout=self.stdout)
        try:
            created = seed_demo_records()
        except IntegrityError:
            raise CommandError(
                "Demo fixture identity conflicts with existing rows. No seed records were changed; choose a fresh demo database."
            ) from None
        self.stdout.write(f"Synthetic demo database: {path}")
        self.stdout.write(
            f"Created {created} records; existing records were preserved."
        )
        call_command("index_articles", stdout=self.stdout, stderr=self.stderr)
        self.stdout.write(
            self.style.SUCCESS(
                "Offline demo ready. All statistics and reporting in this database are synthetic. Create a local account, then runserver with config.settings.demo."
            )
        )
