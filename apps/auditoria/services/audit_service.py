import logging
from apps.auditoria.models import AuditLog

logger = logging.getLogger(__name__)

class AuditService:
    @staticmethod
    def get_client_ip(request):
        """Extrae la IP del cliente del request."""
        if not request:
            return None
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @staticmethod
    def log(action, description, user=None, request=None, details=None):
        """
        Crea un registro de auditoría.
        
        Args:
            action (str): Código de la acción (ej. 'USER_CREATE')
            description (str): Descripción legible.
            user (User, optional): Instancia de usuario. Si es None, intenta sacarlo del request.
            request (HttpRequest, optional): Para extraer IP y usuario si no se pasa explícitamente.
            details (dict, optional): Datos técnicos extra.
        """
        try:
            ip = None
            if request:
                ip = AuditService.get_client_ip(request)
                if not user and request.user.is_authenticated:
                    user = request.user
            
            AuditLog.objects.create(
                user=user,
                action=action,
                description=description,
                details=details or {},
                ip_address=ip
            )
        except Exception as e:
            # Fallar silenciosamente para no interrumpir el flujo principal, pero loguear el error
            logger.error(f"Error creating audit log: {e}")
