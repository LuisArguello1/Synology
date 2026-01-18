from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from .models import NASConfig
from .forms import NASConfigForm
from .services.connection_service import ConnectionService
import logging

logger = logging.getLogger(__name__)

class InitialSetupView(CreateView):
    """
    Vista pública para la configuración inicial del NAS.
    Solo accesible si NO existe configuración activa.
    """
    model = NASConfig
    form_class = NASConfigForm
    template_name = 'settings/initial_setup.html'
    success_url = reverse_lazy('accounts:login')
    
    def dispatch(self, request, *args, **kwargs):
        # Si YA existe configuración, no permitir acceso a setup
        if NASConfig.objects.filter(is_active=True).exists():
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """
        Valida que la conexión sea exitosa ANTES de guardar.
        """
        # 1. Crear instancia temporal sin guardar
        temp_config = form.save(commit=False)
        
        # 2. Probar conexión REAL usando ConnectionService
        try:
            # Usamos el config temporal para el servicio
            service = ConnectionService(config=temp_config)
            result = service.test_connection()
            
            if not result['success']:
                # Si falla, agregar error al form y volver a mostrar
                error_msg = result.get('message', 'Error desconocido al conectar')
                if result.get('error'):
                    error_msg += f" ({result['error']})"
                    
                form.add_error(None, f"❌ No se pudo conectar al NAS: {error_msg}")
                return self.form_invalid(form)
                
        except Exception as e:
            logger.error(f"Error probando conexión en setup: {e}")
            form.add_error(None, f"❌ Error técnico al probar conexión: {str(e)}")
            return self.form_invalid(form)

        # 3. Si la conexión fue exitosa, guardar y activar
        temp_config.is_active = True
        temp_config.save()
        
        logger.info(f"Configuración inicial NAS creada y verificada: {temp_config.host}")
        
        messages.success(
            self.request, 
            f"¡Conexión exitosa! NAS configurado en {temp_config.host}. Ahora inicia sesión."
        )
        return redirect(self.success_url)
