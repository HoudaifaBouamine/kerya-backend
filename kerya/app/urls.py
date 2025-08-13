from django.urls import path, include
from rest_framework.routers import DefaultRouter
# from .views import exampleViewSet

router = DefaultRouter()
# router.register(r'example', exampleViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
