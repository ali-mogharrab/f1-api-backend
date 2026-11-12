from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.responses import error_response, success_response
from apps.core.schema import SuccessResponseSerializer, success_schema
from apps.users.models import FavoriteDriver, FavoriteRace, FavoriteTeam
from apps.users.throttles import (
    LoginThrottle,
    PasswordResetThrottle,
    RefreshThrottle,
    RegistrationThrottle,
)
from apps.users.serializers import (
    FavoriteDriverSerializer,
    FavoriteRaceSerializer,
    FavoriteTeamSerializer,
    RegisterSerializer,
    UserProfileSerializer,
    UserSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserDashboardSerializer,
)


class LoginView(TokenObtainPairView):
    throttle_classes = [LoginThrottle]


class RefreshView(TokenRefreshView):
    throttle_classes = [RefreshThrottle]


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [RegistrationThrottle]

    @extend_schema(
        tags=["users"],
        summary="Register a new user",
        description="Create a new user account. A user profile is created automatically.",
        request=RegisterSerializer,
        responses={201: success_schema(UserSerializer)},
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()
            except IntegrityError:
                return error_response(
                    errors={
                        "non_field_errors": [
                            "An account with this username or email already exists."
                        ]
                    },
                    message="Validation error.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            return success_response(
                data=UserSerializer(user, context={"request": request}).data,
                message="User registered successfully.",
                status_code=status.HTTP_201_CREATED,
            )

        return error_response(
            errors=serializer.errors,
            message="Validation error.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema_view(
    post=extend_schema(
        request=PasswordChangeSerializer, responses={200: SuccessResponseSerializer}
    )
)
class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return success_response(
            message="Password changed successfully.",
            data=None,
        )


@extend_schema_view(
    post=extend_schema(
        request=PasswordResetRequestSerializer,
        responses={200: SuccessResponseSerializer},
    )
)
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return success_response(
            message=(
                "If an account with this email exists, "
                "a password reset link has been sent."
            ),
            data=None,
        )


@extend_schema_view(
    post=extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={200: SuccessResponseSerializer},
    )
)
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return success_response(
            message="Password has been reset successfully.",
            data=None,
        )


class CurrentUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["users"],
        summary="Get current authenticated user",
        description="Return the currently authenticated user's account and profile information.",
        responses={200: success_schema(UserSerializer)},
    )
    def get(self, request):
        serializer = UserSerializer(
            request.user,
            context={"request": request},
        )

        return success_response(
            data=serializer.data,
            message="Current user retrieved successfully.",
            status_code=status.HTTP_200_OK,
        )


class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["users"],
        summary="Get current user's profile",
        responses={200: success_schema(UserProfileSerializer)},
    )
    def get(self, request):
        serializer = UserProfileSerializer(
            request.user.profile,
            context={"request": request},
        )

        return success_response(
            data=serializer.data,
            message="Profile retrieved successfully.",
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["users"],
        summary="Update current user's profile",
        request=UserProfileSerializer,
        responses={200: success_schema(UserProfileSerializer)},
    )
    def patch(self, request):
        serializer = UserProfileSerializer(
            request.user.profile,
            data=request.data,
            partial=True,
            context={"request": request},
        )

        if serializer.is_valid():
            serializer.save()

            return success_response(
                data=serializer.data,
                message="Profile updated successfully.",
                status_code=status.HTTP_200_OK,
            )

        return error_response(
            errors=serializer.errors,
            message="Validation error.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema_view(
    get=extend_schema(
        responses={200: success_schema(FavoriteDriverSerializer, many=True)}
    ),
    post=extend_schema(
        request=FavoriteDriverSerializer,
        responses={201: success_schema(FavoriteDriverSerializer)},
    ),
)
class FavoriteDriverListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FavoriteDriver.objects.filter(
            user=self.request.user,
        ).select_related(
            "driver",
            "driver__current_team",
        )

    def get(self, request):
        serializer = FavoriteDriverSerializer(
            self.get_queryset(),
            many=True,
            context={"request": request},
        )

        return success_response(
            data=serializer.data,
            message="Favorite drivers retrieved successfully.",
            status_code=status.HTTP_200_OK,
        )

    def post(self, request):
        serializer = FavoriteDriverSerializer(
            data=request.data,
            context={"request": request},
        )

        if serializer.is_valid():
            try:
                serializer.save(user=request.user)
            except IntegrityError:
                return error_response(
                    errors={"driver": ["This driver is already in your favorites."]},
                    message="Validation error.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            return success_response(
                data=serializer.data,
                message="Favorite driver added successfully.",
                status_code=status.HTTP_201_CREATED,
            )

        return error_response(
            errors=serializer.errors,
            message="Validation error.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema_view(delete=extend_schema(responses={200: SuccessResponseSerializer}))
class FavoriteDriverDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        favorite = FavoriteDriver.objects.filter(
            pk=pk,
            user=request.user,
        ).first()

        if favorite is None:
            return error_response(
                errors=None,
                message="Favorite driver not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        favorite.delete()

        return success_response(
            data=None,
            message="Favorite driver removed successfully.",
            status_code=status.HTTP_200_OK,
        )


@extend_schema_view(
    get=extend_schema(
        responses={200: success_schema(FavoriteTeamSerializer, many=True)}
    ),
    post=extend_schema(
        request=FavoriteTeamSerializer,
        responses={201: success_schema(FavoriteTeamSerializer)},
    ),
)
class FavoriteTeamListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FavoriteTeam.objects.filter(
            user=self.request.user,
        ).select_related("team")

    def get(self, request):
        serializer = FavoriteTeamSerializer(
            self.get_queryset(),
            many=True,
            context={"request": request},
        )

        return success_response(
            data=serializer.data,
            message="Favorite teams retrieved successfully.",
            status_code=status.HTTP_200_OK,
        )

    def post(self, request):
        serializer = FavoriteTeamSerializer(
            data=request.data,
            context={"request": request},
        )

        if serializer.is_valid():
            try:
                serializer.save(user=request.user)
            except IntegrityError:
                return error_response(
                    errors={"team": ["This team is already in your favorites."]},
                    message="Validation error.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            return success_response(
                data=serializer.data,
                message="Favorite team added successfully.",
                status_code=status.HTTP_201_CREATED,
            )

        return error_response(
            errors=serializer.errors,
            message="Validation error.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema_view(delete=extend_schema(responses={200: SuccessResponseSerializer}))
class FavoriteTeamDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        favorite = FavoriteTeam.objects.filter(
            pk=pk,
            user=request.user,
        ).first()

        if favorite is None:
            return error_response(
                errors=None,
                message="Favorite team not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        favorite.delete()

        return success_response(
            data=None,
            message="Favorite team removed successfully.",
            status_code=status.HTTP_200_OK,
        )


@extend_schema_view(
    get=extend_schema(
        responses={200: success_schema(FavoriteRaceSerializer, many=True)}
    ),
    post=extend_schema(
        request=FavoriteRaceSerializer,
        responses={201: success_schema(FavoriteRaceSerializer)},
    ),
)
class FavoriteRaceListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FavoriteRace.objects.filter(
            user=self.request.user,
        ).select_related(
            "race",
            "race__season",
            "race__circuit",
        )

    def get(self, request):
        serializer = FavoriteRaceSerializer(
            self.get_queryset(),
            many=True,
            context={"request": request},
        )

        return success_response(
            data=serializer.data,
            message="Favorite races retrieved successfully.",
            status_code=status.HTTP_200_OK,
        )

    def post(self, request):
        serializer = FavoriteRaceSerializer(
            data=request.data,
            context={"request": request},
        )

        if serializer.is_valid():
            try:
                serializer.save(user=request.user)
            except IntegrityError:
                return error_response(
                    errors={"race": ["This race is already in your favorites."]},
                    message="Validation error.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            return success_response(
                data=serializer.data,
                message="Favorite race added successfully.",
                status_code=status.HTTP_201_CREATED,
            )

        return error_response(
            errors=serializer.errors,
            message="Validation error.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema_view(delete=extend_schema(responses={200: SuccessResponseSerializer}))
class FavoriteRaceDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        favorite = FavoriteRace.objects.filter(
            pk=pk,
            user=request.user,
        ).first()

        if favorite is None:
            return error_response(
                errors=None,
                message="Favorite race not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        favorite.delete()

        return success_response(
            data=None,
            message="Favorite race removed successfully.",
            status_code=status.HTTP_200_OK,
        )


@extend_schema_view(
    get=extend_schema(responses={200: success_schema(UserDashboardSerializer)})
)
class UserDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        favorite_drivers = (
            FavoriteDriver.objects.filter(user=request.user)
            .select_related("driver", "driver__current_team")
            .order_by("-created_at")
        )

        favorite_teams = (
            FavoriteTeam.objects.filter(user=request.user)
            .select_related("team")
            .order_by("-created_at")
        )

        favorite_races = (
            FavoriteRace.objects.filter(user=request.user)
            .select_related("race", "race__season", "race__circuit")
            .order_by("-created_at")
        )

        data = {
            "user": UserSerializer(
                request.user,
                context={"request": request},
            ).data,
            "favorites_summary": {
                "drivers_count": favorite_drivers.count(),
                "teams_count": favorite_teams.count(),
                "races_count": favorite_races.count(),
            },
            "recent_favorite_drivers": FavoriteDriverSerializer(
                favorite_drivers[:5],
                many=True,
                context={"request": request},
            ).data,
            "recent_favorite_teams": FavoriteTeamSerializer(
                favorite_teams[:5],
                many=True,
                context={"request": request},
            ).data,
            "recent_favorite_races": FavoriteRaceSerializer(
                favorite_races[:5],
                many=True,
                context={"request": request},
            ).data,
        }

        return success_response(
            data=data,
            message="Dashboard retrieved successfully.",
            status_code=status.HTTP_200_OK,
        )
