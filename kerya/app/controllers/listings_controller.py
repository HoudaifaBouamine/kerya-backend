from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from ..serializers.listing_serializers import (
    ListingSerializer,
    ListingCreateSerializer,
    ListingMediaSerializer,
)
from ..services.listings_service import ListingsService


class ListingViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(
        operation_summary="List all listings",
        operation_description="Retrieve a list of listings with optional filters.",
        manual_parameters=[
            openapi.Parameter(
                "type", openapi.IN_QUERY, description="Filter by listing type (house, hotel, event)", type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                "wilaya", openapi.IN_QUERY, description="Filter by wilaya (region)", type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                "municipality", openapi.IN_QUERY, description="Filter by municipality", type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                "min_price", openapi.IN_QUERY, description="Filter by minimum price", type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                "max_price", openapi.IN_QUERY, description="Filter by maximum price", type=openapi.TYPE_INTEGER
            ),
        ],
        responses={200: ListingSerializer(many=True)},
    )
    def list(self, request):
        """GET /api/v1/listings/"""
        filters = request.query_params.dict()
        listings = ListingsService.list_listings(filters)
        return Response(ListingSerializer(listings, many=True).data)

    @swagger_auto_schema(
        operation_summary="Retrieve a listing",
        operation_description="Retrieve a single listing by ID.",
        responses={200: ListingSerializer()},
    )
    def retrieve(self, request, pk=None):
        """GET /api/v1/listings/{id}/"""
        listing = ListingsService.get_listing(pk)
        return Response(ListingSerializer(listing).data)

    @swagger_auto_schema(
        operation_summary="Create a new listing",
        operation_description="Create a new listing (host only).",
        request_body=ListingCreateSerializer,
        responses={201: ListingSerializer()},
    )
    def create(self, request):
        """POST /api/v1/listings/ (host only)"""
        serializer = ListingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = ListingsService.create_listing(request.user, serializer.validated_data)
        return Response(ListingSerializer(listing).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Update a listing",
        operation_description="Partially update a listing (owner only).",
        request_body=ListingCreateSerializer,
        responses={200: ListingSerializer()},
    )
    def partial_update(self, request, pk=None):
        """PATCH /api/v1/listings/{id}/ (owner only)"""
        serializer = ListingCreateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        listing = ListingsService.update_listing(request.user, pk, serializer.validated_data)
        return Response(ListingSerializer(listing).data)

    @swagger_auto_schema(
        operation_summary="Delete a listing",
        operation_description="Soft delete a listing (owner only).",
        responses={204: "No Content"},
    )
    def destroy(self, request, pk=None):
        """DELETE /api/v1/listings/{id}/ (soft delete)"""
        ListingsService.delete_listing(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        method="post",
        operation_summary="Upload listing media",
        operation_description="Upload media files for a listing (host only).",
        request_body=ListingMediaSerializer,
        responses={201: ListingMediaSerializer()},
    )
    @action(detail=True, methods=["post"])
    def media(self, request, pk=None):
        """POST /api/v1/listings/{id}/media/"""
        serializer = ListingMediaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        media = ListingsService.add_media(request.user, pk, serializer.validated_data)
        return Response(ListingMediaSerializer(media).data, status=status.HTTP_201_CREATED)
