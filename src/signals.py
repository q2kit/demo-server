from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from .funks import create_user_profile, delete_user_profile
from .models import Project


@receiver(post_save, sender=User)
def create_user_profile_signal(sender, instance, created, **kwargs):
    if created:
        create_user_profile(instance.username)

        # grant permission
        content_type = ContentType.objects.get_for_models(Project)
        permissions = (
            "add_project",
            "change_project",
            "delete_project",
        )
        permission = Permission.objects.filter(
            codename__in=permissions,
            content_type__in=content_type.values(),
        )
        instance.user_permissions.set(permission)
        instance.is_active = True
        instance.is_staff = True
        instance.save()


@receiver(post_delete, sender=User)
def delete_user_profile_signal(sender, instance, **kwargs):
    delete_user_profile(instance.username)
