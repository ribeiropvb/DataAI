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
        self.assertContains(resposta, 'Usuário ou senha incorretos')

    def test_logout_volta_para_login(self):
        self.client.force_login(self.usuario)
        resposta = self.client.post(reverse('contas:logout'))
        self.assertRedirects(resposta, reverse('contas:login'))

    def test_tabela_propria(self):
        self.assertEqual(get_user_model()._meta.db_table, 'contas_usuario')
