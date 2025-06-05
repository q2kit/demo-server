import os
import re
import secrets
import socket

import jinja2
import requests
import rsa
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from src.env import (
    CLOUDFLARE_API_URL,
    CLOUDFLARE_SECRET_KEY,
    CLOUDFLARE_SITE_KEY,
    HTTP_HOST,
)


def domain_validator(domain):
    """
    Validates subdomain string
    :param subdomain: string
    :return: True if valid, False if not
    """
    domain = domain.strip().lower()
    postfix = f'.{HTTP_HOST}'

    if not domain.endswith(postfix):
        raise ValidationError(f'Invalid domain. Must end with {postfix}')

    subdomain = domain.replace(postfix, '')

    for item in getattr(settings, 'SUBDOMAIN_EXCLUDE_LIST', []):
        if (
            subdomain == item
            or isinstance(item, re.Pattern)
            and item.match(subdomain)
        ):
            raise ValidationError(
                f'Invalid subdomain. "{subdomain}" is not allowed.'
            )

    # min: 2, max: 63, a-z, 0-9, -, no leading or trailing -
    if not re.match(r'^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$', subdomain):
        raise ValidationError(
            'Invalid subdomain. Must be between 2 and 63 characters long, '
            'contain only lowercase letters, numbers, and hyphens, '
            'and start and end with a letter or number.'
        )

    return domain


def gen_secret_key():
    """
    Generates a secret_key string
    :return: string
    """

    return secrets.token_urlsafe(32)


def get_available_port(project_id: int):
    """
    Generates a port number that is not in use on the host
    :return: int
    """

    for port in range(20000, 30001):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        if result != 0 and not cache.get(port):
            cache.set(port, project_id, 30)  # 30 seconds
            return port

    return None


def gen_nginx_conf(domain, port=None):
    """
    Generates nginx config file
    :param domain: string
    :param port: int
    """
    TPL_PATH = 'src/templates/nginx.conf-tpl'
    with open(TPL_PATH, 'r') as f:
        tpl_str = f.read()
    tpl = jinja2.Template(tpl_str)
    conf_str = tpl.render(domain=domain, port=port)
    with open(f'/etc/nginx/sites/{domain}.conf', 'w') as f:
        f.write(conf_str)
    os.system('service nginx reload')


def remove_nginx_conf(domain):
    """
    Removes the nginx config file
    :param domain: string
    """
    try:
        os.remove(f'/etc/nginx/sites/{domain}.conf')
        os.system('service nginx reload')
    except FileNotFoundError:
        pass


def gen_default_nginx_conf(domain):
    """
    Generates a default page
    :param domain: string
    """
    gen_nginx_conf(domain=domain, port=None)


def gen_502_page(domain):
    """
    Generates a 502 error page
    :param domain: string
    """
    TPL_PATH = 'src/templates/502.html-tpl'
    with open(TPL_PATH, 'r') as f:
        tpl_str = f.read()
    tpl = jinja2.Template(tpl_str)
    conf_str = tpl.render(domain=domain, HOST=HTTP_HOST)
    if not os.path.exists('/var/www/demos/502'):
        os.makedirs('/var/www/demos/502')
    with open(f'/var/www/demos/502/{domain}.html', 'w') as f:
        f.write(conf_str)

    os.system('service nginx reload')


def remove_502_page(domain):
    """
    Removes the 502 error page
    :param domain: string
    """
    try:
        os.remove(f'/var/www/demos/502/{domain}.html')
        os.system('service nginx reload')
    except FileNotFoundError:
        pass


def gen_key_pair(username) -> tuple:
    """
    Generates a key pair
    :param username: string
    :return: tuple(public_key_path: string, private_key_path: string)
    """

    DIR = f'/home/{username}/.ssh'

    _, private_key = rsa.newkeys(2048)
    private_key_path = f'{DIR}/private_key.pem'
    with open(private_key_path, 'wb') as f:
        f.write(private_key.save_pkcs1())
    os.chmod(private_key_path, 0o600)
    public_key_path = f'{DIR}/authorized_keys'
    os.system(f'ssh-keygen -y -f {private_key_path} > {public_key_path}')
    os.system(f'chown {username}:{username} {public_key_path}')
    os.chmod(public_key_path, 0o600)

    return public_key_path, private_key_path


def remove_key_pair(username):
    """
    Removes the key pair
    :param username: string
    :return: None
    """
    DIR = f'/home/{username}/.ssh'
    if os.path.exists(f'{DIR}/authorized_keys'):
        os.remove(f'{DIR}/authorized_keys')
    if os.path.exists(f'{DIR}/private_key.pem'):
        os.remove(f'{DIR}/private_key.pem')


def create_user_profile(username):
    """
    Creates a user without password and creates a .ssh directory
    :param username: string
    :return: None
    """

    if username in settings.USERNAME_EXCLUDE_LIST:
        return

    os.system(f'useradd -m -p ! {username}')
    os.system(f'mkdir /home/{username}/.ssh')
    os.system(f'chown {username}:{username} /home/{username}/.ssh')
    os.system(f'chmod 700 /home/{username}/.ssh')
    gen_sshd_conf(username)


def delete_user_profile(username):
    """
    Deletes a user and removes the .ssh directory
    :param username: string
    :return: None
    """

    if username in settings.USERNAME_EXCLUDE_LIST:
        return

    os.system(f'userdel -r {username}')
    remove_sshd_conf(username)


def gen_sshd_conf(username):
    """
    Generates sshd config file
    :param username: string
    :return: string
    """
    TPL_PATH = 'src/templates/sshd.user.conf-tpl'
    with open(TPL_PATH, 'r') as f:
        tpl_str = f.read()
    tpl = jinja2.Template(tpl_str)
    conf_str = tpl.render(username=username)
    CONF_FILE = f'/etc/ssh/sshd_config.d/user.d/{username}.conf'
    with open(CONF_FILE, 'w') as f:
        f.write(conf_str)
    os.system(f'chown root:root {CONF_FILE}')
    os.system(f'chmod 600 {CONF_FILE}')
    os.system('service ssh reload')


def remove_sshd_conf(username):
    """
    Removes the sshd config file
    :param username: string
    :return: None
    """
    CONF_FILE = f'/etc/ssh/sshd_config.d/user.d/{username}.conf'
    try:
        os.remove(CONF_FILE)
        os.system('service ssh reload')
    except FileNotFoundError:
        pass


def username_validator(username):
    """
    Validates username string
    :param username: string
    :return: True if valid, False if not
    """

    if (
        username
        and get_user_model().objects.filter(username__iexact=username).exists()
    ):  # noqa
        raise ValidationError(
            {
                "username": _("This username is already in use."),
            }
        )
    if username in settings.USERNAME_EXCLUDE_LIST:
        raise ValidationError({"username": _("This username is not allowed.")})

    if not re.match(r'^[a-zA-Z][a-zA-Z0-9]{1,23}$', username):
        raise ValidationError(
            {
                "username": _(
                    "Invalid username. Must be between 2 and 24 characters long, "  # noqa
                    "contain only letters and numbers, and start with a letter."  # noqa
                ),
            }
        )
    return username.lower()


def check_cf_turnstile(turnstile_token):
    """
    Checks if the turnstile token is valid
    :param turnstile_token: string
    :return: bool
    """
    data = {
        'secret': CLOUDFLARE_SECRET_KEY,
        'response': turnstile_token,
        'sitekey': CLOUDFLARE_SITE_KEY,
    }
    response = requests.post(CLOUDFLARE_API_URL, data=data)
    return response.status_code == 200 and response.json().get(
        'success', False
    )
