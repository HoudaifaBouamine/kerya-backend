import uuid
from django.utils.text import slugify
from django.db import models
from ..models import User

class Listing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="listings")
    type = models.CharField(
        max_length=10,
        choices=[("house", "House"), ("hotel", "Hotel"), ("event", "Event")],
    )
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True, null=True)
    description = models.TextField()
    wilaya = models.CharField(max_length=50)
    municipality = models.CharField(max_length=50)
    postal_code = models.CharField(max_length=10, null=True, blank=True)
    lat = models.FloatField()
    lng = models.FloatField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"),
            ("active", "Active"),
            ("hidden", "Hidden"),
            ("deleted", "Deleted"),
        ],
        default="draft",
    )
    capacity = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = str(self.id or uuid.uuid4())
        else:
            self.slug = slugify(self.slug)

        super().save(*args, **kwargs)
class HouseDetail(models.Model):
    listing = models.OneToOneField(Listing, on_delete=models.CASCADE, related_name="house_detail")
    house_type = models.CharField(max_length=20)  # Studio, F1..F6, etc.
    rooms = models.IntegerField()
    bathrooms = models.IntegerField()
    furnished = models.BooleanField(default=False)
    amenities = models.JSONField(default=dict)  # wifi, ac, etc.
    rules = models.JSONField(default=dict)
    price_per_night = models.DecimalField(max_digits=12, decimal_places=2)
    min_stay = models.IntegerField(default=1)
    contract_required = models.CharField(max_length=20, choices=[("none","None"),("mandatory","Mandatory"),("optional","Optional")], default="none")

class HotelDetail(models.Model):
    listing = models.OneToOneField(Listing, on_delete=models.CASCADE, related_name="hotel_detail")
    hotel_type = models.CharField(max_length=20)  # Hotel, Hostel, Palace
    stars = models.IntegerField(default=0)
    services = models.JSONField(default=dict)
    contact_phone = models.CharField(max_length=20)
    contact_email = models.EmailField()

class EventDetail(models.Model):
    listing = models.OneToOneField(Listing, on_delete=models.CASCADE, related_name="event_detail")
    event_type = models.CharField(max_length=50)
    date_start = models.DateField()
    date_end = models.DateField(null=True, blank=True)
    family_friendly = models.BooleanField(default=False)
    gender_preference = models.CharField(max_length=10, choices=[("mixed","Mixed"),("male","Male Only"),("female","Female Only")], default="mixed")
    contact_info = models.JSONField(default=dict)

class ListingMedia(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="media")
    media_type = models.CharField(max_length=10, choices=[("image","Image"),("video","Video")])
    object_key = models.CharField(max_length=255)  # S3/MinIO path
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
