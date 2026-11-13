from django import forms
from django.contrib.auth import password_validation
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


class EditarUsuarioForm(forms.ModelForm):
    """Edição feita por um administrador.

    A senha só muda se os dois campos forem preenchidos. Quem edita a
    própria conta não pode se desativar nem tirar o próprio perfil de
    administrador; só o root altera o perfil de administrador.
    """

    nova_senha1 = forms.CharField(label='Nova senha', required=False, strip=False, widget=forms.PasswordInput(render_value=False, attrs={'autocomplete': 'new-password'}))
    nova_senha2 = forms.CharField(label='Confirmação da nova senha', required=False, strip=False, widget=forms.PasswordInput(render_value=False, attrs={'autocomplete': 'new-password'}))

    class Meta:
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active')
        labels = {
            'username': 'Usuário',
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'email': 'E-mail',
            'is_staff': 'Administrador',
            'is_active': 'Acesso ativo',
        }
        help_texts = {
            'username': 'Letras, números e @ . + - _ apenas.',
            'is_staff': 'Pode cadastrar e editar usuários.',
            'is_active': 'Desmarque para desativar: a pessoa não consegue mais entrar, mas a conta e os dados ficam guardados.',
        }

    def __init__(self, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['email'].required = True
        proprio = editor is not None and editor.pk == self.instance.pk
        if proprio:
            del self.fields['is_active']
        if proprio or not (editor and editor.is_superuser):
            del self.fields['is_staff']

    def clean(self):
        dados = super().clean()
        s1, s2 = dados.get('nova_senha1'), dados.get('nova_senha2')
        if s1 or s2:
            if s1 != s2:
                self.add_error('nova_senha2', 'As duas senhas não são iguais.')
            else:
                try:
                    password_validation.validate_password(s1, self.instance)
                except forms.ValidationError as erro:
                    self.add_error('nova_senha1', erro)
        return dados

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get('nova_senha1'):
            usuario.set_password(self.cleaned_data['nova_senha1'])
        if commit:
            usuario.save()
        return usuario
