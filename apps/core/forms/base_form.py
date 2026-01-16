"""
Formularios base para el sistema NAS Manager.

Este módulo define las clases base que TODOS los formularios del sistema
deben heredar. Centraliza funcionalidad común, estilos Tailwind y validaciones.

Arquitectura:
    BaseFormMixin → Aplica estilos Tailwind automáticamente
    CoreBaseForm → Para formularios sin modelo (settings, conexiones)
    CoreBaseModelForm → Para formularios con modelo (CRUD)

Uso:
    from apps.core.forms import CoreBaseForm, CoreBaseModelForm
    
    class MySettingsForm(CoreBaseForm):
        # Hereda estilos automáticos
        pass
    
    class MyModelForm(CoreBaseModelForm):
        class Meta:
            model = MyModel
            fields = '__all__'
"""

from django import forms
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class BaseFormMixin:
    """
    Mixin para aplicar estilos Tailwind CSS automáticamente a todos los widgets.
    
    Este mixin:
    - Detecta el tipo de widget
    - Aplica clases Tailwind apropiadas
    - Maneja placeholders automáticos
    - Respeta clases ya definidas (no las sobreescribe)
    - Soporta readonly y disabled
    
    Estilo Enterprise: Limpio, profesional, tipo Admin Console / NAS.
    """
    
    # Clases base para todos los inputs
    BASE_INPUT_CLASSES = (
        'w-full px-3 py-1.5 text-xs border border-gray-300 rounded-sm '
        'focus:outline-none focus:ring-1 focus:ring-indigo-500 '
        'focus:border-transparent transition-colors'
    )
    
    # Clases para select
    SELECT_CLASSES = (
        'w-full px-3 py-1.5 text-xs border border-gray-300 rounded-sm '
        'focus:outline-none focus:ring-1 focus:ring-indigo-500 '
        'focus:border-transparent bg-white transition-colors'
    )
    
    # Clases para textarea
    TEXTAREA_CLASSES = (
        'w-full px-3 py-2 text-xs border border-gray-300 rounded-sm '
        'focus:outline-none focus:ring-1 focus:ring-indigo-500 '
        'focus:border-transparent transition-colors resize-y'
    )
    
    # Clases para checkbox y radio
    CHECKBOX_CLASSES = (
        'w-3.5 h-3.5 text-indigo-600 border-gray-300 rounded-sm '
        'focus:ring-indigo-500 focus:ring-1 transition-colors'
    )
    
    # Clases para file input
    FILE_CLASSES = (
        'block w-full text-xs text-gray-500 '
        'file:mr-3 file:py-1.5 file:px-3 '
        'file:rounded-sm file:border-0 '
        'file:text-xs file:font-semibold '
        'file:bg-indigo-50 file:text-indigo-700 '
        'hover:file:bg-indigo-100 transition-colors'
    )
    
    # Clases adicionales para estados
    READONLY_CLASSES = 'bg-gray-100 cursor-not-allowed'
    DISABLED_CLASSES = 'bg-gray-100 cursor-not-allowed opacity-60'
    ERROR_CLASSES = 'border-red-500 focus:ring-red-500'
    
    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario y aplica estilos automáticamente.
        """
        super().__init__(*args, **kwargs)
        self._apply_widget_styles()
        self._apply_placeholders()
        self._mark_required_fields()
    
    def _apply_widget_styles(self):
        """
        Aplica clases CSS Tailwind a todos los widgets según su tipo.
        No sobreescribe clases ya definidas.
        """
        for field_name, field in self.fields.items():
            widget = field.widget
            existing_classes = widget.attrs.get('class', '')
            
            # Determinar clases según tipo de widget
            widget_classes = self._get_widget_classes(widget)
            
            # Aplicar clases de estado
            if field.disabled:
                widget_classes += ' ' + self.DISABLED_CLASSES
            elif widget.attrs.get('readonly'):
                widget_classes += ' ' + self.READONLY_CLASSES
            
            # Combinar con clases existentes (sin duplicados)
            if existing_classes:
                # Mantener clases existentes, agregar solo las que no existen
                all_classes = existing_classes + ' ' + widget_classes
            else:
                all_classes = widget_classes
            
            widget.attrs['class'] = all_classes.strip()
    
    def _get_widget_classes(self, widget):
        """
        Retorna las clases CSS apropiadas según el tipo de widget.
        
        Args:
            widget: Widget de Django
        
        Returns:
            str: Clases CSS Tailwind
        """
        # Input de texto, email, url, number, etc.
        if isinstance(widget, (
            forms.TextInput, 
            forms.EmailInput, 
            forms.URLInput, 
            forms.NumberInput,
            forms.DateInput,
            forms.TimeInput,
            forms.DateTimeInput,
        )):
            return self.BASE_INPUT_CLASSES
        
        # Password input
        elif isinstance(widget, forms.PasswordInput):
            return self.BASE_INPUT_CLASSES
        
        # Select
        elif isinstance(widget, forms.Select):
            return self.SELECT_CLASSES
        
        # Textarea
        elif isinstance(widget, forms.Textarea):
            return self.TEXTAREA_CLASSES
        
        # Checkbox
        elif isinstance(widget, forms.CheckboxInput):
            return self.CHECKBOX_CLASSES
        
        # Radio
        elif isinstance(widget, forms.RadioSelect):
            return ''  # Los estilos de radio son más complejos, se manejan en template
        
        # File upload
        elif isinstance(widget, forms.FileInput):
            return self.FILE_CLASSES
        
        # Multiple select
        elif isinstance(widget, forms.SelectMultiple):
            return self.SELECT_CLASSES + ' h-32'
        
        # Default
        else:
            return self.BASE_INPUT_CLASSES
    
    def _apply_placeholders(self):
        """
        Aplica placeholders automáticos si no están definidos.
        Usa el label del campo como placeholder.
        """
        for field_name, field in self.fields.items():
            widget = field.widget
            
            # Solo aplicar a inputs de texto
            if isinstance(widget, (
                forms.TextInput, 
                forms.EmailInput, 
                forms.URLInput,
                forms.NumberInput,
            )):
                if 'placeholder' not in widget.attrs and field.label:
                    widget.attrs['placeholder'] = f'{field.label}...'
    
    def _mark_required_fields(self):
        """
        Marca visualmente los campos requeridos.
        Agrega un atributo 'required' al widget.
        """
        for field_name, field in self.fields.items():
            if field.required:
                field.widget.attrs['required'] = True


class CoreBaseForm(BaseFormMixin, forms.Form):
    """
    Clase base para TODOS los formularios sin modelo del sistema.
    
    Casos de uso:
    - Formularios de configuración
    - Formularios de conexión (NAS, APIs)
    - Formularios de búsqueda y filtros
    - Settings globales
    
    Características:
    - Estilos Tailwind automáticos (heredados de BaseFormMixin)
    - Manejo centralizado de errores
    - Métodos helper para validaciones comunes
    - Logging integrado
    
    Ejemplo:
        class NASConnectionForm(CoreBaseForm):
            host = forms.CharField(label='Host')
            port = forms.IntegerField(label='Puerto')
            
            def clean(self):
                cleaned_data = super().clean()
                # Validación custom
                return cleaned_data
    """
    
    def clean(self):
        """
        Hook de validación global.
        Override en subclases para validaciones custom.
        
        Returns:
            dict: Datos validados
        """
        cleaned_data = super().clean()
        
        # Hook para validaciones cross-field en subclases
        self._validate_cross_fields(cleaned_data)
        
        return cleaned_data
    
    def _validate_cross_fields(self, cleaned_data):
        """
        Placeholder para validaciones entre múltiples campos.
        Override en subclases si es necesario.
        
        Args:
            cleaned_data: Diccionario de datos validados
        """
        pass
    
    def add_error_message(self, field, message):
        """
        Helper para agregar errores de forma consistente.
        
        Args:
            field: Nombre del campo o None para errores globales
            message: Mensaje de error
        """
        logger.warning(f"Error en formulario {self.__class__.__name__}: {field} - {message}")
        self.add_error(field, message)
    
    def get_cleaned_data_or_none(self, field_name):
        """
        Helper para obtener datos validados de forma segura.
        
        Args:
            field_name: Nombre del campo
        
        Returns:
            Valor del campo o None si no existe
        """
        return self.cleaned_data.get(field_name) if hasattr(self, 'cleaned_data') else None
    
    def validate_connection(self, host, port, protocol='https'):
        """
        Método helper para validar conexiones de red.
        Útil para formularios de configuración de NAS/APIs.
        
        Args:
            host: Hostname o IP
            port: Puerto
            protocol: Protocolo (http/https)
        
        Returns:
            bool: True si la conexión es válida
        
        Raises:
            ValidationError: Si la conexión falla
        """
        import socket
        
        try:
            # Validar formato de puerto
            if not (1 <= port <= 65535):
                raise ValidationError('Puerto fuera de rango (1-65535)')
            
            # Intentar resolver el host
            socket.gethostbyname(host)
            
            logger.info(f"Validación de conexión exitosa: {protocol}://{host}:{port}")
            return True
            
        except socket.gaierror:
            raise ValidationError(f'No se pudo resolver el host: {host}')
        except Exception as e:
            raise ValidationError(f'Error al validar conexión: {str(e)}')


class CoreBaseModelForm(BaseFormMixin, forms.ModelForm):
    """
    Clase base para TODOS los formularios con modelo del sistema.
    
    Casos de uso:
    - CRUDs (Create, Read, Update, Delete)
    - Formularios de edición de configuración NAS
    - Formularios de usuarios y permisos
    - Cualquier formulario ligado a un modelo
    
    Características:
    - Estilos Tailwind automáticos (heredados de BaseFormMixin)
    - Asterisco (*) en campos requeridos
    - Hook post_save() para lógica posterior al guardado
    - Método save() extensible
    - Logging integrado
    
    Ejemplo:
        class NASConfigForm(CoreBaseModelForm):
            class Meta:
                model = NASConfig
                fields = ['host', 'port', 'protocol']
            
            def post_save(self, instance, created):
                # Lógica post-guardado
                if created:
                    logger.info(f'Nueva config creada: {instance}')
    """
    
    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario y marca campos requeridos con asterisco.
        """
        super().__init__(*args, **kwargs)
        self._add_required_asterisk()
    
    def _add_required_asterisk(self):
        """
        Agrega asterisco (*) al label de campos requeridos.
        Estilo enterprise: visual claro y consistente.
        """
        for field_name, field in self.fields.items():
            if field.required and field.label:
                field.label = f'{field.label} *'
    
    def save(self, commit=True):
        """
        Guarda la instancia del modelo.
        Extensible para lógica pre-guardado.
        
        Args:
            commit: Si True, guarda en la BD inmediatamente
        
        Returns:
            Instancia del modelo
        """
        # Hook pre-save
        self._pre_save()
        
        # Guardar instancia
        instance = super().save(commit=False)
        
        # Detectar si es creación o actualización
        created = instance.pk is None
        
        if commit:
            instance.save()
            self.save_m2m()  # Guardar relaciones many-to-many
            
            # Hook post-save
            self.post_save(instance, created)
            
            logger.info(
                f"{'Creado' if created else 'Actualizado'} "
                f"{instance.__class__.__name__}: {instance}"
            )
        
        return instance
    
    def _pre_save(self):
        """
        Hook ejecutado ANTES de guardar la instancia.
        Override en subclases para lógica pre-guardado.
        
        Ejemplo:
            def _pre_save(self):
                # Validaciones adicionales
                # Modificaciones de datos
                pass
        """
        pass
    
    def post_save(self, instance, created):
        """
        Hook ejecutado DESPUÉS de guardar la instancia.
        Override en subclases para lógica post-guardado.
        
        Args:
            instance: Instancia guardada del modelo
            created: True si es una nueva instancia, False si es actualización
        
        Ejemplo:
            def post_save(self, instance, created):
                if created:
                    # Enviar notificación
                    # Crear registros relacionados
                    pass
        """
        pass
    
    def clean(self):
        """
        Validación global del formulario.
        Override en subclases para validaciones custom.
        
        Returns:
            dict: Datos validados
        """
        cleaned_data = super().clean()
        
        # Hook para validaciones cross-field
        self._validate_model_constraints(cleaned_data)
        
        return cleaned_data
    
    def _validate_model_constraints(self, cleaned_data):
        """
        Placeholder para validar constraints del modelo.
        Override en subclases si es necesario.
        
        Args:
            cleaned_data: Diccionario de datos validados
        """
        pass
    
    def add_error_message(self, field, message):
        """
        Helper para agregar errores de forma consistente.
        
        Args:
            field: Nombre del campo o None para errores globales
            message: Mensaje de error
        """
        logger.warning(
            f"Error en formulario {self.__class__.__name__}: "
            f"{field} - {message}"
        )
        self.add_error(field, message)
    
    def handle_unique_constraint_error(self, field_name, value):
        """
        Helper para manejar errores de unicidad.
        
        Args:
            field_name: Campo con constraint de unicidad
            value: Valor duplicado
        """
        self.add_error_message(
            field_name,
            f'Ya existe un registro con {field_name}: {value}'
        )
