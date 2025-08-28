import uuid
from django.db import models
from ..models import User, Listing

class BookingStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined"
    CANCELLED_HOST = "cancelled_host", "Cancelled by Host"
    CANCELLED_GUEST = "cancelled_guest", "Cancelled by Guest"

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
    decision_at = models.DateTimeField(null=True, blank=True)  # accept/decline
    cancelled_at = models.DateTimeField(null=True, blank=True) # host or guest cancellation
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    @property
    def nights(self):
        return (self.end_date - self.start_date).days
    
    @property
    def host(self):
        return self.listing.owner

    def save(self, *args, **kwargs):
        nightly_price = self.listing.price_per_night or 0
        self.price_total = self.nights * nightly_price
        self.is_active = self.status in [BookingStatus.REQUESTED, BookingStatus.ACCEPTED]
        super().save(*args, **kwargs)