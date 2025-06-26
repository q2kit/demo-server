import re
import secrets
import socket
import subprocess
from pathlib import Path

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


def domain_validator(domain) -> str:
    """Validate subdomain string.

    :param subdomain: string
    :return: True if valid, False if not
    """
    domain = domain.strip().lower()
    postfix = f".{HTTP_HOST}"

    if not domain.endswith(postfix):
        raise ValidationError(f"Invalid domain. Must end with '{postfix}'.")

    subdomain = domain.replace(postfix, "")

    for item in getattr(settings, "SUBDOMAIN_EXCLUDE_LIST", []):
        if subdomain == item or (
            isinstance(item, re.Pattern) and item.match(subdomain)
        ):
            raise ValidationError(f"Invalid subdomain. '{subdomain}' is not allowed.")

    # min: 2, max: 63, a-z, 0-9, -, no leading or trailing -
    if not re.match(r"^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$", subdomain):
        raise ValidationError(
            "Invalid subdomain. Must be between 2 and 63 characters long, "
            "contain only lowercase letters, numbers, and hyphens, "
            "and start and end with a letter or number.",
        )

    return domain


def gen_secret_key() -> str:
    """Generate a secret_key string.

    :return: string
    """
    return secrets.token_hex(16)


def get_available_port(project_id: int) -> int | None:
    """Generate a port number that is not in use on the host.

    :return: int
    """
    for port in range(20000, 30001):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        if result != 0 and not cache.get(port):
            cache.set(port, project_id, 30)  # 30 seconds
            return port

    return None


def gen_nginx_conf(domain, port=None) -> None:
    """Generate nginx config file.

    :param domain: string
    :param port: int
    """
    with Path("src/templates/nginx.conf-tpl").open() as f:
        tpl_str = f.read()
    tpl = jinja2.Template(tpl_str)
    conf_str = tpl.render(domain=domain, port=port)
    with Path(f"/etc/nginx/sites/{domain}.conf").open("w") as f:
        f.write(conf_str)
    subprocess.run(["service", "nginx", "reload"], check=True)  # noqa: S607


def remove_nginx_conf(domain) -> None:
    """Remove the nginx config file.

    :param domain: string
    """
    try:
        Path(f"/etc/nginx/sites/{domain}.conf").unlink()
    except FileNotFoundError:
        pass
    else:
        subprocess.run(["service", "nginx", "reload"], check=True)  # noqa: S607


def gen_default_nginx_conf(domain) -> None:
    """Generate a default page.

    :param domain: string
    """
    gen_nginx_conf(domain=domain, port=None)


def gen_502_page(domain) -> None:
    """Generate a 502 error page.

    :param domain: string
    """
    with Path("src/templates/502.html-tpl").open() as f:
        tpl_str = f.read()
    tpl = jinja2.Template(tpl_str)
    conf_str = tpl.render(domain=domain, HOST=HTTP_HOST)
    Path("/var/www/demos/502").mkdir(parents=True, exist_ok=True)
    with Path(f"/var/www/demos/502/{domain}.html").open("w") as f:
        f.write(conf_str)

    subprocess.run(["service", "nginx", "reload"], check=True)  # noqa: S607


def remove_502_page(domain) -> None:
    """Remove the 502 error page.

    :param domain: string
    """
    try:
        Path(f"/var/www/demos/502/{domain}.html").unlink()
        subprocess.run(["service", "nginx", "reload"], check=True)  # noqa: S607
    except FileNotFoundError:
        pass


def gen_key_pair(username) -> tuple:
    """Generate a key pair.

    :param username: string
    :return: tuple(public_key_path: string, private_key_path: string)
    """
    DIR = Path(f"/home/{username}/.ssh")  # noqa: N806

    _, private_key = rsa.newkeys(2048)
    private_key_path = DIR / "private_key.pem"
    with private_key_path.open("wb") as f:
        f.write(private_key.save_pkcs1())
    private_key_path.chmod(0o600)
    public_key_path = DIR / "authorized_keys"
    subprocess.run(  # noqa: S603
        ["ssh-keygen", "-y", "-f", str(private_key_path)],  # noqa: S607
        stdout=public_key_path.open("w"),
        check=True,
    )
    public_key_path.chown(username, username)
    public_key_path.chmod(0o600)

    return public_key_path, private_key_path


def remove_key_pair(username) -> None:
    """Remove the key pair.

    :param username: string
    :return: None
    """
    DIR = Path(f"/home/{username}/.ssh")  # noqa: N806
    Path(DIR / "authorized_keys").unlink(missing_ok=True)
    Path(DIR / "private_key.pem").unlink(missing_ok=True)


def create_user_profile(username) -> None:
    """Create a user without password and creates a .ssh directory.

    :param username: string
    :return: None
    """
    if username in settings.USERNAME_EXCLUDE_LIST:
        return

    subprocess.run(  # noqa: S603
        ["useradd", "-m", "-p", "!", username],  # noqa: S607
        check=True,
        capture_output=True,
    )
    ssh_dir = Path(f"/home/{username}/.ssh")
    ssh_dir.mkdir(parents=True, exist_ok=True)
    ssh_dir.chmod(0o700)
    ssh_dir.chown(username, username)
    gen_sshd_conf(username)


def delete_user_profile(username) -> None:
    """Delete a user and remove the .ssh directory.

    :param username: string
    :return: None
    """
    if username in settings.USERNAME_EXCLUDE_LIST:
        return

    subprocess.run(["userdel", "-r", username], check=True, capture_output=True)  # noqa: S603, S607
    remove_sshd_conf(username)


def gen_sshd_conf(username) -> None:
    """Generate sshd config file.

    :param username: string
    :return: None
    """
    with Path("src/templates/sshd.user.conf-tpl").open() as f:
        tpl_str = f.read()
    tpl = jinja2.Template(tpl_str)
    conf_str = tpl.render(username=username)
    CONF_FILE = Path(f"/etc/ssh/sshd_config.d/user.d/{username}.conf")  # noqa: N806
    CONF_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CONF_FILE.open("w") as f:
        f.write(conf_str)
    CONF_FILE.chmod(0o600)
    CONF_FILE.chown("root", "root")
    subprocess.run(
        ["service", "ssh", "reload"],  # noqa: S607
        check=True,
        capture_output=True,
    )


def remove_sshd_conf(username) -> None:
    """Remove the sshd config file.

    :param username: string
    :return: None
    """
    Path(f"/etc/ssh/sshd_config.d/user.d/{username}.conf").unlink(missing_ok=True)
    subprocess.run(
        ["service", "ssh", "reload"],  # noqa: S607
        check=True,
        capture_output=True,
    )


def username_validator(username) -> str:
    """Validate username string.

    :param username: string
    :return: True if valid, False if not
    """
    if username and get_user_model().objects.filter(username__iexact=username).exists():
        raise ValidationError(
            {
                "username": _("This username is already in use."),
            },
        )
    if username in settings.USERNAME_EXCLUDE_LIST:
        raise ValidationError({"username": _("This username is not allowed.")})

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9]{1,23}$", username):
        raise ValidationError(
            {
                "username": _(
                    "Invalid username. Must be between 2 and 24 characters long, "
                    "contain only letters and numbers, and start with a letter.",
                ),
            },
        )
    return username.lower()


def check_cf_turnstile(turnstile_token) -> bool:
    """Check if the turnstile token is valid.

    :param turnstile_token: string
    :return: bool
    """
    data = {
        "secret": CLOUDFLARE_SECRET_KEY,
        "response": turnstile_token,
        "sitekey": CLOUDFLARE_SITE_KEY,
    }
    response = requests.post(CLOUDFLARE_API_URL, data=data, timeout=10)
    return response.status_code == 200 and response.json().get(  # noqa: PLR2004
        "success",
        False,
    )
