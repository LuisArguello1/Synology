import logging
import json
from django.conf import settings
from apps.settings.services.connection_service import ConnectionService
from apps.settings.models import NASConfig

logger = logging.getLogger(__name__)

class UserService:
    """
    Servicio de orquestación para Gestión de Usuarios Synology.
    Interactúa directamente con SYNO.Core.*
    """
    
    def __init__(self):
        self.config = NASConfig.get_active_config()
        self.connection = ConnectionService(self.config)
        # En modo offline, no necesitamos autenticar
        if not getattr(settings, 'NAS_OFFLINE_MODE', False):
            # Autenticar automáticamente para tener SID disponible en todas las llamadas
            self.connection.authenticate()
        
    def list_users(self, limit=50, offset=0):
        """
        Lista usuarios del NAS.
        API: SYNO.Core.User method=list
        """
        try:
            # Info adicional que queremos traer
            additional = ["email", "description", "expired"]
            
            response = self.connection.request(
                api='SYNO.Core.User',
                method='list',
                version=1,
                params={
                    'limit': limit,
                    'offset': offset,
                    'additional': json.dumps(additional) 
                }
            )
            
            if response.get('success'):
                return response.get('data', {}).get('users', [])
            
            logger.error(f"Error listing users: {response}")
            return []
            
        except Exception as e:
            logger.exception("Exception listing users")
            return []

    def get_user(self, name):
        """
        Obtiene detalles de UN usuario con todos los adicionales necesarios para el Wizard.
        API: SYNO.Core.User method=get
        """
        try:
            # Traemos todo lo posible para poblar el Wizard en modo edición
            additional = [
                "email", "description", "expired", "groups", 
                "quota", "cannot_change_password", "app_privilege",
                "speed_limit"
            ] 
            
            response = self.connection.request(
                api='SYNO.Core.User',
                method='get',
                version=1,
                params={
                    'name': name,
                    'additional': json.dumps(additional)
                }
            )
            
            if response.get('success'):
                users = response.get('data', {}).get('users', [])
                if users:
                    user_data = users[0]
                    # Normalizar permisos de aplicación para que sea una lista plana de apps permitidas
                    if 'app_privilege' in user_data:
                        apps = user_data['app_privilege']
                        if isinstance(apps, dict):
                            user_data['apps_list'] = [app for app, allow in apps.items() if allow]
                        elif isinstance(apps, list):
                            user_data['apps_list'] = [a['app'] for a in apps if a.get('allow')]
                    return user_data
            return None
            
        except Exception as e:
            logger.exception(f"Error getting user {name}")
            return None

    def delete_user(self, name):
        """
        Elimina un usuario.
        API: SYNO.Core.User method=delete
        """
        return self.connection.request(
            api='SYNO.Core.User',
            method='delete',
            version=1,
            params={'name': name}
        )

    def get_wizard_options(self):
        """
        Obtiene TODAS las dependencias para poblar los selects del Wizard.
        Incluye permisos de grupos por defecto para la vista previa dinámica.
        """
        from apps.groups.services.group_service import GroupService
        from apps.core.services.resource_service import ResourceService
        
        options = {
            'groups': [],
            'shares': [],
            'apps': [],
            'volumes': [],
            'group_permissions': {} # Para cálculos dinámicos en el wizard
        }
        
        try:
            group_service = GroupService()
            resource_service = ResourceService()

            # 1. Grupos (Service)
            groups = group_service.list_groups()
            options['groups'] = [{'name': g.get('name'), 'description': g.get('description', '')} for g in groups]

            # 2. Shares (Service)
            shares = resource_service.get_shared_folders()
            options['shares'] = shares 

            # 3. Apps (Service)
            apps = resource_service.get_applications()
            options['apps'] = [{'name': a.get('name'), 'desc': a.get('description')} for a in apps]
            
            # 4. Volúmenes (Service)
            options['volumes'] = resource_service.get_volumes()
            # Simplificar para compatibilidad con código previo si es necesario (extraer solo paths)
            if options['volumes']:
                options['volumes_paths'] = [v['name'] for v in options['volumes']]
            else:
                options['volumes_paths'] = ['/volume1']

            # 5. Obtener permisos de TODOS los grupos (para cálculos dinámicos en el wizard)
            if not getattr(settings, 'NAS_OFFLINE_MODE', False):
                try:
                    group_list = [g['name'] for g in options.get('groups', [])]
                    if group_list:
                        params = {
                            'name': ",".join(group_list),
                            'additional': json.dumps(["share_privilege", "app_privilege"])
                        }
                        ug_resp = self.connection.request('SYNO.Core.Group', 'get', version=1, params=params)
                        if ug_resp.get('success') and ug_resp['data']['groups']:
                            for g_info in ug_resp['data']['groups']:
                                g_name = g_info['name']
                                options['group_permissions'][g_name] = {
                                    'shares': {sp['share_name']: sp['privilege'] for sp in g_info.get('share_privilege', [])},
                                    'apps': {}
                                }
                                # Apps
                                apps_priv = g_info.get('app_privilege', {})
                                if isinstance(apps_priv, dict):
                                    options['group_permissions'][g_name]['apps'] = apps_priv
                                elif isinstance(apps_priv, list):
                                    for ap in apps_priv:
                                        options['group_permissions'][g_name]['apps'][ap['app']] = ap.get('allow', False)
                except Exception as ge:
                    logger.error(f"Error fetching all group permissions: {ge}")
            else:
                # Mock para modo offline si quieres simular herencia de grupos
                options['group_permissions']['users'] = {'shares': {}, 'apps': {}}

        except Exception as e:
            logger.error(f"Error fetching wizard options: {e}")
            
        return options

    def apply_user_settings(self, username, data, results):
        """
        Aplica configuraciones complejas (Grupos, Cuotas, Apps, Speed) a un usuario existente.
        Centraliza la lógica para Reutilización en Create y Update.
        """
        info = data.get('info', {})
        update_params = {'name': username}
        has_updates = False

        # 0. Flags de Usuario
        if 'cannot_change_password' in info:
            update_params['cannot_change_passwd'] = info['cannot_change_password']
            has_updates = True

        # 1. Grupos
        if 'groups' in data:
            # Synology espera los grupos separados por coma
            update_params['groups'] = ",".join(data['groups'])
            has_updates = True

        # 2. Permisos de Carpetas (Iterativo por limitación de API v1)
        if 'permissions' in data and data['permissions']:
            perm_errors = []
            for share_name, policy in data['permissions'].items():
                if policy not in ['rw', 'ro', 'na']: continue
                try:
                    p_resp = self.connection.request(
                        api='SYNO.Core.Share.Permission',
                        method='write', version=1,
                        params={'name': share_name, 'user_name': username, 'privilege': policy}
                    )
                    if not p_resp.get('success'): 
                        error_msg = p_resp.get('error', {}).get('code', 'Unknown')
                        perm_errors.append(f"{share_name}: Error {error_msg}")
                except Exception as e: 
                    perm_errors.append(f"{share_name}: {str(e)}")
            
            if not perm_errors: 
                results['steps'].append('Folder Permissions Applied')
            else: 
                results['errors'].append(f"Permission errors: {perm_errors}")

        # 3. Cuotas
        if 'quota' in data and data['quota']:
            quota_list = []
            for vol_path, q_data in data['quota'].items():
                try:
                    size_mb = int(q_data.get('size', 0))
                    unit = q_data.get('unit', 'MB')
                    if unit == 'GB': size_mb *= 1024
                    elif unit == 'TB': size_mb *= 1024 * 1024
                    quota_list.append({"volume_path": vol_path, "size_limit": size_mb})
                except: continue
            
            if quota_list:
                update_params['quota_limit'] = json.dumps(quota_list)
                has_updates = True

        # 4. Aplicaciones
        if 'apps' in data:
            app_list = []
            # 'apps' suele venir como dict { 'app_id': 'allow'/'deny' }
            for app_id, user_setting in data['apps'].items():
                if user_setting in ['allow', 'deny']:
                    app_list.append({
                        "app": app_id,
                        "allow": (user_setting == 'allow'),
                        "allow_empty": False
                    })
            
            if app_list:
                update_params['app_privilege'] = json.dumps(app_list)
                has_updates = True
        
        # 5. Límites de Velocidad
        if 'speed' in data and data['speed']:
            speed_rules = []
            service_map = {'File Station': 'file_station', 'FTP': 'ftp', 'Rsync': 'rsync'}
            
            def to_kb(val, unit):
                try:
                    v = int(val)
                    return v * 1024 if unit == 'MB' else v
                except: return 0

            for name, s_data in data['speed'].items():
                api_id = service_map.get(name)
                if not api_id: continue
                
                rule = {
                    "service": api_id,
                    "mode": s_data.get('mode', 'unlimited'),
                    "upload": to_kb(s_data.get('up'), s_data.get('up_unit')),
                    "download": to_kb(s_data.get('down'), s_data.get('down_unit'))
                }
                speed_rules.append(rule)
            
            if speed_rules:
                update_params['speed_limit_rules'] = json.dumps(speed_rules)
                # Fallback Global para versiones antiguas basado en File Station
                fs = data['speed'].get('File Station', {})
                if fs.get('mode') == 'limit':
                    update_params['speed_limit_up'] = to_kb(fs.get('up'), fs.get('up_unit'))
                    update_params['speed_limit_down'] = to_kb(fs.get('down'), fs.get('down_unit'))
                elif fs.get('mode') == 'unlimited':
                    update_params['speed_limit_up'] = 0
                    update_params['speed_limit_down'] = 0
                
                has_updates = True

        # Ejecutar update consolidado en el NAS
        if has_updates:
            try:
                resp_up = self.connection.request('SYNO.Core.User', 'update', version=1, params=update_params)
                if resp_up.get('success'): 
                    results['steps'].append('Advanced Settings Applied')
                else: 
                    results['errors'].append(f"Settings update failed: {resp_up}")
            except Exception as e: 
                results['errors'].append(f"Update exception: {str(e)}")

        return results

    def create_user_wizard(self, data):
        """Orquestador de CREACIÓN"""
        results = {'success': False, 'steps': [], 'errors': []}
        info = data.get('info', {})
        username = info.get('name')
        
        if not username: return {'success': False, 'message': 'Username is required'}

        # Paso 1: Crear Base
        try:
            params = {
                'name': username,
                'password': info['password'],
                'email': info.get('email', ''),
                'description': info.get('description', ''),
                'expired': 'normal',
                'send_welcome_email': info.get('send_notification', False),
                'cannot_change_passwd': info.get('cannot_change_password', False)
            }
            resp = self.connection.request('SYNO.Core.User', 'create', version=1, params=params)
            if not resp.get('success'):
                error_msg = resp.get('error', {}).get('code', 'Unknown Error')
                return {'success': False, 'message': f"Synology Error: {error_msg}"}
            results['steps'].append('User Created')
        except Exception as e:
            return {'success': False, 'message': f'Exception: {str(e)}'}

        # Paso 2: Aplicar configuraciones avanzadas
        self.apply_user_settings(username, data, results)
        
        results['success'] = len(results['errors']) == 0
        if not results['success']:
             results['message'] = f"User created but some settings failed: {'; '.join(results['errors'])}"
        else:
             results['message'] = "User created successfully with all settings."
             
        return results

    def update_user_wizard(self, data):
        """Orquestador de ACTUALIZACIÓN"""
        results = {'success': False, 'steps': [], 'errors': []}
        info = data.get('info', {})
        username = info.get('name')
        
        if not username: return {'success': False, 'message': 'Username is required'}

        # Paso 1: Update BaseInfo
        try:
            params = {'name': username}
            if info.get('email'): params['email'] = info['email']
            if info.get('description'): params['description'] = info['description']
            if info.get('password'): params['password'] = info['password']
            
            resp = self.connection.request('SYNO.Core.User', 'update', version=1, params=params)
            if not resp.get('success'):
                 results['errors'].append(f"Base info update failed: {resp}")
            else:
                 results['steps'].append('Base Info Updated')
        except Exception as e:
            results['errors'].append(f"Update info exception: {str(e)}")

        # Paso 2: Aplicar configuraciones avanzadas
        self.apply_user_settings(username, data, results)
        
        results['success'] = len(results['errors']) == 0
        if not results['success']:
             results['message'] = f"Update completed with errors: {'; '.join(results['errors'])}"
        else:
             results['message'] = "User updated successfully."
             
        return results

