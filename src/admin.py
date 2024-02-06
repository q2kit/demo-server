from collections.abc import Callable, Sequence
from typing import Any
from django.contrib import admin
from django.http.request import HttpRequest

from .models import Project
from .forms import (
    ProjectForm,
    AddProjectFormSuperUser,
    ChangeProjectFormSuperUser,
)
from .funks import (
    gen_502_page,
    remove_502_page,
    gen_nginx_conf,
    remove_nginx_conf,
)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    search_fields = ('domain', 'user__username')
    list_display_links = ('domain',)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return any((
            request.user.is_superuser,
            request.user.project_set.count() == 0
        ))

    def has_change_permission(self, request: HttpRequest, obj: Any | None = ...) -> bool:  # noqa
        return request.user.is_superuser

    def get_readonly_fields(self, request: HttpRequest, obj: Any | None = ...) -> Sequence[str]:  # noqa
        if obj:
            return ('domain', 'secret')
        return ()

    def get_list_display(self, request: HttpRequest) -> Sequence[str]:
        if request.user.is_superuser:
            return ('domain', 'user', 'secret')
        return ('domain', 'secret')

    def get_form(self, request: Any, obj: Any | None = ..., change: bool = ..., **kwargs: Any) -> Any:  # noqa
        if request.user.is_superuser:
            if change:
                return ChangeProjectFormSuperUser
            else:
                return AddProjectFormSuperUser
        else:
            return ProjectForm

    def get_fields(self, request: HttpRequest, obj: Any | None = ...) -> Sequence[Callable[..., Any] | str]:  # noqa
        if obj:
            if request.user.is_superuser:
                return ('domain', 'user', 'secret')
            else:
                return ('domain', 'secret')
        else:
            if request.user.is_superuser:
                return ('domain', 'user')
            else:
                return ('domain',)

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

        gen_502_page(obj.domain)
        gen_nginx_conf(obj.domain, None)

    def delete_model(self, request: HttpRequest, obj: Any) -> None:
        super().delete_model(request, obj)

        remove_502_page(obj.domain)
        remove_nginx_conf(obj.domain)
