from django.utils.translation import gettext_lazy as ui_gettext

from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Min, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import User
from appointments.models import Appointment
from consultations.models import Message
from specialty.models import Specialty
from django.core.paginator import Paginator


# ============================================================
# DECORATORS
# ============================================================

def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url="accounts:login")
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles:
                return HttpResponseForbidden(
                    "<h2>403 — Access denied</h2>"
                    f'<a href="{request.user.dashboard_url}">'
                    "Go to your dashboard →</a>"
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


@role_required("patient")
def patient_doctors(request):
    """Patient directory using the same approval rules as booking."""
    from appointments.services import approved_doctors

    approved = approved_doctors().select_related("main_specialty", "doctor_profile")
    query = request.GET.get("q", "").strip()[:150]
    selected = request.GET.get("specialty", "")
    specialties = list(Specialty.objects.order_by("name"))
    counts = dict(approved.values("main_specialty_id").annotate(total=Count("pk")).values_list("main_specialty_id", "total"))
    for specialty in specialties:
        specialty.doctor_count = counts.get(specialty.pk, 0)
    doctors = approved
    if selected:
        # Invalid filters have no matches rather than silently showing all doctors.
        doctors = doctors.filter(main_specialty_id=int(selected)) if selected.isdecimal() and len(selected) < 12 else doctors.none()
    for word in query.split()[:12]:
        doctors = doctors.filter(Q(first_name__icontains=word) | Q(last_name__icontains=word) | Q(main_specialty__name__icontains=word))
    page = Paginator(doctors.order_by("first_name", "last_name", "pk"), 9).get_page(request.GET.get("page"))
    context = {"dashboard_role": "patient", "active_nav": "patient_doctors", "page_title": ui_gettext("Mes médecins"),
               "specialties": specialties, "doctors": page, "page_obj": page, "query": query,
               "selected_specialty": selected, "doctor_total": approved.count(), "specialty_total": len(specialties)}
    template = "dashboard/patient/doctors_results.html" if request.headers.get("X-Live-Search") == "1" else "dashboard/patient/doctors.html"
    return render(request, template, context)


def approved_doctor_required(view_func):
    @wraps(view_func)
    @login_required(login_url="accounts:login")
    def wrapper(request, *args, **kwargs):
        user = request.user

        if user.role != "doctor":
            return HttpResponseForbidden(
                "<h2>403 — Access denied</h2>"
                f'<a href="{user.dashboard_url}">'
                "Go to your dashboard →</a>"
            )

        try:
            profile = user.doctor_profile
        except Exception:
            return redirect("accounts:doctor_status")

        if not profile.can_access_dashboard:
            return redirect("accounts:doctor_status")

        return view_func(request, *args, **kwargs)

    return wrapper


# ============================================================
# ADMIN — OVERVIEW
# ============================================================

@role_required("admin")
def admin_overview(request):
    from accounts.models import DoctorProfile

    pending_count = DoctorProfile.objects.filter(
        status=DoctorProfile.Status.PENDING_REVIEW
    ).count()

    context = {
        "page_title": ui_gettext("Overview"),
        "dashboard_role": "admin",
        "active_nav": "overview",
        "stats": [
            {
                "label": ui_gettext("Total patients"),
                "value": "1,248",
                "change": "+12.5%",
                "icon": "P",
            },
            {
                "label": ui_gettext("Active doctors"),
                "value": "86",
                "change": "+4.2%",
                "icon": "D",
            },
            {
                "label": ui_gettext("Appointments"),
                "value": "324",
                "change": "+8.1%",
                "icon": "C",
            },
            {
                "label": ui_gettext("Pending approvals"),
                "value": str(pending_count),
                "change": ui_gettext("Needs review"),
                "icon": "!",
            },
        ],
        "recent_activity": [
            {
                "title": ui_gettext("New doctor registration"),
                "description": "A doctor submitted a verification request.",
                "time": "10 min ago",
            },
            {
                "title": ui_gettext("Appointment booked"),
                "description": "A new consultation was scheduled.",
                "time": "25 min ago",
            },
            {
                "title": ui_gettext("New patient account"),
                "description": "A patient joined MediConnect.",
                "time": "1 hour ago",
            },
        ],
        "pending_doctors": DoctorProfile.objects.filter(
            status=DoctorProfile.Status.PENDING_REVIEW
        ).select_related("user").order_by("-submitted_at")[:5],
    }

    return render(request, "dashboard/admin/overview.html", context)


# ============================================================
# ADMIN — DOCTOR APPLICATIONS
# ============================================================

@role_required("admin")
def admin_doctor_list(request):
    from accounts.models import DoctorProfile

    status_filter = request.GET.get("status", "")

    qs = DoctorProfile.objects.select_related(
        "user"
    ).order_by("-submitted_at", "-created_at")

    if status_filter:
        qs = qs.filter(status=status_filter)

    counts = {
        "all": DoctorProfile.objects.count(),
        "pending_review": DoctorProfile.objects.filter(
            status="pending_review"
        ).count(),
        "needs_more_info": DoctorProfile.objects.filter(
            status="needs_more_info"
        ).count(),
        "approved": DoctorProfile.objects.filter(
            status="approved"
        ).count(),
        "rejected": DoctorProfile.objects.filter(
            status="rejected"
        ).count(),
        "pending_documents": DoctorProfile.objects.filter(
            status="pending_documents"
        ).count(),
    }

    context = {
        "page_title": ui_gettext("Doctor Applications"),
        "dashboard_role": "admin",
        "active_nav": "doctors",
        "profiles": qs,
        "status_filter": status_filter,
        "counts": counts,
        "status_choices": DoctorProfile.Status.choices,
    }

    return render(
        request,
        "dashboard/admin/doctor_list.html",
        context,
    )


# ============================================================
# ADMIN — DOCTOR APPLICATION DETAIL
# ============================================================

@role_required("admin")
def admin_doctor_detail(request, pk):
    from accounts.models import DoctorProfile

    profile = get_object_or_404(
        DoctorProfile.objects.select_related("user"),
        pk=pk,
    )

    if request.method == "POST":
        action = request.POST.get("action")
        now = timezone.now()

        if action == "approve":
            profile.status = DoctorProfile.Status.APPROVED
            profile.reviewed_at = now
            profile.rejection_reason = ""

            profile.save(
                update_fields=[
                    "status",
                    "reviewed_at",
                    "rejection_reason",
                ]
            )

            profile.user.is_active = True
            profile.user.save(update_fields=["is_active"])

            messages.success(
                request,
                ui_gettext('Dr. %(value0)s has been approved.') % {'value0': profile.user.get_full_name()},
            )

            return redirect("dashboard:admin_doctor_list")

        elif action == "reject":
            reason = request.POST.get(
                "rejection_reason",
                "",
            ).strip()

            if not reason:
                messages.error(
                    request,
                    ui_gettext("Please provide a rejection reason."),
                )
            else:
                profile.status = DoctorProfile.Status.REJECTED
                profile.reviewed_at = now
                profile.rejection_reason = reason

                profile.save(
                    update_fields=[
                        "status",
                        "reviewed_at",
                        "rejection_reason",
                    ]
                )

                profile.user.is_active = False
                profile.user.save(update_fields=["is_active"])

                messages.success(
                    request,
                    ui_gettext("Dr. %(value0)s's application has been rejected.") % {'value0': profile.user.get_full_name()},
                )

                return redirect("dashboard:admin_doctor_list")

        elif action == "needs_more_info":
            note = request.POST.get(
                "reviewer_note",
                "",
            ).strip()

            if not note:
                messages.error(
                    request,
                    ui_gettext("Please write a message for the doctor."),
                )
            else:
                profile.status = DoctorProfile.Status.NEEDS_MORE_INFO
                profile.reviewer_note = note

                profile.save(
                    update_fields=[
                        "status",
                        "reviewer_note",
                    ]
                )

                messages.success(
                    request,
                    ui_gettext('Dr. %(value0)s has been asked for more info.') % {'value0': profile.user.get_full_name()},
                )

                return redirect("dashboard:admin_doctor_list")

    context = {
        "page_title": ui_gettext("Review Application"),
        "dashboard_role": "admin",
        "active_nav": "doctors",
        "profile": profile,
    }

    return render(
        request,
        "dashboard/admin/doctor_detail.html",
        context,
    )


# ============================================================
# ADMIN — USERS
# ============================================================

@role_required("admin")
def admin_users(request):
    """Display and filter registered users for administrators."""

    search_query = request.GET.get("q", "").strip()
    selected_role = request.GET.get("role", "").strip()

    users = User.objects.all().order_by("-date_joined")

    if search_query:
        users = users.filter(
            Q(email__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(username__icontains=search_query)
        )

    if selected_role in User.Role.values:
        users = users.filter(role=selected_role)

    context = {
        "page_title": ui_gettext("Users"),
        "dashboard_role": "admin",
        "users": users,
        "search_query": search_query,
        "selected_role": selected_role,
        "role_choices": User.Role.choices,
        "specialties": Specialty.objects.all(),
        "total_users": User.objects.count(),
    }

    return render(
        request,
        "dashboard/admin/users.html",
        context,
    )


@role_required("admin")
def update_user_role(request, user_id):
    """Update a user's MediConnect role from the admin user table."""

    if request.method != "POST":
        return redirect("dashboard:admin_users")

    user = get_object_or_404(User, pk=user_id)
    role = request.POST.get("role", "")

    if role not in User.Role.values:
        messages.error(
            request,
            ui_gettext("Please select a valid user role."),
        )
        return redirect("dashboard:admin_users")

    if user.role == role:
        messages.info(
            request,
            ui_gettext('%(value0)s already has this role.') % {'value0': user.get_full_name() or user.email},
        )
    else:
        user.role = role
        user.save(update_fields=["role"])

        messages.success(
            request,
            ui_gettext('%(value0)s is now a %(value1)s.') % {'value0': user.get_full_name() or user.email, 'value1': user.get_role_display().lower()},
        )

    return redirect("dashboard:admin_users")


# ============================================================
# DOCTOR — DASHBOARD (REAL DATA)
# ============================================================

@approved_doctor_required
def doctor_overview(request):
    """Display real appointment and patient statistics for a doctor."""

    doctor = request.user
    now = timezone.now()
    today = timezone.localdate()

    appointments = Appointment.objects.filter(
        doctor=doctor
    )

    today_appointments = (
        appointments.filter(start__date=today)
        .exclude(status__in=["cancelled", "rejected"])
        .select_related("patient")
        .order_by("start")
    )

    next_appointment = (
        appointments.filter(start__gte=now)
        .exclude(
            status__in=[
                "cancelled",
                "rejected",
                "no_show",
                "completed",
            ]
        )
        .order_by("start")
        .first()
    )

    total_patients = (
        appointments.values("patient_id")
        .distinct()
        .count()
    )

    week_start = now - timedelta(days=7)

    first_appointments = (
        appointments.values("patient_id")
        .annotate(first_visit=Min("start"))
    )

    new_patients_week = sum(
        1
        for item in first_appointments
        if item["first_visit"] >= week_start
    )

    pending_count = appointments.filter(
        status="pending"
    ).count()

    completed_count = appointments.filter(
        status="completed"
    ).count()

    appointment_list = []

    for appt in today_appointments:
        patient_name = (
            appt.patient.get_full_name()
            or appt.patient.username
        )

        appointment_list.append({
            "patient": patient_name,
            "time": timezone.localtime(
                appt.start
            ).strftime("%I:%M %p"),
            "type": (
                appt.reason
                or appt.get_mode_display()
            ),
            "status": appt.get_status_display(),
        })

    if next_appointment:
        next_appointment_label = (
            ui_gettext("Next at ")
            + timezone.localtime(
                next_appointment.start
            ).strftime("%b %d, %I:%M %p")
        )
    else:
        next_appointment_label = ui_gettext('No upcoming appointments')

    context = {
        "page_title": ui_gettext("My Dashboard"),
        "dashboard_role": "doctor",
        "active_nav": "overview",
        "stats": [
            {
                "label": ui_gettext("Today's appointments"),
                "value": today_appointments.count(),
                "change": next_appointment_label,
                "icon": "C",
            },
            {
                "label": ui_gettext("Total patients"),
                "value": total_patients,
                "change": ui_gettext("+%(count)s this week") % {"count": new_patients_week},
                "icon": "P",
            },
            {
                "label": ui_gettext("Pending appointments"),
                "value": pending_count,
                "change": ui_gettext("Awaiting confirmation"),
                "icon": "R",
            },
            {
                "label": ui_gettext("Completed consultations"),
                "value": completed_count,
                "change": ui_gettext("All time"),
                "icon": "✓",
            },
        ],
        "upcoming_appointments": appointment_list,
    }

    return render(
        request,
        "dashboard/doctor/overview.html",
        context,
    )


# ============================================================
# PATIENT — DASHBOARD (REAL POSTGRESQL DATA)
# ============================================================

@role_required("patient")
def patient_overview(request):
    """Display real appointments, doctors and unread messages."""

    patient = request.user
    now = timezone.now()

    appointments = Appointment.objects.filter(
        patient=patient
    )

    upcoming = (
        appointments.filter(
            start__gte=now,
            status__in=["pending", "confirmed"],
        )
        .select_related("doctor", "doctor__main_specialty")
        .order_by("start")
    )

    upcoming_count = upcoming.count()

    doctors_seen = (
        appointments.filter(status="completed")
        .values("doctor_id")
        .distinct()
        .count()
    )

    unread_messages = (
        Message.objects.filter(
            consultation__appointment__patient=patient,
            lu=False,
        )
        .exclude(auteur=patient)
        .count()
    )

    upcoming_list = []

    for appt in upcoming[:5]:
        doctor = appt.doctor
        doctor_name = (
            doctor.get_full_name()
            or doctor.username
        )

        specialty = getattr(
            doctor,
            "main_specialty",
            None,
        )

        upcoming_list.append({
            "pk": appt.pk,
            "day": timezone.localtime(appt.start).strftime("%d"),
            "month": timezone.localtime(appt.start).strftime("%m"),
            "time": timezone.localtime(appt.start).strftime("%H:%M"),
            "status_label": {"pending": ui_gettext("À confirmer"), "confirmed": ui_gettext("Confirmé")}.get(appt.status, appt.get_status_display()),
            "doctor": f"Dr. {doctor_name}",
            "specialty": (
                specialty.name
                if specialty
                else "General medicine"
            ),
            "date": timezone.localtime(
                appt.start
            ).strftime("%b %d, %Y - %I:%M %p"),
            "status": appt.get_status_display(),
            "mode": appt.get_mode_display(),
        })

    context = {
        "page_title": ui_gettext("Mon accueil"),
        "dashboard_role": "patient",
        "active_nav": "overview",
        "stats": [
            {
                "label": ui_gettext("Upcoming appointments"),
                "value": upcoming_count,
                "change": ui_gettext("Scheduled appointments"),
                "icon": "C",
            },
            {
                "label": ui_gettext("Doctors seen"),
                "value": doctors_seen,
                "change": ui_gettext("Completed visits"),
                "icon": "D",
            },
            {
                "label": ui_gettext("Unread messages"),
                "value": unread_messages,
                "change": ui_gettext("From healthcare providers"),
                "icon": "M",
            },
        ],
        "upcoming_appointments": upcoming_list,
        "upcoming_count": upcoming_count,
        "doctors_seen": doctors_seen,
        "unread_messages": unread_messages,
    }

    return render(
        request,
        "dashboard/patient/overview.html",
        context,
    )


# ============================================================
# PROFILE — ALL ROLES
# ============================================================

@login_required
def profile_view(request):
    """User profile page with face enrollment."""

    return render(
        request,
        "dashboard/profile.html",
        {
            "dashboard_role": request.user.role,
            "active_nav": "profile",
            "page_title": ui_gettext("Profile"),
        },
    )


# ============================================================
# DOCTOR — MY PATIENTS
# ============================================================

@approved_doctor_required
def doctor_patients(request):
    """List patients who have appointments with the logged-in doctor."""

    appointments = Appointment.objects.filter(
        doctor=request.user
    )

    patient_data = (
        appointments
        .values(
            "patient_id",
            "patient__first_name",
            "patient__last_name",
            "patient__username",
            "patient__email",
        )
        .annotate(
            appointment_count=Count("id"),
            last_appointment=Max("start"),
            completed_count=Count(
                "id",
                filter=Q(status="completed"),
            ),
        )
        .order_by(
            "patient__first_name",
            "patient__last_name",
        )
    )

    context = {
        "page_title": ui_gettext("My Patients"),
        "dashboard_role": "doctor",
        "active_nav": "patients",
        "patients": patient_data,
    }

    return render(
        request,
        "dashboard/doctor/patients.html",
        context,
    )
