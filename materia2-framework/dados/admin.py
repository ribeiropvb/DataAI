from django.contrib import admin

from .models import Arquivo, Pasta


@admin.register(Pasta)
class PastaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'dono', 'mae', 'criada_em')
    list_filter = ('dono',)


@admin.register(Arquivo)
class ArquivoAdmin(admin.ModelAdmin):
    list_display = ('nome_original', 'dono', 'pasta', 'tamanho', 'enviado_em')
    list_filter = ('dono',)
    exclude = ('resumo',)
