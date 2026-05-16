from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from apps.users.views import (
    CurrentUserAPIView,
    FavoriteDriverDetailAPIView,
    FavoriteDriverListCreateAPIView,
    FavoriteRaceDetailAPIView,
    FavoriteRaceListCreateAPIView,
    FavoriteTeamDetailAPIView,
    FavoriteTeamListCreateAPIView,
    RegisterAPIView,
    UserDashboardAPIView,
    UserProfileAPIView,
)


app_name = "users"

urlpatterns = [
    path(
        "register/",
        RegisterAPIView.as_view(),
        name="register",
    ),
    path(
        "me/",
        CurrentUserAPIView.as_view(),
        name="current-user",
    ),
    path(
        "profile/",
        UserProfileAPIView.as_view(),
        name="profile",
    ),
    path(
        "dashboard/",
        UserDashboardAPIView.as_view(),
        name="dashboard",
    ),
    path(
        "favorites/drivers/",
        FavoriteDriverListCreateAPIView.as_view(),
        name="favorite-driver-list-create",
    ),
    path(
        "favorites/drivers/<uuid:pk>/",
        FavoriteDriverDetailAPIView.as_view(),
        name="favorite-driver-detail",
    ),
    path(
        "favorites/teams/",
        FavoriteTeamListCreateAPIView.as_view(),
        name="favorite-team-list-create",
    ),
    path(
        "favorites/teams/<uuid:pk>/",
        FavoriteTeamDetailAPIView.as_view(),
        name="favorite-team-detail",
    ),
    path(
        "favorites/races/",
        FavoriteRaceListCreateAPIView.as_view(),
        name="favorite-race-list-create",
    ),
    path(
        "favorites/races/<uuid:pk>/",
        FavoriteRaceDetailAPIView.as_view(),
        name="favorite-race-detail",
    ),
    path(
        "token/",
        TokenObtainPairView.as_view(),
        name="token-obtain-pair",
    ),
    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),
    path(
        "token/verify/",
        TokenVerifyView.as_view(),
        name="token-verify",
    ),
]
