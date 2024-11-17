import os

from django.core.management.base import BaseCommand

from src.models import Project, User
from src.funks import create_user_profile, gen_502_page, gen_default_nginx_conf


class Command(BaseCommand):
    help = "Generate nginx config, ssh config"

    def handle(self, *args, **options):  # noqa: U100
        # Create user's profile
        for user in User.objects.filter(is_superuser=False):
            try:
                create_user_profile(user.username)
            except Exception as e:
                print("~" * 50)
                print(f"Error: {e}")
                print("User: ", user.username)

        # Create project's config
        HTTP_HOST = os.getenv('HTTP_HOST')
        for project in Project.objects.all():
            try:
                subdomain = project.domain.split('.')[0]
                project.domain = f"{subdomain}.{HTTP_HOST}"
                project.save()
                gen_502_page(project.domain)
                gen_default_nginx_conf(project.domain)
            except Exception as e:
                print("~" * 50)
                print(f"Error: {e}")
                print("Project: ", project.domain)
