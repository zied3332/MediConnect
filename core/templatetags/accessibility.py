"""Render fields with additional descriptions without changing form validation."""
from django import template

register = template.Library()


@register.simple_tag
def accessible_field(field, *description_ids):
    descriptions = field.field.widget.attrs.get("aria-describedby", "").split()
    if field.auto_id and not field.is_hidden:
        if field.help_text:
            descriptions.append(f"{field.auto_id}_helptext")
        if field.errors:
            descriptions.append(f"{field.auto_id}_error")
    for reference in description_ids:
        descriptions.extend(str(reference or "").split())
    attrs = {}
    if descriptions:
        attrs["aria-describedby"] = " ".join(dict.fromkeys(descriptions))
    return field.as_widget(attrs=attrs)
