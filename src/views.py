from django.http import (
    JsonResponse,
    Http404,
    FileResponse,
    HttpRequest,
)
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache

from .models import Project
from .funks import (
    get_available_port as get_available_port_funk,
    gen_nginx_conf,
    gen_key_pair,
    save_public_key,
)

import os


@csrf_exempt
def get_connection_info(request: HttpRequest) -> JsonResponse:
    """
    Generates user, port and domain of the project
    :return: user: str, port: int
    """
    domain = request.POST.get('domain')
    try:
        project = Project.objects.get(domain=domain)
    except Project.DoesNotExist:
        raise Http404

    return JsonResponse({
        'user': project.user.username,
        'port': get_available_port_funk(project.id),
    })


@csrf_exempt
def get_key_file(request: HttpRequest) -> FileResponse:
    """
    Generates a key pair and returns the private key file
    :return: FileResponse
    """
    if request.method == 'POST':
        domain = request.POST.get('domain')
        secret = request.POST.get('secret')

        try:
            project = Project.objects.get(domain=domain)
        except Project.DoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)

        if project.secret != secret:
            return JsonResponse({'error': 'Invalid secret'}, status=403)

        _, private_key = gen_key_pair()
        private_key_path = f'{project.id}_private_key.pem'
        f = open(private_key_path, 'wb')
        f.write(private_key.save_pkcs1())
        f.close()
        os.chmod(private_key_path, 0o400)
        save_public_key(project, private_key_path)

        return FileResponse(open(f'{project.id}_private_key.pem', 'rb'))
    else:
        raise Http404


@csrf_exempt
def connect(request):
    if request.method == 'POST':
        domain = request.POST.get('domain')
        secret = request.POST.get('secret')
        port = request.POST.get('port')

        try:
            project = Project.objects.get(domain=domain)
        except Project.DoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)

        if project.secret != secret:
            return JsonResponse({'error': 'Invalid secret'}, status=403)

        if cache.get(port) != project.id:
            return JsonResponse({'error': 'Port not available'}, status=409)

        cache.delete(port)
        gen_nginx_conf(domain, port)

        return JsonResponse({
            'success': True,
        })

    else:
        raise Http404
