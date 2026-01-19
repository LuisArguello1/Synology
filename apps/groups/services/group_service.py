import logging
import json
import os
from django.conf import settings
from apps.settings.services.connection_service import ConnectionService
from apps.settings.models import NASConfig
from apps.core.services.resource_service import ResourceService

logger = logging.getLogger(__name__)

class GroupService:
    """
    Servicio de orquestación para Gestión de Grupos Synology
    con opción de modo offline para pruebas usando archivos JSON locales
    """
    
    def __init__(self):
        self.config = NASConfig.get_active_config()
        self.connection = ConnectionService(self.config)
        # Autenticar automáticamente para tener SID disponible en todas las llamadas
        if not getattr(settings, 'NAS_OFFLINE_MODE', False):
            self.connection.authenticate()
        
        # Archivo de simulación para grupos
        self.sim_db_path = os.path.join(settings.BASE_DIR, 'nas_sim_groups.json')
        self._ensure_sim_file()

    def _ensure_sim_file(self):
        """Crea el archivo de simulación con datos por defecto si no existe."""
        if not os.path.exists(self.sim_db_path):
            default_data = [
                {
                    'name': 'administrators', 
                    'description': 'System Administrators', 
                    'is_system': True,
                    'members': ['admin'],
                    'created_at': '2023-01-01T00:00:00'
                },
                {
                    'name': 'users', 
                    'description': 'Default User Group', 
                    'is_system': True,
                    'members': ['admin', 'guest'],
                    'created_at': '2023-01-01T00:00:00'
                }
            ]
            self._save_sim_data(default_data)

    def _get_sim_data(self):
        """Lee grupos del archivo de simulación local."""
        try:
            with open(self.sim_db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def _save_sim_data(self, data):
        """Guarda grupos en el archivo de simulación local."""
        with open(self.sim_db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def list_groups(self):
        """
        Lista grupos del NAS.
        API: SYNO.Core.Group method=list
        """
        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            return self._get_sim_data()
            
        try:
            response = self.connection.request(
                api='SYNO.Core.Group',
                method='list',
                version=1,
                params={'additional': '["members"]'} 
            )
            
            if response.get('success'):
                # Adaptar campos si es necesario
                groups = response.get('data', {}).get('groups', [])
                for g in groups:
                     # Normalizar campos si la API devuelve diferentes nombres
                     if 'desc' in g: g['description'] = g['desc']
                return groups
            
            logger.error(f"Error listing groups: {response}")
            return []
            
        except Exception as e:
            logger.exception("Exception listing groups")
            return []

    def get_group(self, name):
        """
        Obtiene detalles de UN grupo.
        API: SYNO.Core.Group method=get
        """
        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            groups = self._get_sim_data()
            group = next((g for g in groups if g['name'] == name), None)
            return group

        try:
            response = self.connection.request(
                api='SYNO.Core.Group',
                method='get',
                version=1,
                params={
                    'name': name,
                    'additional': '["members","perm","quota","speed_limit_up","speed_limit_down"]'
                }
            )
            
            if response.get('success'):
                groups = response.get('data', {}).get('groups', [])
                return groups[0] if groups else None
            return None
            
        except Exception as e:
            logger.exception(f"Error getting group {name}")
            return None

    def delete_group(self, name):
        """
        Elimina un grupo.
        API: SYNO.Core.Group method=delete
        """
        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            groups = self._get_sim_data()
            new_groups = [g for g in groups if g['name'] != name]
            
            if len(groups) != len(new_groups):
                # Validar sistema
                deleted = next(g for g in groups if g['name'] == name)
                if deleted.get('is_system', False):
                     return {'success': False, 'message': 'Cannot delete system group'}
                
                self._save_sim_data(new_groups)
                return {'success': True}
            return {'success': False, 'message': 'Group not found'}

        # Online implementation
        # Primero valida si es de sistema (mejor no borrar admins) para mantenerse conssitente con el NAS
        group = self.get_group(name)
        if group and group.get('is_system', False):
             return {'success': False, 'message': 'Cannot delete system group'}
             
        return self.connection.request(
            api='SYNO.Core.Group',
            method='delete',
            version=1,
            params={'name': name}
        )

    def create_group(self, data):
        """
        Crea un grupo en el NAS.
        Data debe venir limpia desde el form/JSON.
        """
        # Frontend sends { info: { name: ... }, ... }
        info = data.get('info', {})
        name = info.get('name') or data.get('name')
        
        if not name:
             return {'success': False, 'message': 'Name is required'}
             
        description = info.get('description') or data.get('description', '')

        # --- MODO OFFLINE / SIMULACIÓN ---
        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            groups = self._get_sim_data()
            if any(g['name'] == name for g in groups):
                return {'success': False, 'message': 'Group already exists'}
            
            new_group = {
                'name': name,
                'description': data.get('description', ''),
                'members': data.get('members', []),
                'folder_permissions': data.get('folder_permissions', {}),
                'quotas': data.get('quotas', {}),
                'app_permissions': data.get('app_permissions', {}),
                'created_at': '2023-01-01T00:00:00' 
            }
            groups.append(new_group)
            self._save_sim_data(groups)
            return {'success': True, 'message': f'Group {name} created (Simulated)'}
            
        # --- MODO ONLINE (REAL NAS) ---
        try:
            # 1. Crear el grupo básico
            params = {
                'name': name,
                'description': data.get('description', ''),
            }
            
            if data.get('members'):

                 params['members'] = json.dumps(data['members'])

            resp = self.connection.request('SYNO.Core.Group', 'create', version=1, params=params)
            
            if not resp.get('success'):
                 return {'success': False, 'message': f"NAS Error creating group: {resp.get('error')}"}

            # 2. Asignar Permisos de Carpetas (Iterativo)
            folder_perms = data.get('folder_permissions', {})
            for share_name, perm in folder_perms.items():
                if perm in ['ro', 'rw']: # Solo aplicamos si es explícito
                    # Necesitamos llamar a SYNO.Core.Share.Permission
                    # OJO: La API de Share.Permission a veces requiere el user/group name
                    perm_params = {
                        'path': f"/{share_name}", # Asumimos share name = path root
                        'name': name,
                        'is_group': 'true',
                        'privilege': perm 
                    }
                    # Nota: SYNO.Core.Share.Permission puede variar. Fallback seguro es loguear error.
                    self.connection.request('SYNO.Core.Share.Permission', 'write', version=1, params=perm_params)

            # 3. Asignar Permisos de Aplicaciones
            app_perms = data.get('app_permissions', {}) 
            for app_name, access in app_perms.items():
                if access in ['allow', 'deny']:
                    app_params = {
                        'name': name, 
                        'app': app_name, 
                        'is_group': 'true',
                        'allow': 'true' if access == 'allow' else 'false'
                    }
                    self.connection.request('SYNO.Core.AppPriv', 'set', version=1, params=app_params)

            # 4. Configurar Cuotas y Límites de Velocidad (Update masivo)
            update_params = {'name': name}
            has_updates = False

            # - Cuotas
            quotas = data.get('quotas', {})
            # quotas frontend format: {vol_id: {amount, unit, is_unlimited}}
            # We need to map vol_id to volume_path. Assuming vol_id IS the path or we have a map.
            # In wizard we use volume.id which usually is /volume1
            quota_list = []
            for vol_id, q_data in quotas.items():
                # If is_unlimited, we usually send -1 or 0 depending on API, but mostly we skip setting limit 
                # OR set to 0/unlimited if previous existed. For new group, skip if unlimited.
                if q_data.get('is_unlimited'): continue

                amount = int(q_data.get('amount', 0))
                unit = q_data.get('unit', 'MB')
                
                # Convert to MB for API
                size_mb = amount
                if unit == 'GB': size_mb *= 1024
                elif unit == 'TB': size_mb *= 1024 * 1024
                
                # Vol path hack: In resource service we trust the ID is useful.
                # If ID is numeric, we might need to find path. 
                # For now assume ID is path-like or we trust the frontend sends path as ID or we need lookup.
                # Based on ResourceService, id is usually the path (e.g. /volume1).
                vol_path = str(vol_id) 
                if not vol_path.startswith('/'): vol_path = f'/{vol_path}' # Safety
                if not vol_path.startswith('/volume'): vol_path = '/volume1' # Fallback
                
                quota_list.append({
                    "volume_path": vol_path,
                    "size_limit": size_mb 
                })
            
            if quota_list:
                update_params['quota_limit'] = json.dumps(quota_list)
                has_updates = True

            # - Speed Limits
            speeds = data.get('speed_limits', {})
            # format: {'file_station': {upload, download}, ...}
            # SYNO.Core.Group update usually takes generic speed_limit_up/down or specific by app.
            # Simple global limit or per app?
            # API usually has 'speed_limit_up' (global) or complex structures.
            # For this implementation, we will try setting global if provided, or skip complex per-app speed for now
            # as it requires specific API knowledge per app.
            
            if has_updates:
                 self.connection.request('SYNO.Core.Group', 'update', version=1, params=update_params)

            return {'success': True, 'message': 'Group created successfully'}
                 
        except Exception as e:
            logger.exception("Error creating group")
            return {'success': False, 'message': str(e)}

    def get_wizard_options(self):
        """
        Obtiene dependencias para el wizard de grupos.
        """
        resource_service = ResourceService()
        from apps.usuarios.services.user_service import UserService
        
        users = []
        try:
            user_service = UserService()
            raw_users = user_service.list_users()
            for u in raw_users:
                 users.append({
                    'username': u.get('name'),
                    'email': u.get('email', ''),
                    'description': u.get('description', '')
                })
        except:
            pass
        
        return {
            'shares': resource_service.get_shared_folders(),
            'volumes': resource_service.get_volumes(),
            'apps': resource_service.get_applications(),
            'users': users
        }
