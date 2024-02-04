from collections.abc import Callable, Sequence
from typing import Any
from django.contrib import admin
from django.http.request import HttpRequest

from .models import Project
from .forms import ProjectForm, ProjectFormSuperUser


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    search_fields = ('id', 'domain', 'user__username')
    readonly_fields = ('id', 'secret',)
    list_display_links = ('id', 'domain')

    def get_list_display(self, request: HttpRequest) -> Sequence[str]:
        if request.user.is_superuser:
            return ('id', 'domain', 'user', 'secret')
        return ('id', 'domain', 'secret')

    def get_form(self, request: Any, obj: Any | None = ..., change: bool = ..., **kwargs: Any) -> Any:  # noqa
        if request.user.is_superuser:
            return ProjectFormSuperUser
        else:
            return ProjectForm

    def get_fields(self, request: HttpRequest, obj: Any | None = ...) -> Sequence[Callable[..., Any] | str]:  # noqa
        if request.user.is_superuser:
            return ('id', 'domain', 'user', 'secret')
        return ('id', 'domain', 'secret')

    def get_queryset(self, request: HttpRequest) -> Any:
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    def save_model(self, request: HttpRequest, obj: Any, form: Any, change: bool) -> None:  # noqa
        if not change:
            obj.user = request.user

        super().save_model(request, obj, form, change)
