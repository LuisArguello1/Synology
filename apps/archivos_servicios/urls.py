"""
URLs para el módulo de Servicios de Archivos.
"""
from django.urls import path
from . import views

app_name = 'archivos_servicios'

urlpatterns = [
    # Vista principal
    path('', views.index, name='index'),
    
    # API Endpoints
    path('api/configs/', views.api_get_configs, name='api_configs'),
    path('api/smb/update/', views.api_update_smb, name='api_update_smb'),
    path('api/afp/update/', views.api_update_afp, name='api_update_afp'),
    path('api/nfs/update/', views.api_update_nfs, name='api_update_nfs'),
    path('api/ftp/update/', views.api_update_ftp, name='api_update_ftp'),
    path('api/rsync/update/', views.api_update_rsync, name='api_update_rsync'),
    path('api/advanced/update/', views.api_update_advanced, name='api_update_advanced'),
]
