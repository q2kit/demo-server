from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView as BaseLoginView
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpRequest, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from src.env import CLOUDFLARE_SITE_KEY
from src.forms import AdminAuthenticationForm, UserCreationForm
from src.funks import (
    check_cf_turnstile,
    gen_key_pair,
    get_available_port,
    remove_key_pair,
)
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

        return JsonResponse({'success': True})

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


class LoginView(BaseLoginView):
    """
    Custom login view to handle Turnstile verification.
    """

    form_class = AdminAuthenticationForm
    template_name = 'admin/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        if settings.DEBUG:
            # In debug mode, skip Turnstile verification
            return super().form_valid(form)

        turnstile_token = self.request.POST.get('cf-turnstile-response')
        if check_cf_turnstile(turnstile_token):
            return super().form_valid(form)
        else:
            form.add_error(None, "Invalid Turnstile token.")
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not settings.DEBUG:
            context['cloudflare_sitekey'] = CLOUDFLARE_SITE_KEY
        return context


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        turnstile_token = request.POST.get('cf-turnstile-response')
        is_cf_turnstile_valid = check_cf_turnstile(turnstile_token)

        if form.is_valid() and is_cf_turnstile_valid:
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password1"],
                is_active=True,
                is_staff=True,
            )
            login(request, user)
            return redirect("admin:index")
        elif not is_cf_turnstile_valid:
            form.add_error(None, "Invalid Turnstile token.")
    else:
        form = UserCreationForm()

    context = {
        "form": form,
        "cloudflare_sitekey": CLOUDFLARE_SITE_KEY,
    }

    return render(request, "admin/signup.html", context)


def csrf_failure(request, reason=""):  # noqa: U100
    """
    CSRF failure view.
    """
    raise PermissionDenied("CSRF token missing or incorrect.")
