# bookings/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from ..serializers import BookingCreateUpdateSerializer, BookingReadSerializer
from ..services.bookings_service import BookingService


class HotelBookingViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        request_body=BookingCreateUpdateSerializer,
        responses={201: BookingReadSerializer},
        operation_summary="Create Hotel Booking",
    )
    def create(self, request):
        service = BookingService()
        booking = service.create_hotel_booking(request.data, request.user)
        return Response(BookingReadSerializer(booking).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        request_body=BookingCreateUpdateSerializer,
        responses={200: BookingReadSerializer, 404: "Not Found"},
        operation_summary="Update Hotel Booking",
    )
    def update(self, request, pk=None):
        service = BookingService()
        booking = service.update_hotel_booking(pk, request.data, request.user)
        return Response(BookingReadSerializer(booking).data, status=status.HTTP_200_OK)

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
        return Response(BookingReadSerializer(  booking).data)
