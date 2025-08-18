from rest_framework import serializers
from ..models import Listing, ListingMedia

class ListingMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingMedia
        fields = [
            "id", "media_type", "object_key", "size_bytes", 
            "width", "height", "is_primary", "order", "moderation_status"
        ]


class ListingSerializer(serializers.ModelSerializer):
    media = ListingMediaSerializer(many=True, read_only=True)

    class Meta:
        model = Listing
        fields = [
            "id", "owner_id", "type", "title", "slug", "description",
            "status", "wilaya", "municipality", "postal_code",
            "lat", "lng", "capacity", "rooms", "bathrooms",
            "min_price", "currency", "amenities", "rules",
            "created_at", "updated_at", "media"
        ]
        read_only_fields = ["id", "created_at", "updated_at", "slug"]


class ListingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = [
            "type", "title", "description",
            "wilaya", "municipality", "postal_code", "lat", "lng",
            "capacity", "rooms", "bathrooms", "min_price",
            "currency", "amenities", "rules"
        ]
