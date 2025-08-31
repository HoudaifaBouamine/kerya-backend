# kerya/app/models/event_ticket.py

import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from . import User, Listing

class EventTicketType(models.Model):
    """
    Different ticket categories for an event (VIP, General, Early Bird, etc.)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="ticket_types")
    
    # Basic Info
    name = models.CharField(max_length=100)  # "VIP", "General Admission", "Early Bird"
    description = models.TextField(blank=True)
    
    # Pricing
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    currency = models.CharField(max_length=10, default="DZD")
    
    # Capacity
    total_quantity = models.PositiveIntegerField()
    available_quantity = models.PositiveIntegerField()  # decreases with sales
    
    # Purchase limits
    max_per_user = models.PositiveIntegerField(default=10)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['price']
        unique_together = ['event', 'name']
    
    @property
    def is_available(self):
        return self.is_active and self.available_quantity > 0
    
    @property
    def sold_quantity(self):
        return self.total_quantity - self.available_quantity
    
    def __str__(self):
        return f"{self.event.title} - {self.name}"


class EventTicketStatus(models.TextChoices):
    PENDING = "pending", "Pending Payment"
    VALID = "valid", "Valid"
    USED = "used", "Used"
    CANCELLED = "cancelled", "Cancelled"


class EventTicket(models.Model):
    """
    Individual ticket instance for a single user
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="event_tickets")
    ticket_type = models.ForeignKey(EventTicketType, on_delete=models.CASCADE, related_name="tickets")
    
    # Ticket holder info
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=200, null=True)
    phone = models.CharField(max_length=20, null=True)
    
    # Ticket Details
    ticket_number = models.CharField(max_length=30, unique=True)  # Unique ticket identifier
    qr_code = models.CharField(max_length=100, unique=True)  # For scanning at entrance
    
    # Status & Usage
    status = models.CharField(
        max_length=20,
        choices=EventTicketStatus.choices,
        default=EventTicketStatus.PENDING
    )
    
    # Pricing
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)  # When ticket was scanned/used
    
    class Meta:
        ordering = ['created_at']
    
    def save(self, *args, **kwargs):
        if not self.price:
            self.price = self.ticket_type.price

        if not self.ticket_number:
            # Generate unique ticket number: TKT-EVENTID-XXXXXX
            import random
            event_short = str(self.ticket_type.event_id)[-6:]
            random_part = str(random.randint(100000, 999999))
            self.ticket_number = f"TKT-{event_short}-{random_part}"
        
        if not self.qr_code:
            # Generate QR code data
            import hashlib
            qr_data = f"{self.ticket_number}-{self.email}-{timezone.now().timestamp()}"
            self.qr_code = hashlib.sha256(qr_data.encode()).hexdigest()[:32]
        
        super().save(*args, **kwargs)
    
    @property
    def can_be_used(self):
        return self.status == EventTicketStatus.VALID
    
    def __str__(self):
        return f"{self.ticket_number} - {self.ticket_type.name}"