from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
import json
import logging

from ..services.share_service import ShareService

logger = logging.getLogger(__name__)

class ShareListView(LoginRequiredMixin, TemplateView):
    """
    Vista principal: Tabla de carpetas compartidas.
    """
    template_name = 'carpeta/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = ShareService()
        
        # Breadcrumbs
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': 'core:dashboard'},
            {'name': 'Carpetas Compartidas'}
        ]
        context['page_title'] = 'Carpetas Compartidas'
        
        # Obtener lista 
        all_shares = service.list_shares()
        
        # Paginación local
        from django.core.paginator import Paginator
        paginator = Paginator(all_shares, 15)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['shares'] = page_obj
        context['page_obj'] = page_obj
        context['shares_json'] = json.dumps(all_shares)
        
        return context

class ShareWizardDataView(LoginRequiredMixin, View):
    """
    API Interna: Opciones y creación para el Wizard.
    """
    
    def get(self, request):
        service = ShareService()
        # Carga datos para edición si se implementa en futuro
        name = request.GET.get('name')
        if name:
             share_data = service.get_share(name)
             if share_data:
                 return JsonResponse({'success': True, 'data': share_data})
             return JsonResponse({'success': False, 'message': 'Carpeta no encontrada'}, status=404)
             
        options = service.get_wizard_options()
        return JsonResponse({'success': True, 'data': options})

    def post(self, request):
        try:
            data = json.loads(request.body)
            mode = data.get('mode', 'create')
            service = ShareService()
            
            if mode == 'edit':
                 share_name = data.get('info', {}).get('name') or data.get('name')
                 result = service.update_share_wizard(share_name, data)
                 action_type = 'SHARE_UPDATE'
            else:
                 result = service.create_share_wizard(data)
                 action_type = 'SHARE_CREATE'
            
            if result.get('success'):
                # LOG AUDITORIA
                from apps.auditoria.services.audit_service import AuditService
                name = data.get('info', {}).get('name', 'Unknown')
                AuditService.log(
                    action=action_type,
                    description=f"Carpeta compartida '{name}' {'actualizada' if mode=='edit' else 'creada'} exitosamente.",
                    user=request.user,
                    request=request,
                    details={'nas_result': result}
                )

            return JsonResponse(result)
        except Exception as e:
            logger.exception("Error in share wizard POST")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

class ShareDeleteView(LoginRequiredMixin, View):
    """
    API Interna: Elimina carpeta(s).
    Soporta eliminación masiva si name == 'batch'.
    """
    def post(self, request, name):
        service = ShareService()
        
        # Determinar si es masivo
        names_to_delete = [name]
        if name == 'batch':
            try:
                data = json.loads(request.body)
                names_to_delete = data.get('names', [])
            except:
                return JsonResponse({'success': False, 'message': 'Cuerpo JSON inválido'}, status=400)

        if not names_to_delete:
            return JsonResponse({'success': False, 'message': 'No se especificaron carpetas'}, status=400)

        result = service.delete_shares(names_to_delete)
        success = result.get('success', False)
        
        if success or result.get('count', 0) > 0:
            # LOG AUDITORIA
            from apps.auditoria.services.audit_service import AuditService
            AuditService.log(
                action='SHARE_DELETE',
                description=f"Eliminación de carpetas: {', '.join(names_to_delete)}",
                user=request.user,
                request=request,
                details={'deleted_shares': names_to_delete, 'result': result}
            )

        return JsonResponse({
            'success': success,
            'message': result.get('message', 'Operación completada'),
            'count': result.get('count', 0)
        })
