import os
import jinja2


def domain_validator(domain):
    """
    Validates subdomain string
    :param subdomain: string
    :return: True if valid, False if not
    """
    import re
    from django.core.exceptions import ValidationError

    HTTP_HOST = os.getenv('HTTP_HOST')
    postfix = f'.{HTTP_HOST}'

    if not domain.endswith(postfix):
        raise ValidationError({
            'domain': f'Invalid domain. Must end with {postfix}'
        })

    subdomain = domain.replace(postfix, '')

    # min: 2, max: 63, a-z, 0-9, -, no leading or trailing -
    if not re.match(r'^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$', subdomain):
        raise ValidationError({
            'domain': 'Invalid subdomain. Must be between 2 and 63 characters long, '  # noqa
                      'contain only lowercase letters, numbers, and hyphens, '  # noqa
                      'and start and end with a letter or number.'
        })


def gen_secret():
    """
    Generates a secret string
    :return: string
    """
    import secrets

    return secrets.token_urlsafe(32)


def get_available_port(project_id: int):
    """
    Generates a port number that is not in use on the host
    :return: int
    """
    import socket
    from django.core.cache import cache

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


def gen_502_page(domain):
    """
    Generates a 502 error page
    :param domain: string
    """
    TPL_PATH = 'src/templates/502.html-tpl'
    with open(TPL_PATH, 'r') as f:
        tpl_str = f.read()
    tpl = jinja2.Template(tpl_str)
    conf_str = tpl.render(domain=domain)
    if not os.path.exists('/var/www/http-server/502'):
        os.makedirs('/var/www/http-server/502')
    with open(f'/var/www/http-server/502/{domain}.html', 'w') as f:
        f.write(conf_str)

    os.system('service nginx reload')


def remove_502_page(domain):
    """
    Removes the 502 error page
    :param domain: string
    """
    try:
        os.remove(f'/var/www/http-server/502/{domain}.html')
        os.system('service nginx reload')
    except FileNotFoundError:
        pass


def gen_key_pair(username) -> tuple:
    """
    Generates a key pair
    :param username: string
    :return: tuple(public_key_path: string, private_key_path: string)
    """
    import rsa

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
    from django.conf import settings

    if username in settings.USERNAME_EXCLUDE_LIST:
        return

    os.system(f'useradd -m -p ! {username}')
    os.system(f'mkdir /home/{username}/.ssh')
    os.system(f'chown {username}:{username} /home/{username}/.ssh')
    os.system(f'chmod 700 /home/{username}/.ssh')
    gen_sshd_conf(username)


def gen_sshd_conf(username):
    """
    Generates sshd config file
    :param username: string
    :return: string
    """
    conf_str = r"""Match User %s
    AllowTcpForwarding yes
    ForceCommand /bin/false
    PasswordAuthentication no
""" % username
    DIR = '/etc/ssh/sshd_config.d/user.d'
    FILE = f'{DIR}/{username}.conf'
    with open(FILE, 'w') as f:
        f.write(conf_str)
    os.system(f'chown root:root {FILE}')
    os.system(f'chmod 600 {FILE}')
    os.system('service ssh reload')
