from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Usuario


class NovoUsuarioForm(UserCreationForm):
    """Cadastro feito por um administrador.

    Só um superusuário pode criar outro administrador; para os demais
    admins o campo some e o novo usuário é sempre comum.
    """

    is_staff = forms.BooleanField(
        label='Administrador',
        required=False,
        help_text='Pode cadastrar usuários e bloquear ou reativar acessos.',
    )

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email', 'is_staff')
        labels = {
            'username': 'Usuário',
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'email': 'E-mail',
        }

    def __init__(self, *args, pode_criar_admin=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['email'].required = True
        if not pode_criar_admin:
            del self.fields['is_staff']
