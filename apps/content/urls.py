from django.urls import path

from apps.content.views import (
    ArticleDetailAPIView,
    ArticleListCreateAPIView,
    ArticleSlugDetailAPIView,
    CategoryDetailAPIView,
    CategoryListCreateAPIView,
    FeaturedArticleListAPIView,
    TagDetailAPIView,
    TagListCreateAPIView,
)


app_name = "content"

urlpatterns = [
    path(
        "categories/",
        CategoryListCreateAPIView.as_view(),
        name="category-list-create",
    ),
    path(
        "categories/<uuid:pk>/",
        CategoryDetailAPIView.as_view(),
        name="category-detail",
    ),
    path(
        "tags/",
        TagListCreateAPIView.as_view(),
        name="tag-list-create",
    ),
    path(
        "tags/<uuid:pk>/",
        TagDetailAPIView.as_view(),
        name="tag-detail",
    ),
    path(
        "articles/",
        ArticleListCreateAPIView.as_view(),
        name="article-list-create",
    ),
    path(
        "articles/featured/",
        FeaturedArticleListAPIView.as_view(),
        name="featured-article-list",
    ),
    path(
        "articles/<uuid:pk>/",
        ArticleDetailAPIView.as_view(),
        name="article-detail",
    ),
    path(
        "articles/slug/<slug:slug>/",
        ArticleSlugDetailAPIView.as_view(),
        name="article-slug-detail",
    ),
]
