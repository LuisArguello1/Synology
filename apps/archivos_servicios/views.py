"""
Vistas para el módulo de Servicios de Archivos.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from .services.file_services_service import FileServicesService


def is_admin(user):
    """Verifica si el usuario es administrador"""
    from django.conf import settings
    if getattr(settings, 'NAS_OFFLINE_MODE', False):
        return True
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_admin)
def index(request):
    """
    Vista principal de servicios de archivos.
    Muestra el panel con todas las pestañas.
    """
    service = FileServicesService()
    configs = service.get_all_configs()
    
    context = {
        'configs': configs,
        'page_title': 'Servicios de Archivos'
    }
    
    return render(request, 'archivos_servicios/index.html', context)


# =============================================================================
# API ENDPOINTS
# =============================================================================

@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def api_get_configs(request):
    """
    API: Obtiene todas las configuraciones de servicios.
    """
    service = FileServicesService()
    configs = service.get_all_configs()
    return JsonResponse(configs, safe=False)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def api_update_smb(request):
    """
    API: Actualiza configuración SMB.
    """
    try:
        data = json.loads(request.body)
        service = FileServicesService()
        result = service.set_smb_config(data)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def api_update_afp(request):
    """
    API: Actualiza configuración AFP.
    """
    try:
        data = json.loads(request.body)
        service = FileServicesService()
        result = service.set_afp_config(data)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def api_update_nfs(request):
    """
    API: Actualiza configuración NFS.
    """
    try:
        data = json.loads(request.body)
        service = FileServicesService()
        result = service.set_nfs_config(data)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def api_update_ftp(request):
    """
    API: Actualiza configuración FTP/FTPS/SFTP.
    """
    try:
        data = json.loads(request.body)
        service = FileServicesService()
        result = service.set_ftp_config(data)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def api_update_rsync(request):
    """
    API: Actualiza configuración rsync.
    """
    try:
        data = json.loads(request.body)
        service = FileServicesService()
        result = service.set_rsync_config(data)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def api_update_advanced(request):
    """
    API: Actualiza configuraciones avanzadas.
    """
    try:
        data = json.loads(request.body)
        service = FileServicesService()
        result = service.set_advanced_config(data)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def api_get_rsync_account(request):
    """
    API: Obtiene la cuenta rsync.
    """
    service = FileServicesService()
    result = service.get_rsync_account()
    return JsonResponse(result)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def api_update_rsync_account(request):
    """
    API: Actualiza la cuenta rsync.
    """
    try:
        data = json.loads(request.body)
        service = FileServicesService()
        result = service.set_rsync_account(data)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
