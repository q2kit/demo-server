from django import forms
from django.contrib.admin import widgets
from django.contrib.admin.forms import (
    AdminAuthenticationForm as BaseAdminAuthenticationForm,
)
from django.contrib.admin.sites import site as admin_site
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from src.env import HTTP_HOST
from src.funks import domain_validator, username_validator
from src.models import Project
from src.widgets import UserSelect


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['domain']
        error_messages = {
            'domain': {
                'unique': _("This domain is already in use."),
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['domain'].initial = f".{HTTP_HOST}"

    def clean_domain(self):
        return domain_validator(self.cleaned_data['domain'])


class ProjectFormSuperUser(ProjectForm):
    class Meta:
        model = Project
        fields = ['domain', 'user']
        error_messages = {
            'domain': {
                'unique': _("This domain is already in use."),
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].widget = widgets.RelatedFieldWidgetWrapper(
            UserSelect(
                choices=self.fields['user'].choices,
            ),
            Project._meta.get_field('user').remote_field,
            admin_site,
            can_add_related=True,
            can_change_related=True,
            can_delete_related=True,
            can_view_related=True,
        )

    def clean_user(self):
        user = self.cleaned_data['user']
        if not user.is_active and (
            not hasattr(self.instance, 'user') or user != self.instance.user
        ):
            raise ValidationError(_("This user is inactive."))

        return user


class AdminAuthenticationForm(BaseAdminAuthenticationForm):
    error_messages = {
        **BaseAdminAuthenticationForm.error_messages,
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = _(
            "Must be between 2 and 24 characters long, contain only letters and numbers, and start with a letter"  # noqa
        )
