from collections.abc import Callable, Sequence
from typing import Any
from django.contrib import admin
from django.http.request import HttpRequest

from .models import Project
from .forms import ProjectForm, ProjectFormSuperUser


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    search_fields = ('domain', 'user__username')
    list_display_links = ('domain',)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return any((
            request.user.is_superuser,
            request.user.project_set.count() == 0
        ))

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('domain', 'secret')
        return ('secret',)

    def get_list_display(self, request: HttpRequest) -> Sequence[str]:
        if request.user.is_superuser:
            return ('domain', 'user', 'secret')
        return ('domain', 'secret')

    def get_form(self, request: Any, obj: Any | None = ..., change: bool = ..., **kwargs: Any) -> Any:  # noqa
        if request.user.is_superuser:
            return ProjectFormSuperUser
        else:
            return ProjectForm

    def get_fields(self, request: HttpRequest, obj: Any | None = ...) -> Sequence[Callable[..., Any] | str]:  # noqa
        if request.user.is_superuser:
            return ('domain', 'user', 'secret')
        return ('domain', 'secret')

    def get_queryset(self, request: HttpRequest) -> Any:
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    def save_model(self, request: HttpRequest, obj: Any, form: Any, change: bool) -> None:  # noqa
        # if normal user create project
        if not change and not request.user.is_superuser:
            obj.user = request.user

        super().save_model(request, obj, form, change)
