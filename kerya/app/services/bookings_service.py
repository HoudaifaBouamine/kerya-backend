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

    @staticmethod
    def ensure_active(booking: Booking):
        """
        Raise ValidationError (400) if booking is not active.
        """
        if not booking.is_active:
            raise ValidationError("This booking is inactive and cannot be modified.")

    # ---------- Public API used by controllers ----------

    def create_hotel_booking(self, data: Dict, user):
        validated = self._validate_payload(data, partial=False)
        listing = self._get_listing_or_404(validated["listing"].pk, expected_type="hotel")
        return self._create_booking(validated, listing, user)

    def get_booking_by_id(self, booking_id, user, include_inactive: bool = False):
        """
        Retrieve booking enforcing guest/host permissions.
        By default inactive bookings are not returned unless include_inactive=True.
        """
        return self._get_booking_as_guest_or_host(booking_id, user, role=user.role, include_inactive=include_inactive)

    def get_bookings(self, user: Optional[User] = None, include_inactive: bool = False):
        """
        Return bookings for the given user (guest). By default filter out inactive bookings.
        """
        qs = Booking.objects.select_related("listing", "guest").all()
        if user:
            qs = qs.filter(guest=user)
        if not include_inactive:
            qs = qs.filter(is_active=True)
        return qs.order_by("-created_at")

    def cancel_booking(self, booking_id, user, by="guest"):
        """
        Cancel booking: permission is checked, then booking is cancelled.
        We fetch with include_inactive=True to allow permission checking, but we still
        reject cancelling an already-inactive booking in _cancel_booking.
        """
        booking = self._get_booking_as_guest_or_host(booking_id, user, role=by, include_inactive=True)
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

    def _get_booking_as_guest_or_host(self, booking_id, user: User, role="guest", include_inactive: bool = False) -> Booking:
        """
        Centralized retrieval + permission checks.
        If include_inactive is False, inactive bookings are treated as not-found / invalid access.
        """
        booking = get_object_or_404(Booking, pk=booking_id)

        # Permission checks (keep existing logic)
        if role == "guest" and booking.guest.pk != user.pk:
            raise PermissionDenied("Only the guest who booked can access this booking.")
        if role == "host" and not (booking.host.pk == user.pk or booking.guest.pk == user.pk):
            raise PermissionDenied("Only the host can access this booking.")

        # Inactive guard
        if not include_inactive and not booking.is_active:
            raise ValidationError("This booking is inactive.")

        return booking

    # ---------- Business logic ----------

    def _check_availability(self, listing: Listing, start_date, end_date):
        """
        Ensure no overlapping active 'requested' or 'accepted' bookings exist.
        Inactive bookings are ignored.
        """
        overlapping = Booking.objects.filter(
            listing=listing,
            status__in=[BookingStatus.REQUESTED, BookingStatus.ACCEPTED],
            start_date__lt=end_date,
            end_date__gt=start_date,
            is_active=True,
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
            decision_at=timezone.now(),
            is_active=True,
        )
        return booking

    @transaction.atomic
    def _update_booking(self, booking: Booking, validated: Dict):
        """
        Update fields on a booking. Reject updates if booking is inactive.
        Also forbid updating 'is_active' through this path.
        """
        # forbid modifying inactive bookings
        self.ensure_active(booking)

        # protect is_active from being changed via payload
        if "is_active" in validated:
            raise ValidationError({"is_active": ["This field cannot be updated."]})

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
        """
        Cancel the booking: set status, cancelled_at and mark booking as inactive.
        Reject if already inactive.
        """
        # reject cancelling an already-inactive booking
        self.ensure_active(booking)

        booking.status = BookingStatus.CANCELLED_HOST if by == "host" else BookingStatus.CANCELLED_GUEST
        booking.cancelled_at = timezone.now()
        booking.is_active = False
        # include is_active in update_fields so DB write includes it
        try:
            booking.save(update_fields=["status", "cancelled_at", "updated_at", "is_active"])
        except IntegrityError as ex:
            raise ValidationError({"non_field_errors": [str(ex)]})
        return booking
