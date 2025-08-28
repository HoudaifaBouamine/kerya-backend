# bookings/serializers.py
from rest_framework import serializers
from ..models import Booking, Listing,User

class UserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]  # or whatever you want to expose

class BookingCreateSerializer(serializers.ModelSerializer):
    listing = serializers.PrimaryKeyRelatedField(queryset=Listing.objects.all())

    class Meta:
        model = Booking
        fields = ["listing", "start_date", "end_date"]
class BookingReadSerializer(serializers.ModelSerializer):
    guest = UserMiniSerializer(read_only=True)
    host = UserMiniSerializer(read_only=True)
    class Meta:
        model = Booking
        fields = [
            "id",
            "listing",
            "guest",
            "host",
            "start_date",
            "end_date",
            "nights",
            "price_total",
            "currency",
            "status",
            "created_at",
            "decision_at",
            "cancelled_at",
            "updated_at",
        ]
