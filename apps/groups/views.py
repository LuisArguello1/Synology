"""
Vistas para la app Groups.

Incluye vistas para listar, eliminar y exportar grupos,
así como APIs JSON para el wizard de creación.
"""
from django.views.generic import ListView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import json
import csv
from .models import Group, SharedFolder, Volume, Application
import logging

logger = logging.getLogger(__name__)


from django.shortcuts import redirect

class GroupListView(LoginRequiredMixin, ListView):
    """
    Vista para listar grupos con filtros y búsqueda.
    Incluye el modal wizard para creación.
    """
    model = Group
    template_name = 'groups/group_list.html'
    context_object_name = 'groups'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Búsqueda
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Menu items centralizados
        from apps.core.services.menu_service import MenuService
        context['menu_items'] = MenuService.get_menu_items(self.request)
        
        # Breadcrumbs
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': 'core:dashboard'},
            {'name': 'Grupos'}
        ]
        
        context['page_title'] = 'Administración de Grupos'
        context['search_query'] = self.request.GET.get('search', '')
        
        return context


class GroupDeleteView(LoginRequiredMixin, DeleteView):
    """
    Vista para eliminar un grupo.
    """
    model = Group
    success_url = reverse_lazy('groups:list')
    template_name = 'groups/group_confirm_delete.html'
    
    def delete(self, request, *args, **kwargs):
        group = self.get_object()
        
        # Prevenir eliminación de grupos del sistema
        if group.is_system:
            messages.error(request, 'No se pueden eliminar grupos del sistema.')
            return redirect('groups:list')
        
        messages.success(request, f'Grupo "{group.name}" eliminado correctamente.')
        logger.info(f'Grupo eliminado: {group.name}')
        return super().delete(request, *args, **kwargs)


class GroupExportView(LoginRequiredMixin, ListView):
    """
    Vista para exportar grupos a CSV o JSON.
    """
    model = Group
    
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        groups = Group.objects.all()
        
        if format_type == 'json':
            return self.export_json(groups)
        else:
            return self.export_csv(groups)
    
    def export_csv(self, groups):
        """Exporta grupos a CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="grupos.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Nombre', 'Descripción', 'Miembros', 'Sistema', 'Creado'])
        
        for group in groups:
            writer.writerow([
                group.id,
                group.name,
                group.description,
                group.get_member_count(),
                'Sí' if group.is_system else 'No',
                group.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        
        logger.info('Grupos exportados a CSV')
        return response
    
    def export_json(self, groups):
        """Exporta grupos a JSON."""
        data = [group.export_to_dict() for group in groups]
        
        response = JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})
        response['Content-Disposition'] = 'attachment; filename="grupos.json"'
        
        logger.info('Grupos exportados a JSON')
        return response

@require_http_methods(["GET"])
def get_available_users(request):
    """
    API: Retorna lista de usuarios disponibles para paso 2 del wizard.
    """
    users = User.objects.all().values('id', 'username', 'email', 'first_name', 'last_name')
    users_list = []
    
    for user in users:
        # Asegurar codificación correcta si viene mal de la BD (aunque en Django+SQLite suele ser automágico)
        first_name = user['first_name'] or ''
        last_name = user['last_name'] or ''
        full_name = f"{first_name} {last_name}".strip() or user['username']
        
        users_list.append({
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'full_name': full_name
        })
    
    # ensure_ascii=False permite tildes reales en el JSON en lugar de unicodes escapados
    return JsonResponse(users_list, safe=False, json_dumps_params={'ensure_ascii': False})


@require_http_methods(["GET"])
def get_shared_folders(request):
    """
    API: Retorna lista de carpetas compartidas para paso 3 del wizard.
    """
    folders = SharedFolder.objects.all().values('id', 'name', 'description', 'path')
    return JsonResponse(list(folders), safe=False)


@require_http_methods(["GET"])
def get_volumes(request):
    """
    API: Retorna lista de volúmenes para paso 4 del wizard.
    """
    volumes = Volume.objects.all().values('id', 'name', 'total_space', 'available_space')
    return JsonResponse(list(volumes), safe=False)


@require_http_methods(["GET"])
def get_applications(request):
    """
    API: Retorna lista de aplicaciones para paso 5 del wizard.
    """
    apps = Application.objects.filter(is_active=True).values('id', 'name', 'description')
    return JsonResponse(list(apps), safe=False)


@require_http_methods(["POST"])
@csrf_exempt  # TODO: Implementar CSRF token en el wizard
def create_group_wizard(request):
    """
    API: Crea un grupo con todos los datos del wizard (paso 7).
    
    Espera un JSON con:
    {
        "name": "...",
        "description": "...",
        "members": [user_id1, user_id2, ...],
        "folder_permissions": {"folder_id": "rw|ro|na", ...},
        "quotas": {"volume_id": {"amount": 100, "unit": "GB"}, ...},
        "app_permissions": {"app_name": "allow|deny", ...},
        "speed_limits": {"service": {"upload": 100, "download": 200}, ...}
    }
    """
    try:
        data = json.loads(request.body)
        
        # Validar nombre obligatorio
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({
                'success': False,
                'message': 'El nombre del grupo es obligatorio'
            }, status=400)
        
        # Verificar que no exista el grupo
        if Group.objects.filter(name=name).exists():
            return JsonResponse({
                'success': False,
                'message': f'Ya existe un grupo con el nombre "{name}"'
            }, status=400)
        
        # Crear el grupo
        group = Group.objects.create(
            name=name,
            description=data.get('description', ''),
            folder_permissions=data.get('folder_permissions', {}),
            quotas=data.get('quotas', {}),
            app_permissions=data.get('app_permissions', {}),
            speed_limits=data.get('speed_limits', {})
        )
        
        # Agregar miembros
        member_ids = data.get('members', [])
        if member_ids:
            group.members.set(member_ids)
        
        logger.info(f'Grupo creado via wizard: {group.name} con {len(member_ids)} miembros')
        
        return JsonResponse({
            'success': True,
            'message': f'Grupo "{group.name}" creado exitosamente',
            'group_id': group.id
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'JSON inválido'
        }, status=400)
    
    except Exception as e:
        logger.exception(f'Error al crear grupo: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': f'Error al crear grupo: {str(e)}'
        }, status=500)
