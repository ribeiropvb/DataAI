from django.urls import path

from . import views

app_name = 'dados'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('pastas/<int:pk>/', views.pasta, name='pasta'),
    path('pastas/nova/', views.nova_pasta, name='nova_pasta'),
    path('pastas/<int:pk>/renomear/', views.renomear_pasta, name='renomear_pasta'),
    path('pastas/<int:pk>/excluir/', views.excluir_pasta, name='excluir_pasta'),
    path('enviar/', views.enviar, name='enviar'),
    path('arquivos/<int:pk>/', views.arquivo, name='arquivo'),
    path('arquivos/<int:pk>/baixar/', views.baixar, name='baixar'),
    path('arquivos/<int:pk>/mover/', views.mover, name='mover'),
    path('arquivos/<int:pk>/excluir/', views.excluir_arquivo, name='excluir_arquivo'),
]
