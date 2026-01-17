"""
Views para la app Core.

Siguiendo arquitectura de views delgadas:
- Views solo coordinan services y renderización
- Lógica de negocio en services
- Contexto claro y bien estructurado
"""
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from .services.metrics_service import MetricsService


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Vista principal del dashboard.
    
    Muestra métricas del sistema, archivos recientes y actividad.
    View delgada: obtiene datos del service y renderiza.
    """
    template_name = 'core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener métricas del service
        metrics_service = MetricsService()
        context['metrics'] = metrics_service.get_dashboard_metrics()
        
        # Menu items para el sidebar (Usando Service)
        from apps.core.services.menu_service import MenuService
        context['menu_items'] = MenuService.get_menu_items(self.request.path)
        
        # Breadcrumbs
        context['breadcrumbs'] = [
            {'name': 'Dashboard'}
        ]
        
        # Título de la página
        context['page_title'] = 'Dashboard'
        
        return context
