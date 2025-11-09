from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Schema view for Swagger/OpenAPI
try:
    schema_view = get_schema_view(
        openapi.Info(
            title="ALX Travel App API",
            default_version='v1',
            description="API documentation for ALX Travel App",
            terms_of_service="https://www.example.com/terms/",
            contact=openapi.Contact(email="contact@example.com"),
            license=openapi.License(name="MIT License"),
        ),
        public=True,
        permission_classes=(permissions.AllowAny,),
    )
except Exception as e:
    print(f"Error creating schema view: {e}")
    schema_view = None

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('listings.urls')),  # Include your app's URLs
]

# Add Swagger URLs
if schema_view:
    urlpatterns += [
        re_path(r'^swagger(?P<format>\.json|\.yaml)$', 
                schema_view.without_ui(cache_timeout=0), 
                name='schema-json'),
        path('swagger/', 
             schema_view.with_ui('swagger', cache_timeout=0), 
             name='schema-swagger-ui'),
        path('redoc/', 
             schema_view.with_ui('redoc', cache_timeout=0), 
             name='schema-redoc'),
    ]
else:
    print("Warning: Swagger/OpenAPI documentation is not available due to configuration errors.")
