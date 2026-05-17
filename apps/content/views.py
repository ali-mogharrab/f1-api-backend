from django.db.models import Count, F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.content.models import Article, Category, Tag
from apps.content.serializers import (
    ArticleCreateUpdateSerializer,
    ArticleDetailSerializer,
    ArticleListSerializer,
    CategorySerializer,
    TagSerializer,
)
from apps.core.responses import error_response, success_response
from apps.core.views import BaseListCreateAPIView, BaseRetrieveUpdateDestroyAPIView


class CategoryListCreateAPIView(BaseListCreateAPIView):
    model = Category
    serializer_class = CategorySerializer
    filterset_fields = ["slug"]
    search_fields = ["name", "description", "slug"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        return super().get_queryset().annotate(
            articles_count=Count("articles")
        )


class CategoryDetailAPIView(BaseRetrieveUpdateDestroyAPIView):
    model = Category
    serializer_class = CategorySerializer

    def get_queryset(self):
        return super().get_queryset().annotate(
            articles_count=Count("articles")
        )


class TagListCreateAPIView(BaseListCreateAPIView):
    model = Tag
    serializer_class = TagSerializer
    filterset_fields = ["slug"]
    search_fields = ["name", "slug"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        return super().get_queryset().annotate(
            articles_count=Count("articles")
        )


class TagDetailAPIView(BaseRetrieveUpdateDestroyAPIView):
    model = Tag
    serializer_class = TagSerializer

    def get_queryset(self):
        return super().get_queryset().annotate(
            articles_count=Count("articles")
        )


class ArticleListCreateAPIView(BaseListCreateAPIView):
    model = Article
    serializer_class = ArticleListSerializer
    filterset_fields = [
        "status",
        "is_featured",
        "category",
        "category__slug",
        "tags",
        "tags__slug",
        "author",
        "related_race",
        "related_driver",
        "related_team",
    ]
    search_fields = [
        "title",
        "subtitle",
        "summary",
        "content",
        "category__name",
        "tags__name",
    ]
    ordering_fields = [
        "published_at",
        "created_at",
        "views_count",
        "title",
    ]
    ordering = ["-published_at", "-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            "category",
            "author",
            "related_race",
            "related_driver",
            "related_team",
        ).prefetch_related("tags")

        if not self.request.user.is_authenticated or not self.request.user.is_staff:
            queryset = queryset.filter(
                status=Article.ArticleStatus.PUBLISHED,
                published_at__lte=timezone.now(),
            )

        return queryset.distinct()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ArticleCreateUpdateSerializer

        return ArticleListSerializer

    def post(self, request):
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request},
        )

        if serializer.is_valid():
            serializer.save(author=request.user)

            output_serializer = ArticleDetailSerializer(
                serializer.instance,
                context={"request": request},
            )

            return success_response(
                data=output_serializer.data,
                message="Article created successfully.",
                status_code=status.HTTP_201_CREATED,
            )

        return error_response(
            errors=serializer.errors,
            message="Validation error.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class ArticleDetailAPIView(BaseRetrieveUpdateDestroyAPIView):
    model = Article
    serializer_class = ArticleDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            "category",
            "author",
            "related_race",
            "related_driver",
            "related_team",
        ).prefetch_related("tags")

        if not self.request.user.is_authenticated or not self.request.user.is_staff:
            queryset = queryset.filter(
                status=Article.ArticleStatus.PUBLISHED,
                published_at__lte=timezone.now(),
            )

        return queryset

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return ArticleCreateUpdateSerializer

        return ArticleDetailSerializer
    
    def increment_views_count(self, article):
        Article.objects.filter(pk=article.pk).update(
            views_count=F("views_count") + 1
        )
        article.refresh_from_db(fields=["views_count"])

    def get(self, request, pk):
        article = self.get_object(pk)
        self.increment_views_count(article)

        serializer = ArticleDetailSerializer(
            article,
            context={"request": request},
        )

        return Response(serializer.data)

    def put(self, request, pk):
        article = self.get_object(pk)

        serializer = ArticleCreateUpdateSerializer(
            article,
            data=request.data,
            context={"request": request},
        )

        if serializer.is_valid():
            serializer.save()

            output_serializer = ArticleDetailSerializer(
                serializer.instance,
                context={"request": request},
            )

            return success_response(
                data=output_serializer.data,
                message="Article updated successfully.",
                status_code=status.HTTP_200_OK,
            )

        return error_response(
            errors=serializer.errors,
            message="Validation error.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    def patch(self, request, pk):
        article = self.get_object(pk)

        serializer = ArticleCreateUpdateSerializer(
            article,
            data=request.data,
            partial=True,
            context={"request": request},
        )

        if serializer.is_valid():
            serializer.save()

            output_serializer = ArticleDetailSerializer(
                serializer.instance,
                context={"request": request},
            )

            return success_response(
                data=output_serializer.data,
                message="Article updated successfully.",
                status_code=status.HTTP_200_OK,
            )

        return error_response(
            errors=serializer.errors,
            message="Validation error.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class ArticleSlugDetailAPIView(ArticleDetailAPIView):
    def get_object(self, slug):
        return get_object_or_404(
            self.get_queryset(),
            slug=slug,
        )

    @extend_schema(
        tags=["content"],
        summary="Retrieve article by slug",
        description="Retrieve a published article by slug. This also increments the article view count.",
        responses={200: ArticleDetailSerializer},
    )
    def get(self, request, slug):
        article = self.get_object(slug)
        self.increment_views_count(article)

        serializer = ArticleDetailSerializer(
            article,
            context={"request": request},
        )

        return Response(serializer.data)


class FeaturedArticleListAPIView(BaseListCreateAPIView):
    model = Article
    serializer_class = ArticleListSerializer
    filterset_fields = [
        "category",
        "category__slug",
        "tags",
        "tags__slug",
    ]
    search_fields = [
        "title",
        "subtitle",
        "summary",
        "content",
        "category__name",
        "tags__name",
    ]
    ordering_fields = [
        "published_at",
        "created_at",
        "views_count",
        "title",
    ]
    ordering = ["-published_at", "-created_at"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "category",
                "author",
                "related_race",
                "related_driver",
                "related_team",
            )
            .prefetch_related("tags")
            .filter(
                status=Article.ArticleStatus.PUBLISHED,
                published_at__lte=timezone.now(),
                is_featured=True,
            )
            .distinct()
        )
