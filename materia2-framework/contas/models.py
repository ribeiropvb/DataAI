from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Tabela própria de usuários do site (contas_usuario no SQLite).

    Herda login, senha com hash e permissões do Django, e permite
    acrescentar campos do projeto no futuro sem trocar de tabela.
    """

    email = models.EmailField('e-mail', unique=True)

    class Meta:
        verbose_name = 'usuário'
        verbose_name_plural = 'usuários'

    def __str__(self):
        return self.get_full_name() or self.username
