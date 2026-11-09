from django.conf import settings
from rest_framework import serializers

from .models import Conversation, Message


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(
        max_length=settings.AI_MESSAGE_MAX_LENGTH, trim_whitespace=True
    )
    conversation_id = serializers.UUIDField(required=False, allow_null=True)


class SourceSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.ChoiceField(
        choices=["article", "race_result", "driver_standing", "constructor_standing"]
    )
    entity_id = serializers.UUIDField()
    title = serializers.CharField()
    api_url = serializers.CharField()
    url = serializers.CharField(required=False)
    slug = serializers.CharField(required=False)
    chunk_id = serializers.UUIDField(required=False)
    published_at = serializers.DateTimeField(required=False)


class ChatDataSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField()
    answer = serializers.CharField()
    sources = SourceSerializer(many=True)
    metadata = serializers.DictField()


class ChatResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = ChatDataSerializer()


class ErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    errors = serializers.JSONField(allow_null=True)


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ["id", "title", "created_at", "updated_at"]


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            "id",
            "role",
            "content",
            "sources",
            "metadata",
            "sequence",
            "created_at",
        ]


class ConversationDetailSerializer(ConversationSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ["messages"]


class ConversationDetailResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = ConversationDetailSerializer()
