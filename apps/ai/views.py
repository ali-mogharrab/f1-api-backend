from django.conf import settings
from django.core.cache import caches
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.core.responses import success_response

from .exceptions import ConversationConflict, ConversationLimit
from .models import Conversation, Message
from .orchestration import analyze
from .serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    ConversationDetailResponseSerializer,
    ConversationDetailSerializer,
    ConversationSerializer,
    ErrorResponseSerializer,
)


class AIThrottle(UserRateThrottle):
    scope = "ai"
    cache = caches["ai"]

    def get_rate(self):
        return settings.AI_THROTTLE_RATE


class ChatView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIThrottle]

    @extend_schema(
        tags=["ai"],
        request=ChatRequestSerializer,
        responses={
            200: ChatResponseSerializer,
            **{
                code: ErrorResponseSerializer
                for code in (400, 401, 404, 409, 429, 503, 504)
            },
        },
        description="Analyze local F1 data and/or published articles. JWT authentication required. Sources are verified server-side. Failed provider calls do not append conversation turns.",
    )
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        conversation = None
        if payload.get("conversation_id"):
            conversation = get_object_or_404(
                Conversation, pk=payload["conversation_id"], user=request.user
            )
            if conversation.revision * 2 >= settings.AI_CONVERSATION_MAX_MESSAGES:
                raise ConversationLimit()
        revision = conversation.revision if conversation else 0
        result = analyze(payload["message"], conversation=conversation)
        with transaction.atomic():
            if conversation:
                # Optimistic concurrency: never hold a DB lock during network IO.
                changed = Conversation.objects.filter(
                    pk=conversation.pk, user=request.user, revision=revision
                ).update(
                    revision=revision + 1,
                    updated_at=timezone.now(),
                )
                if not changed:
                    raise ConversationConflict()
            else:
                conversation = Conversation.objects.create(
                    user=request.user, title=payload["message"][:100], revision=1
                )
            Message.objects.bulk_create(
                [
                    Message(
                        conversation=conversation,
                        role=Message.Role.USER,
                        content=payload["message"],
                        sequence=revision * 2,
                    ),
                    Message(
                        conversation=conversation,
                        role=Message.Role.ASSISTANT,
                        content=result.answer,
                        sources=result.sources,
                        metadata=result.metadata,
                        sequence=revision * 2 + 1,
                    ),
                ]
            )
        return success_response(
            {
                "conversation_id": str(conversation.pk),
                "answer": result.answer,
                "sources": result.sources,
                "metadata": result.metadata,
            }
        )


class ConversationListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer
    filter_backends = []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Conversation.objects.none()
        return Conversation.objects.filter(user=self.request.user)

    @extend_schema(
        tags=["ai"],
        description="Paginated conversations owned by the authenticated user.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ConversationDetailView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationDetailSerializer

    @extend_schema(
        tags=["ai"],
        responses={
            200: ConversationDetailResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    def get(self, request, pk):
        conversation = get_object_or_404(
            Conversation.objects.prefetch_related("messages"), pk=pk, user=request.user
        )
        return success_response(self.get_serializer(conversation).data)
