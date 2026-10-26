
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Count, Avg, OuterRef, Subquery
from django.core.paginator import Paginator
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from appointments.models import Appointment, _doctor_is_approved
from notifications.services import notify
from .forms import ConsultationForm, MessageForm, AvisForm
from .models import Consultation, Message, Avis


def _visible(user):
    qs = Consultation.objects.select_related(
        "appointment__doctor",
        "appointment__patient",
    )
    if user.role == "doctor":
        return qs.filter(appointment__doctor=user)
    if user.role == "patient":
        return qs.filter(appointment__patient=user)
    return qs.none()


def _context(request, **extra):
    return {
        "dashboard_role": request.user.role,
        "active_nav": "consultations",
        "page_title": "Consultations",
        **extra,
    }


def _search_people(queryset, query):
    for word in query.split()[:12]:
        queryset = queryset.filter(
            Q(appointment__patient__first_name__icontains=word)
            | Q(appointment__patient__last_name__icontains=word)
            | Q(appointment__doctor__first_name__icontains=word)
            | Q(appointment__doctor__last_name__icontains=word)
        )
    return queryset


@login_required(login_url="accounts:login")
def consultation_list(request):
    qs = _visible(request.user)
    total = qs.count()
    query = request.GET.get("q", "").strip()[:150]
    status = request.GET.get("status", "")

    if query:
        qs = _search_people(qs, query)

    if status in ("confirmed", "completed"):
        qs = qs.filter(appointment__status=status)

    page = Paginator(qs, 9).get_page(request.GET.get("page"))

    unread = (
        Message.objects.filter(
            consultation__in=_visible(request.user),
            lu=False,
        )
        .exclude(auteur=request.user)
        .count()
    )

    template = (
        "consultations/list_results.html"
        if request.headers.get("X-Live-Search") == "1"
        else "consultations/list.html"
    )

    return render(
        request,
        template,
        _context(
            request,
            consultations=page,
            page_obj=page,
            query=query,
            selected_status=status,
            total=total,
            unread=unread,
            completed=_visible(request.user)
            .filter(appointment__status="completed")
            .count(),
        ),
    )


@login_required(login_url="accounts:login")
def detail(request, pk):
    consultation = get_object_or_404(
        _visible(request.user),
        pk=pk,
    )

    avis = Avis.objects.filter(
        consultation=consultation
    ).first()

    from .models import PatientBrief
    from .ai import source_hash
    from medical_records.views import (
        can_access_patient_record,
        can_manage_consultation_prescriptions,
    )

    published_brief = PatientBrief.objects.filter(
        consultation=consultation,
        status="published",
        source_hash=source_hash(consultation),
    ).exists()

    appointment = consultation.appointment

    can_view_medical_record = (
        request.user.role == "doctor"
        and can_access_patient_record(
            request.user,
            appointment.patient_id,
        )
    )

    can_create_prescription = (
        request.user.role == "doctor"
        and can_manage_consultation_prescriptions(
            request.user,
            consultation,
        )
    )

    unread = (
        consultation.messages.filter(lu=False)
        .exclude(auteur=request.user)
        .count()
    )

    return render(
        request,
        "consultations/detail.html",
        _context(
            request,
            consultation=consultation,
            avis=avis,
            published_brief=published_brief,
            unread=unread,
            can_view_medical_record=can_view_medical_record,
            can_create_prescription=can_create_prescription,
        ),
    )


@login_required(login_url="accounts:login")
def edit(request, appointment_id):
    if request.user.role != "doctor" or not _doctor_is_approved(request.user):
        return HttpResponseForbidden(
            "Seul le médecin approuvé concerné peut rédiger la consultation."
        )

    with transaction.atomic():
        appointment = get_object_or_404(
            Appointment.objects.select_for_update(),
            pk=appointment_id,
            doctor=request.user,
        )

        if appointment.status not in (
            Appointment.Status.CONFIRMED,
            Appointment.Status.COMPLETED,
        ):
            return HttpResponseForbidden(
                "Le rendez-vous doit être confirmé ou terminé."
            )

        consultation = Consultation.objects.filter(
            appointment=appointment
        ).first()

        is_new = consultation is None

        if is_new:
            consultation = Consultation(appointment=appointment)

        form = ConsultationForm(
            request.POST if request.method == "POST" else None,
            instance=consultation,
        )

        if request.method == "POST" and form.is_valid():
            consultation = form.save()

            notify(
                appointment.patient,
                (
                    "Votre compte rendu de consultation est disponible."
                    if is_new
                    else "Votre compte rendu de consultation a été mis à jour."
                ),
                "system",
                link=reverse(
                    "consultations:detail",
                    args=[consultation.pk],
                ),
            )

            messages.success(
                request,
                "Consultation enregistrée.",
            )

            return redirect(
                "consultations:detail",
                pk=consultation.pk,
            )

    return render(
        request,
        "consultations/form.html",
        _context(
            request,
            form=form,
            appointment=appointment,
        ),
    )


@login_required(login_url="accounts:login")
def conversation(request, pk):
    consultation = get_object_or_404(
        _visible(request.user),
        pk=pk,
    )

    instance = Message(
        consultation=consultation,
        auteur=request.user,
    )

    form = MessageForm(
        request.POST if request.method == "POST" else None,
        instance=instance,
    )

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            form.save()

            appointment = consultation.appointment

            recipient = (
                appointment.patient
                if request.user.pk == appointment.doctor_id
                else appointment.doctor
            )

            notify(
                recipient,
                "Vous avez reçu un message concernant une consultation.",
                "system",
                link=reverse(
                    "consultations:conversation",
                    args=[pk],
                ),
            )

        return redirect(
            "consultations:conversation",
            pk=pk,
        )

    consultation.messages.exclude(
        auteur=request.user
    ).filter(
        lu=False
    ).update(lu=True)

    return render(
        request,
        "consultations/conversation.html",
        _context(
            request,
            consultation=consultation,
            thread=consultation.messages.select_related("auteur"),
            form=form,
            active_nav="consultation_messages",
        ),
    )


@login_required(login_url="accounts:login")
def inbox(request):
    latest = Message.objects.filter(
        consultation_id=OuterRef("pk")
    ).order_by("-date", "-pk")

    qs = _visible(request.user).annotate(
        message_count=Count("messages"),
        unread_count=Count(
            "messages",
            filter=Q(messages__lu=False)
            & ~Q(messages__auteur=request.user),
        ),
        last_message=Subquery(
            latest.values("contenu")[:1]
        ),
        last_activity=Subquery(
            latest.values("date")[:1]
        ),
    ).filter(
        message_count__gt=0
    ).order_by("-last_activity", "-pk")

    query = request.GET.get("q", "").strip()[:150]
    unread_only = request.GET.get("unread") == "1"

    if query:
        qs = _search_people(qs, query)

    if unread_only:
        qs = qs.filter(unread_count__gt=0)

    page = Paginator(qs, 9).get_page(
        request.GET.get("page")
    )

    template = (
        "consultations/inbox_results.html"
        if request.headers.get("X-Live-Search") == "1"
        else "consultations/inbox.html"
    )

    return render(
        request,
        template,
        _context(
            request,
            threads=page,
            page_obj=page,
            query=query,
            unread_only=unread_only,
            active_nav="consultation_messages",
        ),
    )


@login_required(login_url="accounts:login")
def review_edit(request, pk):
    consultation = get_object_or_404(
        _visible(request.user),
        pk=pk,
    )

    if request.user.role != "patient":
        return HttpResponseForbidden(
            "Seul le patient concerné peut laisser un avis."
        )

    if consultation.appointment.status != Appointment.Status.COMPLETED:
        return HttpResponseForbidden(
            "Le rendez-vous doit être terminé pour laisser un avis."
        )

    with transaction.atomic():
        Consultation.objects.select_for_update().get(
            pk=pk
        )

        instance = (
            Avis.objects.filter(
                consultation=consultation
            ).first()
            or Avis(
                consultation=consultation,
                patient=request.user,
                medecin=consultation.appointment.doctor,
            )
        )

        form = AvisForm(
            request.POST if request.method == "POST" else None,
            instance=instance,
        )

        if request.method == "POST" and form.is_valid():
            form.save()

            notify(
                consultation.appointment.doctor,
                "Un patient a partagé son avis sur une consultation.",
                "system",
                link=reverse("consultations:reviews"),
            )

            messages.success(
                request,
                "Merci ! Votre avis a été enregistré.",
            )

            return redirect(
                "consultations:detail",
                pk=pk,
            )

    return render(
        request,
        "consultations/review_form.html",
        _context(
            request,
            consultation=consultation,
            form=form,
            active_nav="consultation_reviews",
        ),
    )


@login_required(login_url="accounts:login")
@require_POST
def review_delete(request, pk):
    qs = (
        Avis.objects.all()
        if request.user.role == "admin"
        else Avis.objects.filter(patient=request.user)
    )

    avis = get_object_or_404(qs, pk=pk)
    consultation_id = avis.consultation_id

    avis.delete()

    messages.success(
        request,
        "Votre avis a été supprimé.",
    )

    if request.user.role == "admin":
        return redirect("consultations:reviews")

    return redirect(
        "consultations:detail",
        pk=consultation_id,
    )


@login_required(login_url="accounts:login")
def message_edit(request, pk):
    message = get_object_or_404(
        Message,
        pk=pk,
        auteur=request.user,
        consultation__in=_visible(request.user),
    )

    form = MessageForm(
        request.POST if request.method == "POST" else None,
        instance=message,
    )

    if request.method == "POST" and form.is_valid():
        message = form.save(commit=False)
        message.lu = False
        message.save()

        return redirect(
            "consultations:conversation",
            pk=message.consultation_id,
        )

    return render(
        request,
        "consultations/message_form.html",
        _context(
            request,
            form=form,
            message=message,
            active_nav="consultation_messages",
        ),
    )


@login_required(login_url="accounts:login")
@require_POST
def message_delete(request, pk):
    message = get_object_or_404(
        Message,
        pk=pk,
        auteur=request.user,
        consultation__in=_visible(request.user),
    )

    consultation_id = message.consultation_id
    message.delete()

    return redirect(
        "consultations:conversation",
        pk=consultation_id,
    )


@login_required(login_url="accounts:login")
def reviews(request):
    if request.user.role == "doctor":
        qs = Avis.objects.filter(medecin=request.user)
    elif request.user.role == "patient":
        qs = Avis.objects.filter(patient=request.user)
    elif request.user.role == "admin":
        qs = Avis.objects.all()
    else:
        qs = Avis.objects.none()

    stats = qs.aggregate(
        average=Avg("note"),
        total=Count("pk"),
    )

    eligible = (
        _visible(request.user).filter(
            appointment__status="completed",
            avis__isnull=True,
        )
        if request.user.role == "patient"
        else Consultation.objects.none()
    )

    page = Paginator(
        qs.select_related(
            "patient",
            "medecin",
            "consultation__appointment",
        ),
        10,
    ).get_page(request.GET.get("page"))

    return render(
        request,
        "consultations/reviews.html",
        _context(
            request,
            reviews=page,
            page_obj=page,
            stats=stats,
            eligible=eligible,
            active_nav="consultation_reviews",
        ),
    )


@login_required(login_url="accounts:login")
def delete(request, pk):
    consultation = get_object_or_404(
        _visible(request.user),
        pk=pk,
    )

    if request.user.role != "doctor" or not _doctor_is_approved(request.user):
        return HttpResponseForbidden(
            "Seul le médecin concerné peut supprimer ce compte rendu."
        )

    if request.method == "POST":
        consultation.delete()

        messages.success(
            request,
            "La consultation et ses échanges associés ont été supprimés.",
        )

        return redirect("consultations:list")

    return render(
        request,
        "consultations/delete.html",
        _context(
            request,
            consultation=consultation,
        ),
    )
