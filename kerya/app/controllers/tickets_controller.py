# app/views/tickets_views.py

from rest_framework import viewsets, status, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from django.db import models
from drf_yasg import openapi

from ..services.tickets_service import TicketsService
from ..serializers import (
    EventTicketTypeSerializer,
    EventTicketTypeCreateUpdateSerializer,
    EventBookingCreateSerializer,
    EventBookingReadSerializer,
    EventTicketSerializer,
)
from ..models import EventTicketType, EventBooking, EventTicket

# -------------------------
# TICKET TYPE VIEWSET
# -------------------------
class EventTicketTypeViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(
        request_body=EventTicketTypeCreateUpdateSerializer,
        responses={201: EventTicketTypeSerializer},
        operation_summary="Create ticket type",
        tags=['Tickets']
    )
    def create(self, request):
        service = TicketsService()
        tt = service.create_ticket_type(request.data, request.user)
        return Response(EventTicketTypeSerializer(tt).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        responses={200: EventTicketTypeSerializer(many=True)},
        operation_summary="List ticket types",
        tags=['Tickets']
    )
    def list(self, request):
        event = request.query_params.get("event")
        service = TicketsService()
        q = service.list_ticket_types(event)
        return Response(EventTicketTypeSerializer(q, many=True).data)

    @swagger_auto_schema(
        responses={200: EventTicketTypeSerializer, 404: "Not Found"},
        operation_summary="Retrieve ticket type",
        tags=['Tickets']
    )
    def retrieve(self, request, pk=None):
        service = TicketsService()
        tt = service.get_ticket_type(pk)
        return Response(EventTicketTypeSerializer(tt).data)

    @swagger_auto_schema(
        request_body=EventTicketTypeCreateUpdateSerializer,
        responses={200: EventTicketTypeSerializer, 404: "Not Found"},
        operation_summary="Update ticket type",
        tags=['Tickets']
    )
    def update(self, request, pk=None):
        service = TicketsService()
        tt = service.update_ticket_type(pk, request.data, request.user)
        return Response(EventTicketTypeSerializer(tt).data)

# -------------------------
# BOOKING VIEWSET
# -------------------------
class EventBookingViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        request_body=EventBookingCreateSerializer,
        responses={201: EventBookingReadSerializer},
        operation_summary="Create event booking (reserve tickets)",
        tags=['Tickets']
    )
    def create(self, request):
        service = TicketsService()
        booking = service.create_booking(request.data, request.user)
        return Response(EventBookingReadSerializer(booking).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        responses={200: EventBookingReadSerializer},
        operation_summary="Get booking by id",
        tags=['Tickets']
    )
    def retrieve(self, request, pk=None):
        service = TicketsService()
        booking = service.get_booking_by_id(pk)
        # permission: owner or staff
        if booking.user_id != getattr(request.user, "id", None) and not request.user.is_staff:
            raise PermissionDenied("You do not have access to this booking.")
        return Response(EventBookingReadSerializer(booking).data)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter("status", openapi.IN_QUERY, description="Filter by status", type=openapi.TYPE_STRING)
        ],
        responses={200: EventBookingReadSerializer(many=True)},
        operation_summary="List current user's bookings",
        tags=['Tickets']
    )
    def list(self, request):
        qs = EventBooking.objects.select_related("event").prefetch_related("tickets").filter(user=request.user).order_by("-created_at")
        status_q = request.query_params.get("status")
        if status_q:
            qs = qs.filter(status=status_q)
        return Response(EventBookingReadSerializer(qs, many=True).data)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'payment_method': openapi.Schema(type=openapi.TYPE_STRING),
                'payment_reference': openapi.Schema(type=openapi.TYPE_STRING)
            }
        ),
        responses={200: EventBookingReadSerializer},
        operation_summary="Confirm booking (create tickets, mark confirmed)",
        tags=['Tickets']
    )
    def partial_update(self, request, pk=None):
        """
        Use PATCH to confirm a booking: { "action": "confirm", ... } or { "action": "cancel" }
        We'll use 'action' in body to decide operation.
        """
        service = TicketsService()
        action = request.data.get("action")
        if action == "confirm":
            payment_method = request.data.get("payment_method", "")
            payment_reference = request.data.get("payment_reference", "")
            booking = service.confirm_booking(pk, payment_method=payment_method, payment_reference=payment_reference, actor=request.user)
            return Response(EventBookingReadSerializer(booking).data)
        elif action == "cancel":
            booking = service.cancel_booking(pk, actor=request.user)
            return Response(EventBookingReadSerializer(booking).data)
        else:
            return Response({"detail": "Unknown action. Use 'confirm' or 'cancel'."}, status=status.HTTP_400_BAD_REQUEST)

# -------------------------
# TICKET VIEWSET (scan/use)
# -------------------------
class EventTicketViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter("q", openapi.IN_QUERY, description="qr_code or ticket_number to lookup", type=openapi.TYPE_STRING)
        ],
        responses={200: EventTicketSerializer},
        operation_summary="Get ticket by qr or id",
        tags=['Tickets']
    )
    def retrieve(self, request, pk=None):
        # pk can be ticket id; alternatively support q param
        service = TicketsService()
        if pk:
            try:
                ticket = EventTicket.objects.select_related("booking", "ticket_type").get(pk=pk)
            except EventTicket.DoesNotExist:
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            q = request.query_params.get("q")
            if not q:
                return Response({"detail": "Provide ticket id or q param."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                ticket = EventTicket.objects.select_related("booking", "ticket_type").get(models.Q(qr_code=q) | models.Q(ticket_number=q))
            except EventTicket.DoesNotExist:
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # permission: booking owner or staff
        if ticket.booking.user_id != getattr(request.user, "id", None) and not request.user.is_staff:
            raise PermissionDenied("You do not have access to this ticket.")
        return Response(EventTicketSerializer(ticket).data)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={"qr_or_ticket": openapi.Schema(type=openapi.TYPE_STRING)}
        ),
        responses={200: EventTicketSerializer},
        operation_summary="Use/scan a ticket (mark used)",
        tags=['Tickets']
    )
    def create(self, request):
        q = request.data.get("qr_or_ticket")
        if not q:
            return Response({"detail": "qr_or_ticket required."}, status=status.HTTP_400_BAD_REQUEST)
        service = TicketsService()
        ticket = service.use_ticket_by_qr(q, actor=request.user)
        return Response(EventTicketSerializer(ticket).data)
