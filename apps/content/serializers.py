from rest_framework import serializers

from apps.content.models import Article, Category, Tag


class CategorySerializer(serializers.ModelSerializer):
    articles_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "articles_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]


class TagSerializer(serializers.ModelSerializer):
    articles_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tag
        fields = [
            "id",
            "name",
            "slug",
            "articles_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]


class ArticleListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )
    category_slug = serializers.CharField(
        source="category.slug",
        read_only=True,
    )
    author_username = serializers.CharField(
        source="author.username",
        read_only=True,
    )

    tags = TagSerializer(many=True, read_only=True)

    related_race_name = serializers.CharField(
        source="related_race.name",
        read_only=True,
    )
    related_driver_name = serializers.CharField(
        source="related_driver.full_name",
        read_only=True,
    )
    related_team_name = serializers.CharField(
        source="related_team.name",
        read_only=True,
    )

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "slug",
            "subtitle",
            "summary",
            "cover_image",
            "category",
            "category_name",
            "category_slug",
            "tags",
            "author",
            "author_username",
            "related_race",
            "related_race_name",
            "related_driver",
            "related_driver_name",
            "related_team",
            "related_team_name",
            "status",
            "is_featured",
            "published_at",
            "views_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "category_name",
            "category_slug",
            "author_username",
            "related_race_name",
            "related_driver_name",
            "related_team_name",
            "views_count",
            "created_at",
            "updated_at",
        ]


class ArticleDetailSerializer(ArticleListSerializer):
    class Meta(ArticleListSerializer.Meta):
        fields = ArticleListSerializer.Meta.fields + [
            "content",
        ]


class ArticleCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "slug",
            "subtitle",
            "summary",
            "content",
            "cover_image",
            "category",
            "tags",
            "author",
            "related_race",
            "related_driver",
            "related_team",
            "status",
            "is_featured",
            "published_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "author",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        status = attrs.get("status", getattr(self.instance, "status", None))
        published_at = attrs.get(
            "published_at",
            getattr(self.instance, "published_at", None),
        )
        is_featured = attrs.get(
            "is_featured",
            getattr(self.instance, "is_featured", False),
        )

        if status == Article.ArticleStatus.PUBLISHED and published_at is None:
            raise serializers.ValidationError(
                {
                    "published_at": "Published articles must have a published date."
                }
            )

        if status != Article.ArticleStatus.PUBLISHED and is_featured:
            raise serializers.ValidationError(
                {
                    "is_featured": "Only published articles can be featured."
                }
            )

        return attrs
