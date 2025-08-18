from rest_framework import status, viewsets, permissions
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from ..serializers import (
    HouseCreateUpdateSerializer,
    HotelCreateUpdateSerializer,
    EventCreateUpdateSerializer,
    ListingReadSerializer,
)
from ..services.listings_service import ListingsService


# -------------------------
# HOUSE VIEWSET
# -------------------------

class HouseListingViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        request_body=HouseCreateUpdateSerializer,
        responses={201: ListingReadSerializer},
        operation_summary="Create House Listing",
    )
    def create(self, request):
        service = ListingsService()
        listing = service.create_house(request.data, request.user)
        return Response(ListingReadSerializer(listing).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        request_body=HouseCreateUpdateSerializer,
        responses={200: ListingReadSerializer, 404: "Not Found"},
        operation_summary="Update House Listing",
    )
    def update(self, request, pk=None):
        service = ListingsService()
        listing = service.update_house(pk, request.data, request.user)
        return Response(ListingReadSerializer(listing).data, status=status.HTTP_200_OK)


# -------------------------
# HOTEL VIEWSET
# -------------------------

class HotelListingViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        request_body=HotelCreateUpdateSerializer,
        responses={201: ListingReadSerializer},
        operation_summary="Create Hotel Listing",
    )
    def create(self, request):
        service = ListingsService()
        listing = service.create_hotel(request.data, request.user)
        return Response(ListingReadSerializer(listing).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        request_body=HotelCreateUpdateSerializer,
        responses={200: ListingReadSerializer, 404: "Not Found"},
        operation_summary="Update Hotel Listing",
    )
    def update(self, request, pk=None):
        service = ListingsService()
        listing = service.update_hotel(pk, request.data, request.user)
        return Response(ListingReadSerializer(listing).data, status=status.HTTP_200_OK)


# -------------------------
# EVENT VIEWSET
# -------------------------

class EventListingViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        request_body=EventCreateUpdateSerializer,
        responses={201: ListingReadSerializer},
        operation_summary="Create Event Listing",
    )
    def create(self, request):
        service = ListingsService()
        listing = service.create_event(request.data, request.user)
        return Response(ListingReadSerializer(listing).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        request_body=EventCreateUpdateSerializer,
        responses={200: ListingReadSerializer, 404: "Not Found"},
        operation_summary="Update Event Listing",
    )
    def update(self, request, pk=None):
        service = ListingsService()
        listing = service.update_event(pk, request.data, request.user)
        return Response(ListingReadSerializer(listing).data, status=status.HTTP_200_OK)


# -------------------------
# SHARED LISTINGS VIEWSET
# -------------------------

class ListingViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    type_param = openapi.Parameter(
        "type",
        openapi.IN_QUERY,
        description="Filter by listing type (house, hotel, event)",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        manual_parameters=[type_param],
        responses={200: ListingReadSerializer(many=True)},
        operation_summary="Get Listings",
    )
    def list(self, request):
        filters = {}
        listing_type = request.query_params.get("type")
        if listing_type:
            filters["type"] = listing_type

        service = ListingsService()
        listings = service.get_listings(filters)
        return Response(ListingReadSerializer(listings, many=True).data)

    @swagger_auto_schema(
        responses={200: ListingReadSerializer, 404: "Not Found"},
        operation_summary="Get Listing by ID",
    )
    def retrieve(self, request, pk=None):
        service = ListingsService()
        listing = service.get_listing_by_id(pk)
        return Response(ListingReadSerializer(listing).data)
