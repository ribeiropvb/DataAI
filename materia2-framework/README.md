# DataAI · site Django (matéria Framework)

Primeira parte: página de login e página inicial (home) protegida.

## O que já existe

- **Tabela própria de usuários:** o modelo `contas.Usuario` (tabela `contas_usuario` no SQLite) substitui o usuário padrão do Django (`AUTH_USER_MODEL`). Herda senha com hash e permissões, com e-mail único, e pode ganhar campos novos sem trocar de tabela.
- **Login** em `/login/`, **home** em `/` (só para quem está logado) e **sair** pelo botão no topo.
- **Admin** do Django em `/admin/` para cadastrar usuários.

## Como rodar

```bash
cd materia2-framework
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abra http://127.0.0.1:8000/ e entre com o usuário criado.

## Testes

```bash
python manage.py test contas
```

## Estrutura

| Caminho | Papel |
| --- | --- |
| `config/` | Configurações, URLs principais. |
| `contas/` | App de usuários: modelo `Usuario`, login, logout e home. |
| `contas/templates/contas/` | Páginas `base.html`, `login.html` e `home.html`. |
