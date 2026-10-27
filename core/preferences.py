from django import forms
from django.conf import settings
from django.shortcuts import redirect, render
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _


class PreferencesForm(forms.Form):
    theme = forms.ChoiceField(label=_("Appearance"), choices=[('light', _('Light')), ('dark', _('Dark'))], widget=forms.RadioSelect)
    language = forms.ChoiceField(label=_("Application language"), choices=settings.LANGUAGES)


def preferences_context(request):
    theme = request.COOKIES.get('mediconnect_theme', 'light')
    return {'ui_theme': theme if theme in ('light', 'dark') else 'light'}


def preferences_page(request):
    form = PreferencesForm(request.POST if request.method == 'POST' else None,
        initial={'theme': preferences_context(request)['ui_theme'], 'language': translation.get_language().split('-')[0]})
    if request.method == 'POST' and form.is_valid():
        destination = request.POST.get('next', '')
        if not url_has_allowed_host_and_scheme(destination, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            destination = request.path + '?saved=1'
        response = redirect(destination)
        response.set_cookie('mediconnect_theme', form.cleaned_data['theme'], max_age=31536000, samesite='Lax', secure=request.is_secure())
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, form.cleaned_data['language'], max_age=31536000, samesite='Lax', secure=request.is_secure())
        response['Cache-Control'] = 'no-store'
        return response
    role = getattr(request.user, 'role', None) if request.user.is_authenticated else None
    return render(request, 'core/preferences.html', {'form': form, 'saved': request.GET.get('saved') == '1',
        'dashboard_role': role, 'active_nav': 'preferences', 'page_title': _('Preferences'),
        'preferences_base': 'dashboard/base.html' if role else 'base.html'})
