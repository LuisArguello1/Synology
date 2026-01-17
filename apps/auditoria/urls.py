from django.urls import path
from .views.audit_views import AuditListView, AuditDetailView

app_name = 'auditoria'

urlpatterns = [
    path('', AuditListView.as_view(), name='list'),
    path('<int:pk>/', AuditDetailView.as_view(), name='detail'),
]
