"""
Models para la app Settings.

NASConfig: Configuración del NAS Synology (IP, puerto, credenciales)
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class NASConfig(models.Model):
    """
    Configuración del NAS Synology.
    
    Singleton: solo puede existir una configuración activa a la vez.
    Almacena los datos de conexión al NAS (IP, puerto, protocolo, credenciales).
    """
    PROTOCOL_CHOICES = [
        ('http', 'HTTP'),
        ('https', 'HTTPS (Seguro)'),
    ]
    
    host = models.CharField(
        max_length=255,
        verbose_name='Host',
        help_text='IP o dominio del NAS (ej: 192.168.1.100 o nas.ejemplo.com)'
    )
    
    port = models.PositiveIntegerField(
        default=5000,
        verbose_name='Puerto',
        help_text='Puerto DSM (por defecto 5000 HTTP, 5001 HTTPS)',
        validators=[
            MinValueValidator(1),
            MaxValueValidator(65535)
        ]
    )
    
    protocol = models.CharField(
        max_length=5,
        choices=PROTOCOL_CHOICES,
        default='https',
        verbose_name='Protocolo'
    )
    
    admin_username = models.CharField(
        max_length=100,
        verbose_name='Usuario Administrador',
        help_text='Usuario con permisos de administrador en el NAS'
    )
    
    admin_password = models.CharField(
        max_length=255,
        verbose_name='Contraseña',
        help_text='Contraseña del usuario administrador'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Configuración Activa',
        help_text='Solo puede haber una configuración activa'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última Actualización'
    )
    
    class Meta:
        verbose_name = 'Configuración NAS'
        verbose_name_plural = 'Configuraciones NAS'
        ordering = ['-is_active', '-created_at']
    
    def __str__(self):
        return f"{self.protocol}://{self.host}:{self.port}"
    
    def get_base_url(self):
        """
        Construye dinámicamente la URL base del NAS.
        
        Esta es la forma correcta de obtener la URL base:
        NUNCA hardcodear IPs en el código.
        
        Returns:
            str: URL base completa (ej: https://192.168.1.100:5001)
        """
        return f"{self.protocol}://{self.host}:{self.port}"
    
    def save(self, *args, **kwargs):
        """
        Override save para implementar patrón Singleton.
        
        Si esta configuración se marca como activa, 
        desactiva todas las demás.
        """
        if self.is_active:
            # Desactivar todas las demás configuraciones
            NASConfig.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active_config(cls):
        """
        Obtiene la configuración activa actual.
        
        Returns:
            NASConfig or None: La configuración activa o None si no existe
        """
        return cls.objects.filter(is_active=True).first()
