from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.users.models import FavoriteDriver, FavoriteRace, FavoriteTeam, UserProfile


User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "id",
            "bio",
            "avatar",
            "country",
            "favorite_driver_name",
            "favorite_team_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "is_staff",
            "date_joined",
            "profile",
        ]
        read_only_fields = [
            "id",
            "is_staff",
            "date_joined",
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "password_confirm",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        user = User.objects.create_user(
            password=password,
            **validated_data,
        )

        return user


class FavoriteDriverSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source="driver.full_name", read_only=True)
    driver_abbreviation = serializers.CharField(
        source="driver.abbreviation",
        read_only=True,
    )
    driver_country = serializers.CharField(source="driver.country", read_only=True)
    current_team_name = serializers.CharField(
        source="driver.current_team.name",
        read_only=True,
    )

    class Meta:
        model = FavoriteDriver
        fields = [
            "id",
            "driver",
            "driver_name",
            "driver_abbreviation",
            "driver_country",
            "current_team_name",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "driver_name",
            "driver_abbreviation",
            "driver_country",
            "current_team_name",
            "created_at",
        ]

    def validate_driver(self, driver):
        request = self.context.get("request")

        if request and request.user.is_authenticated:
            exists = FavoriteDriver.objects.filter(
                user=request.user,
                driver=driver,
            ).exists()

            if exists:
                raise serializers.ValidationError(
                    "This driver is already in your favorites."
                )

        return driver


class FavoriteTeamSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)
    team_country = serializers.CharField(source="team.country", read_only=True)
    team_logo = serializers.ImageField(source="team.logo", read_only=True)

    class Meta:
        model = FavoriteTeam
        fields = [
            "id",
            "team",
            "team_name",
            "team_country",
            "team_logo",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "team_name",
            "team_country",
            "team_logo",
            "created_at",
        ]

    def validate_team(self, team):
        request = self.context.get("request")

        if request and request.user.is_authenticated:
            exists = FavoriteTeam.objects.filter(
                user=request.user,
                team=team,
            ).exists()

            if exists:
                raise serializers.ValidationError(
                    "This team is already in your favorites."
                )

        return team


class FavoriteRaceSerializer(serializers.ModelSerializer):
    race_name = serializers.CharField(source="race.name", read_only=True)
    season_year = serializers.IntegerField(source="race.season.year", read_only=True)
    round_number = serializers.IntegerField(source="race.round_number", read_only=True)
    circuit_name = serializers.CharField(source="race.circuit.name", read_only=True)
    race_date = serializers.DateField(source="race.race_date", read_only=True)

    class Meta:
        model = FavoriteRace
        fields = [
            "id",
            "race",
            "race_name",
            "season_year",
            "round_number",
            "circuit_name",
            "race_date",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "race_name",
            "season_year",
            "round_number",
            "circuit_name",
            "race_date",
            "created_at",
        ]

    def validate_race(self, race):
        request = self.context.get("request")

        if request and request.user.is_authenticated:
            exists = FavoriteRace.objects.filter(
                user=request.user,
                race=race,
            ).exists()

            if exists:
                raise serializers.ValidationError(
                    "This race is already in your favorites."
                )

        return race
