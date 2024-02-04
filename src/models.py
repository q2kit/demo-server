from django.db import models
from django.contrib.auth.models import User

from .funks import gen_secret


class Project(models.Model):
    domain = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    secret = models.CharField(max_length=255, default=gen_secret)

    def __str__(self) -> str:
        return self.domain
