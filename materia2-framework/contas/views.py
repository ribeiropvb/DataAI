from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EditarUsuarioForm, NovoUsuarioForm
from .models import Usuario


def _e_admin(user):
    return user.is_active and (user.is_staff or user.is_superuser)


admin_requerido = user_passes_test(_e_admin)


@login_required
def home(request):
    return render(request, 'contas/home.html')


@login_required
@admin_requerido
def usuarios(request):
    lista = Usuario.objects.order_by('-is_active', 'first_name', 'username')
    for u in lista:
        u.editavel = pode_editar(request.user, u)
    return render(request, 'contas/usuarios.html', {'usuarios': lista})


@login_required
@admin_requerido
def novo_usuario(request):
    pode_criar_admin = request.user.is_superuser
    form = NovoUsuarioForm(request.POST or None, pode_criar_admin=pode_criar_admin)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        messages.success(request, f'Usuário {usuario.username} cadastrado. Ele já pode entrar.')
        return redirect('contas:usuarios')
    return render(request, 'contas/usuario_novo.html', {'form': form})


def pode_editar(editor, alvo):
    """Root edita qualquer um; admin edita a si mesmo e usuários comuns."""
    if editor.is_superuser or editor.pk == alvo.pk:
        return True
    return not (alvo.is_staff or alvo.is_superuser)


@login_required
@admin_requerido
def editar_usuario(request, pk):
    alvo = get_object_or_404(Usuario, pk=pk)
    if not pode_editar(request.user, alvo):
        raise PermissionDenied
    form = EditarUsuarioForm(request.POST or None, instance=alvo, editor=request.user)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        if usuario.pk == request.user.pk and form.cleaned_data.get('nova_senha1'):
            update_session_auth_hash(request, usuario)
        situacao = '' if usuario.is_active else ' O acesso está desativado.'
        messages.success(request, f'Dados de {usuario.username} salvos.{situacao}')
        return redirect('contas:usuarios')
    return render(request, 'contas/usuario_editar.html', {'form': form, 'alvo': alvo})
