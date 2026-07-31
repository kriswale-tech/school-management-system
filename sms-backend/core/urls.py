from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

v1_path = 'api/v1/'

urlpatterns = [
    # admin urls
    path(f'{v1_path}admin/', admin.site.urls),

    # drf spectacular urls (api docs)
    path(f'{v1_path}schema/', SpectacularAPIView.as_view(), name='schema'),
    path(f'{v1_path}docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # api urls
    path(f'{v1_path}accounts/', include('accounts.urls')),
    path(f'{v1_path}academics/', include('academics.urls')),
    path(f'{v1_path}schools/', include('schools.urls')),
    path(f'{v1_path}students/', include('students.urls')),
]
