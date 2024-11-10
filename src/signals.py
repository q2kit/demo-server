from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from .funks import (
    create_user_profile,
    delete_user_profile,
    gen_502_page,
    gen_default_nginx_conf,
    remove_502_page,
    remove_nginx_conf,
)
from .models import Project


@receiver(post_save, sender=User)
def create_user_profile_signal(sender, instance, created, **kwargs):  # noqa: U100
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
def delete_user_profile_signal(sender, instance, **kwargs):  # noqa: U100
    delete_user_profile(instance.username)


@receiver(post_save, sender=Project)
def save_project_signal(sender, instance, created, **kwargs):  # noqa: U100
    gen_502_page(instance.domain)
    gen_default_nginx_conf(instance.domain)


@receiver(post_delete, sender=Project)
def delete_project_signal(sender, instance, **kwargs):  # noqa: U100
    remove_502_page(instance.domain)
    remove_nginx_conf(instance.domain)
