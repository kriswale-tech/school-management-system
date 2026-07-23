from drf_spectacular.utils import inline_serializer
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


def paginated_schema(item_serializer, *, name='PaginatedResults'):
    """Build a drf-spectacular-compatible paginated response schema."""
    return inline_serializer(
        name=name,
        fields={
            'count': serializers.IntegerField(),
            'page_count': serializers.IntegerField(),
            'page': serializers.IntegerField(),
            'page_size': serializers.IntegerField(),
            'total_pages': serializers.IntegerField(),
            'start_index': serializers.IntegerField(),
            'end_index': serializers.IntegerField(),
            'has_next': serializers.BooleanField(),
            'has_previous': serializers.BooleanField(),
            'next': serializers.URLField(allow_null=True, required=False),
            'previous': serializers.URLField(allow_null=True, required=False),
            'results': item_serializer(many=True),
        },
    )


class StandardResultsSetPagination(PageNumberPagination):
    # Default page size
    page_size = 10

    # Allow clients to change it:
    # /api/users?page_size=25
    page_size_query_param = "page_size"

    # Prevent someone from requesting 1 million records
    max_page_size = 100

    # Page query parameter
    page_query_param = "page"

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "page_count": len(data),
            "page": self.page.number,
            "page_size": self.get_page_size(self.request),
            "total_pages": self.page.paginator.num_pages,
            "start_index": self.page.start_index(),
            "end_index": self.page.end_index(),
            "has_next": self.page.has_next(),
            "has_previous": self.page.has_previous(),
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })

    def get_paginated_response_schema(self, schema):
        """OpenAPI schema for Spectacular / schema generators."""
        return {
            "type": "object",
            "required": [
                "count",
                "page_count",
                "page",
                "page_size",
                "total_pages",
                "start_index",
                "end_index",
                "has_next",
                "has_previous",
                "next",
                "previous",
                "results",
            ],
            "properties": {
                "count": {
                    "type": "integer",
                    "example": 123,
                    "description": "Total number of items across all pages.",
                },
                "page_count": {
                    "type": "integer",
                    "example": 10,
                    "description": "Number of items on the current page.",
                },
                "page": {
                    "type": "integer",
                    "example": 1,
                    "description": "Current page number (1-indexed).",
                },
                "page_size": {
                    "type": "integer",
                    "example": 10,
                    "description": "Requested page size.",
                },
                "total_pages": {
                    "type": "integer",
                    "example": 13,
                    "description": "Total number of pages.",
                },
                "start_index": {
                    "type": "integer",
                    "example": 1,
                    "description": "1-based index of the first item on this page.",
                },
                "end_index": {
                    "type": "integer",
                    "example": 10,
                    "description": "1-based index of the last item on this page.",
                },
                "has_next": {"type": "boolean", "example": True},
                "has_previous": {"type": "boolean", "example": False},
                "next": {
                    "type": "string",
                    "nullable": True,
                    "format": "uri",
                    "example": (
                        f"http://api.example.org/accounts/?{self.page_query_param}=4"
                    ),
                },
                "previous": {
                    "type": "string",
                    "nullable": True,
                    "format": "uri",
                    "example": (
                        f"http://api.example.org/accounts/?{self.page_query_param}=2"
                    ),
                },
                "results": schema,
            },
        }
