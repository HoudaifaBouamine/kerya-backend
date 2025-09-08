from django.forms import ValidationError
from rest_framework import viewsets, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from kerya.app.models.booking import BookingStatus
from ..permissions import *


from ..serializers import BookingCreateSerializer, BookingReadSerializer
from ..services.bookings_service import BookingService

class BookingViewSet(viewsets.ViewSet):
    service = BookingService()
    permission_classes = [permissions.IsAuthenticated]
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
        operation_summary="List Bookings as Guest",
        tags=['Bookings']
    )
    @action(detail=False, url_path="guest")
    def guest_bookings(self, request):
        include_inactive = request.query_params.get("include_inactive", "false").lower() == "true"
        qs = self.service.list_guest_bookings(request.user, include_inactive=include_inactive)
        return Response(BookingReadSerializer(qs, many=True).data)

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
        operation_summary="List Bookings for Host Listings",
        tags=['Bookings']
    )
    @action(detail=False, methods=["get"], url_path="host", permission_classes=[IsHostOrAdmin])
    def host_bookings(self, request):
        include_inactive = request.query_params.get("include_inactive", "false").lower() == "true"
        qs = self.service.list_host_bookings(request.user, include_inactive=include_inactive)
        return Response(BookingReadSerializer(qs, many=True).data)

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
        operation_summary="List Bookings for Host Listings",
        tags=['Bookings']
    )
    @action(detail=False, methods=["get"], url_path="admin", permission_classes=[IsAdmin])
    def all_booking(self, request):
        qs = self.service.list_all_bookings()
        return Response(BookingReadSerializer(qs, many=True).data)


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


class HouseBookingViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    service = BookingService()

    @swagger_auto_schema(
        request_body=BookingCreateSerializer,
        responses={201: BookingReadSerializer},
        operation_summary="Create House Booking",
        tags=['Houses']
    )
    def create(self, request):
        booking = self.service.create_house_booking(request.data, request.user)
        return Response(BookingReadSerializer(booking).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        responses={200: BookingReadSerializer, 404: "Not Found"},
        operation_summary="Retrieve House Booking by ID",
        tags=['Houses']
    )
    def retrieve(self, request, pk=None):
        booking = self.service.get_booking_by_id(pk, request.user, include_inactive=True)
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
        operation_summary="Cancel a House Booking",
        tags=['Houses']
    )
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        by = request.query_params.get("by", "guest")  # default guest
        booking = self.service.cancel_booking(pk, request.user, by=by)
        return Response(BookingReadSerializer(booking).data, status=status.HTTP_200_OK)


    state_handlers = {
            "cancel": service.cancel_booking,
            BookingStatus.ACCEPTED: service.accept_house_booking,
            BookingStatus.DECLINED: service.decline_house_booking,
            BookingStatus.CHECKED_IN: service.check_in_booking,
            BookingStatus.CHECKED_OUT: service.check_out_booking,
            BookingStatus.NO_SHOW: service.no_show_booking,
    }
    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "state",
                openapi.IN_QUERY,
                description="new state of booking",
                type=openapi.TYPE_STRING,
                enum=["cancel",
                        BookingStatus.ACCEPTED, BookingStatus.DECLINED, BookingStatus.CHECKED_IN,
                        BookingStatus.CHECKED_OUT, BookingStatus.NO_SHOW],
                required=False,
            )
        ],
        responses={200: BookingReadSerializer, 403: "Forbidden", 404: "Not Found"},
        operation_summary="Cancel a House Booking",
        tags=['Houses']
    )
    @action(detail=True, methods=["patch"], url_path="set-state")
    def set_state(self, request, pk=None):
        booking = self.service.get_booking_by_id(pk, request.user, include_inactive=True)
        if(not booking): return Response({"Error":"Booking is not found."}, status=status.HTTP_404_NOT_FOUND)
        if(not booking.is_active): return Response({"Error":"Booking is not active."}, status=status.HTTP_400_BAD_REQUEST)
        
        state = request.query_params.get("state")
        user = request.user

        if not state:
            raise ValidationError("Query param 'state' is required.")
        
        if booking.status == BookingStatus.REQUESTED and user.role != "guest":
            return Response({"Error":"Only the guest can cancel a requested booking."})
                
        if state not in self.state_handlers:
            raise ValidationError(f"Invalid state '{state}'. Must be one of {list(self.state_handlers.keys())}")

        # Call the appropriate handler
        booking = self.state_handlers[state](booking_id=pk, user=user)
        return Response({"id": booking.pk, "state": state})