"""
Servicio para gestionar los servicios de archivos del NAS Synology.
Maneja SMB, AFP, NFS, FTP, rsync y configuraciones avanzadas.
"""
import logging
from django.conf import settings
from apps.settings.services.connection_service import ConnectionService
from apps.settings.models import NASConfig

logger = logging.getLogger(__name__)


class FileServicesService:
    """
    Servicio para gestionar configuración de servicios de archivos en Synology NAS.
    Interactúa con las APIs correspondientes.
    """
    
    def __init__(self):
        self.config = NASConfig.get_active_config()
        self.offline_mode = getattr(settings, 'NAS_OFFLINE_MODE', False)
        if not self.offline_mode and self.config:
            self.connection = ConnectionService(self.config)
        else:
            self.connection = None
    
    # =============================================================================
    # SMB SERVICE
    # =============================================================================
    
    def get_smb_config(self):
        """
        Obtiene la configuración actual del servicio SMB.
        API: SYNO.Core.FileServ.SMB
        """
        if self.offline_mode:
            return {
                'success': True,
                'data': {
                    'enable': True,
                    'workgroup': 'WORKGROUP',
                    'hide_dotfiles': False,
                    'hide_unreadable': True,
                    'transfer_log': True,
                    'enable_recycle_bin': True,
                    'enable_aggregation': False,
                    'enable_wsdiscovery': True
                }
            }
        
        try:
            result = self.connection.request(
                api='SYNO.Core.FileServ.SMB',
                method='get',
                version=2
            )
            return {'success': True, 'data': result.get('data', {})}
        except Exception as e:
            logger.error(f"Error obteniendo config SMB: {e}")
            return {'success': False, 'message': str(e)}
    
    def set_smb_config(self, data):
        """
        Actualiza la configuración del servicio SMB.
        """
        if self.offline_mode:
            logger.info(f"[OFFLINE] Guardando configuración SMB: {data}")
            return {'success': True, 'message': 'Configuración SMB actualizada (modo offline)'}
        
        try:
            result = self.connection.request(
                api='SYNO.Core.FileServ.SMB',
                method='set',
                version=2,
                params=data
            )
            return {'success': True, 'message': 'Configuración SMB actualizada correctamente'}
        except Exception as e:
            logger.error(f"Error actualizando config SMB: {e}")
            return {'success': False, 'message': str(e)}
    
    # =============================================================================
    # AFP SERVICE
    # =============================================================================
    
    def get_afp_config(self):
        """
        Obtiene la configuración actual del servicio AFP.
        API: SYNO.Core.FileServ.AFP
        """
        if self.offline_mode:
            return {
                'success': True,
                'data': {
                    'enable': True,
                    'transfer_log': True,
                    'enable_bonjour': True,
                    'enable_timemachine': False
                }
            }
        
        try:
            result = self.connection.request(
                api='SYNO.Core.FileServ.AFP',
                method='get',
                version=2
            )
            return {'success': True, 'data': result.get('data', {})}
        except Exception as e:
            logger.error(f"Error obteniendo config AFP: {e}")
            return {'success': False, 'message': str(e)}
    
    def set_afp_config(self, data):
        """
        Actualiza la configuración del servicio AFP.
        """
        if self.offline_mode:
            logger.info(f"[OFFLINE] Guardando configuración AFP: {data}")
            return {'success': True, 'message': 'Configuración AFP actualizada (modo offline)'}
        
        try:
            result = self.connection.request(
                api='SYNO.Core.FileServ.AFP',
                method='set',
                version=2,
                params=data
            )
            return {'success': True, 'message': 'Configuración AFP actualizada correctamente'}
        except Exception as e:
            logger.error(f"Error actualizando config AFP: {e}")
            return {'success': False, 'message': str(e)}
    
    # =============================================================================
    # NFS SERVICE
    # =============================================================================
    
    def get_nfs_config(self):
        """
        Obtiene la configuración actual del servicio NFS.
        API: SYNO.Core.FileServ.NFS
        """
        if self.offline_mode:
            return {
                'success': True,
                'data': {
                    'enable': True,
                    'nfsv3': True,
                    'nfsv4': False,
                    'nfsv41': False
                }
            }
        
        try:
            result = self.connection.request(
                api='SYNO.Core.FileServ.NFS',
                method='get',
                version=2
            )
            return {'success': True, 'data': result.get('data', {})}
        except Exception as e:
            logger.error(f"Error obteniendo config NFS: {e}")
            return {'success': False, 'message': str(e)}
    
    def set_nfs_config(self, data):
        """
        Actualiza la configuración del servicio NFS.
        """
        if self.offline_mode:
            logger.info(f"[OFFLINE] Guardando configuración NFS: {data}")
            return {'success': True, 'message': 'Configuración NFS actualizada (modo offline)'}
        
        try:
            result = self.connection.request(
                api='SYNO.Core.FileServ.NFS',
                method='set',
                version=2,
                params=data
            )
            return {'success': True, 'message': 'Configuración NFS actualizada correctamente'}
        except Exception as e:
            logger.error(f"Error actualizando config NFS: {e}")
            return {'success': False, 'message': str(e)}
    
    # =============================================================================
    # FTP SERVICE
    # =============================================================================
    
    def get_ftp_config(self):
        """
        Obtiene la configuración actual de los servicios FTP/FTPS/SFTP.
        API: SYNO.Core.FileServ.FTP
        """
        if self.offline_mode:
            return {
                'success': True,
                'data': {
                    'enable_ftp': True,
                    'enable_ftps': False,
                    'enable_sftp': False,
                    'port': 21,
                    'timeout': 300,
                    'pasv_min_port': 55536,
                    'pasv_max_port': 55567,
                    'enable_fxp': False,
                    'enable_ascii': False,
                    'utf8_encoding': 'auto',
                    'time_format': 'utc'
                }
            }
        
        try:
            result = self.connection.request(
                api='SYNO.Core.FileServ.FTP',
                method='get',
                version=3
            )
            return {'success': True, 'data': result.get('data', {})}
        except Exception as e:
            logger.error(f"Error obteniendo config FTP: {e}")
            return {'success': False, 'message': str(e)}
    
    def set_ftp_config(self, data):
        """
        Actualiza la configuración de FTP/FTPS/SFTP.
        """
        if self.offline_mode:
            logger.info(f"[OFFLINE] Guardando configuración FTP: {data}")
            return {'success': True, 'message': 'Configuración FTP actualizada (modo offline)'}
        
        try:
            result = self.connection.request(
                api='SYNO.Core.FileServ.FTP',
                method='set',
                version=3,
                params=data
            )
            return {'success': True, 'message': 'Configuración FTP actualizada correctamente'}
        except Exception as e:
            logger.error(f"Error actualizando config FTP: {e}")
            return {'success': False, 'message': str(e)}
    
    # =============================================================================
    # RSYNC SERVICE
    # =============================================================================
    
    def get_rsync_config(self):
        """
        Obtiene la configuración actual del servicio rsync.
        API: SYNO.Core.FileServ.Rsync
        """
        if self.offline_mode:
            return {
                'success': True,
                'data': {
                    'enable': True,
                    'ssh_port': 22,
                    'enable_rsync_account': False,
                    'speed_limit_enabled': False,
                    'speed_limit': 0
                }
            }
        
        try:
            result = self.connection.request(
                api='SYNO.Core.FileServ.Rsync',
                method='get',
                version=1
            )
            return {'success': True, 'data': result.get('data', {})}
        except Exception as e:
            logger.error(f"Error obteniendo config rsync: {e}")
            return {'success': False, 'message': str(e)}
    
    def set_rsync_config(self, data):
        """
        Actualiza la configuración del servicio rsync.
        """
        if self.offline_mode:
            logger.info(f"[OFFLINE] Guardando configuración rsync: {data}")
            return {'success': True, 'message': 'Configuración rsync actualizada (modo offline)'}
        
        try:
            result = self.connection.request(
                api='SYNO.Core.FileServ.Rsync',
                method='set',
                version=1,
                params=data
            )
            return {'success': True, 'message': 'Configuración rsync actualizada correctamente'}
        except Exception as e:
            logger.error(f"Error actualizando config rsync: {e}")
            return {'success': False, 'message': str(e)}
    
    # =============================================================================
    # ADVANCED SETTINGS
    # =============================================================================
    
    def get_advanced_config(self):
        """
        Obtiene configuraciones avanzadas (Bonjour, SSDP, TFTP, etc).
        """
        if self.offline_mode:
            return {
                'success': True,
                'data': {
                    'enable_fast_clone': False,
                    'enable_bonjour': True,
                    'enable_bonjour_printer': False,
                    'enable_bonjour_timemachine_smb': False,
                    'enable_bonjour_timemachine_afp': False,
                    'enable_ssdp': True,
                    'enable_tftp': False,
                    'tftp_root': '',
                    'enable_traversal_check': False
                }
            }
        
        try:
            result = self.connection.request(
                api='SYNO.Core.FileServ.Advanced',
                method='get',
                version=1
            )
            return {'success': True, 'data': result.get('data', {})}
        except Exception as e:
            logger.error(f"Error obteniendo config avanzada: {e}")
            return {'success': False, 'message': str(e)}
    
    def set_advanced_config(self, data):
        """
        Actualiza configuraciones avanzadas.
        """
        if self.offline_mode:
            logger.info(f"[OFFLINE] Guardando configuración avanzada: {data}")
            return {'success': True, 'message': 'Configuración avanzada actualizada (modo offline)'}
        
        try:
            result = self.connection.request(
                api='SYNO.Core.FileServ.Advanced',
                method='set',
                version=1,
                params=data
            )
            return {'success': True, 'message': 'Configuración avanzada actualizada correctamente'}
        except Exception as e:
            logger.error(f"Error actualizando config avanzada: {e}")
            return {'success': False, 'message': str(e)}
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def get_all_configs(self):
        """
        Obtiene todas las configuraciones de servicios de archivos en una sola llamada.
        """
        return {
            'smb': self.get_smb_config(),
            'afp': self.get_afp_config(),
            'nfs': self.get_nfs_config(),
            'ftp': self.get_ftp_config(),
            'rsync': self.get_rsync_config(),
            'advanced': self.get_advanced_config()
        }
