"""
Forms para la app Settings.

Todos los formularios heredan de CoreBaseModelForm o CoreBaseForm.
"""
from django import forms
import logging

from apps.core.forms.base_form import CoreBaseModelForm
from apps.settings.models import NASConfig

logger = logging.getLogger(__name__)


class NASConfigForm(CoreBaseModelForm):
    """
    Formulario para editar la configuración del NAS.
    
    Hereda de CoreBaseModelForm que proporciona:
    - Estilos Tailwind automáticos
    - Asterisco en campos requeridos
    - Hooks pre_save y post_save
    - Logging integrado
    """
    
    class Meta:
        model = NASConfig
        fields = ['host', 'port', 'protocol', 'admin_username', 'admin_password']
        widgets = {
            'admin_password': forms.PasswordInput(attrs={
                'placeholder': 'Dejar en blanco para mantener actual'
            }),
        }
        help_texts = {
            'admin_password': 'Dejar en blanco para mantener la contraseña actual',
        }
    
    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario.
        El campo password es opcional en edición.
        """
        super().__init__(*args, **kwargs)
        
        # Password opcional si estamos editando
        if self.instance.pk:
            self.fields['admin_password'].required = False
            self.fields['admin_password'].label = 'Contraseña (opcional)'
    
    def clean_port(self):
        """Validación adicional del puerto."""
        port = self.cleaned_data.get('port')
        if port and (port < 1 or port > 65535):
            raise forms.ValidationError('El puerto debe estar entre 1 y 65535')
        return port
    
    def clean_host(self):
        """Validación del host."""
        host = self.cleaned_data.get('host')
        if not host:
            raise forms.ValidationError('El host es requerido')
        return host.strip()
    
    def _pre_save(self):
        """
        Hook pre-save: Manejo especial de contraseña.
        Si el campo password está vacío en edición, mantener el anterior.
        """
        if self.instance.pk and not self.cleaned_data.get('admin_password'):
            # Obtener instancia original de la BD
            original = NASConfig.objects.get(pk=self.instance.pk)
            self.instance.admin_password = original.admin_password
    
    def post_save(self, instance, created):
        """
        Hook post-save: Log de cambios.
        """
        if created:
            logger.info(f'Nueva configuración NAS creada: {instance.get_base_url()}')
        else:
            logger.info(f'Configuración NAS actualizada: {instance.get_base_url()}')

