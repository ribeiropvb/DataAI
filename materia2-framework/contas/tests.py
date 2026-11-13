from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class LoginHomeTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username='ana', email='ana@exemplo.com', password='senha-forte-123'
        )

    def test_home_exige_login(self):
        resposta = self.client.get(reverse('contas:home'))
        self.assertRedirects(resposta, reverse('contas:login') + '?next=/')

    def test_login_valido_vai_para_home(self):
        resposta = self.client.post(
            reverse('contas:login'),
            {'username': 'ana', 'password': 'senha-forte-123'},
        )
        self.assertRedirects(resposta, reverse('contas:home'))
        self.assertContains(self.client.get(reverse('contas:home')), 'Olá, ana')

    def test_login_invalido_mostra_erro(self):
        resposta = self.client.post(
            reverse('contas:login'), {'username': 'ana', 'password': 'errada'}
        )
        self.assertContains(resposta, 'usuário ou senha incorretos')

    def test_logout_volta_para_login(self):
        self.client.force_login(self.usuario)
        resposta = self.client.post(reverse('contas:logout'))
        self.assertRedirects(resposta, reverse('contas:login'))

    def test_tabela_propria(self):
        self.assertEqual(get_user_model()._meta.db_table, 'contas_usuario')


class CadastroUsuariosTests(TestCase):
    dados = {
        'username': 'bruno',
        'first_name': 'Bruno',
        'last_name': 'Lima',
        'email': 'bruno@exemplo.com',
        'password1': 'Analise#2026x',
        'password2': 'Analise#2026x',
    }

    def setUp(self):
        Usuario = get_user_model()
        self.root = Usuario.objects.create_superuser('root', 'root@exemplo.com', 'senha-forte-123')
        self.admin = Usuario.objects.create_user('adm', 'adm@exemplo.com', 'senha-forte-123', is_staff=True)
        self.comum = Usuario.objects.create_user('ana', 'ana@exemplo.com', 'senha-forte-123')

    def test_usuario_comum_nao_acessa(self):
        self.client.force_login(self.comum)
        for nome in ('contas:usuarios', 'contas:novo_usuario'):
            resposta = self.client.get(reverse(nome))
            self.assertEqual(resposta.status_code, 302)
        self.assertNotContains(self.client.get(reverse('contas:home')), 'href="/usuarios/"')

    def test_admin_cadastra_e_novo_usuario_entra(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(reverse('contas:novo_usuario'), self.dados)
        self.assertRedirects(resposta, reverse('contas:usuarios'))
        novo = get_user_model().objects.get(username='bruno')
        self.assertFalse(novo.is_staff)
        self.client.logout()
        self.assertTrue(self.client.login(username='bruno', password='Analise#2026x'))

    def test_admin_comum_nao_cria_admin(self):
        self.client.force_login(self.admin)
        self.assertNotContains(self.client.get(reverse('contas:novo_usuario')), 'id_is_staff')
        self.client.post(reverse('contas:novo_usuario'), {**self.dados, 'is_staff': 'on'})
        self.assertFalse(get_user_model().objects.get(username='bruno').is_staff)

    def test_root_cria_admin(self):
        self.client.force_login(self.root)
        self.client.post(reverse('contas:novo_usuario'), {**self.dados, 'is_staff': 'on'})
        self.assertTrue(get_user_model().objects.get(username='bruno').is_staff)

    def test_email_repetido_e_senhas_diferentes(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(
            reverse('contas:novo_usuario'),
            {**self.dados, 'email': 'ana@exemplo.com', 'password2': 'outra'},
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username='bruno').exists())

    def _editar(self, alvo, **mudancas):
        dados = {
            'username': alvo.username,
            'first_name': alvo.first_name or 'Nome',
            'last_name': alvo.last_name,
            'email': alvo.email,
            'is_active': 'on',
        }
        dados.update(mudancas)
        dados = {k: v for k, v in dados.items() if v is not None}
        return self.client.post(reverse('contas:editar_usuario', args=[alvo.pk]), dados)

    def test_lista_mostra_icone_de_edicao(self):
        self.client.force_login(self.admin)
        resposta = self.client.get(reverse('contas:usuarios'))
        self.assertContains(resposta, reverse('contas:editar_usuario', args=[self.comum.pk]))
        self.assertNotContains(resposta, reverse('contas:editar_usuario', args=[self.root.pk]))

    def test_admin_edita_dados(self):
        self.client.force_login(self.admin)
        resposta = self._editar(self.comum, first_name='Ana Paula', email='anapaula@exemplo.com')
        self.assertRedirects(resposta, reverse('contas:usuarios'))
        self.comum.refresh_from_db()
        self.assertEqual((self.comum.first_name, self.comum.email), ('Ana Paula', 'anapaula@exemplo.com'))

    def test_desativar_e_reativar(self):
        self.client.force_login(self.admin)
        self._editar(self.comum, is_active=None)
        self.comum.refresh_from_db()
        self.assertFalse(self.comum.is_active)
        self.client.logout()
        self.assertFalse(self.client.login(username='ana', password='senha-forte-123'))
        self.client.force_login(self.admin)
        self._editar(self.comum)
        self.comum.refresh_from_db()
        self.assertTrue(self.comum.is_active)

    def test_trocar_senha(self):
        self.client.force_login(self.admin)
        self._editar(self.comum, nova_senha1='Outra#Senha99', nova_senha2='Outra#Senha99')
        self.client.logout()
        self.assertTrue(self.client.login(username='ana', password='Outra#Senha99'))

    def test_senha_em_branco_mantem_e_diferente_recusa(self):
        self.client.force_login(self.admin)
        self._editar(self.comum)
        resposta = self._editar(self.comum, nova_senha1='Outra#Senha99', nova_senha2='Diferente#99')
        self.assertEqual(resposta.status_code, 200)
        self.client.logout()
        self.assertTrue(self.client.login(username='ana', password='senha-forte-123'))

    def test_admin_nao_edita_admin_nem_root(self):
        self.client.force_login(self.admin)
        self.assertEqual(self._editar(self.root, is_active=None).status_code, 403)
        self.root.refresh_from_db()
        self.assertTrue(self.root.is_active)

    def test_nao_desativa_a_si_mesmo(self):
        self.client.force_login(self.admin)
        resposta = self.client.get(reverse('contas:editar_usuario', args=[self.admin.pk]))
        self.assertNotContains(resposta, 'id_is_active')
        self._editar(self.admin, is_active=None)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active and self.admin.is_staff)

    def test_so_root_muda_perfil_admin(self):
        self.client.force_login(self.admin)
        self._editar(self.comum, is_staff='on')
        self.comum.refresh_from_db()
        self.assertFalse(self.comum.is_staff)
        self.client.force_login(self.root)
        self._editar(self.comum, is_staff='on')
        self.comum.refresh_from_db()
        self.assertTrue(self.comum.is_staff)
