from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.content.models import Article, Category, Tag


class ContentRegressionTests(APITestCase):
    def setUp(self):
        self.client.force_authenticate(
            get_user_model().objects.create_user(
                username="content-admin", is_staff=True
            )
        )

    def test_read_only_aliases_reject_writes(self):
        article = Article.objects.create(title="Test", content="Body")
        slug_url = reverse("content:article-slug-detail", args=[article.slug])
        for method in (self.client.patch, self.client.put, self.client.delete):
            self.assertEqual(method(slug_url, {}).status_code, 405)
        self.assertEqual(
            self.client.post(reverse("content:featured-article-list"), {}).status_code,
            405,
        )

    def test_category_and_tag_counts_respect_publication_visibility(self):
        category = Category.objects.create(name="Visibility category")
        tag = Tag.objects.create(name="Visibility tag")
        now = timezone.now()
        for index, (status, published_at) in enumerate(
            (
                ("draft", None),
                ("archived", now - timedelta(days=1)),
                ("published", now + timedelta(days=1)),
                ("published", now - timedelta(days=1)),
            )
        ):
            article = Article.objects.create(
                title=f"Visibility {index}",
                content="Body",
                category=category,
                status=status,
                published_at=published_at,
            )
            article.tags.add(tag)
        admin = get_user_model().objects.get(username="content-admin")
        regular = get_user_model().objects.create_user(
            username="reader", email="reader@example.com"
        )
        for user, expected in ((None, 1), (regular, 1), (admin, 4)):
            self.client.force_authenticate(user)
            for name, record in (("category", category), ("tag", tag)):
                with self.subTest(user=user, name=name):
                    detail = self.client.get(
                        reverse(f"content:{name}-detail", args=[record.pk])
                    )
                    listing = self.client.get(reverse(f"content:{name}-list-create"))
                    self.assertEqual(detail.status_code, 200)
                    self.assertEqual(listing.status_code, 200)
                    self.assertEqual(detail.data["articles_count"], expected)
                    self.assertEqual(
                        listing.data["results"][0]["articles_count"], expected
                    )
