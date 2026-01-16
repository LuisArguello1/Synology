from apps.core.forms import CoreBaseForm
from django import forms
from django.contrib.auth import authenticate

class LoginForm(CoreBaseForm):
    """
    Formulario de login que autentica contra Synology.
    """
    username = forms.CharField(
        label='Usuario',
        max_length=150,
        widget=forms.TextInput(attrs={
            'autofocus': True,
            'autocomplete': 'username',
            'placeholder': 'Usuario de Synology'
        })
    )
    
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'current-password',
            'placeholder': 'Contraseña'
        })
    )
    
    remember_me = forms.BooleanField(
        label='Recordarme',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'w-3.5 h-3.5 text-indigo-600 border-gray-300 rounded-sm focus:ring-indigo-500 focus:ring-1'})
    )
    
    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user_cache = None
    
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        
        if username and password:
            # Autenticar contra Synology usando el backend custom
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password
            )
            
            if self.user_cache is None:
                raise forms.ValidationError(
                    'Error de autenticación. '
                    'Verifica usuario/contraseña o la conexión con el NAS.'
                )
            elif not self.user_cache.is_active:
                raise forms.ValidationError(
                    'Esta cuenta está inactiva.'
                )
        
        return cleaned_data
    
    def get_user(self):
        return self.user_cache
