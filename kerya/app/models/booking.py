from django.utils import timezone
import uuid
from django.db import models
from django.forms import ValidationError
from ..models import User, Listing

class BookingStatus(models.TextChoices):
    REQUESTED = "requested", "Requested" # When guest request booking, waiting for host approval (pending)
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined" # When host decline the request
    CANCELLED_HOST = "cancelled_host", "Cancelled by Host" # When host cancel after approval
    CANCELLED_GUEST = "cancelled_guest", "Cancelled by Guest" # When guest cancel after approval
    CANCELLED_REQUEST = "cancelled_request", "Cancellation Requested" # When client cancel before host approval
    CHECKED_IN = "checked_in", "Checked In"
    CHECKED_OUT = "checked_out", "Checked Out"
    NO_SHOW = "no_show", "No Show"

class Booking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="bookings")
    guest = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings_made")
    start_date = models.DateField()
    end_date = models.DateField()
    nights = models.IntegerField()
    price_total = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="DZD")
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.REQUESTED,
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    decision_at = models.DateTimeField(null=True, blank=True)  # accept/decline
    cancelled_at = models.DateTimeField(null=True, blank=True) # host or guest cancellation
    check_in_at = models.DateTimeField(null=True, blank=True)
    check_out_at = models.DateTimeField(null=True, blank=True)
    
    @property
    def nights(self):
        return (self.end_date - self.start_date).days
    
    @property
    def host(self):
        return self.listing.owner
    
    def ensure_active(self):
        if not self.is_active:
            raise ValidationError("This booking is inactive and cannot be modified.")

    def save(self, *args, **kwargs):
        nightly_price = self.listing.price_per_night or 0
        self.price_total = self.nights * nightly_price
        self.is_active = self.status in [BookingStatus.REQUESTED, BookingStatus.ACCEPTED, BookingStatus.CHECKED_IN]
        super().save(*args, **kwargs)
        
    def cancel(self, user: User, by: str):
        self.ensure_active()
        if self.status == BookingStatus.REQUESTED:
            if by == "guest":
                self.status = BookingStatus.CANCELLED_REQUEST
            else:
                raise ValidationError("Only the guest can cancel a requested booking.")
        elif user.pk == self.host.pk:
            self.status = BookingStatus.CANCELLED_HOST
        elif user.pk == self.guest.pk:
            self.status = BookingStatus.CANCELLED_GUEST
        else:
            raise ValidationError("Only the host or guest can cancel this booking.")
            
        self.cancelled_at = timezone.now()
        self.is_active = False
        self.save(update_fields=["status", "cancelled_at", "updated_at", "is_active"])
        return self

    def accept(self):
        self.ensure_active()
        self.status = BookingStatus.ACCEPTED
        self.decision_at = timezone.now()
        self.is_active = True
        self.save(update_fields=["status", "decision_at", "updated_at", "is_active"])
        return self

    def decline(self):
        self.ensure_active()
        self.status = BookingStatus.DECLINED
        self.decision_at = timezone.now()
        self.is_active = False
        self.save(update_fields=["status", "decision_at", "updated_at", "is_active"])
        return self

    def check_in(self):
        self.ensure_active()
        self.status = BookingStatus.CHECKED_IN
        self.check_in_at = timezone.now()
        self.save(update_fields=["status", "check_in_at", "updated_at"])
        return self

    def check_out(self):
        self.ensure_active()
        self.status = BookingStatus.CHECKED_OUT
        self.check_out_at = timezone.now()
        self.save(update_fields=["status", "check_out_at", "updated_at"])
        return self
        
    def no_show(self):
        self.ensure_active()
        self.status = BookingStatus.NO_SHOW
        self.save(update_fields=["status", "updated_at"])
        return self