from typing import Any

from django import forms


class UserSelect(forms.Select):
    def create_option(  # noqa: PLR0913
        self,
        name,
        value,
        label,
        selected,
        index,
        subindex=None,
        attrs=None,
    ) -> dict[str, Any]:
        option = super().create_option(
            name,
            value,
            label,
            selected,
            index,
            subindex=subindex,
            attrs=attrs,
        )
        if value and not value.instance.is_active:
            option["attrs"]["disabled"] = "disabled"
            option["label"] += " (inactive)"
        return option
