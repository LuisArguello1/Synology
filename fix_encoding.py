from django.contrib.auth.models import User

# Corregir nombres con caracteres extraños
users = {
    'jperez': ('Juan', 'Pérez'),
    'mgomez': ('María', 'Gómez'),
    'cpavez': ('Carlos', 'Pavez'),
    'asilva': ('Ana', 'Silva')
}

print("Corrigiendo nombres de usuarios...")
for username, (first, last) in users.items():
    try:
        u = User.objects.get(username=username)
        u.first_name = first
        u.last_name = last
        u.save()
        print(f"✓ Corregido: {u.username} -> {u.get_full_name()}")
    except User.DoesNotExist:
        print(f"User {username} not found")

print("Listo.")
