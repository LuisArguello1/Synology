from django.urls import reverse

class MenuService:
    @staticmethod
    def get_menu_items(request):
        """
        Genera items del menú principal de forma centralizada.
        """
        current_path = request.path
        
        return [
            {
                'name': 'Dashboard',
                'icon': 'tachometer-alt',
                'url': 'core:dashboard',
                'active': current_path == reverse('core:dashboard')
            },
            {'separator': True, 'label': 'SISTEMA'},
            {
                'name': 'Usuarios',
                'icon': 'users',
                'url': 'core:dashboard', # Placeholder, idealmente 'accounts:list'
                'active': False
            },
            {
                'name': 'Grupos',
                'icon': 'users-cog',
                'url': 'groups:list',
                'active': current_path.startswith('/groups/')
            },
            {
                'name': 'Carpetas',
                'icon': 'folder',
                'url': 'core:dashboard', # Placeholder
                'active': False
            },
            {
                'name': 'Aplicaciones',
                'icon': 'layer-group',
                'url': 'core:dashboard', # Placeholder
                'active': False
            },
            {'separator': True, 'label': 'CONFIGURACIÓN'},
            {
                'name': 'NAS Config',
                'icon': 'cog',
                'url': 'settings:config',
                'active': current_path.startswith('/settings/')
            },
        ]
