import io
import shutil
import tempfile

import pandas as pd
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Arquivo, Pasta

MIDIA = tempfile.mkdtemp(prefix='dataai-testes-')


def xlsx(nome='vendas.xlsx', abas=None):
    abas = abas or {'Vendas': pd.DataFrame({'mes': ['jan', 'fev', 'mar'], 'valor': [10, 20, 30]})}
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as escritor:
        for aba, df in abas.items():
            df.to_excel(escritor, sheet_name=aba, index=False)
    return SimpleUploadedFile(nome, buffer.getvalue())


def csv(nome='clientes.csv', texto='id;nome\n1;Ana\n2;Bruno\n'):
    return SimpleUploadedFile(nome, texto.encode('utf-8'))


@override_settings(MEDIA_ROOT=MIDIA)
class Base(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MIDIA, ignore_errors=True)

    def setUp(self):
        U = get_user_model()
        self.root = U.objects.create_superuser('root', 'root@exemplo.com', 'senha-forte-123')
        self.admin = U.objects.create_user('adm', 'adm@exemplo.com', 'senha-forte-123', is_staff=True)
        self.ana = U.objects.create_user('ana', 'ana@exemplo.com', 'senha-forte-123')
        self.bruno = U.objects.create_user('bruno', 'bruno@exemplo.com', 'senha-forte-123')

    def enviar(self, usuario, *arquivos, pasta=None):
        self.client.force_login(usuario)
        dados = {'arquivos': list(arquivos)}
        if pasta:
            dados['pasta'] = pasta.pk
        return self.client.post(reverse('dados:enviar'), dados)


class EnvioTests(Base):
    def test_exige_login(self):
        resposta = self.client.get(reverse('dados:inicio'))
        self.assertEqual(resposta.status_code, 302)

    def test_envia_xlsx_e_guarda_resumo(self):
        resposta = self.enviar(self.ana, xlsx())
        a = Arquivo.objects.get()
        self.assertRedirects(resposta, reverse('dados:arquivo', args=[a.pk]))
        self.assertEqual(a.dono, self.ana)
        self.assertEqual(a.nome_original, 'vendas.xlsx')
        self.assertTrue(a.arquivo.name.startswith(f'uploads/{self.ana.pk}/'))
        self.assertEqual(a.abas[0]['colunas'], ['mes', 'valor'])
        self.assertEqual(a.total_linhas, 3)
        previa = self.client.get(reverse('dados:arquivo', args=[a.pk]))
        self.assertContains(previa, 'fev')

    def test_varios_arquivos_e_varias_abas(self):
        planilha = xlsx(abas={'A': pd.DataFrame({'x': [1]}), 'B': pd.DataFrame({'y': [1, 2]})})
        self.enviar(self.ana, planilha, csv())
        self.assertEqual(Arquivo.objects.count(), 2)
        excel = Arquivo.objects.get(nome_original='vendas.xlsx')
        self.assertEqual([a['nome'] for a in excel.abas], ['A', 'B'])
        texto = Arquivo.objects.get(nome_original='clientes.csv')
        self.assertEqual(texto.abas[0]['colunas'], ['id', 'nome'])

    def test_recusa_tipo_errado_e_arquivo_ilegivel_sem_salvar_nada(self):
        resposta = self.enviar(self.ana, xlsx(), SimpleUploadedFile('nota.pdf', b'%PDF'))
        self.assertEqual(resposta.status_code, 400)
        self.assertContains(resposta, 'tipo não aceito', status_code=400)
        resposta = self.enviar(self.ana, SimpleUploadedFile('falso.xlsx', b'nao sou excel'))
        self.assertContains(resposta, 'não foi possível ler', status_code=400)
        self.assertEqual(Arquivo.objects.count(), 0)

    @override_settings(DADOS_TAMANHO_MAXIMO=100)
    def test_recusa_acima_do_limite(self):
        resposta = self.enviar(self.ana, xlsx())
        self.assertContains(resposta, 'acima do limite', status_code=400)
        self.assertEqual(Arquivo.objects.count(), 0)

    def test_baixar_devolve_o_arquivo_original(self):
        self.enviar(self.ana, csv())
        a = Arquivo.objects.get()
        resposta = self.client.get(reverse('dados:baixar', args=[a.pk]))
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('clientes.csv', resposta['Content-Disposition'])
        self.assertEqual(b''.join(resposta.streaming_content), b'id;nome\n1;Ana\n2;Bruno\n')

    def test_excluir_apaga_do_disco(self):
        self.enviar(self.ana, csv())
        a = Arquivo.objects.get()
        caminho = a.arquivo.path
        self.client.post(reverse('dados:excluir_arquivo', args=[a.pk]))
        self.assertFalse(Arquivo.objects.exists())
        import os
        self.assertFalse(os.path.exists(caminho))


class PastasTests(Base):
    def test_criar_subpasta_enviar_dentro_e_mover(self):
        self.client.force_login(self.ana)
        self.client.post(reverse('dados:nova_pasta'), {'nome': 'Vendas'})
        vendas = Pasta.objects.get(nome='Vendas')
        self.client.post(reverse('dados:nova_pasta'), {'nome': '2026', 'mae': vendas.pk})
        ano = Pasta.objects.get(nome='2026')
        self.assertEqual(ano.mae, vendas)
        self.enviar(self.ana, csv(), pasta=ano)
        a = Arquivo.objects.get()
        self.assertEqual(a.pasta, ano)
        self.client.post(reverse('dados:mover', args=[a.pk]), {'destino': ''})
        a.refresh_from_db()
        self.assertIsNone(a.pasta)
        pagina = self.client.get(reverse('dados:pasta', args=[ano.pk]))
        self.assertContains(pagina, 'Vendas')

    def test_nome_repetido_no_mesmo_lugar(self):
        self.client.force_login(self.ana)
        self.client.post(reverse('dados:nova_pasta'), {'nome': 'Vendas'})
        resposta = self.client.post(reverse('dados:nova_pasta'), {'nome': 'vendas'})
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(Pasta.objects.count(), 1)

    def test_renomear(self):
        p = Pasta.objects.create(dono=self.ana, nome='Antiga')
        self.client.force_login(self.ana)
        self.client.post(reverse('dados:renomear_pasta', args=[p.pk]), {'nome': 'Nova'})
        p.refresh_from_db()
        self.assertEqual(p.nome, 'Nova')

    def test_excluir_pasta_sobe_conteudo(self):
        mae = Pasta.objects.create(dono=self.ana, nome='Mãe')
        filha = Pasta.objects.create(dono=self.ana, nome='Filha', mae=mae)
        neta = Pasta.objects.create(dono=self.ana, nome='Neta', mae=filha)
        self.enviar(self.ana, csv(), pasta=filha)
        self.client.post(reverse('dados:excluir_pasta', args=[filha.pk]))
        self.assertFalse(Pasta.objects.filter(pk=filha.pk).exists())
        neta.refresh_from_db()
        self.assertEqual(neta.mae, mae)
        self.assertEqual(Arquivo.objects.get().pasta, mae)


class AcessoTests(Base):
    def setUp(self):
        super().setUp()
        self.pasta_ana = Pasta.objects.create(dono=self.ana, nome='Particular')
        self.enviar(self.ana, csv(), pasta=self.pasta_ana)
        self.arq_ana = Arquivo.objects.get()
        self.client.logout()

    def urls_de_leitura(self):
        return [
            reverse('dados:arquivo', args=[self.arq_ana.pk]),
            reverse('dados:baixar', args=[self.arq_ana.pk]),
            reverse('dados:pasta', args=[self.pasta_ana.pk]),
        ]

    def test_outro_usuario_nao_ve_nem_altera(self):
        self.client.force_login(self.bruno)
        for url in self.urls_de_leitura():
            self.assertEqual(self.client.get(url).status_code, 404, url)
        self.assertNotContains(self.client.get(reverse('dados:inicio')), 'Particular')
        self.assertEqual(self.client.post(reverse('dados:excluir_arquivo', args=[self.arq_ana.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('dados:mover', args=[self.arq_ana.pk]), {'destino': ''}).status_code, 404)
        self.assertEqual(self.client.post(reverse('dados:excluir_pasta', args=[self.pasta_ana.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('dados:enviar'), {'arquivos': [csv()], 'pasta': self.pasta_ana.pk}).status_code, 404)

    def test_admin_comum_tambem_nao_ve(self):
        self.client.force_login(self.admin)
        for url in self.urls_de_leitura():
            self.assertEqual(self.client.get(url).status_code, 404, url)
        resposta = self.client.get(reverse('dados:inicio') + f'?usuario={self.ana.pk}')
        self.assertNotContains(resposta, 'Particular')
        self.assertNotContains(resposta, 'Ver arquivos de')

    def test_root_ve_e_baixa_de_todos(self):
        self.client.force_login(self.root)
        for url in self.urls_de_leitura():
            self.assertEqual(self.client.get(url).status_code, 200, url)
        raiz_ana = self.client.get(reverse('dados:inicio') + f'?usuario={self.ana.pk}')
        self.assertContains(raiz_ana, 'Particular')
        self.assertContains(raiz_ana, 'Somente leitura')
        self.assertContains(self.client.get(reverse('dados:inicio')), 'Ver arquivos de')

    def test_root_nao_altera_arquivos_dos_outros(self):
        self.client.force_login(self.root)
        self.assertEqual(self.client.post(reverse('dados:excluir_arquivo', args=[self.arq_ana.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('dados:renomear_pasta', args=[self.pasta_ana.pk]), {'nome': 'X'}).status_code, 404)
        self.assertTrue(Arquivo.objects.filter(pk=self.arq_ana.pk).exists())
