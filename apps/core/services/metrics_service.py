"""
Servicio de métricas para el Dashboard.

Este servicio encapsula la lógica de negocio para obtener
métricas y estadísticas del sistema.

Por ahora retorna datos simulados. En producción, esto se
integraría con la API del NAS Synology.
"""

class MetricsService:
    """
    Servicio para obtener métricas del sistema NAS.
    """
    
    def get_dashboard_metrics(self):
        """
        Obtiene todas las métricas para el dashboard principal.
        
        Returns:
            dict: Diccionario con métricas del sistema:
                - storage: Info de almacenamiento
                - system: Métricas del sistema (CPU, RAM, uptime)
                - recent_files: Archivos recientes
                - activity: Actividad reciente
        """
        return {
            'storage': self._get_storage_metrics(),
            'system': self._get_system_metrics(),
            'recent_files': self._get_recent_files(),
            'activity': self._get_recent_activity(),
        }
    
    def _get_storage_metrics(self):
        """
        Obtiene métricas de almacenamiento.
        
        En producción, esto llamaría a la API del NAS:
        - SYNO.Core.System para info del sistema
        - SYNO.Storage.CGI.Storage para info de volúmenes
        """
        return {
            'total': '10 TB',
            'used': '6.5 TB',
            'available': '3.5 TB',
            'percent_used': 65,
            'volumes': [
                {
                    'name': 'Volume 1',
                    'total': '8 TB',
                    'used': '5.2 TB',
                    'percent': 65
                },
                {
                    'name': 'Volume 2',
                    'total': '2 TB',
                    'used': '1.3 TB',
                    'percent': 65
                }
            ]
        }
    
    def _get_system_metrics(self):
        """
        Obtiene métricas del sistema (CPU, RAM, etc).
        
        En producción: SYNO.Core.System.Utilization
        """
        return {
            'cpu_usage': 23,
            'memory_usage': 45,
            'uptime_days': 127,
            'temperature': 42,  # Celsius
            'network': {
                'upload': '125 Mbps',
                'download': '890 Mbps'
            }
        }
    
    def _get_recent_files(self):
        """
        Obtiene lista de archivos recientes.
        
        En producción: SYNO.FileStation.List con filtro de fecha
        """
        return [
            {
                'name': 'backup_2026-01-15.zip',
                'size': '2.3 GB',
                'date': '2026-01-15',
                'type': 'archive',
                'icon': 'file-archive'
            },
            {
                'name': 'Fotos_Vacaciones.tar.gz',
                'size': '5.1 GB',
                'date': '2026-01-14',
                'type': 'archive',
                'icon': 'file-archive'
            },
            {
                'name': 'Documentos_Q1_2026.pdf',
                'size': '12.5 MB',
                'date': '2026-01-13',
                'type': 'document',
                'icon': 'file-pdf'
            },
            {
                'name': 'Video_Presentacion.mp4',
                'size': '1.8 GB',
                'date': '2026-01-12',
                'type': 'video',
                'icon': 'file-video'
            },
        ]
    
    def _get_recent_activity(self):
        """
        Obtiene actividad reciente del sistema.
        
        En producción: Logs del sistema
        """
        return [
            {
                'type': 'upload',
                'user': 'admin',
                'description': 'Subió backup_2026-01-15.zip',
                'timestamp': '2026-01-15 18:30:00',
                'icon': 'cloud-upload-alt',
                'color': 'blue'
            },
            {
                'type': 'download',
                'user': 'usuario1',
                'description': 'Descargó Fotos_Vacaciones.tar.gz',
                'timestamp': '2026-01-15 16:15:00',
                'icon': 'cloud-download-alt',
                'color': 'green'
            },
            {
                'type': 'share',
                'user': 'admin',
                'description': 'Compartió carpeta "Proyectos"',
                'timestamp': '2026-01-15 14:00:00',
                'icon': 'share-alt',
                'color': 'purple'
            },
            {
                'type': 'login',
                'user': 'usuario2',
                'description': 'Inició sesión en el sistema',
                'timestamp': '2026-01-15 09:45:00',
                'icon': 'sign-in-alt',
                'color': 'gray'
            },
        ]
