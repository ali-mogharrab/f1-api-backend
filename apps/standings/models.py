from django.db import models

from apps.core.models import BaseModel
from apps.racing.models import Driver, Season, Team


class DriverStanding(BaseModel):
    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        related_name="driver_standings",
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name="standings",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="driver_standings",
        help_text="Main/current team for this driver in this season standing.",
    )

    position = models.PositiveSmallIntegerField()
    points = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
    )

    wins = models.PositiveSmallIntegerField(default=0)
    podiums = models.PositiveSmallIntegerField(default=0)
    poles = models.PositiveSmallIntegerField(default=0)
    fastest_laps = models.PositiveSmallIntegerField(default=0)

    races_entered = models.PositiveSmallIntegerField(default=0)
    races_finished = models.PositiveSmallIntegerField(default=0)
    dnfs = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["season__year", "position"]
        verbose_name = "Driver Standing"
        verbose_name_plural = "Driver Standings"
        constraints = [
            models.UniqueConstraint(
                fields=["season", "driver"],
                name="unique_driver_standing_per_season",
            ),
            models.UniqueConstraint(
                fields=["season", "position"],
                name="unique_driver_standing_position_per_season",
            ),
        ]

    def __str__(self):
        return f"{self.season.year} - P{self.position} - {self.driver.full_name}"


class ConstructorStanding(BaseModel):
    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        related_name="constructor_standings",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="constructor_standings",
    )

    position = models.PositiveSmallIntegerField()
    points = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
    )

    wins = models.PositiveSmallIntegerField(default=0)
    podiums = models.PositiveSmallIntegerField(default=0)
    poles = models.PositiveSmallIntegerField(default=0)
    fastest_laps = models.PositiveSmallIntegerField(default=0)

    races_entered = models.PositiveSmallIntegerField(default=0)
    double_podiums = models.PositiveSmallIntegerField(default=0)
    double_points_finishes = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["season__year", "position"]
        verbose_name = "Constructor Standing"
        verbose_name_plural = "Constructor Standings"
        constraints = [
            models.UniqueConstraint(
                fields=["season", "team"],
                name="unique_constructor_standing_per_season",
            ),
            models.UniqueConstraint(
                fields=["season", "position"],
                name="unique_constructor_standing_position_per_season",
            ),
        ]

    def __str__(self):
        return f"{self.season.year} - P{self.position} - {self.team.name}"
