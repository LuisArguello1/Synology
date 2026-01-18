from django.urls import path
from .views import ShareListView, ShareWizardDataView, ShareDeleteView

app_name = 'carpeta'

urlpatterns = [
    # Vista UI Principal
    path('', ShareListView.as_view(), name='list'),
    
    # APIs para Wizard y Acciones
    path('api/wizard/', ShareWizardDataView.as_view(), name='wizard_api'),
    path('api/delete/<str:name>/', ShareDeleteView.as_view(), name='delete'),
]
