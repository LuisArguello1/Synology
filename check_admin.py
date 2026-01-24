import os
import django
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.settings.services.connection_service import ConnectionService
from apps.settings.models import NASConfig

def diagnostic():
    config = NASConfig.get_active_config()
    if not config:
        print("ERROR: No active NAS configuration found.")
        return

    print(f"--- DIAGNOSTIC SYSTEM ---")
    print(f"Connecting to: {config.host}:{config.port} as user: {config.admin_username}")
    
    conn = ConnectionService(config)
    auth = conn.authenticate(session_alias='DSM')
    
    if not auth.get('success'):
        print(f"CRITICAL: Failed to login: {auth.get('message')}")
        return

    print("SUCCESS: Login successful.")
    sid = auth.get('sid')
    
    # Try to list users to see names and groups
    print("Listing all users to check permissions and groups...")
    resp = conn.request(
        api='SYNO.Core.User',
        method='list',
        version=1,
        params={
            'limit': 10,
            'additional': json.dumps(["groups"])
        }
    )
    
    if resp.get('success'):
        users = resp.get('data', {}).get('users', [])
        print(f"Found {len(users)} users.")
        for u in users:
            name = u.get('name')
            groups = [g.get('name') for g in u.get('groups', [])]
            print(f"- User: {name}, Groups: {groups}")
            if name == config.admin_username:
                if 'administrators' in groups:
                    print(f"  RESULT: User {name} IS an administrator.")
                else:
                    print(f"  RESULT: User {name} IS NOT an administrator.")
    else:
        print(f"ERROR listing users: {resp}")

    conn.logout(sid, session_alias='DSM')

if __name__ == "__main__":
    diagnostic()
