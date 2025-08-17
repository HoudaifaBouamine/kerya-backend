import uuid
from django.db import models
from ..models import User, Listing

class Booking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="bookings")
    guest = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings_made")
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings_received")
    start_date = models.DateField()
    end_date = models.DateField()
    nights = models.IntegerField()
    price_total = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="DZD")
    status = models.CharField(max_length=20, choices=[("requested","Requested"),("accepted","Accepted"),("declined","Declined"),("cancelled","Cancelled")], default="requested")
    created_at = models.DateTimeField(auto_now_add=True)
