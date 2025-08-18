# app/services/listings_service.py
from typing import Dict, Optional
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError, PermissionDenied

from ..models import Listing, HouseDetail, HotelDetail, EventDetail
from ..serializers import (
    HouseCreateUpdateSerializer,
    HotelCreateUpdateSerializer,
    EventCreateUpdateSerializer,
)

class ListingsService:
    """
    Service layer for Listing CRUD with type-specific detail handling.
    Returns model instances / querysets; controllers handle serialization.
    """

    # ---------- Public API used by controllers ----------

    def create_house(self, data: Dict, user):
        validated_list, detail = self._validate_house_payload(data, partial=False)
        return self._create_with_detail("house", validated_list, detail, user)

    def update_house(self, listing_id, data: Dict, user):
        listing = self._get_owned_listing_or_403(listing_id, user, expected_type="house")
        validated_list, detail = self._validate_house_payload(data, partial=True, instance=listing)
        return self._update_with_detail(listing, validated_list, detail, "house")

    def create_hotel(self, data: Dict, user):
        validated_list, detail = self._validate_hotel_payload(data, partial=False)
        return self._create_with_detail("hotel", validated_list, detail, user)

    def update_hotel(self, listing_id, data: Dict, user):
        listing = self._get_owned_listing_or_403(listing_id, user, expected_type="hotel")
        validated_list, detail = self._validate_hotel_payload(data, partial=True, instance=listing)
        return self._update_with_detail(listing, validated_list, detail, "hotel")

    def create_event(self, data: Dict, user):
        validated_list, detail = self._validate_event_payload(data, partial=False)
        return self._create_with_detail("event", validated_list, detail, user)

    def update_event(self, listing_id, data: Dict, user):
        listing = self._get_owned_listing_or_403(listing_id, user, expected_type="event")
        validated_list, detail = self._validate_event_payload(data, partial=True, instance=listing)
        return self._update_with_detail(listing, validated_list, detail, "event")

    def get_listings(self, filters: Optional[Dict] = None):
        """
        Returns a queryset (controllers serialize with ListingReadSerializer).
        Default excludes status='deleted' unless explicitly asked for.
        """
        qs = (Listing.objects
              .select_related("house_detail", "hotel_detail", "event_detail", "owner")
              .prefetch_related("media")
              .all())

        filters = filters or {}
        include_deleted = filters.pop("include_deleted", False)
        if not include_deleted:
            qs = qs.exclude(status="deleted")

        if filters:
            qs = qs.filter(**filters)
        return qs.order_by("-created_at")

    def get_listing_by_id(self, listing_id):
        return (Listing.objects
                .select_related("house_detail", "hotel_detail", "event_detail", "owner")
                .prefetch_related("media")
                .get(pk=listing_id))

    # ---------- Internal helpers ----------

    def _get_owned_listing_or_403(self, listing_id, user, expected_type: Optional[str] = None) -> Listing:
        listing = get_object_or_404(Listing, pk=listing_id)
        if expected_type and listing.type != expected_type:
            raise ValidationError({"type": [f"Listing is '{listing.type}', expected '{expected_type}' for this endpoint."]})
        if listing.owner_id != getattr(user, "id", None):
            # If you want admins to bypass, add a check here (e.g., user.is_staff).
            raise PermissionDenied("You do not have permission to modify this listing.")
        return listing

    # --- Validation splitters (use your serializers just for validation) ---

    def _validate_house_payload(self, data, partial: bool, instance: Optional[Listing] = None):
        ser = HouseCreateUpdateSerializer(instance=instance, data=data, partial=partial)
        ser.is_valid(raise_exception=True)
        vd = dict(ser.validated_data)
        detail = vd.pop("detail", None)
        # Enforce correct type; ignore/override incoming 'type' if present
        vd["type"] = "house"
        return vd, detail

    def _validate_hotel_payload(self, data, partial: bool, instance: Optional[Listing] = None):
        ser = HotelCreateUpdateSerializer(instance=instance, data=data, partial=partial)
        ser.is_valid(raise_exception=True)
        vd = dict(ser.validated_data)
        detail = vd.pop("detail", None)
        vd["type"] = "hotel"
        return vd, detail

    def _validate_event_payload(self, data, partial: bool, instance: Optional[Listing] = None):
        ser = EventCreateUpdateSerializer(instance=instance, data=data, partial=partial)
        ser.is_valid(raise_exception=True)
        vd = dict(ser.validated_data)
        detail = vd.pop("detail", None)
        vd["type"] = "event"
        return vd, detail

    # --- Create / Update implementations ---

    @transaction.atomic
    def _create_with_detail(self, type, listing_data, detail_data, user):
        # remove unwanted keys
        listing_data = {
            k: v for k, v in listing_data.items()
            if k not in ["detail", "type", "owner"]
        }

        # now safe to create
        listing = Listing.objects.create(owner=user, type=type, **listing_data)

        if type == "house":
            HouseDetail.objects.create(listing=listing, **detail_data)
        elif type == "hotel":
            HotelDetail.objects.create(listing=listing, **detail_data)
        elif type == "event":
            EventDetail.objects.create(listing=listing, **detail_data)

        return listing

    @transaction.atomic
    def _update_with_detail(self, listing: Listing, listing_data: Dict, detail_data: Optional[Dict], expected_type: str):
        # Never allow type/owner changes here
        listing_data.pop("owner", None)
        listing_data.pop("type", None)

        # Apply scalar fields
        dirty = False
        for k, v in listing_data.items():
            if getattr(listing, k) != v:
                setattr(listing, k, v)
                dirty = True
        if dirty:
            try:
                listing.save()
            except IntegrityError as ex:
                raise ValidationError({"non_field_errors": [str(ex)]})

        # Upsert detail if provided
        if detail_data is not None:
            self._upsert_detail(expected_type, listing, detail_data)

        # Reload relations so controllers serialize fresh values
        return (Listing.objects
                .select_related("house_detail", "hotel_detail", "event_detail", "owner")
                .prefetch_related("media")
                .get(pk=listing.pk))

    # --- Detail creators/updaters ---

    def _create_detail(self, expected_type: str, listing: Listing, detail: Dict):
        if expected_type == "house":
            HouseDetail.objects.create(listing=listing, **detail)
        elif expected_type == "hotel":
            HotelDetail.objects.create(listing=listing, **detail)
        elif expected_type == "event":
            EventDetail.objects.create(listing=listing, **detail)
        else:
            raise ValidationError({"type": [f"Unsupported type '{expected_type}'"]})

    def _upsert_detail(self, expected_type: str, listing: Listing, detail: Dict):
        if expected_type == "house":
            HouseDetail.objects.update_or_create(listing=listing, defaults=detail)
        elif expected_type == "hotel":
            HotelDetail.objects.update_or_create(listing=listing, defaults=detail)
        elif expected_type == "event":
            EventDetail.objects.update_or_create(listing=listing, defaults=detail)
        else:
            raise ValidationError({"type": [f"Unsupported type '{expected_type}'"]})
