from django import forms
from apps.core.forms.base_form import CoreBaseForm

class ProfileEditForm(CoreBaseForm):
    description = forms.CharField(
        required=False, 
        label="Descripción"
    )
    email = forms.EmailField(
        required=False,
        label="Email"
    )
    password = forms.CharField(
        required=False,
        label="Nueva Contraseña",
        widget=forms.PasswordInput,
        help_text="Dejar en blanco para no cambiar."
    )
    confirm_password = forms.CharField(
        required=False,
        label="Confirmar Contraseña",
        widget=forms.PasswordInput
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password:
            if password != confirm_password:
                self.add_error('confirm_password', "Las contraseñas no coinciden.")
        return cleaned_data
