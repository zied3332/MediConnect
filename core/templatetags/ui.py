from django import template
from django.utils.translation import gettext, ngettext

register = template.Library()


@register.filter(name='ui')
def ui(value):
    """Translate known interface labels, never machine-translate user records."""
    return gettext(str(value)) if value is not None else ''


@register.filter(name='ui_count')
def ui_count(value, kind):
    """Keep counts and their complete plural phrases together in every language."""
    phrases = {
        'doctor': ('%(count)s doctor', '%(count)s doctors'),
        'doctor_found': ('%(count)s doctor found', '%(count)s doctors found'),
        'result': ('%(count)s result', '%(count)s results'),
        'message': ('%(count)s message', '%(count)s messages'),
        'unread': ('%(count)s unread', '%(count)s unread'),
    }
    singular, plural = phrases[kind]
    count = int(value or 0)
    return ngettext(singular, plural, count) % {'count': count}
