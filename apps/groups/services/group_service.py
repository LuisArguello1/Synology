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
    
    def __init__(self, session='FileStation'):
        self.config = NASConfig.get_active_config()
        self.connection = ConnectionService(self.config)
        # Autenticar automáticamente para tener SID disponible en todas las llamadas
        if not getattr(settings, 'NAS_OFFLINE_MODE', False):
            self.connection.authenticate(session_alias=session)
        
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
                # Robustness: Handle different possible structures for 'data'
                data = response.get('data', {})
                groups_list = []
                
                if isinstance(data, list):
                    groups_list = data
                elif isinstance(data, dict):
                    # Check common keys used by different DSM versions
                    groups_list = data.get('groups') or data.get('items') or data.get('datalist', [])
                    # If still not found but it's a dict, maybe the dict itself is the group? (unlikely for list)
                
                if not isinstance(groups_list, list):
                    logger.warning(f"Unexpected groups format in API response: {type(groups_list)}")
                    return []

                for g in groups_list:
                     # Normalizar campos si la API devuelve diferentes nombres
                     if 'group_name' in g and 'name' not in g: g['name'] = g['group_name']
                     if 'desc' in g and 'description' not in g: g['description'] = g['desc']
                     # Normalización de grupo de sistema
                     g['is_system'] = g.get('is_system') or g.get('is_sys') or (g.get('name') in ['administrators', 'users'])
                
                logger.info(f"Successfully listed {len(groups_list)} groups from NAS")
                return groups_list
            
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
            print(f"DEBUG: Fetching group details for: {name}")
            # La consulta básica para tener gid y descripción
            response = self.connection.request(
                api='SYNO.Core.Group',
                method='get',
                version=1,
                params={'name': name}
            )
            
            if response.get('success'):
                data = response.get('data', {})
                group_data = None
                
                if isinstance(data, dict):
                    items = data.get('groups') or data.get('items')
                    if items and isinstance(items, list):
                        group_data = items[0]
                    elif 'name' in data or 'group_name' in data:
                        group_data = data
                elif isinstance(data, list) and data:
                    group_data = data[0]
                
                if group_data:
                    # Normalización Básica
                    if 'group_name' in group_data and 'name' not in group_data: group_data['name'] = group_data['group_name']
                    if 'desc' in group_data and 'description' not in group_data: group_data['description'] = group_data['desc']
                    # Normalización de grupo de sistema
                    group_data['is_system'] = group_data.get('is_system') or group_data.get('is_sys') or (group_data.get('name') in ['administrators', 'users'])
                    
                    # 1. MIEMBROS (Dedicated call)
                    members = []
                    try:
                        m_resp = self.connection.request('SYNO.Core.Group.Member', 'list', version=1, params={'group': name})
                        if m_resp.get('success'):
                            m_data = m_resp.get('data', {})
                            # DSM usa 'users' para los miembros del grupo
                            members_raw = m_data.get('users') or m_data.get('members') or m_data.get('items') or []
                            members = [m.get('name') if isinstance(m, dict) else str(m) for m in members_raw]
                    except Exception as me:
                        logger.error(f"Error fetching members: {me}")
                    group_data['members'] = members

                    # 2. PERMISOS DE CARPETAS (Fallback robusto)
                    folder_perms = {}
                    try:
                        # Obtenemos lista de carpetas para consultar una por una o via detail si existe
                        resource_service = ResourceService()
                        shares = resource_service.get_shared_folders()
                        for share in shares:
                            share_name = share['name']
                            p_resp = self.connection.request('SYNO.Core.Share.Permission', 'get', version=1, params={
                                'name': name,
                                'is_group': 'true',
                                'path': f"/{share_name}"
                            })
                            if p_resp.get('success'):
                                p_data = p_resp.get('data', {})
                                folder_perms[share_name] = p_data.get('privilege', 'na')
                    except Exception as pe:
                        logger.error(f"Error fetching folder perms: {pe}")
                    group_data['mapped_folder_permissions'] = folder_perms

                    # 3. CUOTAS
                    mapped_quotas = {}
                    try:
                        q_resp = self.connection.request('SYNO.Core.Quota', 'get', version=1, params={
                            'name': name,
                            'is_group': 'true'
                        })
                        if q_resp.get('success'):
                            q_list = q_resp.get('data', {}).get('quotas', [])
                            for q in q_list:
                                vol_path = q.get('volume_path')
                                limit = q.get('quota_limit', 0)
                                mapped_quotas[vol_path] = {
                                    'amount': limit,
                                    'unit': 'MB',
                                    'is_unlimited': (limit == 0)
                                }
                    except Exception as qe:
                        logger.error(f"Error fetching quotas: {qe}")
                    group_data['mapped_quotas'] = mapped_quotas

                    # 4. PRIVILEGIOS DE APPS
                    mapped_apps = {}
                    try:
                        # SYNO.Core.AppPriv:get suele devolver todos los privilegios del sujeto
                        a_resp = self.connection.request('SYNO.Core.AppPriv', 'get', version=1, params={
                            'name': name,
                            'is_group': 'true'
                        })
                        if a_resp.get('success'):
                            apps_data = a_resp.get('data', {}).get('apps', [])
                            for app in apps_data:
                                app_id = app.get('app')
                                allowed = app.get('allow', False)
                                mapped_apps[app_id] = 'allow' if allowed else 'deny'
                    except Exception as ae:
                        logger.error(f"Error fetching app perms: {ae}")
                    group_data['mapped_app_permissions'] = mapped_apps
                    
                    print(f"DEBUG: Final data found: {json.dumps(group_data)}")
                    return group_data
                return None
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
        # Primero valida si es de sistema
        group = self.get_group(name)
        if group and group.get('is_system', False):
             return {'success': False, 'message': 'Cannot delete system group'}
             
        admin_conn = ConnectionService(self.config)
        auth_result = admin_conn.authenticate(session_alias='DSM')
        if not auth_result.get('success'):
            return auth_result
            
        current_sid = auth_result.get('sid')
        try:
            return admin_conn.request(
                api='SYNO.Core.Group',
                method='delete',
                version=1,
                params={'name': name, 'group_name': name}
            )
        finally:
            if admin_conn and current_sid:
                admin_conn.logout(current_sid, session_alias='DSM')

    def apply_group_settings(self, name, data, items_results=None, conn=None):
        """
        Aplica configuraciones avanzadas (Carpetas, Apps, Cuotas) a un grupo.
        Centralizado para Reutilización en Create y Update.
        """
        active_conn = conn or self.connection
        
        # 1. Asignar Permisos de Carpetas
        folder_perms = data.get('folder_permissions', {})
        for share_name, perm in folder_perms.items():
            # Synology usa 'na' para No Access, 'ro' para Read Only y 'rw' para Read/Write
            if perm in ['ro', 'rw', 'na']:
                perm_params = {
                    'name': name,
                    'user_name': '', # Vacío para grupos
                    'group_name': name,
                    'is_group': 'true',
                    'privilege': perm,
                    'share_name': share_name
                }
                # Intentamos con 'share_name' y con 'name' (path-style) para mayor compatibilidad
                try:
                    resp = active_conn.request('SYNO.Core.Share.Permission', 'set', version=1, params=perm_params)
                    if not resp.get('success'):
                        # Fallback: intentar estilo de ruta
                        perm_params['name'] = share_name
                        active_conn.request('SYNO.Core.Share.Permission', 'set', version=1, params=perm_params)
                except Exception as e:
                    logger.error(f"Error setting folder permission for {share_name}: {e}")

        # 2. Asignar Permisos de Aplicaciones
        app_perms = data.get('app_permissions', {}) 
        for app_name, access in app_perms.items():
            if access in ['allow', 'deny']:
                app_params = {
                    'name': name, 
                    'app': app_name, 
                    'is_group': 'true',
                    'allow': 'true' if access == 'allow' else 'false'
                }
                active_conn.request('SYNO.Core.AppPriv', 'set', version=1, params=app_params)

        # 3. Configurar Cuotas
        update_params = {'name': name}
        has_updates = False
        quotas = data.get('quotas', {})
        quota_list = []
        for vol_id, q_data in quotas.items():
            if q_data.get('is_unlimited'): continue
            
            amount = int(q_data.get('amount', 0))
            unit = q_data.get('unit', 'MB')
            size_mb = amount
            if unit == 'GB': size_mb *= 1024
            elif unit == 'TB': size_mb *= 1024 * 1024
            
            vol_path = str(vol_id) 
            if not vol_path.startswith('/'): vol_path = f'/{vol_path}'
            
            quota_list.append({
                "volume_path": vol_path,
                "size_limit": size_mb 
            })
        
        if quota_list:
            update_params['quota_limit'] = json.dumps(quota_list)
            has_updates = True

        if has_updates:
            active_conn.request('SYNO.Core.Group', 'update', version=1, params=update_params)

    def _sync_group_members(self, admin_conn, group_name, members_list):
        """
        Intenta sincronizar los miembros de un grupo probando varias estrategias de la API.
        Muchas versiones de DSM son inconsistentes con los nombres de parámetros.
        """
        if members_list is None: return True
        
        print(f"DEBUG: Syncing members for {group_name}: {members_list}")
        
        # 1. Preparar formatos: CSV (Standard) y JSON (Algunas versiones modernas)
        member_str = ",".join(members_list) if isinstance(members_list, list) else str(members_list)
        member_json = json.dumps(members_list)
        
        # Estrategias de parámetros comunes
        strategies = [
            # Estrategias con string (CSV)
            {'g': 'group', 'm': 'member',  'fmt': member_str, 'method': 'set'},
            {'g': 'group', 'm': 'members', 'fmt': member_str, 'method': 'set'},
            {'g': 'name',  'm': 'member',  'fmt': member_str, 'method': 'set'},
            {'g': 'group', 'm': 'user',    'fmt': member_str, 'method': 'set'},
            # Estrategias con JSON
            {'g': 'group', 'm': 'member',  'fmt': member_json, 'method': 'set'},
            {'g': 'group', 'm': 'user',    'fmt': member_json, 'method': 'set'},
        ]
        
        # Intentamos con 'set' primero
        for s in strategies:
            params = {s['g']: group_name, s['m']: s['fmt']}
            print(f"DEBUG: Trial SYNO.Core.Group.Member:{s['method']} ({s['g']}={group_name}, {s['m']}=...)")
            resp = admin_conn.request('SYNO.Core.Group.Member', s['method'], version=1, params=params)
            if resp.get('success'):
                print(f"DEBUG: SUCCESS with {s['g']}/{s['m']} ({s['method']})")
                return True

        # Fallback a 'add' si 'set' no funcionó
        for s in strategies:
            params = {s['g']: group_name, s['m']: s['fmt']}
            resp = admin_conn.request('SYNO.Core.Group.Member', 'add', version=1, params=params)
            if resp.get('success'):
                print(f"DEBUG: SUCCESS with {s['g']}/{s['m']} (add)")
                return True

        return False

    def create_group(self, data):
        """Orquestador de CREACIÓN con permisos administrativos"""
        print(f"DEBUG: create_group RECEIVED DATA: {json.dumps(data)}")
        info = data.get('info', {})
        name = info.get('name') or data.get('name')
        
        if not name:
             return {'success': False, 'message': 'Name is required'}
             
        # --- MODO OFFLINE ---
        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            groups = self._get_sim_data()
            if any(g['name'] == name for g in groups):
                return {'success': False, 'message': 'Group already exists'}
            
            new_group = {
                'name': name,
                'description': info.get('description', ''),
                'members': data.get('members', []),
                'folder_permissions': data.get('folder_permissions', {}),
                'quotas': data.get('quotas', {}),
                'app_permissions': data.get('app_permissions', {}),
                'created_at': '2023-01-01T00:00:00' 
            }
            groups.append(new_group)
            self._save_sim_data(groups)
            return {'success': True, 'message': f'Group {name} created (Simulated)'}
            
        # --- MODO ONLINE ---
        admin_conn = None
        current_sid = None
        try:
            # 1. Crear conexión admin (DSM)
            admin_conn = ConnectionService(self.config)
            auth_result = admin_conn.authenticate(session_alias='DSM')
            if not auth_result.get('success'):
                return {'success': False, 'message': 'Failed to authenticate as admin'}
            
            current_sid = auth_result.get('sid')

            # 2. Crear el grupo básico
            params = {
                'name': name,
                'description': info.get('description', ''),
            }
            
            # Intentamos creación básica
            resp = admin_conn.request('SYNO.Core.Group', 'create', version=1, params=params)
            print(f"DEBUG: SYNO.Core.Group:create for {name} resp: {json.dumps(resp)}")
            
            if not resp.get('success'):
                error_code = resp.get('error', {}).get('code', 'Unknown')
                return {'success': False, 'message': f"NAS Error: {error_code}"}

            # 3. Gestionar Miembros (Usando nuestra función robusta)
            members_list = data.get('members', [])
            if members_list:
                self._sync_group_members(admin_conn, name, members_list)

            # 4. Aplicar configuraciones avanzadas
            self.apply_group_settings(name, data, conn=admin_conn)
            return {'success': True, 'message': 'Group created successfully'}
                 
        except Exception as e:
            logger.exception("Error creating group")
            return {'success': False, 'message': str(e)}
        finally:
            if admin_conn and current_sid:
                admin_conn.logout(current_sid, session_alias='DSM')

    def update_group_wizard(self, name, data):
        """Orquestador de ACTUALIZACIÓN con permisos administrativos"""
        print(f"DEBUG: update_group_wizard RECEIVED DATA for {name}: {json.dumps(data)}")
        info = data.get('info', {})
        
        if not name:
             return {'success': False, 'message': 'Name is required'}

        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            groups = self._get_sim_data()
            found = False
            for g in groups:
                if g['name'] == name:
                    # Actualizar campos básicos
                    desc = info.get('description') or data.get('description')
                    if desc is not None: g['description'] = desc
                    
                    # Actualizar relaciones si vienen en la data
                    if 'members' in data: g['members'] = data['members']
                    if 'folder_permissions' in data: g['folder_permissions'] = data['folder_permissions']
                    if 'quotas' in data: g['quotas'] = data['quotas']
                    if 'app_permissions' in data: g['app_permissions'] = data['app_permissions']
                    found = True
                    break
            
            if found:
                self._save_sim_data(groups)
                return {'success': True, 'message': f'Group {name} updated (Simulated)'}
            return {'success': False, 'message': 'Group not found in simulation'}

        admin_conn = None
        current_sid = None
        try:
            print(f"DEBUG: Updating group {name}")
            admin_conn = ConnectionService(self.config)
            auth_result = admin_conn.authenticate(session_alias='DSM')
            if not auth_result.get('success'):
                return {'success': False, 'message': 'Failed to authenticate as admin'}
            
            current_sid = auth_result.get('sid')

            # 1. Update Base Info
            params = {'name': name}
            if info.get('description') is not None: params['description'] = info['description']
            
            u_resp = admin_conn.request('SYNO.Core.Group', 'update', version=1, params=params)
            print(f"DEBUG: SYNO.Core.Group:update resp: {json.dumps(u_resp)}")

            # 2. Update Members (Usando nuestra función robusta)
            members_list = data.get('members')
            if members_list is not None:
                self._sync_group_members(admin_conn, name, members_list)

            # 3. Update Settings
            self.apply_group_settings(name, data, conn=admin_conn)
            return {'success': True, 'message': 'Group updated successfully'}
                 
        except Exception as e:
            logger.exception("Error updating group")
            return {'success': False, 'message': str(e)}
        finally:
            if admin_conn and current_sid:
                admin_conn.logout(current_sid, session_alias='DSM')

    def get_group_details(self, name):
        """Alias para get_group para compatibilidad con vistas"""
        return self.get_group(name)

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
                username = u.get('name') or u.get('user_name') or ''
                if not username:
                    continue
                    
                users.append({
                    'id': username,  # Added ID for Alpine.js :key compatibility
                    'username': username,
                    'email': u.get('email', ''),
                    'description': u.get('description', '')
                })
        except Exception as e:
            logger.error(f"Error fetching users for wizard: {str(e)}")
        
        return {
            'shares': resource_service.get_shared_folders(),
            'volumes': resource_service.get_volumes(),
            'apps': resource_service.get_applications(),
            'users': users
        }
