"""
Admin configuration para Settings app.
"""
from django.contrib import admin
from .models import NASConfig


@admin.register(NASConfig)
class NASConfigAdmin(admin.ModelAdmin):
    """
    Admin para NASConfig.
    """
    list_display = ['host', 'port', 'protocol', 'admin_username', 'is_active', 'updated_at']
    list_filter = ['protocol', 'is_active', 'created_at']
    search_fields = ['host', 'admin_username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información de Conexión', {
            'fields': ('host', 'port', 'protocol')
        }),
        ('Credenciales', {
            'fields': ('admin_username', 'admin_password'),
            'description': 'Credenciales del administrador del NAS'
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
