from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.utils import get_md5_hash_password

from apps.users.models import FavoriteDriver, FavoriteRace, FavoriteTeam, UserProfile


User = get_user_model()


class AccountTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])
        try:
            user = User.objects.get(
                **{jwt_settings.USER_ID_FIELD: refresh.get(jwt_settings.USER_ID_CLAIM)}
            )
        except (User.DoesNotExist, DjangoValidationError, ValueError, TypeError):
            raise AuthenticationFailed("Invalid or expired session.") from None
        if not jwt_settings.USER_AUTHENTICATION_RULE(user) or (
            jwt_settings.CHECK_REVOKE_TOKEN
            and refresh.get(jwt_settings.REVOKE_TOKEN_CLAIM)
            != get_md5_hash_password(user.password)
        ):
            raise AuthenticationFailed("Invalid or expired session.")
        return super().validate(attrs)


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

    def get_full_name(self, obj) -> str:
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

    def validate_email(self, value):
        email = User.objects.normalize_email(value).lower()

        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )

        return email

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        user = User.objects.create_user(
            password=password,
            **validated_data,
        )

        return user


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user

        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")

        return value

    def validate(self, attrs):
        new_password = attrs["new_password"]
        new_password_confirm = attrs["new_password_confirm"]

        if new_password != new_password_confirm:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )

        validate_password(new_password, self.context["request"].user)

        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])

        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower()

    def save(self, **kwargs):
        email = self.validated_data["email"]

        users = User.objects.filter(email__iexact=email, is_active=True)

        for user in users:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            reset_url = (
                f"{settings.FRONTEND_URL}/reset-password-confirm"
                f"?uid={uid}&token={token}"
            )

            subject = "Reset your F1 account password"
            message = (
                "You requested a password reset for your F1 account.\n\n"
                f"Click the link below to reset your password:\n\n"
                f"{reset_url}\n\n"
                "If you did not request this, you can ignore this email."
            )

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        uid = attrs["uid"]
        token = attrs["token"]
        new_password = attrs["new_password"]
        new_password_confirm = attrs["new_password_confirm"]

        if new_password != new_password_confirm:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id, is_active=True)
        except (
            TypeError,
            ValueError,
            OverflowError,
            DjangoValidationError,
            User.DoesNotExist,
        ) as exc:
            raise serializers.ValidationError(
                {"token": "Invalid password reset link."}
            ) from exc

        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError(
                {"token": "Invalid or expired password reset link."}
            )

        validate_password(new_password, user)

        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])

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


class UserDashboardSerializer(serializers.Serializer):
    user = UserSerializer()
    favorites_summary = serializers.DictField(child=serializers.IntegerField())
    recent_favorite_drivers = FavoriteDriverSerializer(many=True)
    recent_favorite_teams = FavoriteTeamSerializer(many=True)
    recent_favorite_races = FavoriteRaceSerializer(many=True)
