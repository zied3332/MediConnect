from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.models import DoctorProfile, User
from core.models import Specialty
from dashboard.views import approved_doctor_required, role_required

from . import services
from .forms import (
    AdminFilterForm,
    BookingForm,
    DoctorFilterForm,
    RejectForm,
    RescheduleForm,
    SpecialtyChoiceForm,
    slot_value,
)
from .models import Appointment

PAGE_SIZE = 10


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _context(request, page_title, **extra):
    return {
        "page_title": page_title,
        "dashboard_role": request.user.role,
        "active_nav": "appointments",
        **extra,
    }


def _paginate(request, queryset):
    page = Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return page, params.urlencode()


def _error_text(error):
    return " ".join(error.messages) if hasattr(error, "messages") else str(error)


def _safe_next(request, fallback):
    target = request.POST.get("next", "")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return target
    return fallback


def _slot_days(slots):
    """Slots grouped by day with their radio values, for the slot picker."""
    grouped = services.group_slots_by_day(slots)
    return [
        {"day": day, "slots": [{"value": slot_value(s), "time": timezone.localtime(s)} for s in day_slots]}
        for day, day_slots in grouped.items()
    ]


def _appointment_for(user, pk):
    """Fetch an appointment the user is allowed to see, else 404."""
    queryset = Appointment.objects.select_related("patient", "doctor", "doctor__main_specialty")
    if user.role == User.Role.PATIENT:
        queryset = queryset.filter(patient=user)
    elif user.role == User.Role.DOCTOR:
        queryset = queryset.filter(doctor=user)
    elif user.role != User.Role.ADMIN:
        raise Http404
    return get_object_or_404(queryset, pk=pk)


# ─────────────────────────────────────────────────────────────────────────────
# Patient
# ─────────────────────────────────────────────────────────────────────────────

@role_required("patient")
def my_appointments(request):
    tab = "past" if request.GET.get("tab") == "past" else "upcoming"
    now = timezone.now()
    base = Appointment.objects.filter(patient=request.user).select_related(
        "doctor", "doctor__main_specialty"
    )
    upcoming_q = Q(start__gt=now, status__in=Appointment.ACTIVE_STATUSES)
    if tab == "upcoming":
        appointments = base.filter(upcoming_q).order_by("start")
    else:
        appointments = base.exclude(upcoming_q).order_by("-start")
    page, query_string = _paginate(request, appointments)
    return render(
        request,
        "appointments/patient/list.html",
        _context(
            request,
            "Appointments",
            tab=tab,
            page_obj=page,
            query_string=query_string,
            upcoming_count=base.filter(upcoming_q).count(),
        ),
    )


@role_required("patient")
def book_appointment(request):
    """Step 1 and 2: choose a specialty, then one of its approved doctors."""
    form = SpecialtyChoiceForm(request.GET or None)
    specialty = form.cleaned_data["specialty"] if form.is_valid() else None
    doctors = None
    if specialty:
        doctors = (
            services.approved_doctors()
            .filter(main_specialty=specialty)
            .order_by("last_name", "first_name")
        )
    specialties = Specialty.objects.annotate(
        doctor_count=Count(
            "doctors",
            filter=Q(
                doctors__role=User.Role.DOCTOR,
                doctors__is_active=True,
                doctors__doctor_profile__status=DoctorProfile.Status.APPROVED,
            ),
        )
    )
    return render(
        request,
        "appointments/patient/book_doctor.html",
        _context(
            request,
            "Book appointment",
            form=form,
            specialty=specialty,
            doctors=doctors,
            specialties=specialties,
        ),
    )


@role_required("patient")
def book_with_doctor(request, doctor_id):
    """Step 3: pick a free slot, the mode and the reason."""
    doctor = get_object_or_404(
        services.approved_doctors().select_related("main_specialty"), pk=doctor_id
    )
    slots = services.get_free_slots(doctor)
    form = BookingForm(request.POST or None, slots=slots)

    if request.method == "POST" and form.is_valid():
        try:
            appointment = services.book_appointment(
                patient=request.user,
                doctor=doctor,
                start=form.cleaned_data["slot"],
                mode=form.cleaned_data["mode"],
                reason=form.cleaned_data["reason"],
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(
                request,
                f"Your request was sent to {services.doctor_name(doctor)}. "
                "You will be notified when it is confirmed.",
            )
            return redirect(appointment)

    return render(
        request,
        "appointments/patient/book_slot.html",
        _context(
            request,
            "Book appointment",
            doctor=doctor,
            form=form,
            days=_slot_days(slots),
            selected=form["slot"].value(),
        ),
    )


@role_required("patient")
def reschedule_appointment(request, pk):
    appointment = _appointment_for(request.user, pk)
    if not appointment.can_be_changed_by_patient:
        messages.error(request, "This appointment can no longer be changed (less than 24 hours left).")
        return redirect(appointment)

    slots = services.get_free_slots(appointment.doctor, exclude_appointment=appointment)
    slots = [s for s in slots if s != appointment.start]
    form = RescheduleForm(request.POST or None, slots=slots)
    if request.method == "POST" and form.is_valid():
        try:
            services.reschedule_appointment(appointment, request.user, form.cleaned_data["slot"])
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Your appointment was moved. The doctor needs to confirm it again.")
            return redirect(appointment)

    return render(
        request,
        "appointments/patient/reschedule.html",
        _context(
            request,
            "Reschedule",
            appointment=appointment,
            form=form,
            days=_slot_days(slots),
            selected=form["slot"].value(),
        ),
    )


@role_required("patient")
def cancel_appointment(request, pk):
    appointment = _appointment_for(request.user, pk)
    if request.method == "POST":
        try:
            services.cancel_appointment(appointment, request.user)
        except ValidationError as error:
            messages.error(request, _error_text(error))
        else:
            messages.success(request, "Your appointment was cancelled.")
        return redirect(appointment)
    return render(
        request,
        "appointments/patient/cancel_confirm.html",
        _context(request, "Cancel appointment", appointment=appointment),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Shared detail page
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def appointment_detail(request, pk):
    user = request.user
    if user.role == User.Role.DOCTOR:
        profile = DoctorProfile.objects.filter(user=user).first()
        if not profile or not profile.can_access_dashboard:
            return redirect("accounts:doctor_status")
    appointment = _appointment_for(user, pk)
    return render(
        request,
        "appointments/detail.html",
        _context(
            request,
            "Appointment",
            appointment=appointment,
            reject_form=RejectForm(),
            now=timezone.now(),
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Doctor
# ─────────────────────────────────────────────────────────────────────────────

@approved_doctor_required
def doctor_appointments(request):
    form = DoctorFilterForm(request.GET or None)
    filters = form.cleaned_data if form.is_valid() else {}
    when = filters.get("when") or "upcoming"
    now = timezone.now()

    appointments = Appointment.objects.filter(doctor=request.user).select_related("patient")
    if filters.get("status"):
        appointments = appointments.filter(status=filters["status"])
    if filters.get("date"):
        appointments = appointments.filter(start__date=filters["date"]).order_by("start")
    elif when == "upcoming":
        appointments = appointments.filter(start__gte=now).order_by("start")
    elif when == "past":
        appointments = appointments.filter(start__lt=now).order_by("-start")
    else:
        appointments = appointments.order_by("-start")

    page, query_string = _paginate(request, appointments)
    return render(
        request,
        "appointments/doctor/list.html",
        _context(
            request,
            "Appointments",
            filter_form=form,
            page_obj=page,
            query_string=query_string,
            now=now,
            pending_count=Appointment.objects.filter(
                doctor=request.user, status=Appointment.Status.PENDING, start__gt=now
            ).count(),
        ),
    )


def _retry_risk(appointment, user):
    if appointment.no_show_risk is not None:
        raise ValidationError("The risk is already available.")
    Appointment.objects.filter(pk=appointment.pk).update(risk_status=Appointment.RiskStatus.PENDING)
    services.queue_risk_computation(appointment.pk)


DOCTOR_ACTIONS = {
    "confirm": (services.confirm_appointment, "Appointment confirmed. The patient was notified."),
    "reject": (services.reject_appointment, "Appointment rejected. The patient was notified."),
    "complete": (services.complete_appointment, "Appointment marked as completed."),
    "no-show": (services.mark_no_show, "Appointment marked as no-show."),
    "retry-risk": (_retry_risk, "The risk estimate is being computed again."),
}


@approved_doctor_required
@require_POST
def doctor_action(request, pk, action):
    if action not in DOCTOR_ACTIONS:
        raise Http404
    appointment = get_object_or_404(Appointment, pk=pk, doctor=request.user)
    handler, success_message = DOCTOR_ACTIONS[action]
    try:
        if action == "reject":
            form = RejectForm(request.POST)
            reason = form.cleaned_data["reason"] if form.is_valid() else ""
            handler(appointment, request.user, reason)
        else:
            handler(appointment, request.user)
    except (ValidationError, PermissionDenied) as error:
        messages.error(request, _error_text(error))
    else:
        messages.success(request, success_message)
    return redirect(_safe_next(request, reverse("appointments:doctor_list")))


# ─────────────────────────────────────────────────────────────────────────────
# Admin
# ─────────────────────────────────────────────────────────────────────────────

@role_required("admin")
def admin_appointments(request):
    form = AdminFilterForm(request.GET or None)
    appointments = Appointment.objects.select_related("patient", "doctor").order_by("-start")
    if form.is_valid():
        data = form.cleaned_data
        if data.get("doctor"):
            appointments = appointments.filter(doctor=data["doctor"])
        if data.get("patient"):
            appointments = appointments.filter(patient=data["patient"])
        if data.get("status"):
            appointments = appointments.filter(status=data["status"])
        if data.get("date"):
            appointments = appointments.filter(start__date=data["date"])

    page, query_string = _paginate(request, appointments)
    return render(
        request,
        "appointments/admin/list.html",
        _context(
            request,
            "Appointments",
            filter_form=form,
            page_obj=page,
            query_string=query_string,
            total=Appointment.objects.count(),
        ),
    )


@role_required("admin")
@require_POST
def admin_delete_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    appointment.delete()
    messages.success(request, "The appointment was deleted.")
    return redirect(_safe_next(request, reverse("appointments:admin_list")))


@role_required("admin")
def admin_ai_model(request):
    from .ml.predictor import load_metrics, model_path

    metrics = load_metrics()
    report_rows, confusion = [], None
    if metrics:
        report = metrics.get("classification_report", {})
        labels = {"show": "Showed up", "no_show": "No-show", "macro avg": "Macro average",
                  "weighted avg": "Weighted average"}
        for key, label in labels.items():
            if key in report:
                row = report[key]
                report_rows.append({
                    "label": label,
                    "precision": row["precision"],
                    "recall": row["recall"],
                    "f1": row["f1-score"],
                    "support": int(row["support"]),
                })
        matrix = metrics.get("confusion_matrix")
        if matrix and len(matrix) == 2:
            (tn, fp), (fn, tp) = matrix
            confusion = {"tn": tn, "fp": fp, "fn": fn, "tp": tp}
    return render(
        request,
        "appointments/admin/ai_model.html",
        _context(
            request,
            "AI model",
            active_nav="ai_model",
            metrics=metrics,
            report_rows=report_rows,
            confusion=confusion,
            model_available=model_path().exists(),
        ),
    )
