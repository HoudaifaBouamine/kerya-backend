from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .controllers import auth_controller

router = DefaultRouter()
# router.register(r'example', exampleViewSet)

auth_patterns = [
    path("register/", auth_controller.RegisterView.as_view()),
    path("login/", auth_controller.LoginView.as_view()),
    path("logout/", auth_controller.LogoutView.as_view()),
    path("send-phone-code/", auth_controller.SendPhoneCodeView.as_view()),
    path("verify-phone/", auth_controller.VerifyPhoneView.as_view()),
]

urlpatterns = [
    path("", include(router.urls)),
    path("auth/", include((auth_patterns, "auth"))),
]
