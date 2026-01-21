from django.views.generic import FormView
from django.contrib.auth import login, logout
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.views import View
from ..forms.login_form import LoginForm

class LoginView(FormView):
    """
    Vista de login que autentica contra Synology.
    """
    template_name = 'accounts/login.html'
    form_class = LoginForm
    
    def get_success_url(self):
        next_url = self.request.GET.get('next')
        return next_url or reverse_lazy('core:dashboard')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Importación tardía para evitar ciclos
        from apps.core.services.metrics_service import MetricsService
        
        # Obtener métricas para mostrar en el login
        metrics_service = MetricsService()
        context['metrics'] = metrics_service.get_dashboard_metrics()
        
        return context
    
    def form_valid(self, form):
        user = form.get_user()
        
        # Login usuario en Django
        login(self.request, user)
        
        # Configurar sesión según "recordarme"
        if not form.cleaned_data.get('remember_me'):
            # Sesión expira al cerrar navegador
            self.request.session.set_expiry(0)
        else:
            # Sesión dura 7 días
            self.request.session.set_expiry(604800)
        
        messages.success(
            self.request,
            f'Bienvenido, {user.username}!'
        )
        
        # LOG AUDITORIA
        from apps.auditoria.services.audit_service import AuditService
        AuditService.log(
            action='LOGIN',
            description=f'Inicio de sesión exitoso: {user.username}',
            user=user,
            request=self.request
        )
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(
            self.request,
            'No se pudo iniciar sesión. Verifica credenciales y conexión.'
        )
        return super().form_invalid(form)
    
    def dispatch(self, request, *args, **kwargs):
        # 🟢 CHECK: ¿Existe configuración?
        # Evitar import circular
        from apps.settings.models import NASConfig
        if not NASConfig.objects.filter(is_active=True).exists():
            return redirect('settings:initial_setup')

        # Redirect si ya está autenticado
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)


class LogoutView(View):
    """
    Vista de logout que cierra sesión en Django y Synology.
    """
    
    def post(self, request):
        user = request.user
        # Obtener SID de sesión
        sid = request.session.get('synology_sid')
        
        # Cerrar sesión en Synology si existe SID
        if sid:
            try:
                from apps.settings.services.connection_service import ConnectionService
                from apps.settings.models import NASConfig
                
                config = NASConfig.get_active_config()
                if config:
                    service = ConnectionService(config)
                    service.logout(sid)
            except Exception:
                pass  # No fallar si Synology no está disponible o config no existe
        
        # Cerrar sesión Django
        logout(request)
        
        # LOG AUDITORIA (Usamos 'user' capturado antes de logout)
        if user.is_authenticated:
            from apps.auditoria.services.audit_service import AuditService
            AuditService.log(
                action='LOGOUT',
                description=f'Cierre de sesión: {user.username}',
                user=user,
                request=request
            )
        
        messages.info(request, 'Has cerrado sesión correctamente')
        return redirect('accounts:login')
    
    # También permitir GET para compatibilidad
    def get(self, request):
        return self.post(request)
