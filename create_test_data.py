"""
Script para insertas datos de prueba y probar que el módulo de grupos funciona correctamente

"""
from django.contrib.auth.models import User
from apps.groups.models import SharedFolder, Volume, Application

print("=== Creando datos de prueba para el módulo de grupos ===\n")

# Crear usuarios de prueba (si no existen)
print("1. Creando usuarios de prueba...")
users_data = [
    {'username': 'jperez', 'email': 'jperez@empresa.com', 'first_name': 'Juan', 'last_name': 'Pérez'},
    {'username': 'mgomez', 'email': 'mgomez@empresa.com', 'first_name': 'María', 'last_name': 'Gómez'},
    {'username': 'cpavez', 'email': 'cpavez@empresa.com', 'first_name': 'Carlos', 'last_name': 'Pavez'},
    {'username': 'asilva', 'email': 'asilva@empresa.com', 'first_name': 'Ana', 'last_name': 'Silva'},
]

for user_data in users_data:
    user, created = User.objects.get_or_create(
        username=user_data['username'],
        defaults={
            'email': user_data['email'],
            'first_name': user_data['first_name'],
            'last_name': user_data['last_name']
        }
    )
    if created:
        user.set_password('password123')
        user.save()
        print(f"   ✓ Usuario creado: {user.get_full_name()} (@{user.username})")
    else:
        print(f"   - Usuario ya existe: {user.get_full_name()} (@{user.username})")

# Crear carpetas compartidas
print("\n2. Creando carpetas compartidas...")
folders_data = [
    {'name': 'Documentos', 'description': 'Documentos corporativos', 'path': '/volume1/documentos'},
    {'name': 'Multimedia', 'description': 'Fotos y videos', 'path': '/volume1/multimedia'},
    {'name': 'Proyectos', 'description': 'Proyectos en desarrollo', 'path': '/volume1/proyectos'},
    {'name': 'Respaldos', 'description': 'Backups automáticos', 'path': '/volume1/respaldos'},
]

for folder_data in folders_data:
    folder, created = SharedFolder.objects.get_or_create(
        name=folder_data['name'],
        defaults={
            'description': folder_data['description'],
            'path': folder_data['path']
        }
    )
    if created:
        print(f"   ✓ Carpeta creada: {folder.name}")
    else:
        print(f"   - Carpeta ya existe: {folder.name}")

# Crear volúmenes
print("\n3. Creando volúmenes...")
volumes_data = [
    {'name': 'volume1', 'total_space': 2000, 'available_space': 1200},
    {'name': 'volume2', 'total_space': 4000, 'available_space': 3500},
]

for volume_data in volumes_data:
    volume, created = Volume.objects.get_or_create(
        name=volume_data['name'],
        defaults={
            'total_space': volume_data['total_space'],
            'available_space': volume_data['available_space']
        }
    )
    if created:
        print(f"   ✓ Volumen creado: {volume.name} ({volume.available_space}/{volume.total_space} GB)")
    else:
        print(f"   - Volumen ya existe: {volume.name}")

# Crear aplicaciones
print("\n4. Creando aplicaciones...")
apps_data = [
    {'name': 'AFP', 'description': 'Apple Filing Protocol'},
    {'name': 'DSM', 'description': 'DiskStation Manager'},
    {'name': 'FTP', 'description': 'File Transfer Protocol'},
    {'name': 'File Station', 'description': 'Explorador de archivos web'},
    {'name': 'SFTP', 'description': 'SSH File Transfer Protocol'},
    {'name': 'SMB', 'description': 'Server Message Block'},
    {'name': 'Universal Search', 'description': 'Búsqueda universal'},
]

for app_data in apps_data:
    app, created = Application.objects.get_or_create(
        name=app_data['name'],
        defaults={
            'description': app_data['description'],
            'is_active': True
        }
    )
    if created:
        print(f"   ✓ Aplicación creada: {app.name}")
    else:
        print(f"   - Aplicación ya existe: {app.name}")

print("\n✅ Datos de prueba creados exitosamente!")
print("\nPuedes acceder al módulo de grupos en: http://localhost:8000/groups/")
