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
        
        # Para Alpine.js (Búsqueda y Selección)
        context['users_json'] = json.dumps([{
            'name': u['name'],
            'email': u.get('email', ''),
            'description': u.get('description', ''),
            'expired': u.get('expired', 'false')
        } for n, u in enumerate(all_users)])
        
        return context

class UserWizardDataView(LoginRequiredMixin, View):
    """
    API Interna: Retorna opciones para el Wizard (Grupos, Shares, etc)
    y procesa la creación COMPLETA del usuario (POST).
    """
    
    def get(self, request):
        """Retorna JSON con opciones para poblar selects o datos de un usuario específico"""
        service = UserService()
        
        # Si viene 'name', es para cargar datos de edición
        username = request.GET.get('name')
        if username:
            user_data = service.get_user(username)
            if user_data:
                return JsonResponse({'success': True, 'data': user_data})
            return JsonResponse({'success': False, 'message': 'Usuario no encontrado'}, status=404)
            
        options = service.get_wizard_options()
        return JsonResponse({'success': True, 'data': options})

    def post(self, request):
        """Recibe el payload JSON completo del Wizard y crea/actualiza el usuario"""
        try:
            data = json.loads(request.body)
            mode = data.get('mode', 'create')
            service = UserService()
            
            if mode == 'edit':
                result = service.update_user_wizard(data)
                action_type = 'USER_UPDATE_WIZARD'
            else:
                result = service.create_user_wizard(data)
                action_type = 'USER_CREATE_WIZARD'

            if result.get('success'):
                # LOG AUDITORIA
                from apps.auditoria.services.audit_service import AuditService
                username = data.get('info', {}).get('name', 'Unknown')
                AuditService.log(
                    action=action_type,
                    description=f"Usuario '{username}' {'actualizado' if mode == 'edit' else 'creado'} exitosamente vía Wizard.",
                    user=request.user,
                    request=request,
                    details={
                        'nas_result': result,
                        'user_affected': username,
                        'mode': mode
                    }
                )

            return JsonResponse(result)
        except Exception as e:
            logger.exception(f"Error in user wizard POST")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

class UserDeleteView(LoginRequiredMixin, View):
    """
    API Interna: Elimina usuario
    """
    def post(self, request, username):
        service = UserService()
        
        # Si username es 'batch', buscar en el body
        if username == 'batch':
            try:
                data = json.loads(request.body)
                usernames = data.get('usernames', [])
                if not usernames:
                    return JsonResponse({'success': False, 'message': 'No se seleccionaron usuarios'})
            except:
                return JsonResponse({'success': False, 'message': 'Invalid data'})
        else:
            usernames = [username]

        result = service.delete_user(usernames)
        success = result.get('success', False)
        error = result.get('error', {})
        
        if success:
            # LOG AUDITORIA
            from apps.auditoria.services.audit_service import AuditService
            desc = f"Usuarios eliminados: {', '.join(usernames)}" if len(usernames) > 1 else f"Usuario '{usernames[0]}' eliminado."
            AuditService.log(
                action='DELETE_USER',
                description=desc,
                user=request.user,
                request=request,
                details={'deleted_users': usernames}
            )

        return JsonResponse({
            'success': success,
            'message': 'Usuario eliminado correctamente' if success else f'Error: {error}'
        })
