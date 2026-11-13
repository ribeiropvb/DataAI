from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import NovoUsuarioForm
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


@login_required
@admin_requerido
@require_POST
def alternar_acesso(request, pk):
    alvo = get_object_or_404(Usuario, pk=pk)
    if alvo == request.user:
        messages.error(request, 'Você não pode bloquear o seu próprio acesso.')
        return redirect('contas:usuarios')
    if (alvo.is_superuser or alvo.is_staff) and not request.user.is_superuser:
        raise PermissionDenied
    alvo.is_active = not alvo.is_active
    alvo.save(update_fields=['is_active'])
    if alvo.is_active:
        messages.success(request, f'Acesso de {alvo.username} reativado.')
    else:
        messages.success(request, f'Acesso de {alvo.username} bloqueado.')
    return redirect('contas:usuarios')
