from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.content.models import Article, Category, Tag
from apps.racing.models import Circuit, Driver, Race, Season, Team


User = get_user_model()


class ContentAPITests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="StrongPassword123!",
            is_staff=True,
        )

        self.normal_user = User.objects.create_user(
            username="ali",
            email="ali@example.com",
            password="StrongPassword123!",
        )

        self.category = Category.objects.create(
            name="Race Previews",
            description="Previews before Formula 1 race weekends.",
        )

        self.tag = Tag.objects.create(
            name="Monaco GP",
        )

        self.season = Season.objects.create(
            year=2026,
            name="2026 Formula One World Championship",
            is_current=True,
        )

        self.team = Team.objects.create(
            name="Red Bull Racing",
            official_name="Oracle Red Bull Racing",
            country="Austria",
            base_location="Milton Keynes, United Kingdom",
            power_unit="Red Bull Ford Powertrains",
            first_team_entry=2005,
            world_championships=6,
            is_active=True,
        )

        self.driver = Driver.objects.create(
            first_name="Max",
            last_name="Verstappen",
            abbreviation="VER",
            number=1,
            country="Netherlands",
            status=Driver.DriverStatus.ACTIVE,
            current_team=self.team,
        )

        self.circuit = Circuit.objects.create(
            name="Circuit de Monaco",
            country="Monaco",
            city="Monte Carlo",
            length_km="3.337",
            number_of_laps=78,
            race_distance_km="260.286",
        )

        self.race = Race.objects.create(
            season=self.season,
            circuit=self.circuit,
            name="Monaco Grand Prix",
            official_name="Formula 1 Grand Prix de Monaco 2026",
            round_number=8,
            race_date="2026-06-07",
            race_time="15:00:00",
            status=Race.RaceStatus.SCHEDULED,
        )

    def test_category_slug_is_generated(self):
        self.assertEqual(self.category.slug, "race-previews")

    def test_tag_slug_is_generated(self):
        self.assertEqual(self.tag.slug, "monaco-gp")

    def test_unique_article_slug_is_generated(self):
        first_article = Article.objects.create(
            title="Monaco Grand Prix Preview",
            summary="First article summary.",
            content="First article content.",
            category=self.category,
            author=self.admin_user,
            status=Article.ArticleStatus.PUBLISHED,
            published_at=timezone.now(),
        )

        second_article = Article.objects.create(
            title="Monaco Grand Prix Preview",
            summary="Second article summary.",
            content="Second article content.",
            category=self.category,
            author=self.admin_user,
            status=Article.ArticleStatus.PUBLISHED,
            published_at=timezone.now(),
        )

        self.assertEqual(first_article.slug, "monaco-grand-prix-preview")
        self.assertEqual(second_article.slug, "monaco-grand-prix-preview-2")

    def test_public_user_can_list_published_articles(self):
        article = Article.objects.create(
            title="Monaco Grand Prix Preview",
            summary="Article summary.",
            content="Article content.",
            category=self.category,
            author=self.admin_user,
            status=Article.ArticleStatus.PUBLISHED,
            published_at=timezone.now(),
        )
        article.tags.add(self.tag)

        url = reverse("content:article-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["title"],
            "Monaco Grand Prix Preview",
        )
        self.assertEqual(
            response.data["results"][0]["category_name"],
            "Race Previews",
        )

    def test_public_user_cannot_see_draft_articles(self):
        Article.objects.create(
            title="Draft Article",
            summary="Draft summary.",
            content="Draft content.",
            category=self.category,
            author=self.admin_user,
            status=Article.ArticleStatus.DRAFT,
            published_at=None,
        )

        url = reverse("content:article-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_public_user_cannot_see_future_published_articles(self):
        Article.objects.create(
            title="Future Article",
            summary="Future summary.",
            content="Future content.",
            category=self.category,
            author=self.admin_user,
            status=Article.ArticleStatus.PUBLISHED,
            published_at=timezone.now() + timezone.timedelta(days=1),
        )

        url = reverse("content:article-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_admin_user_can_see_draft_articles(self):
        Article.objects.create(
            title="Draft Article",
            summary="Draft summary.",
            content="Draft content.",
            category=self.category,
            author=self.admin_user,
            status=Article.ArticleStatus.DRAFT,
            published_at=None,
        )

        self.client.force_authenticate(user=self.admin_user)

        url = reverse("content:article-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["status"], "draft")

    def test_public_user_cannot_create_article(self):
        url = reverse("content:article-list-create")
        payload = {
            "title": "Unauthorized Article",
            "summary": "Summary.",
            "content": "Content.",
            "category": str(self.category.id),
            "status": Article.ArticleStatus.PUBLISHED,
            "published_at": timezone.now().isoformat(),
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_normal_authenticated_user_cannot_create_article(self):
        self.client.force_authenticate(user=self.normal_user)

        url = reverse("content:article-list-create")
        payload = {
            "title": "Unauthorized Article",
            "summary": "Summary.",
            "content": "Content.",
            "category": str(self.category.id),
            "status": Article.ArticleStatus.PUBLISHED,
            "published_at": timezone.now().isoformat(),
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_can_create_article(self):
        self.client.force_authenticate(user=self.admin_user)

        url = reverse("content:article-list-create")
        payload = {
            "title": "Monaco Grand Prix Preview",
            "subtitle": "A look ahead to Monaco.",
            "summary": "Preview summary.",
            "content": "Full article content.",
            "category": str(self.category.id),
            "tags": [str(self.tag.id)],
            "related_race": str(self.race.id),
            "related_driver": str(self.driver.id),
            "related_team": str(self.team.id),
            "status": Article.ArticleStatus.PUBLISHED,
            "is_featured": True,
            "published_at": timezone.now().isoformat(),
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["title"], "Monaco Grand Prix Preview")
        self.assertEqual(response.data["data"]["slug"], "monaco-grand-prix-preview")
        self.assertEqual(response.data["data"]["author_username"], "admin")
        self.assertEqual(response.data["data"]["category_name"], "Race Previews")
        self.assertEqual(response.data["data"]["related_race_name"], "Monaco Grand Prix")
        self.assertEqual(Article.objects.count(), 1)

    def test_public_user_can_retrieve_article_by_id(self):
        article = Article.objects.create(
            title="Monaco Grand Prix Preview",
            summary="Article summary.",
            content="Article content.",
            category=self.category,
            author=self.admin_user,
            status=Article.ArticleStatus.PUBLISHED,
            published_at=timezone.now(),
        )

        url = reverse(
            "content:article-detail",
            kwargs={"pk": article.id},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Monaco Grand Prix Preview")
        self.assertEqual(response.data["content"], "Article content.")

    def test_public_user_can_retrieve_article_by_slug(self):
        article = Article.objects.create(
            title="Monaco Grand Prix Preview",
            summary="Article summary.",
            content="Article content.",
            category=self.category,
            author=self.admin_user,
            status=Article.ArticleStatus.PUBLISHED,
            published_at=timezone.now(),
        )

        url = reverse(
            "content:article-slug-detail",
            kwargs={"slug": article.slug},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], "monaco-grand-prix-preview")

    def test_article_detail_increments_views_count(self):
        article = Article.objects.create(
            title="Monaco Grand Prix Preview",
            summary="Article summary.",
            content="Article content.",
            category=self.category,
            author=self.admin_user,
            status=Article.ArticleStatus.PUBLISHED,
            published_at=timezone.now(),
            views_count=0,
        )

        url = reverse(
            "content:article-detail",
            kwargs={"pk": article.id},
        )

        first_response = self.client.get(url)
        second_response = self.client.get(url)

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)

        article.refresh_from_db()
        self.assertEqual(article.views_count, 2)

    def test_article_slug_detail_increments_views_count(self):
        article = Article.objects.create(
            title="Monaco Grand Prix Preview",
            summary="Article summary.",
            content="Article content.",
            category=self.category,
            author=self.admin_user,
            status=Article.ArticleStatus.PUBLISHED,
            published_at=timezone.now(),
            views_count=0,
        )

        url = reverse(
            "content:article-slug-detail",
            kwargs={"slug": article.slug},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        article.refresh_from_db()
        self.assertEqual(article.views_count, 1)

    def test_filter_articles_by_category_slug(self):
        Article.objects.create(
            title="Monaco Grand Prix Preview",
            summary="Article summary.",
            content="Article content.",
            category=self.category,
            author=self.admin_user,
            status=Article.ArticleStatus.PUBLISHED,
            published_at=timezone.now(),
        )

        url = reverse("content:article-list-create")
        response = self.client.get(
            url,
            {"category__slug": "race-previews"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_filter_articles_by_tag_slug(self):
        article = Article.objects.create(
            title="Monaco Grand Prix Preview",
            summary="Article summary.",
            content="Article content.",
            category=self.category,
            author=self.admin_user,
            status=Article.ArticleStatus.PUBLISHED,
            published_at=timezone.now(),
        )
        article.tags.add(self.tag)

        url = reverse("content:article-list-create")
        response = self.client.get(
            url,
            {"tags__slug": "monaco-gp"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_search_articles(self):
        Article.objects.create(
            title="Monaco Grand Prix Preview",
            summary="Strategy and qualifying will be important.",
            content="Full Monaco content.",
            category=self.category,
            author=self.admin_user,
            status=Article.ArticleStatus.PUBLISHED,
            published_at=timezone.now(),
        )

        url = reverse("content:article-list-create")
        response = self.client.get(url, {"search": "qualifying"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_featured_articles_endpoint_returns_only_featured_published_articles(self):
        featured_article = Article.objects.create(
            title="Featured Monaco Preview",
            summary="Featured summary.",
            content="Featured content.",
            category=self.category,
            author=self.admin_user,
            status=Article.ArticleStatus.PUBLISHED,
            is_featured=True,
            published_at=timezone.now(),
        )

        Article.objects.create(
            title="Normal Monaco Preview",
            summary="Normal summary.",
            content="Normal content.",
            category=self.category,
            author=self.admin_user,
            status=Article.ArticleStatus.PUBLISHED,
            is_featured=False,
            published_at=timezone.now(),
        )

        url = reverse("content:featured-article-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(featured_article.id))

    def test_admin_cannot_create_published_article_without_published_at(self):
        self.client.force_authenticate(user=self.admin_user)

        url = reverse("content:article-list-create")
        payload = {
            "title": "Invalid Published Article",
            "summary": "Summary.",
            "content": "Content.",
            "category": str(self.category.id),
            "status": Article.ArticleStatus.PUBLISHED,
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("published_at", response.data["errors"])

    def test_admin_cannot_create_featured_draft_article(self):
        self.client.force_authenticate(user=self.admin_user)

        url = reverse("content:article-list-create")
        payload = {
            "title": "Invalid Featured Draft",
            "summary": "Summary.",
            "content": "Content.",
            "category": str(self.category.id),
            "status": Article.ArticleStatus.DRAFT,
            "is_featured": True,
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("is_featured", response.data["errors"])
