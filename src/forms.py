from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from .models import Project
from .funks import domain_validator

import os


class ProjectForm(ModelForm):
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
        self.fields['domain'].initial = f".{os.getenv('HTTP_HOST')}"

    def clean_domain(self):
        domain = self.cleaned_data['domain']
        try:
            domain_validator(domain)
        except ValidationError as e:
            self._update_errors(e)
        return domain


class AddProjectFormSuperUser(ModelForm):
    class Meta:
        model = Project
        fields = ['domain', 'user', 'secret']
        error_messages = {
            'domain': {
                'unique': "This domain is already in use.",
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['domain'].initial = f".{os.getenv('HTTP_HOST')}"

    def clean_domain(self):
        domain = self.cleaned_data['domain']
        try:
            domain_validator(domain)
        except ValidationError as e:
            self._update_errors(e)
        return domain


class ChangeProjectFormSuperUser(ModelForm):
    class Meta:
        model = Project
        fields = ['user']


def clean_username(self):
    """Reject usernames that differ only in case."""
    from django.conf import settings

    username = self.cleaned_data.get("username")
    if (
        username
        and self._meta.model.objects.filter(username__iexact=username).exists()
    ):
        self._update_errors(
            ValidationError({
                "username": self.instance.unique_error_message(
                    self._meta.model, ["username"]
                )
            })
        )
    elif username in settings.USERNAME_EXCLUDE_LIST:
        self._update_errors(
            ValidationError({
                "username": "This username is not allowed."
            })
        )
    else:
        return username


UserCreationForm.clean_username = clean_username
