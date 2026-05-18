import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.racing.models import Season, Team, Driver, Circuit, Race
from apps.standings.models import DriverStanding, ConstructorStanding
from apps.content.models import Category, Tag, Article

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo data for Formula 1 API"

    def handle(self, *args, **options):
        self.stdout.write("Seeding demo data...")

        # Users
        if not User.objects.filter(username="demoadmin").exists():
            admin = User.objects.create_superuser(
                username="demoadmin",
                email="demoadmin@example.com",
                password="DemoPassword123!"
            )
            self.stdout.write("Created superuser demoadmin")
        else:
            admin = User.objects.get(username="demoadmin")

        if not User.objects.filter(username="demouser").exists():
            user = User.objects.create_user(
                username="demouser",
                email="demouser@example.com",
                password="DemoPassword123!"
            )
            self.stdout.write("Created normal user demouser")
        else:
            user = User.objects.get(username="demouser")

        # Season
        season, _ = Season.objects.get_or_create(
            year=2026,
            defaults={"name": "2026 Formula One World Championship", "is_current": True}
        )

        # Teams
        teams_data = [
            {"name": "Red Bull Racing", "official_name": "Oracle Red Bull Racing", "country": "Austria"},
            {"name": "Mercedes", "official_name": "Mercedes-AMG Petronas F1 Team", "country": "Germany"},
            {"name": "Ferrari", "official_name": "Scuderia Ferrari", "country": "Italy"},
        ]
        teams = []
        for t in teams_data:
            team, _ = Team.objects.get_or_create(
                name=t["name"],
                defaults=t
            )
            teams.append(team)
        self.stdout.write(f"Created {len(teams)} teams")

        # Drivers
        drivers_data = [
            {"first_name": "Max", "last_name": "Verstappen", "abbreviation": "VER", "number": 1, "country": "Netherlands"},
            {"first_name": "Lewis", "last_name": "Hamilton", "abbreviation": "HAM", "number": 44, "country": "UK"},
            {"first_name": "Charles", "last_name": "Leclerc", "abbreviation": "LEC", "number": 16, "country": "Monaco"},
        ]
        drivers = []
        for i, d in enumerate(drivers_data):
            driver, _ = Driver.objects.get_or_create(
                first_name=d["first_name"],
                last_name=d["last_name"],
                defaults={
                    **d,
                    "status": Driver.DriverStatus.ACTIVE,
                    "current_team": teams[i % len(teams)]
                }
            )
            drivers.append(driver)
        self.stdout.write(f"Created {len(drivers)} drivers")

        # Circuits
        circuits_data = [
            {"name": "Circuit de Monaco", "country": "Monaco", "city": "Monte Carlo", "length_km": "3.337", "number_of_laps": 78, "race_distance_km": "260.286"},
            {"name": "Silverstone Circuit", "country": "UK", "city": "Silverstone", "length_km": "5.891", "number_of_laps": 52, "race_distance_km": "306.198"},
        ]
        circuits = []
        for c in circuits_data:
            circuit, _ = Circuit.objects.get_or_create(name=c["name"], defaults=c)
            circuits.append(circuit)
        self.stdout.write(f"Created {len(circuits)} circuits")

        # Races
        for i, circuit in enumerate(circuits):
            race_name = f"{circuit.city} Grand Prix"
            race, _ = Race.objects.get_or_create(
                season=season,
                name=race_name,
                defaults={
                    "official_name": f"Formula 1 {circuit.city} Grand Prix {season.year}",
                    "round_number": i+1,
                    "race_date": date(season.year, 5 + i, 15),
                    "race_time": "15:00:00",
                    "status": Race.RaceStatus.SCHEDULED,
                    "circuit": circuit,
                }
            )
        self.stdout.write(f"Created {len(circuits)} races")

        # Content
        category, _ = Category.objects.get_or_create(name="Race Previews", description="Preview articles for upcoming races")
        tag, _ = Tag.objects.get_or_create(name="Monaco GP")

        for race in Race.objects.filter(season=season):
            article, _ = Article.objects.get_or_create(
                title=f"{race.name} Preview {season.year}",
                defaults={
                    "summary": f"Preview article for {race.name}",
                    "content": f"Content of {race.name} preview article...",
                    "category": category,
                    "author": admin,
                    "status": Article.ArticleStatus.PUBLISHED,
                    "published_at": timezone.now(),
                }
            )
            article.tags.add(tag)
        self.stdout.write("Created sample articles")

        self.stdout.write(self.style.SUCCESS("Demo data seeding complete!"))
