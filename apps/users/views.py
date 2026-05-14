from django.db import IntegrityError
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import error_response, success_response
from apps.users.models import FavoriteDriver, FavoriteRace, FavoriteTeam
from apps.users.serializers import (
    FavoriteDriverSerializer,
    FavoriteRaceSerializer,
    FavoriteTeamSerializer,
    RegisterSerializer,
    UserProfileSerializer,
    UserSerializer,
)


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

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


class CurrentUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

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
