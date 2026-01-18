from django.urls import path
from .views import (
    GroupListView, GroupDeleteView, GroupWizardOptionsView, 
    GroupWizardAPIView, GroupDetailView, GroupExportView
)

app_name = 'groups'

urlpatterns = [
    # Main List
    path('', GroupListView.as_view(), name='list'),
    
    # Actions
    path('delete/', GroupDeleteView.as_view(), name='delete'),
    path('export/', GroupExportView.as_view(), name='export'),
    
    # Wizard & API
    path('api/wizard/options/', GroupWizardOptionsView.as_view(), name='wizard_options'),
    path('api/wizard/', GroupWizardAPIView.as_view(), name='wizard_api'),
    path('api/detail/<str:name>/', GroupDetailView.as_view(), name='detail'),
]
