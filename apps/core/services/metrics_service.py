import logging
import json
from django.conf import settings
from apps.settings.services.connection_service import ConnectionService
from apps.settings.models import NASConfig

logger = logging.getLogger(__name__)

class MetricsService:
    """
    Servicio para obtener métricas REALES del sistema NAS.
    """
    
    def __init__(self):
        self.config = NASConfig.get_active_config()
        # En modo offline, no necesitamos autenticar
        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            self.connected = True
            return

        # Intentamos conectar, si falla, métodos devolverán estado vacío/error graceful
        try:
            self.connection = ConnectionService(self.config)
            self.connection.authenticate()
            self.connected = True
        except Exception as e:
            logger.error(f"MetricsService failed to connect: {e}")
            self.connected = False
    
    def get_dashboard_metrics(self):
        """
        Obtiene todas las métricas para el dashboard principal.
        """
        from django.conf import settings
        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            return self._get_mock_metrics()

        if not self.connected:
            return self._get_empty_metrics("No connection to NAS")

        return {
            'storage': self._get_storage_metrics(),
            'system': self._get_system_metrics(),
            'health': self._get_health_status(),
            'connections': self._get_active_connections(),
            'recent_files': self._get_recent_files(),
            'activity': self._get_recent_activity(),
        }

    def _get_mock_metrics(self):
        """Métricas de ejemplo para desarrollo offline"""
        return {
            'storage': {
                'total': '16.0 TB', 
                'used': '4.2 TB', 
                'available': '11.8 TB',
                'percent_used': 26.3,
                'volumes': [
                    {'name': 'Volume 1 (SATA)', 'total': '8.0 TB', 'used': '3.5 TB', 'percent': 43.8},
                    {'name': 'Volume 2 (SSD)', 'total': '8.0 TB', 'used': '0.7 TB', 'percent': 8.8},
                ]
            },
            'system': {
                'cpu_usage': 12, 
                'memory_usage': 34, 
                'uptime_days': 15, 
                'temperature': 42,
                'network': {'upload': '24.5 KB/s', 'download': '1.2 MB/s', 'up_raw': 25088, 'down_raw': 1258291}
            },
            'health': {'status': 'health-ok', 'is_ok': True},
            'connections': {'total': 3},
            'recent_files': [
                {'name': 'Proyecto_Final.pdf', 'path': '/volume1/Compartida/Proyectos', 'size': '2.4 MB', 'time': '2026-01-17 01:45:10', 'ext': 'pdf'},
                {'name': 'Dataset_Entrenamiento.zip', 'path': '/volume1/Investigacion', 'size': '1.2 GB', 'time': '2026-01-17 01:10:05', 'ext': 'zip'},
                {'name': 'Presupuesto_2026.xlsx', 'path': '/volume1/admin/Contabilidad', 'size': '450 KB', 'time': '2026-01-16 22:30:45', 'ext': 'xlsx'},
                {'name': 'Logo_Facultad.png', 'path': '/volume1/Multimedia/Diseño', 'size': '8.1 MB', 'time': '2026-01-16 15:20:00', 'ext': 'png'},
                {'name': 'Manual_Usuario.docx', 'path': '/volume1/Compartida/Docs', 'size': '1.1 MB', 'time': '2026-01-15 09:12:33', 'ext': 'docx'},
            ],
            'activity': [
                {'time': '2026-01-17 01:20:45', 'user': 'admin', 'level': 'info', 'msg': 'User [luis] logged in from [192.168.1.15]'},
                {'time': '2026-01-17 01:15:22', 'user': 'system', 'level': 'warn', 'msg': 'Backup task [Weekly Backup] interrupted'},
                {'time': '2026-01-17 00:50:10', 'user': 'admin', 'level': 'info', 'msg': 'File [/volume1/Compartida/report.pdf] was modified'},
                {'time': '2026-01-16 23:45:00', 'user': 'system', 'level': 'err', 'msg': 'Fan speed on [Disk 1] returned to normal'},
                {'time': '2026-01-16 10:30:15', 'user': 'luis', 'level': 'info', 'msg': 'Connected to shared folder [Documentos]'},
            ]
        }

    def _get_empty_metrics(self, msg=""):
        return {
            'storage': {'total': 'N/A', 'used': 'N/A', 'percent_used': 0, 'volumes': []},
            'system': {
                'cpu_usage': 0, 
                'memory_usage': 0, 
                'uptime_days': 0, 
                'temperature': 0,
                'network': {'upload': '0 KB/s', 'download': '0 KB/s', 'up_raw': 0, 'down_raw': 0}
            },
            'health': {'status': 'Unknown', 'is_ok': False},
            'connections': {'total': 0},
            'recent_files': [],
            'activity': []
        }
    
    def _get_storage_metrics(self):
        """
        Obtiene métricas de almacenamiento vía SYNO.Storage.CGI.Storage
        """
        try:
            # Esta API suele devolver info detallada de volumenes
            # params: {version: 1, method: load_info} (o list)
            resp = self.connection.request('SYNO.Storage.CGI.Storage', 'load_info', version=1)
            
            if resp.get('success'):
                vols = resp.get('data', {}).get('vol_info', [])
                
                total_bytes = 0
                used_bytes = 0
                volumes_data = []

                for vol in vols:
                    # Synology suele usar bytes en strings o enteros
                    try:
                        t = int(vol.get('total_size', 0))
                        u = int(vol.get('used_size', 0))
                        
                        total_bytes += t
                        used_bytes += u
                        
                        pct = round((u / t * 100), 1) if t > 0 else 0
                        
                        volumes_data.append({
                            'name': vol.get('name', 'Volume'),
                            'total': self._format_bytes(t),
                            'used': self._format_bytes(u),
                            'percent': pct
                        })
                    except:
                        continue

                global_pct = round((used_bytes / total_bytes * 100), 1) if total_bytes > 0 else 0
                
                return {
                    'total': self._format_bytes(total_bytes),
                    'used': self._format_bytes(used_bytes),
                    'available': self._format_bytes(total_bytes - used_bytes),
                    'percent_used': global_pct,
                    'volumes': volumes_data
                }
                
            return {'total': '0', 'used': '0', 'percent_used': 0}

        except Exception as e:
            logger.error(f"Error fetching storage metrics: {e}")
            return {'total': 'Error', 'used': 'Error', 'percent_used': 0}
    
    def _get_system_metrics(self):
        """
        Obtiene métricas vía SYNO.Core.System o Utilization
        """
        metrics = {
            'cpu_usage': 0,
            'memory_usage': 0,
            'uptime_days': 0,
            'temperature': 0,
            'network': {'upload': '0 KB/s', 'download': '0 KB/s', 'up_raw': 0, 'down_raw': 0}
        }
        
        try:
            # 1. Utilización (CPU, RAM, Network)
            util_resp = self.connection.request('SYNO.Core.System.Utilization', 'get', version=1)
            if util_resp.get('success'):
                data = util_resp.get('data', {})
                # cpu suele ser user_load + system_load
                cpu = data.get('cpu', {})
                metrics['cpu_usage'] = cpu.get('user_load', 0) + cpu.get('system_load', 0)
                
                # RAM
                mem = data.get('memory', {})
                if 'real_usage' in mem:
                    metrics['memory_usage'] = mem['real_usage']
                    
                # Network flow
                net = data.get('network', [])
                if net and len(net) > 0:
                    tx_total = sum(int(n.get('tx', 0)) for n in net)
                    rx_total = sum(int(n.get('rx', 0)) for n in net)
                    metrics['network']['up_raw'] = tx_total
                    metrics['network']['down_raw'] = rx_total
                    metrics['network']['upload'] = self._format_speed(tx_total)
                    metrics['network']['download'] = self._format_speed(rx_total)

            # 2. System Status (Uptime, Temp)
            info_resp = self.connection.request('SYNO.Core.System', 'info', version=1)
            if info_resp.get('success'):
                d = info_resp.get('data', {})
                uptime_sec = int(d.get('uptime', 0))
                metrics['uptime_days'] = uptime_sec // 86400
                
                # Temperatura
                if 'thermal' in d and isinstance(d['thermal'], list) and len(d['thermal']) > 0:
                    metrics['temperature'] = d['thermal'][0].get('temperature', 0)
            
        except Exception as e:
            logger.error(f"Error fetching system metrics: {e}")
            
        return metrics

    def _format_speed(self, b):
        """Formatea bytes/s a formato legible"""
        if b < 1024: return f"{b} B/s"
        if b < 1024 * 1024: return f"{b/1024:.1f} KB/s"
        return f"{b/(1024*1024):.1f} MB/s"

    def _get_health_status(self):
        """
        Obtiene el estado de salud global vía SYNO.Core.System.SystemHealth
        """
        try:
            resp = self.connection.request('SYNO.Core.System.SystemHealth', 'get', version=1)
            if resp.get('success'):
                # status suele ser 'health-ok' o similar
                status = resp.get('data', {}).get('status', 'unknown')
                return {
                    'status': status,
                    'is_ok': status == 'health-ok'
                }
        except Exception as e:
            logger.error(f"Error fetching health status: {e}")
        return {'status': 'Error', 'is_ok': False}

    def _get_active_connections(self):
        """
        Obtiene número de conexiones activas vía SYNO.Core.CurrentConnection
        """
        try:
            resp = self.connection.request('SYNO.Core.CurrentConnection', 'list', version=1)
            if resp.get('success'):
                connections = resp.get('data', {}).get('items', [])
                return {
                    'total': len(connections),
                    'items': connections[:5] # Top 5
                }
        except Exception as e:
            logger.error(f"Error fetching active connections: {e}")
        return {'total': 0}

    def _get_recent_activity(self, limit=10):
        """
        Obtiene logs recientes del sistema vía SYNO.Core.SyslogClient.Log
        """
        try:
            # Intentamos obtener logs generales del sistema
            # SYNO.Core.SyslogClient.Log method=list es standard
            resp = self.connection.request(
                api='SYNO.Core.SyslogClient.Log', 
                method='list', 
                version=1,
                params={
                    'limit': limit,
                    'offset': 0,
                    'log_type': 'system' # general system logs
                }
            )
            
            if resp.get('success'):
                logs = resp.get('data', {}).get('items', [])
                formatted_logs = []
                for log in logs:
                    # El formato de log de Synology varía según versión, 
                    # usualmente trae: time, user, level, ldata (msg)
                    formatted_logs.append({
                        'time': log.get('time', 'N/A'),
                        'user': log.get('user', 'system'),
                        'level': log.get('level', 'info').lower(), # info, warn, err
                        'msg': log.get('ldata', log.get('msg', 'Sin descripción'))
                    })
                return formatted_logs
                
        except Exception as e:
            logger.error(f"Error fetching recent activity logs: {e}")
            
        return []

    def _get_recent_files(self, limit=5):
        """
        Obtiene archivos recientes vía SYNO.FileStation.List
        Nota: Esta API requiere un folder_path. Para el dashboard global, 
        podríamos iterar sobre shares principales o usar SYNO.FileStation.Search (más lento).
        Estrategia: Listar el contenido de '/' (shares) y traer los más recientes.
        """
        try:
            # Primero listamos los shares
            resp = self.connection.request(
                api='SYNO.FileStation.List',
                method='list_share',
                version=2,
                params={'additional': json.dumps(['time', 'size'])}
            )
            
            if resp.get('success'):
                shares = resp.get('data', {}).get('shares', [])
                # Para simplificar y no hacer N peticiones, mostramos los shares como "directorios recientes"
                # o si quisiéramos archivos reales, tendríamos que entrar en cada uno.
                # Como compromiso: mostramos los últimos 5 archivos de la carpeta compartida principal o home.
                
                # Intentamos listar el primer share disponible como ejemplo de "Archivos recientes"
                if shares:
                    main_share = shares[0].get('path')
                    f_resp = self.connection.request(
                        api='SYNO.FileStation.List',
                        method='list',
                        version=2,
                        params={
                            'folder_path': main_share,
                            'limit': limit,
                            'sort_by': 'mtime',
                            'sort_direction': 'desc',
                            'additional': json.dumps(['time', 'size'])
                        }
                    )
                    
                    if f_resp.get('success'):
                        files = f_resp.get('data', {}).get('files', [])
                        formatted_files = []
                        for f in files:
                            name = f.get('name')
                            ext = name.split('.')[-1].lower() if '.' in name else 'folder'
                            formatted_files.append({
                                'name': name,
                                'path': f.get('path'),
                                'size': self._format_bytes(f.get('additional', {}).get('size', 0)),
                                'time': f.get('additional', {}).get('time', {}).get('mtime', 'N/A'),
                                'ext': ext
                            })
                        return formatted_files
                        
        except Exception as e:
            logger.error(f"Error fetching recent files: {e}")
            
        return []

    def _format_bytes(self, size):
        # Helper simple
        if not isinstance(size, (int, float)):
            try:
                size = int(size)
            except:
                return "0 B"
        
        power = 1024
        n = 0
        power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T', 5: 'P'}
        while size >= power and n < 5:
            size /= power
            n += 1
        return f"{size:.1f} {power_labels.get(n, '')}B"
