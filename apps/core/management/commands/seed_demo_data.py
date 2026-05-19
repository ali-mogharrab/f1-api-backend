from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.content.models import Article, Category, Tag
from apps.racing.models import (
    Circuit,
    Driver,
    QualifyingResult,
    Race,
    RaceResult,
    Season,
    SprintResult,
    Team,
)
from apps.standings.models import ConstructorStanding, DriverStanding


User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo data for the Formula 1 API"

    def handle(self, *args, **options):
        self.stdout.write("Seeding demo data...")

        admin = self.create_users()
        season = self.create_season()
        teams = self.create_teams()
        drivers = self.create_drivers(teams)
        circuits = self.create_circuits()
        races = self.create_races(season, circuits)

        self.create_qualifying_results(races[0], drivers)
        self.create_race_results(races[0], drivers)
        self.create_sprint_results(races[1], drivers)
        self.create_standings(season, drivers, teams)
        self.create_articles(admin, races, drivers, teams)

        self.stdout.write(self.style.SUCCESS("Demo data seeding complete."))

    def create_users(self):
        admin, created = User.objects.get_or_create(
            username="demoadmin",
            defaults={
                "email": "demoadmin@example.com",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin.set_password("DemoPassword123!")
            admin.save()
            self.stdout.write("Created demo admin user.")

        user, created = User.objects.get_or_create(
            username="demouser",
            defaults={
                "email": "demouser@example.com",
            },
        )
        if created:
            user.set_password("DemoPassword123!")
            user.save()
            self.stdout.write("Created demo normal user.")

        return admin

    def create_season(self):
        season, _ = Season.objects.update_or_create(
            year=2026,
            defaults={
                "name": "2026 Formula One World Championship",
                "is_current": True,
            },
        )

        Season.objects.exclude(id=season.id).update(is_current=False)

        return season

    def create_teams(self):
        teams_data = [
            {
                "name": "Red Bull Racing",
                "official_name": "Oracle Red Bull Racing",
                "country": "Austria",
                "base_location": "Milton Keynes, United Kingdom",
                "team_principal": "Laurent Mekies",
                "technical_chief": "Pierre Waché",
                "chassis": "RB22",
                "power_unit": "Red Bull Ford Powertrains",
                "first_team_entry": 2005,
                "world_championships": 6,
                "website": "https://www.redbullracing.com/",
                "is_active": True,
            },
            {
                "name": "Ferrari",
                "official_name": "Scuderia Ferrari",
                "country": "Italy",
                "base_location": "Maranello, Italy",
                "team_principal": "Frédéric Vasseur",
                "technical_chief": "Loïc Serra",
                "chassis": "SF-26",
                "power_unit": "Ferrari",
                "first_team_entry": 1950,
                "world_championships": 16,
                "website": "https://www.ferrari.com/en-EN/formula1",
                "is_active": True,
            },
            {
                "name": "McLaren",
                "official_name": "McLaren Formula 1 Team",
                "country": "United Kingdom",
                "base_location": "Woking, United Kingdom",
                "team_principal": "Andrea Stella",
                "technical_chief": "Peter Prodromou",
                "chassis": "MCL40",
                "power_unit": "Mercedes",
                "first_team_entry": 1966,
                "world_championships": 9,
                "website": "https://www.mclaren.com/racing/",
                "is_active": True,
            },
        ]

        teams = []

        for data in teams_data:
            team, _ = Team.objects.update_or_create(
                name=data["name"],
                defaults=data,
            )
            teams.append(team)

        self.stdout.write(f"Seeded {len(teams)} teams.")
        return teams

    def create_drivers(self, teams):
        red_bull, ferrari, mclaren = teams

        drivers_data = [
            {
                "first_name": "Max",
                "last_name": "Verstappen",
                "abbreviation": "VER",
                "number": 1,
                "country": "Netherlands",
                "date_of_birth": "1997-09-30",
                "place_of_birth": "Hasselt, Belgium",
                "current_team": red_bull,
            },
            {
                "first_name": "Charles",
                "last_name": "Leclerc",
                "abbreviation": "LEC",
                "number": 16,
                "country": "Monaco",
                "date_of_birth": "1997-10-16",
                "place_of_birth": "Monte Carlo, Monaco",
                "current_team": ferrari,
            },
            {
                "first_name": "Lando",
                "last_name": "Norris",
                "abbreviation": "NOR",
                "number": 4,
                "country": "United Kingdom",
                "date_of_birth": "1999-11-13",
                "place_of_birth": "Bristol, United Kingdom",
                "current_team": mclaren,
            },
        ]

        drivers = []

        for data in drivers_data:
            driver, _ = Driver.objects.update_or_create(
                abbreviation=data["abbreviation"],
                defaults={
                    **data,
                    "status": Driver.DriverStatus.ACTIVE,
                },
            )
            drivers.append(driver)

        self.stdout.write(f"Seeded {len(drivers)} drivers.")
        return drivers

    def create_circuits(self):
        circuits_data = [
            {
                "name": "Circuit de Monaco",
                "official_name": "Circuit de Monaco",
                "country": "Monaco",
                "city": "Monte Carlo",
                "length_km": "3.337",
                "number_of_laps": 78,
                "race_distance_km": "260.286",
                "lap_record": "1:12.909",
                "lap_record_driver": "Lewis Hamilton",
                "lap_record_year": 2021,
                "latitude": "43.734722",
                "longitude": "7.420556",
            },
            {
                "name": "Silverstone Circuit",
                "official_name": "Silverstone Circuit",
                "country": "United Kingdom",
                "city": "Silverstone",
                "length_km": "5.891",
                "number_of_laps": 52,
                "race_distance_km": "306.198",
                "lap_record": "1:27.097",
                "lap_record_driver": "Max Verstappen",
                "lap_record_year": 2020,
                "latitude": "52.078611",
                "longitude": "-1.016944",
            },
        ]

        circuits = []

        for data in circuits_data:
            circuit, _ = Circuit.objects.update_or_create(
                name=data["name"],
                country=data["country"],
                defaults=data,
            )
            circuits.append(circuit)

        self.stdout.write(f"Seeded {len(circuits)} circuits.")
        return circuits

    def create_races(self, season, circuits):
        monaco, silverstone = circuits

        races_data = [
            {
                "name": "Monaco Grand Prix",
                "official_name": "Formula 1 Grand Prix de Monaco 2026",
                "round_number": 8,
                "race_date": date(2026, 6, 7),
                "race_time": "15:00:00",
                "qualifying_date": date(2026, 6, 6),
                "qualifying_time": "16:00:00",
                "sprint_date": None,
                "sprint_time": None,
                "status": Race.RaceStatus.COMPLETED,
                "circuit": monaco,
            },
            {
                "name": "British Grand Prix",
                "official_name": "Formula 1 British Grand Prix 2026",
                "round_number": 9,
                "race_date": date(2026, 7, 5),
                "race_time": "15:00:00",
                "qualifying_date": date(2026, 7, 4),
                "qualifying_time": "16:00:00",
                "sprint_date": date(2026, 7, 4),
                "sprint_time": "12:00:00",
                "status": Race.RaceStatus.SCHEDULED,
                "circuit": silverstone,
            },
        ]

        races = []

        for data in races_data:
            race, _ = Race.objects.update_or_create(
                season=season,
                round_number=data["round_number"],
                defaults=data,
            )
            races.append(race)

        self.stdout.write(f"Seeded {len(races)} races.")
        return races

    def create_qualifying_results(self, race, drivers):
        results_data = [
            {
                "driver": drivers[1],
                "team": drivers[1].current_team,
                "position": 1,
                "q1_time": "1:11.456",
                "q2_time": "1:10.982",
                "q3_time": "1:10.270",
                "laps_completed": 18,
            },
            {
                "driver": drivers[0],
                "team": drivers[0].current_team,
                "position": 2,
                "q1_time": "1:11.700",
                "q2_time": "1:11.002",
                "q3_time": "1:10.445",
                "laps_completed": 17,
            },
            {
                "driver": drivers[2],
                "team": drivers[2].current_team,
                "position": 3,
                "q1_time": "1:11.820",
                "q2_time": "1:11.120",
                "q3_time": "1:10.612",
                "laps_completed": 17,
            },
        ]

        for data in results_data:
            QualifyingResult.objects.update_or_create(
                race=race,
                driver=data["driver"],
                defaults=data,
            )

        self.stdout.write("Seeded qualifying results.")

    def create_race_results(self, race, drivers):
        results_data = [
            {
                "driver": drivers[0],
                "team": drivers[0].current_team,
                "position": 1,
                "classified_position": "1",
                "grid_position": 2,
                "laps_completed": 78,
                "time": "1:42:15.456",
                "fastest_lap": True,
                "fastest_lap_time": "1:12.909",
                "fastest_lap_rank": 1,
                "points": "26.00",
                "status": RaceResult.ResultStatus.CLASSIFIED,
            },
            {
                "driver": drivers[1],
                "team": drivers[1].current_team,
                "position": 2,
                "classified_position": "2",
                "grid_position": 1,
                "laps_completed": 78,
                "time": "+4.125",
                "fastest_lap": False,
                "fastest_lap_time": "1:13.210",
                "fastest_lap_rank": 2,
                "points": "18.00",
                "status": RaceResult.ResultStatus.CLASSIFIED,
            },
            {
                "driver": drivers[2],
                "team": drivers[2].current_team,
                "position": 3,
                "classified_position": "3",
                "grid_position": 3,
                "laps_completed": 78,
                "time": "+9.872",
                "fastest_lap": False,
                "fastest_lap_time": "1:13.455",
                "fastest_lap_rank": 3,
                "points": "15.00",
                "status": RaceResult.ResultStatus.CLASSIFIED,
            },
        ]

        for data in results_data:
            RaceResult.objects.update_or_create(
                race=race,
                driver=data["driver"],
                defaults=data,
            )

        self.stdout.write("Seeded race results.")

    def create_sprint_results(self, race, drivers):
        results_data = [
            {
                "driver": drivers[2],
                "team": drivers[2].current_team,
                "position": 1,
                "grid_position": 1,
                "laps_completed": 19,
                "time": "31:05.123",
                "points": "8.00",
                "status": SprintResult.SprintStatus.CLASSIFIED,
            },
            {
                "driver": drivers[0],
                "team": drivers[0].current_team,
                "position": 2,
                "grid_position": 2,
                "laps_completed": 19,
                "time": "+2.821",
                "points": "7.00",
                "status": SprintResult.SprintStatus.CLASSIFIED,
            },
            {
                "driver": drivers[1],
                "team": drivers[1].current_team,
                "position": 3,
                "grid_position": 3,
                "laps_completed": 19,
                "time": "+6.402",
                "points": "6.00",
                "status": SprintResult.SprintStatus.CLASSIFIED,
            },
        ]

        for data in results_data:
            SprintResult.objects.update_or_create(
                race=race,
                driver=data["driver"],
                defaults=data,
            )

        self.stdout.write("Seeded sprint results.")

    def create_standings(self, season, drivers, teams):
        driver_standings_data = [
            {
                "driver": drivers[0],
                "team": drivers[0].current_team,
                "position": 1,
                "points": "275.00",
                "wins": 8,
                "podiums": 13,
                "poles": 5,
                "fastest_laps": 4,
                "races_entered": 14,
                "races_finished": 13,
                "dnfs": 1,
            },
            {
                "driver": drivers[2],
                "team": drivers[2].current_team,
                "position": 2,
                "points": "241.00",
                "wins": 5,
                "podiums": 11,
                "poles": 4,
                "fastest_laps": 3,
                "races_entered": 14,
                "races_finished": 14,
                "dnfs": 0,
            },
            {
                "driver": drivers[1],
                "team": drivers[1].current_team,
                "position": 3,
                "points": "218.00",
                "wins": 3,
                "podiums": 10,
                "poles": 3,
                "fastest_laps": 2,
                "races_entered": 14,
                "races_finished": 12,
                "dnfs": 2,
            },
        ]

        for data in driver_standings_data:
            DriverStanding.objects.update_or_create(
                season=season,
                driver=data["driver"],
                defaults=data,
            )

        constructor_standings_data = [
            {
                "team": teams[2],
                "position": 1,
                "points": "430.00",
                "wins": 6,
                "podiums": 18,
                "poles": 5,
                "fastest_laps": 4,
                "races_entered": 14,
                "double_podiums": 5,
                "double_points_finishes": 12,
            },
            {
                "team": teams[0],
                "position": 2,
                "points": "389.00",
                "wins": 8,
                "podiums": 14,
                "poles": 5,
                "fastest_laps": 4,
                "races_entered": 14,
                "double_podiums": 3,
                "double_points_finishes": 10,
            },
            {
                "team": teams[1],
                "position": 3,
                "points": "352.00",
                "wins": 3,
                "podiums": 12,
                "poles": 3,
                "fastest_laps": 2,
                "races_entered": 14,
                "double_podiums": 2,
                "double_points_finishes": 9,
            },
        ]

        for data in constructor_standings_data:
            ConstructorStanding.objects.update_or_create(
                season=season,
                team=data["team"],
                defaults=data,
            )

        self.stdout.write("Seeded championship standings.")

    def create_articles(self, admin, races, drivers, teams):
        category, _ = Category.objects.update_or_create(
            name="Race Previews",
            defaults={
                "description": "Previews before upcoming Formula 1 race weekends.",
            },
        )

        analysis_category, _ = Category.objects.update_or_create(
            name="Analysis",
            defaults={
                "description": "Formula 1 analysis, strategy, and performance stories.",
            },
        )

        monaco_tag, _ = Tag.objects.update_or_create(name="Monaco GP")
        strategy_tag, _ = Tag.objects.update_or_create(name="Strategy")
        red_bull_tag, _ = Tag.objects.update_or_create(name="Red Bull")

        articles_data = [
            {
                "title": "Monaco Grand Prix 2026 Review",
                "subtitle": "A tense street fight decided by qualifying and strategy.",
                "summary": (
                    "The Monaco Grand Prix delivered another tactical battle, "
                    "with track position, tire management, and late-race pressure shaping the result."
                ),
                "content": (
                    "The 2026 Monaco Grand Prix showed once again why Saturday is so important "
                    "on the streets of Monte Carlo.\n\n"
                    "Qualifying shaped the race, but strategy kept the result alive until the final laps. "
                    "Red Bull, Ferrari, and McLaren all showed competitive pace, creating a tight fight at the front."
                ),
                "category": analysis_category,
                "tags": [monaco_tag, strategy_tag],
                "related_race": races[0],
                "related_driver": drivers[0],
                "related_team": teams[0],
                "status": Article.ArticleStatus.PUBLISHED,
                "is_featured": True,
                "published_at": timezone.now(),
            },
            {
                "title": "British Grand Prix 2026 Preview",
                "subtitle": "Silverstone prepares for a high-speed championship battle.",
                "summary": (
                    "The British Grand Prix is expected to favor efficient cars with strong high-speed balance."
                ),
                "content": (
                    "Silverstone is one of the fastest circuits on the Formula 1 calendar.\n\n"
                    "The 2026 race could be a major test for McLaren, Ferrari, and Red Bull as the championship fight develops."
                ),
                "category": category,
                "tags": [strategy_tag],
                "related_race": races[1],
                "related_driver": drivers[2],
                "related_team": teams[2],
                "status": Article.ArticleStatus.PUBLISHED,
                "is_featured": True,
                "published_at": timezone.now(),
            },
            {
                "title": "How Red Bull Managed Monaco Strategy",
                "subtitle": "A closer look at the decisions that shaped the race.",
                "summary": (
                    "Red Bull's Monaco race was built around patience, clean execution, and a decisive tire strategy."
                ),
                "content": (
                    "Monaco strategy is rarely simple. Overtaking is difficult, so teams must use pit timing, "
                    "tire life, and traffic management to create opportunities.\n\n"
                    "Red Bull's execution helped convert pressure into victory."
                ),
                "category": analysis_category,
                "tags": [red_bull_tag, strategy_tag, monaco_tag],
                "related_race": races[0],
                "related_driver": drivers[0],
                "related_team": teams[0],
                "status": Article.ArticleStatus.PUBLISHED,
                "is_featured": False,
                "published_at": timezone.now(),
            },
        ]

        for data in articles_data:
            tags = data.pop("tags")

            article, _ = Article.objects.update_or_create(
                title=data["title"],
                defaults={
                    **data,
                    "author": admin,
                },
            )
            article.tags.set(tags)

        self.stdout.write("Seeded articles.")