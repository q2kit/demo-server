from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.cache import cache
from django.http import FileResponse, Http404, HttpRequest, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from src.forms import UserCreationForm
from src.funks import gen_key_pair, get_available_port, remove_key_pair
from src.models import Project


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

    return JsonResponse(
        {
            'user': project.user.username,
            'port': get_available_port(project.id),
        }
    )


@csrf_exempt
def get_key_file(request: HttpRequest) -> FileResponse:
    """
    Generates a key pair and returns the private key file
    :return: FileResponse
    """
    if request.method == 'POST':
        domain = request.POST.get('domain')
        secret_key = request.POST.get('secret_key')

        try:
            project = Project.objects.get(domain=domain)
        except Project.DoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)

        if project.secret_key != secret_key:
            return JsonResponse({'error': 'Invalid secret_key'}, status=403)

        _, private_key_path = gen_key_pair(project.user.username)

        import threading

        threading.Timer(
            60, remove_key_pair, args=(project.user.username,)
        ).start()  # noqa

        return FileResponse(open(private_key_path, 'rb'))  # noqa: SIM115
    else:
        raise Http404


@csrf_exempt
def connect(request):
    if request.method == 'POST':
        domain = request.POST.get('domain')
        secret_key = request.POST.get('secret_key')
        port = request.POST.get('port')

        try:
            project = Project.objects.get(domain=domain)
        except Project.DoesNotExist:
            return JsonResponse(
                {'success': False, 'error': 'Project not found'}, status=404
            )

        if project.secret_key != secret_key:
            return JsonResponse(
                {'success': False, 'error': 'Invalid secret_key'}, status=403
            )

        if cache.get(port) != project.id:
            return JsonResponse(
                {'success': False, 'error': 'Port not available'}, status=409
            )

        cache.delete(port)
        project.connect(port)

        return JsonResponse(
            {
                'success': True,
            }
        )

    else:
        raise Http404


@csrf_exempt
def disconnect(request):
    if request.method == 'POST':
        domain = request.POST.get('domain')
        secret_key = request.POST.get('secret_key')

        try:
            project = Project.objects.get(domain=domain)
        except Project.DoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)

        if project.secret_key != secret_key:
            return JsonResponse({'error': 'Invalid secret_key'}, status=403)

        project.disconnect()

        return JsonResponse(
            {
                'success': True,
            }
        )

    else:
        raise Http404


@csrf_exempt
def keep_alive_connection(request):
    domain = request.POST.get('domain')
    try:
        project = Project.objects.get(domain=domain)
        project.keep_alive_connection()
        return JsonResponse(
            {
                'success': True,
            }
        )
    except Project.DoesNotExist:
        raise Http404


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password1"],
                is_active=True,
                is_staff=True,
            )
            login(request, user)
            return redirect("admin:index")
    else:
        form = UserCreationForm()

    return render(
        request,
        "admin/signup.html",
        {"form": form},
    )
