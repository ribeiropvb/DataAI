"""Telas de arquivos e pastas.

Regra de acesso: cada pessoa vê e mexe só no que é dela. O root
(superusuário) também pode VER e BAIXAR os arquivos de todos, mas não
altera nada que seja de outra pessoa. Administradores comuns não têm
acesso aos arquivos dos outros.
"""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import EnvioForm, MoverForm, PastaForm
from .models import Arquivo, Pasta


# ---------- acesso ----------

def _visiveis(user, modelo):
    """Objetos que a pessoa pode ver: os próprios, ou todos se for root."""
    if user.is_superuser:
        return modelo.objects.all()
    return modelo.objects.filter(dono=user)


def _pasta_propria(request, pk):
    return get_object_or_404(Pasta, pk=pk, dono=request.user)


def _arquivo_proprio(request, pk):
    return get_object_or_404(Arquivo, pk=pk, dono=request.user)


def _url_pasta(pasta):
    return reverse('dados:pasta', args=[pasta.pk]) if pasta else reverse('dados:inicio')


def _dono_da_raiz(request):
    """Na raiz, o root pode escolher de quem ver os arquivos (?usuario=)."""
    alvo = request.GET.get('usuario')
    if alvo and request.user.is_superuser:
        return get_object_or_404(get_user_model(), pk=alvo)
    return request.user


# ---------- navegação ----------

def _render_pasta(request, dono, pasta, form_envio=None, form_pasta=None, status=200):
    contexto = {
        'dono': dono,
        'pasta': pasta,
        'caminho': pasta.caminho() if pasta else [],
        'subpastas': Pasta.objects.filter(dono=dono, mae=pasta),
        'arquivos': Arquivo.objects.filter(dono=dono, pasta=pasta),
        'pode_editar': dono == request.user,
        'form_envio': form_envio or EnvioForm(),
        'form_pasta': form_pasta or PastaForm(dono=dono, mae=pasta),
    }
    if request.user.is_superuser:
        contexto['usuarios'] = get_user_model().objects.order_by('first_name', 'username')
    return render(request, 'dados/pasta.html', contexto, status=status)


@login_required
def inicio(request):
    return _render_pasta(request, _dono_da_raiz(request), None)


@login_required
def pasta(request, pk):
    p = get_object_or_404(_visiveis(request.user, Pasta), pk=pk)
    return _render_pasta(request, p.dono, p)


# ---------- pastas ----------

@login_required
@require_POST
def nova_pasta(request):
    mae_id = request.POST.get('mae')
    mae = _pasta_propria(request, mae_id) if mae_id else None
    form = PastaForm(request.POST, dono=request.user, mae=mae)
    if form.is_valid():
        nova = form.save()
        messages.success(request, f'Pasta "{nova.nome}" criada.')
        return redirect(_url_pasta(mae))
    return _render_pasta(request, request.user, mae, form_pasta=form, status=400)


@login_required
@require_POST
def renomear_pasta(request, pk):
    p = _pasta_propria(request, pk)
    antigo = p.nome
    form = PastaForm(request.POST, instance=p, dono=request.user, mae=p.mae)
    if form.is_valid():
        form.save()
        messages.success(request, f'Pasta "{antigo}" renomeada para "{p.nome}".')
    else:
        p.nome = antigo
        messages.error(request, ' '.join(form.errors.get('nome', ['Nome inválido.'])))
    return redirect(_url_pasta(p))


def _nome_livre(dono, mae, nome):
    candidato, n = nome, 2
    while Pasta.objects.filter(dono=dono, mae=mae, nome__iexact=candidato).exists():
        candidato = f'{nome} ({n})'
        n += 1
    return candidato


@login_required
@require_POST
def excluir_pasta(request, pk):
    """Apaga a pasta e sobe o conteúdo dela (arquivos e subpastas) um nível."""
    p = _pasta_propria(request, pk)
    mae = p.mae
    Arquivo.objects.filter(pasta=p).update(pasta=mae)
    for sub in list(p.subpastas.all()):
        sub.nome = _nome_livre(request.user, mae, sub.nome)
        sub.mae = mae
        sub.save(update_fields=['nome', 'mae'])
    nome = p.nome
    p.delete()
    lugar = f'a pasta "{mae.nome}"' if mae else 'o início'
    messages.success(request, f'Pasta "{nome}" excluída. O que estava nela foi para {lugar}.')
    return redirect(_url_pasta(mae))


# ---------- arquivos ----------

@login_required
@require_POST
def enviar(request):
    destino_id = request.POST.get('pasta')
    destino = _pasta_propria(request, destino_id) if destino_id else None
    form = EnvioForm(request.POST, request.FILES)
    if not form.is_valid():
        return _render_pasta(request, request.user, destino, form_envio=form, status=400)
    enviados = [
        Arquivo.objects.create(
            dono=request.user,
            pasta=destino,
            arquivo=arq,
            nome_original=arq.name,
            tamanho=arq.size,
            resumo=arq.resumo,
        )
        for arq in form.cleaned_data['arquivos']
    ]
    if len(enviados) == 1:
        messages.success(request, f'Arquivo "{enviados[0].nome_original}" enviado.')
        return redirect('dados:arquivo', pk=enviados[0].pk)
    messages.success(request, f'{len(enviados)} arquivos enviados.')
    return redirect(_url_pasta(destino))


@login_required
def arquivo(request, pk):
    a = get_object_or_404(_visiveis(request.user, Arquivo), pk=pk)
    pode_editar = a.dono == request.user
    try:
        indice = max(0, min(int(request.GET.get('aba', 0)), len(a.abas) - 1))
    except ValueError:
        indice = 0
    return render(request, 'dados/arquivo.html', {
        'arquivo': a,
        'aba': a.abas[indice] if a.abas else None,
        'indice_aba': indice,
        'caminho': a.pasta.caminho() if a.pasta else [],
        'pode_editar': pode_editar,
        'form_mover': MoverForm(dono=a.dono, initial={'destino': a.pasta_id or ''}) if pode_editar else None,
    })


@login_required
def baixar(request, pk):
    a = get_object_or_404(_visiveis(request.user, Arquivo), pk=pk)
    try:
        conteudo = a.arquivo.open('rb')
    except FileNotFoundError:
        raise Http404('Arquivo não encontrado no disco.')
    return FileResponse(conteudo, as_attachment=True, filename=a.nome_original)


@login_required
@require_POST
def mover(request, pk):
    a = _arquivo_proprio(request, pk)
    form = MoverForm(request.POST, dono=request.user)
    if form.is_valid():
        destino_id = form.cleaned_data['destino']
        a.pasta = _pasta_propria(request, destino_id) if destino_id else None
        a.save(update_fields=['pasta'])
        lugar = f'a pasta "{a.pasta.nome}"' if a.pasta else 'o início'
        messages.success(request, f'"{a.nome_original}" movido para {lugar}.')
    return redirect('dados:arquivo', pk=a.pk)


@login_required
@require_POST
def excluir_arquivo(request, pk):
    a = _arquivo_proprio(request, pk)
    pasta_de_volta, nome = a.pasta, a.nome_original
    a.delete()
    messages.success(request, f'Arquivo "{nome}" excluído.')
    return redirect(_url_pasta(pasta_de_volta))
