from apps.core.views import BaseListCreateAPIView, BaseRetrieveUpdateDestroyAPIView

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
from apps.racing.serializers import (
    CircuitSerializer,
    DriverSerializer,
    QualifyingResultSerializer,
    RaceResultSerializer,
    RaceSerializer,
    SeasonSerializer,
    SprintResultSerializer,
    TeamSerializer,
)


class SeasonListCreateAPIView(BaseListCreateAPIView):
    model = Season
    serializer_class = SeasonSerializer
    filterset_fields = ["is_current"]
    search_fields = ["name"]
    ordering_fields = ["year", "created_at"]
    ordering = ["-year"]


class SeasonDetailAPIView(BaseRetrieveUpdateDestroyAPIView):
    model = Season
    serializer_class = SeasonSerializer


class TeamListCreateAPIView(BaseListCreateAPIView):
    model = Team
    serializer_class = TeamSerializer
    filterset_fields = ["country", "is_active", "power_unit"]
    search_fields = [
        "name",
        "official_name",
        "country",
        "team_principal",
        "power_unit",
    ]
    ordering_fields = [
        "name",
        "country",
        "first_team_entry",
        "world_championships",
        "created_at",
    ]
    ordering = ["name"]


class TeamDetailAPIView(BaseRetrieveUpdateDestroyAPIView):
    model = Team
    serializer_class = TeamSerializer


class DriverListCreateAPIView(BaseListCreateAPIView):
    model = Driver
    serializer_class = DriverSerializer
    filterset_fields = [
        "status",
        "country",
        "current_team",
    ]
    search_fields = [
        "first_name",
        "last_name",
        "abbreviation",
        "country",
        "current_team__name",
    ]
    ordering_fields = [
        "first_name",
        "last_name",
        "number",
        "country",
        "created_at",
    ]
    ordering = ["last_name", "first_name"]

    def get_queryset(self):
        return super().get_queryset().select_related("current_team")


class DriverDetailAPIView(BaseRetrieveUpdateDestroyAPIView):
    model = Driver
    serializer_class = DriverSerializer
    
    def get_queryset(self):
        return super().get_queryset().select_related("current_team")


class CircuitListCreateAPIView(BaseListCreateAPIView):
    model = Circuit
    serializer_class = CircuitSerializer
    filterset_fields = ["country", "city"]
    search_fields = [
        "name",
        "official_name",
        "country",
        "city",
    ]
    ordering_fields = [
        "name",
        "country",
        "length_km",
        "created_at",
    ]
    ordering = ["name"]


class CircuitDetailAPIView(BaseRetrieveUpdateDestroyAPIView):
    model = Circuit
    serializer_class = CircuitSerializer


class RaceListCreateAPIView(BaseListCreateAPIView):
    model = Race
    serializer_class = RaceSerializer
    filterset_fields = [
        "season",
        "season__year",
        "circuit",
        "circuit__country",
        "status",
    ]
    search_fields = [
        "name",
        "official_name",
        "circuit__name",
        "circuit__country",
    ]
    ordering_fields = [
        "season__year",
        "round_number",
        "race_date",
        "created_at",
    ]
    ordering = ["season__year", "round_number"]

    def get_queryset(self):
        return super().get_queryset().select_related(
            "season",
            "circuit",
        )


class RaceDetailAPIView(BaseRetrieveUpdateDestroyAPIView):
    model = Race
    serializer_class = RaceSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("season", "circuit")


class RaceResultListCreateAPIView(BaseListCreateAPIView):
    model = RaceResult
    serializer_class = RaceResultSerializer
    filterset_fields = [
        "race",
        "race__season",
        "race__season__year",
        "driver",
        "team",
        "position",
        "status",
        "fastest_lap",
    ]
    search_fields = [
        "race__name",
        "driver__first_name",
        "driver__last_name",
        "driver__abbreviation",
        "team__name",
    ]
    ordering_fields = [
        "race__season__year",
        "race__round_number",
        "position",
        "grid_position",
        "points",
        "created_at",
    ]
    ordering = [
        "race__season__year",
        "race__round_number",
        "position",
    ]

    def get_queryset(self):
        return super().get_queryset().select_related(
            "race",
            "race__season",
            "driver",
            "team",
        )


class RaceResultDetailAPIView(BaseRetrieveUpdateDestroyAPIView):
    model = RaceResult
    serializer_class = RaceResultSerializer

    def get_queryset(self):
        return super().get_queryset().select_related(
            "race",
            "race__season",
            "driver",
            "team",
        )


class QualifyingResultListCreateAPIView(BaseListCreateAPIView):
    model = QualifyingResult
    serializer_class = QualifyingResultSerializer
    filterset_fields = [
        "race",
        "race__season",
        "race__season__year",
        "driver",
        "team",
        "position",
    ]
    search_fields = [
        "race__name",
        "driver__first_name",
        "driver__last_name",
        "driver__abbreviation",
        "team__name",
    ]
    ordering_fields = [
        "race__season__year",
        "race__round_number",
        "position",
        "created_at",
    ]
    ordering = [
        "race__season__year",
        "race__round_number",
        "position",
    ]

    def get_queryset(self):
        return super().get_queryset().select_related(
            "race",
            "race__season",
            "driver",
            "team",
        )


class QualifyingResultDetailAPIView(BaseRetrieveUpdateDestroyAPIView):
    model = QualifyingResult
    serializer_class = QualifyingResultSerializer

    def get_queryset(self):
        return super().get_queryset().select_related(
            "race",
            "race__season",
            "driver",
            "team",
        )


class SprintResultListCreateAPIView(BaseListCreateAPIView):
    model = SprintResult
    serializer_class = SprintResultSerializer
    filterset_fields = [
        "race",
        "race__season",
        "race__season__year",
        "driver",
        "team",
        "position",
        "status",
    ]
    search_fields = [
        "race__name",
        "driver__first_name",
        "driver__last_name",
        "driver__abbreviation",
        "team__name",
    ]
    ordering_fields = [
        "race__season__year",
        "race__round_number",
        "position",
        "grid_position",
        "points",
        "created_at",
    ]
    ordering = [
        "race__season__year",
        "race__round_number",
        "position",
    ]

    def get_queryset(self):
        return super().get_queryset().select_related(
            "race",
            "race__season",
            "driver",
            "team",
        )


class SprintResultDetailAPIView(BaseRetrieveUpdateDestroyAPIView):
    model = SprintResult
    serializer_class = SprintResultSerializer

    def get_queryset(self):
        return super().get_queryset().select_related(
            "race",
            "race__season",
            "driver",
            "team",
        )
