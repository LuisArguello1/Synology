from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock
from apps.carpeta.services.share_service import ShareService

class ShareServiceTest(TestCase):

    @override_settings(NAS_OFFLINE_MODE=True)
    def test_list_shares_offline(self):
        service = ShareService()
        shares = service.list_shares()
        self.assertGreater(len(shares), 0)
        self.assertEqual(shares[0]['name'], 'video')

    @override_settings(NAS_OFFLINE_MODE=True)
    def test_create_share_offline(self):
        service = ShareService()
        new_share_data = {
            'info': {'name': 'test_share', 'description': 'desc', 'volume': '/volume1'}
        }
        result = service.create_share_wizard(new_share_data)
        self.assertTrue(result['success'])
        
        shares = service.list_shares()
        self.assertIn('test_share', [s['name'] for s in shares])

    @override_settings(NAS_OFFLINE_MODE=False)
    @patch('apps.carpeta.services.share_service.ConnectionService')
    def test_create_share_online_dsm(self, MockConn):
        mock_instance = MockConn.return_value
        mock_instance.authenticate.return_value = {'success': True, 'sid': 'dsm_sid'}
        mock_instance.request.return_value = {'success': True}
        
        service = ShareService()
        result = service.create_share_wizard({
            'info': {'name': 'nas_share', 'volume': '/volume1'}
        })
        
        self.assertTrue(result['success'])
        # Verificar que se usó DSM
        MockConn.return_value.authenticate.assert_called_with(session_alias='DSM')
        # Verificar logout
        MockConn.return_value.logout.assert_called_with('dsm_sid', session_alias='DSM')

    @override_settings(NAS_OFFLINE_MODE=False)
    @patch('apps.carpeta.services.share_service.ConnectionService')
    def test_delete_share_online(self, MockConn):
        mock_instance = MockConn.return_value
        mock_instance.authenticate.return_value = {'success': True, 'sid': 'dsm_sid'}
        mock_instance.request.return_value = {'success': True}
        
        service = ShareService()
        result = service.delete_share('to_delete')
        
        self.assertTrue(result['success'])
        MockConn.return_value.request.assert_called_with(
            api='SYNO.Core.Share', method='delete', version=1, params={'name': 'to_delete'}
        )

    @override_settings(NAS_OFFLINE_MODE=False)
    @patch('apps.carpeta.services.share_service.ConnectionService')
    def test_update_share_online_with_quota(self, MockConn):
        mock_instance = MockConn.return_value
        mock_instance.authenticate.return_value = {'success': True, 'sid': 'dsm_sid'}
        mock_instance.request.return_value = {'success': True}
        
        service = ShareService()
        result = service.update_share_wizard('existing_share', {
            'info': {'description': 'updated', 'recyclebin': True, 'hide_network': True},
            'advanced': {
                'quota_enabled': True,
                'quota_size': 2,
                'quota_unit': 'GB'
            }
        })
        
        self.assertTrue(result['success'])
        
        # Verificar parámetros de visibilidad
        # Importante: Los primeros 3 argumentos son posicionales en el servicio
        mock_instance.request.assert_any_call(
            'SYNO.Core.Share', 'set', version=1, 
            params={
                'name': 'existing_share',
                'desc': 'updated',
                'enable_recycle_bin': 'true',
                'browseable': 'false',
                'hide_unreadable': 'false',
                'adv_recycle_bin_admin_only': 'false'
            }
        )
        
        # Verificar conversión de cuota (2GB = 2048MB)
        mock_instance.request.assert_any_call(
            'SYNO.Core.Share', 'set', version=1, 
            params={'name': 'existing_share', 'quota_value': 2048}
        )
