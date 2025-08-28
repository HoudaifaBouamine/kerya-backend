# app/services/tickets_service.py

from typing import Dict, Optional, List
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db import models
from django.db.models import F
from rest_framework.exceptions import ValidationError, NotFound
from ..models import (
    EventTicketType,
    EventBooking,
    EventTicket,
)
from ..serializers import (
    EventTicketTypeCreateUpdateSerializer,
    EventTicketTypeSerializer,
    EventBookingCreateSerializer,
    EventBookingReadSerializer,
    EventTicketSerializer,
)
from ..models import Listing, User
from django.utils import timezone

class TicketsService:
    """
    Service layer for ticket types, bookings, and ticket operations.
    """

    # ---------- Ticket Types ----------
    def list_ticket_types(self, event_id: Optional[str] = None):
        qs = EventTicketType.objects.select_related("event").all()
        if event_id:
            qs = qs.filter(event_id=event_id)
        return qs.order_by("price")

    def get_ticket_type(self, pk):
        return get_object_or_404(EventTicketType, pk=pk)

    def create_ticket_type(self, data: Dict, user: User):
        # rely on serializer for basic validation
        ser = EventTicketTypeCreateUpdateSerializer(data=data)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return obj

    def update_ticket_type(self, pk, data: Dict, user: User):
        obj = self.get_ticket_type(pk)
        ser = EventTicketTypeCreateUpdateSerializer(instance=obj, data=data, partial=True)
        ser.is_valid(raise_exception=True)
        return ser.save()

    # ---------- Bookings ----------
    @transaction.atomic
    def create_booking(self, data: Dict, user: User) -> EventBooking:
        """
        Creates a booking in PENDING state and reserves quantities (decrementing available_quantity).
        Data must follow EventBookingCreateSerializer (including 'lines').
        """
        ser = EventBookingCreateSerializer(data=data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data

        event: Listing = v["event"]
        lines = v["lines"]  # list of dicts with ticket_type (uuid) and quantity

        # fetch ticket types and lock for update to prevent race
        tt_ids = [l["ticket_type"] for l in lines]
        tts = list(EventTicketType.objects.select_for_update().filter(id__in=tt_ids))

        if len(tts) != len(tt_ids):
            raise ValidationError({"lines": "One or more ticket types not found."})

        # Map id -> ticket_type
        tt_map = {str(tt.id): tt for tt in tts}

        total_tickets = 0
        total_amount = 0

        # Validate each requested line
        for line in lines:
            tid = str(line["ticket_type"])
            qty = int(line["quantity"])
            tt = tt_map.get(tid)
            if not tt:
                raise ValidationError({"lines": f"Ticket type {tid} not found."})
            # ensure ticket belongs to same event
            if tt.event_id != event.id:
                raise ValidationError({"lines": f"Ticket type {tt.id} does not belong to the given event."})
            if not tt.is_available:
                raise ValidationError({"lines": f"Ticket type '{tt.name}' is not available."})
            if qty > tt.available_quantity:
                raise ValidationError({"lines": f"Requested quantity {qty} exceeds available {tt.available_quantity} for '{tt.name}'."})
            if qty > tt.max_per_user:
                raise ValidationError({"lines": f"Requested quantity {qty} exceeds per-user limit {tt.max_per_user} for '{tt.name}'."})
            total_tickets += qty
            total_amount += float(tt.price) * qty

        # Create booking: reserve (decrement) available_quantity on types
        booking = EventBooking.objects.create(
            event=event,
            user=user,
            total_tickets=total_tickets,
            total_amount=total_amount,
            currency="DZD",
            customer_name=v.get("customer_name") or getattr(user, "full_name", ""),
            customer_email=v.get("customer_email") or getattr(user, "email", ""),
            customer_phone=v.get("customer_phone", ""),
            payment_method=v.get("payment_method", ""),
            status=EventBooking.PENDING if hasattr(EventBooking, 'PENDING') else "pending",
        )

        # store lines in a simple place: we don't have a line model - keep a simple approach:
        # decrement quantities now and store an internal mapping on booking via payment_reference? For now decrement only.
        for line in lines:
            tt = tt_map[str(line["ticket_type"])]
            qty = int(line["quantity"])
            # decrement available quantity
            tt.available_quantity = F('available_quantity') - qty
            tt.save(update_fields=["available_quantity"])

            # persist a quick relation for later (we'll store counts in EventBooking.payment_reference temporarily)
            # Better approach: create a proper BookingLine model. For now, store a serialized snapshot into booking.payment_reference
            # but that's hacky. Instead we will attach a minimal JSON into booking.payment_reference if empty (not ideal).
        # refresh tts from db (resolve F expressions)
        for tt in tts:
            tt.refresh_from_db()

        # Save a basic summary into payment_reference field to recover counts later (not ideal but keeps single-file change)
        # Format: "LINES|<ticket_type_id>:<qty>,<ticket_type_id>:<qty>"
        line_pairs = []
        for line in lines:
            line_pairs.append(f"{line['ticket_type']}:{line['quantity']}")
        booking.payment_reference = "LINES|" + ",".join(line_pairs)
        booking.save(update_fields=["payment_reference"])
        
        return booking

    def get_booking_by_id(self, booking_id):
        return get_object_or_404(EventBooking.objects.prefetch_related("tickets"), pk=booking_id)

    # ---------- Confirm booking (creates tickets) ----------
    @transaction.atomic
    def confirm_booking(self, booking_id: str, payment_method: str = "", payment_reference: str = "", actor: Optional[User] = None) -> EventBooking:
        booking = self.get_booking_by_id(booking_id)
        if booking.status == EventBooking.CONFIRMED:
            return booking
        if booking.status == EventBooking.CANCELLED:
            raise ValidationError({"status": "Cannot confirm a cancelled booking."})

        # Parse lines from payment_reference (see create_booking hack)
        if not booking.payment_reference or not booking.payment_reference.startswith("LINES|"):
            raise ValidationError({"booking": "Booking lines not available to create tickets."})
        payload = booking.payment_reference[len("LINES|"):]
        lines = []
        for part in payload.split(","):
            if not part:
                continue
            tid, qty = part.split(":")
            lines.append({"ticket_type": tid, "quantity": int(qty)})

        # Create tickets and mark booking confirmed
        created_tickets = []
        for line in lines:
            tt = get_object_or_404(EventTicketType, pk=line["ticket_type"])
            for _ in range(line["quantity"]):
                t = EventTicket.objects.create(
                    booking=booking,
                    ticket_type=tt,
                    holder_name=booking.customer_name,
                    holder_email=booking.customer_email
                )
                created_tickets.append(t)

        booking.status = EventBooking.CONFIRMED
        booking.confirmed_at = timezone.now()
        booking.payment_method = payment_method or booking.payment_method
        booking.payment_reference = payment_reference or booking.payment_reference
        booking.save(update_fields=["status", "confirmed_at", "payment_method", "payment_reference"])

        return booking

    # ---------- Cancel booking ----------
    @transaction.atomic
    def cancel_booking(self, booking_id: str, actor: Optional[User] = None) -> EventBooking:
        booking = self.get_booking_by_id(booking_id)
        if booking.status == EventBooking.CANCELLED:
            return booking

        # parse reserved lines to restore quantities
        if not booking.payment_reference or not booking.payment_reference.startswith("LINES|"):
            # try to recover counts from tickets
            tickets = list(booking.tickets.all())
            counts = {}
            for t in tickets:
                counts[str(t.ticket_type_id)] = counts.get(str(t.ticket_type_id), 0) + 1
        else:
            payload = booking.payment_reference[len("LINES|"):]
            counts = {}
            for part in payload.split(","):
                if not part:
                    continue
                tid, qty = part.split(":")
                counts[tid] = counts.get(tid, 0) + int(qty)

        # restore quantities with select_for_update
        for tid, qty in counts.items():
            tt = EventTicketType.objects.select_for_update().get(pk=tid)
            tt.available_quantity = F('available_quantity') + qty
            tt.save(update_fields=['available_quantity'])

        # If tickets exist, mark them canceled
        booking.tickets.update(status=EventTicket.CANCELLED)

        booking.status = EventBooking.CANCELLED
        booking.cancelled_at = timezone.now()
        booking.save(update_fields=["status", "cancelled_at"])

        return booking

    # ---------- Ticket usage ----------
    @transaction.atomic
    def use_ticket_by_qr(self, qr_or_ticket_number: str, actor: Optional[User] = None) -> EventTicket:
        """
        Mark a ticket as used when scanned. Accepts either qr_code or ticket_number.
        """
        try:
            ticket = EventTicket.objects.select_for_update().select_related("booking", "ticket_type").get(
                models.Q(qr_code=qr_or_ticket_number) | models.Q(ticket_number=qr_or_ticket_number)
            )
        except EventTicket.DoesNotExist:
            raise NotFound("Ticket not found.")

        if not ticket.can_be_used:
            raise ValidationError({"ticket": "Ticket cannot be used (invalid status or booking not confirmed)."})
        if ticket.status == EventTicket.USED:
            raise ValidationError({"ticket": "Ticket already used."})

        ticket.status = EventTicket.USED
        ticket.used_at = timezone.now()
        ticket.save(update_fields=["status", "used_at"])
        return ticket
