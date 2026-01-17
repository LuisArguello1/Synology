from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    """
    Registro de auditoría para acciones críticas del sistema.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="Usuario que realizó la acción (puede ser NULL si es sistema o anónimo)"
    )
    action = models.CharField(max_length=50, help_text="Código de acción (ej. CREATE_USER, LOGIN)")
    description = models.TextField(help_text="Descripción legible por humanos")
    details = models.JSONField(default=dict, blank=True, help_text="Datos técnicos adicionales")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Registro de Auditoría"
        verbose_name_plural = "Registros de Auditoría"

    def __str__(self):
        return f"[{self.timestamp}] {self.user} - {self.action}"
