# app/serializers.py  (append the following)

from rest_framework import serializers
from ..models import (
    EventTicketType,
    EventBooking,
    EventTicket,
)
from ..models import Listing  # adjust import if needed (relative to your layout)


# -------------------------
# TICKET TYPE SERIALIZERS
# -------------------------
class EventTicketTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventTicketType
        fields = [
            "id", "event", "name", "description", "price", "currency",
            "total_quantity", "available_quantity", "max_per_user", "is_active",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EventTicketTypeCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventTicketType
        fields = [
            "id", "event", "name", "description", "price", "currency",
            "total_quantity", "available_quantity", "max_per_user", "is_active"
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        # If available_quantity not provided, initialize it to total_quantity
        if "available_quantity" not in validated_data or validated_data["available_quantity"] is None:
            validated_data["available_quantity"] = validated_data.get("total_quantity", 0)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # If total_quantity changes, ensure available_quantity remains consistent
        total_before = instance.total_quantity
        avail_before = instance.available_quantity
        instance = super().update(instance, validated_data)
        total_after = instance.total_quantity
        # if total decreased below sold => clamp available to max(0, total - sold)
        sold = total_before - avail_before
        computed_available = max(0, total_after - sold)
        if instance.available_quantity != computed_available:
            instance.available_quantity = computed_available
            instance.save(update_fields=["available_quantity"])
        return instance


# -------------------------
# EVENT TICKET SERIALIZERS
# -------------------------
class EventTicketSerializer(serializers.ModelSerializer):
    ticket_type = EventTicketTypeSerializer(read_only=True)
    ticket_type_id = serializers.PrimaryKeyRelatedField(
        source="ticket_type", queryset=EventTicketType.objects.all(), write_only=True, required=False
    )

    class Meta:
        model = EventTicket
        fields = [
            "id", "booking", "ticket_type", "ticket_type_id",
            "ticket_number", "qr_code", "holder_name", "holder_email",
            "status", "created_at", "used_at"
        ]
        read_only_fields = [
            "id", "ticket_number", "qr_code", "status", "created_at", "used_at", "ticket_type"
        ]


# -------------------------
# BOOKING SERIALIZERS
# -------------------------
class BookingTicketLineSerializer(serializers.Serializer):
    ticket_type = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class EventBookingCreateSerializer(serializers.ModelSerializer):
    # Accept a "lines" list indicating which ticket types and quantities are requested
    lines = BookingTicketLineSerializer(write_only=True, many=True)

    class Meta:
        model = EventBooking
        fields = [
            "id", "event", "customer_name", "customer_email", "customer_phone",
            "payment_method", "lines", "total_tickets", "total_amount", "currency"
        ]
        read_only_fields = ["id", "total_tickets", "total_amount", "currency"]

    def validate_event(self, value):
        # ensure provided listing is an event
        if value.type != "event":
            raise serializers.ValidationError("Provided listing is not an event.")
        return value

    def validate(self, data):
        lines = data.get("lines", [])
        if not lines:
            raise serializers.ValidationError({"lines": "At least one ticket line is required."})
        return data


class EventBookingReadSerializer(serializers.ModelSerializer):
    tickets = EventTicketSerializer(many=True, read_only=True)
    class Meta:
        model = EventBooking
        fields = [
            "id", "event", "booking_reference", "total_tickets", "total_amount", "currency",
            "customer_name", "customer_email", "customer_phone",
            "status", "created_at", "confirmed_at", "cancelled_at", "payment_method", "payment_reference",
            "tickets"
        ]
        read_only_fields = fields
