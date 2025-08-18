from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from rest_framework import permissions
from drf_yasg import openapi
from drf_yasg.views import get_schema_view as swagger_get_schema_view
from drf_yasg.renderers import OpenAPIRenderer
from drf_yasg.renderers import SwaggerJSONRenderer

schema_view = swagger_get_schema_view(
    openapi.Info(
        title="Kerya API",
        default_version='v1',
        description="API documentation for Kerya project",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    authentication_classes=[],  # disable default auth
)

class JSONOnlySchemaView(schema_view):
    renderer_classes = (SwaggerJSONRenderer,)
    
urlpatterns = [
    path('', lambda request: redirect('schema-swagger-ui', permanent=False)),

    path('admin/', admin.site.urls),

    path('api/v1/', include([
        path('', include('kerya.app.urls')),
    ])),

    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    path('swagger.json',
            JSONOnlySchemaView.as_view(),
            name='schema-json'),
]

