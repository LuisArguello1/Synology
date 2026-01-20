"""
Servicio de conexión al NAS Synology.

Este servicio encapsula toda la comunicación con la API del NAS.
Centraliza las peticiones HTTP y maneja errores de conexión.

ARQUITECTURA CLAVE:
- Ninguna view debe llamar directamente a la API del NAS
- Toda comunicación pasa por este ConnectionService
- La URL base se construye dinámicamente desde NASConfig
- Se implementa DISCOVERY (query.cgi) antes de cualquier operación
"""
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class ConnectionService:
    """
    Servicio para gestionar conexiones al NAS Synology.
    Implementa el protocolo oficial de File Station: Discovery -> Auth (v3) -> Request
    """
    
    def __init__(self, config=None):
        if config:
            self.config = config
        else:
            from ..models import NASConfig
            self.config = NASConfig.get_active_config()
            
        if not self.config:
            # En modo offline, permitimos iniciar sin config para simulaciones
            if not getattr(settings, 'NAS_OFFLINE_MODE', False):
                raise ValueError("No hay configuración NAS activa. Configure el NAS primero.")
            logger.info("ConnectionService initialized in OFFLINE MODE (No active config)")
        
        # Cache para rutas de API descubiertas
        self.api_paths = {}

    def get_sid(self):
        """Devuelve el SID actual si existe"""
        return getattr(self, '_sid', None)
    
    def get_base_url(self):
        """Obtiene URL base sin slash final"""
        return self.config.get_base_url()
    
    def _discover_apis(self):
        """
        PASO 1: Descubrir rutas de APIs disponibles.
        Consulta /webapi/query.cgi para obtener la ubicación real de cada servicio.
        """
        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            # En modo offline, no descubrimos nada, usamos rutas ficticias para evitar logs de error
            self.api_paths = {
                'SYNO.API.Auth': {'path': 'entry.cgi', 'maxVersion': 3},
                'SYNO.Core.Group': {'path': 'entry.cgi', 'maxVersion': 1},
                'SYNO.Core.Share': {'path': 'entry.cgi', 'maxVersion': 1}
            }
            return True

        try:
            url = f"{self.get_base_url()}/webapi/query.cgi"
            
            # Queries simplificadas para asegurar compatibilidad
            # Solo preguntamos por Auth y FileStation base primero
            queries = [
                'SYNO.API.Auth',
                'SYNO.FileStation.List',
                'SYNO.FileStation.Upload',
                'SYNO.FileStation.CreateFolder',
                'SYNO.FileStation.Delete',
                'SYNO.FileStation.Rename',
                'SYNO.FileStation.CopyMove'
            ]
            
            params = {
                'api': 'SYNO.API.Info',
                'version': 1,
                'method': 'query',
                'query': ','.join(queries)
            }
            
            logger.info(f"Discovering APIs at {url}...")
            response = requests.get(url, params=params, timeout=10, verify=False)
            
            # Log de respuesta raw para depuración
            logger.debug(f"Discovery Response Status: {response.status_code}")
            logger.debug(f"Discovery Response Body: {response.text}") # 🔍 Para ver qué devuelve exactamente

            if response.status_code != 200:
                 logger.error(f"Discovery HTTP Error: {response.status_code}")
                 return False

            data = response.json()
            if data.get('success'):
                self.api_paths = data['data']
                return True
            else:
                logger.error(f"Discovery failed: {data}")
                return False
                
        except Exception as e:
            logger.warning(f"📡 NAS Inalcanzable durante discovery: {str(e)}")
            return False

    def _get_api_info(self, api_name):
        """
        Obtiene información (path, maxVersion) de una API.
        Si no está en caché, intenta descubrirla.
        """
        if api_name not in self.api_paths:
            success = self._discover_apis()
            if not success:
                # Fallback de emergencia si discovery falla (aunque no debería usarse en prod)
                logger.warning(f"Could not discover {api_name}, using fallback to entry.cgi")
                return {'path': 'entry.cgi', 'maxVersion': 1}
        
        return self.api_paths.get(api_name, {'path': 'entry.cgi', 'maxVersion': 1})

    def test_connection(self):
        """
        Prueba la conexión y disponibilidad del NAS.
        Se basa en si el discovery de APIs funciona correctamente.
        """
        try:
            success = self._discover_apis()
            
            if success:
                # Verificar info específica de Auth para confirmar compatibilidad
                auth_info = self.api_paths.get('SYNO.API.Auth', {})
                max_ver = auth_info.get('maxVersion', 'unknown')
                
                return {
                    'success': True,
                    'message': f'✅ Conexión exitosa. API Auth disponible (v{max_ver})',
                    'data': self.api_paths
                }
            else:
                return {
                    'success': False,
                    'message': '❌ El NAS responde pero falló la consulta de APIs (query.cgi).',
                    'error': 'Discovery Failed'
                }
                
        except Timeout:
            return {
                'success': False,
                'message': f'❌ Timeout al conectar con {self.config.host}:{self.config.port}',
                'error': 'timeout'
            }
        except ConnectionError as e:
            return {
                'success': False,
                'message': '❌ No se puede establecer conexión de red.',
                'error': str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'❌ Error inesperado: {str(e)}',
                'error': str(e)
            }

    def authenticate(self, session_alias='FileStation'):
        """
        Autentica usando flujo correcto:
        1. Consulta ruta de SYNO.API.Auth
        2. Usa version 3 (o máxima compatible)
        3. Session = FileStation (por defecto) o DSM (para tareas admin)
        """
        # Chequeo Modo Offline
        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            logger.info("OFFLINE MODE: Simulating authentication success")
            fake_sid = 'OFFLINE_MODE_SID_12345'
            self._sid = fake_sid
            return {
                'success': True,
                'sid': fake_sid,
                'synotoken': '',
                'did': ''
            }

        try:
            # 1. Obtener ruta correcta
            auth_info = self._get_api_info('SYNO.API.Auth')
            api_path = auth_info.get('path', 'entry.cgi')
            max_ver = auth_info.get('maxVersion', 3)
            
            # Utilizar la versión máxima disponible para Auth
            # Versiones antiguas (v2/v3) pueden crear sesiones con permisos limitados
            # Especialmente para sesiones 'DSM'
            use_version = max_ver
            
            # Si max_ver es muy alto (ej 7) y hay problemas, podríamos limitar, 
            # pero probemos con la más alta primero para garantizar permisos modernos.
            if use_version > 6: use_version = 6 # Cap conservador en 6 por compatibilidad probada
                
            url = f"{self.get_base_url()}/webapi/{api_path}"
            
            logger.info(f"Authenticating via {api_path} (v{use_version}) session={session_alias}...")
            
            params = {
                'api': 'SYNO.API.Auth',
                'version': use_version,
                'method': 'login',
                'account': self.config.admin_username,
                'passwd': self.config.admin_password,
                'session': session_alias,   # Configurable: FileStation o DSM
                'format': 'sid'             # Obtenemos SID en JSON
            }
            
            response = requests.get(url, params=params, timeout=15, verify=False)
            response.raise_for_status()
            data = response.json()
            
            if data.get('success'):
                logger.info("✅ Login exitoso")
                self._sid = data['data']['sid'] # Guardar SID en la instancia
                return {
                    'success': True,
                    'sid': data['data']['sid'],
                    'synotoken': data.get('data', {}).get('synotoken'),
                    'did': data.get('data', {}).get('did')
                }
            else:
                error_code = data.get('error', {}).get('code')
                msg = self._get_auth_error_message(error_code)
                logger.warning(f"Login failed: {error_code} - {msg}")
                return {
                    'success': False,
                    'error': data.get('error'),
                    'message': msg
                }
                
        except Exception as e:
            logger.warning(f"⚠️ Fallo de conexión o tiempo de espera agotado al autenticar: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Error de conexión: El NAS no responde en {self.get_base_url()}'
            }

    def request(self, api, method, version=1, params=None, sid=None):
        """
        Método genérico para realizar peticiones a la API.
        Maneja:
        - Discovery de ruta (path)
        - Inyección de SID (si existe autenticación previa)
        - Construcción de URL
        """
        if params is None:
            params = {}
            
        # Chequeo Modo Offline
        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            logger.info(f"OFFLINE MODE: Simulating request to {api} / {method}")
            # Retornar estructuras vacías válidas para evitar crashes en el frontend
            return {'success': True, 'data': {
                'users': [], 
                'groups': [], 
                'shares': [], 
                'vol_info': [],
                'app_privs': [] # Added missing key
            }}

        try:
            # 1. Resolver path de la API
            info = self._get_api_info(api)
            path = info.get('path', 'entry.cgi')
            
            # 2. Construir URL base
            url = f"{self.get_base_url()}/webapi/{path}"
            
            # 3. Preparar parámetros de control (siempre en la URL para mayor compatibilidad)
            control_params = {
                'api': api,
                'version': version,
                'method': method
            }
            
            # 4. Inyectar SID (Prioridad: Argumento > self._sid)
            active_sid = sid or getattr(self, '_sid', None)
            if active_sid:
                control_params['_sid'] = active_sid
                
            # 5. Ejecutar Request
            # Nota: Synology suele aceptar todo por GET o POST. 
            # Sin embargo, para peticiones que modifican datos (POST), es más robusto 
            # pasar los parámetros de control (api, version, method, _sid) en el query string 
            # y los parámetros de datos en el cuerpo (form-data).
            if method in ['query', 'list', 'get']:
                # En GET, todo va en la URL
                all_params = {**control_params, **params}
                resp = requests.get(url, params=all_params, timeout=30, verify=False)
            else:
                # En POST, control en URL, data en BODY
                resp = requests.post(url, params=control_params, data=params, timeout=30, verify=False)
                
            # 6. Procesar respuesta
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    # Log detallado de errores para depuración (solo si no es exitoso)
                    if not data.get('success'):
                        logger.warning(f"NAS API Error in {api}/{method}: {data}")
                    return data
                except ValueError:
                    return {'success': False, 'message': 'Invalid JSON response', 'raw': resp.text}
            else:
                logger.error(f"HTTP Error {resp.status_code} in {api}/{method}: {resp.text}")
                return {'success': False, 'http_code': resp.status_code, 'message': f'HTTP Error {resp.status_code}'}

        except Exception as e:
            logger.error(f"Error in ConnectionService.request({api}, {method}): {e}")
            return {'success': False, 'message': str(e)}

    def logout(self, sid):
        """Cierra sesión usando la ruta correcta"""
        try:
            auth_info = self._get_api_info('SYNO.API.Auth')
            api_path = auth_info.get('path', 'entry.cgi')
            
            url = f"{self.get_base_url()}/webapi/{api_path}"
            params = {
                'api': 'SYNO.API.Auth',
                'version': 1,  # Logout suele ser v1
                'method': 'logout',
                'session': 'FileStation',
                '_sid': sid
            }
            requests.get(url, params=params, timeout=5, verify=False)
            return True
        except Exception:
            return False

    def _get_auth_error_message(self, error_code):
        messages = {
            400: 'Usuario o contraseña incorrectos',
            401: 'Cuenta deshabilitada',
            402: 'Permiso denegado',
            403: 'Se requiere código 2FA',
            404: 'Código 2FA inválido',
            407: 'IP bloqueada (demasiados intentos)',
        }
        return messages.get(error_code, f'Error desconocido ({error_code})')


        