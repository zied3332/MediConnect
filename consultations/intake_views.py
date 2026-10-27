from django.utils.translation import gettext_lazy as ui_gettext
from datetime import timedelta

from django import forms
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from .models import AIIntakeSession

FAILURE = ui_gettext('L’orientation est indisponible. Vous pouvez contacter un professionnel ou réessayer. Aucun diagnostic n’a été établi.')
URGENT = ui_gettext('Ne vous fiez pas à cet assistant pour une urgence. Contactez immédiatement les services d’urgence locaux ou un professionnel. Aucune réservation n’est proposée ici.')


def eligible_doctors():
    return User.objects.filter(role='doctor', is_active=True, doctor_profile__status='approved', main_specialty__isnull=False).select_related('main_specialty')


def specialty_catalog():
    return [{'id': pk, 'name': name} for pk, name in eligible_doctors().values_list('main_specialty_id', 'main_specialty__name').distinct().order_by('main_specialty__name')]


class IntakeForm(forms.Form):
    complaint = forms.CharField(label=ui_gettext('Décrivez votre état en quelques phrases'), min_length=10, max_length=2000,
        widget=forms.Textarea(attrs={'rows': 7, 'maxlength': 2000, 'placeholder': ui_gettext('Expliquez ce que vous ressentez, depuis quand et ce qui vous gêne au quotidien. Ne renseignez ni nom ni coordonnées.')}))
    consent = forms.BooleanField(widget=forms.HiddenInput, initial=True)


@login_required(login_url='accounts:login')
def intake_page(request):
    if request.user.role != 'patient':
        return HttpResponseForbidden(ui_gettext('Cet assistant est réservé aux patients.'))
    response = render(request, 'consultations/intake.html', {'form': IntakeForm(), 'dashboard_role': 'patient', 'active_nav': 'intake', 'page_title': ui_gettext('Orientation IA')})
    response['Cache-Control'] = 'no-store'
    return response


@login_required(login_url='accounts:login')
@require_POST
def intake_start(request):
    if request.user.role != 'patient':
        return JsonResponse({'error': ui_gettext('Accès réservé aux patients.')}, status=403)
    form = IntakeForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'error': ui_gettext('Vérifiez les champs et votre accord.'), 'fields': form.errors.get_json_data()}, status=400)
    from .intake_tasks import generate_orientation
    with transaction.atomic():
        answers = {key: value for key, value in form.cleaned_data.items() if key != 'consent'}
        session = AIIntakeSession.objects.create(patient=request.user, answers=answers, consent_at=timezone.now())
        def enqueue():
            try:
                generate_orientation.apply_async(args=[str(session.pk)], retry=False)
            except Exception:
                AIIntakeSession.objects.filter(pk=session.pk, status='pending').update(status='failed', error_code='queue', updated_at=timezone.now())
        transaction.on_commit(enqueue)
    return JsonResponse({'status_url': reverse('consultations:intake_status', args=[session.pk]), 'delete_url': reverse('consultations:intake_delete', args=[session.pk])}, status=202)


@login_required(login_url='accounts:login')
def intake_status(request, pk):
    session = get_object_or_404(AIIntakeSession, pk=pk, patient=request.user)
    if session.status == 'pending' and session.updated_at < timezone.now()-timedelta(minutes=2):
        AIIntakeSession.objects.filter(pk=pk, status='pending').update(status='failed', error_code='timeout')
        session.refresh_from_db()
    data = {'status': session.status, 'duration_ms': session.duration_ms}
    if session.status == 'ready':
        result = session.result
        doctors = eligible_doctors().filter(main_specialty_id=result.get('specialty_id'))[:8] if result.get('specialty_id') else []
        data.update(result=result, doctors=[{'name': doctor.get_full_name(), 'specialty': doctor.main_specialty.name,
            'url': reverse('appointments:book_slot', args=[doctor.pk])} for doctor in doctors])
    elif session.status in ('failed', 'urgent'):
        errors = {'configuration': ui_gettext('Le service IA n’est pas configuré. Contactez l’administrateur.'),
                  'queue': ui_gettext('Le traitement n’a pas pu démarrer. Vérifiez le worker d’orientation.'),
                  'timeout': ui_gettext('Le délai est dépassé. Vérifiez le worker et réessayez.'),
                  'rate_limit': ui_gettext('Le fournisseur IA est très sollicité. Réessayez plus tard.'),
                  'invalid_response': ui_gettext('La réponse IA a été refusée par les contrôles. Aucune orientation n’est affichée.')}
        data['error'] = URGENT if session.status == 'urgent' else errors.get(session.error_code, FAILURE)
    response = JsonResponse(data)
    response['Cache-Control'] = 'no-store'
    return response


@login_required(login_url='accounts:login')
@require_POST
def intake_delete(request, pk):
    get_object_or_404(AIIntakeSession, pk=pk, patient=request.user).delete()
    return JsonResponse({'deleted': True})
