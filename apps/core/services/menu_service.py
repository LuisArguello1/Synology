from django.urls import reverse

class MenuService:
    """
    Servicio para generar la estructura del menú lateral (Sidebar).
    Centraliza la definición de items y el cálculo de estado activo.
    """
    
    @staticmethod
    def get_menu_items(current_path, user=None):
        """
        Retorna la lista de items del menú filtrada por permisos.
        """
        from django.conf import settings
        is_offline = getattr(settings, 'NAS_OFFLINE_MODE', False)
        is_staff = getattr(user, 'is_staff', False) or is_offline
        
        try:
            dashboard_url = reverse('core:dashboard')
        except:
            dashboard_url = '#'

        try:
            settings_url = reverse('settings:config')
        except:
            settings_url = '#'
            
        try:
            users_url = reverse('usuarios:list')
        except:
            users_url = '#'
            
        try:
            audit_url = reverse('auditoria:list')
        except:
            audit_url = '#'

        try:
            share_folder_url = reverse('carpeta:list')
        except:
            share_folder_url = '#'

        try:
            my_files_url = reverse('archivos:index')
        except:
            my_files_url = '#'

        menu = []
        
        # Dashboard siempre visible
        menu.append({
            'name': 'Dashboard',
            'icon': 'tachometer-alt',
            'url': dashboard_url,
            'active': current_path == dashboard_url
        })
        
        # Sección de Sistema
        menu.append({'separator': True, 'label': 'SISTEMA'})
        
        # Mis Archivos
        menu.append({
            'name': 'Mis Archivos',
            'icon': 'folder',
            'url': my_files_url,
            'active': current_path.startswith('/archivos/')
        })
        
        # Solo para administradores
        if is_staff:
            menu.append({
                'name': 'Usuarios',
                'icon': 'users', 
                'url': users_url,
                'active': current_path.startswith('/usuarios/')
            })
            menu.append({
                'name': 'Auditoría',
                'icon': 'clipboard-list',
                'url': audit_url,
                'active': current_path.startswith('/auditoria/')
            })
            menu.append({
                'name': 'Carpetas Compartidas',
                'icon': 'folder',
                'url': share_folder_url,
                'active': current_path.startswith('/carpeta/')
            })
            
            # Sección de Configuración
            menu.append({'separator': True, 'label': 'CONFIGURACIÓN'})
            menu.append({
                'name': 'NAS Config',
                'icon': 'cog',
                'url': settings_url,
                'active': current_path == settings_url
            })
        
        return menu
