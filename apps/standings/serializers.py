from rest_framework import serializers

from apps.standings.models import ConstructorStanding, DriverStanding


class DriverStandingSerializer(serializers.ModelSerializer):
    season_year = serializers.IntegerField(
        source="season.year",
        read_only=True,
    )

    driver_name = serializers.CharField(
        source="driver.full_name",
        read_only=True,
    )
    driver_abbreviation = serializers.CharField(
        source="driver.abbreviation",
        read_only=True,
    )
    driver_number = serializers.IntegerField(
        source="driver.number",
        read_only=True,
    )
    driver_country = serializers.CharField(
        source="driver.country",
        read_only=True,
    )

    team_name = serializers.CharField(
        source="team.name",
        read_only=True,
    )

    class Meta:
        model = DriverStanding
        fields = [
            "id",
            "season",
            "season_year",
            "driver",
            "driver_name",
            "driver_abbreviation",
            "driver_number",
            "driver_country",
            "team",
            "team_name",
            "position",
            "points",
            "wins",
            "podiums",
            "poles",
            "fastest_laps",
            "races_entered",
            "races_finished",
            "dnfs",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "season_year",
            "driver_name",
            "driver_abbreviation",
            "driver_number",
            "driver_country",
            "team_name",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        driver = attrs.get("driver", getattr(self.instance, "driver", None))
        team = attrs.get("team", getattr(self.instance, "team", None))
        points = attrs.get("points", getattr(self.instance, "points", 0))
        position = attrs.get("position", getattr(self.instance, "position", None))

        if position is not None and position < 1:
            raise serializers.ValidationError(
                {
                    "position": "Position must be greater than or equal to 1."
                }
            )

        if points < 0:
            raise serializers.ValidationError(
                {
                    "points": "Points cannot be negative."
                }
            )

        if driver and team and driver.current_team_id:
            if driver.current_team_id != team.id:
                raise serializers.ValidationError(
                    {
                        "team": "Team must match the driver's current team."
                    }
                )

        return attrs


class ConstructorStandingSerializer(serializers.ModelSerializer):
    season_year = serializers.IntegerField(
        source="season.year",
        read_only=True,
    )

    team_name = serializers.CharField(
        source="team.name",
        read_only=True,
    )
    team_country = serializers.CharField(
        source="team.country",
        read_only=True,
    )
    team_logo = serializers.ImageField(
        source="team.logo",
        read_only=True,
    )

    class Meta:
        model = ConstructorStanding
        fields = [
            "id",
            "season",
            "season_year",
            "team",
            "team_name",
            "team_country",
            "team_logo",
            "position",
            "points",
            "wins",
            "podiums",
            "poles",
            "fastest_laps",
            "races_entered",
            "double_podiums",
            "double_points_finishes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "season_year",
            "team_name",
            "team_country",
            "team_logo",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        points = attrs.get("points", getattr(self.instance, "points", 0))
        position = attrs.get("position", getattr(self.instance, "position", None))

        if position is not None and position < 1:
            raise serializers.ValidationError(
                {
                    "position": "Position must be greater than or equal to 1."
                }
            )

        if points < 0:
            raise serializers.ValidationError(
                {
                    "points": "Points cannot be negative."
                }
            )

        return attrs
