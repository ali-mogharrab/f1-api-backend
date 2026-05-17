from django.contrib import admin

from apps.content.models import Article, Category, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_at"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_at"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "category",
        "author",
        "status",
        "is_featured",
        "published_at",
        "views_count",
    ]
    list_filter = [
        "status",
        "is_featured",
        "category",
        "tags",
        "published_at",
    ]
    search_fields = [
        "title",
        "subtitle",
        "summary",
        "content",
        "slug",
    ]
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = [
        "category",
        "tags",
        "author",
        "related_race",
        "related_driver",
        "related_team",
    ]
    filter_horizontal = ["tags"]
    readonly_fields = [
        "id",
        "views_count",
        "created_at",
        "updated_at",
    ]
    ordering = ["-published_at", "-created_at"]
