import logging
import json
from django.conf import settings
from apps.settings.services.connection_service import ConnectionService
from apps.settings.models import NASConfig

logger = logging.getLogger(__name__)

class UserService:
    """
    Servicio de orquestación para Gestión de Usuarios Synology.
    Ubicación: apps/usuarios/services/user_service.py
    No guarda estado local. Interactúa directamente con SYNO.Core.*
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
        Obtiene detalles de UN usuario.
        API: SYNO.Core.User method=get
        """
        try:
            additional = ["email", "description", "expired", "groups", "quota", "cannot_change_password"] 
            
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
                # get devuelve una lista 'users' con un elemento
                users = response.get('data', {}).get('users', [])
                return users[0] if users else None
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
        Obtiene TODAS las dependencias para poblar los selects del Wizard:
        - Grupos existentes (API/Simulado)
        - Carpetas compartidas (API/Simulado)
        - Volumenes (API/Simulado)
        - Apps (API/Simulado)
        """
        from apps.groups.services.group_service import GroupService
        from apps.core.services.resource_service import ResourceService
        
        options = {
            'groups': [],
            'shares': [],
            'apps': [],
            'volumes': []
        }
        
        try:
            group_service = GroupService()
            resource_service = ResourceService()

            # 1. Grupos (Service)
            groups = group_service.list_groups()
            options['groups'] = [{'name': g.get('name'), 'description': g.get('description', '')} for g in groups]

            # 2. Shares (Service)
            shares = resource_service.get_shared_folders()
            options['shares'] = shares # Ya viene formateado del servicio

            # 3. Apps (Service)
            apps = resource_service.get_applications()
            options['apps'] = [{'name': a.get('name'), 'desc': a.get('description')} for a in apps]
            
            # 4. Volúmenes (Service)
            options['volumes'] = resource_service.get_volumes()
            if not options['volumes']:
                options['volumes'] = ['/volume1'] # Fallback

        except Exception as e:
            logger.error(f"Error fetching wizard options: {e}")
            
        return options

    def create_user_wizard(self, data):
        """
        ORQUESTADOR DE CREACIÓN DE USUARIO.
        Ejecuta pasos secuenciales y aplica configuraciones complejas.
        """
        results = {'success': False, 'steps': [], 'errors': []}
        info = data.get('info', {})
        username = info.get('name')
        
        if not username:
            return {'success': False, 'message': 'Username is required'}

        # ---------------------------------------------------------
        # PASO 1: Crear Usuario Base (SYNO.Core.User / create)
        # ---------------------------------------------------------
        try:
            params = {
                'name': info['name'],
                'password': info['password'],
                'email': info.get('email', ''),
                'description': info.get('description', ''),
                'expired': 'normal'
            }
            
            resp = self.connection.request('SYNO.Core.User', 'create', version=1, params=params)
            
            if not resp.get('success'):
                error_code = resp.get('error', {}).get('code', 'unknown')
                return {'success': False, 'message': f'Failed to create user. Synology Error: {error_code}'}
            
            results['steps'].append('User Created')
            
        except Exception as e:
            logger.exception("Error creating user base")
            return {'success': False, 'message': f'Exception creating user: {str(e)}'}

        # Si llegamos aqui, el usuario existe. 
        # Ahora preparamos un GRAN update o varios updates para configurar lo demás.
        # Synology SYNO.Core.User update (v1) soporta muchos parametros simultaneos.
        
        update_params = {'name': username}
        has_updates = False

        # ---------------------------------------------------------
        # PASO 2: Grupos
        # ---------------------------------------------------------
        if 'groups' in data and data['groups']:
            # groups debe ser CSV
            update_params['groups'] = ",".join(data['groups'])
            has_updates = True

        # ---------------------------------------------------------
        # PASO 3: Permisos Carpetas (shares: JSON)
        # ---------------------------------------------------------
        # data['permissions'] es un dict: {'shareName': 'rw', ...}
        # Synology espera un array de objetos en un string JSON si la API lo soporta, 
        # OJO: V1 a veces no tiene "permissions" param en 'User update'.
        # Si no lo soporta, habría que usar SYNO.Core.Share.Permission set por cada carpeta.
        # Asumiremos la estrategia de intentar pasarlo en update (algunas versiones DSM lo aceptan), 
        # si no, iteraremos.
        # Estrategia segura: Iterar SYNO.Core.Share.Permission para cada share modificado.
        
        # ---------------------------------------------------------
        # PASO 3: Permisos Carpetas (SYNO.Core.Share.Permission)
        # ---------------------------------------------------------
        # La API de usuarios v1 no siempre acepta permisos de share en el update.
        # La forma canónica "Regla del NAS" es iterar sobre los shares y usar su API específica.
        if 'permissions' in data and data['permissions']:
            perm_errors = []
            for share_name, policy in data['permissions'].items():
                if policy not in ['rw', 'ro', 'na']: continue
                
                try:
                    # SYNO.Core.Share.Permission: method='write' 
                    # params: name=<ShareName>, user_name=<User>, privilege=<rw|ro|na>
                    p_resp = self.connection.request(
                        api='SYNO.Core.Share.Permission',
                        method='write',
                        version=1,
                        params={
                            'name': share_name,
                            'user_name': username,
                            'privilege': policy
                        }
                    )
                    
                    if not p_resp.get('success'):
                         perm_errors.append(f"{share_name}: {p_resp}")
                         
                except Exception as e:
                    perm_errors.append(f"{share_name} Exception: {str(e)}")
            
            if perm_errors:
                results['errors'].append(f"Permission errors: {perm_errors}")
            else:
                results['steps'].append('Folder Permissions Applied')

        # ---------------------------------------------------------
        # PASO 4: Cuota (quota: JSON)
        # ---------------------------------------------------------
        if 'quota' in data and data['quota']:
            quota_list = []
            for vol_path, q_data in data['quota'].items():
                size_mb = int(q_data.get('size', 0))
                unit = q_data.get('unit', 'MB')
                
                if unit == 'GB': size_mb *= 1024
                elif unit == 'TB': size_mb *= 1024 * 1024
                
                # Formato estándar para SYNO.Core.User quota_limit
                quota_list.append({
                    "volume_path": vol_path,
                    "size_limit": size_mb 
                })
            
            if quota_list:
                update_params['quota_limit'] = json.dumps(quota_list)
                has_updates = True

        # ---------------------------------------------------------
        # PASO 5: Apps (apps: List)
        # ---------------------------------------------------------
        # Aquí seteamos permisos de aplicación explícitos.
        if 'apps' in data:
            app_list = []
            # data['apps'] contiene nombres de apps permitidas.
            # Synology espera objetos con "allow": true/false
            
            for app_name in data['apps']:
                app_list.append({
                    "app": app_name,
                    "allow": True,          # Permitir acceso
                    "allow_empty": False    # No heredar
                })
            
            if app_list:
                update_params['app_privilege'] = json.dumps(app_list)
                has_updates = True
        
        # ---------------------------------------------------------
        # PASO 6: Limites de Velocidad (speed: JSON)
        # ---------------------------------------------------------
        if 'speed' in data and data['speed']:
             # speed = { 'upload_value': 100, 'upload_unit': 'KB', ... }
             # SYNO.Core.User update espera 'speed_limit_up' y 'speed_limit_down' (en KB/s usualmente)
             s_data = data['speed']
             
             # Calculadora simple a KB
             def to_kb(val, unit):
                 try: 
                     val = int(val)
                     if unit == 'MB': return val * 1024
                     return val
                 except: return 0

             up_kb = to_kb(s_data.get('upload_value'), s_data.get('upload_unit'))
             down_kb = to_kb(s_data.get('download_value'), s_data.get('download_unit'))
             
             if up_kb > 0:
                 update_params['speed_limit_up'] = up_kb
                 has_updates = True
             if down_kb > 0:
                 update_params['speed_limit_down'] = down_kb
                 has_updates = True

        # ---------------------------------------------------------
        # EJECUTAR UPDATE MASIVO
        # ---------------------------------------------------------
        if has_updates:
            try:
                resp_up = self.connection.request('SYNO.Core.User', 'update', version=1, params=update_params)
                if resp_up.get('success'):
                    results['steps'].append('Settings Updated')
                else:
                    results['errors'].append(f"Update failed: {resp_up}")
            except Exception as e:
                results['errors'].append(f"Update exception: {str(e)}")

        if results['errors']:
            results['success'] = False
            results['message'] = "User created but some settings failed: " + "; ".join(results['errors'])
        else:
            results['success'] = True
        
        return results

    def update_user(self, name, data):
        return self.connection.request('SYNO.Core.User', 'update', version=1, params=data)
