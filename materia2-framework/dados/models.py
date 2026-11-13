import uuid
from pathlib import Path

from django.conf import settings
from django.db import models


class Pasta(models.Model):
    """Pasta lógica, guardada só no banco. Pode ter subpastas."""

    dono = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pastas')
    nome = models.CharField('nome', max_length=120)
    mae = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subpastas')
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def caminho(self):
        """Pastas da raiz até esta, para o caminho de navegação."""
        partes, atual = [], self
        while atual is not None:
            partes.append(atual)
            atual = atual.mae
        return list(reversed(partes))


def destino_upload(instancia, nome):
    """No disco o nome é sempre um UUID; o nome original fica no banco."""
    extensao = Path(nome).suffix.lower()
    return f'uploads/{instancia.dono_id}/{uuid.uuid4().hex}{extensao}'


class Arquivo(models.Model):
    dono = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='arquivos')
    pasta = models.ForeignKey(Pasta, on_delete=models.SET_NULL, null=True, blank=True, related_name='arquivos')
    arquivo = models.FileField(upload_to=destino_upload)
    nome_original = models.CharField('nome', max_length=255)
    tamanho = models.PositiveBigIntegerField('tamanho em bytes')
    resumo = models.JSONField('abas, colunas e amostra', default=dict)
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome_original']

    def __str__(self):
        return self.nome_original

    @property
    def extensao(self):
        return Path(self.nome_original).suffix.lower().lstrip('.')

    @property
    def abas(self):
        return self.resumo.get('abas', [])

    @property
    def total_linhas(self):
        return sum(aba.get('linhas', 0) for aba in self.abas)

    def delete(self, *args, **kwargs):
        armazenamento, caminho = self.arquivo.storage, self.arquivo.name
        resultado = super().delete(*args, **kwargs)
        if caminho:
            armazenamento.delete(caminho)
        return resultado
