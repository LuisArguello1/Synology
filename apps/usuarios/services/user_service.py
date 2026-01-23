import logging
import json
import re
from django.conf import settings
from apps.settings.services.connection_service import ConnectionService
from apps.settings.models import NASConfig

logger = logging.getLogger(__name__)

class UserService:
    """
    Servicio de orquestación para Gestión de Usuarios Synology.
    Interactúa directamente con SYNO.Core.*
    """
    
    def __init__(self, session='FileStation'):
        self.config = NASConfig.get_active_config()
        self.connection = ConnectionService(self.config)
        # En modo offline, no necesitamos autenticar
        if not getattr(settings, 'NAS_OFFLINE_MODE', False):
            # Autenticar automáticamente para tener SID disponible en todas las llamadas
            self.connection.authenticate(session_alias=session)

    def _validate_user_data(self, data, mode='create'):
        """Validación interna de robustez"""
        info = data.get('info', {})
        username = info.get('name', '').strip()
        email = info.get('email', '').strip()
        password = info.get('password', '')

        # 1. Username
        if not username:
            return False, "El nombre de usuario es requerido"
        
        reserved = ['admin', 'guest']
        if username.lower() in reserved:
            return False, f"El nombre '{username}' es un nombre reservado en Synology"

        if not re.match(r'^[a-zA-Z0-9_\-\.]{1,64}$', username):
            return False, "El nombre de usuario contiene caracteres no permitidos"

        # 2. Email
        if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return False, "El formato del correo electrónico es inválido"

        # 3. Password (solo en creación)
        if mode == 'create' and not password:
            return False, "La contraseña es requerida para nuevos usuarios"

        return True, None
        
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
                data = response.get('data', {})
                users_list = []
                if isinstance(data, list):
                    users_list = data
                elif isinstance(data, dict):
                    users_list = data.get('users') or data.get('items') or data.get('datalist', [])
                
                for u in users_list:
                    if 'user_name' in u and 'name' not in u: u['name'] = u['user_name']
                    if 'desc' in u and 'description' not in u: u['description'] = u['desc']
                
                return users_list
            
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
            # Si falla, iremos quitando campos para asegurar que al menos traemos lo básico
            all_additional = [
                "email", "description", "expired", "groups", 
                "quota", "cannot_change_password", "app_privilege",
                "speed_limit"
            ] 
            
            # Intentos progresivos: 1. Todo, 2. Básico, 3. Mínimo
            attempts = [
                all_additional,
                ["email", "description", "groups", "quota"],
                ["email", "groups"]
            ]

            response = None
            for fields in attempts:
                logger.info(f"Attempting get_user for '{name}' with additional={fields}")
                params = {
                    'name': name,
                    'additional': json.dumps(fields)
                }
                response = self.connection.request(
                    api='SYNO.Core.User',
                    method='get',
                    version=1,
                    params=params
                )
                
                # DSM 7+ a veces prefiere 'user_name' en el GET si 'name' falla con 3106
                if not response.get('success') and response.get('error', {}).get('code') == 3106:
                    logger.info(f"Retrying with 'user_name' parameter for '{name}'")
                    params['user_name'] = name
                    del params['name']
                    response = self.connection.request('SYNO.Core.User', 'get', version=1, params=params)
                
                if response.get('success'):
                    break
                
                error_code = response.get('error', {}).get('code')
                logger.warning(f"get_user failed with code {error_code} for fields {fields}. Retrying...")

            if response and response.get('success'):
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

    def delete_user(self, names):
        """
        Elimina uno o varios usuarios usando sesión administrativa.
        API: SYNO.Core.User method=delete
        """
        # Synology permite nombres separados por coma para borrado en lote
        if isinstance(names, list):
            names = ",".join(names)
            
        admin_conn = ConnectionService(self.config)
        auth_result = admin_conn.authenticate(session_alias='DSM')
        
        if not auth_result.get('success'):
            logger.error(f"Failed to create admin session for deletion: {auth_result}")
            return auth_result
            
        current_sid = auth_result.get('sid')
        try:
            logger.info(f"Deleting user(s): {names}")
            resp = admin_conn.request(
                api='SYNO.Core.User',
                method='delete',
                version=1,
                params={'name': names}
            )
            return resp
        finally:
            if admin_conn and current_sid:
                admin_conn.logout(current_sid, session_alias='DSM')

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
            options['groups'] = [
                {'name': g.get('name') or g.get('group_name'), 'description': g.get('description') or g.get('desc', '')} 
                for g in groups if g.get('name') or g.get('group_name')
            ]

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
                                apps_priv = g_info.get('app_privilege', {})
                                options['group_permissions'][g_name] = {
                                    'shares': {sp['share_name']: sp['privilege'] for sp in g_info.get('share_privilege', [])},
                                    'apps': {}
                                }
                                if isinstance(apps_priv, dict):
                                    options['group_permissions'][g_name]['apps'] = apps_priv
                                elif isinstance(apps_priv, list):
                                    for ap in apps_priv:
                                        if isinstance(ap, dict) and 'app' in ap:
                                            options['group_permissions'][g_name]['apps'][ap['app']] = ap.get('allow', False)
                except Exception as ge:
                    logger.error(f"Error fetching all group permissions: {ge}")
            else:
                # Mock para modo offline si quieres simular herencia de grupos
                options['group_permissions']['users'] = {'shares': {}, 'apps': {}}

        except Exception as e:
            logger.error(f"Error fetching wizard options: {e}")
            
        return options

    # =========================================================================
    # PASOS GRANULARES DSM 7+ (LLAMADAS INDEPENDIENTES)
    # =========================================================================

    def _step_create_user(self, username, password, info, conn):
        """PASO 1: Crear Base (Solo datos básicos)"""
        real_name = info.get('real_name') or info.get('description') or username
        params = {
            'name': username,
            'password': password,
            'real_name': real_name,
            'description': real_name
        }
        if info.get('email'):
            params['email'] = info['email']
        
        logger.info(f"[STEP 1] Creating base user '{username}'")
        resp = conn.request('SYNO.Core.User', 'create', version=1, params=params)
        logger.debug(f"DSM Create response: {resp}")
        return resp  # Devolver respuesta completa para validación en el wizard

    def _step_assign_groups(self, username, groups, conn):
        """PASO 2: Asignar Grupos (Solo agrega los faltantes - FIX DSM 7)"""
        if not groups:
            return True

        import time
        # 1. Esperar propagación real DSM (Retry loop para evitar Error 3106)
        user_propagated = False
        for i in range(5):
            u_check = conn.request('SYNO.Core.User', 'get', version=1, params={'name': username})
            if u_check.get('success') and u_check.get('data', {}).get('users'):
                user_propagated = True
                break
            logger.warning(f"Waiting for user {username} to propagate in DSM... (Attempt {i+1}/5)")
            time.sleep(0.6)

        if not user_propagated:
            logger.error(f"User {username} did not propagate in DSM after 3 seconds.")
            return False

        # 2. Obtener grupos actuales para no re-agregar o borrar por error
        current_groups_raw = []
        user_resp = conn.request('SYNO.Core.User', 'get', version=1, 
                               params={'name': username, 'additional': json.dumps(['groups'])})
        if user_resp.get('success') and user_resp['data']['users']:
            current_groups_raw = user_resp['data']['users'][0].get('groups', [])

        current_groups = []
        for g in current_groups_raw:
            if isinstance(g, dict):
                g_item = g.get('name') or g.get('group_name')
                if g_item: current_groups.append(g_item)
            else:
                current_groups.append(g)

        # 3. Validar grupos existentes en el sistema (Evitar Error 404/105 por grupos inexistentes)
        valid_groups = []
        g_resp = conn.request('SYNO.Core.Group', 'list', version=1)
        if g_resp.get('success'):
            data = g_resp.get('data', {})
            groups_list = data.get('groups') or data.get('items') or []
            valid_groups = [g['name'] for g in groups_list if 'name' in g]
        
        # 4. Filtrar grupos solicitados: Solo existentes y NO protegidos
        # 'users' es asignado por DSM, 'administrators' requiere UI o APIs específicas a veces
        protected_groups = ['users', 'http', 'ftp', 'backup']
        requested_groups = [g for g in groups if g in valid_groups and g not in protected_groups]
        
        if len(requested_groups) != len(groups):
            invalid = [g for g in groups if g not in valid_groups]
            if invalid:
                logger.warning(f"Ignoring NON-EXISTENT groups for DSM: {invalid}")
            protected = [g for g in groups if g in protected_groups]
            if protected:
                logger.info(f"Skipping AUTO-MANAGED/PROTECTED groups: {protected}")

        # 5. Sincronización de Miembros (API SYNO.Core.User.Group)
        to_add = [g for g in requested_groups if g not in current_groups]
        to_remove = [g for g in current_groups if g not in requested_groups and g not in protected_groups]
        
        if not to_add and not to_remove:
            logger.info("No group changes needed.")
            return True

        logger.info(f"[STEP 2] Batch updating groups for '{username}': Join={to_add}, Leave={to_remove}")
        
        # Esta API es la correcta según depuración en vivo del usuario
        params = {
            'name': username,
            'join_group': json.dumps(to_add),
            'leave_group': json.dumps(to_remove)
        }
        
        resp = conn.request('SYNO.Core.User.Group', 'join', version=1, params=params)
        logger.debug(f"DSM Response for SYNO.Core.User.Group:join: {resp}")
        
        if resp.get('success'):
            task_id = resp.get('data', {}).get('task_id', 'N/A')
            logger.info(f"Successfully updated groups for user '{username}' (Task ID: {task_id})")
            return True
        else:
            logger.error(f"DSM RAW GROUP ERROR: {resp}")
            logger.error(f"Failed to update groups for user {username}")
            return False

    def _step_set_flags(self, username, info, conn):
        """PASO 3: Flags de Usuario (Solo campos simples)"""
        params = {'name': username}
        has_flags = False
        
        if 'cannot_change_password' in info:
            params['cannot_change_passwd'] = 'true' if info['cannot_change_password'] else 'false'
            has_flags = True
            
        if info.get('expired') is not None:
            params['expired'] = 'true' if info['expired'] else 'false'
            has_flags = True

        if not has_flags:
            return True
            
        logger.info(f"[STEP 3] Setting user flags for '{username}'")
        resp = conn.request('SYNO.Core.User', 'set', version=1, params=params)
        logger.debug(f"DSM Set Flags response: {resp}")
        return resp.get('success', False)

    def _step_set_app_privs(self, username, apps_data, conn):
        """PASO 4: Permisos de Aplicaciones - MÚLTIPLES ESTRATEGIAS DSM 7+"""
        if not apps_data or not isinstance(apps_data, dict):
            return True
            
        success_count = 0
        fail_count = 0
        
        for app_id, policy in apps_data.items():
            if policy not in ['allow', 'deny']: 
                continue
            
            logger.info(f"[STEP 4] Setting app '{app_id}' to '{policy}' for user '{username}'")
            
            # Convertir allow/deny a valores booleanos
            allow_bool = (policy == 'allow')
            
            # ESTRATEGIA 1: SYNO.Core.AppPriv (API documentada)
            strategies = [
                {
                    'api': 'SYNO.Core.AppPriv',
                    'params': {
                        'name': username,
                        'app': app_id,
                        'is_group': 'false',
                        'allow': 'true' if allow_bool else 'false'
                    }
                },
                # ESTRATEGIA 2: SYNO.Core.AppPriv.App (versión específica)
                {
                    'api': 'SYNO.Core.AppPriv.App',
                    'params': {
                        'name': username,
                        'app': app_id,
                        'is_group': 'false',
                        'allow': 'true' if allow_bool else 'false'
                    }
                },
                # ESTRATEGIA 3: Con username en lugar de name
                {
                    'api': 'SYNO.Core.AppPriv',
                    'params': {
                        'username': username,
                        'app': app_id,
                        'is_group': 'false',
                        'allow': 'true' if allow_bool else 'false'
                    }
                },
                # ESTRATEGIA 4: allow como 1/0 en lugar de true/false
                {
                    'api': 'SYNO.Core.AppPriv',
                    'params': {
                        'name': username,
                        'app': app_id,
                        'is_group': 'false',
                        'allow': '1' if allow_bool else '0'
                    }
                },
            ]
            
            app_success = False
            for idx, strategy in enumerate(strategies, 1):
                logger.debug(f"  → Strategy {idx}/{len(strategies)}: {strategy['api']} with params {strategy['params']}")
                
                resp = conn.request(strategy['api'], 'set', version=1, params=strategy['params'])
                
                if resp.get('success'):
                    logger.info(f"  ✓ SUCCESS with Strategy {idx} ({strategy['api']})")
                    app_success = True
                    break
                else:
                    error_info = resp.get('error', {})
                    logger.warning(f"  ✗ Strategy {idx} failed: code={error_info.get('code')}, error={error_info}")
            
            if app_success:
                success_count += 1
            else:
                logger.error(f"[STEP 4] ALL STRATEGIES FAILED for app '{app_id}'")
                fail_count += 1
        
        logger.info(f"[STEP 4] App Permissions: {success_count} success, {fail_count} failed")
        return fail_count == 0

    def _step_set_folder_perms(self, username, perms_data, conn):
        """PASO 5: Permisos de Carpetas - FORMATO CORRECTO DSM 7+
        
        Formato descubierto del tráfico NAS + pruebas curl exitosas:
        - Campos requeridos: is_admin, is_custom, is_deny, is_readonly, is_writable, name
        - user_group_type: "local_user"
        - permissions: array JSON completo
        """
        if not perms_data or not isinstance(perms_data, dict):
            return True
            
        success_count = 0
        fail_count = 0
        
        for share_name, policy in perms_data.items():
            if policy not in ['rw', 'ro', 'na']: 
                continue
            
            logger.info(f"[STEP 5] Setting folder '{share_name}' to '{policy}' for user '{username}'")
            
            # Convertir policy (rw/ro/na) al formato completo de Synology
            if policy == 'rw':
                perm = {
                    "is_admin": False,
                    "is_custom": False,
                    "is_deny": False,
                    "is_readonly": False,
                    "is_writable": True,
                    "name": username
                }
            elif policy == 'ro':
                perm = {
                    "is_admin": False,
                    "is_custom": False,
                    "is_deny": False,
                    "is_readonly": True,
                    "is_writable": False,
                    "name": username
                }
            elif policy == 'na':  # na = deny
                perm = {
                    "is_admin": False,
                    "is_custom": False,
                    "is_deny": True,
                    "is_readonly": False,
                    "is_writable": False,
                    "name": username
                }
            
            # Formato correcto con TODOS los campos requeridos
            permissions = [perm]
            
            # Llamada con el formato correcto
            params = {
                "name": share_name,
                "user_group_type": "local_user",
                "permissions": json.dumps(permissions)
            }
            
            logger.debug(f"  → Calling SYNO.Core.Share.Permission.set with params: {params}")
            resp = conn.request('SYNO.Core.Share.Permission', 'set', version=1, params=params)
            
            if resp.get('success'):
                logger.info(f"  ✓ SUCCESS setting permission for '{share_name}'")
                success_count += 1
            else:
                error_info = resp.get('error', {})
                logger.error(f"  ✗ FAILED for '{share_name}': code={error_info.get('code')}, error={error_info}")
                fail_count += 1
        
        logger.info(f"[STEP 5] Folder Permissions: {success_count} success, {fail_count} failed")
        return fail_count == 0

    def _step_set_quotas(self, username, quota_data, conn):
        """PASO 6: Cuotas de Almacenamiento - MÚLTIPLES ESTRATEGIAS DSM 7+"""
        if not quota_data or not isinstance(quota_data, dict):
            return True
            
        success_count = 0
        fail_count = 0
        
        for vol_path, q_info in quota_data.items():
            try:
                size_mb = int(q_info.get('size', 0))
                unit = q_info.get('unit', 'MB')
                if unit == 'GB': size_mb *= 1024
                elif unit == 'TB': size_mb *= 1024 * 1024
                
                # Asegurar que vol_path empiece con /
                if not vol_path.startswith('/'):
                    vol_path = f'/{vol_path}'
                
                logger.info(f"[STEP 6] Setting quota on '{vol_path}' to {size_mb}MB for user '{username}'")
                
                # Múltiples estrategias para cuotas
                strategies = [
                    # ESTRATEGIA 1: Parámetros estándar con type='user'
                    {
                        'method': 'set',
                        'params': {
                            'type': 'user',
                            'name': username,
                            'volume_path': vol_path,
                            'size_limit': size_mb
                        }
                    },
                    # ESTRATEGIA 2: Con 'username' en lugar de 'name'
                    {
                        'method': 'set',
                        'params': {
                            'type': 'user',
                            'username': username,
                            'volume_path': vol_path,
                            'size_limit': size_mb
                        }
                    },
                    # ESTRATEGIA 3: Con 'user' en lugar de 'name'
                    {
                        'method': 'set',
                        'params': {
                            'user': username,
                            'volume_path': vol_path,
                            'size_limit': size_mb
                        }
                    },
                    # ESTRATEGIA 4: Con 'vol_path' en lugar de 'volume_path'
                    {
                        'method': 'set',
                        'params': {
                            'type': 'user',
                            'name': username,
                            'vol_path': vol_path,
                            'size_limit': size_mb
                        }
                    },
                    # ESTRATEGIA 5: Con 'quota_size' en lugar de 'size_limit'
                    {
                        'method': 'set',
                        'params': {
                            'type': 'user',
                            'name': username,
                            'volume_path': vol_path,
                            'quota_size': size_mb
                        }
                    },
                    # ESTRATEGIA 6: Sin 'type', solo datos directos
                    {
                        'method': 'set',
                        'params': {
                            'name': username,
                            'volume_path': vol_path,
                            'size_limit': size_mb
                        }
                    },
                ]
                
                quota_success = False
                for idx, strategy in enumerate(strategies, 1):
                    logger.debug(f"  → Strategy {idx}/{len(strategies)}: method={strategy['method']}, params={strategy['params']}")
                    
                    resp = conn.request('SYNO.Core.Quota', strategy['method'], version=1, params=strategy['params'])
                    
                    if resp.get('success'):
                        logger.info(f"  ✓ SUCCESS with Strategy {idx}")
                        quota_success = True
                        break
                    else:
                        error_info = resp.get('error', {})
                        logger.warning(f"  ✗ Strategy {idx} failed: code={error_info.get('code')}, error={error_info}")
                
                if quota_success:
                    success_count += 1
                else:
                    logger.error(f"[STEP 6] ALL STRATEGIES FAILED for volume '{vol_path}'")
                    fail_count += 1
                    
            except Exception as e:
                logger.error(f"[STEP 6] Exception processing quota for {vol_path}: {e}")
                fail_count += 1
        
        logger.info(f"[STEP 6] Quotas: {success_count} success, {fail_count} failed")
        return fail_count == 0

    def _step_set_speed_limit(self, username, speed_data, conn):
        """PASO 7: Límites de Velocidad - MÚLTIPLES ESTRATEGIAS DSM 7+"""
        if not speed_data or not isinstance(speed_data, dict):
            return True
            
        fs = speed_data.get('File Station', {})
        if not fs: 
            return True
    
        logger.info(f"[STEP 7] Setting speed limits for '{username}'")
        
        def to_kb(val, unit):
            try:
                v = int(val)
                return v * 1024 if unit == 'MB' else v
            except:
                return 0

        # Calcular valores
        if fs.get('mode') == 'limit':
            upload_kb = to_kb(fs.get('up', 0), fs.get('up_unit', 'KB'))
            download_kb = to_kb(fs.get('down', 0), fs.get('down_unit', 'KB'))
        elif fs.get('mode') == 'unlimited':
            upload_kb = 0
            download_kb = 0
        else:
            return True  # No hay configuración válida
        
        logger.debug(f"  Calculated: upload={upload_kb}KB/s, download={download_kb}KB/s")
        
        # Múltiples estrategias para límites de velocidad
        strategies = [
            # ESTRATEGIA 1: SYNO.Core.BandwidthControl (API dedicada según documentación)
            {
                'api': 'SYNO.Core.BandwidthControl',
                'method': 'set',
                'params': {
                    'user': username,
                    'upload_limit': upload_kb,
                    'download_limit': download_kb,
                    'enable': 'true'
                }
            },
            # ESTRATEGIA 2: SYNO.Core.BandwidthControl con 'username'
            {
                'api': 'SYNO.Core.BandwidthControl',
                'method': 'set',
                'params': {
                    'username': username,
                    'upload_limit': upload_kb,
                    'download_limit': download_kb
                }
            },
            # ESTRATEGIA 3: SYNO.Core.User con speed_limit_up/down
            {
                'api': 'SYNO.Core.User',
                'method': 'set',
                'params': {
                    'name': username,
                    'speed_limit_up': upload_kb,
                    'speed_limit_down': download_kb
                }
            },
            # ESTRATEGIA 4: SYNO.Core.User con username en lugar de name
            {
                'api': 'SYNO.Core.User',
                'method': 'set',
                'params': {
                    'username': username,
                    'speed_limit_up': upload_kb,
                    'speed_limit_down': download_kb
                }
            },
            # ESTRATEGIA 5: SYNO.Core.BandwidthControl con application_id
            {
                'api': 'SYNO.Core.BandwidthControl',
                'method': 'set',
                'params': {
                    'user_id': username,
                    'application_id': 'SYNO.SDS.FileStation',
                    'upload_limit': upload_kb,
                    'download_limit': download_kb
                }
            },
        ]
        
        for idx, strategy in enumerate(strategies, 1):
            logger.debug(f"  → Strategy {idx}/{len(strategies)}: {strategy['api']}.{strategy['method']} with {strategy['params']}")
            
            resp = conn.request(strategy['api'], strategy['method'], version=1, params=strategy['params'])
            
            if resp.get('success'):
                logger.info(f"  ✓ SUCCESS with Strategy {idx} ({strategy['api']})")
                return True
            else:
                error_info = resp.get('error', {})
                logger.warning(f"  ✗ Strategy {idx} failed: code={error_info.get('code')}, error={error_info}")
        
        logger.error(f"[STEP 7] ALL STRATEGIES FAILED for speed limits")
        return False

    def apply_user_settings(self, username, data, results, conn):
        """Orquestador secuencial (DSM 7 Compatible - Validación Estricta)"""
        info = data.get('info', {})
        
        # 1. Grupos (Paso Estructural - Si falla, abortamos para evitar inconsistencias)
        if 'groups' in data:
            if self._step_assign_groups(username, data['groups'], conn):
                results['steps'].append('Groups Assigned')
            else:
                results['errors'].append('Critical: Group assignment failed. Aborting further settings.')
                return results

        # 2. Flags de Usuario
        if self._step_set_flags(username, info, conn):
            results['steps'].append('Flags Set')
        else:
            results['errors'].append('User flags update failed')

        # 3. Aplicaciones (Control de herencia DSM 7)
        if 'apps' in data:
            apps_raw = data['apps']
            apps_to_apply = {}
            if isinstance(apps_raw, dict):
                apps_to_apply = apps_raw.copy()
            elif isinstance(apps_raw, list):
                apps_to_apply = {app: 'allow' for app in apps_raw}

            # Opcional: Si tenemos info de permisos de grupos, saltamos redundancias
            group_perms = self.get_wizard_options().get('group_permissions', {})
            inherited_apps = {}
            for g_name in data.get('groups', []):
                inherited_apps.update(group_perms.get(g_name, {}).get('apps', {}))
            
            # Filtrar redundancias que el NAS ignorará
            final_apps = {}
            for app_id, policy in apps_to_apply.items():
                is_allow = (policy == 'allow')
                if inherited_apps.get(app_id) == is_allow:
                    logger.info(f"Skipping redundant app privilege for {app_id} (Inherited: {is_allow})")
                    continue
                final_apps[app_id] = policy

            if final_apps:
                if self._step_set_app_privs(username, final_apps, conn):
                    results['steps'].append('App Privileges Applied')
                else:
                    results['errors'].append('Some app privileges failed')
            else:
                results['steps'].append('App Privileges (All inherited/redundant skip)')

        # 4. Carpetas
        if 'permissions' in data:
            if self._step_set_folder_perms(username, data['permissions'], conn):
                results['steps'].append('Folder Permissions Applied')
            else:
                results['errors'].append('Some folder permissions failed')

        # 5. Cuotas
        if 'quota' in data:
            if self._step_set_quotas(username, data['quota'], conn):
                results['steps'].append('Quotas Applied')
            else:
                results['errors'].append('Some quotas failed')

        # 6. Velocidad
        if 'speed' in data:
            if self._step_set_speed_limit(username, data['speed'], conn):
                results['steps'].append('Speed Limits Applied')
            else:
                results['errors'].append('Speed limit setting failed')

        return results

    def create_user_wizard(self, data):
        """Orquestador de CREACIÓN"""
        results = {'success': False, 'steps': [], 'errors': []}

        valid, error_msg = self._validate_user_data(data, mode='create')
        if not valid:
            return {'success': False, 'message': error_msg}
        info = data.get('info', {})
        username = info.get('name')
        
        if not username: return {'success': False, 'message': 'Username is required'}

        # Paso 1: Crear Base
        admin_conn = None
        current_sid = None
        try:
            # Asegurar permisos administrativos (Session: DSM)
            admin_conn = ConnectionService(self.config)
            auth_result = admin_conn.authenticate(session_alias='DSM')
            
            if not auth_result.get('success'):
                logger.error(f"Failed to create admin session: {auth_result}")
                return {'success': False, 'message': f"Failed to authenticate as admin: {auth_result.get('message')}"}
            
            current_sid = auth_result.get('sid')
            
            # 1. Crear Usuario (Básico únicamente)
            resp = self._step_create_user(username, info['password'], info, admin_conn)
            
            if not resp.get('success'):
                error_code = resp.get('error', {}).get('code', 'Unknown')
                return {'success': False, 'message': f"Synology Error {error_code} on Create"}
                
            results['steps'].append('User Created')
            
            # DSM 7 no es transaccional. Esperar un instante para que el sistema propague el nuevo usuario
            import time
            time.sleep(2.5)

            # Pasos 2-7: Aplicar configuraciones avanzadas (Granular)
            self.apply_user_settings(username, data, results, conn=admin_conn)
            
        except Exception as e:
            logger.exception(f"Exception creating user: {str(e)}")
            return {'success': False, 'message': f'Exception: {str(e)}'}
        finally:
            if admin_conn and current_sid:
                admin_conn.logout(current_sid, session_alias='DSM')

        # Paso 3: Evaluar éxito global
        results['success'] = len(results['errors']) == 0
        if not results['success']:
             results['message'] = f"User created but some settings failed: {'; '.join(results['errors'])}"
        else:
             results['message'] = "User created successfully with all settings."
             
        return results

    def update_user_wizard(self, data):
        """Orquestador de ACTUALIZACIÓN"""
        results = {'success': False, 'steps': [], 'errors': []}

        valid, error_msg = self._validate_user_data(data, mode='edit')
        if not valid:
            return {'success': False, 'message': error_msg}

        info = data.get('info', {})
        username = info.get('name')
        
        if not username: return {'success': False, 'message': 'Username is required'}

        # Proceso de actualización modular (DSM 7)
        admin_conn = None
        current_sid = None
        try:
            admin_conn = ConnectionService(self.config)
            auth_result = admin_conn.authenticate(session_alias='DSM')
            if not auth_result.get('success'):
                return {'success': False, 'message': "Admin auth failed"}
            
            current_sid = auth_result.get('sid')
            
            # ACTUALIZACIÓN BASE Y REFRESCO DE CONTEXTO (OBLIGATORIO EN DSM 7)
            base_params = {'name': username}
            
            if info.get('email'):
                base_params['email'] = info['email']
            if info.get('description'):
                base_params['description'] = info['description']
            if info.get('real_name'): # Mantener real_name sincronizado
                base_params['real_name'] = info['real_name']

            # Siempre ejecutamos el set para "despertar" el contexto de DSM 7
            resp_base = admin_conn.request('SYNO.Core.User', 'set', version=1, params=base_params)
            logger.debug(f"DSM Context/Base Update response: {resp_base}")
            
            if resp_base.get('success'):
                results['steps'].append('User Context Refreshed / Base Updated')
            else:
                results['errors'].append(f"Basic update failed: {resp_base.get('error')}")

            # Ejecutar actualización granular reutilizando el orquestador
            self.apply_user_settings(username, data, results, conn=admin_conn)
            
            # Si hay cambio de password, es un flag independiente en User.set
            if info.get('password'):
                admin_conn.request('SYNO.Core.User', 'set', version=1, 
                                 params={'name': username, 'password': info['password']})
                results['steps'].append('Password Updated')

        except Exception as e:
            results['errors'].append(f"Update exception: {str(e)}")
        finally:
            if admin_conn and current_sid:
                admin_conn.logout(current_sid, session_alias='DSM')
        results['success'] = len(results['errors']) == 0
        if not results['success']:
             results['message'] = f"Update completed with errors: {'; '.join(results['errors'])}"
        else:
             results['message'] = "User updated successfully."
             
        return results

