from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel


class Season(BaseModel):
    year = models.PositiveSmallIntegerField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-year"]
        verbose_name = "Season"
        verbose_name_plural = "Seasons"

    def __str__(self):
        return str(self.year)


class Team(BaseModel):
    name = models.CharField(max_length=150)
    official_name = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=100, blank=True)

    base_location = models.CharField(max_length=150, blank=True)
    team_principal = models.CharField(max_length=150, blank=True)
    technical_chief = models.CharField(max_length=150, blank=True)

    chassis = models.CharField(max_length=100, blank=True)
    power_unit = models.CharField(max_length=100, blank=True)

    first_team_entry = models.PositiveSmallIntegerField(null=True, blank=True)
    world_championships = models.PositiveSmallIntegerField(default=0)

    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to="teams/logos/", null=True, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Team"
        verbose_name_plural = "Teams"
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                name="unique_team_name",
            )
        ]

    def __str__(self):
        return self.name


class Driver(BaseModel):
    class DriverStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        RESERVE = "reserve", "Reserve"
        TEST = "test", "Test Driver"

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    abbreviation = models.CharField(
        max_length=3,
        help_text="Official three-letter F1 abbreviation, for example VER, HAM, LEC.",
    )

    number = models.PositiveSmallIntegerField(null=True, blank=True)
    country = models.CharField(max_length=100, blank=True)

    date_of_birth = models.DateField(null=True, blank=True)
    place_of_birth = models.CharField(max_length=150, blank=True)

    status = models.CharField(
        max_length=20,
        choices=DriverStatus.choices,
        default=DriverStatus.ACTIVE,
    )

    current_team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_drivers",
    )

    image = models.ImageField(upload_to="drivers/images/", null=True, blank=True)
    biography = models.TextField(blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Driver"
        verbose_name_plural = "Drivers"
        constraints = [
            models.UniqueConstraint(
                fields=["first_name", "last_name", "date_of_birth"],
                name="unique_driver_identity",
            ),
            models.UniqueConstraint(
                fields=["abbreviation"],
                name="unique_driver_abbreviation",
            ),
        ]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Circuit(BaseModel):
    name = models.CharField(max_length=150)
    official_name = models.CharField(max_length=255, blank=True)

    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True)

    length_km = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        null=True,
        blank=True,
    )

    number_of_laps = models.PositiveSmallIntegerField(null=True, blank=True)
    race_distance_km = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        null=True,
        blank=True,
    )

    lap_record = models.CharField(max_length=50, blank=True)
    lap_record_driver = models.CharField(max_length=150, blank=True)
    lap_record_year = models.PositiveSmallIntegerField(null=True, blank=True)

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    image = models.ImageField(upload_to="circuits/images/", null=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Circuit"
        verbose_name_plural = "Circuits"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "country"],
                name="unique_circuit_name_country",
            )
        ]

    def __str__(self):
        return self.name


class Race(BaseModel):
    class RaceStatus(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        POSTPONED = "postponed", "Postponed"

    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        related_name="races",
    )
    circuit = models.ForeignKey(
        Circuit,
        on_delete=models.PROTECT,
        related_name="races",
    )

    name = models.CharField(max_length=150)
    official_name = models.CharField(max_length=255, blank=True)

    round_number = models.PositiveSmallIntegerField()

    race_date = models.DateField()
    race_time = models.TimeField(null=True, blank=True)

    qualifying_date = models.DateField(null=True, blank=True)
    qualifying_time = models.TimeField(null=True, blank=True)

    sprint_date = models.DateField(null=True, blank=True)
    sprint_time = models.TimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=RaceStatus.choices,
        default=RaceStatus.SCHEDULED,
    )

    class Meta:
        ordering = ["season__year", "round_number"]
        verbose_name = "Race"
        verbose_name_plural = "Races"
        constraints = [
            models.UniqueConstraint(
                fields=["season", "round_number"],
                name="unique_race_round_per_season",
            ),
            models.UniqueConstraint(
                fields=["season", "name"],
                name="unique_race_name_per_season",
            ),
        ]

    def clean(self):
        errors = {}

        if self.qualifying_date and self.qualifying_date > self.race_date:
            errors["qualifying_date"] = "Qualifying date cannot be after race date."

        if self.sprint_date and self.sprint_date > self.race_date:
            errors["sprint_date"] = "Sprint date cannot be after race date."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.season.year} - Round {self.round_number}: {self.name}"


class RaceResult(BaseModel):
    class ResultStatus(models.TextChoices):
        CLASSIFIED = "classified", "Classified"
        NOT_CLASSIFIED = "not_classified", "Not Classified"
        RETIRED = "retired", "Retired"
        DISQUALIFIED = "disqualified", "Disqualified"
        DID_NOT_START = "did_not_start", "Did Not Start"
        DID_NOT_FINISH = "did_not_finish", "Did Not Finish"

    race = models.ForeignKey(
        Race,
        on_delete=models.CASCADE,
        related_name="race_results",
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.PROTECT,
        related_name="race_results",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="race_results",
    )

    position = models.PositiveSmallIntegerField(null=True, blank=True)
    classified_position = models.CharField(max_length=10, blank=True)

    grid_position = models.PositiveSmallIntegerField(null=True, blank=True)

    laps_completed = models.PositiveSmallIntegerField(default=0)

    time = models.CharField(
        max_length=50,
        blank=True,
        help_text="Race time or gap to winner, for example 1:25:33.607 or +5.123.",
    )

    fastest_lap = models.BooleanField(default=False)
    fastest_lap_time = models.CharField(max_length=50, blank=True)
    fastest_lap_rank = models.PositiveSmallIntegerField(null=True, blank=True)

    points = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    status = models.CharField(
        max_length=30,
        choices=ResultStatus.choices,
        default=ResultStatus.CLASSIFIED,
    )

    class Meta:
        ordering = ["race__season__year", "race__round_number", "position"]
        verbose_name = "Race Result"
        verbose_name_plural = "Race Results"
        constraints = [
            models.UniqueConstraint(
                fields=["race", "driver"],
                name="unique_race_result_per_driver",
            ),
            models.UniqueConstraint(
                fields=["race", "position"],
                condition=models.Q(position__isnull=False),
                name="unique_race_result_position_per_race",
            ),
        ]

    def clean(self):
        errors = {}

        if self.position is not None and self.position < 1:
            errors["position"] = "Position must be greater than or equal to 1."

        if self.grid_position is not None and self.grid_position < 1:
            errors["grid_position"] = "Grid position must be greater than or equal to 1."

        if self.fastest_lap_rank is not None and self.fastest_lap_rank < 1:
            errors["fastest_lap_rank"] = "Fastest lap rank must be greater than or equal to 1."

        if self.points < 0:
            errors["points"] = "Points cannot be negative."

        if self.driver_id and self.team_id and self.driver.current_team_id:
            if self.driver.current_team_id != self.team_id:
                errors["team"] = "Team must match the driver's current team."

        if errors:
            raise ValidationError(errors)
        
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.race} - {self.driver.full_name} - P{self.position}"


class QualifyingResult(BaseModel):
    race = models.ForeignKey(
        Race,
        on_delete=models.CASCADE,
        related_name="qualifying_results",
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.PROTECT,
        related_name="qualifying_results",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="qualifying_results",
    )

    position = models.PositiveSmallIntegerField(null=True, blank=True)

    q1_time = models.CharField(max_length=30, blank=True)
    q2_time = models.CharField(max_length=30, blank=True)
    q3_time = models.CharField(max_length=30, blank=True)

    laps_completed = models.PositiveSmallIntegerField(default=0)

    penalty = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["race__season__year", "race__round_number", "position"]
        verbose_name = "Qualifying Result"
        verbose_name_plural = "Qualifying Results"
        constraints = [
            models.UniqueConstraint(
                fields=["race", "driver"],
                name="unique_qualifying_result_per_driver",
            ),
            models.UniqueConstraint(
                fields=["race", "position"],
                condition=models.Q(position__isnull=False),
                name="unique_qualifying_position_per_race",
            ),
        ]

    def clean(self):
        errors = {}

        if self.position is not None and self.position < 1:
            errors["position"] = "Position must be greater than or equal to 1."

        if self.team_id and self.driver_id and self.driver.current_team_id:
            if self.driver.current_team_id != self.team_id:
                errors["team"] = "Team must match the driver's current team."

        if errors:
            raise ValidationError(errors)


    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.race} - Qualifying - {self.driver.full_name} - P{self.position}"


class SprintResult(BaseModel):
    class SprintStatus(models.TextChoices):
        CLASSIFIED = "classified", "Classified"
        NOT_CLASSIFIED = "not_classified", "Not Classified"
        RETIRED = "retired", "Retired"
        DISQUALIFIED = "disqualified", "Disqualified"
        DID_NOT_START = "did_not_start", "Did Not Start"
        DID_NOT_FINISH = "did_not_finish", "Did Not Finish"

    race = models.ForeignKey(
        Race,
        on_delete=models.CASCADE,
        related_name="sprint_results",
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.PROTECT,
        related_name="sprint_results",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="sprint_results",
    )

    position = models.PositiveSmallIntegerField(null=True, blank=True)
    grid_position = models.PositiveSmallIntegerField(null=True, blank=True)

    laps_completed = models.PositiveSmallIntegerField(default=0)

    time = models.CharField(
        max_length=50,
        blank=True,
        help_text="Sprint time or gap to winner.",
    )

    points = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    status = models.CharField(
        max_length=30,
        choices=SprintStatus.choices,
        default=SprintStatus.CLASSIFIED,
    )

    class Meta:
        ordering = ["race__season__year", "race__round_number", "position"]
        verbose_name = "Sprint Result"
        verbose_name_plural = "Sprint Results"
        constraints = [
            models.UniqueConstraint(
                fields=["race", "driver"],
                name="unique_sprint_result_per_driver",
            ),
            models.UniqueConstraint(
                fields=["race", "position"],
                condition=models.Q(position__isnull=False),
                name="unique_sprint_position_per_race",
            ),
        ]

    def __str__(self):
        return f"{self.race} - Sprint - {self.driver.full_name} - P{self.position}"
