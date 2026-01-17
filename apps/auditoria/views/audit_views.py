from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from ..models import AuditLog

class AuditListView(LoginRequiredMixin, ListView):
    model = AuditLog
    template_name = 'auditoria/audit_list.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q')
        
        if q:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(action__icontains=q) |
                Q(description__icontains=q) |
                Q(user__username__icontains=q) |
                Q(ip_address__icontains=q)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pass search param to template
        context['q'] = self.request.GET.get('q', '')
        
        # Breadcrumbs
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': 'core:dashboard'},
            {'name': 'Auditoría', 'url': 'auditoria:list'}
        ]
        context['page_title'] = 'Logs de Auditoría'
        
        # Sidebar integration is now handled by context_processor
        
        return context




class AuditDetailView(LoginRequiredMixin, DetailView):
    model = AuditLog
    template_name = 'auditoria/audit_detail.html'
    context_object_name = 'log'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Breadcrumbs
        context['breadcrumbs'] = [
            {'name': 'Dashboard', 'url': 'core:dashboard'},
            {'name': 'Auditoría', 'url': 'auditoria:list'},
            {'name': f'Registro #{self.object.id}'}
        ]
        context['page_title'] = 'Detalle de Auditoría'
        
        return context
