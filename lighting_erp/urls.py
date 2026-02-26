from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from apps.common.jwt_views import (
    ERPTokenObtainPairView,
    ERPTokenRefreshView,
)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Frontend pages
    path('', TemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
    path('login/', TemplateView.as_view(template_name='login.html'), name='login'),
    path('projects/', TemplateView.as_view(template_name='projects.html'), name='projects'),
    path('projects/<int:pk>/', TemplateView.as_view(template_name='project_detail.html'), name='project_detail'),
    path('projects/<int:project_id>/areas/<int:area_id>/', TemplateView.as_view(template_name='area_products.html'), name='area_products'),
    path('projects/<int:project_id>/areas/<int:area_id>/configurations/add/', TemplateView.as_view(template_name='add_configuration.html'), name='add_configuration'),
    path('masters/', TemplateView.as_view(template_name='masters.html'), name='masters'),
    path('boq/', TemplateView.as_view(template_name='boq.html'), name='boq'),
    path('audit/logs/', TemplateView.as_view(template_name='audit_logs.html'), name='audit_logs_ui'),

    # 🔐 JWT AUTH (ADD THIS)
    path("api/auth/login/", ERPTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", ERPTokenRefreshView.as_view(), name="token_refresh"),

    # Swagger / OpenAPI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),

    # RBAC API
    path("api/", include("apps.rbac.urls")),

    # ERP APIs
    path('api/masters/', include('apps.masters.urls')),
    path('api/projects/', include('apps.projects.urls')),
    path('api/configurations/', include('apps.configurations.urls')),
    path('api/boq/', include('apps.boq.urls')),
    path("api/common/", include("apps.common.urls")),
    
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)