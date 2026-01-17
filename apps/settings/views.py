"""
Views para la app Settings.

Views delgadas que usan services para la lógica de negocio.
"""
from django.views.generic import UpdateView, View
from .views_setup import InitialSetupView  # Importar Setup View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.shortcuts import redirect
from .models import NASConfig
from .forms import NASConfigForm
from .services.connection_service import ConnectionService
import logging

logger = logging.getLogger(__name__)


class NASConfigView(LoginRequiredMixin, UpdateView):
    """
    Vista para editar la configuración del NAS.
    Si no existe configuración, crea una nueva.
    """
    model = NASConfig
    form_class = NASConfigForm
    template_name = 'settings/config_form.html'
    success_url = reverse_lazy('settings:config')
    
    def get_object(self, queryset=None):
        """Obtiene o crea la configuración activa."""
        obj, created = NASConfig.objects.get_or_create(
            is_active=True,
            defaults={
                'host': '192.168.1.100',
                'port': 5000,
                'protocol': 'https',
                'admin_username': 'admin',
                'admin_password': ''
            }
        )
        if created:
            logger.info("Creada nueva configuración NAS")
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Menu items para el sidebar (Global Context Processor)
        # context['menu_items'] = self.get_menu_items()
        
        # Breadcrumbs
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': 'core:dashboard'},
            {'name': 'Configuración NAS'}
        ]
        
        context['page_title'] = 'Configuración del NAS'
        
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Configuración guardada correctamente')
        logger.info(f"Configuración NAS actualizada: {form.instance.host}:{form.instance.port}")
        
        # LOG AUDITORIA
        from apps.auditoria.services.audit_service import AuditService
        AuditService.log(
            action='UPDATE_SETTINGS',
            description='Configuración del NAS actualizada',
            user=self.request.user,
            request=self.request,
            details={
                'host': form.instance.host,
                'port': form.instance.port,
                'user': form.instance.admin_username
            }
        )
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Error al guardar la configuración. Revisa los campos.')
        return super().form_invalid(form)
    
    def get_menu_items(self):
        """Genera items del menú."""
        current_path = self.request.path
        return [
            {
                'name': 'Dashboard',
                'icon': 'tachometer-alt',
                'url': 'core:dashboard',
                'active': current_path == reverse('core:dashboard')
            },
            {'separator': True, 'label': 'SISTEMA'},
            {
                'name': 'Archivos',
                'icon': 'folder',
                'url': 'core:dashboard',
                'active': False
            },
            {
                'name': 'Usuarios',
                'icon': 'users',
                'url': 'core:dashboard',
                'active': False
            },
            {'separator': True, 'label': 'CONFIGURACIÓN'},
            {
                'name': 'NAS Config',
                'icon': 'cog',
                'url': 'settings:config',
                'active': current_path == reverse('settings:config')
            },
        ]


class TestConnectionView(LoginRequiredMixin, View):
    """
    Vista para probar la conexión al NAS.
    Retorna JSON con el resultado.
    """
    
    def post(self, request, *args, **kwargs):
        """
        Ejecuta test de conexión y retorna JSON.
        
        Returns:
            JsonResponse con el resultado del test
        """
        try:
            # Usar el service para probar conexión
            service = ConnectionService()
            result = service.test_connection()
            
            logger.info(f"Test de conexión: {result['success']}")
            
            return JsonResponse(result)
            
        except ValueError as e:
            # No hay configuración activa
            logger.warning(f"Test de conexión sin config: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
        
        except Exception as e:
            logger.exception(f"Error en test de conexión: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error inesperado: {str(e)}'
            })
