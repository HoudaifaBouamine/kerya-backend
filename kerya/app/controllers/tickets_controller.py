# app/views/tickets_views.py

from rest_framework import viewsets, status, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from kerya.app.permissions import IsHostOrAdminOrAuthenticatedReadOnly

from ..services.tickets_service import TicketsService
from ..serializers import (
    EventTicketTypeSerializer,
    EventTicketTypeCreateUpdateSerializer,
    EventTicketSerializer,
    EventTicketCreateSerializer,
)
from ..models import EventTicketType, EventTicket

# -------------------------
# TICKET TYPE VIEWSET
# -------------------------
class EventTicketTypeViewSet(viewsets.ViewSet):
    permission_classes = [IsHostOrAdminOrAuthenticatedReadOnly]
    service = TicketsService()

    @swagger_auto_schema(
        request_body=EventTicketTypeCreateUpdateSerializer,
        responses={201: EventTicketTypeSerializer},
        operation_summary="Create a new ticket type",
        tags=['Tickets']
    )
    def create(self, request):
        tt = self.service.create_ticket_type(request.data)
        return Response(EventTicketTypeSerializer(tt).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        responses={200: EventTicketTypeSerializer(many=True)},
        operation_summary="List all ticket types",
        tags=['Tickets']
    )
    def list(self, request):
        event_id = request.query_params.get("event_id")
        qs = self.service.list_ticket_types(event_id)
        return Response(EventTicketTypeSerializer(qs, many=True).data)

    @swagger_auto_schema(
        responses={200: EventTicketTypeSerializer, 404: "Not Found"},
        operation_summary="Retrieve a ticket type by ID",
        tags=['Tickets']
    )
    def retrieve(self, request, pk=None):
        tt = self.service.get_ticket_type(pk)
        return Response(EventTicketTypeSerializer(tt).data)

    @swagger_auto_schema(
        request_body=EventTicketTypeCreateUpdateSerializer,
        responses={200: EventTicketTypeSerializer, 404: "Not Found"},
        operation_summary="Update a ticket type",
        tags=['Tickets']
    )
    def update(self, request, pk=None):
        tt = self.service.update_ticket_type(pk, request.data)
        return Response(EventTicketTypeSerializer(tt).data)


# -------------------------
# EVENT TICKET VIEWSET
# -------------------------
class EventTicketViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    service = TicketsService()

    @swagger_auto_schema(
        request_body=EventTicketCreateSerializer,
        responses={201: EventTicketSerializer},
        operation_summary="Create an individual ticket",
        tags=['Tickets']
    )
    def create(self, request):
        ticket = self.service.create_ticket(request.data, request.user)
        return Response(EventTicketSerializer(ticket).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        responses={200: EventTicketSerializer},
        operation_summary="Retrieve a ticket by ID",
        tags=['Tickets']
    )
    def retrieve(self, request, pk=None):
        ticket = self.service.get_ticket(pk)
        if ticket.user_id != request.user.id:
            raise PermissionDenied("You do not have access to this ticket.")
        return Response(EventTicketSerializer(ticket).data)

    @swagger_auto_schema(
        responses={200: EventTicketSerializer(many=True)},
        operation_summary="List current user's tickets",
        tags=['Tickets']
    )
    def list(self, request):
        if request.user.role != "admin":
            raise PermissionDenied("Only admin can view all tickets.")
        qs = self.service.list_all_tickets()
        return Response(EventTicketSerializer(qs, many=True).data)
    
    @swagger_auto_schema(
        responses={200: EventTicketSerializer(many=True)},
        operation_summary="List current user's tickets",
        tags=['Tickets']
    )
    @action(detail=False, methods=["get"], url_path="mine")
    def mine(self, request):
        qs = self.service.list_tickets_for_user(request.user)
        return Response(EventTicketSerializer(qs, many=True).data)
    
    @swagger_auto_schema(
        responses={200: EventTicketSerializer(many=True)},
        operation_summary="List current user's tickets",
        tags=['Tickets']
    )
    @action(detail=False, methods=["get"], url_path="my-events")
    def my_events(self, request):
        if request.user.role not in ["admin", "host"]:
            raise PermissionDenied("Only hosts or admins can view event tickets.")
        qs = self.service.list_tickets_for_host_events(request.user)
        return Response(EventTicketSerializer(qs, many=True).data)


# -------------------------
# TICKET SCANNING VIEWSET
# -------------------------
class TicketScanViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    service = TicketsService()
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "qr_code": openapi.Schema(type=openapi.TYPE_STRING, description="The QR code to scan"),
            },
            required=["qr_code"]
        ),
        responses={200: EventTicketSerializer},
        operation_summary="Use/scan a ticket (mark used)",
        tags=['Tickets']
    )
    def create(self, request):
        qr_code = request.data.get("qr_code")
        if not qr_code:
            return Response({"detail": "QR code is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        ticket = self.service.use_ticket_by_qr(qr_code, actor=request.user)
        return Response(EventTicketSerializer(ticket).data)