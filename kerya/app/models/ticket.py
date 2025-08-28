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


class EventBookingStatus(models.TextChoices):
    PENDING = "pending", "Pending Payment"
    CONFIRMED = "confirmed", "Confirmed"
    CANCELLED = "cancelled", "Cancelled"


class EventBooking(models.Model):
    """
    A booking transaction that can contain multiple tickets
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="event_bookings")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="event_bookings")
    
    # Booking Details
    booking_reference = models.CharField(max_length=20, unique=True)  # Human-readable reference
    total_tickets = models.PositiveIntegerField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="DZD")
    
    # Customer Info
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20, blank=True)
    
    # Status & Timestamps
    status = models.CharField(
        max_length=20,
        choices=EventBookingStatus.choices,
        default=EventBookingStatus.PENDING
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Payment tracking
    payment_method = models.CharField(max_length=50, blank=True)  # "card", "cash", "bank_transfer"
    payment_reference = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.booking_reference:
            # Generate human-readable reference: EVT-YYYYMMDD-XXXX
            import random
            date_part = timezone.now().strftime('%Y%m%d')
            random_part = str(random.randint(1000, 9999))
            self.booking_reference = f"EVT-{date_part}-{random_part}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.booking_reference} - {self.event.title}"


class EventTicketStatus(models.TextChoices):
    VALID = "valid", "Valid"
    USED = "used", "Used"
    CANCELLED = "cancelled", "Cancelled"


class EventTicket(models.Model):
    """
    Individual ticket instance within a booking
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(EventBooking, on_delete=models.CASCADE, related_name="tickets")
    ticket_type = models.ForeignKey(EventTicketType, on_delete=models.CASCADE, related_name="tickets")
    
    # Ticket Details
    ticket_number = models.CharField(max_length=30, unique=True)  # Unique ticket identifier
    qr_code = models.CharField(max_length=100, unique=True)  # For scanning at entrance
    
    # Ticket holder info
    holder_name = models.CharField(max_length=200)
    holder_email = models.EmailField(blank=True)
    
    # Status & Usage
    status = models.CharField(
        max_length=20,
        choices=EventTicketStatus.choices,
        default=EventTicketStatus.VALID
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)  # When ticket was scanned/used
    
    class Meta:
        ordering = ['created_at']
    
    def save(self, *args, **kwargs):
        if not self.ticket_number:
            # Generate unique ticket number: TKT-EVENTID-XXXXXX
            import random
            event_short = str(self.ticket_type.event_id)[-6:]
            random_part = str(random.randint(100000, 999999))
            self.ticket_number = f"TKT-{event_short}-{random_part}"
        
        if not self.qr_code:
            # Generate QR code data
            import hashlib
            qr_data = f"{self.ticket_number}-{self.booking.booking_reference}-{timezone.now().timestamp()}"
            self.qr_code = hashlib.sha256(qr_data.encode()).hexdigest()[:32]
        
        # Set holder info from booking if not set
        if not self.holder_name and self.booking:
            self.holder_name = self.booking.customer_name
            self.holder_email = self.booking.customer_email
        
        super().save(*args, **kwargs)
    
    @property
    def can_be_used(self):
        return (
            self.status == EventTicketStatus.VALID and 
            self.booking.status == EventBookingStatus.CONFIRMED
        )
    
    def __str__(self):
        return f"{self.ticket_number} - {self.ticket_type.name}"