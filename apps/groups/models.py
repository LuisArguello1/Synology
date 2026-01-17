"""
Modelos para la app Groups.

- Group: Grupos de usuarios con permisos, cuotas y configuraciones
- SharedFolder: Carpetas compartidas (simulación)
- Volume: Volúmenes de almacenamiento (simulación)
- Application: Aplicaciones/servicios del NAS (simulación)
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class SharedFolder(models.Model):
    """
    Carpetas compartidas del NAS (simulación).
    
    En un entorno real, estas se sincronizarían con el NAS.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    path = models.CharField(
        max_length=255,
        verbose_name='Ruta',
        help_text='Ruta virtual de la carpeta (ej: /volume1/homes)'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )
    
    class Meta:
        verbose_name = 'Carpeta compartida'
        verbose_name_plural = 'Carpetas compartidas'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Volume(models.Model):
    """
    Volúmenes de almacenamiento del NAS (simulación).
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre',
        help_text='ej: volume1, volume2'
    )
    
    total_space = models.BigIntegerField(
        verbose_name='Espacio total (GB)',
        validators=[MinValueValidator(1)]
    )
    
    available_space = models.BigIntegerField(
        verbose_name='Espacio disponible (GB)',
        validators=[MinValueValidator(0)]
    )
    
    class Meta:
        verbose_name = 'Volumen'
        verbose_name_plural = 'Volúmenes'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.available_space}/{self.total_space} GB)"


class Application(models.Model):
    """
    Aplicaciones/servicios del NAS (simulación).
    
    Ejemplos: AFP, DSM, FTP, File Station, SFTP, SMB, Universal Search
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activa',
        help_text='Si la aplicación está disponible en el sistema'
    )
    
    class Meta:
        verbose_name = 'Aplicación'
        verbose_name_plural = 'Aplicaciones'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Group(models.Model):
    """
    Grupo de usuarios del NAS.
    
    Almacena toda la configuración del grupo:
    - Información básica (nombre, descripción)
    - Miembros (usuarios)
    - Permisos de carpetas compartidas
    - Cuotas por volumen
    - Permisos de aplicaciones
    - Límites de velocidad
    """
    
    # === PASO 1: Información básica ===
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre del grupo',
        help_text='Nombre único del grupo'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    # === PASO 2: Miembros ===
    members = models.ManyToManyField(
        User,
        blank=True,
        related_name='groups_membership',
        verbose_name='Miembros'
    )
    
    # === PASO 3: Permisos de carpetas compartidas ===
    folder_permissions = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Permisos de carpetas',
        help_text='Formato: {"folder_id": "rw|ro|na"} (rw=read-write, ro=read-only, na=no-access)'
    )
    
    # === PASO 4: Cuotas por volumen ===
    quotas = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Cuotas',
        help_text='Formato: {"volume_id": {"amount": 100, "unit": "GB"}}'
    )
    
    # === PASO 5: Permisos de aplicaciones ===
    app_permissions = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Permisos de aplicaciones',
        help_text='Formato: {"app_name": "allow|deny"}'
    )
    
    # === PASO 6: Límites de velocidad ===
    speed_limits = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Límites de velocidad',
        help_text='Formato: {"service": {"upload": 100, "download": 200}} (KB/s)'
    )
    
    # === Metadatos ===
    is_system = models.BooleanField(
        default=False,
        verbose_name='Grupo del sistema',
        help_text='Los grupos del sistema no se pueden eliminar'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización'
    )
    
    class Meta:
        verbose_name = 'Grupo'
        verbose_name_plural = 'Grupos'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_member_count(self):
        """Retorna el número de miembros del grupo."""
        return self.members.count()
    
    def export_to_dict(self):
        """
        Exporta el grupo a un diccionario (para CSV/JSON).
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'member_count': self.get_member_count(),
            'folder_permissions': self.folder_permissions,
            'quotas': self.quotas,
            'app_permissions': self.app_permissions,
            'speed_limits': self.speed_limits,
            'is_system': self.is_system,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
