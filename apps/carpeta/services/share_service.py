import logging
import json
import os
from django.conf import settings
from apps.settings.services.connection_service import ConnectionService
from apps.settings.models import NASConfig

logger = logging.getLogger(__name__)

class ShareService:
    """
    Servicio de orquestación para Carpetas Compartidas Synology.
    Soporta modo offline y sesiones administrativas DSM.
    """
    
    def __init__(self, session_alias='FileStation'):
        self.config = NASConfig.get_active_config()
        self.connection = ConnectionService(self.config)
        if not getattr(settings, 'NAS_OFFLINE_MODE', False):
            self.connection.authenticate(session_alias=session_alias)
        
        # Simulación offline
        self.sim_db_path = os.path.join(settings.BASE_DIR, 'nas_sim_shares.json')
        self._ensure_sim_file()

    def _ensure_sim_file(self):
        if not os.path.exists(self.sim_db_path):
            default_data = [
                {
                    'name': 'video', 'desc': 'Películas y series', 
                    'vol_path': '/volume1', 'recyclebin': True, 'encryption': 0
                },
                {
                    'name': 'music', 'desc': 'Biblioteca musical', 
                    'vol_path': '/volume1', 'recyclebin': True, 'encryption': 0
                }
            ]
            self._save_sim_data(default_data)

    def _get_sim_data(self):
        try:
            with open(self.sim_db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return []

    def _save_sim_data(self, data):
        with open(self.sim_db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def list_shares(self, limit=50, offset=0):
        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            return self._get_sim_data()
            
        try:
            response = self.connection.request(
                api='SYNO.Core.Share',
                method='list',
                version=1,
                params={
                    'limit': limit,
                    'offset': offset,
                    'additional': json.dumps([
                        "vol_path", "mount_point_type", "encryption", "recyclebin", 
                        "desc", "enable_share_compress", "enable_share_cow"
                    ])
                }
            )
            return response.get('data', {}).get('shares', []) if response.get('success') else []
        except Exception:
            logger.exception("Error listing shares")
            return []

    def get_share(self, name):
        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            shares = self._get_sim_data()
            raw_share = next((s for s in shares if s['name'] == name), None)
            return self._normalize_share_for_wizard(raw_share) if raw_share else None

        try:
            response = self.connection.request(
                api='SYNO.Core.Share',
                method='get',
                version=1,
                params={
                    'name': name, 
                    'additional': json.dumps([
                        "vol_path", "encryption", "recyclebin", "desc", 
                        "quota_value", "enable_share_compress", "enable_share_cow",
                        "browseable", "hide_unreadable", "adv_recycle_bin_admin_only"
                    ])
                }
            )
            if response.get('success') and response.get('data', {}).get('shares'):
                return self._normalize_share_for_wizard(response['data']['shares'][0])
        except Exception:
            logger.exception(f"Error getting share {name}")
        return None

    def _normalize_share_for_wizard(self, raw_share):
        return {
            'info': {
                'name': raw_share.get('name', ''),
                'description': raw_share.get('desc', '') or raw_share.get('description', ''),
                'volume': raw_share.get('vol_path', '/volume1'),
                'recyclebin': raw_share.get('recyclebin', False),
                'hide_network': not raw_share.get('browseable', True),
                'hide_subfolders': raw_share.get('hide_unreadable', False),
                'admin_only': raw_share.get('adv_recycle_bin_admin_only', False)
            },
            'security': {
                'encrypted': raw_share.get('encryption', 0) == 1,
                'password': '', 'password_confirm': ''
            },
            'advanced': {
                'checksum': raw_share.get('enable_share_cow', False),
                'compression': raw_share.get('enable_share_compress', False),
                'quota_enabled': raw_share.get('quota_value', 0) > 0,
                'quota_size': raw_share.get('quota_value', 0),
                'quota_unit': 'MB'
            }
        }

    def delete_share(self, name):
        return self.delete_shares([name])

    def delete_shares(self, names):
        """Elimina una lista de carpetas compartidas."""
        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            shares = self._get_sim_data()
            new_shares = [s for s in shares if s['name'] not in names]
            self._save_sim_data(new_shares)
            return {'success': True, 'count': len(names)}

        admin_conn = ConnectionService(self.config)
        auth = admin_conn.authenticate(session_alias='DSM')
        if not auth.get('success'): return auth
        
        results = []
        try:
            for name in names:
                resp = admin_conn.request(
                    api='SYNO.Core.Share', method='delete', version=1, 
                    params={'name': name}
                )
                results.append(resp.get('success', False))
            
            success = all(results)
            return {
                'success': success, 
                'message': 'Todas las carpetas eliminadas' if success else 'Algunas carpetas no pudieron eliminarse',
                'count': results.count(True)
            }
        finally:
            admin_conn.logout(auth.get('sid'), session_alias='DSM')

    def create_share_wizard(self, data):
        return self._save_share_wizard(data, mode='create')

    def update_share_wizard(self, name, data):
        return self._save_share_wizard(data, mode='edit', name=name)

    def _save_share_wizard(self, data, mode='create', name=None):
        info = data.get('info', {})
        advanced = data.get('advanced', {})
        security = data.get('security', {})
        target_name = name or info.get('name')
        
        # Conversión de Cuota a MB
        quota_mb = 0
        if advanced.get('quota_enabled'):
            try:
                size = float(advanced.get('quota_size', 0))
                unit = advanced.get('quota_unit', 'MB')
                if unit == 'GB': size *= 1024
                elif unit == 'TB': size *= 1024 * 1024
                quota_mb = int(size)
            except (ValueError, TypeError): quota_mb = 0

        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            shares = self._get_sim_data()
            if mode == 'create':
                shares.append({
                    'name': target_name, 
                    'desc': info.get('description', ''),
                    'vol_path': info.get('volume', '/volume1'),
                    'recyclebin': info.get('recyclebin', False),
                    'encryption': 1 if security.get('encrypted') else 0,
                    'quota_value': quota_mb,
                    'enable_share_compress': advanced.get('compression', False),
                    'enable_share_cow': advanced.get('checksum', False),
                    'browseable': not info.get('hide_network', False),
                    'hide_unreadable': info.get('hide_subfolders', False),
                    'adv_recycle_bin_admin_only': info.get('admin_only', False)
                })
            else:
                for s in shares:
                    if s['name'] == target_name:
                        s['desc'] = info.get('description', s.get('desc'))
                        s['recyclebin'] = info.get('recyclebin', s.get('recyclebin'))
                        s['quota_value'] = quota_mb
                        s['enable_share_compress'] = advanced.get('compression', s.get('enable_share_compress'))
                        s['enable_share_cow'] = advanced.get('checksum', s.get('enable_share_cow'))
                        s['browseable'] = not info.get('hide_network', not s.get('browseable', True))
                        s['hide_unreadable'] = info.get('hide_subfolders', s.get('hide_unreadable', False))
                        s['adv_recycle_bin_admin_only'] = info.get('admin_only', s.get('adv_recycle_bin_admin_only', False))
                        break
            self._save_sim_data(shares)
            return {'success': True}

        admin_conn = ConnectionService(self.config)
        auth = admin_conn.authenticate(session_alias='DSM')
        if not auth.get('success'): return auth

        try:
            params = {
                'name': target_name,
                'desc': info.get('description', ''),
                'enable_recycle_bin': json.dumps(info.get('recyclebin', False)),
                'browseable': json.dumps(not info.get('hide_network', False)),
                'hide_unreadable': json.dumps(info.get('hide_subfolders', False)),
                'adv_recycle_bin_admin_only': json.dumps(info.get('admin_only', False))
            }

            if mode == 'create':
                params.update({
                    'vol_path': info.get('volume', '/volume1'),
                    'enable_share_compress': json.dumps(advanced.get('compression', False)),
                    'enable_share_cow': json.dumps(advanced.get('checksum', False))
                })
                if security.get('encrypted'):
                    params.update({'encryption': 1, 'key': security.get('password', '')})
            
            method = 'create' if mode == 'create' else 'set'
            resp = admin_conn.request('SYNO.Core.Share', method, version=1, params=params)
            
            # Aplicar Cuota
            if resp.get('success'):
                quota_params = {'name': target_name, 'quota_value': quota_mb}
                admin_conn.request('SYNO.Core.Share', 'set', version=1, params=quota_params)
            
            return resp
        finally:
            admin_conn.logout(auth.get('sid'), session_alias='DSM')

    def get_wizard_options(self):
        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            return {'volumes': ['/volume1', '/volume2']}
        try:
            v_resp = self.connection.request('SYNO.Core.Storage.Volume', 'list', version=1)
            return {'volumes': [v['path'] for v in v_resp['data']['volumes']]} if v_resp.get('success') else {'volumes': ['/volume1']}
        except: return {'volumes': ['/volume1']}
