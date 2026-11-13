from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'contas'

urlpatterns = [
    path('', views.home, name='home'),
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='contas/login.html',
            redirect_authenticated_user=True,
        ),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('usuarios/', views.usuarios, name='usuarios'),
    path('usuarios/novo/', views.novo_usuario, name='novo_usuario'),
    path('usuarios/<int:pk>/acesso/', views.alternar_acesso, name='alternar_acesso'),
]
