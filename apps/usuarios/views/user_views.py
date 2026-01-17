from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
import json
import logging

from ..services.user_service import UserService

logger = logging.getLogger(__name__)

class UserListView(LoginRequiredMixin, TemplateView):
    """
    Vista principal: Tabla de usuarios (estilo ERP).
    """
    template_name = 'usuarios/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = UserService()
        
        # 1. Breadcrumbs
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': 'core:dashboard'},
            {'name': 'Usuarios'}
        ]
        context['page_title'] = 'Gestión de Usuarios'
        
        # Sidebar Menu handled by context_processor

        # 2. Obtener lista de usuarios completa
        # (Idealmente, usaríamos paginación de API, pero para usar el componente 
        #  de paginación de Django reutilizable, traemos la lista y paginamos localmente
        #  o creamos un adaptador. Por simplicidad en este paso, paginamos localmente)
        all_users = service.list_users()
        
        # 3. Paginación
        from django.core.paginator import Paginator
        paginator = Paginator(all_users, 15) # 15 usuarios por página
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['users'] = page_obj # La vista itera sobre page_obj
        context['page_obj'] = page_obj
        
        return context

class UserWizardDataView(LoginRequiredMixin, View):
    """
    API Interna: Retorna opciones para el Wizard (Grupos, Shares, etc)
    y procesa la creación COMPLETA del usuario (POST).
    """
    
    def get(self, request):
        """Retorna JSON con opciones para poblar selects"""
        service = UserService()
        options = service.get_wizard_options()
        return JsonResponse({'success': True, 'data': options})

    def post(self, request):
        """Recibe el payload JSON completo del Wizard y crea el usuario"""
        try:
            data = json.loads(request.body)
            service = UserService()
            result = service.create_user_wizard(data)

            if result.get('success'):
                # LOG AUDITORIA
                from apps.auditoria.services.audit_service import AuditService
                username = data.get('info', {}).get('name', 'Unknown')
                AuditService.log(
                    action='USER_CREATE_WIZARD',
                    description=f"Usuario '{username}' creado exitosamente vía Wizard.",
                    user=request.user,
                    request=request,
                    details=result
                )

            return JsonResponse(result)
        except Exception as e:
            logger.error(f"Error in user wizard POST: {e}")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

class UserDeleteView(LoginRequiredMixin, View):
    """
    API Interna: Elimina usuario
    """
    def post(self, request, username):
        service = UserService()
        result = service.delete_user(username)
        success = result.get('success', False)
        error = result.get('error', {})
        
        if success:
            # LOG AUDITORIA
            from apps.auditoria.services.audit_service import AuditService
            AuditService.log(
                action='DELETE_USER',
                description=f"Usuario '{username}' eliminado.",
                user=request.user,
                request=request,
                details={'deleted_user': username}
            )

        return JsonResponse({
            'success': success,
            'message': 'Usuario eliminado correctamente' if success else f'Error: {error}'
        })
