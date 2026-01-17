"""
URLs para la app Groups.
"""
from django.urls import path
from . import views

app_name = 'groups'

urlpatterns = [
    # Vistas principales
    path('', views.GroupListView.as_view(), name='list'),
    path('export/', views.GroupExportView.as_view(), name='export'),
    path('<int:pk>/delete/', views.GroupDeleteView.as_view(), name='delete'),
    
    # APIs para wizard (JSON responses)
    path('api/users/', views.get_available_users, name='api_users'),
    path('api/folders/', views.get_shared_folders, name='api_folders'),
    path('api/volumes/', views.get_volumes, name='api_volumes'),
    path('api/applications/', views.get_applications, name='api_applications'),
    path('api/create/', views.create_group_wizard, name='api_create'),
]
