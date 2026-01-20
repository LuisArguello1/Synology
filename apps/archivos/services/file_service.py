import logging
import json
import urllib.parse
from apps.settings.services.connection_service import ConnectionService
from apps.settings.models import NASConfig
from django.conf import settings

logger = logging.getLogger(__name__)

class FileService:
    """
    Servicio para interactuar con el sistema de archivos del NAS vía SYNO.FileStation.
    Encapsula lógica de listado, operaciones de archivos y manejo de permisos.
    """

    def __init__(self):
        self.config = NASConfig.get_active_config()
        self.connection = ConnectionService(self.config)
        # Check offline mode
        self.offline_mode = getattr(settings, 'NAS_OFFLINE_MODE', False)
        
        if not self.offline_mode:
            self.connection.authenticate()

    def list_shares(self, additional=None):
        """
        Lista las carpetas compartidas raíz (Shared Folders).
        API: SYNO.FileStation.List method=list_share
        """
        if self.offline_mode:
            return self._get_mock_shares()

        if additional is None:
            additional = ["perm", "real_path", "size", "owner", "time", "volume_status"]
            
        try:
            response = self.connection.request(
                api='SYNO.FileStation.List',
                method='list_share',
                version=2,
                params={
                    'additional': json.dumps(additional),
                    'check_dir': True
                }
            )
            
            if response.get('success'):
                shares = response.get('data', {}).get('shares', [])
                return self._process_items(shares)
            else:
                logger.error(f"Error listing shares: {response}")
                return []
        except Exception as e:
            logger.exception("Exception listing shares")
            return []

    def list_files(self, folder_path, additional=None):
        """
        Lista contenido de una carpeta específica.
        API: SYNO.FileStation.List method=list
        """
        if self.offline_mode:
            return self._get_mock_files(folder_path)

        if additional is None:
            # Metadata clave para el frontend
            additional = ["perm", "real_path", "size", "owner", "time", "type"]

        try:
            response = self.connection.request(
                api='SYNO.FileStation.List',
                method='list',
                version=2,
                params={
                    'folder_path': folder_path,
                    'additional': json.dumps(additional),
                    'check_dir': True
                }
            )
            
            if response.get('success'):
                files = response.get('data', {}).get('files', [])
                return self._process_items(files)
            else:
                 logger.error(f"Error listing files in {folder_path}: {response}")
                 return []
        except Exception as e:
            logger.exception(f"Exception listing files in {folder_path}")
            return []

    def create_folder(self, folder_path, name, force_parent=False):
        """
        Crea una nueva carpeta.
        API: SYNO.FileStation.CreateFolder method=create
        """
        if self.offline_mode:
            return {'success': True, 'data': {'folders': [{'path': f"{folder_path}/{name}", 'name': name, 'isdir': True}]}}

        try:
            # force_parent: crea carpetas padre si no existen (opcional)
            response = self.connection.request(
                api='SYNO.FileStation.CreateFolder',
                method='create',
                version=2,
                params={
                    'folder_path': folder_path,
                    'name': name,
                    'force_parent': str(force_parent).lower()
                }
            )
            return response
        except Exception as e:
            return {'success': False, 'error': {'code': 9999, 'msg': str(e)}}

    def rename_item(self, path, name):
        """
        Renombra un archivo o carpeta.
        API: SYNO.FileStation.Rename method=rename
        """
        if self.offline_mode:
            return {'success': True, 'data': {'files': [{'path': f"{path}_renamed", 'name': name}]}}

        try:
            response = self.connection.request(
                api='SYNO.FileStation.Rename',
                method='rename',
                version=2,
                params={
                    'path': path,
                    'name': name
                }
            )
            return response
        except Exception as e:
             return {'success': False, 'error': {'code': 9999, 'msg': str(e)}}

    def delete_item(self, paths):
        """
        Elimina archivo(s) o carpeta(s) (sincrónico).
        API: SYNO.FileStation.Delete method=delete
        """
        if self.offline_mode:
             return {'success': True}

        try:
            # paths puede ser una lista o un string separado por comas
            if isinstance(paths, list):
                paths = ','.join(paths)
                
            response = self.connection.request(
                api='SYNO.FileStation.Delete',
                method='delete',
                version=2,
                params={
                    'path': paths,
                    'recursive': 'true' 
                }
            )
            return response
        except Exception as e:
            return {'success': False, 'error': {'code': 9999, 'msg': str(e)}}

    def upload_file(self, folder_path, file_obj, create_parents=True, overwrite=True):
        """
        Sube un archivo a una carpeta específica.
        API: SYNO.FileStation.Upload method=upload
        """
        if self.offline_mode:
             return {'success': True, 'data': {'file': {'path': f"{folder_path}/{file_obj.name}", 'name': file_obj.name}}}

        try:
            import requests # Import local para evitar circularidad si fuera top-level (aunque no lo es, es seguro)
            
            # 1. Preparar URL y Params
            # Usamos entry.cgi como punto de entrada genérico si no tenemos path específico cacheado
            # Idealmente deberíamos usar self.connection._get_api_info('SYNO.FileStation.Upload') pero es interno.
            # Asumiremos entry.cgi que funciona con el alias.
            url = f"{self.connection.get_base_url()}/webapi/entry.cgi"
            
            sid = self.connection.get_sid()
            if not sid:
                return {'success': False, 'error': {'code': 401, 'msg': 'No session ID (Not authenticated)'}}

            params = {
                'api': 'SYNO.FileStation.Upload',
                'method': 'upload',
                'version': 2,
                'path': folder_path,
                'create_parents': str(create_parents).lower(),
                'overwrite': str(overwrite).lower(),
                '_sid': sid
            }
            
            # 2. Preparar Archivo
            # 'file' es el nombre del campo esperado por Synology
            files = {'file': (file_obj.name, file_obj, file_obj.content_type)}
            
            # 3. Request
            response = requests.post(url, data=params, files=files, verify=False, timeout=300) # 5 min timeout para uploads
            
            if response.status_code == 200:
                return response.json()
            else:
                 return {'success': False, 'error': {'code': response.status_code, 'msg': 'HTTP Error'}}

        except Exception as e:
            return {'success': False, 'error': {'code': 9999, 'msg': str(e)}}

    def copy_move_item(self, path, dest_folder, is_move=False):
        """
        Inicia tarea de Copiado o Movimiento.
        API: SYNO.FileStation.CopyMove method=start
        """
        action_name = "move" if is_move else "copy"
        
        if self.offline_mode:
            return {'success': True, 'message': f'Simulación: {action_name} de {path} a {dest_folder} iniciado.'}

        try:
            # Synology CopyMove start params:
            # path: ruta(s) origen (pueden ser multiples separadas por coma)
            # dest_folder_path: carpeta destino
            # remove_src: true para move, false para copy
            # overwrite: comportamiento ante colisiones (opcional, por defecto overwrite o skip)
            
            response = self.connection.request(
                api='SYNO.FileStation.CopyMove',
                method='start',
                version=3,
                params={
                    'path': path,
                    'dest_folder_path': dest_folder,
                    'remove_src': str(is_move).lower(),
                    'overwrite': 'true' # Simplificacion para UX
                }
            )
            
            # La respuesta incluye un taskid para polling.
            # Para esta iteración, asumiremos que "start" exitoso es suficiente feedback
            # o podríamos implementar un polling loop simple en el frontend si el taskid se retorna.
            return response
            
        except Exception as e:
             return {'success': False, 'error': {'code': 9999, 'msg': str(e)}}

    def search_files(self, folder_path, pattern):
        """
        Busca archivos que coincidan con el patrón.
        API: SYNO.FileStation.Search method=start -> list
        Nota: Search también es asíncrono (start -> list task).
        Para búsquedas rápidas, intentaremos listar y filtrar si el API de search es complejo de implementar en una fase.
        
        Sin embargo, SYNO.FileStation.List tiene filtros básicos? No, List es directo.
        Vamos a usar SYNO.FileStation.Search correctamente.
        1. start
        2. list (con taskid)
        
        Simplificación para UX inmedita:
        Si el usuario busca en una carpeta con pocos archivos, filtrado en cliente es mejor.
        Si busca recursivo, necesitamos API.
        
        Implementaremos la API real.
        """
        if self.offline_mode:
             # Retornar mocks filtrados es complejo sin estado real, devolvemos mocks estáticos
             return self._get_mock_files(folder_path) # Return standard files as "results"

        try:
            # 1. Start Search Task
            start_res = self.connection.request(
                api='SYNO.FileStation.Search',
                method='start',
                version=2,
                params={
                    'folder_path': folder_path,
                    'pattern': pattern,
                    'recursive': 'true'
                }
            )
            
            if not start_res.get('success'):
                return start_res
                
            task_id = start_res.get('data', {}).get('taskid')
            
            # 2. List Results (Synchronous wait logic simplified)
            # En una app real, el frontend haría polling. Aquí haremos un wait corto y retornaremos lo que haya.
            import time
            time.sleep(0.5) # Esperar un poco a que indexe algo
            
            list_res = self.connection.request(
                api='SYNO.FileStation.Search',
                method='list',
                version=2,
                params={
                    'taskid': task_id,
                    'limit': 100,
                    'additional': json.dumps(["size", "owner", "time", "type"])
                }
            )
            
            if list_res.get('success'):
                files = list_res.get('data', {}).get('files', [])
                return self._process_items(files)
            else:
                 return []
                 
        except Exception as e:
            return {'success': False, 'error': {'code': 9999, 'msg': str(e)}}
            
    def get_file_stream(self, path):
        """
        Obtiene stream de archivo para descarga o visualización.
        API: SYNO.FileStation.Download method=download
        """
        if self.offline_mode:
             return None, "Offline mode"

        try:
            import requests
            url = f"{self.connection.get_base_url()}/webapi/entry.cgi"
            sid = self.connection.get_sid()
            
            params = {
                'api': 'SYNO.FileStation.Download',
                'method': 'download',
                'version': 2,
                'path': path,
                'mode': 'download',
                '_sid': sid
            }
            
            response = requests.get(url, params=params, stream=True, verify=False, timeout=300)
            if response.status_code == 200:
                return response, None
            else:
                return None, f"HTTP Error {response.status_code}"
                
        except Exception as e:
            logger.exception("Error getting file stream")
            return None, str(e)

    def get_download_url(self, path):
        """
        Devuelve URL para descargar archivo.
        En esta implementación, redirigimos a nuestro propio endpoint interno.
        """
        return {'success': True, 'path': path}

    def _process_items(self, items):
        """
        Procesa la lista cruda de ítems para normalizar datos y permisos para el frontend.
        """
        normalized = []
        for item in items:
            perm = item.get('perm', {})
            # Simplificación de permisos para el frontend
            # ACL mode puede ser compleja, aquí extraemos lo básico para UI
            # posix o acl. Asumimos acl por defecto en DSM moderno.
            
            is_dir = item.get('isdir', False)
            
            # TODO: Mapeo más robusto según documentación de 'perm' de Synology
            # Por ahora basamos en la existencia de flags comunes
            can_write = perm.get('posix', 0) > 0 or item.get('perm', {}).get('acl', {}).get('append', False) # Placeholder logic
            
            acl = perm.get('acl', {})
            is_acl = perm.get('is_acl_mode', False)
            
            permissions = {
                'can_view': True, # Si está en lista, puede verlo (generalmente)
                'can_download': acl.get('read', True),
                'can_write': acl.get('write', False),
                'can_upload': acl.get('write', False) and is_dir,
                'can_delete': acl.get('del', False),
                'can_rename': acl.get('write', False) # Renombrar suele requerir write
            }

            normalized.append({
                'name': item.get('name'),
                'path': item.get('path'),
                'is_dir': is_dir,
                'size': item.get('additional', {}).get('size', 0), # A veces size está en root, a veces en additional
                'formatted_size': self._format_size(item.get('additional', {}).get('size', item.get('size', 0))),
                'type': 'folder' if is_dir else self._guess_type(item.get('name')),
                'time': item.get('additional', {}).get('time', {}).get('mtime', 0),
                'owner': item.get('additional', {}).get('owner', {}).get('user', ''),
                'permissions': permissions
            })
        return normalized

    def _format_size(self, size):
        # Convert bytes to human readable
        if not size: return '0 B'
        size = int(size)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    def _guess_type(self, filename):
        if not filename: return 'unknown'
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp']: return 'image'
        if ext in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt']: return 'document'
        if ext in ['zip', 'rar', '7z', 'tar', 'gz']: return 'archive'
        return 'file'

    # --- Mocks ---
    def _get_mock_shares(self):
        """Simula carpetas raíz"""
        import time
        now = int(time.time())
        mocks = [
            {'name': 'home', 'path': '/home', 'isdir': True, 'additional': {'size': 1024*1024*50, 'time': {'mtime': now}, 'owner': {'user': 'admin'}}},
            {'name': 'homes', 'path': '/homes', 'isdir': True, 'additional': {'size': 1024*1024*500, 'time': {'mtime': now}, 'owner': {'user': 'root'}}},
            {'name': 'projects', 'path': '/projects', 'isdir': True, 'additional': {'size': 1024*1024*1024*2, 'time': {'mtime': now}, 'owner': {'user': 'admin'}}},
            {'name': 'music', 'path': '/music', 'isdir': True, 'additional': {'size': 1024*1024*300, 'time': {'mtime': now}, 'owner': {'user': 'admin'}}},
            {'name': 'video', 'path': '/video', 'isdir': True, 'additional': {'size': 1024*1024*1024*10, 'time': {'mtime': now}, 'owner': {'user': 'admin'}}},
        ]
        return self._process_items(mocks)

    def _get_mock_files(self, folder_path):
        """Simula contenido de carpetas"""
        import time
        import random
        now = int(time.time())
        # Contenido determinista basado en el path para parecer real
        items = []
        
        # Subcarpetas simuladas
        for i in range(3):
             items.append({
                'name': f'Carpeta_{i+1}', 
                'path': f'{folder_path}/Carpeta_{i+1}', 
                'isdir': True, 
                'additional': {'size': 4096, 'time': {'mtime': now}}
            })
            
        # Archivos simulados
        file_types = ['document.pdf', 'image.jpg', 'archive.zip', 'notes.txt', 'presentation.pptx']
        for i in range(5):
            fname = file_types[i]
            items.append({
                'name': fname,
                'path': f'{folder_path}/{fname}',
                'isdir': False,
                'additional': {'size': random.randint(1024, 1024*1024*5), 'time': {'mtime': now}}
            })
            
        return self._process_items(items)
