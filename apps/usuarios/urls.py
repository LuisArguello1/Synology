from django.urls import path
from .views import UserListView, UserWizardDataView, UserDeleteView

app_name = 'usuarios'

urlpatterns = [
    # Vista UI Principal
    path('', UserListView.as_view(), name='list'),
    
    # APIs para Wizard y Acciones
    path('api/wizard/', UserWizardDataView.as_view(), name='wizard_api'),
    path('api/delete/<str:username>/', UserDeleteView.as_view(), name='delete'),
]
