from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dados/', include('dados.urls')),
    path('', include('contas.urls')),
]
