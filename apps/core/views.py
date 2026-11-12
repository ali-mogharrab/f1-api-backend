from django.shortcuts import get_object_or_404
from rest_framework import filters, status
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from django_filters.rest_framework import DjangoFilterBackend

from apps.core.permissions import IsAdminOrReadOnly
from apps.core.responses import error_response, success_response
from apps.core.schema import ResourceSchema


class BaseListCreateAPIView(APIView):
    schema = ResourceSchema()
    paginated_list = True
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    permission_classes = [IsAdminOrReadOnly]

    model = None
    serializer_class = None

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = []
    search_fields = []
    ordering_fields = []
    ordering = None

    def get_queryset(self):
        if self.model is None:
            raise NotImplementedError("You must define model on the view.")

        queryset = self.model.objects.all()

        for backend in self.filter_backends:
            queryset = backend().filter_queryset(self.request, queryset, self)

        return queryset

    def paginate_queryset(self, queryset):
        paginator_class = api_settings.DEFAULT_PAGINATION_CLASS

        if paginator_class is None:
            return None, None

        paginator = paginator_class()
        page = paginator.paginate_queryset(queryset, self.request, view=self)

        return page, paginator

    def get_serializer_class(self):
        if self.serializer_class is None:
            raise NotImplementedError("You must define serializer_class on the view.")

        return self.serializer_class

    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("context", {"request": self.request})
        serializer_class = self.get_serializer_class()
        return serializer_class(*args, **kwargs)

    def get(self, request):
        queryset = self.get_queryset()
        page, paginator = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return success_response(
                data=serializer.data,
                message=f"{self.model.__name__} created successfully.",
                status_code=status.HTTP_201_CREATED,
            )

        return error_response(
            errors=serializer.errors,
            message="Validation error.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class BaseRetrieveUpdateDestroyAPIView(APIView):
    schema = ResourceSchema()
    permission_classes = [IsAdminOrReadOnly]

    model = None
    serializer_class = None

    def get_queryset(self):
        if self.model is None:
            raise NotImplementedError("You must define model on the view.")

        return self.model.objects.all()

    def get_object(self, pk):
        return get_object_or_404(self.get_queryset(), pk=pk)

    def get_serializer_class(self):
        if self.serializer_class is None:
            raise NotImplementedError("You must define serializer_class on the view.")

        return self.serializer_class

    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("context", {"request": self.request})
        serializer_class = self.get_serializer_class()
        return serializer_class(*args, **kwargs)

    def get(self, request, pk):
        instance = self.get_object(pk)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def put(self, request, pk):
        instance = self.get_object(pk)
        serializer = self.get_serializer(
            instance,
            data=request.data,
        )

        if serializer.is_valid():
            serializer.save()
            return success_response(
                data=serializer.data,
                message=f"{self.model.__name__} updated successfully.",
                status_code=status.HTTP_200_OK,
            )

        return error_response(
            errors=serializer.errors,
            message="Validation error.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    def patch(self, request, pk):
        instance = self.get_object(pk)
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            serializer.save()
            return success_response(
                data=serializer.data,
                message=f"{self.model.__name__} updated successfully.",
                status_code=status.HTTP_200_OK,
            )

        return error_response(
            errors=serializer.errors,
            message="Validation error.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, pk):
        instance = self.get_object(pk)
        instance.delete()

        return success_response(
            data=None,
            message=f"{self.model.__name__} deleted successfully.",
            status_code=status.HTTP_200_OK,
        )
