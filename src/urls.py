"""
URL configuration for src project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from src.views import (
    signup,
    get_connection_info,
    get_key_file,
    connect,
    disconnect,
    keep_alive_connection,
)
from django.http import HttpResponse
from django.shortcuts import redirect

admin.site.site_header = "DEMOS"
admin.site.site_title = "DEMOS"
admin.site.index_title = "Welcome to Demos"
admin.site.site_url = None

urlpatterns = [
    path('health', lambda _: HttpResponse('OK')),
    path('admin/signup/', signup, name='signup'),
    path('admin/', admin.site.urls),
    path('get_connection_info/', get_connection_info),
    path('get_key_file/', get_key_file),
    path('connect/', connect),
    path('disconnect/', disconnect),
    path('keep_alive/', keep_alive_connection),
    path('', lambda _: redirect('admin/')),
]
