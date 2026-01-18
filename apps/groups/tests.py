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
    def test_create_group_online(self, MockConnection):
        """Test creating group in online mode."""
        mock_conn = MockConnection.return_value
        mock_conn.request.return_value = {'success': True}
        
        service = GroupService()
        result = service.create_group({'name': 'nas_created_group', 'description': 'online'})
        
        self.assertTrue(result['success'])
        mock_conn.request.assert_called_with(
            'SYNO.Core.Group', 'create', version=1, 
            params={'name': 'nas_created_group', 'description': 'online'}
        )
