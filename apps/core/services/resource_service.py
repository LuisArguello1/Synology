import logging
import json
import os
from django.conf import settings
from apps.settings.services.connection_service import ConnectionService
from apps.settings.models import NASConfig

logger = logging.getLogger(__name__)

class ResourceService:
    """
    Servicio para obtener recursos compartidos del NAS:
    - Shared Folders
    - Volumes
    - Applications
    
    Patrón: Service + API (Online) | JSON Mock (Offline)
    """
    
    def __init__(self):
        self.config = NASConfig.get_active_config()
        self.connection = ConnectionService(self.config)
        # Autenticar automáticamente para tener SID disponible en todas las llamadas
        if not getattr(settings, 'NAS_OFFLINE_MODE', False):
            self.connection.authenticate()
        
        # Archivo de simulación para recursos
        self.sim_file_path = os.path.join(settings.BASE_DIR, 'nas_sim_resources.json')
        self._ensure_sim_file()

    def _ensure_sim_file(self):
        """Crea el archivo de simulación con datos por defecto si no existe."""
        if not os.path.exists(self.sim_file_path):
            default_data = {
                'shares': [
                    {'name': 'homes', 'path': '/volume1/homes', 'description': 'User homes'},
                    {'name': 'music', 'path': '/volume1/music', 'description': 'Music library'},
                    {'name': 'video', 'path': '/volume1/video', 'description': 'Video library'},
                ],
                'volumes': [
                    {'name': '/volume1', 'total_size': 1000 * 1024 * 1024 * 1024, 'used': 200 * 1024 * 1024 * 1024}
                ],
                'apps': [
                    {'name': 'FileStation', 'description': 'File Management'},
                    {'name': 'DSM', 'description': 'Desktop UI'},
                    {'name': 'FTP', 'description': 'FTP Service'},
                ]
            }
            with open(self.sim_file_path, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=4)

    def _get_sim_data(self, key):
        """Lee una clave específica del archivo de simulación."""
        try:
            with open(self.sim_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get(key, [])
        except Exception as e:
            logger.error(f"Error reading simulation file: {e}")
            return []

    def get_shared_folders(self):
        """
        Obtiene carpetas compartidas.
        API: SYNO.Core.Share (list)
        """
        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            return self._get_sim_data('shares')
            
        try:
            # SYNO.Core.Share list
            response = self.connection.request('SYNO.Core.Share', 'list', version=1)
            if response.get('success'):
                # Adaptamos la respuesta para que sea consistente
                shares = response.get('data', {}).get('shares', [])
                return [{
                    'name': s.get('name'),
                    'path': s.get('path'),
                    'description': s.get('desc', '')
                } for s in shares]
            return []
        except Exception as e:
            logger.exception("Error getting shared folders")
            return []

    def get_volumes(self):
        """
        Obtiene volúmenes.
        API: SYNO.Core.Storage.Volume (list)
        """
        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            vols = self._get_sim_data('volumes')
            # Adaptamos formato para que sea consistente con lo que espera el frontend
            results = []
            for v in vols:
                total_gb = round(v.get('total_size', 0) / (1024**3), 2)
                used_gb = round(v.get('used', 0) / (1024**3), 2)
                results.append({
                    'id': v.get('name'),
                    'name': v.get('name'),
                    'total_space': total_gb,
                    'available_space': round(total_gb - used_gb, 2)
                })
            return results

        try:
            response = self.connection.request('SYNO.Core.Storage.Volume', 'list', version=1)
            logger.info(f"Volume API Response: {response}")
            
            if response.get('success'):
                vols = response.get('data', {}).get('volumes', [])
                logger.info(f"Found {len(vols)} volumes")
                results = []
                for v in vols:
                    # Synology API suele devolver tamaños en bytes en 'size' object
                    size = v.get('size', {})
                    total = int(size.get('total', 0))
                    used = int(size.get('used', 0))
                    
                    vol_path = v.get('volume_path')
                    results.append({
                        'id': vol_path,
                        'name': vol_path,
                        'total_space': round(total / (1024**3), 2),
                        'available_space': round((total - used) / (1024**3), 2)
                    })
                
                # Si no hay volúmenes, retornar un volumen por defecto
                if not results:
                    logger.warning("No volumes found in API response, using default /volume1")
                    results = [{
                        'id': '/volume1',
                        'name': '/volume1',
                        'total_space': 1000,
                        'available_space': 500
                    }]
                
                return results
            else:
                logger.error(f"Volume API failed: {response}")
                # Fallback: retornar volumen por defecto
                return [{
                    'id': '/volume1',
                    'name': '/volume1',
                    'total_space': 1000,
                    'available_space': 500
                }]
        except Exception as e:
            logger.exception("Exception getting volumes")
            # Fallback: retornar volumen por defecto
            return [{
                'id': '/volume1',
                'name': '/volume1',
                'total_space': 1000,
                'available_space': 500
            }]

    def get_applications(self):
        """
        Obtiene aplicaciones instaladas/disponibles para permisos.
        API: SYNO.Core.App (list - hipotético, depende de versión DSM)
        Nota: DSM a veces no expone lista simple de apps con permisos via API pública fácil.
        Usaremos una lista fija o simulada si falla el discovery.
        """
        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            return self._get_sim_data('apps')

        # Implementación Online (Simplificada: Retornar lista común si no hay API clara)
        # Muchas veces SYNO.Core.Group options devuelve apps disponibles
        return [
            {'name': 'FileStation', 'description': 'File Station'},
            {'name': 'FTP', 'description': 'FTP'},
            {'name': 'WebDAV', 'description': 'WebDAV'},
            {'name': 'DSM', 'description': 'DSM'}
        ]
