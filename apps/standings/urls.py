from django.urls import path

from apps.standings.views import (
    ConstructorStandingDetailAPIView,
    ConstructorStandingListCreateAPIView,
    DriverStandingDetailAPIView,
    DriverStandingListCreateAPIView,
)


app_name = "standings"

urlpatterns = [
    path(
        "drivers/",
        DriverStandingListCreateAPIView.as_view(),
        name="driver-standing-list-create",
    ),
    path(
        "drivers/<uuid:pk>/",
        DriverStandingDetailAPIView.as_view(),
        name="driver-standing-detail",
    ),
    path(
        "constructors/",
        ConstructorStandingListCreateAPIView.as_view(),
        name="constructor-standing-list-create",
    ),
    path(
        "constructors/<uuid:pk>/",
        ConstructorStandingDetailAPIView.as_view(),
        name="constructor-standing-detail",
    ),
]
