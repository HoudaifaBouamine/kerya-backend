# app/services/bookings_service.py
from datetime import datetime
from typing import Dict, Optional
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied

from kerya.app.models.user import User

from ..models import Booking, Listing, BookingStatus
from ..serializers import BookingReadSerializer, BookingCreateSerializer


class BookingService:
    """
    Service layer for Bookings (house & hotel).
    Keeps controllers thin, encapsulates business rules.
    """

    # ---------- Public API used by controllers ----------

    def create_hotel_booking(self, data: Dict, user):
        validated = self._validate_payload(data, partial=False)
        listing = self._get_listing_or_404(validated["listing"].pk, expected_type="hotel")
        return self._create_booking(validated, listing, user)

    def get_booking_by_id(self, booking_id, user):
        return self._get_booking_as_guest_or_host(booking_id, user, role=user.role)

    def get_bookings(self, user: Optional[Dict] = None):
        qs = Booking.objects.select_related("listing", "guest").all()
        filters = {"guest": user}   # ✅ must be a dict
        qs = qs.filter(**filters)
        # return qs
        # if filters:
        #     qs = qs.filter(**filters)
        return qs.order_by("-created_at")

    def cancel_booking(self, booking_id, user, by="guest"):
        booking = self._get_booking_as_guest_or_host(booking_id, user, role=by)
        return self._cancel_booking(booking, by)

    # ---------- Internal helpers ----------

    def _validate_payload(self, data, partial: bool, instance: Optional[Booking] = None):
        ser = BookingCreateSerializer(instance=instance, data=data, partial=partial)
        ser.is_valid(raise_exception=True)
        return dict(ser.validated_data)

    def _get_listing_or_404(self, listing_id, expected_type=None) -> Listing:
        listing = get_object_or_404(Listing, pk=listing_id)
        if expected_type and listing.type != expected_type:
            raise ValidationError({"listing": [f"Listing must be of type '{expected_type}'"]})
        return listing

    def _get_booking_as_guest_or_host(self, booking_id, user : User, role="guest") -> Booking:
        booking = get_object_or_404(Booking, pk=booking_id)
        if role == "guest" and booking.guest.pk != user.pk:
            raise PermissionDenied("Only the guest who booked can access this booking.")
        if role == "host" and not (booking.host.pk == user.pk or booking.guest.pk == user.pk):
            raise PermissionDenied("Only the host can access this booking.")
        return booking

    # ---------- Business logic ----------

    def _check_availability(self, listing: Listing, start_date, end_date):
        overlapping = Booking.objects.filter(
            listing=listing,
            status__in=["requested", "accepted"],
            start_date__lt=end_date,
            end_date__gt=start_date,
        )
        if overlapping.exists():
            raise ValidationError({"dates": ["Listing is not available for the selected dates."]})

    # ---------- Create / Update / Cancel ----------

    @transaction.atomic
    def _create_booking(self, validated: Dict, listing: Listing, user):
        self._check_availability(listing, validated["start_date"], validated["end_date"])

        booking = Booking.objects.create(
            listing=listing,
            guest=user,
            start_date=validated["start_date"],
            end_date=validated["end_date"],
            currency=validated.get("currency", "DZD"),
            status=BookingStatus.ACCEPTED,
            decision_at=datetime.now(),
        )
        return booking

    @transaction.atomic
    def _update_booking(self, booking: Booking, validated: Dict):
        dirty = False
        for k, v in validated.items():
            if getattr(booking, k) != v:
                setattr(booking, k, v)
                dirty = True
        if dirty:
            try:
                booking.save()
            except IntegrityError as ex:
                raise ValidationError({"non_field_errors": [str(ex)]})
        return booking

    @transaction.atomic
    def _cancel_booking(self, booking: Booking, by: str):
        booking.status = BookingStatus.CANCELLED_HOST if by == "host" else BookingStatus.CANCELLED_GUEST # cancelled_host / cancelled_guest
        booking.cancelled_at = timezone.now()
        booking.save(update_fields=["status", "cancelled_at", "updated_at"])
        return booking
