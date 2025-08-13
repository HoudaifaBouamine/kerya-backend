from django.contrib import admin
from django.urls import include, path

from drf_yasg import openapi
from drf_yasg.views import get_schema_view as swagger_get_schema_view

schema_view = swagger_get_schema_view(
    openapi.Info(
        title="Kerya API",
        default_version='v1',
        description="API documentation for Kerya project",
    ),
    public=True
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('api/', include('kerya.app.urls')),
    path('api/v1', 
        include([
            path('', include('kerya.app.urls')),
            path('/swagger', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
        ])
    )
]
