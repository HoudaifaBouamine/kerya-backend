from rest_framework import serializers
from ..models import Listing, HouseDetail, HotelDetail, EventDetail, ListingMedia


# -------------------------
# DETAIL SERIALIZERS
# -------------------------

class HouseDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = HouseDetail
        exclude = ["listing", "id"]


class HotelDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelDetail
        exclude = ["listing", "id"]


class EventDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventDetail
        exclude = ["listing", "id"]


class ListingMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingMedia
        exclude = ["listing"]


# -------------------------
# CREATE / UPDATE SERIALIZERS
# -------------------------

class BaseListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = [
            "id", "owner", "type", "title", "slug", "description",
            "wilaya", "municipality", "postal_code", "lat", "lng",
            "status", "capacity"
        ]
        read_only_fields = ["id", "owner"]


class HouseCreateUpdateSerializer(BaseListingSerializer):
    detail = HouseDetailSerializer(write_only=True)

    class Meta(BaseListingSerializer.Meta):
        fields = BaseListingSerializer.Meta.fields + ["detail"]

    def create(self, validated_data):
        detail_data = validated_data.pop("detail")
        # enforce correct type
        validated_data["type"] = "house"
        listing = Listing.objects.create(**validated_data)
        HouseDetail.objects.create(listing=listing, **detail_data)
        return listing

    def update(self, instance, validated_data):
        detail_data = validated_data.pop("detail", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.type = "house"  # enforce type consistency
        instance.save()
        if detail_data:
            HouseDetail.objects.update_or_create(listing=instance, defaults=detail_data)
        return instance


class HotelCreateUpdateSerializer(BaseListingSerializer):
    detail = HotelDetailSerializer(write_only=True)

    class Meta(BaseListingSerializer.Meta):
        fields = BaseListingSerializer.Meta.fields + ["detail"]

    def create(self, validated_data):
        detail_data = validated_data.pop("detail")
        validated_data["type"] = "hotel"
        listing = Listing.objects.create(**validated_data)
        HotelDetail.objects.create(listing=listing, **detail_data)
        return listing

    def update(self, instance, validated_data):
        detail_data = validated_data.pop("detail", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.type = "hotel"
        instance.save()
        if detail_data:
            HotelDetail.objects.update_or_create(listing=instance, defaults=detail_data)
        return instance


class EventCreateUpdateSerializer(BaseListingSerializer):
    detail = EventDetailSerializer(write_only=True)

    class Meta(BaseListingSerializer.Meta):
        fields = BaseListingSerializer.Meta.fields + ["detail"]

    def create(self, validated_data):
        detail_data = validated_data.pop("detail")
        validated_data["type"] = "event"
        listing = Listing.objects.create(**validated_data)
        EventDetail.objects.create(listing=listing, **detail_data)
        return listing

    def update(self, instance, validated_data):
        detail_data = validated_data.pop("detail", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.type = "event"
        instance.save()
        if detail_data:
            EventDetail.objects.update_or_create(listing=instance, defaults=detail_data)
        return instance


# -------------------------
# READ SERIALIZER
# -------------------------

class ListingReadSerializer(serializers.ModelSerializer):
    media = ListingMediaSerializer(many=True, read_only=True)
    detail = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id", "owner", "type", "title", "slug", "description",
            "wilaya", "municipality", "postal_code", "lat", "lng",
            "status", "capacity", "media", "created_at", "updated_at", "detail"
        ]

    def get_detail(self, obj):
        if obj.type == "house" and hasattr(obj, "house_detail"):
            return HouseDetailSerializer(obj.house_detail).data
        elif obj.type == "hotel" and hasattr(obj, "hotel_detail"):
            return HotelDetailSerializer(obj.hotel_detail).data
        elif obj.type == "event" and hasattr(obj, "event_detail"):
            return EventDetailSerializer(obj.event_detail).data
        return None

