from django.contrib import admin

from apps.standings.models import ConstructorStanding, DriverStanding


@admin.register(DriverStanding)
class DriverStandingAdmin(admin.ModelAdmin):
    list_display = [
        "season",
        "position",
        "driver",
        "team",
        "points",
        "wins",
        "podiums",
        "poles",
        "fastest_laps",
    ]
    list_filter = [
        "season",
        "team",
    ]
    search_fields = [
        "driver__first_name",
        "driver__last_name",
        "driver__abbreviation",
        "team__name",
        "season__year",
    ]
    ordering = [
        "season__year",
        "position",
    ]
    autocomplete_fields = [
        "season",
        "driver",
        "team",
    ]


@admin.register(ConstructorStanding)
class ConstructorStandingAdmin(admin.ModelAdmin):
    list_display = [
        "season",
        "position",
        "team",
        "points",
        "wins",
        "podiums",
        "poles",
        "fastest_laps",
    ]
    list_filter = [
        "season",
        "team",
    ]
    search_fields = [
        "team__name",
        "team__official_name",
        "season__year",
    ]
    ordering = [
        "season__year",
        "position",
    ]
    autocomplete_fields = [
        "season",
        "team",
    ]
