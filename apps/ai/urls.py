from django.urls import path

from .views import ChatView, ConversationDetailView, ConversationListView

app_name = "ai"
urlpatterns = [
    path("chat/", ChatView.as_view(), name="chat"),
    path("conversations/", ConversationListView.as_view(), name="conversation-list"),
    path(
        "conversations/<uuid:pk>/",
        ConversationDetailView.as_view(),
        name="conversation-detail",
    ),
]
