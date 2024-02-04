from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from .funks import create_user_profile


@receiver(post_save, sender=User)
def create_user_profile_signal(sender, instance, created, **kwargs):
    if created:
        create_user_profile(instance.username)
