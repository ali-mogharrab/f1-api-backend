from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.core.utils import generate_unique_slug


class Category(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(
                instance=self,
                source_field="name",
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(
                instance=self,
                source_field="name",
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Article(BaseModel):
    class ArticleStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)

    subtitle = models.CharField(max_length=255, blank=True)
    summary = models.TextField(blank=True)
    content = models.TextField()

    cover_image = models.ImageField(
        upload_to="content/articles/covers/",
        null=True,
        blank=True,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="articles",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )

    related_race = models.ForeignKey(
        "racing.Race",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )
    related_driver = models.ForeignKey(
        "racing.Driver",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )
    related_team = models.ForeignKey(
        "racing.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )

    status = models.CharField(
        max_length=20,
        choices=ArticleStatus.choices,
        default=ArticleStatus.DRAFT,
    )

    is_featured = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    views_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = "Article"
        verbose_name_plural = "Articles"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
            models.Index(fields=["published_at"]),
            models.Index(fields=["is_featured"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(
                instance=self,
                source_field="title",
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
