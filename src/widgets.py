from django import forms


class UserSelect(forms.Select):
    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        if value and not value.instance.is_active:
            option['attrs']['disabled'] = 'disabled'
            option['label'] += ' (inactive)'
        return option
