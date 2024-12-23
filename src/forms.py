from django import forms
from django.conf import settings
from django.contrib.admin import widgets
from django.contrib.admin.sites import site as admin_site
from django.contrib.auth.forms import UserCreationForm, UsernameField
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.utils.translation import gettext_lazy as _

from src.env import HTTP_HOST
from src.funks import domain_validator
from src.models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['domain']
        error_messages = {
            'domain': {
                'unique': "This domain is already in use.",
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['domain'].initial = f".{HTTP_HOST}"

    def clean_domain(self):
        domain = self.cleaned_data['domain']
        try:
            domain_validator(domain)
        except ValidationError as e:
            self._update_errors(e)
        return domain


class ProjectFormSuperUser(ProjectForm):
    class Meta:
        model = Project
        fields = ['domain', 'user']
        error_messages = {
            'domain': {
                'unique': "This domain is already in use.",
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].widget = widgets.RelatedFieldWidgetWrapper(
            self.fields['user'].widget,
            Project._meta.get_field('user').remote_field,
            admin_site,
            can_add_related=True,
            can_change_related=True,
            can_delete_related=True,
            can_view_related=True,
        )


def clean_username(self):
    """Reject usernames that differ only in case."""
    username = self.cleaned_data.get("username")
    if (
        username
        and self._meta.model.objects.filter(username__iexact=username).exists()
    ):  # noqa
        self._update_errors(
            ValidationError(
                {
                    "username": self.instance.unique_error_message(
                        self._meta.model, ["username"]
                    )
                }
            )
        )
    elif username in settings.USERNAME_EXCLUDE_LIST:
        self._update_errors(
            ValidationError({"username": "This username is not allowed."})
        )
    else:
        return username


UserCreationForm.clean_username = clean_username  # type ignore[method-assign]


class RegistrationForm(forms.Form):
    error_messages = {
        "password_mismatch": _("The two password fields didn't match."),
        "username_exists": _("This username is already in use."),
        "username_not_allowed": "This username is not allowed.",
    }

    username = UsernameField(
        label=_("Username"),
        widget=forms.TextInput(attrs={"autofocus": True, "inputmode": "text"}),
        validators=[MinLengthValidator(3)],
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(),
        validators=[MinLengthValidator(6)],
    )
    password2 = forms.CharField(
        label=_("Confirm Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"id": "id_password2"}),
    )

    def clean_username(self):
        """Reject usernames that differ only in case."""
        username = self.cleaned_data.get("username")
        if (
            username
            and User.objects.filter(username__iexact=username).exists()
        ):
            raise forms.ValidationError(
                self.error_messages["username_exists"],
                code="username_exists",
            )
        elif username in settings.USERNAME_EXCLUDE_LIST:
            raise forms.ValidationError(
                self.error_messages["username_not_allowed"],
                code="username_not_allowed",
            )
        else:
            return username

    def clean_password2(self):
        password1 = self.cleaned_data.get("password")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.cleaned_data["password"] = password1
            raise forms.ValidationError(
                self.error_messages["password_mismatch"],
                code="password_mismatch",
            )
        return password2
