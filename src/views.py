from django.http import (
    JsonResponse,
    Http404,
    FileResponse,
    HttpRequest,
)
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.contrib.auth.models import User

from .models import Project
from .funks import (
    get_available_port as get_available_port_funk,
    gen_nginx_conf,
    gen_default_nginx_conf as reset_default_nginx_conf,
    gen_key_pair,
    remove_key_pair,
)
from .forms import RegistrationForm


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

        _, private_key_path = gen_key_pair(project.user.username)

        import threading
        threading.Timer(60, remove_key_pair, args=(project.user.username,)).start()  # noqa

        return FileResponse(open(private_key_path, 'rb'))
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


@csrf_exempt
def disconnect(request):
    if request.method == 'POST':
        domain = request.POST.get('domain')
        secret = request.POST.get('secret')

        try:
            project = Project.objects.get(domain=domain)
        except Project.DoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)

        if project.secret != secret:
            return JsonResponse({'error': 'Invalid secret'}, status=403)

        reset_default_nginx_conf(domain)

        return JsonResponse({
            'success': True,
        })

    else:
        raise Http404


def signup(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
                is_active=True,
                is_staff=True,
            )
            login(request, user)
            return redirect("admin:index")
    else:
        form = RegistrationForm()

    return render(
        request,
        "admin/signup.html",
        {"form": form},
    )
