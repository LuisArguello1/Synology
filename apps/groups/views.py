"""
Vistas para la app Groups.

Refactorizado:
- Eliminada dependencia de modelos locales (Group, SharedFolder, etc).
- Implementado patrón Service para consumo de API NAS.
"""
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect
import json
import csv
import logging

from .services.group_service import GroupService
from apps.core.services.resource_service import ResourceService
from apps.archivos.services.file_service import FileService # Reuse logic if needed or use ResourceService

logger = logging.getLogger(__name__)

class GroupListView(LoginRequiredMixin, TemplateView):
    """
    Vista para listar grupos.
    Obtiene datos del NAS via GroupService.
    Soporta respuesta JSON cuando se solicita con ?format=json
    """
    template_name = 'groups/group_list.html'
    
    def get(self, request, *args, **kwargs):
        """Override get() to support JSON responses"""
        # Check if JSON format is requested
        if request.GET.get('format') == 'json':
            try:
                service = GroupService()
                groups = service.list_groups()
                
                # Apply search filter if provided
                search = request.GET.get('search', '').strip().lower()
                if search:
                    groups = [
                        g for g in groups 
                        if search in g.get('name', '').lower() or search in g.get('description', '').lower()
                    ]
                
                return JsonResponse({'groups': groups})
            except Exception as e:
                logger.exception("Error listing groups")
                return JsonResponse({'groups': [], 'error': str(e)}, status=500)
        
        # Default: render HTML template
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Servicio
        service = GroupService()
        all_groups = service.list_groups()
        
        # Búsqueda local en la lista devuelta
        search = self.request.GET.get('search', '').strip().lower()
        if search:
            all_groups = [
                g for g in all_groups 
                if search in g.get('name', '').lower() or search in g.get('description', '').lower()
            ]
        
        context['groups'] = all_groups
        context['search_query'] = search
        context['page_title'] = 'Administración de Grupos (NAS)'
        
        # Breadcrumbs
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': 'core:dashboard'},
            {'name': 'Grupos'}
        ]
        
        return context

class GroupDeleteView(LoginRequiredMixin, View):
    """
    Vista para eliminar un grupo via POST.
    """
    def get(self, request):
        """Listar grupos"""
        service = GroupService()
        if request.GET.get('format') == 'json':
            try:
                groups = service.list_groups()
                return JsonResponse({'groups': groups})
            except Exception as e:
                 return JsonResponse({'groups': [], 'error': str(e)}, status=500)
            
        return render(request, 'groups/group_list.html')

    def post(self, request, *args, **kwargs):
        group_name = request.POST.get('name')
        if not group_name:
            error_msg = 'Nombre de grupo no especificado'
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
                return JsonResponse({'success': False, 'message': error_msg})
            messages.error(request, error_msg)
            return redirect('groups:list')

        service = GroupService()
        result = service.delete_group(group_name)
        
        # Si es una petición AJAX o se solicitó JSON, respondemos siempre con JSON
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
            return JsonResponse(result)

        # Si es una petición tradicional, usamos mensajes y redirección
        if result.get('success', False):
            messages.success(request, f'Grupo "{group_name}" eliminado correctamente.')
        else:
            messages.error(request, f'Error al eliminar grupo: {result.get("message", "Error desconocido")}')
            
        return redirect('groups:list')

@method_decorator(csrf_exempt, name='dispatch')
class CreateGroupWizardView(LoginRequiredMixin, View):
    """
    API endpoint para el wizard de creación.
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            service = GroupService()
            result = service.create_group(data)
            
            if result['success']:
                return JsonResponse({'success': True, 'message': result['message']})
            else:
                 return JsonResponse({'success': False, 'message': result['message']}, status=400)
                 
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.exception("Create Group Error")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

class GroupWizardOptionsView(View):
    def get(self, request):
        service = GroupService()
        options = service.get_wizard_options()
        return JsonResponse(options)

class GroupWizardAPIView(View):
    def post(self, request):
        try:
            print(f"DEBUG: GroupWizardAPIView RECEIVED BODY: {request.body.decode('utf-8')}")
            data = json.loads(request.body)
            service = GroupService()
            
            # Identify mode (create/edit)
            mode = data.get('mode', 'create')
            print(f"DEBUG: Processing mode: {mode}")
            
            if mode == 'create':
                result = service.create_group(data)
            else:
                 group_name = data.get('info', {}).get('name') or data.get('name')
                 result = service.update_group_wizard(group_name, data)
            
            print(f"DEBUG: Wizard Result: {json.dumps(result)}")
            return JsonResponse(result)
        except Exception as e:
            logger.exception("GroupWizardAPIView Error")
            return JsonResponse({'success': False, 'message': str(e)})

class GroupDetailView(View):
    def get(self, request, name):
        service = GroupService()
        group = service.get_group_details(name)
        if group:
             return JsonResponse({'success': True, 'data': group})
        return JsonResponse({'success': False, 'message': 'Group not found'}), 500


# === API Endpoints for Wizard Options (Proxy to Services) ===

@require_http_methods(["GET"])
def get_available_users(request):
    """API: Retorna usuarios via UserService"""
    from apps.usuarios.services.user_service import UserService
    
    try:
        service = UserService()
        users = service.list_users()
        
        # Formato para el wizard
        user_list = []
        for u in users:
            # list_users devuelve dicts en modo offline o realtime
            full_name = u.get('description', '') or u.get('name')
            if 'email' in u and u['email']:
                 full_name += f" ({u['email']})"
                 
            user_list.append({
                'id': u.get('id', u.get('name')), # ID o nombre como fallback
                'username': u.get('name'),
                'email': u.get('email', ''),
                'full_name': u.get('name') # Simple name for now, description is separate
            })
            
        return JsonResponse(user_list, safe=False)
    except Exception as e:
         logger.exception("Error getting users for group wizard")
         return JsonResponse([], safe=False)

@require_http_methods(["GET"])
def get_shared_folders(request):
    """API: Retorna shared folders"""
    service = ResourceService()
    return JsonResponse(service.get_shared_folders(), safe=False)

@require_http_methods(["GET"])
def get_volumes(request):
    """API: Retorna volúmenes"""
    service = ResourceService()
    return JsonResponse(service.get_volumes(), safe=False)

@require_http_methods(["GET"])
def get_applications(request):
    """API: Retorna applications"""
    service = ResourceService()
    return JsonResponse(service.get_applications(), safe=False)

@require_http_methods(["GET"])
def get_group_detail(request, name):
    """API: Retorna detalles de un grupo específico para edición"""
    service = GroupService()
    group = service.get_group(name)
    if group:
        return JsonResponse({'success': True, 'data': group})
    return JsonResponse({'success': False, 'message': 'Grupo no encontrado'}, status=404)

class GroupExportView(LoginRequiredMixin, View):
    """
    Vista para exportar grupos.
    """
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        service = GroupService()
        groups = service.list_groups()
        
        if format_type == 'json':
            response = JsonResponse(groups, safe=False, json_dumps_params={'ensure_ascii': False})
            response['Content-Disposition'] = 'attachment; filename="grupos.json"'
            return response
        else:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="grupos.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Nombre', 'Descripción', 'Miembros', 'Sistema'])
            
            for g in groups:
                 writer.writerow([
                     g.get('name'),
                     g.get('description'),
                     len(g.get('members', [])),
                     'Sí' if g.get('is_system') else 'No'
                 ])
            return response
