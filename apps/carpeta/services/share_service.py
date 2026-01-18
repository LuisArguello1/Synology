import logging
import json
from apps.settings.services.connection_service import ConnectionService
from apps.settings.models import NASConfig

logger = logging.getLogger(__name__)

class ShareService:
    """
    Servicio de orquestación para Carpetas Compartidas Synology.
    Interactúa directamente con SYNO.Core.Share.*
    """
    
    def __init__(self):
        self.config = NASConfig.get_active_config()
        self.connection = ConnectionService(self.config)
        self.connection.authenticate()
        
    def list_shares(self, limit=50, offset=0):
        """
        Lista carpetas compartidas.
        API: SYNO.Core.Share method=list
        """
        try:
            response = self.connection.request(
                api='SYNO.Core.Share',
                method='list',
                version=1,
                params={
                    'limit': limit,
                    'offset': offset,
                    'additional': json.dumps(["vol_path", "mount_point_type", "encryption", "recyclebin"])
                }
            )
            
            if response.get('success'):
                return response.get('data', {}).get('shares', [])
            
            logger.error(f"Error listing shares: {response}")
            return []
            
        except Exception as e:
            logger.exception("Exception listing shares")
            return []

    def get_share(self, name):
        """
        Obtiene detalles de UNA carpeta compartida.
        API: SYNO.Core.Share method=get
        """
        try:
            additional = ["vol_path", "encryption", "recyclebin", "desc"]
            
            response = self.connection.request(
                api='SYNO.Core.Share',
                method='get',
                version=1,
                params={
                    'name': name,
                    'additional': json.dumps(additional)
                }
            )
            
            if response.get('success'):
                shares = response.get('data', {}).get('shares', [])
                if shares:
                    raw_share = shares[0]
                    # Transformar al formato del Wizard
                    return {
                        'info': {
                            'name': raw_share.get('name', ''),
                            'description': raw_share.get('desc', ''),
                            'volume': raw_share.get('vol_path', '/volume1'),
                            'recyclebin': raw_share.get('recyclebin', False),
                             # Campos no siempre disponibles en API estándar
                            'hide_network': False,
                            'hide_subfolders': False,
                            'admin_only': False
                        },
                        'security': {
                            'encrypted': raw_share.get('encryption', 0) == 1,
                            'password': '', # No retornan password
                            'password_confirm': ''
                        },
                        'advanced': {
                            # Valores por defecto o intentar mapear si API devuelve más info
                            'checksum': False,
                            'compression': False,
                            'quota_enabled': False,
                            'quota_size': 0,
                            'quota_unit': 'GB'
                        }
                    }
            return None
            
        except Exception as e:
            logger.exception(f"Error getting share {name}")
            return None

    def delete_share(self, name):
        """
        Elimina una carpeta compartida.
        API: SYNO.Core.Share method=delete
        """
        return self.connection.request(
            api='SYNO.Core.Share',
            method='delete',
            version=1,
            params={'name': name}
        )

    def get_wizard_options(self):
        """
        Obtiene opciones para el wizard (básicamente volúmenes).
        """
        options = {
            'volumes': []
        }
        
        try:
            # Obtener volúmenes
            v_resp = self.connection.request('SYNO.Core.Storage.Volume', 'list', version=1)
            if v_resp.get('success'):
                # Formato esperado: "/volume1"
                options['volumes'] = [v['path'] for v in v_resp['data']['volumes']]
            else:
                 options['volumes'] = ['/volume1'] # Fallback
        except Exception as e:
            logger.error(f"Error fetching wizard options: {e}")
            if not options['volumes']: options['volumes'] = ['/volume1']
            
        return options

    def create_share_wizard(self, data):
        """
        Orquestador de CREACIÓN de carpeta compartida.
        """
        return self._save_share_wizard(data, mode='create')

    def update_share_wizard(self, data):
        """
        Orquestador de EDICIÓN de carpeta compartida.
        Nota: SYNO.Core.Share 'set' tiene params parecidos a create pero no todos son modificables.
        """
        return self._save_share_wizard(data, mode='edit')

    def _save_share_wizard(self, data, mode='create'):
        results = {'success': False, 'steps': [], 'errors': []}
        info = data.get('info', {})
        name = info.get('name')
        
        if not name: return {'success': False, 'message': 'Name is required'}

        # Params comunes
        params = {
            'name': name,
            'desc': info.get('description', ''),
        }
        
        # En create es obligatorio vol_path, en edit no necesariamente (no se suele mover fácil)
        if mode == 'create':
            params['vol_path'] = info.get('volume', '/volume1')
            params['recyclebin'] = info.get('recyclebin', False)
            
            # Seguridad / Cifrado solo al crear (usualmente)
            security = data.get('security', {})
            if security.get('encrypted'):
                params['encryption'] = 1
                params['key'] = security.get('password', '')
        
        else:
             # UPDATE (method 'set')
             # recyclebin se puede editar
             params['recyclebin'] = info.get('recyclebin', False)
             # Volumen no se envía en update
        
        method = 'create' if mode == 'create' else 'set'

        try:
            resp = self.connection.request('SYNO.Core.Share', method, version=1, params=params)
            
            if not resp.get('success'):
                 error_code = resp.get('error', {}).get('code')
                 return {'success': False, 'message': f"Synology Error {error_code}: {self._get_error_msg(error_code)}"}
            
            results['steps'].append(f"Share {'Created' if mode=='create' else 'Updated'}")
            results['success'] = True
            
        except Exception as e:
             return {'success': False, 'message': f'Exception: {str(e)}'}

        return results
        
    def _get_error_msg(self, code):
        # Códigos de error comunes de SYNO.Core.Share
        errors = {
            400: "Nombre de carpeta inválido o faltan parámetros.",
            401: "Parámetro inválido.",
            402: "El sistema es demasiado lento (busy).",
            403: "Nombre de carpeta ya existe.",
            404: "Nombre de carpeta inválido.",
            405: "Caracteres especiales no permitidos.",
            406: "No se permite 'home' como nombre.",
            407: "Nombre reservado por el sistema.",
            408: "El volumen no existe.",
            409: "El volumen está desmontado.",
            # Agregar más según doc oficial
        }
        return errors.get(code, "Error desconocido")
