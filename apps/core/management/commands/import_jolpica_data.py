import time
from datetime import date
from decimal import Decimal, InvalidOperation

import requests
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from django.utils.dateparse import parse_date, parse_time

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


BASE_URL = "https://api.jolpi.ca/ergast/f1"


def safe_int(value):
    if value in (None, ""):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def safe_positive_int(value):
    number = safe_int(value)

    if number is None or number < 1:
        return None

    return number


def safe_decimal(value):
    if value in (None, ""):
        return Decimal("0")

    try:
        return Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        return Decimal("0")


def safe_nullable_decimal(value):
    if value in (None, ""):
        return None

    try:
        return Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        return None


def safe_date(value):
    if not value:
        return None

    return parse_date(value)


def safe_time(value):
    if not value:
        return None

    return parse_time(value.replace("Z", ""))


def build_driver_abbreviation(driver_data):
    code = driver_data.get("code")

    if code:
        return code[:3].upper()

    first_name = driver_data.get("givenName", "")
    last_name = driver_data.get("familyName", "")
    driver_id = driver_data.get("driverId", "")

    fallback = f"{first_name[:1]}{last_name[:2]}".upper()

    if len(fallback) == 3:
        return fallback

    return driver_id[:3].upper()


def map_result_status(status_text):
    if not status_text:
        return RaceResult.ResultStatus.CLASSIFIED

    normalized = status_text.lower().strip()

    if normalized == "finished":
        return RaceResult.ResultStatus.CLASSIFIED

    if "lap" in normalized:
        return RaceResult.ResultStatus.CLASSIFIED

    if normalized == "retired":
        return RaceResult.ResultStatus.RETIRED

    if normalized in {"disqualified", "excluded"}:
        return RaceResult.ResultStatus.DISQUALIFIED

    if normalized in {"did not start", "dns", "withdrew"}:
        return RaceResult.ResultStatus.DID_NOT_START

    if normalized == "not classified":
        return RaceResult.ResultStatus.NOT_CLASSIFIED

    return RaceResult.ResultStatus.DID_NOT_FINISH


def map_sprint_status(status_text):
    if not status_text:
        return SprintResult.SprintStatus.CLASSIFIED

    normalized = status_text.lower().strip()

    if normalized == "finished":
        return SprintResult.SprintStatus.CLASSIFIED

    if "lap" in normalized:
        return SprintResult.SprintStatus.CLASSIFIED

    if normalized == "retired":
        return SprintResult.SprintStatus.RETIRED

    if normalized in {"disqualified", "excluded"}:
        return SprintResult.SprintStatus.DISQUALIFIED

    if normalized in {"did not start", "dns", "withdrew"}:
        return SprintResult.SprintStatus.DID_NOT_START

    if normalized == "not classified":
        return SprintResult.SprintStatus.NOT_CLASSIFIED

    return SprintResult.SprintStatus.DID_NOT_FINISH


class JolpicaClient:
    def __init__(self, delay=0.35, timeout=25):
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()

    def get(self, path, params=None, allow_404=False):
        url = f"{BASE_URL}/{path.strip('/')}/"

        response = self.session.get(url, params=params, timeout=self.timeout)

        if allow_404 and response.status_code == 404:
            return None

        response.raise_for_status()

        time.sleep(self.delay)

        return response.json()

    def get_all(self, path, table_path, limit=100):
        results = []
        offset = 0

        while True:
            data = self.get(
                path,
                params={
                    "limit": limit,
                    "offset": offset,
                },
            )

            mr_data = data.get("MRData", {})
            total = safe_int(mr_data.get("total")) or 0

            current = mr_data

            for key in table_path.split("."):
                current = current.get(key, {})

            if not isinstance(current, list):
                break

            results.extend(current)

            offset += limit

            if offset >= total or not current:
                break

        return results


class Command(BaseCommand):
    help = "Import real Formula 1 data from Jolpica into the local database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--season",
            default="current",
            help='Season year, for example "2024", "2025", "2026", or "current".',
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.35,
            help="Delay between API requests. Default: 0.35 seconds.",
        )
        parser.add_argument(
            "--skip-results",
            action="store_true",
            help="Import only seasons, teams, drivers, circuits, races, and standings.",
        )

    def handle(self, *args, **options):
        self.season_arg = options["season"]
        self.skip_results = options["skip_results"]
        self.client = JolpicaClient(delay=options["delay"])

        self.stdout.write(self.style.WARNING("Importing Formula 1 data from Jolpica..."))

        season = self.import_season()
        self.import_teams()
        self.import_drivers()
        self.import_races(season)
        self.import_driver_standings(season)
        self.import_constructor_standings(season)

        if not self.skip_results:
            self.import_race_results(season)
            self.import_qualifying_results(season)
            self.import_sprint_results(season)

        self.stdout.write(self.style.SUCCESS("Import finished successfully."))

    def import_season(self):
        if self.season_arg == "current":
            data = self.client.get("current")
            race_table = data["MRData"]["RaceTable"]

            season_year = safe_int(race_table.get("season"))

            if not season_year:
                races = race_table.get("Races", [])

                if races:
                    season_year = safe_int(races[0].get("season"))

            if not season_year:
                season_year = date.today().year
        else:
            season_year = safe_int(self.season_arg)

        if not season_year:
            raise ValueError("Could not determine season year.")

        Season.objects.filter(is_current=True).exclude(year=season_year).update(
            is_current=False
        )

        season, _ = Season.objects.update_or_create(
            year=season_year,
            defaults={
                "name": f"{season_year} Formula 1 Season",
                "is_current": self.season_arg == "current",
            },
        )

        self.stdout.write(self.style.SUCCESS(f"Season imported: {season.year}"))

        return season

    def import_teams(self):
        constructors = self.client.get_all(
            f"{self.season_arg}/constructors",
            "ConstructorTable.Constructors",
        )

        count = 0

        for constructor in constructors:
            name = constructor.get("name")
            nationality = constructor.get("nationality", "")
            website = constructor.get("url", "")

            if not name:
                continue

            Team.objects.update_or_create(
                name=name,
                defaults={
                    "official_name": name,
                    "country": nationality,
                    "website": website,
                    "is_active": True,
                },
            )

            count += 1

        self.stdout.write(self.style.SUCCESS(f"Teams imported/updated: {count}"))

    def import_drivers(self):
        drivers = self.client.get_all(
            f"{self.season_arg}/drivers",
            "DriverTable.Drivers",
        )

        count = 0

        for driver_data in drivers:
            first_name = driver_data.get("givenName")
            last_name = driver_data.get("familyName")
            date_of_birth = safe_date(driver_data.get("dateOfBirth"))

            if not first_name or not last_name or not date_of_birth:
                continue

            abbreviation = build_driver_abbreviation(driver_data)

            driver = Driver.objects.filter(
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth,
            ).first()

            if driver is None:
                abbreviation_owner = Driver.objects.filter(
                    abbreviation=abbreviation
                ).first()

                if abbreviation_owner:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping {first_name} {last_name}: abbreviation "
                            f"{abbreviation} already belongs to {abbreviation_owner.full_name}."
                        )
                    )
                    continue

                driver = Driver(
                    first_name=first_name,
                    last_name=last_name,
                    date_of_birth=date_of_birth,
                )

            driver.abbreviation = abbreviation
            driver.number = safe_int(driver_data.get("permanentNumber"))
            driver.country = driver_data.get("nationality", "")
            driver.status = Driver.DriverStatus.ACTIVE
            driver.save()

            count += 1

        self.stdout.write(self.style.SUCCESS(f"Drivers imported/updated: {count}"))

    def import_races(self, season):
        races = self.client.get_all(
            f"{self.season_arg}/races",
            "RaceTable.Races",
        )

        count = 0

        for race_data in races:
            circuit = self.get_or_create_circuit(race_data.get("Circuit", {}))

            round_number = safe_positive_int(race_data.get("round"))
            race_name = race_data.get("raceName")
            race_date = safe_date(race_data.get("date"))
            race_time = safe_time(race_data.get("time"))

            if not circuit or not round_number or not race_name or not race_date:
                continue

            qualifying = race_data.get("Qualifying") or {}
            sprint = race_data.get("Sprint") or {}

            status = (
                Race.RaceStatus.COMPLETED
                if race_date < date.today()
                else Race.RaceStatus.SCHEDULED
            )

            race = Race.objects.filter(
                season=season,
                name=race_name,
            ).first()

            if race is None:
                race = Race.objects.filter(
                    season=season,
                    round_number=round_number,
                ).first()

            if race is None:
                race = Race(
                    season=season,
                    name=race_name,
                )

            race.circuit = circuit
            race.name = race_name
            race.official_name = race_name
            race.round_number = round_number
            race.race_date = race_date
            race.race_time = race_time
            race.qualifying_date = safe_date(qualifying.get("date"))
            race.qualifying_time = safe_time(qualifying.get("time"))
            race.sprint_date = safe_date(sprint.get("date"))
            race.sprint_time = safe_time(sprint.get("time"))
            race.status = status
            race.save()

            count += 1

        self.stdout.write(self.style.SUCCESS(f"Races imported/updated: {count}"))

    def get_or_create_circuit(self, circuit_data):
        if not circuit_data:
            return None

        location = circuit_data.get("Location", {})

        name = circuit_data.get("circuitName")
        country = location.get("country", "")
        city = location.get("locality", "")

        if not name or not country:
            return None

        circuit, _ = Circuit.objects.update_or_create(
            name=name,
            country=country,
            defaults={
                "official_name": name,
                "city": city,
                "latitude": safe_nullable_decimal(location.get("lat")),
                "longitude": safe_nullable_decimal(location.get("long")),
            },
        )

        return circuit

    def import_driver_standings(self, season):
        data = self.client.get(f"{self.season_arg}/driverstandings")

        standings_lists = (
            data.get("MRData", {})
            .get("StandingsTable", {})
            .get("StandingsLists", [])
        )

        if not standings_lists:
            self.stdout.write(self.style.WARNING("No driver standings found."))
            return

        DriverStanding.objects.filter(season=season).delete()

        standings = standings_lists[0].get("DriverStandings", [])

        count = 0

        for standing_data in standings:
            driver = self.find_driver(standing_data.get("Driver", {}))

            constructors = standing_data.get("Constructors", [])
            team = self.find_team(constructors[0] if constructors else {})

            if not driver:
                continue

            if team:
                driver.current_team = team
                driver.status = Driver.DriverStatus.ACTIVE
                driver.save(update_fields=["current_team", "status", "updated_at"])

            DriverStanding.objects.create(
                season=season,
                driver=driver,
                team=team,
                position=safe_positive_int(standing_data.get("position")) or 1,
                points=safe_decimal(standing_data.get("points")),
                wins=safe_int(standing_data.get("wins")) or 0,
            )

            count += 1

        self.stdout.write(self.style.SUCCESS(f"Driver standings imported: {count}"))

    def import_constructor_standings(self, season):
        data = self.client.get(f"{self.season_arg}/constructorstandings")

        standings_lists = (
            data.get("MRData", {})
            .get("StandingsTable", {})
            .get("StandingsLists", [])
        )

        if not standings_lists:
            self.stdout.write(self.style.WARNING("No constructor standings found."))
            return

        ConstructorStanding.objects.filter(season=season).delete()

        standings = standings_lists[0].get("ConstructorStandings", [])

        count = 0

        for standing_data in standings:
            team = self.find_team(standing_data.get("Constructor", {}))

            if not team:
                continue

            ConstructorStanding.objects.create(
                season=season,
                team=team,
                position=safe_positive_int(standing_data.get("position")) or 1,
                points=safe_decimal(standing_data.get("points")),
                wins=safe_int(standing_data.get("wins")) or 0,
            )

            count += 1

        self.stdout.write(self.style.SUCCESS(f"Constructor standings imported: {count}"))

    def import_race_results(self, season):
        races = Race.objects.filter(season=season).order_by("round_number")

        total_count = 0

        for race in races:
            data = self.client.get(
                f"{season.year}/{race.round_number}/results",
                allow_404=True,
            )

            race_items = (
                data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
                if data
                else []
            )

            if not race_items:
                continue

            results = race_items[0].get("Results", [])

            if not results:
                continue

            RaceResult.objects.filter(race=race).delete()

            for result_data in results:
                driver = self.find_driver(result_data.get("Driver", {}))
                team = self.find_team(result_data.get("Constructor", {}))

                if not driver or not team:
                    continue

                if driver.current_team_id is None:
                    driver.current_team = team
                    driver.save(update_fields=["current_team", "updated_at"])

                time_data = result_data.get("Time", {})
                fastest_lap_data = result_data.get("FastestLap", {})
                fastest_lap_time = fastest_lap_data.get("Time", {})

                position = safe_positive_int(result_data.get("position"))
                grid_position = safe_positive_int(result_data.get("grid"))
                fastest_lap_rank = safe_positive_int(fastest_lap_data.get("rank"))

                try:
                    RaceResult.objects.create(
                        race=race,
                        driver=driver,
                        team=team,
                        position=position,
                        classified_position=result_data.get("positionText", ""),
                        grid_position=grid_position,
                        laps_completed=safe_int(result_data.get("laps")) or 0,
                        time=time_data.get("time", ""),
                        fastest_lap=fastest_lap_rank == 1,
                        fastest_lap_time=fastest_lap_time.get("time", ""),
                        fastest_lap_rank=fastest_lap_rank,
                        points=safe_decimal(result_data.get("points")),
                        status=map_result_status(result_data.get("status")),
                    )
                    total_count += 1
                except (IntegrityError, ValueError) as exc:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipped race result for {driver.full_name} "
                            f"in {race.name}: {exc}"
                        )
                    )

        self.stdout.write(self.style.SUCCESS(f"Race results imported: {total_count}"))

    def import_qualifying_results(self, season):
        races = Race.objects.filter(season=season).order_by("round_number")

        total_count = 0

        for race in races:
            data = self.client.get(
                f"{season.year}/{race.round_number}/qualifying",
                allow_404=True,
            )

            race_items = (
                data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
                if data
                else []
            )

            if not race_items:
                continue

            results = race_items[0].get("QualifyingResults", [])

            if not results:
                continue

            QualifyingResult.objects.filter(race=race).delete()

            for result_data in results:
                driver = self.find_driver(result_data.get("Driver", {}))
                team = self.find_team(result_data.get("Constructor", {}))

                if not driver or not team:
                    continue

                if driver.current_team_id is None:
                    driver.current_team = team
                    driver.save(update_fields=["current_team", "updated_at"])

                position = safe_positive_int(result_data.get("position"))

                try:
                    QualifyingResult.objects.create(
                        race=race,
                        driver=driver,
                        team=team,
                        position=position,
                        q1_time=result_data.get("Q1", ""),
                        q2_time=result_data.get("Q2", ""),
                        q3_time=result_data.get("Q3", ""),
                    )
                    total_count += 1
                except (IntegrityError, ValueError) as exc:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipped qualifying result for {driver.full_name} "
                            f"in {race.name}: {exc}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(f"Qualifying results imported: {total_count}")
        )

    def import_sprint_results(self, season):
        races = Race.objects.filter(season=season).order_by("round_number")

        total_count = 0

        for race in races:
            data = self.client.get(
                f"{season.year}/{race.round_number}/sprint",
                allow_404=True,
            )

            race_items = (
                data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
                if data
                else []
            )

            if not race_items:
                continue

            results = race_items[0].get("SprintResults", [])

            if not results:
                continue

            SprintResult.objects.filter(race=race).delete()

            for result_data in results:
                driver = self.find_driver(result_data.get("Driver", {}))
                team = self.find_team(result_data.get("Constructor", {}))

                if not driver or not team:
                    continue

                if driver.current_team_id is None:
                    driver.current_team = team
                    driver.save(update_fields=["current_team", "updated_at"])

                time_data = result_data.get("Time", {})

                position = safe_positive_int(result_data.get("position"))
                grid_position = safe_positive_int(result_data.get("grid"))

                try:
                    SprintResult.objects.create(
                        race=race,
                        driver=driver,
                        team=team,
                        position=position,
                        grid_position=grid_position,
                        laps_completed=safe_int(result_data.get("laps")) or 0,
                        time=time_data.get("time", ""),
                        points=safe_decimal(result_data.get("points")),
                        status=map_sprint_status(result_data.get("status")),
                    )
                    total_count += 1
                except (IntegrityError, ValueError) as exc:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipped sprint result for {driver.full_name} "
                            f"in {race.name}: {exc}"
                        )
                    )

        self.stdout.write(self.style.SUCCESS(f"Sprint results imported: {total_count}"))

    def find_driver(self, driver_data):
        if not driver_data:
            return None

        first_name = driver_data.get("givenName")
        last_name = driver_data.get("familyName")
        date_of_birth = safe_date(driver_data.get("dateOfBirth"))

        if not first_name or not last_name or not date_of_birth:
            return None

        return Driver.objects.filter(
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
        ).first()

    def find_team(self, constructor_data):
        if not constructor_data:
            return None

        name = constructor_data.get("name")

        if not name:
            return None

        return Team.objects.filter(name=name).first()
