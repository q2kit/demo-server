from collections.abc import Callable, Sequence
from typing import Any

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.options import InlineModelAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, User
from django.db.models import Count
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.utils.translation import gettext_lazy as _

from src.forms import ProjectForm, ProjectFormSuperUser, UserCreationForm
from src.models import Project


class SuperAdminFilter(SimpleListFilter):
    def __init__(self, request, params, model, model_admin) -> None:
        super().__init__(request, params, model, model_admin)
        if not request.user.is_superuser:
            self.lookup_choices = []


class ActiveUserFilter(SuperAdminFilter):
    title = _("active user")
    parameter_name = "is_user_active"

    def lookups(self, request, model_admin) -> Sequence[tuple[str, str]]:  # noqa: ARG002
        return (
            ("1", _("Yes")),
            ("0", _("No")),
        )

    def queryset(self, request, queryset) -> QuerySet[Project]:  # noqa: ARG002
        if self.value() == "1":
            return queryset.filter(user__is_active=True)
        if self.value() == "0":
            return queryset.filter(user__is_active=False)
        return queryset


class UserHasProjectsFilter(SuperAdminFilter):
    title = _("user")
    parameter_name = "user"

    def lookups(self, request, model_admin) -> Sequence[tuple[str, str]]:  # noqa: ARG002
        return (
            User.objects.annotate(projects_count=Count("projects"))
            .filter(projects_count__gt=0)
            .values_list("id", "username")
        )

    def queryset(self, request, queryset) -> QuerySet[Project]:  # noqa: ARG002
        if self.value():
            return queryset.filter(user=self.value())
        return queryset


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    search_fields = ("domain", "user__username")
    list_display_links = ("domain",)
    list_filter = (UserHasProjectsFilter, ActiveUserFilter)

    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: Project | None,
    ) -> Sequence[str]:
        if obj:
            if request.user.is_superuser:
                return ("secret_key",)
            return ("domain", "secret_key")
        return ()

    def get_list_display(self, request: HttpRequest) -> Sequence[str]:
        if request.user.is_superuser:
            return (
                "domain",
                "user",
                "secret_key",
                "created_at",
                "updated_at",
                "last_connected_at",
            )
        return (
            "domain",
            "secret_key",
            "created_at",
            "updated_at",
            "last_connected_at",
        )

    def get_form(
        self,
        request: HttpRequest,
        *args,  # noqa: ARG002
        **kwargs,  # noqa: ARG002
    ) -> ProjectForm | ProjectFormSuperUser:
        if request.user.is_superuser:
            return ProjectFormSuperUser
        return ProjectForm

    def get_fields(
        self,
        request: HttpRequest,
        obj: Project | None = None,
    ) -> Sequence[Callable[..., Any] | str]:
        if obj:
            if request.user.is_superuser:
                return ("domain", "user", "secret_key")
            return ("domain", "secret_key")
        if request.user.is_superuser:
            return ("domain", "user")
        return ("domain",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Project]:
        qs = super().get_queryset(request).select_related("user")
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    def save_model(
        self,
        request: HttpRequest,
        obj: Project,
        form: ProjectForm | ProjectFormSuperUser,
        change: bool,  # noqa: FBT001
    ) -> None:
        # if normal user create project
        if not change and not request.user.is_superuser:
            obj.user = request.user

        super().save_model(request, obj, form, change)


class ProjectInline(admin.TabularInline):
    model = Project
    extra = 0
    fields = (
        "domain",
        "created_at",
        "updated_at",
        "last_connected_at",
    )
    readonly_fields = (
        "domain",
        "created_at",
        "updated_at",
        "last_connected_at",
    )
    can_delete = False
    show_change_link = True

    def get_queryset(self, request: HttpRequest) -> QuerySet[Project]:
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    def has_add_permission(self, request, obj=None) -> bool:  # noqa: ARG002
        return False


class IsGhostUserFilter(SuperAdminFilter):
    title = _("ghost user")
    parameter_name = "is_ghost_user"

    def lookups(self, request, model_admin) -> Sequence[tuple[str, str]]:  # noqa: ARG002
        return (
            ("1", _("Yes")),
            ("0", _("No")),
        )

    def queryset(self, request, queryset) -> QuerySet[User]:  # noqa: ARG002
        if self.value() == "1":
            return queryset.annotate(projects_count=Count("projects")).filter(
                projects_count=0,
            )
        if self.value() == "0":
            return queryset.annotate(projects_count=Count("projects")).filter(
                projects_count__gt=0,
            )
        return queryset


admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_form = UserCreationForm
    list_display = (
        "username",
        "email",
        "projects_count",
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
                ),
            },
        ),
        (
            _("Permissions"),
            {
                "fields": ("is_active",),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    inlines = [ProjectInline]
    list_filter = ("is_active", IsGhostUserFilter)

    def get_queryset(self, request: HttpRequest) -> QuerySet[User]:
        return (
            super()
            .get_queryset(request)
            .annotate(projects_count=Count("projects"))
            .filter(is_superuser=False)
        )

    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: User | None,
    ) -> Sequence[str]:
        res = super().get_readonly_fields(request, obj)
        if obj:
            res += ("username",)
        return res

    @admin.display(description=_("Projects count"), ordering="projects_count")
    def projects_count(self, obj: User) -> int:
        return obj.projects_count

    def get_inline_instances(self, request, obj=None) -> list[InlineModelAdmin]:
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)
