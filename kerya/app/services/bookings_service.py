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
        return self._create_hotel_booking(validated, listing, user)

    def create_house_booking(self, data: Dict, user):
        validated = self._validate_payload(data, partial=False)
        listing = self._get_listing_or_404(validated["listing"].pk, expected_type="house")
        return self._create_house_booking(validated, listing, user)

    def get_booking_by_id(self, booking_id, user, include_inactive: bool = False):
        """
        Retrieve booking enforcing guest/host permissions.
        By default inactive bookings are not returned unless include_inactive=True.
        """
        return self._get_booking_as_guest_or_host(booking_id, user, role=user.role, include_inactive=include_inactive)

    def list_all_bookings(self):
        """Admin only – list all bookings"""
        return Booking.objects.select_related("listing", "guest").order_by("-created_at")

    def list_guest_bookings(self, user: User, include_inactive=False):
        qs = Booking.objects.filter(guest=user).select_related("listing", "guest")
        if not include_inactive:
            qs = qs.filter(is_active=True)
        return qs.order_by("-created_at")

    def list_host_bookings(self, user: User, include_inactive=False):
        qs = Booking.objects.filter(listing__owner=user).select_related("listing", "guest")
        if not include_inactive:
            qs = qs.filter(is_active=True)
        return qs.order_by("-created_at")

    def user_can_view_booking(self, user: User, booking: Booking) -> bool:
        """Allow guest, host, or admin"""
        if booking.guest_id == user.id:
            return True
        if booking.listing.owner_id == user.id:
            return True
        if user.role == "admin":
            return True
        return False

    def cancel_booking(self, booking_id, user):
        by = user.role
        booking = self._get_booking_as_guest_or_host(booking_id, user, role=by, include_inactive=True)
        return booking.cancel(by=by, user=user)
    
    def accept_house_booking(self, booking_id, user):
        booking = self._get_booking_as_guest_or_host(booking_id, user, role="host", include_inactive=True)
        return booking.accept()

    def decline_house_booking(self, booking_id, user):
        booking = self._get_booking_as_guest_or_host(booking_id, user, role="host", include_inactive=True)
        return booking.decline()
    
    def check_in_booking(self, booking_id, user):
        booking = self._get_booking_as_guest_or_host(booking_id, user, role="host", include_inactive=True)
        return booking.check_in()
    
    def check_out_booking(self, booking_id, user):
        booking = self._get_booking_as_guest_or_host(booking_id, user, role="host", include_inactive=True)
        return booking.check_out()
    
    def no_show_booking(self, booking_id, user):
        booking = self._get_booking_as_guest_or_host(booking_id, user, role="host", include_inactive=True)
        return booking.no_show()
    

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
    def _create_hotel_booking(self, validated: Dict, listing: Listing, user):
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
    
    def _create_house_booking(self, validated: Dict, listing: Listing, user):
        self._check_availability(listing, validated["start_date"], validated["end_date"])

        booking = Booking.objects.create(
            listing=listing,
            guest=user,
            start_date=validated["start_date"],
            end_date=validated["end_date"],
            currency=validated.get("currency", "DZD"),
            status=BookingStatus.REQUESTED,
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