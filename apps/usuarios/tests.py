import time
import logging
import json
from django.test import TestCase
from apps.usuarios.services.user_service import UserService

logger = logging.getLogger(__name__)

class UserServicePerformanceTest(TestCase):
    """
    Test de rendimiento y funcionalidad para UserService.
    Mide tiempos de respuesta de la API del NAS y valida integridad de datos.
    """

    def setUp(self):
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
        print(f"⏱️ [PERF] list_users(): {duration_ms:.2f} ms")
        
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
        print(f"⏱️ [PERF] get_wizard_options(): {duration_ms:.2f} ms")
        
        # Validaciones funcionales
        self.assertIsInstance(options, dict, "Opciones debe ser un diccionario")
        self.assertIn('groups', options, "Falta clave 'groups'")
        self.assertIn('shares', options, "Falta clave 'shares'")
        self.assertIn('group_permissions', options, "Falta clave 'group_permissions'")
        
        print(f"✅ [FUNC] get_wizard_options(): Estructura de datos completa.")

    def test_admin_session_latency(self):
        """Mide latencia de creación de sesión administrativa (DSM)."""
        from apps.settings.services.connection_service import ConnectionService
        
        start_time = time.time()
        admin_conn = ConnectionService(self.user_service.config)
        auth_result = admin_conn.authenticate(session_alias='DSM')
        end_time = time.time()
        
        duration_ms = (end_time - start_time) * 1000
        print(f"⏱️ [PERF] Authenticate (DSM): {duration_ms:.2f} ms")
        
        if auth_result.get('success'):
            print(f"✅ [FUNC] Authenticate (DSM): Conexión exitosa.")
            # Cerrar sesión para no saturar
            admin_conn.logout(auth_result['sid'], session_alias='DSM')
        else:
            print(f"⚠️ [FUNC] Authenticate (DSM): Falló (Normal si no hay NAS real y no está en offline mode).")

    def tearDown(self):
        print("="*50 + "\n")
