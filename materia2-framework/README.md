# DataAI · site Django (matéria Framework)

Primeira parte: página de login e página inicial (home) protegida.

## O que já existe

- **Tabela própria de usuários:** o modelo `contas.Usuario` (tabela `contas_usuario` no SQLite) substitui o usuário padrão do Django (`AUTH_USER_MODEL`). Herda senha com hash e permissões, com e-mail único, e pode ganhar campos novos sem trocar de tabela.
- **Login** em `/login/`, **home** em `/` (só para quem está logado) e **sair** pelo botão no topo.
- **Cadastro de usuários** em `/usuarios/`, só para administradores (`is_staff`) e root (`is_superuser`): lista quem tem acesso, cadastra pessoas novas e edita os dados pelo ícone de lápis (nome, e-mail, usuário, senha e o campo "Acesso ativo", que desativa a conta sem apagá-la). Só o root edita administradores e muda o perfil de administrador, e ninguém desativa a própria conta.
- **Arquivos** em `/dados/` (app `dados`): envio de vários `.xlsx`, `.xls` ou `.csv` de uma vez (até 20 MB cada, conferidos com pandas antes de salvar), pastas e subpastas para organizar (criar, renomear, excluir e mover arquivos), pré-visualização com abas, colunas e as 10 primeiras linhas, e download. Os arquivos ficam em `media/uploads/<id do usuário>/` com nome aleatório; só o caminho vai para o SQLite, e o download passa por uma view que confere o dono. Cada pessoa vê só os próprios arquivos; **só o root** pode ver e baixar os de todos (filtro "Ver arquivos de"), sem poder alterá-los.
- **Admin** do Django em `/admin/`, para casos fora do site.
- **Identidade visual** do DataAI em tema escuro (tokens da skill `brand-identity`, IBM Plex e o símbolo), em `contas/static/contas/`.

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
| `contas/templates/contas/` | Páginas de login, home e usuários, e o `base.html` comum. |
| `dados/` | App de arquivos: modelos `Pasta` e `Arquivo`, envio, pastas, pré-visualização e download. |
| `dados/leitura.py` | Leitura das planilhas com pandas (validação e resumo para a pré-visualização). |
| `media/` | Arquivos enviados (fora do git). |
