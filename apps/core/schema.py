"""Describe the existing response envelopes without changing runtime responses."""

from functools import lru_cache

from drf_spectacular.openapi import AutoSchema
from rest_framework import serializers


class SuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.JSONField(allow_null=True)


@lru_cache
def success_schema(serializer_class, many=False):
    name = serializer_class.__name__.removesuffix("Serializer")
    return type(
        f"{name}{'List' if many else ''}ResponseSerializer",
        (SuccessResponseSerializer,),
        {"data": serializer_class(many=many)},
    )


class ResourceSchema(AutoSchema):
    def _is_list_view(self, serializer=None):
        return self.method == "GET" and getattr(self.view, "paginated_list", False)

    def get_response_serializers(self):
        if self.method == "DELETE":
            return {200: SuccessResponseSerializer}
        if self.method in {"POST", "PUT", "PATCH"}:
            serializer = getattr(self.view, "write_response_serializer_class", None)
            serializer = serializer or self.view.get_serializer_class()
            return {201 if self.method == "POST" else 200: success_schema(serializer)}
        return super().get_response_serializers()
