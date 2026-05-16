from apps.core.views import BaseListCreateAPIView, BaseRetrieveUpdateDestroyAPIView
from apps.standings.models import ConstructorStanding, DriverStanding
from apps.standings.serializers import (
    ConstructorStandingSerializer,
    DriverStandingSerializer,
)


class DriverStandingListCreateAPIView(BaseListCreateAPIView):
    model = DriverStanding
    serializer_class = DriverStandingSerializer
    filterset_fields = [
        "season",
        "season__year",
        "driver",
        "team",
        "position",
    ]
    search_fields = [
        "driver__first_name",
        "driver__last_name",
        "driver__abbreviation",
        "driver__country",
        "team__name",
    ]
    ordering_fields = [
        "season__year",
        "position",
        "points",
        "wins",
        "podiums",
        "created_at",
    ]
    ordering = [
        "season__year",
        "position",
    ]

    def get_queryset(self):
        return super().get_queryset().select_related(
            "season",
            "driver",
            "team",
        )


class DriverStandingDetailAPIView(BaseRetrieveUpdateDestroyAPIView):
    model = DriverStanding
    serializer_class = DriverStandingSerializer

    def get_queryset(self):
        return super().get_queryset().select_related(
            "season",
            "driver",
            "team",
        )


class ConstructorStandingListCreateAPIView(BaseListCreateAPIView):
    model = ConstructorStanding
    serializer_class = ConstructorStandingSerializer
    filterset_fields = [
        "season",
        "season__year",
        "team",
        "position",
    ]
    search_fields = [
        "team__name",
        "team__official_name",
        "team__country",
    ]
    ordering_fields = [
        "season__year",
        "position",
        "points",
        "wins",
        "podiums",
        "created_at",
    ]
    ordering = [
        "season__year",
        "position",
    ]

    def get_queryset(self):
        return super().get_queryset().select_related(
            "season",
            "team",
        )


class ConstructorStandingDetailAPIView(BaseRetrieveUpdateDestroyAPIView):
    model = ConstructorStanding
    serializer_class = ConstructorStandingSerializer

    def get_queryset(self):
        return super().get_queryset().select_related(
            "season",
            "team",
        )
