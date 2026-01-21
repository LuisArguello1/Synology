from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock
from apps.groups.services.group_service import GroupService

class GroupServiceTest(TestCase):

    @override_settings(NAS_OFFLINE_MODE=True)
    def test_list_groups_offline(self):
        """Test listing groups in offline mode (mock data)."""
        service = GroupService()
        # Mock _get_sim_data to return a fixed list
        with patch.object(service, '_get_sim_data') as mock_data:
            mock_data.return_value = [{'name': 'test_group', 'description': 'desc'}]
            
            groups = service.list_groups()
            self.assertEqual(len(groups), 1)
            self.assertEqual(groups[0]['name'], 'test_group')

    @override_settings(NAS_OFFLINE_MODE=True)
    def test_create_group_offline(self):
        """Test creating a group in offline mode."""
        service = GroupService()
        
        # Starts with empty list
        with patch.object(service, '_get_sim_data', return_value=[]), \
             patch.object(service, '_save_sim_data') as mock_save:
            
            result = service.create_group({'name': 'new_group', 'description': 'new desc'})
            
            self.assertTrue(result['success'])
            mock_save.assert_called_once()
            # Verify the data passed to save includes the new group
            saved_data = mock_save.call_args[0][0]
            self.assertEqual(len(saved_data), 1)
            self.assertEqual(saved_data[0]['name'], 'new_group')

    @override_settings(NAS_OFFLINE_MODE=False)
    @patch('apps.groups.services.group_service.ConnectionService')
    def test_list_groups_online(self, MockConnection):
        """Test listing groups in online mode (mocking ConnectionService)."""
        # Setup mock connection
        mock_conn = MockConnection.return_value
        mock_conn.request.return_value = {
            'success': True, 
            'data': {'groups': [{'name': 'nas_group', 'desc': 'from nas'}]}
        }
        
        service = GroupService()
        groups = service.list_groups()
        
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['name'], 'nas_group')
        # Check that we called the correct API
        mock_conn.request.assert_called_with(
            api='SYNO.Core.Group', 
            method='list', 
            version=1, 
            params={'additional': '["members"]'}
        )

    @override_settings(NAS_OFFLINE_MODE=False)
    @patch('apps.groups.services.group_service.ConnectionService')
    def test_create_group_online(self, MockConnectionService):
        """Test creating group in online mode with DSM session verification."""
        # 1. Configurar el mock para la instancia (self.connection y admin_conn)
        mock_instance = MockConnectionService.return_value
        # Todas las llamadas a request devuelven éxito por defecto
        mock_instance.request.return_value = {'success': True}
        # authenticate devuelve un diccionario con sid o el mismo mock
        mock_instance.authenticate.return_value = {'success': True, 'sid': 'test_sid'}
        
        service = GroupService()
        result = service.create_group({
            'name': 'nas_created_group', 
            'description': 'online',
            'members': ['user1']
        })
        
        self.assertTrue(result['success'])
        # Verificar que se intentó autenticar con DSM
        mock_instance.authenticate.assert_any_call(session_alias='DSM')
        # Verificar que se cerró la sesión DSM
        mock_instance.logout.assert_called_with('test_sid', session_alias='DSM')

    def test_delete_group_offline(self):
        """Test deleting a group in offline mode."""
        service = GroupService()
        # Crear grupo para borrar
        service.create_group({'name': 'to_delete', 'description': 'bye'})
        
        result = service.delete_group('to_delete')
        self.assertTrue(result['success'])
        
        # Verificar que no está
        groups = service.list_groups()
        self.assertNotIn('to_delete', [g['name'] for g in groups])

    @override_settings(NAS_OFFLINE_MODE=False)
    @patch('apps.groups.services.group_service.ConnectionService')
    def test_delete_group_online(self, MockConnectionService):
        """Test deleting group in online mode with DSM session."""
        mock_instance = MockConnectionService.return_value
        mock_instance.request.return_value = {'success': True}
        mock_instance.authenticate.return_value = {'success': True, 'sid': 'test_sid'}
        
        # Simular que el grupo existe y NO es de sistema
        with patch.object(GroupService, 'get_group') as mock_get:
            mock_get.return_value = {'name': 'existing_group', 'is_system': False}
            
            service = GroupService()
            result = service.delete_group('existing_group')
            
            self.assertTrue(result['success'])
            mock_instance.authenticate.assert_called_with(session_alias='DSM')
            mock_instance.logout.assert_called_with('test_sid', session_alias='DSM')

    def test_update_wizard_offline(self):
        """Test update wizard logic in offline mode."""
        service = GroupService()
        service.create_group({'name': 'wizard_test', 'description': 'old'})
        
        update_data = {
            'info': {'description': 'new desc'},
            'members': ['admin']
        }
        
        # Corregido: update_group_wizard ahora recibe (name, data)
        result = service.update_group_wizard('wizard_test', update_data)
        self.assertTrue(result['success'])
        
        group = service.get_group('wizard_test')
        self.assertEqual(group['description'], 'new desc')

    @override_settings(NAS_OFFLINE_MODE=False)
    @patch('apps.groups.services.group_service.ConnectionService')
    def test_sync_members_fallback(self, MockConnectionService):
        """Verify _sync_group_members próbility/fallback."""
        mock_instance = MockConnectionService.return_value
        # Simular que 'set' falla pero 'add' funciona
        mock_instance.request.side_effect = [
            {'success': False, 'error': {'code': 101}},
            {'success': True}
        ]
        
        service = GroupService()
        success = service._sync_group_members(mock_instance, 'test_group', ['user1'])
        self.assertTrue(success)
        self.assertGreaterEqual(mock_instance.request.call_count, 2)
