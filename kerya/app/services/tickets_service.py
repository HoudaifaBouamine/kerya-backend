# app/services/tickets_service.py

from typing import Dict, Optional, List
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db import models
from django.db.models import F
from rest_framework.exceptions import ValidationError, NotFound
from ..models import (
    EventTicketType,
    EventTicket,
)
from ..serializers import (
    EventTicketTypeCreateUpdateSerializer,
    EventTicketTypeSerializer,
    EventTicketCreateSerializer,
    EventTicketSerializer,
)
from ..models import Listing, User
from django.utils import timezone

class TicketsService:
    """
    Service layer for ticket types and ticket operations.
    """

    # ---------- Ticket Types ----------
    def list_ticket_types(self, event_id: Optional[str] = None):
        """
        Lists ticket types, optionally filtered by event ID.
        """
        qs = EventTicketType.objects.select_related("event").all()
        if event_id:
            qs = qs.filter(event_id=event_id)
        return qs.order_by("price")

    def get_ticket_type(self, pk):
        """
        Retrieves a single ticket type by its primary key.
        """
        return get_object_or_404(EventTicketType, pk=pk)

    def create_ticket_type(self, data: Dict):
        """
        Creates a new ticket type for an event.
        """
        ser = EventTicketTypeCreateUpdateSerializer(data=data)
        ser.is_valid(raise_exception=True)
        return ser.save()

    def update_ticket_type(self, pk, data: Dict):
        """
        Updates an existing ticket type.
        """
        obj = self.get_ticket_type(pk)
        ser = EventTicketTypeCreateUpdateSerializer(instance=obj, data=data, partial=True)
        ser.is_valid(raise_exception=True)
        return ser.save()

    # ---------- Tickets ----------
    @transaction.atomic
    def create_ticket(self, data: Dict, user: User) -> EventTicket:
        """
        Creates a single new ticket for a user. This also handles decrementing
        the available quantity on the associated EventTicketType.
        """
        ser = EventTicketCreateSerializer(data=data, context={'request': {'user': user}})
        ser.is_valid(raise_exception=True)
        return ser.save()

    def list_all_tickets(self):
        """Admin only – list all tickets."""
        return EventTicket.objects.select_related("ticket_type", "user").order_by("-created_at")

    def list_tickets_for_user(self, user: User):
        """Tickets booked by the given user."""
        return EventTicket.objects.filter(user=user).select_related("ticket_type").order_by("-created_at")

    def list_tickets_for_host_events(self, host: User):
        """Tickets booked for events owned by host/admin."""
        return EventTicket.objects.filter(
            ticket_type__event__created_by=host  # assumes Listing has created_by=User
        ).select_related("ticket_type", "user").order_by("-created_at")

    def user_can_view_ticket(self, user: User, ticket: EventTicket) -> bool:
        """Owner or event host/admin can view."""
        if ticket.user_id == user.id:
            return True
        if user.role in ["admin", "host"] and ticket.ticket_type.event.created_by_id == user.id:
            return True
        return False
    
    def use_ticket(self, ticket_id: str, user: User) -> EventTicket:
        """
        Marks a ticket as 'used'. Requires the user to have permission.
        """
        with transaction.atomic():
            ticket = get_object_or_404(EventTicket.objects.select_for_update(), pk=ticket_id)
            
            # Additional logic can be added here, e.g., only event staff can use a ticket
            # if user.is_staff or user.is_event_organizer...
            # For now, we assume a separate endpoint/permission system for this.

            if not ticket.can_be_used:
                raise ValidationError({"detail": "This ticket cannot be used."})

            ticket.status = EventTicket.EventTicketStatus.USED
            ticket.used_at = timezone.now()
            ticket.save(update_fields=["status", "used_at"])
            return ticket

    def use_ticket_by_qr(self, qr_or_ticket_number: str, actor: Optional[User] = None) -> EventTicket:
        """
        Marks a ticket as used when scanned. Accepts either qr_code or ticket_number.
        """
        try:
            ticket = EventTicket.objects.select_for_update().select_related("ticket_type").get(
                models.Q(qr_code=qr_or_ticket_number) | models.Q(ticket_number=qr_or_ticket_number)
            )
        except EventTicket.DoesNotExist:
            raise NotFound("Ticket not found.")

        if not ticket.can_be_used:
            raise ValidationError({"ticket": "Ticket cannot be used (invalid status)."})
        if ticket.status == EventTicket.EventTicketStatus.USED:
            raise ValidationError({"ticket": "Ticket already used."})

        ticket.status = EventTicket.EventTicketStatus.USED
        ticket.used_at = timezone.now()
        ticket.save(update_fields=["status", "used_at"])
        return ticket