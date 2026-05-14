from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.users.models import (
    FavoriteDriver,
    FavoriteRace,
    FavoriteTeam,
    User,
    UserProfile,
)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = [
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "date_joined",
    ]
    list_filter = [
        "is_staff",
        "is_active",
        "is_superuser",
    ]
    search_fields = [
        "username",
        "email",
        "first_name",
        "last_name",
    ]
    ordering = ["username"]
    readonly_fields = ["id", "date_joined", "last_login"]
    inlines = [UserProfileInline]

    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "Additional info",
            {
                "fields": ("id",),
            },
        ),
    )


@admin.register(FavoriteDriver)
class FavoriteDriverAdmin(admin.ModelAdmin):
    list_display = ["user", "driver", "created_at"]
    search_fields = [
        "user__username",
        "user__email",
        "driver__first_name",
        "driver__last_name",
        "driver__abbreviation",
    ]
    autocomplete_fields = ["user", "driver"]


@admin.register(FavoriteTeam)
class FavoriteTeamAdmin(admin.ModelAdmin):
    list_display = ["user", "team", "created_at"]
    search_fields = [
        "user__username",
        "user__email",
        "team__name",
        "team__official_name",
    ]
    autocomplete_fields = ["user", "team"]


@admin.register(FavoriteRace)
class FavoriteRaceAdmin(admin.ModelAdmin):
    list_display = ["user", "race", "created_at"]
    search_fields = [
        "user__username",
        "user__email",
        "race__name",
        "race__official_name",
    ]
    autocomplete_fields = ["user", "race"]
