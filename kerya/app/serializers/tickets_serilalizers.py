from rest_framework import serializers
from ..models import (
    EventTicketType,
    EventTicket,
)
# We don't need EventBooking in the imports anymore
from ..models import Listing, User 


# -------------------------
# TICKET TYPE SERIALIZERS
# -------------------------
class EventTicketTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventTicketType
        fields = [
            "id", "event", "name", "description", "price", "currency",
            "total_quantity", "available_quantity", "max_per_user", "is_active",
            "created_at", "updated_at", "is_available", "sold_quantity"
        ]
        read_only_fields = ["id", "created_at", "updated_at", "is_available", "sold_quantity"]


class EventTicketTypeCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventTicketType
        fields = [
            "id", "event", "name", "description", "price", "currency",
            "total_quantity", "available_quantity", "max_per_user", "is_active"
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        if "available_quantity" not in validated_data or validated_data["available_quantity"] is None:
            validated_data["available_quantity"] = validated_data.get("total_quantity", 0)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        total_before = instance.total_quantity
        avail_before = instance.available_quantity
        instance = super().update(instance, validated_data)
        total_after = instance.total_quantity
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
    """
    Serializer for reading EventTicket data.
    """
    ticket_type = EventTicketTypeSerializer(read_only=True)
    
    class Meta:
        model = EventTicket
        fields = [
            "id", "user", "ticket_type", "first_name", "last_name", "email",
            "phone", "ticket_number", "qr_code", "status", "price",
            "created_at", "used_at", "can_be_used"
        ]
        read_only_fields = [
            "id", "user", "ticket_type", "ticket_number", "qr_code", 
            "status", "price", "created_at", "used_at", "can_be_used"
        ]


class EventTicketCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new EventTicket.
    It links to the ticket type and records the holder's details.
    """
    ticket_type_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = EventTicket
        fields = [
            "id", "ticket_type_id", "first_name", "last_name", "email", "phone"
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        user = self.context['request'].user
        ticket_type_id = validated_data.pop("ticket_type_id")

        try:
            with transaction.atomic():
                ticket_type = EventTicketType.objects.get(id=ticket_type_id)
                
                if not ticket_type.is_available:
                    raise serializers.ValidationError({"ticket_type_id": "This ticket type is no longer available."})
                
                tickets_purchased = EventTicket.objects.filter(
                    user=user, 
                    ticket_type=ticket_type, 
                    status__in=[EventTicket.EventTicketStatus.PENDING, EventTicket.EventTicketStatus.VALID]
                ).count()
                
                if tickets_purchased >= ticket_type.max_per_user:
                    raise serializers.ValidationError({"ticket_type_id": "You have reached the purchase limit for this ticket type."})
                
                ticket = EventTicket.objects.create(
                    user=user,
                    ticket_type=ticket_type,
                    **validated_data
                )
                
                ticket_type.available_quantity -= 1
                ticket_type.save()

        except EventTicketType.DoesNotExist:
            raise serializers.ValidationError({"ticket_type_id": "Invalid ticket type ID."})
            
        return ticket