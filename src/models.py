import threading
from datetime import datetime

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import models
from django.utils.timezone import now

from src.env import KEEP_ALIVE_TIMEOUT
from src.funks import gen_default_nginx_conf as reset_default_nginx_conf
from src.funks import gen_nginx_conf, gen_secret_key


class Project(models.Model):
    domain: str = models.CharField(max_length=255, unique=True)
    user: User = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={
            "is_superuser": False,
            "is_active": True,
        },
        related_name="projects",
    )
    secret_key: str = models.CharField(max_length=255, default=gen_secret_key)
    created_at: datetime = models.DateTimeField(auto_now_add=True)
    updated_at: datetime = models.DateTimeField(auto_now=True)
    last_connected_at: datetime = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.domain

    def connect(self, port: int) -> None:
        gen_nginx_conf(self.domain, port)
        cache.set(self.domain, True, KEEP_ALIVE_TIMEOUT)

        def disconnect_task():
            if not cache.get(self.domain):
                reset_default_nginx_conf(self.domain)
            cache.delete(self.domain)

        threading.Timer(KEEP_ALIVE_TIMEOUT, disconnect_task).start()

        self.last_connected_at = now()
        self.save(update_fields=["last_connected_at"])

    def disconnect(self) -> None:
        reset_default_nginx_conf(self.domain)

    def keep_alive_connection(self) -> None:
        cache.set(self.domain, True, KEEP_ALIVE_TIMEOUT)
