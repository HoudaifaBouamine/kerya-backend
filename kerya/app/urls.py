from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .controllers import auth_controller
from .controllers import (
    HouseListingViewSet,
    HotelListingViewSet,
    EventListingViewSet,
    ListingViewSet,
    HotelBookingViewSet,
    HouseBookingViewSet,
    BookingViewSet,
)
from .controllers import (
    EventTicketTypeViewSet,
    EventBookingViewSet,
    EventTicketViewSet,
)

router = DefaultRouter()

# Listings
router.register(r"listings/houses", HouseListingViewSet, basename="house-listings")
router.register(r"listings/hotels", HotelListingViewSet, basename="hotel-listings")
router.register(r"listings/events", EventListingViewSet, basename="event-listings")
router.register(r"listings", ListingViewSet, basename="listings")

# Bookings
router.register(r"booking/hotel", HotelBookingViewSet, basename="hotel-booking")
router.register(r"booking/house", HouseBookingViewSet, basename="house-booking")
router.register(r"booking", BookingViewSet, basename="generic-booking")

# Tickets
router.register(r"tickets/types", EventTicketTypeViewSet, basename="event-ticket-types")
router.register(r"tickets/bookings", EventBookingViewSet, basename="event-bookings")
router.register(r"tickets", EventTicketViewSet, basename="event-tickets")

# Auth
auth_patterns = [
    path("register/", auth_controller.RegisterView.as_view()),
    path("login/email/", auth_controller.EmailLoginView.as_view()),
    path("login/phone/", auth_controller.PhoneLoginView.as_view()),
    path("logout/", auth_controller.LogoutView.as_view()),
    path("send-phone-code/", auth_controller.SendPhoneCodeView.as_view()),
    path("verify-phone/", auth_controller.VerifyPhoneView.as_view()),
]

urlpatterns = [
    path("", include(router.urls)),
    path("auth/", include((auth_patterns, "auth"), namespace="auth")),
]
