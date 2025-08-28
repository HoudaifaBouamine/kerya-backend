from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from ..serializers import BookingCreateSerializer, BookingReadSerializer
from ..services.bookings_service import BookingService


class HotelBookingViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        request_body=BookingCreateSerializer,
        responses={201: BookingReadSerializer},
        operation_summary="Create Hotel Booking",
        tags=['Hotels']
    )
    def create(self, request):
        service = BookingService()
        booking = service.create_hotel_booking(request.data, request.user)
        return Response(BookingReadSerializer(booking).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "include_inactive",
                openapi.IN_QUERY,
                description="Include inactive bookings (default: false)",
                type=openapi.TYPE_BOOLEAN,
                required=False,
            )
        ],
        responses={200: BookingReadSerializer(many=True)},
        operation_summary="List Hotel Bookings (guest or host)",
        tags=['Hotels']
    )
    def list(self, request):
        service = BookingService()
        include_inactive = request.query_params.get("include_inactive", "false").lower() == "true"
        bookings = service.get_bookings(request.user, include_inactive=include_inactive)
        return Response(BookingReadSerializer(bookings, many=True).data)

    @swagger_auto_schema(
        responses={200: BookingReadSerializer, 404: "Not Found"},
        operation_summary="Retrieve Hotel Booking by ID",
        tags=['Hotels']
    )
    def retrieve(self, request, pk=None):
        service = BookingService()
        include_inactive = True
        booking = service.get_booking_by_id(pk, request.user, include_inactive=include_inactive)
        return Response(BookingReadSerializer(booking).data)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "by",
                openapi.IN_QUERY,
                description="Who cancels the booking (guest or host)",
                type=openapi.TYPE_STRING,
                enum=["guest", "host"],
                required=False,
            )
        ],
        responses={200: BookingReadSerializer, 403: "Forbidden", 404: "Not Found"},
        operation_summary="Cancel a Hotel Booking",
        tags=['Hotels']
    )
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        service = BookingService()
        by = request.query_params.get("by", "guest")  # default guest
        booking = service.cancel_booking(pk, request.user, by=by)
        return Response(BookingReadSerializer(booking).data, status=status.HTTP_200_OK)
