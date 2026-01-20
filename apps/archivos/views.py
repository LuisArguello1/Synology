from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import logging

from .services.file_service import FileService

logger = logging.getLogger(__name__)

class ExplorerView(LoginRequiredMixin, TemplateView):
    """
    Vista principal SPA del Explorador de Archivos.
    """
    template_name = 'archivos/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Explorador de Archivos'
        return context

class FileAPIView(LoginRequiredMixin, View):
    """
    API Unificada para operaciones del file explorer.
    GET: Listar contenido (Root o Carpeta Específica)
    POST: Crear carpeta, Renombrar, Eliminar
    """

    def get(self, request):
        service = FileService()
        action = request.GET.get('action', 'list')
        path = request.GET.get('path', '')

        try:
            if action == 'list_shares':
                data = service.list_shares()
                return JsonResponse({'success': True, 'items': data, 'is_root': True})
            
            elif action == 'list':
                if not path:
                     # Si no hay path, asumimos shares list
                     data = service.list_shares()
                     return JsonResponse({'success': True, 'items': data, 'is_root': True})
                
                data = service.list_files(path)
                return JsonResponse({'success': True, 'items': data, 'is_root': False})
                
            return JsonResponse({'success': False, 'message': 'Invalid action'}, status=400)
            
        except Exception as e:
            logger.exception("FileAPI Error")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    def post(self, request):
        service = FileService()
        try:
            # Detectar si es JSON body o Form Data (Uploads)
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                action = data.get('action')
                
                if action == 'create_folder':
                    path = data.get('path')
                    name = data.get('name')
                    res = service.create_folder(path, name)
                    return JsonResponse(res)
                
                elif action == 'rename':
                    path = data.get('path')
                    name = data.get('name')
                    res = service.rename_item(path, name)
                    return JsonResponse(res)
                    
                elif action == 'delete':
                    path = data.get('path')
                    res = service.delete_item(path)
                    return JsonResponse(res)

                elif action == 'copy' or action == 'move':
                    path = data.get('path') # Origen
                    dest = data.get('dest') # Carpeta destino
                    is_move = (action == 'move')
                    if not path or not dest:
                        return JsonResponse({'success': False, 'message': 'Missing path or dest'}, status=400)
                    res = service.copy_move_item(path, dest, is_move)
                    return JsonResponse(res)

                elif action == 'search':
                    path = data.get('path')
                    pattern = data.get('pattern')
                    if not path or not pattern:
                         return JsonResponse({'success': False, 'message': 'Missing path or pattern'}, status=400)
                    items = service.search_files(path, pattern)
                    return JsonResponse({'success': True, 'items': items})

            return JsonResponse({'success': False, 'message': 'Action not supported via POST'}, status=400)

        except Exception as e:
            logger.exception("FileAPI POST Error")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
class FileUploadView(LoginRequiredMixin, View):
    """
    Endpoint dedicado para subida de archivos (Multipart).
    """
    def post(self, request):
        try:
            service = FileService()
            path = request.POST.get('path')
            
            if not path:
                return JsonResponse({'success': False, 'message': 'Path is required'}, status=400)
            
            if 'file' not in request.FILES:
                return JsonResponse({'success': False, 'message': 'File is required (key: file)'}, status=400)
                
            uploaded_file = request.FILES['file']
            
            # Streaming passthrough a la API de Synology
            res = service.upload_file(path, uploaded_file)
            
            if res.get('success'):
                return JsonResponse({'success': True, 'data': res.get('data')})
            else:
                return JsonResponse({'success': False, 'error': res.get('error')}, status=400)
                
        except Exception as e:
            logger.exception("Upload Error")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

class FileDownloadView(LoginRequiredMixin, View):
    """
    Proxy para descargar o visualizar archivos desde el NAS.
    """
    def get(self, request):
        path = request.GET.get('path')
        if not path:
            return JsonResponse({'success': False, 'message': 'Path is required'}, status=400)
        
        try:
            service = FileService()
            stream_res, error = service.get_file_stream(path)
            
            if error:
                return JsonResponse({'success': False, 'message': error}, status=400)
            
            # Preparar la respuesta de streaming
            filename = path.split('/')[-1]
            response = StreamingHttpResponse(
                stream_res.iter_content(chunk_size=8192),
                content_type=stream_res.headers.get('Content-Type')
            )
            
            # Si el usuario quiere forzar descarga, o para tipos no visualizables
            if 'download' in request.GET:
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
            else:
                response['Content-Disposition'] = f'inline; filename="{filename}"'
                
            return response
            
        except Exception as e:
            logger.exception("Download Proxy Error")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
