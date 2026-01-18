from django.urls import path
from .views import ExplorerView, FileAPIView, FileUploadView

app_name = 'archivos'

urlpatterns = [
    path('', ExplorerView.as_view(), name='index'),
    path('api/files/', FileAPIView.as_view(), name='api_files'),
    path('api/upload/', FileUploadView.as_view(), name='api_upload'),
]
