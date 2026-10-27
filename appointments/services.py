from django.utils.translation import gettext_lazy as ui_gettext
"""
Business logic for appointments.

Views must go through these functions: they hold the slot rules, check who is
allowed to change an appointment and notify the other side.
"""

import logging
from collections import OrderedDict
from datetime import datetime, timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from accounts.models import DoctorProfile, User
from notifications.models import Notification
from notifications.services import notify

from .models import MAX_DURATION_MINUTES, Appointment

logger = logging.getLogger(__name__)

SLOT_MINUTES = 30
CHANGE_DEADLINE = timedelta(hours=24)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def display_name(user):
    return user.get_full_name() or user.email


def doctor_name(user):
    return f"Dr. {display_name(user)}"


def format_start(appointment):
    return f"{timezone.localtime(appointment.start):%a %d %b %Y at %H:%M}"


def approved_doctors():
    return User.objects.filter(
        role=User.Role.DOCTOR,
        is_active=True,
        doctor_profile__status=DoctorProfile.Status.APPROVED,
    )


def _link(appointment):
    return reverse("appointments:detail", args=[appointment.pk])


# ─────────────────────────────────────────────────────────────────────────────
# Free slots
# ─────────────────────────────────────────────────────────────────────────────

def get_free_slots(doctor, days=14, now=None, exclude_appointment=None):
    """
    Return the doctor's free 30-minute slots (aware datetimes, sorted) for the
    next `days` days: weekly Availability (is_free=True) minus active
    appointments minus times already passed.
    """
    now = now or timezone.now()
    tz = timezone.get_current_timezone()
    today = timezone.localtime(now).date()
    window_end = datetime.combine(today + timedelta(days=days), datetime.min.time(), tz)

    availability = {}
    for slot in doctor.availability_slots.filter(is_free=True):
        availability.setdefault(slot.weekday, []).append(slot)

    taken = Appointment.objects.filter(
        doctor=doctor,
        status__in=Appointment.ACTIVE_STATUSES,
        start__lt=window_end,
        start__gt=now - timedelta(minutes=MAX_DURATION_MINUTES),
    )
    if exclude_appointment is not None:
        taken = taken.exclude(pk=exclude_appointment.pk)
    busy = [(a.start, a.end) for a in taken]

    step = timedelta(minutes=SLOT_MINUTES)
    slots = []
    for offset in range(days):
        day = today + timedelta(days=offset)
        for block in availability.get(day.weekday(), []):
            current = datetime.combine(day, block.start_time, tz)
            block_end = datetime.combine(day, block.end_time, tz)
            while current + step <= block_end:
                slot_end = current + step
                is_busy = any(start < slot_end and current < end for start, end in busy)
                if current > now and not is_busy:
                    slots.append(current)
                current = slot_end
    return sorted(set(slots))


def group_slots_by_day(slots):
    """{date: [datetime, ...]} in chronological order, for templates."""
    grouped = OrderedDict()
    for slot in slots:
        grouped.setdefault(timezone.localtime(slot).date(), []).append(slot)
    return grouped


# ─────────────────────────────────────────────────────────────────────────────
# Booking / rescheduling
# ─────────────────────────────────────────────────────────────────────────────

def _save_validated(appointment):
    """full_clean + save, turning a lost race on the unique constraint into a clean error."""
    try:
        with transaction.atomic():
            # Lock the doctor row so two bookings for the same doctor are serialized.
            User.objects.select_for_update().get(pk=appointment.doctor_id)
            appointment.full_clean()
            appointment.save()
    except IntegrityError:
        raise ValidationError(ui_gettext("This slot was just taken. Please choose another one."))
    return appointment


def queue_risk_computation(appointment_id):
    """Ask Celery to compute the no-show risk once the transaction is committed."""
    def _send():
        try:
            from .tasks import compute_no_show_risk

            compute_no_show_risk.delay(appointment_id)
        except Exception:  # broker down: keep the booking, show "Risk not available"
            logger.exception("Could not queue no-show risk task for appointment %s", appointment_id)
            Appointment.objects.filter(pk=appointment_id).update(
                risk_status=Appointment.RiskStatus.FAILED
            )

    transaction.on_commit(_send)


def book_appointment(patient, doctor, start, mode, reason):
    if patient.role != User.Role.PATIENT:
        raise PermissionDenied("Only patients can book appointments.")
    appointment = Appointment(
        patient=patient,
        doctor=doctor,
        start=start,
        mode=mode,
        reason=reason,
        status=Appointment.Status.PENDING,
    )
    _save_validated(appointment)
    notify(
        doctor,
        f"New appointment request from {display_name(patient)} on {format_start(appointment)}.",
        Notification.Type.APPOINTMENT,
        _link(appointment),
    )
    queue_risk_computation(appointment.pk)
    return appointment


def reschedule_appointment(appointment, user, new_start):
    if user.pk != appointment.patient_id:
        raise PermissionDenied("Only the patient can reschedule this appointment.")
    if not appointment.can_be_changed_by_patient:
        raise ValidationError(ui_gettext("Appointments can only be changed more than 24 hours in advance."))

    appointment.start = new_start
    appointment.status = Appointment.Status.PENDING
    appointment.reminder_sent = False
    appointment.early_reminder_sent = False
    appointment.no_show_risk = None
    appointment.risk_status = Appointment.RiskStatus.PENDING
    try:
        _save_validated(appointment)
    except ValidationError:
        appointment.refresh_from_db()
        raise
    notify(
        appointment.doctor,
        f"{display_name(appointment.patient)} moved their appointment to "
        f"{format_start(appointment)}. Please confirm it again.",
        Notification.Type.APPOINTMENT,
        _link(appointment),
    )
    queue_risk_computation(appointment.pk)
    return appointment


# ─────────────────────────────────────────────────────────────────────────────
# Status changes
# ─────────────────────────────────────────────────────────────────────────────

def _check_doctor(appointment, user):
    if user.pk != appointment.doctor_id:
        raise PermissionDenied("Only the doctor of this appointment can do this.")


def _check_status(appointment, allowed, action):
    if appointment.status not in allowed:
        raise ValidationError(
            f"A {appointment.get_status_display().lower()} appointment cannot be {action}."
        )


def _set_status(appointment, status, **extra):
    appointment.status = status
    for field, value in extra.items():
        setattr(appointment, field, value)
    appointment.save(update_fields=["status", "updated_at", *extra])
    return appointment


def confirm_appointment(appointment, user):
    _check_doctor(appointment, user)
    _check_status(appointment, [Appointment.Status.PENDING], "confirmed")
    if appointment.start <= timezone.now():
        raise ValidationError(ui_gettext("This appointment is already in the past."))
    _set_status(appointment, Appointment.Status.CONFIRMED)
    notify(
        appointment.patient,
        f"{doctor_name(appointment.doctor)} confirmed your appointment on {format_start(appointment)}.",
        Notification.Type.APPOINTMENT,
        _link(appointment),
    )
    return appointment


def reject_appointment(appointment, user, reason=""):
    _check_doctor(appointment, user)
    _check_status(appointment, [Appointment.Status.PENDING], "rejected")
    reason = (reason or "").strip()
    _set_status(appointment, Appointment.Status.REJECTED, status_note=reason)
    message = f"{doctor_name(appointment.doctor)} declined your appointment on {format_start(appointment)}."
    if reason:
        message += f" Reason: {reason}"
    notify(appointment.patient, message, Notification.Type.APPOINTMENT, _link(appointment))
    return appointment


def cancel_appointment(appointment, user):
    if user.pk != appointment.patient_id:
        raise PermissionDenied("Only the patient can cancel this appointment.")
    _check_status(appointment, Appointment.ACTIVE_STATUSES, "cancelled")
    if appointment.start - timezone.now() <= CHANGE_DEADLINE:
        raise ValidationError(ui_gettext("Appointments can only be cancelled more than 24 hours in advance."))
    _set_status(appointment, Appointment.Status.CANCELLED)
    notify(
        appointment.doctor,
        f"{display_name(appointment.patient)} cancelled the appointment on {format_start(appointment)}.",
        Notification.Type.APPOINTMENT,
        _link(appointment),
    )
    return appointment


def _check_started(appointment):
    if appointment.start > timezone.now():
        raise ValidationError(ui_gettext("This appointment has not started yet."))


def complete_appointment(appointment, user):
    _check_doctor(appointment, user)
    _check_status(appointment, [Appointment.Status.CONFIRMED], "marked as completed")
    _check_started(appointment)
    _set_status(appointment, Appointment.Status.COMPLETED)
    notify(
        appointment.patient,
        f"Your appointment with {doctor_name(appointment.doctor)} on {format_start(appointment)} "
        "is marked as completed.",
        Notification.Type.APPOINTMENT,
        _link(appointment),
    )
    return appointment


def mark_no_show(appointment, user):
    _check_doctor(appointment, user)
    _check_status(appointment, [Appointment.Status.CONFIRMED], "marked as no-show")
    _check_started(appointment)
    _set_status(appointment, Appointment.Status.NO_SHOW)
    notify(
        appointment.patient,
        f"You were marked as absent for your appointment with {doctor_name(appointment.doctor)} "
        f"on {format_start(appointment)}. Please cancel in advance next time.",
        Notification.Type.APPOINTMENT,
        _link(appointment),
    )
    return appointment


# ─────────────────────────────────────────────────────────────────────────────
# Reminders (run every hour by Celery beat)
# ─────────────────────────────────────────────────────────────────────────────

def send_due_reminders(now=None):
    """
    Notify patients 24h before confirmed appointments, plus an earlier 48h
    reminder when the AI risk is high. Returns how many of each were sent.
    """
    from .models import RISK_HIGH_THRESHOLD

    now = now or timezone.now()
    confirmed = Appointment.objects.filter(
        status=Appointment.Status.CONFIRMED, start__gt=now
    ).select_related("patient", "doctor")

    sent = {"reminders": 0, "early_reminders": 0}

    early_due = confirmed.filter(
        early_reminder_sent=False,
        reminder_sent=False,
        no_show_risk__gte=RISK_HIGH_THRESHOLD,
        start__gt=now + timedelta(hours=24),
        start__lte=now + timedelta(hours=48),
    )
    for appointment in early_due:
        notify(
            appointment.patient,
            f"Reminder: you have an appointment with {doctor_name(appointment.doctor)} on "
            f"{format_start(appointment)}. If you cannot come, please cancel so someone else can get the slot.",
            Notification.Type.REMINDER,
            _link(appointment),
        )
        appointment.early_reminder_sent = True
        appointment.save(update_fields=["early_reminder_sent", "updated_at"])
        sent["early_reminders"] += 1

    for appointment in confirmed.filter(reminder_sent=False, start__lte=now + timedelta(hours=24)):
        notify(
            appointment.patient,
            f"Reminder: your appointment with {doctor_name(appointment.doctor)} is on "
            f"{format_start(appointment)}"
            f"{' (video call)' if appointment.mode == Appointment.Mode.VISIO else ''}.",
            Notification.Type.REMINDER,
            _link(appointment),
        )
        appointment.reminder_sent = True
        appointment.save(update_fields=["reminder_sent", "updated_at"])
        sent["reminders"] += 1

    return sent
