from pathlib import Path

from django import forms
from django.conf import settings
from django.template.defaultfilters import filesizeformat

from .leitura import EXTENSOES, ArquivoIlegivel, resumir
from .models import Pasta


class VariosArquivosInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class VariosArquivosField(forms.FileField):
    widget = VariosArquivosInput

    def clean(self, dados, inicial=None):
        if isinstance(dados, (list, tuple)):
            return [super(VariosArquivosField, self).clean(d, inicial) for d in dados]
        return [super().clean(dados, inicial)]


class EnvioForm(forms.Form):
    arquivos = VariosArquivosField(
        label='Arquivos',
        widget=VariosArquivosInput(attrs={'accept': ','.join(sorted(EXTENSOES))}),
        error_messages={'required': 'Escolha pelo menos um arquivo.'},
    )

    def clean_arquivos(self):
        arquivos = self.cleaned_data['arquivos']
        limite = settings.DADOS_TAMANHO_MAXIMO
        erros, validos = [], []
        for arq in arquivos:
            extensao = Path(arq.name).suffix.lower()
            if extensao not in EXTENSOES:
                erros.append(f'{arq.name}: tipo não aceito (use .xlsx, .xls ou .csv).')
                continue
            if arq.size > limite:
                erros.append(f'{arq.name}: tem {filesizeformat(arq.size)}, acima do limite de {filesizeformat(limite)}.')
                continue
            try:
                arq.resumo = resumir(arq)
            except ArquivoIlegivel:
                erros.append(f'{arq.name}: não foi possível ler o arquivo. Confira se ele abre no Excel.')
                continue
            validos.append(arq)
        if erros:
            raise forms.ValidationError(erros)
        return validos


class PastaForm(forms.ModelForm):
    class Meta:
        model = Pasta
        fields = ('nome',)
        labels = {'nome': 'Nome da pasta'}

    def __init__(self, *args, dono, mae=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.dono, self.mae = dono, mae
        self.fields['nome'].widget.attrs.update({'placeholder': 'Ex.: Vendas 2026', 'autocomplete': 'off'})

    def clean_nome(self):
        nome = self.cleaned_data['nome'].strip()
        if not nome:
            raise forms.ValidationError('Dê um nome à pasta.')
        repetidas = Pasta.objects.filter(dono=self.dono, mae=self.mae, nome__iexact=nome)
        if self.instance.pk:
            repetidas = repetidas.exclude(pk=self.instance.pk)
        if repetidas.exists():
            raise forms.ValidationError('Já existe uma pasta com esse nome aqui.')
        return nome

    def save(self, commit=True):
        pasta = super().save(commit=False)
        pasta.dono = self.dono
        if not pasta.pk:
            pasta.mae = self.mae
        if commit:
            pasta.save()
        return pasta


class MoverForm(forms.Form):
    destino = forms.ChoiceField(label='Mover para')

    def __init__(self, *args, dono, **kwargs):
        super().__init__(*args, **kwargs)
        opcoes = [('', 'Início (sem pasta)')]

        def adicionar(mae, nivel):
            for pasta in Pasta.objects.filter(dono=dono, mae=mae).order_by('nome'):
                opcoes.append((str(pasta.pk), f'{"— " * nivel}{pasta.nome}'))
                adicionar(pasta, nivel + 1)

        adicionar(None, 1)
        self.fields['destino'].choices = opcoes
        self.fields['destino'].required = False
