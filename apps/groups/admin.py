from django.contrib import admin
from .models import Group, SharedFolder, Volume, Application


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'get_member_count', 'is_system', 'created_at']
    list_filter = ['is_system', 'created_at']
    search_fields = ['name', 'description']
    filter_horizontal = ['members']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información básica', {
            'fields': ('name', 'description', 'is_system')
        }),
        ('Miembros', {
            'fields': ('members',)
        }),
        ('Permisos y configuraciones', {
            'fields': ('folder_permissions', 'quotas', 'app_permissions', 'speed_limits'),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SharedFolder)
class SharedFolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'path', 'created_at']
    search_fields = ['name', 'description']


@admin.register(Volume)
class VolumeAdmin(admin.ModelAdmin):
    list_display = ['name', 'total_space', 'available_space']
    search_fields = ['name']


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
