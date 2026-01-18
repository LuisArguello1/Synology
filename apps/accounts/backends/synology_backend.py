from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from apps.settings.services.connection_service import ConnectionService
import logging

logger = logging.getLogger(__name__)

class SynologyAuthBackend(BaseBackend):
    """
    Autentica usuarios contra Synology NAS API.
    Crea usuario en Django si no existe (solo para sesión).
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Obtener config NAS para host/puerto
            from apps.settings.models import NASConfig
            config = NASConfig.get_active_config()
            
            if not config:
                logger.warning("No hay configuración NAS activa para autenticación")
                return None
            
            # Crear configuración temporal con las credenciales del usuario que intenta loguearse
            # Usamos una clase simple para imitar la interfaz de NASConfig
            class TempConfig:
                def __init__(self, original_config, user, pwd):
                    self.host = original_config.host
                    self.port = original_config.port
                    self.protocol = original_config.protocol
                    self.admin_username = user
                    self.admin_password = pwd
                    
                def get_base_url(self):
                    return f"{self.protocol}://{self.host}:{self.port}"
            
            temp_config = TempConfig(config, username, password)
            
            # En modo offline, no intentamos conectar al NAS real
            from django.conf import settings
            offline_mode = getattr(settings, 'NAS_OFFLINE_MODE', False)
            
            if offline_mode:
                logger.info(f"🛠️ MODO OFFLINE: Simulando éxito de autenticación para {username}")
                result = {'success': True, 'sid': 'fake-sid-offline', 'synotoken': 'fake-token'}
            else:
                # Usar servicio con config temporal para probar contra el NAS REAL
                service = ConnectionService(temp_config)
                
                # Log detallado antes de autenticar
                logger.info(f"🔐 Intentando autenticar usuario: {username}")
                logger.info(f"📡 NAS: {temp_config.get_base_url()}")
                
                result = service.authenticate()
                
                # Log detallado del resultado
                logger.info(f"📊 Resultado de autenticación: {result}")
            
            if result.get('success'):
                logger.info(f"Usuario {username} autenticado correctamente")
                
                # Autenticación exitosa en Synology
                User = get_user_model()
                
                # Obtener detalles del usuario para ver grupos (Sincronización de permisos)
                is_admin = False
                
                # En modo offline, forzamos admin para poder desarrollar la UI completa
                from django.conf import settings
                if getattr(settings, 'NAS_OFFLINE_MODE', False):
                    is_admin = True
                    logger.info(f"🛠️ MODO OFFLINE: Forzando privilegios de administrador para {username}")
                else:
                    try:
                        from apps.usuarios.services.user_service import UserService
                        user_service = UserService()
                        user_info = user_service.get_user(username)
                        if user_info and 'groups' in user_info:
                            # Buscamos 'administrators' en la lista de nombres de grupos
                            groups = [g.get('name') for g in user_info.get('groups', [])]
                            if 'administrators' in groups:
                                is_admin = True
                                logger.info(f"👑 Usuario {username} es administrador en Synology")
                    except Exception as e:
                        logger.error(f"Error sincronizando grupos de Synology para {username}: {e}")
                
                # Crear o actualizar usuario local
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'is_active': True,
                        'is_staff': is_admin,
                        'is_superuser': is_admin,
                        'email': f"{username}@synology.local"
                    }
                )
                
                # Actualizar si ya existía pero cambió su estado de admin
                if not created and (user.is_staff != is_admin):
                    user.is_staff = is_admin
                    user.is_superuser = is_admin
                    user.save()
                
                # Guardar datos de Synology en sesión
                if request:
                    request.session['synology_sid'] = result['sid']
                    request.session['synology_token'] = result.get('synotoken')
                    request.session['synology_username'] = username
                    request.session['synology_did'] = result.get('did')
                
                return user
            else:
                logger.warning(f"Fallo autenticación Synology para {username}: {result.get('message')}")
            
            return None
            
        except Exception as e:
            logger.exception(f"Error en backend de autenticación Synology: {str(e)}")
            return None
    
    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
