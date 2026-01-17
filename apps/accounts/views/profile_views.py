from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.usuarios.services.user_service import UserService
import logging

logger = logging.getLogger(__name__)

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Mi Perfil'
        
        # Breadcrumbs
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': 'core:dashboard'},
            {'name': 'Mi Perfil'}
        ]
        
        # Fetch Real Data from Synology
        try:
            service = UserService()
            # Asumimos que el username de Django coincide con Synology
            current_user = self.request.user.username
            
            # Obtener datos usando el servicio existente
            user_data = service.get_user(current_user)
            
            if user_data:
                context['syno_user'] = user_data
            else:
                context['error'] = "No se pudieron obtener los datos de Synology."
                
        except Exception as e:
            logger.error(f"Error fetching profile: {e}")
            context['error'] = f"Error de conexión: {str(e)}"
            
        return context

from django.views.generic import FormView
from django.urls import reverse_lazy
from django.contrib import messages
from .auth_views import LoginView
from ..forms.profile_form import ProfileEditForm

class ProfileEditView(LoginRequiredMixin, FormView):
    template_name = 'accounts/profile_edit.html'
    form_class = ProfileEditForm
    success_url = reverse_lazy('accounts:profile')

    def get_initial(self):
        service = UserService()
        user_data = service.get_user(self.request.user.username)
        if user_data:
            return {
                'description': user_data.get('description', ''),
                'email': user_data.get('email', '')
            }
        return {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Editar Perfil'
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': 'core:dashboard'},
            {'name': 'Mi Perfil', 'url': 'accounts:profile'},
            {'name': 'Editar'}
        ]
        
        # Check permissions for template
        service = UserService()
        user_data = service.get_user(self.request.user.username)
        if user_data:
            context['syno_user'] = user_data
            
        return context

    def form_valid(self, form):
        data = form.cleaned_data
        username = self.request.user.username
        service = UserService()
        
        # Prepare Synology update params
        update_params = {
            'description': data.get('description', ''),
            'email': data.get('email', '')
        }
        
        # Update password only if provided
        if data.get('password'):
            # Double check permission (security layer)
            user_data = service.get_user(username)
            if user_data and user_data.get('cannot_change_password'):
                messages.error(self.request, 'No tienes permisos para cambiar tu contraseña.')
                return self.form_invalid(form)
                
            update_params['password'] = data.get('password')

        # Execute Update
        try:
            result = service.update_user(username, update_params)
            
            if result.get('success'):
                messages.success(self.request, 'Perfil actualizado correctamente.')
                
                # Log Audit
                from apps.auditoria.services.audit_service import AuditService
                AuditService.log(
                    action='UPDATE_PROFILE',
                    description=f'Usuario {username} actualizó su perfil.',
                    user=self.request.user,
                    request=self.request,
                    details={k: '***' if k == 'password' else v for k, v in update_params.items()}
                )
                
                return super().form_valid(form)
            else:
                messages.error(self.request, f"Error al actualizar en NAS: {result}")
                return self.form_invalid(form)
                
        except Exception as e:
            messages.error(self.request, f"Excepción actualizando perfil: {e}")
            return self.form_invalid(form)
