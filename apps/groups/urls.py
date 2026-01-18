from django.urls import path
from . import views

app_name = 'groups'

urlpatterns = [
    # Main List
    path('', views.GroupListView.as_view(), name='list'),
    
    # Actions
    path('delete/', views.GroupDeleteView.as_view(), name='delete'), # Now a POST endpoint mostly
    path('export/', views.GroupExportView.as_view(), name='export'),
    
    # API / Wizard
    path('api/create/', views.CreateGroupWizardView.as_view(), name='api_create'),
    path('api/users/', views.get_available_users, name='api_users'),
    path('api/shares/', views.get_shared_folders, name='api_shares'),
    path('api/volumes/', views.get_volumes, name='api_volumes'),
    path('api/apps/', views.get_applications, name='api_apps'),
    path('api/detail/<str:name>/', views.get_group_detail, name='api_detail'),
]
