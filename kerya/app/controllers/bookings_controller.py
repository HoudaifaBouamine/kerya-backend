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
    )
    def create(self, request):
        service = BookingService()
        booking = service.create_hotel_booking(request.data, request.user)
        return Response(BookingReadSerializer(booking).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        responses={200: BookingReadSerializer(many=True)},
        operation_summary="List Hotel Bookings (guest or host)",
    )
    def list(self, request):
        service = BookingService()
        bookings = service.get_bookings(request.user)
        return Response(BookingReadSerializer(bookings, many=True).data)

    @swagger_auto_schema(
        responses={200: BookingReadSerializer, 404: "Not Found"},
        operation_summary="Retrieve Hotel Booking by ID",
    )
    def retrieve(self, request, pk=None):
        service = BookingService()
        booking = service.get_booking_by_id(pk, request.user)
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
    )
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        service = BookingService()
        by = request.query_params.get("by", "guest")  # default guest
        booking = service.cancel_booking(pk, request.user, by=by)
        return Response(BookingReadSerializer(booking).data, status=status.HTTP_200_OK)
