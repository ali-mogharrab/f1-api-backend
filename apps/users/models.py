import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import BaseModel


class User(AbstractUser):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    email = models.EmailField(unique=True)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.username


class UserProfile(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    bio = models.TextField(blank=True)
    avatar = models.ImageField(
        upload_to="users/avatars/",
        null=True,
        blank=True,
    )
    country = models.CharField(max_length=100, blank=True)
    favorite_driver_name = models.CharField(max_length=150, blank=True)
    favorite_team_name = models.CharField(max_length=150, blank=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.username}'s profile"


class FavoriteDriver(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favorite_drivers",
    )
    driver = models.ForeignKey(
        "racing.Driver",
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )

    class Meta:
        verbose_name = "Favorite Driver"
        verbose_name_plural = "Favorite Drivers"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "driver"],
                name="unique_favorite_driver_per_user",
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.driver.full_name}"


class FavoriteTeam(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favorite_teams",
    )
    team = models.ForeignKey(
        "racing.Team",
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )

    class Meta:
        verbose_name = "Favorite Team"
        verbose_name_plural = "Favorite Teams"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "team"],
                name="unique_favorite_team_per_user",
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.team.name}"


class FavoriteRace(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favorite_races",
    )
    race = models.ForeignKey(
        "racing.Race",
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )

    class Meta:
        verbose_name = "Favorite Race"
        verbose_name_plural = "Favorite Races"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "race"],
                name="unique_favorite_race_per_user",
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.race.name}"
