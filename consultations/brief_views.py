"""Doctor-only generation/review, patient access only after explicit publication."""
import uuid
from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from appointments.models import _doctor_is_approved
from notifications.services import notify
from .ai import ERRORS, SECTIONS, source_hash
from .models import Consultation, PatientBrief
from .tasks import generate_patient_brief
from .views import _context, _visible


class BriefApprovalForm(forms.Form):
    generation_id = forms.UUIDField(widget=forms.HiddenInput)
    constat = forms.CharField(label="Ce qui a été constaté", max_length=2000, widget=forms.Textarea(attrs={"rows": 4}))
    consignes = forms.CharField(label="Les consignes mentionnées", max_length=2000, widget=forms.Textarea(attrs={"rows": 4}))
    suivi = forms.CharField(label="La suite prévue", max_length=2000, widget=forms.Textarea(attrs={"rows": 4}))
    confirm = forms.BooleanField(label="J'ai comparé chaque rubrique avec le compte rendu et je valide sa publication au patient.")


def _doctor_consultation(request, pk):
    return get_object_or_404(Consultation, pk=pk, appointment__doctor=request.user)


def _current(brief, consultation):
    return brief is not None and brief.source_hash == source_hash(consultation)


def _expire(brief):
    if brief and brief.status == "pending" and brief.updated_at < timezone.now() - timedelta(minutes=3):
        PatientBrief.objects.filter(pk=brief.pk, generation_id=brief.generation_id, status="pending").update(status="failed", error_code="timeout")
        brief.refresh_from_db()


@login_required(login_url="accounts:login")
def brief_page(request, pk):
    consultation = get_object_or_404(_visible(request.user), pk=pk)
    brief = PatientBrief.objects.filter(consultation=consultation).first()
    _expire(brief)
    current = _current(brief, consultation)
    if request.user.role == "patient":
        if not current or brief.status != "published":
            return HttpResponseForbidden("La fiche patient n'est pas encore validée par votre médecin.")
        return render(request, "consultations/brief_patient.html", _context(request, consultation=consultation, brief=brief))
    if not _doctor_is_approved(request.user):
        return HttpResponseForbidden("Votre compte médecin doit être approuvé.")
    initial = {"generation_id": brief.generation_id} if brief else {}
    if current and brief.status in ("ready", "published"):
        initial.update({card["key"]: card["text"] for card in (brief.approved_cards if brief.status == "published" else brief.cards)})
    template = "consultations/brief_fragment.html" if request.GET.get("fragment") == "1" else "consultations/brief_review.html"
    return render(request, template, _context(request,
        consultation=consultation, brief=brief, current=current,
        form=BriefApprovalForm(initial=initial),
        api_configured=bool(settings.ANTHROPIC_API_KEY),
        error_message=ERRORS.get(brief.error_code, ERRORS["unavailable"]) if brief and brief.status == "failed" else "",
        eager=settings.CELERY_TASK_ALWAYS_EAGER,
    ))


@login_required(login_url="accounts:login")
@require_POST
def brief_generate(request, pk):
    if request.user.role != "doctor" or not _doctor_is_approved(request.user):
        return JsonResponse({"error": "Seul le médecin approuvé concerné peut générer cette fiche."}, status=403)
    _doctor_consultation(request, pk)
    if request.POST.get("consent") != "yes":
        return JsonResponse({"error": "Confirmez l'envoi du diagnostic et des notes au service Anthropic."}, status=400)
    if not settings.ANTHROPIC_API_KEY:
        return JsonResponse({"error": ERRORS["configuration"]}, status=503)
    with transaction.atomic():
        consultation = Consultation.objects.select_for_update().get(pk=pk)
        if len(consultation.diagnostic) + len(consultation.notes) > 12000:
            return JsonResponse({"error": ERRORS["too_long"]}, status=400)
        brief = PatientBrief.objects.filter(consultation=consultation).first()
        _expire(brief)
        if brief and brief.status == "pending":
            return JsonResponse({"error": "Une génération est déjà en cours. Patientez avant de réessayer."}, status=409)
        if brief and brief.updated_at > timezone.now() - timedelta(seconds=20):
            return JsonResponse({"error": "Patientez 20 secondes entre deux générations."}, status=429)
        brief, _ = PatientBrief.objects.update_or_create(consultation=consultation, defaults={
            "status": "pending", "generation_id": uuid.uuid4(), "source_hash": source_hash(consultation),
            "cards": [], "approved_cards": [], "error_code": "", "model_name": "", "duration_ms": None,
            "published_at": None, "published_by": None,
        })
        brief_id, generation = brief.pk, str(brief.generation_id)

        def enqueue():
            try:
                generate_patient_brief.apply_async(args=[brief_id, generation], retry=False)
            except Exception:
                PatientBrief.objects.filter(pk=brief_id, generation_id=generation, status="pending").update(status="failed", error_code="queue")

        transaction.on_commit(enqueue)
    return JsonResponse({"status_url": reverse("consultations:brief_status", args=[pk])}, status=202)


@login_required(login_url="accounts:login")
def brief_status(request, pk):
    if request.user.role != "doctor" or not _doctor_is_approved(request.user):
        return JsonResponse({"error": "Accès réservé au médecin concerné."}, status=403)
    consultation = _doctor_consultation(request, pk)
    brief = get_object_or_404(PatientBrief, consultation=consultation)
    _expire(brief)
    if not _current(brief, consultation):
        return JsonResponse({"status": "failed", "error": ERRORS["source_changed"]})
    return JsonResponse({"status": brief.status, "error": ERRORS.get(brief.error_code, ERRORS["unavailable"]) if brief.status == "failed" else ""})


@login_required(login_url="accounts:login")
@require_POST
def brief_publish(request, pk):
    wants_json = "application/json" in request.headers.get("Accept", "")
    if request.user.role != "doctor" or not _doctor_is_approved(request.user):
        return HttpResponseForbidden("Seul le médecin concerné peut valider la fiche.")
    _doctor_consultation(request, pk)
    form = BriefApprovalForm(request.POST)
    if not form.is_valid():
        if wants_json:
            return JsonResponse({"error": "Complétez les trois rubriques et confirmez votre vérification."}, status=400)
        messages.error(request, "Complétez les trois rubriques et confirmez la vérification avant publication.")
        return redirect("consultations:brief", pk=pk)
    with transaction.atomic():
        consultation = Consultation.objects.select_for_update().get(pk=pk)
        brief = get_object_or_404(PatientBrief.objects.select_for_update(), consultation=consultation)
        if not _current(brief, consultation) or brief.status not in ("ready", "published") or brief.generation_id != form.cleaned_data["generation_id"]:
            if wants_json:
                return JsonResponse({"error": "Le compte rendu ou le brouillon a changé. Fermez puis rouvrez la fiche avant validation."}, status=409)
            messages.error(request, "Le compte rendu ou le brouillon a changé. Rechargez la page avant validation.")
            return redirect("consultations:brief", pk=pk)
        brief.approved_cards = [{"key": key, "title": title, "text": form.cleaned_data[key]} for key, title in SECTIONS]
        brief.status = "published"
        brief.published_at = timezone.now()
        brief.published_by = request.user
        brief.save()
        notify(consultation.appointment.patient, "Votre médecin a validé une fiche de lecture de votre consultation.", "system", link=reverse("consultations:brief", args=[pk]))
    if wants_json:
        return JsonResponse({"published": True})
    messages.success(request, "La fiche vérifiée est maintenant accessible au patient.")
    return redirect("consultations:brief", pk=pk)
