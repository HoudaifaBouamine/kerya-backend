import uuid
from django.db import transaction
from django.db.models import Q, Min
from django.utils.text import slugify
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist

from ..models import Listing, ListingMedia


class ListingsService:

    @staticmethod
    def list_listings(filters: dict):
        """Return filtered listings."""
        qs = Listing.objects.exclude(status="deleted")

        # Filtering
        if "type" in filters:
            qs = qs.filter(type=filters["type"])

        if "wilaya" in filters:
            qs = qs.filter(wilaya__iexact=filters["wilaya"])

        if "municipality" in filters:
            qs = qs.filter(municipality__iexact=filters["municipality"])

        if "min_price" in filters:
            qs = qs.filter(min_price__gte=filters["min_price"])

        if "max_price" in filters:
            qs = qs.filter(min_price__lte=filters["max_price"])

        return qs

    @staticmethod
    def get_listing(pk: uuid.UUID) -> Listing:
        """Retrieve a single listing by ID."""
        try:
            return Listing.objects.get(pk=pk, status__in=["draft", "active", "hidden"])
        except ObjectDoesNotExist:
            raise ObjectDoesNotExist(f"Listing {pk} not found")

    @staticmethod
    @transaction.atomic
    def create_listing(user, data: dict) -> Listing:
        """Create a new listing and auto-generate slug."""
        slug_base = slugify(data["title"])
        slug = slug_base
        counter = 1
        while Listing.objects.filter(slug=slug).exists():
            slug = f"{slug_base}-{counter}"
            counter += 1

        listing = Listing.objects.create(
            owner=user,
            slug=slug,
            status="draft",  # always starts in draft
            **data
        )
        return listing

    @staticmethod
    @transaction.atomic
    def update_listing(user, pk: uuid.UUID, data: dict) -> Listing:
        """Update an existing listing (owner only)."""
        try:
            listing = Listing.objects.get(pk=pk)
        except ObjectDoesNotExist:
            raise ObjectDoesNotExist(f"Listing {pk} not found")

        if listing.owner != user:
            raise PermissionDenied("You do not own this listing")

        for field, value in data.items():
            setattr(listing, field, value)

        listing.save()
        return listing

    @staticmethod
    @transaction.atomic
    def delete_listing(user, pk: uuid.UUID):
        """Soft delete a listing (owner only)."""
        try:
            listing = Listing.objects.get(pk=pk)
        except ObjectDoesNotExist:
            raise ObjectDoesNotExist(f"Listing {pk} not found")

        if listing.owner != user:
            raise PermissionDenied("You do not own this listing")

        listing.status = "deleted"
        listing.save(update_fields=["status"])

    @staticmethod
    @transaction.atomic
    def add_media(user, pk: uuid.UUID, data: dict) -> ListingMedia:
        """Add media to listing (owner only)."""
        try:
            listing = Listing.objects.get(pk=pk)
        except ObjectDoesNotExist:
            raise ObjectDoesNotExist(f"Listing {pk} not found")

        if listing.owner != user:
            raise PermissionDenied("You do not own this listing")

        # Ensure only one primary
        if data.get("is_primary", False):
            ListingMedia.objects.filter(listing=listing, is_primary=True).update(is_primary=False)

        media = ListingMedia.objects.create(listing=listing, **data)
        return media
