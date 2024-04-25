from django.db import models
from django.contrib.auth.models import User
from django.core.cache import cache

from .funks import (
    gen_secret,
    gen_nginx_conf,
    gen_default_nginx_conf as reset_default_nginx_conf,
)

import threading


class Project(models.Model):
    domain = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'is_superuser': False},
    )
    secret = models.CharField(max_length=255, default=gen_secret)

    def __str__(self) -> str:
        return self.domain

    def connect(self, port: int) -> None:
        gen_nginx_conf(self.domain, port)
        cache.set(self.domain, True, 120)

        def disconnect_task():
            if not cache.get(self.domain):
                reset_default_nginx_conf(self.domain)
            cache.delete(self.domain)

        threading.Timer(120, disconnect_task).start()

    def disconnect(self) -> None:
        reset_default_nginx_conf(self.domain)

    def keep_alive_connection(self) -> None:
        cache.set(self.domain, True, 120)
