"""
URLs para la app Settings.
"""
from django.urls import path
from . import views

app_name = 'settings'

urlpatterns = [
    path('config/', views.NASConfigView.as_view(), name='config'),
    path('setup/', views.InitialSetupView.as_view(), name='initial_setup'),
    path('test-connection/', views.TestConnectionView.as_view(), name='test_connection'),
]
