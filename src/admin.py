from collections.abc import Callable, Sequence
from typing import Any

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, User
from django.http.request import HttpRequest
from django.utils.translation import gettext_lazy as _

from src.forms import ProjectForm, ProjectFormSuperUser
from src.models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    search_fields = ('domain', 'user__username')
    list_display_links = ('domain',)

    def get_readonly_fields(
        self, request: HttpRequest, obj: Any | None = ...
    ) -> Sequence[str]:  # noqa
        if obj:
            if request.user.is_superuser:
                return ('secret_key',)
            else:
                return ('domain', 'secret_key')
        return ()

    def get_list_display(self, request: HttpRequest) -> Sequence[str]:
        if request.user.is_superuser:
            return (
                'domain',
                'user',
                'secret_key',
                'created_at',
                'updated_at',
                'last_connected_at',
            )
        else:
            return (
                'domain',
                'secret_key',
                'created_at',
                'updated_at',
                'last_connected_at',
            )

    def get_form(
        self,
        request: HttpRequest,
        _obj: Any | None = ...,
        _change: bool = ...,
        **_kwargs: Any
    ) -> Any:
        if request.user.is_superuser:
            return ProjectFormSuperUser
        else:
            return ProjectForm

    def get_fields(
        self, request: HttpRequest, obj: Any | None = ...
    ) -> Sequence[Callable[..., Any] | str]:  # noqa
        if obj:
            if request.user.is_superuser:
                return ('domain', 'user', 'secret_key')
            else:
                return ('domain', 'secret_key')
        else:
            if request.user.is_superuser:
                return ('domain', 'user')
            else:
                return ('domain',)

    def get_queryset(self, request: HttpRequest) -> Any:
        qs = (
            super()
            .get_queryset(request)
            .select_related("user")
            .filter(user__is_active=True)
        )
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    def save_model(
        self, request: HttpRequest, obj: Any, form: Any, change: bool
    ) -> None:  # noqa
        # if normal user create project
        if not change and not request.user.is_superuser:
            obj.user = request.user

        super().save_model(request, obj, form, change)


class ProjectInline(admin.TabularInline):
    model = Project
    extra = 0
    fields = (
        "domain",
        "secret_key",
        "created_at",
        "updated_at",
        "last_connected_at",
    )
    readonly_fields = ("created_at", "updated_at", "last_connected_at")
    can_delete = False

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "project_count",
        "is_staff",
        "is_active",
    )
    fieldsets = (
        (
            _("Personal info"),
            {
                "fields": (
                    "username",
                    "password",
                    "first_name",
                    "last_name",
                    "email",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    inlines = [ProjectInline]
    list_filter = ("is_staff", "is_active")

    def get_queryset(self, request: HttpRequest) -> Any:
        qs = super().get_queryset(request)
        return qs.filter(is_superuser=False)

    def get_readonly_fields(
        self, request: HttpRequest, obj: Any | None = ...
    ) -> Sequence[str]:  # noqa
        res = super().get_readonly_fields(request, obj)
        if obj:
            res += ('username',)
        return res

    def project_count(self, obj: Any) -> int:
        return obj.projects.count()
