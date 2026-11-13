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

    def test_bloquear_e_reativar(self):
        self.client.force_login(self.admin)
        url = reverse('contas:alternar_acesso', args=[self.comum.pk])
        self.client.post(url)
        self.comum.refresh_from_db()
        self.assertFalse(self.comum.is_active)
        self.client.post(url)
        self.comum.refresh_from_db()
        self.assertTrue(self.comum.is_active)

    def test_nao_bloqueia_a_si_nem_admin_sem_ser_root(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('contas:alternar_acesso', args=[self.admin.pk]))
        resposta = self.client.post(reverse('contas:alternar_acesso', args=[self.root.pk]))
        self.assertEqual(resposta.status_code, 403)
        self.admin.refresh_from_db()
        self.root.refresh_from_db()
        self.assertTrue(self.admin.is_active and self.root.is_active)

    def test_bloqueio_exige_post(self):
        self.client.force_login(self.admin)
        resposta = self.client.get(reverse('contas:alternar_acesso', args=[self.comum.pk]))
        self.assertEqual(resposta.status_code, 405)
