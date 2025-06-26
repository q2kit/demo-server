import threading
from pathlib import Path
from typing import Any, Never

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView as BaseLoginView
from django.core.cache import cache
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from src.env import CLOUDFLARE_SITE_KEY
from src.exceptions import CsrfFailureException
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
    """Generate user, port and domain of the project."""
    domain = request.POST.get("domain")
    try:
        project = Project.objects.get(domain=domain)
    except Project.DoesNotExist as e:
        raise Http404 from e

    return JsonResponse(
        {
            "user": project.user.username,
            "port": get_available_port(project.id),
        },
    )


@csrf_exempt
def get_key_file(request: HttpRequest) -> FileResponse:
    """Generate a key pair and returns the private key file."""
    if request.method == "POST":
        domain = request.POST.get("domain")
        secret_key = request.POST.get("secret_key")

        try:
            project = Project.objects.get(domain=domain)
        except Project.DoesNotExist:
            return JsonResponse({"error": "Project not found"}, status=404)

        if project.secret_key != secret_key:
            return JsonResponse({"error": "Invalid secret_key"}, status=403)

        _, private_key_path = gen_key_pair(project.user.username)

        threading.Timer(
            60,
            remove_key_pair,
            args=(project.user.username,),
        ).start()

        return FileResponse(Path(private_key_path).open("rb"))
    raise Http404


@csrf_exempt
def connect(request) -> JsonResponse:
    if request.method == "POST":
        domain = request.POST.get("domain")
        secret_key = request.POST.get("secret_key")
        port = request.POST.get("port")

        try:
            project = Project.objects.get(domain=domain)
        except Project.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Project not found"},
                status=404,
            )

        if project.secret_key != secret_key:
            return JsonResponse(
                {"success": False, "error": "Invalid secret_key"},
                status=403,
            )

        if cache.get(port) != project.id:
            return JsonResponse(
                {"success": False, "error": "Port not available"},
                status=409,
            )

        cache.delete(port)
        project.connect(port)

        return JsonResponse({"success": True})

    raise Http404


@csrf_exempt
def disconnect(request) -> JsonResponse:
    if request.method == "POST":
        domain = request.POST.get("domain")
        secret_key = request.POST.get("secret_key")

        try:
            project = Project.objects.get(domain=domain)
        except Project.DoesNotExist:
            return JsonResponse({"error": "Project not found"}, status=404)

        if project.secret_key != secret_key:
            return JsonResponse({"error": "Invalid secret_key"}, status=403)

        project.disconnect()

        return JsonResponse(
            {
                "success": True,
            },
        )

    raise Http404


@csrf_exempt
def keep_alive_connection(request) -> JsonResponse:
    domain = request.POST.get("domain")
    try:
        project = Project.objects.get(domain=domain)
        project.keep_alive_connection()
        return JsonResponse(
            {
                "success": True,
            },
        )
    except Project.DoesNotExist as e:
        raise Http404 from e


class LoginView(BaseLoginView):
    """Custom login view to handle Turnstile verification."""

    form_class = AdminAuthenticationForm
    template_name = "admin/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form) -> HttpResponse:
        if settings.DEBUG:
            # In debug mode, skip Turnstile verification
            return super().form_valid(form)

        turnstile_token = self.request.POST.get("cf-turnstile-response")
        if check_cf_turnstile(turnstile_token):
            return super().form_valid(form)
        form.add_error(None, "Are you a robot? Please leave me alone!")
        return self.form_invalid(form)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        if not settings.DEBUG:
            context["cloudflare_sitekey"] = CLOUDFLARE_SITE_KEY
        return context


def signup(request) -> HttpResponse:
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        turnstile_token = request.POST.get("cf-turnstile-response")
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
        if not is_cf_turnstile_valid:
            form.add_error(None, "Are you a robot? Please leave me alone!")
    else:
        form = UserCreationForm()

    context = {
        "form": form,
        "cloudflare_sitekey": CLOUDFLARE_SITE_KEY,
    }

    return render(request, "admin/signup.html", context)


def csrf_failure(request, reason="") -> Never:  # noqa: ARG001
    """CSRF failure view."""
    raise CsrfFailureException
