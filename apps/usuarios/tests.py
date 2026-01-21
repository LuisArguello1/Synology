import time
import logging
import json
from django.conf import settings
from django.test import TestCase
from apps.usuarios.services.user_service import UserService

logger = logging.getLogger(__name__)

class UserServicePerformanceTest(TestCase):
    """
    Test de rendimiento y funcionalidad para UserService.
    Mide tiempos de respuesta de la API del NAS y valida integridad de datos.
    """

    def setUp(self):
        # Asegurar que existe una configuración para evitar ValueError
        from apps.settings.models import NASConfig
        from django.conf import settings
        
        # Desactivar modo offline para tests reales
        setattr(settings, 'NAS_OFFLINE_MODE', False)
        
        # Poblamos la base de datos de test con la configuración real del NAS
        if not NASConfig.get_active_config():
            NASConfig.objects.create(
                host='10.2.0.48',
                port=5001,
                protocol='https',
                admin_username='FACI',
                admin_password='Passw0rd2021',
                is_active=True
            )
            
        self.user_service = UserService()
        print("\n" + "="*50)
        print("INICIANDO TEST DE RENDIMIENTO: USER SERVICE")
        print("="*50)

    def test_list_users_performance(self):
        """Mide tiempo de listado de usuarios y valida estructura."""
        start_time = time.time()
        users = self.user_service.list_users()
        end_time = time.time()
        
        duration_ms = (end_time - start_time) * 1000
        print(f"DEBUG: list_users() duration: {duration_ms:.2f} ms")
        
        # Validaciones funcionales
        self.assertIsInstance(users, list, "El resultado debe ser una lista")
        if users:
            u = users[0]
            self.assertIn('name', u, "El usuario debe tener el campo 'name'")
        
        print(f"✅ [FUNC] list_users(): Validación exitosa. Total usuarios: {len(users)}")

    def test_get_wizard_options_performance(self):
        """Mide tiempo de carga de opciones del wizard y valida campos críticos."""
        start_time = time.time()
        options = self.user_service.get_wizard_options()
        end_time = time.time()
        
        duration_ms = (end_time - start_time) * 1000
        print(f"DEBUG: get_wizard_options() duration: {duration_ms:.2f} ms")
        
        # Validaciones funcionales
        self.assertIsInstance(options, dict, "Opciones debe ser un diccionario")
        self.assertIn('groups', options, "Falta clave 'groups'")
        self.assertIn('shares', options, "Falta clave 'shares'")
        self.assertIn('group_permissions', options, "Falta clave 'group_permissions'")
        
        print(f"DONE: get_wizard_options(): Estructura de datos completa.")

    def test_admin_session_latency(self):
        """Mide latencia de creación de sesión administrativa (DSM)."""
        from apps.settings.services.connection_service import ConnectionService
        
        start_time = time.time()
        admin_conn = ConnectionService(self.user_service.config)
        auth_result = admin_conn.authenticate(session_alias='DSM')
        end_time = time.time()
        
        duration_ms = (end_time - start_time) * 1000
        print(f"DEBUG: Authenticate (DSM) duration: {duration_ms:.2f} ms")
        
        if auth_result.get('success'):
            print(f"DONE: Authenticate (DSM): Conexión exitosa.")
            # Cerrar sesión para no saturar
            admin_conn.logout(auth_result['sid'], session_alias='DSM')
        else:
            print(f"WARN: Authenticate (DSM): Falló ({auth_result.get('message', 'Error desconocido')})")

    def test_user_crud_lifecycle(self):
        """
        Prueba el ciclo de vida completo de un usuario:
        Creación -> Verificación -> Modificación -> Eliminación
        """
        if getattr(settings, 'NAS_OFFLINE_MODE', False):
            self.skipTest("Saltando test CRUD real en modo OFFLINE")

        test_username = "test_user_antigravity"
        test_password = "Password123!"
        
        print(f"\nSTART: Iniciando Ciclo CRUD para: {test_username}")

        # 1. ELIMINAR PREVIAMENTE (por si acaso quedó de un test fallido)
        # No verificamos éxito aquí porque puede que no exista
        self.user_service.delete_user([test_username])

        # 2. CREAR USUARIO
        create_data = {
            'info': {
                'name': test_username,
                'password': test_password,
                'email': 'test@example.com',
                'description': 'Usuario de prueba automatizada',
                'cannot_change_password': False
            },
            'groups': ['users'],
            'permissions': {},
            'quota': {},
            'apps': {},
            'speed': {}
        }
        
        print("Creating user...")
        create_res = self.user_service.create_user_wizard(create_data)
        self.assertTrue(create_res['success'], f"Error al crear usuario: {create_res.get('message')}")
        print("DONE: Usuario creado")

        # 3. VERIFICAR EXISTENCIA
        print("Verifying user...")
        user = self.user_service.get_user(test_username)
        self.assertIsNotNone(user, "El usuario creado no fue encontrado en el NAS")
        self.assertEqual(user.get('name'), test_username)
        print("DONE: Usuario verificado")

        # 4. ACTUALIZAR USUARIO
        print("Updating user...")
        update_data = create_data.copy()
        update_data['mode'] = 'edit'
        update_data['info']['description'] = 'Descripción ACTUALIZADA'
        
        update_res = self.user_service.update_user_wizard(update_data)
        self.assertTrue(update_res['success'], f"Error al actualizar usuario: {update_res.get('message')}")
        
        # Verificar cambio
        updated_user = self.user_service.get_user(test_username)
        self.assertEqual(updated_user.get('description'), 'Descripción ACTUALIZADA')
        print("DONE: Usuario actualizado")

        # 5. ELIMINAR USUARIO
        print("Deleting user...")
        delete_res = self.user_service.delete_user([test_username])
        self.assertTrue(delete_res.get('success'), f"Error al eliminar usuario: {delete_res}")
        
        # Verificar eliminación
        final_user = self.user_service.get_user(test_username)
        self.assertIsNone(final_user, "El usuario aún existe después de intentar eliminarlo")
        print("DONE: Usuario eliminado exitosamente")

    def tearDown(self):
        print("="*50 + "\n")
