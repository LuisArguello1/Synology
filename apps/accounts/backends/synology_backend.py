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
            
            # Usar servicio con config temporal
            service = ConnectionService(temp_config)
            
            # Log detallado antes de autenticar
            logger.info(f"🔐 Intentando autenticar usuario: {username}")
            logger.info(f"📡 NAS: {temp_config.get_base_url()}")
            
            result = service.authenticate()
            
            # Log detallado del resultado
            logger.info(f"📊 Resultado de autenticación: {result}")
            
            if result['success']:
                logger.info(f"Usuario {username} autenticado exitosamente en Synology")
                
                # Autenticación exitosa en Synology
                User = get_user_model()
                # Crear o actualizar usuario local
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'is_active': True,
                        'is_staff': True, # Permitir acceso a admin si se desea, o manejarlo por grupos
                        'email': f"{username}@synology.local" # Dummy email
                    }
                )
                
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
