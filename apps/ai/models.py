from django.conf import settings
from django.db import models
from pgvector.django import VectorField

from apps.core.models import BaseModel


class Conversation(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_conversations",
    )
    title = models.CharField(max_length=100)
    revision = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [models.Index(fields=["user", "-updated_at"])]


class Message(BaseModel):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    sources = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    sequence = models.PositiveIntegerField()

    class Meta:
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "sequence"], name="ai_message_sequence_unique"
            )
        ]


class ArticleDocument(BaseModel):
    article = models.OneToOneField(
        "content.Article", on_delete=models.CASCADE, related_name="ai_document"
    )
    fingerprint = models.CharField(max_length=64)
    profile = models.CharField(max_length=64, db_index=True)
    indexed_at = models.DateTimeField(auto_now=True)


class ArticleChunk(BaseModel):
    document = models.ForeignKey(
        ArticleDocument, on_delete=models.CASCADE, related_name="chunks"
    )
    ordinal = models.PositiveIntegerField()
    text = models.TextField()
    embedding = VectorField()
    metadata = models.JSONField(default=dict)

    class Meta:
        ordering = ["document_id", "ordinal"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "ordinal"], name="ai_chunk_ordinal_unique"
            )
        ]
