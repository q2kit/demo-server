from django import forms
from django.contrib.admin import widgets
from django.contrib.admin.sites import site as admin_site
from django.contrib.auth.forms import (
    AuthenticationForm as BaseAuthenticationForm,
)
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from src.env import HTTP_HOST
from src.funks import domain_validator, username_validator
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
            return domain_validator(domain)
        except ValidationError as e:
            self._update_errors(e)


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


class AuthenticationForm(BaseAuthenticationForm):
    error_messages = {
        "invalid_login": _("Please enter a correct username and password."),
        "inactive": _("This account is inactive."),
    }


class UserCreationForm(BaseUserCreationForm):
    def clean_username(self):
        username = super().clean_username()
        try:
            return username_validator(username) if username else None
        except ValidationError as e:
            self._update_errors(e)
