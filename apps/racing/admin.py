from django.contrib import admin

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

@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ["year", "name", "is_current", "created_at"]
    list_filter = ["is_current"]
    search_fields = ["name"]
    ordering = ["-year"]


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "country",
        "team_principal",
        "power_unit",
        "is_active",
    ]
    list_filter = ["country", "is_active", "power_unit"]
    search_fields = ["name", "official_name", "country"]


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = [
        "full_name",
        "abbreviation",
        "number",
        "country",
        "current_team",
        "status",
    ]
    list_filter = ["status", "country", "current_team"]
    search_fields = [
        "first_name",
        "last_name",
        "abbreviation",
        "country",
    ]


@admin.register(Circuit)
class CircuitAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "country",
        "city",
        "length_km",
        "number_of_laps",
    ]
    list_filter = ["country"]
    search_fields = ["name", "official_name", "country", "city"]


@admin.register(Race)
class RaceAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "season",
        "round_number",
        "circuit",
        "race_date",
        "status",
    ]
    list_filter = ["season", "status", "circuit__country"]
    search_fields = ["name", "official_name", "circuit__name"]
    ordering = ["season__year", "round_number"]


@admin.register(RaceResult)
class RaceResultAdmin(admin.ModelAdmin):
    list_display = [
        "race",
        "position",
        "driver",
        "team",
        "grid_position",
        "points",
        "status",
        "fastest_lap",
    ]
    list_filter = [
        "race__season",
        "race",
        "team",
        "status",
        "fastest_lap",
    ]
    search_fields = [
        "race__name",
        "driver__first_name",
        "driver__last_name",
        "team__name",
    ]
    ordering = [
        "race__season__year",
        "race__round_number",
        "position",
    ]
    autocomplete_fields = [
        "race",
        "driver",
        "team",
    ]


@admin.register(QualifyingResult)
class QualifyingResultAdmin(admin.ModelAdmin):
    list_display = [
        "race",
        "position",
        "driver",
        "team",
        "q1_time",
        "q2_time",
        "q3_time",
        "penalty",
    ]
    list_filter = [
        "race__season",
        "race",
        "team",
    ]
    search_fields = [
        "race__name",
        "driver__first_name",
        "driver__last_name",
        "team__name",
    ]
    ordering = [
        "race__season__year",
        "race__round_number",
        "position",
    ]
    autocomplete_fields = [
        "race",
        "driver",
        "team",
    ]


@admin.register(SprintResult)
class SprintResultAdmin(admin.ModelAdmin):
    list_display = [
        "race",
        "position",
        "driver",
        "team",
        "grid_position",
        "points",
        "status",
    ]
    list_filter = [
        "race__season",
        "race",
        "team",
        "status",
    ]
    search_fields = [
        "race__name",
        "driver__first_name",
        "driver__last_name",
        "team__name",
    ]
    ordering = [
        "race__season__year",
        "race__round_number",
        "position",
    ]
    autocomplete_fields = [
        "race",
        "driver",
        "team",
    ]
