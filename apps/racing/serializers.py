from rest_framework import serializers

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

def validate_driver_team_match(driver, team):
    if driver and team and driver.current_team_id:
        if driver.current_team_id != team.id:
            raise serializers.ValidationError(
                {
                    "team": "Team must match the driver's current team."
                }
            )

class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Season
        fields = [
            "id",
            "year",
            "name",
            "is_current",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "official_name",
            "country",
            "base_location",
            "team_principal",
            "technical_chief",
            "chassis",
            "power_unit",
            "first_team_entry",
            "world_championships",
            "website",
            "logo",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DriverSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    current_team_name = serializers.CharField(
        source="current_team.name",
        read_only=True,
    )

    class Meta:
        model = Driver
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "abbreviation",
            "number",
            "country",
            "date_of_birth",
            "place_of_birth",
            "status",
            "current_team",
            "current_team_name",
            "image",
            "biography",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "full_name",
            "current_team_name",
            "created_at",
            "updated_at",
        ]


class CircuitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Circuit
        fields = [
            "id",
            "name",
            "official_name",
            "country",
            "city",
            "length_km",
            "number_of_laps",
            "race_distance_km",
            "lap_record",
            "lap_record_driver",
            "lap_record_year",
            "latitude",
            "longitude",
            "image",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RaceSerializer(serializers.ModelSerializer):
    season_year = serializers.IntegerField(
        source="season.year",
        read_only=True,
    )
    circuit_name = serializers.CharField(
        source="circuit.name",
        read_only=True,
    )
    circuit_country = serializers.CharField(
        source="circuit.country",
        read_only=True,
    )

    class Meta:
        model = Race
        fields = [
            "id",
            "season",
            "season_year",
            "circuit",
            "circuit_name",
            "circuit_country",
            "name",
            "official_name",
            "round_number",
            "race_date",
            "race_time",
            "qualifying_date",
            "qualifying_time",
            "sprint_date",
            "sprint_time",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "season_year",
            "circuit_name",
            "circuit_country",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        race_date = attrs.get("race_date", getattr(self.instance, "race_date", None))
        qualifying_date = attrs.get(
            "qualifying_date",
            getattr(self.instance, "qualifying_date", None),
        )
        sprint_date = attrs.get(
            "sprint_date",
            getattr(self.instance, "sprint_date", None),
        )

        if qualifying_date and race_date and qualifying_date > race_date:
            raise serializers.ValidationError(
                {
                    "qualifying_date": "Qualifying date cannot be after race date."
                }
            )

        if sprint_date and race_date and sprint_date > race_date:
            raise serializers.ValidationError(
                {
                    "sprint_date": "Sprint date cannot be after race date."
                }
            )

        return attrs


class RaceResultSerializer(serializers.ModelSerializer):
    race_name = serializers.CharField(source="race.name", read_only=True)
    season_year = serializers.IntegerField(source="race.season.year", read_only=True)
    round_number = serializers.IntegerField(source="race.round_number", read_only=True)

    driver_name = serializers.CharField(source="driver.full_name", read_only=True)
    driver_abbreviation = serializers.CharField(
        source="driver.abbreviation",
        read_only=True,
    )

    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta:
        model = RaceResult
        fields = [
            "id",
            "race",
            "race_name",
            "season_year",
            "round_number",
            "driver",
            "driver_name",
            "driver_abbreviation",
            "team",
            "team_name",
            "position",
            "classified_position",
            "grid_position",
            "laps_completed",
            "time",
            "fastest_lap",
            "fastest_lap_time",
            "fastest_lap_rank",
            "points",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "race_name",
            "season_year",
            "round_number",
            "driver_name",
            "driver_abbreviation",
            "team_name",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        driver = attrs.get("driver", getattr(self.instance, "driver", None))
        team = attrs.get("team", getattr(self.instance, "team", None))
        points = attrs.get("points", getattr(self.instance, "points", 0))

        validate_driver_team_match(driver, team)

        if points < 0:
            raise serializers.ValidationError(
                {
                    "points": "Points cannot be negative."
                }
            )

        return attrs


class QualifyingResultSerializer(serializers.ModelSerializer):
    race_name = serializers.CharField(source="race.name", read_only=True)
    season_year = serializers.IntegerField(source="race.season.year", read_only=True)
    round_number = serializers.IntegerField(source="race.round_number", read_only=True)

    driver_name = serializers.CharField(source="driver.full_name", read_only=True)
    driver_abbreviation = serializers.CharField(
        source="driver.abbreviation",
        read_only=True,
    )

    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta:
        model = QualifyingResult
        fields = [
            "id",
            "race",
            "race_name",
            "season_year",
            "round_number",
            "driver",
            "driver_name",
            "driver_abbreviation",
            "team",
            "team_name",
            "position",
            "q1_time",
            "q2_time",
            "q3_time",
            "laps_completed",
            "penalty",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "race_name",
            "season_year",
            "round_number",
            "driver_name",
            "driver_abbreviation",
            "team_name",
            "created_at",
            "updated_at",
        ]


class SprintResultSerializer(serializers.ModelSerializer):
    race_name = serializers.CharField(source="race.name", read_only=True)
    season_year = serializers.IntegerField(source="race.season.year", read_only=True)
    round_number = serializers.IntegerField(source="race.round_number", read_only=True)

    driver_name = serializers.CharField(source="driver.full_name", read_only=True)
    driver_abbreviation = serializers.CharField(
        source="driver.abbreviation",
        read_only=True,
    )

    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta:
        model = SprintResult
        fields = [
            "id",
            "race",
            "race_name",
            "season_year",
            "round_number",
            "driver",
            "driver_name",
            "driver_abbreviation",
            "team",
            "team_name",
            "position",
            "grid_position",
            "laps_completed",
            "time",
            "points",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "race_name",
            "season_year",
            "round_number",
            "driver_name",
            "driver_abbreviation",
            "team_name",
            "created_at",
            "updated_at",
        ]
