import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.settings.services.connection_service import ConnectionService
from apps.settings.models import NASConfig

def check_users():
    config = NASConfig.get_active_config()
    conn = ConnectionService(config)
    auth = conn.authenticate(session_alias='DSM')
    
    # Listar todos los usuarios
    resp = conn.request('SYNO.Core.User', 'list', version=1, params={'limit': 100})
    if resp.get('success'):
        users = resp.get('data', {}).get('users', [])
        print(f"TOTAL USUARIOS EN EL NAS: {len(users)}")
        for u in users:
            print(f"- {u.get('name')}")
    else:
        print(f"Error: {resp}")

if __name__ == "__main__":
    check_users()
